"""Drives step advancement for an `AcademyManager` + `TutorialOverlay` pair.

`TutorialOverlay` only renders whatever step it's told to render — something
has to notice the step changed, find the widgets a step's
`target_widget_name(s)` refer to, wire up `InteractionStep`'s auto-advance
signal, and poll `VerificationStep`/`ForcedInteractionStep` validators on a
timer. In the Hub that's `WorkspaceWindow.timerEvent()`, deeply tied to
Hub-only concepts (`PluginStoreDialog`, `home_screen`, `FlowCanvas` guide
polygons). An isolated plugin's window has none of that — just one panel —
so this is a separate, smaller driver rather than an attempt to share the
Hub's own window-level logic: same step-type handling, scoped down to a
single `search_root` widget instead of switching between several pages.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, QRect, QTimer
from PyQt6.QtWidgets import QWidget

from .academy import AcademyManager
from .tutorial_models import ActionStep, ForcedInteractionStep, InteractionStep, VerificationStep
from .tutorial_overlay import TutorialOverlay

logger = logging.getLogger(__name__)

_VALIDATION_POLL_TICKS = 20
_TIMER_INTERVAL_MS = 100


class AcademyStepDriver(QObject):
    """Polls `academy_manager.current_step` and drives `overlay` accordingly.

    `search_root` is where target widgets are looked up by object name
    (`findChild`/`findChildren`) — for an isolated plugin this is just its
    own panel. `state_provider` is called on demand to get whatever object a
    course's `IValidator`s expect to `validate()` against (e.g. a plugin's
    own `state`) — a no-op default returns `None` for courses that don't use
    `VerificationStep`/`ForcedInteractionStep` at all.
    """

    def __init__(
        self,
        academy_manager: AcademyManager,
        overlay: TutorialOverlay,
        search_root: QWidget,
        state_provider: Callable[[], Any] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._academy_manager = academy_manager
        self._overlay = overlay
        self._search_root = search_root
        self._state_provider = state_provider or (lambda: None)

        self._connections: dict[str, Any] = {}
        self._last_step_id: str | None = None
        self._verification_wait = 0
        self._verification_attempts = 0
        self._last_action_step_executed: str | None = None
        self._current_forced_step_id: str | None = None
        self._reported_subtask_errors: set[tuple[str, str]] = set()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(_TIMER_INTERVAL_MS)

    def _tick(self) -> None:
        if not self._overlay.isVisible():
            return

        step = self._academy_manager.current_step
        has_completion = (
            hasattr(self._overlay, "completion_container") and self._overlay.completion_container.isVisible()
        )
        if not step and not has_completion:
            self._overlay.hide()
            return

        new_geom = self._search_root.rect()
        if self._overlay.geometry() != new_geom:
            self._overlay.setGeometry(new_geom)
            self._overlay.raise_()
        if not step:
            return

        if step.id != self._last_step_id:
            self._last_step_id = step.id
            self._verification_wait = 0
            self._verification_attempts = 0
            self._overlay.raise_()
            self._overlay.render_step(step)
            if isinstance(step, InteractionStep) and step.target_widget_name:
                self._wire_interaction_step(step)

        if isinstance(step, VerificationStep) and step.validator:
            # A validator can mutate its own step's .text in place (e.g. to
            # report live progress) — render_step() only ran above on an
            # actual step change, so pick up in-place text edits here too.
            if self._overlay.text_label.text() != step.text:
                self._overlay.text_label.setText(step.text)
            self._verification_wait += 1
            if self._verification_wait > _VALIDATION_POLL_TICKS:
                self._verification_wait = 0
                self._poll_verification_step(step)

        if isinstance(step, ForcedInteractionStep) and step.sub_tasks:
            self._process_forced_interaction_step(step)

        if isinstance(step, ActionStep) and step.id != self._last_action_step_executed:
            self._run_action_step(step)

        self._update_targets(step)

    def _wire_interaction_step(self, step: InteractionStep) -> None:
        targets = self._search_root.findChildren(QWidget, step.target_widget_name)
        for target_w in targets:
            if not hasattr(target_w, step.event_trigger):
                continue
            conn_key = f"{step.id}__{step.target_widget_name}__{step.event_trigger}__{id(target_w)}"
            if conn_key in self._connections:
                continue

            def _make_advancer(step_id: str) -> Callable[..., None]:
                def _advance(*_args: Any) -> None:
                    current = self._academy_manager.current_step
                    if current and current.id == step_id:
                        self._academy_manager.next_step()

                return _advance

            advancer = _make_advancer(step.id)
            self._connections[conn_key] = advancer
            try:
                getattr(target_w, step.event_trigger).connect(advancer)
            except Exception as e:
                logger.warning(f"Academy: failed to connect to {step.event_trigger}: {e}")

    def _poll_verification_step(self, step: VerificationStep) -> None:
        app_state = self._state_provider()
        try:
            is_valid = step.validator.validate(app_state)
        except Exception as e:
            logger.exception(f"Academy: VerificationStep validation error: {e}")
            is_valid = False

        if is_valid:
            self._verification_attempts = 0
            self._academy_manager.next_step(step.on_success_step_id)
        elif not getattr(step, "allow_interaction", False) and step.on_fail_step_id:
            max_retries = getattr(step, "max_retries", 0)
            if self._verification_attempts >= max_retries:
                self._verification_attempts = 0
                self._academy_manager.next_step(step.on_fail_step_id)
            else:
                self._verification_attempts += 1

    def _process_forced_interaction_step(self, step: ForcedInteractionStep) -> None:
        if self._current_forced_step_id != step.id:
            self._current_forced_step_id = step.id
            self._reported_subtask_errors = set()

        self._verification_wait += 1
        if self._verification_wait <= _VALIDATION_POLL_TICKS:
            return
        self._verification_wait = 0

        app_state = self._state_provider()
        for task in step.sub_tasks:
            if self._academy_manager.active_subtask_progress.get(task.id, False):
                continue
            if not task.validator:
                self._academy_manager.complete_subtask(task.id)
                continue
            try:
                task_valid = task.validator.validate(app_state)
            except Exception as e:
                if (step.id, task.id) not in self._reported_subtask_errors:
                    logger.exception(f"Academy: SubTask validation error for {task.id}: {e}")
                    self._reported_subtask_errors.add((step.id, task.id))
                task_valid = False
            if task_valid:
                self._academy_manager.complete_subtask(task.id)

        if getattr(step, "auto_advance_when_complete", False) and all(
            self._academy_manager.active_subtask_progress.get(task.id, False) for task in step.sub_tasks
        ):
            self._academy_manager.next_step(step.next_step_id)

    def _run_action_step(self, step: ActionStep) -> None:
        self._last_action_step_executed = step.id
        try:
            if step.action:
                step.action(self._search_root)
        except Exception as e:
            logger.exception(f"Academy: ActionStep error: {e}")
        self._academy_manager.next_step(step.next_step_id)

    def _update_targets(self, step: Any) -> None:
        targets: list[QWidget] = []
        name = getattr(step, "target_widget_name", "")
        if name:
            w = self._search_root.findChild(QWidget, name)
            if w and w.isVisible():
                targets.append(w)
        for name in getattr(step, "target_widget_names", []):
            by_name = [w for w in self._search_root.findChildren(QWidget, name) if w and w.isVisible()]
            if by_name:
                targets.extend(by_name)
            else:
                for w in self._search_root.findChildren(QWidget):
                    if w.property("tutorial_id") == name and w.isVisible():
                        targets.append(w)

        rects = []
        for w in targets:
            global_pos = w.mapToGlobal(w.rect().topLeft())
            local_pos = self._overlay.mapFromGlobal(global_pos)
            rects.append(QRect(local_pos, w.size()))
        self._overlay.set_targets(rects)
