from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

from orchestration.runtime.continuous_runtime_controller import (
    attach_developmental_learning_mission,
    compile_governed_isolated_evaluator_authoring_api_request,
    compile_prompt_complete_isolated_evaluator_authoring_replacement_request,
    compile_retained_teaching_material_recovery_request,
    compile_replacement_isolated_evaluator_authoring_api_request,
    consume_retained_teaching_material_recovery_response,
    begin_isolated_evaluator_authoring_execution,
    handoff_sealed_isolated_evaluator_to_resource_fulfillment,
    consume_continuous_operator_interaction_response,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    record_isolated_evaluator_authoring_provider_result,
    record_recovered_retained_teaching_material,
    recover_nonexecutable_sealed_evaluator_execution,
    recover_validated_sealed_evaluator_learning_execution,
    start_continuous_runtime_controller,
    start_persistent_developmental_agenda,
)
from orchestration.runtime.isolated_evaluator_authoring import (
    CASE_KINDS,
    EXECUTION_CONTRACT_VERSION,
    FULFILLMENT_TYPE,
    compile_isolated_evaluator_authoring_request,
    openai_evaluator_authoring_json_schema,
    project_learner_visible_evaluation_cases,
    validate_provider_authored_evaluator_response,
)
from orchestration.runtime.developmental_learning import (
    DevelopmentalMissionContract,
    execute_learning_attempt,
)
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal
from orchestration.runtime.continuous_worker_supervisor import (
    initialize_supervisor_state,
    request_intentional_worker_stop,
    start_supervised_worker,
)


INSTRUCTION = "Continue your governed developmental agenda. Propose one goal at a time and wait for approval before each mission."


def _source() -> dict[str, object]:
    return {
        "source_kind": "retained_evaluation_gap",
        "domain": "mathematics",
        "topic": "spectral_theorem",
        "target_capability": "complex_inner_product_space_scope",
        "target_behavior": "apply spectral reasoning on independently sealed complex cases",
        "source_gap_ids": ("spectral-complex-gap",),
        "prerequisites": (),
        "evidence": ("retained-spectral-gap",),
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


def _pending(controller: object, kind: str) -> dict[str, object]:
    return next(
        dict(item)
        for item in controller.continuous_developmental_insight_requests
        if item.get("request_kind") == kind and item.get("status") == "pending"
    )


def _deferred_evaluator_controller() -> object:
    controller = replace(
        start_continuous_runtime_controller(session_id="isolated-evaluator-authoring"),
        continuous_learning_state={
            "interest_sources": (_source(),),
            "retained_bundle": {
                "resource_bundle_id": "prior-teaching-only",
                "topic": "spectral_theorem",
                "study_resources": ({"resource_id": "retained-teaching", "topic": "spectral_theorem"},),
                "resource_provenance": ({"source_record_id": "mit-teaching-content-must-not-cross"},),
            },
        },
    )
    proposed = start_persistent_developmental_agenda(controller, INSTRUCTION)
    goal = _pending(proposed, "developmental_goal_approval")
    policy = consume_continuous_operator_interaction_response(
        proposed,
        request_id=str(goal["request_id"]),
        response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal",
        operator_text="Approve bounded evaluator acquisition.",
        approved_scope=str(goal["authority_scope"]),
    )
    authority = _pending(policy, "developmental_resource_authority")
    approved = consume_continuous_operator_interaction_response(
        policy,
        request_id=str(authority["request_id"]),
        response_kind="developmental_resource_authority",
        selected_option="approve_scoped_authority",
        operator_text="Evaluator authority only.",
        approved_scope=str(authority["authority_scope"]),
    )
    fulfillment = _pending(approved, "developmental_resource_fulfillment")
    return consume_continuous_operator_interaction_response(
        approved,
        request_id=str(fulfillment["request_id"]),
        response_kind="developmental_resource_fulfillment",
        selected_option="defer_fulfillment",
        operator_text="",
    )


def _valid_provider_response(request: dict[str, object]) -> dict[str, object]:
    capability = request["input_packet"]["capability_specification"]
    return {
        "fulfillment_type": FULFILLMENT_TYPE,
        "execution_contract_version": EXECUTION_CONTRACT_VERSION,
        "source_identity": "openai-isolated-evaluator-v1",
        "source_reference": "provider://openai/isolated-evaluator-v1",
        "source_digest": "provider-evaluator-digest-v1",
        "provenance": {
            "authoring_method": "isolated-provider-authoring",
            "independence_statement": "authoring input did not contain learner material",
        },
        "topic": capability["topic"],
        "target_capability": capability["target_capability"],
        "candidate_mutable": False,
        "independent_evaluator": {
            "evaluator_identity": "isolated-provider-evaluator-v1",
            "teaching_source_isolated": True,
        },
        "authoring_provenance": {
            "provider": request["provider"],
            "model": request["model"],
            "input_packet_digest": request["input_packet_digest"],
            "request_id": request["request_id"],
            "timestamp": "2026-07-17T00:00:00+00:00",
        },
        "sealed_evaluation_cases": tuple(
            {
                "case_id": f"spectral-{kind}",
                "case_kind": kind,
                "task_type": "deterministic_linear_algebra_check",
                "target_capability": capability["target_capability"],
                "assessment_dimension": capability["target_capability"],
                "execution_contract_version": EXECUTION_CONTRACT_VERSION,
                "learner_view": {
                    "category": kind,
                    "prompt": f"Provide a bounded {kind} spectral-theorem response for the stated independent case.",
                    "response_format": "short structured explanation",
                    "constraints": ("state assumptions",),
                    "instruction": "Return the required concepts as a structured explanation.",
                    "input_data": {"input_kind": "text_context", "prompt_context": kind, "matrix_data": None, "vector_data": None, "scalar_parameters": ()},
                    "response_schema": {"response_kind": "text_explanation", "required_fields": ({"field_name": "explanation", "field_type": "text"},), "allow_additional_fields": False, "max_response_words": 120},
                },
                "evaluator_view": {
                    "answer_key": None,
                    "scoring_rule": {
                        "procedure": "verify the declared property using an independent deterministic predicate",
                        "pass_condition": "the predicate succeeds for the declared case",
                    },
                    "deterministic_predicate": {"type": "required_concept_coverage", "required_concepts": ("Hermitian matrix",), "forbidden_concepts": (), "minimum_coverage": 1.0},
                    "rubric": ("uses the declared independent predicate",),
                    "pass_threshold": 1.0,
                    "provenance": {"evaluator_case_author": "isolated-provider-authoring"},
                },
            }
            for kind in CASE_KINDS
        ),
    }


def _legacy_prompt_blocked_controller(handed_off: object) -> object:
    """Turn a valid fixture package into immutable v1 historical evidence."""

    state = dict(handed_off.continuous_learning_state)
    authoring = dict(state["isolated_evaluator_authoring"])
    result = dict(authoring["result"])
    package = dict(result["sealed_package"])
    legacy_cases = tuple({
        "case_id": case["case_id"],
        "case_kind": case["case_kind"],
        "task_type": case["task_type"],
        "answer_key": case["evaluator_view"]["answer_key"],
        "scoring_rule": case["evaluator_view"]["scoring_rule"],
    } for case in package["sealed_evaluation_cases"])
    legacy_package = {**package, "sealed_evaluation_cases": legacy_cases}
    legacy_result = {**result, "sealed_package": legacy_package}
    return replace(
        handed_off,
        continuous_mission_state="developmental_resource_fulfillment_incomplete",
        active_work_item="learner_visible_evaluation_prompts_unavailable",
        continuous_learning_state={
            **state,
            "isolated_evaluator_authoring": {**authoring, "status": "result_handed_off", "result": legacy_result},
            "resource_blocker": {
                "blocker": "retained_learning_material_not_executable",
                "missing_fields": ("missing_learner_visible_evaluation_prompts",),
            },
        },
    )


def test_evaluator_first_goal_retains_one_dormant_learning_mission_for_policy_lineage():
    deferred = _deferred_evaluator_controller()
    state = deferred.continuous_learning_state
    mission = state["mission"]
    requirement = state["developmental_resource_policy"]["requirement"]

    assert mission["mission_id"]
    assert requirement["mission_id"] == mission["mission_id"]
    assert state["developmental_agenda"]["active_mission_id"] == mission["mission_id"]
    assert not deferred.continuous_active_subgoal


def test_nested_provider_evaluator_without_existing_execution_contract_fails_before_attempt():
    deferred = _deferred_evaluator_controller()
    mission = deferred.continuous_learning_state["mission"]
    request = compile_isolated_evaluator_authoring_request(
        mission_id=mission["mission_id"],
        requirement=deferred.continuous_learning_state["developmental_resource_policy"]["requirement"],
        provider="openai",
        model="gpt-4.1-mini",
    )
    package = _valid_provider_response(request)
    bundle = {
        "topic": "spectral_theorem",
        "assessment_dimensions": ({
            "dimension": "complex_inner_product_space_scope",
            "topic": "spectral_theorem",
            "baseline_case_id": "baseline",
            "baseline_components": (),
            "required_components": ("Hermitian matrix",),
            "prerequisites": (),
            "evidence_ref": "teaching",
            "expected_learning_value": 0.8,
            "information_gain": 0.8,
            "estimated_effort": 0.3,
        },),
        "study_resources": ({
            "resource_id": "teaching",
            "topic": "spectral_theorem",
            "supports_dimensions": ("complex_inner_product_space_scope",),
            "study_components": ("Hermitian matrix",),
            "study_facts": ("Hermitian matrices have real eigenvalues.",),
        },),
        "sealed_evaluation_cases": package["sealed_evaluation_cases"],
        "independent_evaluator": package["independent_evaluator"],
    }

    blocked = attach_developmental_learning_mission(
        deferred,
        str(mission["operator_instruction"]),
        bundle,
        existing_mission=DevelopmentalMissionContract(**mission),
        preserve_learning_state=True,
    )

    assert blocked.continuous_mission_state == "developmental_resource_fulfillment_incomplete"
    assert blocked.active_work_item == "sealed_evaluator_execution_contract_unsupported"
    assert not blocked.continuous_active_subgoal
    assert blocked.continuous_learning_state["mission"]["mission_id"] == mission["mission_id"]
    assert "unsupported_execution_contract_version" in blocked.continuous_learning_state["resource_blocker"]["missing_fields"]


def test_legacy_false_exhaustion_is_reclassified_without_replaying_attempt():
    deferred = _deferred_evaluator_controller()
    mission = deferred.continuous_learning_state["mission"]
    package = _valid_provider_response(compile_isolated_evaluator_authoring_request(
        mission_id=mission["mission_id"],
        requirement=deferred.continuous_learning_state["developmental_resource_policy"]["requirement"],
        provider="openai",
        model="gpt-4.1-mini",
    ))
    legacy = replace(
        deferred,
        continuous_mission_state="developmental_agenda_exhausted",
        continuous_learning_state={
            **deferred.continuous_learning_state,
            "retained_bundle": {"sealed_evaluation_cases": package["sealed_evaluation_cases"]},
            "evaluations": ({"evaluation_id": "legacy-evaluation", "content_case_results": ()},),
        },
    )

    corrected = recover_nonexecutable_sealed_evaluator_execution(legacy)

    assert corrected.continuous_mission_state == "developmental_resource_fulfillment_incomplete"
    assert corrected.active_work_item == "sealed_evaluator_execution_contract_unsupported"
    assert corrected.continuous_learning_state["evaluations"] == legacy.continuous_learning_state["evaluations"]
    assert corrected.continuous_learning_state["developmental_agenda"]["status"] == "blocked_resolvable_evaluator_execution_contract"
    assert recover_nonexecutable_sealed_evaluator_execution(corrected) == corrected


def test_authoring_packet_contains_only_evaluation_contract_not_learner_or_teaching_data():
    request = compile_isolated_evaluator_authoring_request(
        mission_id="mission-1",
        requirement={
            "semantic_identity": "semantic-1",
            "topic": "spectral_theorem",
            "target_capability": "complex_inner_product_space_scope",
            "target_behavior": "apply spectral reasoning",
        },
        provider="openai",
        model="gpt-4.1-mini",
    )
    sent = request["system_prompt"] + request["user_prompt"]
    assert request["input_packet"]["required_case_categories"] == CASE_KINDS
    assert request["input_packet"]["authoring_provenance_required"]["request_id"] == request["request_id"]
    assert "learner_internal_study_notes" in sent
    assert "MIT" not in sent
    assert "candidate_answer" not in request["input_packet"]
    assert request["output_contract"]["sealed_from_learner_before_attempt"] is True


def test_provider_response_requires_strict_schema_and_rejects_nested_teaching_or_learner_leakage():
    request = compile_isolated_evaluator_authoring_request(
        mission_id="mission-1",
        requirement={
            "semantic_identity": "semantic-1",
            "topic": "spectral_theorem",
            "target_capability": "complex_inner_product_space_scope",
            "target_behavior": "apply spectral reasoning",
        },
        provider="openai",
        model="gpt-4.1-mini",
    )
    accepted = validate_provider_authored_evaluator_response(request, _valid_provider_response(request))
    assert accepted["accepted"] is True
    assert accepted["sealed_package"]["learner_visible_metadata"]["answer_key_exposed"] is False

    leaky = _valid_provider_response(request)
    leaky["independent_evaluator"] = {**leaky["independent_evaluator"], "teaching_content": "forbidden"}
    rejected = validate_provider_authored_evaluator_response(request, leaky)
    assert rejected["accepted"] is False
    assert "forbidden_learner_or_teaching_field_present" in rejected["errors"]


def test_provider_response_with_wrong_nested_json_shapes_is_a_schema_rejection_not_a_transport_error():
    request = compile_isolated_evaluator_authoring_request(
        mission_id="mission-1",
        requirement={
            "semantic_identity": "semantic-1",
            "topic": "spectral_theorem",
            "target_capability": "complex_inner_product_space_scope",
            "target_behavior": "apply spectral reasoning",
        },
        provider="openai",
        model="gpt-4.1-mini",
    )
    malformed = _valid_provider_response(request)
    malformed["independent_evaluator"] = True
    malformed["authoring_provenance"] = False

    rejected = validate_provider_authored_evaluator_response(request, malformed)

    assert rejected["accepted"] is False
    assert "independent_evaluator_not_object" in rejected["errors"]
    assert "authoring_provenance_not_object" in rejected["errors"]


def test_provider_response_rejects_wrong_fulfillment_missing_case_evidence_truncated_and_prose_wrapped_json():
    request = compile_isolated_evaluator_authoring_request(
        mission_id="mission-1",
        requirement={
            "semantic_identity": "semantic-1",
            "topic": "spectral_theorem",
            "target_capability": "complex_inner_product_space_scope",
            "target_behavior": "apply spectral reasoning",
        },
        provider="openai",
        model="gpt-4.1-mini",
    )
    wrong_type = _valid_provider_response(request)
    wrong_type["fulfillment_type"] = "provider_authored_sealed_evaluator_fulfillment"
    assert "invalid_fulfillment_type" in validate_provider_authored_evaluator_response(request, wrong_type)["errors"]

    missing_case_evidence = _valid_provider_response(request)
    missing_case_evidence["sealed_evaluation_cases"][0]["evaluator_view"]["scoring_rule"] = None
    assert "case_answer_key_or_scoring_rule_missing" in validate_provider_authored_evaluator_response(request, missing_case_evidence)["errors"]

    assert validate_provider_authored_evaluator_response(request, '{"fulfillment_type":')["errors"] == ("response_not_valid_json_object",)
    prose_wrapped = "Here is the package:\n" + json.dumps(_valid_provider_response(request))
    assert validate_provider_authored_evaluator_response(request, prose_wrapped)["errors"] == ("response_not_valid_json_object",)


def test_authoring_packet_names_required_nested_objects_and_replacement_can_follow_schema_failure():
    pending = compile_governed_isolated_evaluator_authoring_api_request(_deferred_evaluator_controller())
    request = _pending(pending, "developmental_evaluator_authoring_api")
    packet = pending.continuous_learning_state["isolated_evaluator_authoring"]["request"]
    schema = packet["input_packet"]["schema_requirements"]
    assert schema["field_types"]["independent_evaluator"]["type"] == "object"
    assert schema["field_types"]["authoring_provenance"]["type"] == "object"
    assert schema["field_types"]["provenance"] == "nonempty_object"
    assert "never booleans" in packet["system_prompt"]
    assert packet["input_packet"]["response_shape_example"]["fulfillment_type"] == FULFILLMENT_TYPE
    assert len(packet["input_packet"]["response_shape_example"]["sealed_evaluation_cases"]) == len(CASE_KINDS)
    native_schema = openai_evaluator_authoring_json_schema(packet)
    assert native_schema["properties"]["fulfillment_type"]["const"] == FULFILLMENT_TYPE
    assert native_schema["properties"]["independent_evaluator"]["type"] == "object"
    assert native_schema["properties"]["sealed_evaluation_cases"]["items"]["properties"]["learner_view"]["type"] == "object"

    approved = consume_continuous_operator_interaction_response(
        pending,
        request_id=str(request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve one isolated authoring call.",
        approved_scope=str(request["authority_scope"]),
    )
    malformed = _valid_provider_response(packet)
    malformed["independent_evaluator"] = True
    invalid = record_isolated_evaluator_authoring_provider_result(
        begin_isolated_evaluator_authoring_execution(approved),
        raw_response=malformed,
    )
    assert invalid.continuous_mission_state == "isolated_evaluator_authoring_result_invalid"
    forensic = invalid.continuous_learning_state["isolated_evaluator_authoring"]["result"]["operator_only_forensic_response"]
    assert forensic["raw_response"] == malformed
    assert forensic["learner_visible"] is False
    assert forensic["capability_eligible"] is False
    replacement = compile_replacement_isolated_evaluator_authoring_api_request(invalid)
    assert _pending(replacement, "developmental_evaluator_authoring_api")["request_id"] != request["request_id"]


def test_sealed_provider_evaluator_uses_existing_fulfillment_path_without_capability_promotion():
    pending = compile_governed_isolated_evaluator_authoring_api_request(_deferred_evaluator_controller())
    request = _pending(pending, "developmental_evaluator_authoring_api")
    approved = consume_continuous_operator_interaction_response(
        pending,
        request_id=str(request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve evaluator authoring.",
        approved_scope=str(request["authority_scope"]),
    )
    sealed = record_isolated_evaluator_authoring_provider_result(
        begin_isolated_evaluator_authoring_execution(approved),
        raw_response=_valid_provider_response(approved.continuous_learning_state["isolated_evaluator_authoring"]["request"]),
    )
    handed_off = handoff_sealed_isolated_evaluator_to_resource_fulfillment(sealed)
    state = handed_off.continuous_learning_state
    assert state["isolated_evaluator_authoring"]["status"] == "result_handed_off"
    assert state["developmental_resource_fulfillments"][-1]["status"] == "validated"
    assert not state.get("capability_update")
    assert handed_off.continuous_mission_state == "developmental_resource_fulfillment_incomplete"
    assert handed_off.active_work_item == "retained_learning_material_incomplete"
    assert "missing_assessment_dimensions" in state["resource_blocker"]["missing_fields"]
    assert state["resource_blocker"]["no_provider_or_research_call_performed"] is True
    assert handoff_sealed_isolated_evaluator_to_resource_fulfillment(handed_off) == handed_off
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=handed_off.session_id),
        export_continuous_mission_restart_state(handed_off),
    )
    assert restored.continuous_mission_state == "developmental_resource_fulfillment_incomplete"
    assert restored.active_work_item == "retained_learning_material_incomplete"
    assert restored.continuous_learning_state["resource_blocker"] == state["resource_blocker"]
    assert not restored.continuous_active_subgoal
    assert handoff_sealed_isolated_evaluator_to_resource_fulfillment(restored) == restored


def test_validated_v3_evaluator_rebinds_the_same_mission_after_pre_v3_adapter_restart(tmp_path: Path):
    pending = compile_governed_isolated_evaluator_authoring_api_request(_deferred_evaluator_controller())
    request = _pending(pending, "developmental_evaluator_authoring_api")
    approved = consume_continuous_operator_interaction_response(
        pending,
        request_id=str(request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve evaluator authoring.",
        approved_scope=str(request["authority_scope"]),
    )
    sealed = record_isolated_evaluator_authoring_provider_result(
        begin_isolated_evaluator_authoring_execution(approved),
        raw_response=_valid_provider_response(approved.continuous_learning_state["isolated_evaluator_authoring"]["request"]),
    )
    handed_off = handoff_sealed_isolated_evaluator_to_resource_fulfillment(sealed)
    state = dict(handed_off.continuous_learning_state)
    bundle = dict(state["retained_bundle"])
    bundle.update({
        "assessment_dimensions": ({
            "dimension": "complex_inner_product_space_scope",
            "topic": "spectral_theorem",
            "baseline_case_id": "spectral-baseline",
            "baseline_components": (),
            "required_components": ("Hermitian matrix",),
            "prerequisites": (),
            "evidence_ref": "retained-teaching",
            "expected_learning_value": 0.8,
            "information_gain": 0.8,
            "estimated_effort": 0.3,
        },),
        "study_resources": ({
            "resource_id": "retained-teaching",
            "topic": "spectral_theorem",
            "supports_dimensions": ("complex_inner_product_space_scope",),
            "study_components": ("Hermitian matrix",),
            "study_facts": ("Hermitian matrices have real eigenvalues.",),
        },),
    })
    legacy_adapter_state = replace(
        handed_off,
        continuous_learning_state={**state, "retained_bundle": bundle},
    )
    provider_calls = legacy_adapter_state.continuous_api_authority["calls_consumed"]
    fulfillment_count = len(state["developmental_resource_fulfillments"])

    resumed = recover_validated_sealed_evaluator_learning_execution(legacy_adapter_state)

    assert resumed.continuous_mission_state == "learning_subgoal_active"
    assert resumed.continuous_active_subgoal
    assert resumed.continuous_active_subgoal["mission_id"] == state["mission"]["mission_id"]
    assert resumed.continuous_api_authority["calls_consumed"] == provider_calls
    assert len(resumed.continuous_learning_state["developmental_resource_fulfillments"]) == fulfillment_count
    assert recover_validated_sealed_evaluator_learning_execution(resumed) == resumed

    executed, _result = execute_continuous_active_subgoal(
        resumed,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
    )
    attempt = executed.continuous_learning_state["attempts"][-1]
    assert {item["case_id"] for item in attempt["task_records"]} == {
        "spectral-baseline", "spectral-control", "spectral-held_out", "spectral-adversarial", "spectral-transfer",
    }
    assert all(not item["response_schema_errors"] for item in attempt["task_records"])
    assert "answer_key" not in str(attempt["task_records"])
    evaluation = executed.continuous_learning_state["evaluations"][-1]
    assert set(evaluation["case_ids"]) == {item["case_id"] for item in attempt["task_records"]}


def test_v3_prompt_conditioning_selects_public_evidence_and_reports_missing_teaching_facts():
    subgoal = SimpleNamespace(
        subgoal_id="v3-prompt-conditioning",
        mission_id="mission-1",
        attempt_type="guided_study_attempt",
        capability_target="linear_operator_reasoning",
        study_resource_ids=("teaching",),
    )
    bundle = {
        "execution_contract_version": EXECUTION_CONTRACT_VERSION,
        "study_resources": ({
            "resource_id": "teaching",
            "study_components": ("normal operator", "counterexample"),
            "study_facts": (
                "A normal operator commutes with its adjoint.",
                "Not every complex matrix is normal.",
            ),
        },),
        "sealed_evaluation_cases": (
            {
                "case_id": "proof",
                "case_kind": "control",
                "task_type": "concept_coverage",
                "capability_dimension": "linear_operator_reasoning",
                "learner_view": {
                    "instruction": "Give a proof sketch for a normal operator.",
                    "prompt": "Explain why a normal operator has the stated property.",
                    "constraints": (),
                    "input_data": {"input_kind": "text_context"},
                    "response_schema": {"response_kind": "text_explanation", "required_fields": ({"field_name": "proof", "field_type": "text"},), "max_response_words": 80},
                },
            },
            {
                "case_id": "correction",
                "case_kind": "adversarial",
                "task_type": "concept_coverage",
                "capability_dimension": "linear_operator_reasoning",
                "learner_view": {
                    "instruction": "Correct the false claim.",
                    "prompt": "Explain the error in saying every complex matrix is normal.",
                    "constraints": (),
                    "input_data": {"input_kind": "text_context"},
                    "response_schema": {"response_kind": "text_explanation", "required_fields": ({"field_name": "correction", "field_type": "text"},), "max_response_words": 80},
                },
            },
            {
                "case_id": "missing",
                "case_kind": "held_out",
                "task_type": "concept_coverage",
                "capability_dimension": "linear_operator_reasoning",
                "learner_view": {
                    "instruction": "Give a proof sketch using Schur decomposition.",
                    "prompt": "Explain the Schur decomposition step.",
                    "constraints": (),
                    "input_data": {"input_kind": "text_context"},
                    "response_schema": {"response_kind": "text_explanation", "required_fields": ({"field_name": "explanation", "field_type": "text"},), "max_response_words": 80},
                },
            },
        ),
    }

    attempt = execute_learning_attempt(subgoal, bundle)
    records = {record["case_id"]: record for record in attempt.task_records}

    assert records["proof"]["response_plan"] == "proof_sketch"
    assert records["correction"]["response_plan"] == "misconception_correction"
    assert records["proof"]["selected_retained_facts"] != records["correction"]["selected_retained_facts"]
    assert records["missing"]["evidence_sufficiency"] == "insufficient_retained_teaching_evidence"
    assert "schur" in records["missing"]["missing_retained_evidence_terms"]
    assert all(not record["response_schema_errors"] for record in records.values())
    assert "answer_key" not in str(attempt.task_records)


def test_newer_validated_evaluator_supersedes_stale_local_reuse_policy_once_without_new_authority():
    pending = compile_governed_isolated_evaluator_authoring_api_request(_deferred_evaluator_controller())
    request = _pending(pending, "developmental_evaluator_authoring_api")
    approved = consume_continuous_operator_interaction_response(
        pending,
        request_id=str(request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve evaluator authoring.",
        approved_scope=str(request["authority_scope"]),
    )
    sealed = record_isolated_evaluator_authoring_provider_result(
        begin_isolated_evaluator_authoring_execution(approved),
        raw_response=_valid_provider_response(approved.continuous_learning_state["isolated_evaluator_authoring"]["request"]),
    )
    state = dict(sealed.continuous_learning_state)
    authoring = dict(state["isolated_evaluator_authoring"])
    policy = dict(state["developmental_resource_policy"])
    stale_decision = {**dict(policy["decision"]), "decision_id": "stale-local-reuse-decision", "action_type": "reuse_validated_retained_resource"}
    stale = replace(
        sealed,
        continuous_learning_state={
            **state,
            "developmental_resource_policy": {**policy, "decision": stale_decision},
            "resource_policy_authorities": {
                **dict(state.get("resource_policy_authorities") or {}),
                "sealed_evaluator": {"request_id": authoring["authority_request_id"]},
            },
        },
    )
    before_projection = project_learner_visible_evaluation_cases(authoring["result"]["sealed_package"])
    before_requests = stale.continuous_developmental_insight_requests
    before_claim = authoring["execution_claim"]
    before_calls = stale.continuous_api_authority["calls_consumed"]
    prior_fulfillment_count = len(state["developmental_resource_fulfillments"])

    handed_off = handoff_sealed_isolated_evaluator_to_resource_fulfillment(stale)
    updated = handed_off.continuous_learning_state
    effective_policy = updated["developmental_resource_policy"]
    assert effective_policy["decision"]["action_type"] == "request_operator_sealed_evaluator"
    assert effective_policy["decision_history"][-1]["decision"] == stale_decision
    assert effective_policy["decision_history"][-1]["status"] == "superseded_by_validated_sealed_evaluator"
    assert len(updated["developmental_resource_fulfillments"]) == prior_fulfillment_count + 1
    assert updated["developmental_resource_fulfillments"][-1]["status"] == "validated"
    assert handed_off.continuous_api_authority["calls_consumed"] == before_calls
    assert handed_off.continuous_developmental_insight_requests == before_requests
    assert updated["isolated_evaluator_authoring"]["execution_claim"] == before_claim
    assert project_learner_visible_evaluation_cases(
        authoring["result"]["sealed_package"]
    ) == before_projection
    assert not handed_off.continuous_active_subgoal
    assert not updated.get("capability_update")
    assert handoff_sealed_isolated_evaluator_to_resource_fulfillment(handed_off) == handed_off

    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=handed_off.session_id),
        export_continuous_mission_restart_state(handed_off),
    )
    assert restored.continuous_learning_state["developmental_resource_policy"]["decision_history"] == effective_policy["decision_history"]
    assert handoff_sealed_isolated_evaluator_to_resource_fulfillment(restored) == restored

    invalid = replace(
        stale,
        continuous_learning_state={
            **stale.continuous_learning_state,
            "isolated_evaluator_authoring": {**authoring, "result": {**authoring["result"], "status": "invalid", "sealed_package": {}}},
        },
    )
    assert handoff_sealed_isolated_evaluator_to_resource_fulfillment(invalid) == invalid


def test_exact_retained_teaching_recovery_request_is_bound_and_does_not_issue_work():
    pending = compile_governed_isolated_evaluator_authoring_api_request(_deferred_evaluator_controller())
    request = _pending(pending, "developmental_evaluator_authoring_api")
    approved = consume_continuous_operator_interaction_response(
        pending,
        request_id=str(request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve evaluator authoring.",
        approved_scope=str(request["authority_scope"]),
    )
    sealed = record_isolated_evaluator_authoring_provider_result(
        begin_isolated_evaluator_authoring_execution(approved),
        raw_response=_valid_provider_response(approved.continuous_learning_state["isolated_evaluator_authoring"]["request"]),
    )
    handed_off = handoff_sealed_isolated_evaluator_to_resource_fulfillment(sealed)
    state = dict(handed_off.continuous_learning_state)
    bundle = dict(state["retained_bundle"])
    bundle["resource_provenance"] = ({
        "source_record_id": "external-research-source-mit-spectral",
        "canonical_reference": "https://ocw.mit.edu/courses/18-701-algebra-i-fall-2010/resources/mit18_701f10_spthm/",
        "content_digest": "retained-mit-spectral-digest",
    },)
    bundle["study_resources"] = ({
        "resource_id": "external-research-source-mit-spectral",
        "source_record_id": "external-research-source-mit-spectral",
        "topic": "spectral_theorem",
        "study_components": ("source_grounded_explanation",),
    },)
    incomplete = replace(handed_off, continuous_learning_state={**state, "retained_bundle": bundle})
    recovery = compile_retained_teaching_material_recovery_request(incomplete)
    recovery_request = _pending(recovery, "developmental_teaching_material_recovery_authority")
    assert recovery_request["source_locator"] == "https://ocw.mit.edu/courses/18-701-algebra-i-fall-2010/resources/mit18_701f10_spthm/"
    assert recovery_request["authority_granted"] is False
    assert recovery_request["evaluator_projection"]["status"] == "ready"
    assert recovery_request["evaluator_projection"]["errors"] == ()
    assert recovery.continuous_api_authority == incomplete.continuous_api_authority
    assert not recovery.continuous_active_subgoal
    assert compile_retained_teaching_material_recovery_request(recovery) == recovery


def test_learner_prompt_projection_excludes_evaluator_only_fields():
    projected = project_learner_visible_evaluation_cases({
        "sealed_evaluation_cases": ({
            "case_id": "case-1",
            "case_kind": "held_out",
            "learner_view": {
                "category": "held_out",
                "prompt": "Classify the stated matrix under the declared condition.",
                "response_format": "short structured explanation",
                "constraints": ("show one check",),
            },
            "evaluator_view": {"answer_key": "evaluator-only", "scoring_rule": {"procedure": "evaluator-only", "pass_condition": "evaluator-only"}},
        },),
    })
    assert projected["accepted"] is True
    assert projected["learner_cases"] == ({
        "case_id": "case-1",
        "case_category": "held_out",
        "prompt": "Classify the stated matrix under the declared condition.",
        "response_format": "short structured explanation",
        "constraints": ("show one check",),
    },)
    assert "answer_key" not in str(projected["learner_cases"])
    assert "scoring_rule" not in str(projected["learner_cases"])


def test_provider_response_requires_nonblank_learner_prompt_and_response_format_for_every_case():
    request = compile_isolated_evaluator_authoring_request(
        mission_id="mission-1",
        requirement={
            "semantic_identity": "semantic-1",
            "topic": "spectral_theorem",
            "target_capability": "complex_inner_product_space_scope",
            "target_behavior": "apply spectral reasoning",
        },
        provider="openai",
        model="gpt-4.1-mini",
    )
    missing_prompt = _valid_provider_response(request)
    del missing_prompt["sealed_evaluation_cases"][0]["learner_view"]["prompt"]
    assert "case_learner_prompt_missing" in validate_provider_authored_evaluator_response(request, missing_prompt)["errors"]

    blank_prompt = _valid_provider_response(request)
    blank_prompt["sealed_evaluation_cases"][0]["learner_view"]["prompt"] = "   "
    assert "case_learner_prompt_missing" in validate_provider_authored_evaluator_response(request, blank_prompt)["errors"]

    missing_response_format = _valid_provider_response(request)
    del missing_response_format["sealed_evaluation_cases"][0]["learner_view"]["response_format"]
    assert "case_learner_response_format_missing" in validate_provider_authored_evaluator_response(request, missing_response_format)["errors"]


def test_legacy_sealed_package_remains_immutable_and_compiles_one_prompt_complete_replacement():
    pending = compile_governed_isolated_evaluator_authoring_api_request(_deferred_evaluator_controller())
    request = _pending(pending, "developmental_evaluator_authoring_api")
    approved = consume_continuous_operator_interaction_response(
        pending,
        request_id=str(request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve evaluator authoring.",
        approved_scope=str(request["authority_scope"]),
    )
    sealed = record_isolated_evaluator_authoring_provider_result(
        begin_isolated_evaluator_authoring_execution(approved),
        raw_response=_valid_provider_response(approved.continuous_learning_state["isolated_evaluator_authoring"]["request"]),
    )
    handed_off = handoff_sealed_isolated_evaluator_to_resource_fulfillment(sealed)
    legacy = _legacy_prompt_blocked_controller(handed_off)
    legacy_package = legacy.continuous_learning_state["isolated_evaluator_authoring"]["result"]["sealed_package"]
    before = copy.deepcopy(legacy_package)
    projection = project_learner_visible_evaluation_cases(legacy_package)
    assert projection["accepted"] is False
    assert projection["errors"] == ("missing_learner_visible_evaluation_prompt",)
    assert legacy_package == before

    replacement = compile_prompt_complete_isolated_evaluator_authoring_replacement_request(legacy)
    pending_replacement = _pending(replacement, "developmental_evaluator_authoring_api")
    replacement_authoring = replacement.continuous_learning_state["isolated_evaluator_authoring"]
    assert replacement.continuous_mission_state == "awaiting_operator_insight"
    assert replacement.active_work_item == "awaiting_prompt_complete_isolated_evaluator_authoring_api_approval"
    assert pending_replacement["request_id"] != request["request_id"]
    assert replacement_authoring["request"]["protocol"] == "isolated_evaluator_authoring_v3"
    assert replacement_authoring["prior_claims"][-1]["status"] == "legacy_sealed_package_missing_learner_projection"
    assert replacement_authoring["prior_claims"][-1]["result"]["sealed_package"] == before
    assert "teaching_source_content" not in replacement_authoring["request"]["input_packet"]
    assert "study_resources" not in replacement_authoring["request"]["input_packet"]
    assert compile_prompt_complete_isolated_evaluator_authoring_replacement_request(replacement) == replacement
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=replacement.session_id),
        export_continuous_mission_restart_state(replacement),
    )
    assert _pending(restored, "developmental_evaluator_authoring_api")["request_id"] == pending_replacement["request_id"]
    assert compile_prompt_complete_isolated_evaluator_authoring_replacement_request(restored) == restored


def test_exact_teaching_recovery_claim_retains_teaching_only_and_preserves_prompt_blocker():
    pending = compile_governed_isolated_evaluator_authoring_api_request(_deferred_evaluator_controller())
    authoring_request = _pending(pending, "developmental_evaluator_authoring_api")
    approved = consume_continuous_operator_interaction_response(
        pending,
        request_id=str(authoring_request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve evaluator authoring.",
        approved_scope=str(authoring_request["authority_scope"]),
    )
    sealed = record_isolated_evaluator_authoring_provider_result(
        begin_isolated_evaluator_authoring_execution(approved),
        raw_response=_valid_provider_response(approved.continuous_learning_state["isolated_evaluator_authoring"]["request"]),
    )
    handed_off = handoff_sealed_isolated_evaluator_to_resource_fulfillment(sealed)
    handed_off = _legacy_prompt_blocked_controller(handed_off)
    state = dict(handed_off.continuous_learning_state)
    bundle = dict(state["retained_bundle"])
    bundle["resource_provenance"] = ({
        "source_record_id": "external-research-source-mit-spectral",
        "canonical_reference": "https://ocw.mit.edu/courses/18-701-algebra-i-fall-2010/resources/mit18_701f10_spthm/",
        "content_digest": "retained-mit-spectral-digest",
    },)
    bundle["study_resources"] = ({
        "resource_id": "external-research-source-mit-spectral",
        "source_record_id": "external-research-source-mit-spectral",
        "topic": "spectral_theorem",
    },)
    incomplete = replace(handed_off, continuous_learning_state={**state, "retained_bundle": bundle})
    recovery_pending = compile_retained_teaching_material_recovery_request(incomplete)
    request = _pending(recovery_pending, "developmental_teaching_material_recovery_authority")
    claimed = consume_retained_teaching_material_recovery_response(
        recovery_pending,
        request_id=str(request["request_id"]),
        selected_option="approve_exact_source_recovery",
        operator_text="Approve the exact MIT source recovery.",
        approved_scope=str(request["authority_scope"]),
    )
    claim = claimed.continuous_learning_state["teaching_material_recovery"]["claim"]
    assert claim["claim_state"] == "approved_pending_exact_retrieval"
    assert claimed.continuous_api_authority == recovery_pending.continuous_api_authority
    recovered = record_recovered_retained_teaching_material(
        claimed,
        source_locator=str(request["source_locator"]),
        source_text="The spectral theorem for Hermitian matrices states that a Hermitian matrix is unitarily diagonalizable and has real eigenvalues.",
    )
    artifact = recovered.continuous_learning_state["teaching_material_recovery"]["artifact"]
    assert artifact["source_locator"] == request["source_locator"]
    assert artifact["assessment_dimensions"]
    assert artifact["study_resource"]["visible_practice_cases"]
    assert recovered.continuous_mission_state == "developmental_resource_fulfillment_incomplete"
    assert recovered.active_work_item == "learner_visible_evaluation_prompts_unavailable"
    assert not recovered.continuous_active_subgoal
    assert "answer_key" not in str(recovered.continuous_learning_state["teaching_material_recovery"]["learner_evaluation_projection"])


def test_deferred_evaluator_compiles_one_restart_safe_provider_authoring_request_and_exact_once_claim():
    deferred = _deferred_evaluator_controller()
    pending = compile_governed_isolated_evaluator_authoring_api_request(deferred)
    request = _pending(pending, "developmental_evaluator_authoring_api")
    packet = pending.continuous_learning_state["isolated_evaluator_authoring"]["request"]
    assert pending.continuous_mission_state == "awaiting_operator_insight"
    assert pending.continuous_api_authority == deferred.continuous_api_authority
    assert packet["request_id"] == request["request_id"]
    assert "mit-teaching-content-must-not-cross" not in packet["user_prompt"]
    assert compile_governed_isolated_evaluator_authoring_api_request(pending) == pending

    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="isolated-evaluator-authoring"),
        export_continuous_mission_restart_state(pending),
    )
    replay = compile_governed_isolated_evaluator_authoring_api_request(restored)
    assert _pending(replay, "developmental_evaluator_authoring_api")["request_id"] == request["request_id"]

    approved = consume_continuous_operator_interaction_response(
        replay,
        request_id=str(request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve this isolated evaluator-only call.",
        approved_scope=str(request["authority_scope"]),
    )
    claim = approved.continuous_learning_state["isolated_evaluator_authoring"]["execution_claim"]
    assert claim["claim_state"] == "approved_pending_execution"
    assert claim["execution_attempt_count"] == 0
    assert approved.continuous_api_authority["call_allowance"] == 1
    assert approved.continuous_mission_state == "awaiting_isolated_evaluator_authoring_execution"
    assert not approved.continuous_learning_state.get("capability_update")

    dispatching = begin_isolated_evaluator_authoring_execution(approved)
    assert dispatching.continuous_learning_state["isolated_evaluator_authoring"]["execution_claim"]["execution_attempt_count"] == 1
    assert dispatching.continuous_api_authority["calls_consumed"] == 1
    sealed = record_isolated_evaluator_authoring_provider_result(
        dispatching,
        raw_response=_valid_provider_response(dispatching.continuous_learning_state["isolated_evaluator_authoring"]["request"]),
        provider_usage={"total_tokens": 12},
    )
    assert sealed.continuous_mission_state == "isolated_evaluator_authoring_result_sealed"
    assert sealed.continuous_learning_state["isolated_evaluator_authoring"]["result"]["sealed_package"]["learner_visible_metadata"]["answer_key_exposed"] is False
    assert not sealed.continuous_learning_state.get("capability_update")

    duplicate = consume_continuous_operator_interaction_response(
        sealed,
        request_id=str(request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Duplicate approval.",
        approved_scope=str(request["authority_scope"]),
    )
    assert duplicate.continuous_learning_state["isolated_evaluator_authoring"]["execution_claim"]["execution_attempt_count"] == 1


def test_replacement_authoring_packet_preserves_approved_nonce_through_dispatch():
    pending = compile_governed_isolated_evaluator_authoring_api_request(_deferred_evaluator_controller())
    original_request = _pending(pending, "developmental_evaluator_authoring_api")
    approved = consume_continuous_operator_interaction_response(
        pending,
        request_id=str(original_request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve original preflight attempt.",
        approved_scope=str(original_request["authority_scope"]),
    )
    failed = record_isolated_evaluator_authoring_provider_result(
        begin_isolated_evaluator_authoring_execution(approved),
        raw_response=None,
        provider_error="provider_configuration_not_permitted_or_does_not_match_approved_packet",
    )
    replacement = compile_replacement_isolated_evaluator_authoring_api_request(failed)
    replacement_request = _pending(replacement, "developmental_evaluator_authoring_api")
    replacement_packet = replacement.continuous_learning_state["isolated_evaluator_authoring"]["request"]
    assert replacement_packet["attempt_nonce"]
    assert replacement_packet["request_id"] == replacement_request["request_id"]

    replacement_approved = consume_continuous_operator_interaction_response(
        replacement,
        request_id=str(replacement_request["request_id"]),
        response_kind="developmental_evaluator_authoring_api",
        selected_option="approve_evaluator_authoring_api",
        operator_text="Approve replacement attempt.",
        approved_scope=str(replacement_request["authority_scope"]),
    )
    legacy_state = dict(replacement_approved.continuous_learning_state)
    legacy_authoring = dict(legacy_state["isolated_evaluator_authoring"])
    legacy_packet = dict(legacy_authoring["request"])
    legacy_packet.pop("attempt_nonce")
    legacy = replace(
        replacement_approved,
        continuous_learning_state={
            **legacy_state,
            "isolated_evaluator_authoring": {**legacy_authoring, "request": legacy_packet},
        },
    )
    dispatching = begin_isolated_evaluator_authoring_execution(legacy)
    assert dispatching.continuous_mission_state == "isolated_evaluator_authoring_dispatching"
    assert dispatching.continuous_learning_state["isolated_evaluator_authoring"]["execution_claim"]["execution_attempt_count"] == 1


def test_worker_compiles_deferred_evaluator_to_one_pending_authoring_request(tmp_path: Path):
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(_deferred_evaluator_controller()),
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
        execute_active_subgoal=True,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        deadline = time.monotonic() + 5.0
        restart_path = tmp_path / "restart_state.json"
        request = {}
        while time.monotonic() < deadline:
            state = __import__("json").loads(restart_path.read_text(encoding="utf-8"))
            request = next(
                (
                    dict(item)
                    for item in state["continuous_developmental_insight_requests"]
                    if item.get("request_kind") == "developmental_evaluator_authoring_api"
                    and item.get("status") == "pending"
                ),
                {},
            )
            if request:
                break
            time.sleep(0.05)
        assert request
        assert state["continuous_mission_state"] == "awaiting_operator_insight"
        assert state["continuous_learning_state"]["isolated_evaluator_authoring"]["status"] == "pending_operator_approval"
        assert state["continuous_api_authority"]["calls_consumed"] == 0
    finally:
        request_intentional_worker_stop(tmp_path, reason="test_cleanup")
        if supervisor.process is not None:
            try:
                supervisor.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                supervisor.process.kill()
                supervisor.process.wait(timeout=5)
