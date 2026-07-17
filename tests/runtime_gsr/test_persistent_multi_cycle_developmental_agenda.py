from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    consume_developmental_learning_evaluation,
    consume_continuous_operator_interaction_response,
    export_continuous_mission_restart_state,
    observe_developmental_agenda_mission_outcome,
    restore_continuous_mission_restart_state,
    set_persistent_developmental_agenda_paused,
    start_continuous_runtime_controller,
    start_persistent_developmental_agenda,
)
from orchestration.runtime.developmental_learning import (
    LearningSubgoal,
    evaluate_learning_attempt,
    execute_learning_attempt,
)


INSTRUCTION = "Continue your governed developmental agenda. Propose one goal at a time and wait for approval before each mission."


def _source(topic: str, target: str, gap: str, value: float) -> dict[str, object]:
    return {
        "source_kind": "retained_evaluation_gap",
        "domain": "mathematics" if topic != "natural_selection" else "biology",
        "topic": topic,
        "target_capability": target,
        "target_behavior": f"demonstrate {target.replace('_', ' ')} on an independently retained case",
        "source_gap_ids": (gap,),
        "prerequisites": (),
        "evidence": (f"retained-{topic}-evidence", f"baseline-{gap}"),
        "resource_state": "available_retained",
        "authority_state": "operator_approval_required",
        "evaluator_authorities": ({"strategy": "deterministic_predicate", "identity": f"retained-{topic}-evaluator", "provenance": (f"retained-{topic}-evidence",)},),
        "expected_learning_value": value,
        "transfer_value": value - 0.04,
        "prerequisite_value": value - 0.08,
        "information_gain": value - 0.1,
        "estimated_effort": 0.3,
        "estimated_risk": 0.08,
    }


def _controller() -> object:
    sources = (
        _source("mathematical_induction", "proof_structure", "induction-gap", 0.9),
        _source("spectral_theorem", "symmetric_matrix_reasoning", "spectral-gap", 0.8),
        _source("natural_selection", "selection_mechanism", "selection-gap", 0.7),
    )
    return replace(
        start_continuous_runtime_controller(session_id="persistent-agenda"),
        continuous_learning_state={"interest_sources": sources},
    )


def _pending(controller: object) -> dict[str, object]:
    return next(
        dict(item)
        for item in controller.continuous_developmental_insight_requests
        if item.get("request_kind") == "developmental_goal_approval" and item.get("status") == "pending"
    )


def test_agenda_runs_completed_rejected_then_distinct_pending_cycles():
    first = start_persistent_developmental_agenda(_controller(), INSTRUCTION)
    first_request = _pending(first)
    assert first.continuous_learning_state["developmental_agenda"]["status"] == "proposal_pending"

    approved = consume_continuous_operator_interaction_response(
        first,
        request_id=str(first_request["request_id"]),
        response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal",
        operator_text="Approve the first bounded learning mission.",
        approved_scope=str(first_request["authority_scope"]),
    )
    active_agenda = approved.continuous_learning_state["developmental_agenda"]
    assert active_agenda["status"] == "mission_active"
    assert active_agenda["active_mission_id"]

    second = observe_developmental_agenda_mission_outcome(
        approved,
        outcome_id="agenda-outcome-1",
        outcome="completed",
        evidence_refs=("sealed-induction-evaluation",),
    )
    second_request = _pending(second)
    assert second_request["proposal_id"] != first_request["proposal_id"]
    first_interest = first.continuous_learning_state["developmental_interest"]["selected_interest_id"]
    second_interest = second.continuous_learning_state["developmental_interest"]["selected_interest_id"]
    assert second_interest != first_interest
    assert second.continuous_learning_state["developmental_agenda"]["cycle_count"] == 1

    rejected = consume_continuous_operator_interaction_response(
        second,
        request_id=str(second_request["request_id"]),
        response_kind="developmental_goal_approval",
        selected_option="reject_developmental_goal",
        operator_text="Defer this direction in favor of another available interest.",
        approved_scope="",
    )
    third_request = _pending(rejected)
    assert third_request["proposal_id"] not in {first_request["proposal_id"], second_request["proposal_id"]}
    agenda = rejected.continuous_learning_state["developmental_agenda"]
    assert agenda["rejected_proposal_ids"] == (second_request["proposal_id"],)
    assert agenda["pending_proposal_id"] == third_request["proposal_id"]
    assert rejected.continuous_learning_state["developmental_interest"]["selected_interest_id"] not in {first_interest, second_interest}


def test_existing_sealed_learning_evaluations_return_to_agenda_exactly_once():
    proposed = start_persistent_developmental_agenda(_controller(), INSTRUCTION)
    first = _pending(proposed)
    controller = consume_continuous_operator_interaction_response(
        proposed,
        request_id=str(first["request_id"]),
        response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal",
        operator_text="Proceed through the existing sealed learning lifecycle.",
        approved_scope=str(first["authority_scope"]),
    )
    seen_evaluations = []
    for _ in range(4):
        active = LearningSubgoal(**{
            key: value
            for key, value in controller.continuous_active_subgoal.items()
            if key in LearningSubgoal.__dataclass_fields__
        })
        attempt = execute_learning_attempt(active, controller.continuous_learning_state["retained_bundle"])
        evaluation = evaluate_learning_attempt(active, attempt, controller.continuous_learning_state["retained_bundle"])
        seen_evaluations.append(evaluation.evaluation_id)
        controller = consume_developmental_learning_evaluation(controller, evaluation, attempt=attempt.as_dict())
        if not controller.continuous_active_subgoal:
            break
    next_request = _pending(controller)
    agenda = controller.continuous_learning_state["developmental_agenda"]
    assert len(seen_evaluations) == len(set(seen_evaluations))
    assert agenda["cycle_count"] == 1
    assert agenda["successful_cycle_count"] == 1
    assert next_request["proposal_id"] != first["proposal_id"]
    assert controller.continuous_mission_state == "awaiting_operator_insight"


def test_defer_applies_cooldown_then_selects_one_distinct_alternative():
    proposed = start_persistent_developmental_agenda(_controller(), INSTRUCTION)
    first = _pending(proposed)
    deferred = consume_continuous_operator_interaction_response(
        proposed,
        request_id=str(first["request_id"]),
        response_kind="developmental_goal_approval",
        selected_option="defer_developmental_goal",
        operator_text="Keep the evidence, but defer this direction.",
        approved_scope="",
    )
    alternative = _pending(deferred)
    agenda = deferred.continuous_learning_state["developmental_agenda"]
    assert alternative["proposal_id"] != first["proposal_id"]
    assert agenda["deferred_proposal_ids"] == (first["proposal_id"],)
    assert agenda["remaining_proposal_budget"] == 1


def test_agenda_restart_preserves_pending_proposal_and_suppresses_equivalent_recompile():
    proposed = start_persistent_developmental_agenda(_controller(), INSTRUCTION)
    request = _pending(proposed)
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="persistent-agenda"),
        export_continuous_mission_restart_state(proposed),
    )
    resumed = start_persistent_developmental_agenda(restored, INSTRUCTION)
    pending = _pending(resumed)
    assert pending["proposal_id"] == request["proposal_id"]
    assert len([item for item in resumed.continuous_developmental_insight_requests if item.get("status") == "pending"]) == 1


def test_agenda_pause_budget_and_corrupt_restart_fail_closed():
    proposed = start_persistent_developmental_agenda(_controller(), INSTRUCTION)
    paused = set_persistent_developmental_agenda_paused(proposed, paused=True)
    assert paused.continuous_learning_state["developmental_agenda"]["status"] == "paused"
    resumed = set_persistent_developmental_agenda_paused(paused, paused=False)
    assert resumed.continuous_learning_state["developmental_agenda"]["status"] == "idle"

    restart = export_continuous_mission_restart_state(proposed)
    restart["continuous_learning_state"] = {
        **dict(restart["continuous_learning_state"]),
        "developmental_agenda": {"agenda_id": "corrupt"},
    }
    recovered = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="persistent-agenda"), restart,
    )
    assert recovered.continuous_mission_state == "developmental_agenda_blocked"
    assert recovered.continuous_learning_state["developmental_agenda"]["status"] == "blocked"

    exhausted_state = {
        **dict(proposed.continuous_learning_state),
        "developmental_agenda": {**proposed.continuous_learning_state["developmental_agenda"], "pending_proposal_id": "", "remaining_attempt_budget": 0},
    }
    exhausted = start_persistent_developmental_agenda(replace(proposed, continuous_learning_state=exhausted_state), INSTRUCTION)
    assert exhausted.continuous_mission_state == "developmental_agenda_completed_session"


def test_two_terminal_failures_stop_with_diminishing_return_boundary():
    proposed = start_persistent_developmental_agenda(_controller(), INSTRUCTION)
    first = _pending(proposed)
    approved = consume_continuous_operator_interaction_response(
        proposed, request_id=str(first["request_id"]), response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal", operator_text="Proceed.", approved_scope=str(first["authority_scope"]),
    )
    second = observe_developmental_agenda_mission_outcome(approved, outcome_id="failed-1", outcome="behaviorally_failed")
    second_request = _pending(second)
    approved_second = consume_continuous_operator_interaction_response(
        second, request_id=str(second_request["request_id"]), response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal", operator_text="Proceed once more.", approved_scope=str(second_request["authority_scope"]),
    )
    stopped = observe_developmental_agenda_mission_outcome(approved_second, outcome_id="failed-2", outcome="behaviorally_failed")
    assert stopped.continuous_mission_state == "developmental_agenda_blocked"
    assert stopped.continuous_learning_state["developmental_agenda"]["exhaustion_reasons"] == ("consecutive_failure_budget_reached",)
