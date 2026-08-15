"""Unit tests for karcytics_sdk.plugin.academy.AcademyManager.

Exercises the real state machine against a fake `AcademyEventBus` and a
tmp_path persistence directory — no Qt, no Hub, no plugin process needed,
since the whole point of the dependency-injection split (see academy.py's
module docstring) is that the class itself has no such requirement.
"""

from __future__ import annotations

from typing import Any

import pytest

from karcytics_sdk.plugin.academy import (
    ACADEMY_COURSE_COMPLETED,
    ACADEMY_COURSE_PREPARE_PROJECT,
    ACADEMY_STEP_CHANGED,
    ACADEMY_SUBTASK_COMPLETED,
    AcademyManager,
)
from karcytics_sdk.plugin.tutorial_models import (
    Course,
    ForcedInteractionStep,
    InfoStep,
    SubTask,
    WaitForEventStep,
)


class FakeEventBus:
    """Records every subscribe/unsubscribe/emit call; delivers emitted args
    synchronously to any matching subscriber, mirroring a real bus closely
    enough to exercise WaitForEventStep auto-advance.
    """

    def __init__(self) -> None:
        self.subscriptions: dict[str, list[Any]] = {}
        self.emitted: list[tuple[str, tuple]] = []

    def subscribe(self, topic: str, callback: Any) -> None:
        self.subscriptions.setdefault(topic, []).append(callback)

    def unsubscribe(self, topic: str, callback: Any) -> None:
        if topic in self.subscriptions and callback in self.subscriptions[topic]:
            self.subscriptions[topic].remove(callback)

    def emit(self, topic: str, *args: Any) -> None:
        self.emitted.append((topic, args))
        for callback in list(self.subscriptions.get(topic, [])):
            callback(*args)


@pytest.fixture
def bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def manager(bus, tmp_path) -> AcademyManager:
    return AcademyManager(event_bus=bus, persistence_dir=tmp_path / "academy")


def make_two_step_course(course_id: str = "course_1") -> Course:
    return Course(
        id=course_id,
        title="Test Course",
        badge_reward="Test Badge",
        badge_icon="🏅",
        steps=[
            InfoStep(id="step_1", text="First", next_step_id="step_2"),
            InfoStep(id="step_2", text="Second", next_step_id=None),
        ],
    )


class TestRegisterAndDiscoverCourses:
    def test_register_storyboard_stores_the_course_for_its_module(self, manager):
        course = make_two_step_course()

        manager.register_storyboard("flow_cytometry", course)

        assert manager.courses_by_module["flow_cytometry"] == [course]
        assert manager.get_courses_for_module("flow_cytometry") == [course]

    def test_get_courses_for_unregistered_module_is_an_empty_list(self, manager):
        assert manager.get_courses_for_module("nothing_registered") == []


class TestStartCourse:
    def test_start_course_emits_prepare_project_without_starting(self, manager, bus):
        manager.start_course("course_1")

        assert bus.emitted == [(ACADEMY_COURSE_PREPARE_PROJECT, ("course_1",))]
        assert manager.active_course is None

    def test_start_course_confirmed_activates_first_step(self, manager, bus):
        course = make_two_step_course()
        manager.register_storyboard("m", course)

        started = manager.start_course_confirmed("course_1")

        assert started is True
        assert manager.active_course is course
        assert manager.current_step.id == "step_1"
        assert (ACADEMY_STEP_CHANGED, (manager.current_step,)) in bus.emitted

    def test_start_course_confirmed_returns_false_for_unknown_course(self, manager):
        assert manager.start_course_confirmed("nope") is False
        assert manager.active_course is None


class TestNextStep:
    def test_next_step_advances_to_the_named_next_step(self, manager):
        course = make_two_step_course()
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("course_1")

        manager.next_step()

        assert manager.current_step.id == "step_2"

    def test_next_step_past_the_last_step_completes_the_course(self, manager, bus):
        course = make_two_step_course()
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("course_1")

        manager.next_step()  # -> step_2
        manager.next_step()  # step_2.next_step_id is None -> complete

        assert manager.current_step is None
        assert "course_1" in manager.completed_courses
        completions = [e for e in bus.emitted if e[0] == ACADEMY_COURSE_COMPLETED]
        assert completions == [(ACADEMY_COURSE_COMPLETED, ("course_1", "Test Badge"))]

    def test_next_step_with_no_active_course_is_a_safe_noop(self, manager):
        manager.next_step()
        assert manager.current_step is None


class TestForcedInteractionStep:
    def test_next_step_blocked_until_all_subtasks_complete(self, manager):
        course = Course(
            id="c",
            title="Forced",
            steps=[
                ForcedInteractionStep(
                    id="step_1",
                    text="Do both",
                    next_step_id="step_2",
                    sub_tasks=[
                        SubTask(id="a", instruction="A", target_widget_name="w1"),
                        SubTask(id="b", instruction="B", target_widget_name="w2"),
                    ],
                ),
                InfoStep(id="step_2", text="Done"),
            ],
        )
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("c")

        manager.next_step()
        assert manager.current_step.id == "step_1", "must not advance with 0/2 subtasks done"

        manager.complete_subtask("a")
        manager.next_step()
        assert manager.current_step.id == "step_1", "must not advance with 1/2 subtasks done"

        manager.complete_subtask("b")
        manager.next_step()
        assert manager.current_step.id == "step_2"

    def test_complete_subtask_emits_remaining_count(self, manager, bus):
        course = Course(
            id="c",
            title="Forced",
            steps=[
                ForcedInteractionStep(
                    id="step_1",
                    text="Do both",
                    sub_tasks=[
                        SubTask(id="a", instruction="A", target_widget_name="w1"),
                        SubTask(id="b", instruction="B", target_widget_name="w2"),
                    ],
                ),
            ],
        )
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("c")

        manager.complete_subtask("a")

        assert (ACADEMY_SUBTASK_COMPLETED, ("a", 1)) in bus.emitted

    def test_complete_subtask_with_unknown_id_is_ignored(self, manager, bus):
        course = Course(
            id="c",
            title="Forced",
            steps=[
                ForcedInteractionStep(
                    id="step_1",
                    text="Do one",
                    sub_tasks=[SubTask(id="a", instruction="A", target_widget_name="w1")],
                ),
            ],
        )
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("c")
        bus.emitted.clear()

        manager.complete_subtask("not_a_real_subtask")

        assert bus.emitted == []


class TestWaitForEventStep:
    def test_subscribes_on_start_and_auto_advances_when_the_event_fires(self, manager, bus):
        course = Course(
            id="c",
            title="Waits",
            steps=[
                WaitForEventStep(id="step_1", text="Waiting...", next_step_id="step_2", event_name="PROJECT_LOADED"),
                InfoStep(id="step_2", text="Done"),
            ],
        )
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("c")

        assert "PROJECT_LOADED" in bus.subscriptions
        assert manager.current_step.id == "step_1"

        bus.emit("PROJECT_LOADED", "/some/project")

        assert manager.current_step.id == "step_2"

    def test_advancing_past_a_wait_step_unsubscribes_it(self, manager, bus):
        course = Course(
            id="c",
            title="Waits",
            steps=[
                WaitForEventStep(id="step_1", text="Waiting...", next_step_id="step_2", event_name="PROJECT_LOADED"),
                InfoStep(id="step_2", text="Done"),
            ],
        )
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("c")

        bus.emit("PROJECT_LOADED")

        assert bus.subscriptions["PROJECT_LOADED"] == []

    def test_a_stale_event_after_manually_skipping_the_step_is_ignored(self, manager):
        course = Course(
            id="c",
            title="Waits",
            steps=[
                WaitForEventStep(id="step_1", text="Waiting...", next_step_id="step_2", event_name="PROJECT_LOADED"),
                InfoStep(id="step_2", text="Done", next_step_id="step_1"),
            ],
        )
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("c")
        manager.next_step(specific_step_id="step_2")
        assert manager.current_step.id == "step_2"


class TestProgressPersistence:
    def test_progress_persists_across_manager_instances(self, bus, tmp_path):
        persistence_dir = tmp_path / "academy"
        course = make_two_step_course()

        first = AcademyManager(event_bus=bus, persistence_dir=persistence_dir)
        first.register_storyboard("m", course)
        first.start_course_confirmed("course_1")
        first.next_step()
        first.next_step()  # completes the course

        second = AcademyManager(event_bus=FakeEventBus(), persistence_dir=persistence_dir)

        assert second.completed_courses == ["course_1"]
        assert second.badges[0]["id"] == "course_1"

    def test_missing_progress_file_starts_with_empty_state(self, bus, tmp_path):
        manager = AcademyManager(event_bus=bus, persistence_dir=tmp_path / "nonexistent")

        assert manager.completed_courses == []
        assert manager.badges == []

    def test_record_and_has_prerequisite(self, manager):
        assert manager.has_prerequisite("course_1") is False

        manager.record_prerequisite("course_1", "workflow_hash_abc")

        assert manager.has_prerequisite("course_1") is True


class TestGetProgressAndResetCourse:
    def test_get_progress_is_100_once_completed(self, manager):
        course = make_two_step_course()
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("course_1")
        manager.next_step()
        manager.next_step()

        assert manager.get_progress("course_1") == 100.0

    def test_get_progress_is_zero_for_untouched_course(self, manager):
        assert manager.get_progress("never_started") == 0.0

    def test_reset_course_clears_completion_and_badges(self, manager):
        course = make_two_step_course()
        manager.register_storyboard("m", course)
        manager.start_course_confirmed("course_1")
        manager.next_step()
        manager.next_step()
        assert "course_1" in manager.completed_courses

        manager.reset_course("course_1")

        assert "course_1" not in manager.completed_courses
        assert manager.badges == []
        assert manager.active_course is None


class TestIsCoreIntroDone:
    def test_false_when_not_completed(self, manager):
        assert manager.is_core_intro_done() is False

    def test_true_once_core_intro_v1_is_completed(self, manager):
        course = Course(id="core_intro_v1", title="Core Intro", steps=[InfoStep(id="s", text="hi")])
        manager.register_storyboard("core", course)
        manager.start_course_confirmed("core_intro_v1")
        manager.next_step()  # only step -> completes

        assert manager.is_core_intro_done() is True
