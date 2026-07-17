from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_developmental_resource_policy,
    consume_continuous_operator_interaction_response,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
    start_persistent_developmental_agenda,
)
from orchestration.runtime.developmental_interest import compile_persistent_developmental_agenda
from orchestration.runtime.developmental_resource_policy import (
    compile_developmental_resource_authority_fulfillment,
)
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal


INSTRUCTION = "Continue your governed developmental agenda. Propose one goal at a time and wait for approval before each mission."


def _source() -> dict[str, object]:
    return {
        "source_kind": "retained_evaluation_gap",
        "domain": "mathematics",
        "topic": "spectral_theorem",
        "target_capability": "symmetric_matrix_reasoning",
        "target_behavior": "apply spectral reasoning on independently sealed symmetric-matrix cases",
        "source_gap_ids": ("spectral-complex-gap",),
        "prerequisites": (),
        "evidence": ("spectral-gap",),
        "resource_state": "available_retained",
        "authority_state": "operator_approval_required",
        "evaluator_authorities": (),
        "allow_evaluator_acquisition": True,
        "expected_learning_value": 0.95,
        "transfer_value": 0.9,
        "prerequisite_value": 0.85,
        "information_gain": 0.8,
        "estimated_effort": 0.3,
        "estimated_risk": 0.08,
    }


def _controller() -> object:
    return replace(
        start_continuous_runtime_controller(session_id="fulfillment-resume"),
        continuous_learning_state={"interest_sources": (_source(),)},
    )


def _pending(controller: object, kind: str) -> dict[str, object]:
    return next(
        dict(item)
        for item in controller.continuous_developmental_insight_requests
        if item.get("request_kind") == kind and item.get("status") == "pending"
    )


def _approved_fulfillment_request() -> tuple[object, dict[str, object], dict[str, object]]:
    proposed = start_persistent_developmental_agenda(_controller(), INSTRUCTION)
    goal = _pending(proposed, "developmental_goal_approval")
    policy = consume_continuous_operator_interaction_response(
        proposed,
        request_id=str(goal["request_id"]),
        response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal",
        operator_text="Approve the bounded evaluator acquisition goal.",
        approved_scope=str(goal["authority_scope"]),
    )
    authority = _pending(policy, "developmental_resource_authority")
    approved = consume_continuous_operator_interaction_response(
        policy,
        request_id=str(authority["request_id"]),
        response_kind="developmental_resource_authority",
        selected_option="approve_scoped_authority",
        operator_text="Provide one evaluator package only.",
        approved_scope=str(authority["authority_scope"]),
    )
    return approved, goal, _pending(approved, "developmental_resource_fulfillment")


def _sealed_material() -> dict[str, object]:
    cases = []
    for kind in ("baseline", "control", "held_out", "adversarial", "transfer"):
        cases.append({
            "case_id": f"complex-spectral-{kind}",
            "case_kind": kind,
            "capability_dimension": "symmetric_matrix_reasoning",
            "task_type": "component_assertion",
            "required_components": ("complex spectral scope",),
            "forbidden_components": (),
        })
    return {
        "fulfillment_type": "operator_sealed_evaluator_fulfillment",
        "source_identity": "operator-authored-complex-spectral-evaluator-v1",
        "source_reference": "operator://complex-spectral-evaluator-v1",
        "source_digest": "sealed-evaluator-digest-v1",
        "provenance": ("operator-authored-independent-evaluator-v1",),
        "topic": "spectral_theorem",
        "target_capability": "symmetric_matrix_reasoning",
        "intended_role": "sealed_evaluator",
        "sealed_evaluation_cases": tuple(cases),
        "independent_evaluator": {
            "evaluator_identity": "operator-complex-spectral-sealed-v1",
            "authority_source": "operator-authored-independent-evaluator-v1",
            "authority_digest": "sealed-evaluator-digest-v1",
            "teaching_source_isolated": True,
        },
    }


def _teaching_material() -> dict[str, object]:
    return {
        "fulfillment_type": "operator_teaching_resource_fulfillment",
        "source_identity": "operator-authored-symmetric-spectral-teaching-v1",
        "source_reference": "operator://symmetric-spectral-teaching-v1",
        "source_digest": "teaching-digest-v1",
        "provenance": ("operator-authored-teaching-v1",),
        "topic": "spectral_theorem",
        "target_capability": "symmetric_matrix_reasoning",
        "intended_role": "teaching_resource",
        "capability_catalog": ("symmetric_matrix_reasoning",),
        "assessment_dimensions": ({
            "dimension": "symmetric_matrix_reasoning",
            "baseline_components": (),
            "baseline_case_id": "operator-symmetric-spectral-baseline",
            "required_components": ("complex spectral scope",),
            "prerequisites": (),
            "evidence_ref": "operator-authored-teaching-v1",
            "expected_learning_value": 0.8,
            "information_gain": 0.8,
            "estimated_effort": 0.3,
        },),
        "study_resources": ({
            "resource_id": "operator-symmetric-spectral-study-v1",
            "topic": "spectral_theorem",
            "supports_dimensions": ("symmetric_matrix_reasoning",),
            "study_components": ("complex spectral scope",),
            "visible_practice_cases": ({
                "task_id": "operator-visible-spectral-practice",
                "capability_dimension": "symmetric_matrix_reasoning",
                "task_type": "component_assertion",
                "required_components": ("complex spectral scope",),
                "forbidden_components": (),
            },),
        },),
    }


def test_valid_sealed_fulfillment_resolves_original_blocker_and_resumes_once(tmp_path: Path):
    approved, goal, fulfillment_request = _approved_fulfillment_request()
    evaluator_attached = consume_continuous_operator_interaction_response(
        approved,
        request_id=str(fulfillment_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="supply_fulfillment",
        operator_text=__import__("json").dumps(_sealed_material()),
    )
    state = evaluator_attached.continuous_learning_state
    fulfillment = state["developmental_resource_fulfillments"][0]
    assert fulfillment["status"] == "validated"
    assert fulfillment["blocker_resolution_state"] == "resolved"
    assert not evaluator_attached.continuous_active_subgoal
    teaching_authority = _pending(evaluator_attached, "developmental_resource_authority")
    assert teaching_authority["action_type"] == "request_operator_teaching_resource"
    teaching_approved = consume_continuous_operator_interaction_response(
        evaluator_attached,
        request_id=str(teaching_authority["request_id"]),
        response_kind="developmental_resource_authority",
        selected_option="approve_scoped_authority",
        operator_text="Provide bounded teaching material only.",
        approved_scope=str(teaching_authority["authority_scope"]),
    )
    teaching_request = _pending(teaching_approved, "developmental_resource_fulfillment")
    resumed = consume_continuous_operator_interaction_response(
        teaching_approved,
        request_id=str(teaching_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="supply_fulfillment",
        operator_text=__import__("json").dumps(_teaching_material()),
    )
    state = resumed.continuous_learning_state
    assert state["developmental_resource_policy"]["status"] == "blocker_resolved"
    assert state["developmental_agenda"]["status"] == "mission_active"
    assert state["developmental_interest"]["proposal"]["proposal_id"] == goal["proposal_id"]
    assert resumed.continuous_active_subgoal
    duplicate = consume_continuous_operator_interaction_response(
        resumed,
        request_id=str(teaching_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="supply_fulfillment",
        operator_text=__import__("json").dumps(_teaching_material()),
    )
    assert len(duplicate.continuous_learning_state["developmental_resource_fulfillments"]) == 2
    assert duplicate.continuous_active_subgoal == resumed.continuous_active_subgoal
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="fulfillment-resume"),
        export_continuous_mission_restart_state(resumed),
    )
    assert len(restored.continuous_learning_state["developmental_resource_fulfillments"]) == 2
    assert restored.continuous_active_subgoal["subgoal_id"] == resumed.continuous_active_subgoal["subgoal_id"]
    completed, result = execute_continuous_active_subgoal(
        resumed, artifact_root=tmp_path / "fulfillment-pilot", repository_root=Path.cwd(),
    )
    assert result.disposition == "behaviorally_demonstrated"
    assert completed.continuous_learning_state["developmental_agenda"]["cycle_count"] == 1
    assert not completed.continuous_active_subgoal
    assert len(completed.continuous_learning_state["evaluations"]) == 1


def test_teaching_material_cannot_become_evaluator_authority():
    approved, _goal, fulfillment_request = _approved_fulfillment_request()
    material = {
        **_sealed_material(),
        "fulfillment_type": "operator_teaching_resource_fulfillment",
            "study_resources": ({"resource_id": "teaching", "supports_dimensions": ("symmetric_matrix_reasoning",)},),
    }
    invalid = consume_continuous_operator_interaction_response(
        approved,
        request_id=str(fulfillment_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="supply_fulfillment",
        operator_text=__import__("json").dumps(material),
    )
    fulfillment = invalid.continuous_learning_state["developmental_resource_fulfillments"][0]
    assert fulfillment["status"] == "invalid"
    assert "fulfillment_type_does_not_match_selected_policy_action" in fulfillment["validation_errors"]
    assert not invalid.continuous_active_subgoal


def test_deferred_fulfillment_preserves_blocker_without_resuming_mission():
    approved, _goal, fulfillment_request = _approved_fulfillment_request()
    deferred = consume_continuous_operator_interaction_response(
        approved,
        request_id=str(fulfillment_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="defer_fulfillment",
        operator_text="",
    )
    assert deferred.continuous_mission_state == "developmental_resource_fulfillment_deferred"
    assert not deferred.continuous_active_subgoal
    assert deferred.continuous_learning_state["developmental_resource_fulfillments"][0]["blocker_resolution_state"] == "unresolved"


def test_rejected_partial_and_scope_mismatched_fulfillments_do_not_resume():
    approved, _goal, fulfillment_request = _approved_fulfillment_request()
    rejected = consume_continuous_operator_interaction_response(
        approved,
        request_id=str(fulfillment_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="reject_fulfillment",
        operator_text="",
    )
    assert rejected.continuous_learning_state["developmental_resource_fulfillments"][0]["status"] == "rejected"
    assert not rejected.continuous_active_subgoal

    approved, _goal, fulfillment_request = _approved_fulfillment_request()
    partial = consume_continuous_operator_interaction_response(
        approved,
        request_id=str(fulfillment_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="supply_fulfillment",
        operator_text=__import__("json").dumps({
            **_sealed_material(),
            "fulfillment_type": "partial_fulfillment",
            "partial_sections": ("transfer",),
        }),
    )
    partial_record = partial.continuous_learning_state["developmental_resource_fulfillments"][0]
    assert partial_record["status"] == "partial"
    assert partial_record["blocker_resolution_state"] == "partially_resolved"
    assert not partial.continuous_active_subgoal

    approved, _goal, fulfillment_request = _approved_fulfillment_request()
    mismatch = consume_continuous_operator_interaction_response(
        approved,
        request_id=str(fulfillment_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="supply_fulfillment",
        operator_text=__import__("json").dumps({**_sealed_material(), "topic": "unrelated_topic"}),
    )
    assert "scope_mismatch" in mismatch.continuous_learning_state["developmental_resource_fulfillments"][0]["validation_errors"]
    assert not mismatch.continuous_active_subgoal


def test_pure_contract_rejects_evaluator_leakage_and_unsafe_execution_scope():
    requirement = {
        "agenda_id": "agenda", "mission_id": "mission", "goal_id": "goal", "proposal_id": "proposal",
        "requirement_id": "requirement", "topic": "spectral_theorem", "target_capability": "symmetric_matrix_reasoning",
    }
    evaluator = compile_developmental_resource_authority_fulfillment(
        requirement,
        {"decision_id": "decision", "action_type": "request_operator_sealed_evaluator"},
        authority_request_id="authority", operator_interaction_id="interaction", supplied={**_sealed_material(), "study_resources": ({"resource_id": "leak"},)},
    )
    assert evaluator.status == "invalid"
    assert "teaching_source_conflict" in evaluator.validation_errors
    execution = compile_developmental_resource_authority_fulfillment(
        requirement,
        {"decision_id": "execution", "action_type": "request_execution_authority"},
        authority_request_id="authority", operator_interaction_id="interaction", supplied={
            "fulfillment_type": "execution_authority_fulfillment", "source_identity": "operator-execution",
            "source_reference": "operator://execution", "provenance": ("operator",), "topic": "spectral_theorem",
            "target_capability": "symmetric_matrix_reasoning", "scope": "apply tracked source patch",
        },
    )
    assert execution.status == "invalid"
    assert "execution_scope_not_disposable" in execution.validation_errors


def test_completed_shared_local_model_result_is_advisory_fulfillment_only(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    monkeypatch.setattr(
        "orchestration.runtime.local_model_request_result_ledger.select_model_lane",
        lambda *_: {"available": True, "lane": "reasoning", "selected_model_id": "test-local-model"},
    )
    agenda = compile_persistent_developmental_agenda(operator_scope=INSTRUCTION, material_digest="local-result").as_dict()
    state = {
        "developmental_agenda": agenda,
        "developmental_interest": {
            "proposal": {
                "proposal_id": "proposal-local", "selected_interest_id": "interest-local", "domain": "mathematics",
                "topic": "spectral_theorem", "target_capability": "symmetric_matrix_reasoning",
                "measurable_outcome": "apply spectral reasoning on independently sealed cases", "source_evidence": ("spectral-gap",),
            },
            "candidate_interests": ({
                "interest_id": "interest-local", "domain": "mathematics", "topic": "spectral_theorem",
                "target_capability": "symmetric_matrix_reasoning", "target_behavior": "apply spectral reasoning on independently sealed cases",
                "resource_state": "available_retained", "authority_state": "operator_approval_required", "evaluator_state": "evaluation_plan_ready",
            },),
        },
        "evaluation_strategy": {"selected_plan": {"plan_id": "sealed", "status": "evaluation_plan_ready", "selected_strategy": "deterministic_predicate"}},
    }
    controller = replace(start_continuous_runtime_controller(session_id="local-result"), continuous_learning_state=state)
    policy = compile_governed_developmental_resource_policy(controller)
    authority = _pending(policy, "developmental_resource_authority")
    assert authority["action_type"] == "request_local_model_resource"
    approved = consume_continuous_operator_interaction_response(
        policy, request_id=str(authority["request_id"]), response_kind="developmental_resource_authority",
        selected_option="approve_scoped_authority", operator_text="One advisory explanation.", approved_scope=str(authority["authority_scope"]),
    )
    fulfillment_request = _pending(approved, "developmental_resource_fulfillment")
    request_id = approved.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator")
    ledger.execute_claimed_request(request_id, {"executor": lambda *_: {
        "executed": True, "model_id": "test-local-model",
        "answer": "Spectral theorem statement. Prerequisites include eigenvalues. Example and practice question. Scope uncertainty remains.",
    }})
    observed = consume_continuous_operator_interaction_response(
        approved, request_id=str(fulfillment_request["request_id"]), response_kind="developmental_resource_fulfillment",
        selected_option="observe_completed_local_model_result", operator_text="",
    )
    fulfillment = observed.continuous_learning_state["developmental_resource_fulfillments"][0]
    assert fulfillment["fulfillment_type"] == "local_model_result_fulfillment"
    assert fulfillment["status"] == "validated"
    assert observed.continuous_learning_state["local_model_execution_count"] == 1
    assert not observed.continuous_capability_inventory
    assert ledger.observe_request(request_id)["execution_attempt_count"] == 1


def test_corrupt_fulfillment_restart_fails_closed():
    approved, _goal, fulfillment_request = _approved_fulfillment_request()
    invalid = consume_continuous_operator_interaction_response(
        approved,
        request_id=str(fulfillment_request["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="supply_fulfillment",
        operator_text=__import__("json").dumps({**_sealed_material(), "source_digest": "tampered"}),
    )
    restart = export_continuous_mission_restart_state(invalid)
    restart["continuous_learning_state"] = {
        **restart["continuous_learning_state"],
        "developmental_resource_fulfillments": ({
            **restart["continuous_learning_state"]["developmental_resource_fulfillments"][0],
            "fulfillment_digest": "tampered",
        },),
    }
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="fulfillment-resume"), restart,
    )
    assert restored.continuous_mission_state == "developmental_resource_policy_blocked"
    assert restored.continuous_learning_state["developmental_resource_policy"]["failure_reason"] == "invalid_resource_fulfillment_state_on_restart"
