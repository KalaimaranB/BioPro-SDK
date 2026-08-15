"""Unit tests for karcytics_sdk.plugin.runtime_services.

An isolated plugin process never runs any other way — its standalone `.venv`
never depends on the Hub's own `karcytics` package, so a call site that used
to `from karcytics.core.task_scheduler import task_scheduler` etc. was always
going to be wrong there. This module is the real, permanent, honestly-named
home those imports move to; nothing here is a compatibility shim for a
dual-mode existence that doesn't exist for a plugin pinned to
`process_model = "isolated"`.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from karcytics_sdk.plugin.academy import AcademyManager
from karcytics_sdk.plugin.runtime_services import (
    DiagnosticsForwarder,
    KarcyticsEvent,
    LocalTaskScheduler,
    RemoteEventBus,
    _LocalAcademyEventBus,
    diagnostics,
    event_bus,
    task_scheduler,
    tutorial_manager,
)


class MockAnalyzer:
    def __init__(self, plugin_id: str, *, fail: bool = False):
        from karcytics_sdk.plugin import AnalysisBase

        class _Impl(AnalysisBase):
            def run(_self, state=None):
                if fail:
                    raise ValueError("boom")
                return {"value": 42}

        self._impl = _Impl(plugin_id)

    def __getattr__(self, name):
        return getattr(self._impl, name)


class TestLocalTaskScheduler:
    def test_submit_emits_task_started_and_task_finished(self, qtbot):
        scheduler = LocalTaskScheduler()
        started_ids = []
        scheduler.task_started.connect(started_ids.append)

        with qtbot.waitSignal(scheduler.task_finished, timeout=2000) as blocker:
            worker = scheduler.submit(MockAnalyzer("p"))
            task_id = worker.task_id

        assert task_id in started_ids
        assert blocker.args == [task_id, {"value": 42}]
        assert task_id not in scheduler._active_workers

    def test_submit_emits_task_error_on_failure(self, qtbot):
        scheduler = LocalTaskScheduler()

        with qtbot.waitSignal(scheduler.task_error, timeout=2000) as blocker:
            worker = scheduler.submit(MockAnalyzer("p", fail=True))
            task_id = worker.task_id

        assert blocker.args[0] == task_id
        assert "boom" in blocker.args[1]
        assert task_id not in scheduler._active_workers

    def test_cancel_all_does_not_raise(self):
        LocalTaskScheduler().cancel_all()

    def test_cleanup_disconnect_resilience(self):
        scheduler = LocalTaskScheduler()
        mock_worker = MagicMock()
        scheduler._active_workers["ghost"] = mock_worker
        scheduler._cleanup("ghost")
        assert "ghost" not in scheduler._active_workers


class TestTaskSchedulerSingleton:
    def test_module_level_task_scheduler_is_a_shared_singleton(self):
        """Every call site importing `task_scheduler` from this module must
        resolve to the same underlying instance — that's the entire point of
        replacing the Hub's shared singleton with this process's own.
        """
        from karcytics_sdk.plugin.runtime_services import task_scheduler as again

        assert task_scheduler is again

    def test_lazy_construction_does_not_build_qobject_until_first_use(self):
        """Mirrors the Hub's own TaskSchedulerProxy pattern: constructing a
        QObject before a QApplication fully exists can crash on some
        platforms, so building the real scheduler is deferred to first
        attribute access.
        """
        from karcytics_sdk.plugin.runtime_services import _TaskSchedulerProxy

        proxy = _TaskSchedulerProxy()
        assert proxy._instance is None
        proxy.cancel_all()
        assert proxy._instance is not None


class TestRemoteEventBus:
    def test_emit_forwards_to_hub_as_event_frame(self, monkeypatch):
        sent = []
        monkeypatch.setattr(
            "karcytics_sdk.plugin.runtime_services.send_event",
            lambda topic, payload=None: sent.append((topic, payload)),
        )
        bus = RemoteEventBus()

        bus.emit(KarcyticsEvent.MODULE_OPENED, {"id": "flow_cytometry"})

        assert sent == [("module_opened", {"id": "flow_cytometry"})]

    def test_publish_forwards_to_hub_as_event_frame(self, monkeypatch):
        sent = []
        monkeypatch.setattr(
            "karcytics_sdk.plugin.runtime_services.send_event",
            lambda topic, payload=None: sent.append((topic, payload)),
        )
        RemoteEventBus().publish("custom_topic", {"a": 1})

        assert sent == [("custom_topic", {"a": 1})]

    def test_subscribe_and_unsubscribe_are_safe_noops(self):
        """No cross-process push channel for arbitrary Hub-originated events
        exists yet; documented as a real, permanent no-op rather than an
        error, since nothing in an isolated plugin can rely on receiving one.
        """
        bus = RemoteEventBus()
        bus.subscribe(KarcyticsEvent.ACADEMY_STEP_CHANGED, lambda *a: None)
        bus.unsubscribe(KarcyticsEvent.ACADEMY_STEP_CHANGED, lambda *a: None)

    def test_module_level_event_bus_is_a_remote_event_bus(self):
        assert isinstance(event_bus, RemoteEventBus)


class TestKarcyticsEventAccessor:
    def test_attribute_access_returns_the_name_itself(self):
        assert KarcyticsEvent.MODULE_OPENED == "MODULE_OPENED"
        assert KarcyticsEvent.ANYTHING_AT_ALL == "ANYTHING_AT_ALL"


class TestDiagnosticsForwarder:
    def test_report_error_forwards_message_plugin_id_and_fatal(self, monkeypatch):
        sent = []
        monkeypatch.setattr(
            "karcytics_sdk.plugin.runtime_services.send_event",
            lambda topic, payload=None: sent.append((topic, payload)),
        )

        DiagnosticsForwarder().report_error("oops", plugin_id="flow_cytometry", fatal=True)

        assert sent == [
            (
                "diagnostics_error",
                {
                    "message": "oops",
                    "exception": None,
                    "plugin_id": "flow_cytometry",
                    "fatal": True,
                },
            )
        ]

    def test_report_error_serializes_exception_to_a_string(self, monkeypatch):
        """`exception` is a live BaseException the Hub's own diagnostics API
        accepts, but exceptions aren't msgpack-serializable — must cross the
        wire as a string, matching what the Hub-side handler can consume.
        """
        sent = []
        monkeypatch.setattr(
            "karcytics_sdk.plugin.runtime_services.send_event",
            lambda topic, payload=None: sent.append((topic, payload)),
        )

        DiagnosticsForwarder().report_error("bad transform", exception=ValueError("nope"))

        assert sent[0][1]["exception"] == "nope"

    def test_module_level_diagnostics_is_a_diagnostics_forwarder(self):
        assert isinstance(diagnostics, DiagnosticsForwarder)


class TestLocalAcademyEventBus:
    """Adapts CentralEventBus's single-payload publish/subscribe to the
    multi-arg `emit()` AcademyManager calls (e.g. a `(course_id,
    badge_reward)` pair for ACADEMY_COURSE_COMPLETED).
    """

    def test_zero_arg_emit_delivers_no_args(self):
        bus = _LocalAcademyEventBus()
        received = []
        bus.subscribe("topic", lambda *a: received.append(a))

        bus.emit("topic")

        assert received == [()]

    def test_single_arg_emit_delivers_one_arg(self):
        bus = _LocalAcademyEventBus()
        received = []
        bus.subscribe("topic", lambda *a: received.append(a))

        bus.emit("topic", "step_object")

        assert received == [("step_object",)]

    def test_multi_arg_emit_delivers_all_args(self):
        bus = _LocalAcademyEventBus()
        received = []
        bus.subscribe("topic", lambda *a: received.append(a))

        bus.emit("topic", "course_1", "badge_reward")

        assert received == [("course_1", "badge_reward")]

    def test_unsubscribe_stops_delivery(self):
        bus = _LocalAcademyEventBus()
        received = []

        def callback(*args):
            received.append(args)

        bus.subscribe("topic", callback)
        bus.unsubscribe("topic", callback)
        bus.emit("topic", "x")

        assert received == []


class TestModuleLevelTutorialManager:
    """`tutorial_manager` used to be a `NullTutorialManager` stand-in; it is
    now a real `AcademyManager` wired to this process's own local event bus,
    so every course that only touches the plugin's own live UI actually
    runs (see `academy.py` and this module's docstring for why
    `WaitForEventStep` remains the one gap).
    """

    def test_module_level_tutorial_manager_is_a_real_academy_manager(self):
        assert isinstance(tutorial_manager, AcademyManager)

    def test_register_storyboard_stores_the_course_for_its_module(self):
        from karcytics_sdk.plugin.tutorial_models import Course

        course = Course(id="__test_course__", title="Test")

        tutorial_manager.register_storyboard("__test_module__", course)

        assert tutorial_manager.get_courses_for_module("__test_module__") == [course]


@pytest.fixture(autouse=True)
def _no_leaking_sys_modules():
    """Guards against a future regression reintroducing sys.modules
    injection under the Hub's own `karcytics.*` namespace — this module must
    never do that; it's a set of real, directly-importable objects.
    """
    import sys

    pre_existing = set(sys.modules)
    yield
    leaked = {m for m in sys.modules if m not in pre_existing and m.startswith("karcytics.")}
    assert not leaked, f"runtime_services must never inject fake modules, found: {leaked}"
