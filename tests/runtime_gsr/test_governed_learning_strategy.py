from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_learning_strategy_for_mission,
    consume_continuous_operator_interaction_response,
    start_continuous_runtime_controller,
)
from orchestration.runtime.governed_learning_strategy import (
    compile_governed_learning_strategy,
    learner_visible_strategy_packet,
    validate_governed_learning_strategy,
)


def _state(*, changed_prompt: bool = False) -> dict:
    prompt = "Explain how a bounded relationship applies to an unseen finite case."
    if changed_prompt:
        prompt = "Explain how a different bounded relationship applies to an unseen finite case."
    return {
        "mission": {
            "mission_id": "mission-strategy", "goal_id": "goal-strategy", "topic": "abstract_topic",
            "primary_capability_target": "bounded_relationship", "allowed_resource_classes": ("retained_local_sources",),
            "excluded_resource_classes": ("provider_without_authorization",), "attempt_budget": 1,
        },
        "retained_bundle": {
            "study_resources": ({
                "resource_id": "teaching-1", "topic": "abstract_topic",
                "study_facts": ("A bounded property has a defined scope.",),
                "study_components": ("defined scope",),
                "supports_dimensions": ("bounded_relationship",),
            },),
        },
        "attempts": ({
            "attempt_id": "attempt-1",
            "task_records": ({
                "case_id": "case-1", "case_kind": "held_out", "visible_prompt": prompt,
                "response_schema": {"response_kind": "text_explanation"},
                "candidate_response": {"explanation": "A bounded property has a defined scope."},
                "output_digest": "output-1", "missing_retained_evidence_terms": ("unseen",),
            },),
        },),
        "evaluations": ({"evaluation_id": "evaluation-1", "capability_dimension": "bounded_relationship", "disposition": "behaviorally_failed"},),
        "teaching_material_recovery": {"artifact": {
            "source_identity": "retained-source-1", "source_locator": "https://example.test/exact-source",
            "source_digest": "source-digest-1",
        }},
    }


def test_strategy_packet_excludes_evaluator_material_and_compiles_grounded_questions():
    state = _state()
    state["retained_bundle"]["sealed_evaluation_cases"] = ({"answer_key": {"hidden": True}},)
    packet = learner_visible_strategy_packet(state)
    assert "answer_key" not in str(packet)
    strategy = compile_governed_learning_strategy(packet)
    validation = validate_governed_learning_strategy(strategy.as_dict(), packet)
    assert validation["accepted"]
    assert strategy.learning_questions
    assert strategy.authority_candidates
    assert all("everything" not in item["question"].lower() for item in strategy.learning_questions)
    assert all("what is unseen" not in item["question"].lower() for item in strategy.learning_questions)
    assert all("what is and" not in item["question"].lower() for item in strategy.learning_questions)
    assert all("what does brief" not in item["question"].lower() for item in strategy.learning_questions)


def test_ungrounded_strategy_and_evaluator_leakage_fail_closed():
    packet = learner_visible_strategy_packet(_state())
    strategy = compile_governed_learning_strategy(packet).as_dict()
    strategy["knowledge_inventory"] = ({"claim": "invented", "evidence_refs": ("not-present",)},)
    strategy["evaluator_view"] = {"answer_key": "hidden"}
    validation = validate_governed_learning_strategy(strategy, packet)
    assert not validation["accepted"]
    assert "evaluator_only_material_present" in validation["errors"]
    assert "unsupported_knowledge_claim" in validation["errors"]


def test_controller_persists_one_strategy_and_supersedes_only_on_material_evidence_change():
    controller = start_continuous_runtime_controller(session_id="governed-learning-strategy")
    controller = replace(controller, continuous_learning_state=_state())
    compiled = compile_governed_learning_strategy_for_mission(controller)
    strategy = compiled.continuous_learning_state["governed_learning_strategy"]
    request = compiled.continuous_learning_state["governed_learning_strategy_authority_request"]
    assert strategy["status"] == "learning_strategy_awaiting_authority"
    assert request["status"] == "pending"
    assert request["source_locator"] == "https://example.test/exact-source"
    assert compiled.continuous_mission_state == "learning_strategy_awaiting_authority"
    duplicate = compile_governed_learning_strategy_for_mission(compiled)
    assert duplicate.continuous_learning_state["governed_learning_strategy"]["strategy_id"] == strategy["strategy_id"]
    changed = replace(duplicate, continuous_learning_state={**duplicate.continuous_learning_state, **_state(changed_prompt=True)})
    superseded = compile_governed_learning_strategy_for_mission(changed)
    assert superseded.continuous_learning_state["governed_learning_strategy"]["strategy_id"] != strategy["strategy_id"]
    assert superseded.continuous_learning_state["governed_learning_strategy_history"]


def _pending_strategy_controller():
    controller = start_continuous_runtime_controller(session_id="governed-learning-strategy-response")
    return compile_governed_learning_strategy_for_mission(replace(controller, continuous_learning_state=_state()))


def test_strategy_authority_response_tokens_are_exact_once_and_never_retrieve():
    controller = _pending_strategy_controller()
    request = controller.continuous_learning_state["governed_learning_strategy_authority_request"]
    assert any(item["request_id"] == request["request_id"] for item in controller.continuous_developmental_insight_requests)
    approved = consume_continuous_operator_interaction_response(
        controller, request_id=request["request_id"], response_kind=request["request_kind"], operator_text="",
        selected_option="approve_learning_strategy_authority", approved_scope=request["authority_scope"],
    )
    assert approved.continuous_mission_state == "learning_strategy_acquisition_ready"
    assert approved.continuous_learning_state["governed_learning_strategy"]["status"] == "learning_strategy_acquisition_ready"
    assert approved.continuous_learning_state["governed_learning_strategy_authority_request"]["authority_granted"]
    assert not approved.continuous_active_subgoal
    replay = consume_continuous_operator_interaction_response(
        approved, request_id=request["request_id"], response_kind=request["request_kind"], operator_text="",
        selected_option="approve_learning_strategy_authority", approved_scope=request["authority_scope"],
    )
    assert len(replay.continuous_operator_interaction_responses) == 1


def test_legacy_strategy_request_is_reconciled_into_the_existing_operator_transport():
    controller = _pending_strategy_controller()
    state = dict(controller.continuous_learning_state)
    legacy = {key: value for key, value in state["governed_learning_strategy_authority_request"].items() if key not in {"permitted_responses", "authority_scope", "exact_question"}}
    requests = tuple(
        legacy if item.get("request_id") == legacy["request_id"] else item
        for item in controller.continuous_developmental_insight_requests
    )
    legacy_controller = replace(
        controller,
        continuous_learning_state={**state, "governed_learning_strategy_authority_request": legacy},
        continuous_developmental_insight_requests=requests,
    )
    reconciled = compile_governed_learning_strategy_for_mission(legacy_controller)
    request = reconciled.continuous_learning_state["governed_learning_strategy_authority_request"]
    visible = next(item for item in reconciled.continuous_developmental_insight_requests if item["request_id"] == request["request_id"])
    assert visible["permitted_responses"] == request["permitted_responses"]
    assert visible["permitted_responses"][0] == "approve_learning_strategy_authority"


def test_strategy_authority_rejects_bad_binding_scope_and_preserves_nonapproval_paths():
    controller = _pending_strategy_controller()
    request = controller.continuous_learning_state["governed_learning_strategy_authority_request"]
    wrong_id = consume_continuous_operator_interaction_response(
        controller, request_id="wrong", response_kind=request["request_kind"], operator_text="",
        selected_option="approve_learning_strategy_authority", approved_scope=request["authority_scope"],
    )
    assert not wrong_id.continuous_operator_interaction_responses
    wrong_scope = consume_continuous_operator_interaction_response(
        controller, request_id=request["request_id"], response_kind=request["request_kind"], operator_text="",
        selected_option="approve_learning_strategy_authority", approved_scope="broader scope",
    )
    assert not wrong_scope.continuous_operator_interaction_responses
    rejected = consume_continuous_operator_interaction_response(
        _pending_strategy_controller(), request_id=request["request_id"], response_kind=request["request_kind"], operator_text="",
        selected_option="reject_learning_strategy_authority",
    )
    assert rejected.continuous_mission_state == "learning_strategy_blocked"
    assert not rejected.continuous_operator_interaction_responses[0]["authority_granted"]
    deferred_controller = _pending_strategy_controller()
    deferred_request = deferred_controller.continuous_learning_state["governed_learning_strategy_authority_request"]
    deferred = consume_continuous_operator_interaction_response(
        deferred_controller, request_id=deferred_request["request_id"], response_kind=deferred_request["request_kind"], operator_text="",
        selected_option="defer_learning_strategy_authority",
    )
    assert deferred.continuous_learning_state["governed_learning_strategy"]["status"] == "learning_strategy_deferred"
    assert not deferred.continuous_operator_interaction_responses[0]["authority_granted"]
