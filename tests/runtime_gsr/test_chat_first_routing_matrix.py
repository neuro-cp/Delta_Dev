from dataclasses import replace

import pytest

from orchestration.runtime.chat_first_dispatch_contract import plan_message_dispatch
from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    handle_conversational_message,
    start_or_restore_runtime,
)
from tests.runtime_gsr.chat_first_routing_matrix import ATOMIC_CASES, MIXED_CASES, RUNTIME_STATES, RoutingCase


def _active_state(tmp_path):
    return handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        "Your new goal is to study engine efficiency.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state


def _pending(state, request_type: str):
    request = ChatAddressableRequest(
        request_id=f"matrix-{request_type}",
        request_type=request_type,
        objective_id=state.active_objective.objective_id,
        goal_label="Engine efficiency",
        prompt_text="A bounded matrix request.",
        max_calls=1,
        max_spend_usd=1.0,
    )
    return replace(state, pending_chat_requests=(request,))


def _state_for_case(tmp_path, case: RoutingCase):
    state = _active_state(tmp_path)
    if case.case_id in {"G1", "MX1", "MX2", "MX3", "MX4", "MX5", "MX24", "MX31", "MX35", "MX39", "MX40"}:
        state = start_or_restore_runtime(tmp_path / f"{case.case_id}-fresh")
    if case.case_id in {"A1", "A2", "A3", "A4", "A5", "A6", "MX15", "MX16", "MX17", "MX18", "MX19", "MX32"}:
        state = _pending(state, "capability_adoption_and_restart")
    if case.case_id in {"P1", "P2", "P3", "MX20", "MX21", "MX30", "MX38"}:
        state = _pending(state, "provider_authority")
    if case.case_id in {"S1", "S2", "MX22"}:
        state = _pending(state, "directional_question")
    if case.case_id in {"S3", "MX23"}:
        provider = ChatAddressableRequest("matrix-provider", "provider_authority", state.active_objective.objective_id, "Engine efficiency", "Provider?", max_calls=1, max_spend_usd=1.0)
        direction = ChatAddressableRequest("matrix-direction", "directional_question", state.active_objective.objective_id, "Engine efficiency", "Direction?")
        state = replace(state, pending_chat_requests=(provider, direction))
    return state


@pytest.mark.parametrize("case", ATOMIC_CASES, ids=lambda item: item.case_id)
def test_atomic_matrix_has_declared_foreground_and_control_ownership(tmp_path, case):
    plan = plan_message_dispatch(_state_for_case(tmp_path, case), case.prompt)
    control_types = {item.control_type for item in plan.controls}

    assert plan.persistence.transcript_write_count == 1
    assert plan.persistence.expected_single_user_turn is True
    assert plan.foreground.requested is case.foreground
    if case.control:
        expected = set(case.control.split("+"))
        assert expected & control_types, (case.case_id, case.prompt, control_types)


@pytest.mark.parametrize("case", MIXED_CASES, ids=lambda item: item.case_id)
def test_mixed_matrix_plans_independent_obligations(tmp_path, case):
    plan = plan_message_dispatch(_state_for_case(tmp_path, case), case.prompt)
    control_types = {item.control_type for item in plan.controls}

    assert plan.persistence.transcript_write_count == 1
    assert plan.persistence.expected_single_user_turn is True
    assert plan.foreground.requested is case.foreground
    if case.control:
        expected = set(case.control.split("+"))
        assert expected & control_types, (case.case_id, case.prompt, control_types)


def test_two_controls_are_retained_in_plan_not_overwritten(tmp_path):
    plan = plan_message_dispatch(
        _pending(_active_state(tmp_path), "provider_authority"),
        "Pause the current goal and deny the pending provider request.",
    )

    assert [item.control_type for item in plan.controls] == ["pause_goal", "provider_approval"]
    assert plan.foreground.requested is False


@pytest.mark.parametrize("runtime_state", RUNTIME_STATES)
def test_foreground_question_remains_owned_by_chat_in_every_relevant_runtime_state(tmp_path, runtime_state):
    state = _active_state(tmp_path)
    if runtime_state == "multiple_pending":
        provider = ChatAddressableRequest("provider", "provider_authority", state.active_objective.objective_id, "Engine", "Provider?")
        directional = ChatAddressableRequest("direction", "directional_question", state.active_objective.objective_id, "Engine", "Direction?")
        state = replace(state, pending_chat_requests=(provider, directional))
    elif runtime_state == "archived":
        state = replace(state, active_objective=None, lifecycle_state="archived")
    elif runtime_state != "no_goal":
        state = replace(state, lifecycle_state=runtime_state)
    else:
        state = start_or_restore_runtime(tmp_path / "no-goal")

    plan = plan_message_dispatch(state, "What color is the sky?")

    assert plan.foreground.requested is True
    assert plan.foreground.owner == "rc2_router"
    assert plan.control.detected is False
    assert plan.background.start_requested is False


def test_stale_duplicate_goal_creates_a_fresh_objective_instead_of_claiming_progress(tmp_path):
    state = _active_state(tmp_path)
    stale = replace(state, lifecycle_state="paused_budget", completed_cycle_keys=("cycle-1",) * state.active_objective.cycle_budget)

    result = handle_conversational_message(
        stale,
        "Your new goal is to study engine efficiency.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    assert result.objective_created is True
    assert result.state.active_objective.objective_id != state.active_objective.objective_id
    assert result.state.completed_cycle_keys == ()
    assert "already working" not in result.reply.lower()
