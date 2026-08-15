"""Tests for the vendored karcytics_sdk.plugin.tutorial_models.

A plugin author building Academy course content needs these type
definitions without depending on the Hub's unimportable `karcytics.core.*`
path — this module is their real, permanent home. No new behavior here
versus the Hub's own copy; these tests just confirm the vendored shapes are
usable standalone.
"""

from karcytics_sdk.plugin.tutorial_models import (
    ActionStep,
    BranchingStep,
    Course,
    ForcedInteractionStep,
    InfoStep,
    InteractionStep,
    IValidator,
    SubTask,
    VerificationStep,
    WaitForEventStep,
)


class _AlwaysValid(IValidator):
    def validate(self, app_state) -> bool:
        return True


def test_course_get_step_finds_matching_step():
    course = Course(
        id="c1",
        title="Course 1",
        steps=[InfoStep(id="s1", text="Hello"), InfoStep(id="s2", text="World")],
    )

    assert course.get_step("s2").text == "World"
    assert course.get_step("missing") is None


def test_course_get_main_path_follows_next_step_id_chain():
    course = Course(
        id="c1",
        title="Course 1",
        steps=[
            InfoStep(id="s1", text="a", next_step_id="s2"),
            InfoStep(id="s2", text="b", next_step_id="s3"),
            InfoStep(id="s3", text="c"),
        ],
    )

    assert course.get_main_path() == ["s1", "s2", "s3"]


def test_verification_step_follows_on_success_over_next_step_id():
    course = Course(
        id="c1",
        title="Course 1",
        steps=[
            VerificationStep(id="s1", text="verify", on_success_step_id="s3", next_step_id="s2"),
            InfoStep(id="s2", text="fail path"),
            InfoStep(id="s3", text="success path"),
        ],
    )

    assert course.get_main_path() == ["s1", "s3"]


def test_forced_interaction_step_holds_subtasks_with_validators():
    step = ForcedInteractionStep(
        id="s1",
        text="do things",
        sub_tasks=[
            SubTask(id="t1", instruction="click it", target_widget_name="btn"),
            SubTask(
                id="t2",
                instruction="verify it",
                target_widget_name="canvas",
                validator=_AlwaysValid(),
            ),
        ],
    )

    assert len(step.sub_tasks) == 2
    assert step.sub_tasks[1].validator.validate(None) is True


def test_action_step_holds_a_plain_callable():
    calls = []
    step = ActionStep(id="s1", text="run", action=lambda panel: calls.append(panel))

    step.action("main_panel_sentinel")

    assert calls == ["main_panel_sentinel"]


def test_branching_step_maps_option_labels_to_step_ids():
    step = BranchingStep(id="s1", text="choose", options={"Yes": "s2", "No": "s3"})

    assert step.options["Yes"] == "s2"


def test_wait_for_event_step_stores_event_name():
    step = WaitForEventStep(id="s1", text="waiting", event_name="PROJECT_LOADED")

    assert step.event_name == "PROJECT_LOADED"


def test_interaction_step_defaults():
    step = InteractionStep(id="s1", text="click", target_widget_name="btn")

    assert step.event_trigger == "clicked"


def test_ivalidator_subclass_must_implement_validate():
    import pytest

    class _Incomplete(IValidator):
        pass

    with pytest.raises(TypeError):
        _Incomplete()  # type: ignore[abstract]
