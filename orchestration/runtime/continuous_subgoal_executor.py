"""Execution bridge from continuous subgoals to governed local development.

The continuous runtime controller owns mission semantics. This module consumes
one controller-owned active subgoal and performs bounded local development
work for that subgoal: evidence inspection, baseline, candidate artifact,
focused validation, clean reproduction, and disposition handoff. It does not
select weaknesses, mutate tracked source, approve applications, or change API
authority.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from orchestration.runtime.continuous_mission_foundation import (
    BehavioralFailureRecord,
    BehavioralEvaluationRecord,
    CapabilityKnowledgeRecord,
    RepositoryBehaviorContract,
    capability_is_acquired,
    compile_behavioral_failure_record,
    promote_capability_with_behavioral_evaluation,
)
from orchestration.runtime.continuous_runtime_controller import (
    ContinuousRuntimeController,
    continue_continuous_mission_after_reassessment,
    consume_continuous_capability_reassessment,
    consume_continuous_pcm_bridge_result,
    pause_continuous_mission_for_application,
    consume_developmental_learning_evaluation,
)
from orchestration.runtime.developmental_learning import (
    LearningSubgoal,
    execute_learning_attempt,
    evaluate_learning_attempt,
)
from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime import gsr_a_governed_self_regulation as gsr
from orchestration.runtime.rc2_conversational_mode_router import execute_local_model_answer, select_model_lane


LIVENESS_ONLY_METRICS = (
    "active_continuous_mission",
    "worker_alive",
    "heartbeat",
    "cycle_count",
    "artifact_created",
    "mission_active",
)

CANDIDATE_DESIGN_PROTOCOL = "repository_bound_candidate_design_v1"
CONTINUOUS_PCM_BRIDGE_PROTOCOL = "continuous_to_pcm_closed_loop_fixture_v1"
REPOSITORY_BEHAVIOR_CONTRACT_PROTOCOL = "repository_behavior_contract"
REPOSITORY_BEHAVIOR_CONTRACT_VERSION = "1"
PCM_SUPPORTED_REPAIR_SHAPES = {"expected_symbol_missing", "exact_behavioral_logic_replacement"}
FORBIDDEN_CONTRACT_KEYS = {
    "patch",
    "patch_text",
    "replacement_text",
    "candidate_code",
    "candidate_source",
    "implementation",
    "intended_patch",
    "exact_implementation_instructions",
}


@dataclass(frozen=True)
class ResourceUseRecord:
    resource_type: str
    resource_id: str
    purpose: str
    result: str
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubgoalExecutionResult:
    accepted: bool
    disposition: str
    reason: str
    subgoal_id: str
    campaign_root: str
    consumed_once: bool
    source_inspection: dict[str, Any]
    baseline: dict[str, Any]
    candidate: dict[str, Any]
    validation: dict[str, Any]
    clean_reproduction: dict[str, Any]
    application_request: dict[str, Any]
    behavioral_evaluation_request: dict[str, Any]
    reassessment: dict[str, Any]
    resource_usage: tuple[ResourceUseRecord, ...]
    meaningful_transition_timestamps: dict[str, str]
    stalled_execution: bool = False

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["resource_usage"] = [asdict(item) for item in self.resource_usage]
        return data


def execute_continuous_active_subgoal(
    controller: ContinuousRuntimeController,
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
    python_executable: str | None = None,
    local_model_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    reference_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    create_application_request: bool = False,
    allow_local_model_execution: bool = False,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    """Consume one active subgoal through local governed development work."""

    if not controller.continuous_active_subgoal:
        raise ValueError("continuous subgoal execution requires an active subgoal")
    subgoal = dict(controller.continuous_active_subgoal)
    subgoal_id = str(subgoal.get("subgoal_id") or "")
    if not subgoal_id:
        raise ValueError("active subgoal missing subgoal_id")
    root = Path(artifact_root) / "subgoal_executions" / subgoal_id
    repo = Path(repository_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    result_path = root / "execution_result.json"
    if result_path.exists():
        previous = _read_json(result_path)
        duplicate = _result_from_previous(previous, reason="duplicate_subgoal_consumption_prevented")
        return controller, duplicate

    if str(subgoal.get("execution_kind") or "") == "independent_behavioral_evaluation":
        return _execute_independent_behavioral_evaluation(
            controller,
            subgoal=subgoal,
            root=root,
            result_path=result_path,
        )
    if str(subgoal.get("execution_kind") or "") == "continuous_to_pcm_closed_loop_fixture":
        return execute_continuous_to_pcm_closed_loop_fixture(
            controller,
            artifact_root=artifact_root,
            python_executable=python_executable,
        )
    if str(subgoal.get("execution_kind") or "") == "developmental_learning":
        return _execute_developmental_learning_subgoal(
            controller,
            subgoal=subgoal,
            root=root,
            result_path=result_path,
        )

    timestamps: dict[str, str] = {"execution_started": utc_now()}
    baseline_metric = str(subgoal.get("baseline") or "")
    if _is_liveness_only_metric(baseline_metric):
        result = SubgoalExecutionResult(
            accepted=False,
            disposition="rejected_liveness_only_subgoal",
            reason="liveness-only metrics cannot satisfy runtime-improvement subgoals",
            subgoal_id=subgoal_id,
            campaign_root=str(root),
            consumed_once=True,
            source_inspection={},
            baseline={"metric": baseline_metric, "accepted": False},
            candidate={},
            validation={},
            clean_reproduction={},
            application_request={},
            behavioral_evaluation_request={},
            reassessment={},
            resource_usage=(),
            meaningful_transition_timestamps=timestamps,
            stalled_execution=True,
        )
        _write_json(result_path, result.as_dict())
        return controller, result

    # A broad weakness label and even a prefilled design mapping are not a
    # sandbox implementation contract. The only path here records and checks
    # repository-bound evidence; materializing code belongs to the separately
    # governed candidate/application lifecycle.
    return _execute_repository_bound_candidate_design(
        controller,
        subgoal=subgoal,
        root=root,
        repo=repo,
        result_path=result_path,
        local_model_adapter=local_model_adapter,
        allow_local_model_execution=allow_local_model_execution,
    )


def _execute_developmental_learning_subgoal(
    controller: ContinuousRuntimeController,
    *,
    subgoal: Mapping[str, Any],
    root: Path,
    result_path: Path,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    """Execute one non-code attempt and score it only against sealed cases."""

    state = dict(controller.continuous_learning_state or {})
    bundle = dict(state.get("retained_bundle") or {})
    if not bundle:
        raise ValueError("developmental learning subgoal requires retained resource and evaluation bundle")
    typed = LearningSubgoal(**{key: value for key, value in dict(subgoal).items() if key in LearningSubgoal.__dataclass_fields__})
    # The learner receives teaching evidence plus the public V3 case view. The
    # full evaluator package remains controller-owned for scoring below.
    learner_cases = tuple(
        {
            "case_id": str(case.get("case_id") or ""),
            "case_kind": str(case.get("case_kind") or ""),
            "task_type": str(case.get("task_type") or ""),
            "capability_dimension": str(case.get("capability_dimension") or ""),
            "learner_view": dict(case.get("learner_view") or {}),
        }
        for case in bundle.get("sealed_evaluation_cases") or ()
        if isinstance(case, Mapping)
    )
    learner_bundle = {
        "study_resources": bundle.get("study_resources") or (),
        "execution_contract_version": bundle.get("execution_contract_version"),
        "sealed_evaluation_cases": learner_cases,
    }
    attempt = execute_learning_attempt(typed, learner_bundle)
    evaluation = evaluate_learning_attempt(typed, attempt, bundle)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "learning_attempt.json", attempt.as_dict())
    _write_json(root / "developmental_evaluation.json", evaluation.as_dict())
    next_controller = consume_developmental_learning_evaluation(controller, evaluation, attempt=attempt.as_dict())
    timestamps = {"attempt_started": utc_now(), "sealed_evaluation_completed": utc_now(), "reassessment_completed": utc_now()}
    result = SubgoalExecutionResult(
        accepted=evaluation.promotion_eligible,
        disposition=evaluation.disposition,
        reason="candidate-independent sealed learning evaluation completed",
        subgoal_id=typed.subgoal_id,
        campaign_root=str(root),
        consumed_once=True,
        source_inspection={"resource_ids": typed.study_resource_ids, "provider_calls": 0, "web_calls": 0},
        baseline=dict(evaluation.baseline_metrics),
        candidate=dict(evaluation.candidate_metrics),
        validation={"control": dict(evaluation.control_metrics), "held_out": dict(evaluation.held_out_metrics), "adversarial": dict(evaluation.adversarial_metrics), "transfer": dict(evaluation.transfer_metrics)},
        clean_reproduction={"not_applicable": "non-code learning attempt uses retained local resources and sealed evaluator"},
        application_request={},
        behavioral_evaluation_request=evaluation.as_dict(),
        reassessment={"next_state": next_controller.continuous_mission_state, "next_subgoal": dict(next_controller.continuous_active_subgoal or {})},
        resource_usage=(ResourceUseRecord("retained_local_source", item, "bounded guided study", "used") for item in typed.study_resource_ids),
        meaningful_transition_timestamps=timestamps,
        stalled_execution=False,
    )
    # The record type is a tuple by contract; retain construction above as a
    # generator-free value for stable serialization and restart artifacts.
    result = replace(result, resource_usage=tuple(result.resource_usage))
    _write_json(result_path, result.as_dict())
    return next_controller, result


def compile_continuous_pcm_bridge_fixture(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile an evidence-complete, inert fixture design for the existing PCM.

    This is deliberately a fixture compiler, not a general candidate generator.
    It keeps the current gate independent of advisory-model quality while
    binding every later PCM action to controller-owned mission provenance.
    """

    subgoal_id = str(subgoal.get("subgoal_id") or "")
    weakness_id = str(subgoal.get("weakness_id") or "")
    if not subgoal_id or not weakness_id:
        raise ValueError("continuous PCM bridge fixture requires controller-owned subgoal and weakness IDs")
    mission_id = str((controller.continuous_mission_contract or {}).get("mission_id") or controller.session_id)
    main_goal_id = str((controller.continuous_main_goal or {}).get("main_goal_id") or "continuous-main-goal")
    capability_id = _capability_id_from_subgoal(subgoal) or "continuous_pcm_bridge_fixture"
    expected_symbol = "missing_guard"
    design = {
        "protocol": CONTINUOUS_PCM_BRIDGE_PROTOCOL,
        "mission_id": mission_id,
        "main_goal_id": main_goal_id,
        "subgoal_id": subgoal_id,
        "weakness_id": weakness_id,
        "capability_id": capability_id,
        "developmental_gap_id": f"{weakness_id}:behavioral_gap",
        "preexisting_behavioral_failure_id": stable_id("continuous-pcm-baseline-failure", mission_id, subgoal_id, expected_symbol),
        "first_incorrect_transition": "structural PCM pass -> capability acquisition without sealed behavioral evidence",
        "affected_implementation_path": "sample.py",
        "independent_evidence_path": "sealed_behavioral_bundle.json",
        "source_inspection_id": stable_id("continuous-pcm-source-inspection", mission_id, subgoal_id, "sample.py"),
        "allowed_paths": ("sample.py", "tests/test_pcm_generated_review.py"),
        "excluded_paths": ("DELTA-75", "reports/RC4_*", "orchestration/runtime", "tests/runtime_gsr"),
        "candidate_behavior": "provide the missing callable without changing present() behavior",
        "validation_target": "sealed callable return behavior with an unchanged control",
        "baseline_evidence_reference": "baseline_missing_guard_behavior",
        "control_requirement": "present() remains 1",
        "held_out_requirement": "missing_guard() returns True through a sealed invocation distinct from PCM symbol existence",
        "rollback_restoration_condition": "restored baseline source again lacks missing_guard while present() remains 1",
        "authority_state": "fixture_local_disposable_only",
        "grounded_design_protocol": CONTINUOUS_PCM_BRIDGE_PROTOCOL,
        "grounded_design_digest": "",
        "model_result_marker": "deterministic_fixture_no_model_authority",
        "expected_symbol": expected_symbol,
    }
    return {**design, "grounded_design_digest": _digest(design)}


def execute_continuous_to_pcm_closed_loop_fixture(
    controller: ContinuousRuntimeController,
    *,
    artifact_root: str | Path,
    python_executable: str | None = None,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    """Exercise one sealed, disposable PCM lifecycle and return it once.

    The existing PCM remains authoritative for attachment, inspection,
    diagnosis, patching, disposable materialization, and structural testing.
    The sealed bundle below is purposefully separate from PCM's generated test
    so a structural ``proposal_passed`` cannot certify a capability.
    """

    if not controller.continuous_active_subgoal:
        raise ValueError("continuous PCM bridge requires an active controller subgoal")
    subgoal = dict(controller.continuous_active_subgoal)
    design = compile_continuous_pcm_bridge_fixture(controller, subgoal)
    bridge_id = stable_id("continuous-pcm-bridge", design["mission_id"], design["subgoal_id"], design["grounded_design_digest"])
    idempotency_key = stable_id("continuous-pcm-bridge-idempotency", bridge_id, design["preexisting_behavioral_failure_id"])
    for entry in controller.continuous_pcm_bridge_ledger:
        if str(entry.get("bridge_id") or "") == bridge_id or str(entry.get("idempotency_key") or "") == idempotency_key:
            return controller, _pcm_bridge_duplicate_result(subgoal, bridge_id, str(artifact_root))

    root = Path(artifact_root) / "continuous_pcm_bridge" / bridge_id
    root.mkdir(parents=True, exist_ok=True)
    result_path = root / "execution_result.json"
    if result_path.exists():
        return _recover_or_suppress_completed_pcm_bridge_result(controller, subgoal, bridge_id, root)

    timestamps = {"bridge_started": utc_now()}
    baseline_source = "def present():\n    return 1\n"
    fixture_root = root / "baseline_fixture"
    fixture_root.mkdir(exist_ok=True)
    (fixture_root / "sample.py").write_text(baseline_source, encoding="utf-8")
    bundle = _create_sealed_pcm_behavioral_bundle(design, baseline_source)
    bundle_path = root / "sealed_behavioral_bundle.json"
    _write_json(bundle_path, bundle)
    sealed_digest = _digest(_read_json(bundle_path))
    timestamps["sealed_bundle_created_before_implementation"] = utc_now()

    cycle = gsr.make_governed_objective_cycle(
        gsr.make_development_objective("Continuous PCM closed-loop bridge fixture", sequence=1),
        sequence=1,
    )
    manifest = gsr.make_python_coding_module_manifest()
    capability = gsr.make_python_coding_capability_request(
        cycle,
        manifest,
        requested_source_scope=("sample.py",),
        request_sequence=2,
    )
    attachment_request = gsr.make_python_coding_module_attachment_request(manifest, capability, requested_attachment_sequence=3)
    attachment_authorization = gsr.make_python_coding_module_attachment_authorization(attachment_request, issued_sequence=4, expiration_sequence=90)
    attachment_eligibility = gsr.evaluate_python_coding_module_attachment_eligibility(
        cycle, manifest, capability, attachment_request, attachment_authorization, sequence=5
    )
    attachment = gsr.create_python_coding_module_inert_attachment_record(
        gsr.make_python_coding_module_attachment_state(), attachment_eligibility, sequence=6
    )
    if not attachment.accepted or attachment.attachment_record is None:
        raise RuntimeError(f"PCM attachment failed: {attachment.reason}")
    record = attachment.attachment_record

    inspection_request = gsr.make_python_source_inspection_request(record, requested_relative_paths=("sample.py",), request_sequence=7)
    inspection_authorization = gsr.make_python_source_inspection_authorization(inspection_request, issued_sequence=8, expiration_sequence=90)
    inspection = gsr.inspect_python_source_read_only(record, inspection_request, inspection_authorization, root=fixture_root, sequence=9)
    diagnosis_request = gsr.make_python_bounded_diagnosis_request(
        record,
        inspection,
        diagnosis_question="Is missing_guard missing?",
        expected_transition="missing_guard should appear",
        expected_symbol=str(design["expected_symbol"]),
        request_sequence=10,
    )
    diagnosis_authorization = gsr.make_python_bounded_diagnosis_authorization(diagnosis_request, issued_sequence=11, expiration_sequence=90)
    diagnosis = gsr.perform_python_bounded_diagnosis(record, inspection, diagnosis_request, diagnosis_authorization, sequence=12)
    test_request = gsr.make_python_focused_test_proposal_request(
        record,
        diagnosis,
        expected_behavior="missing_guard exists",
        proposed_test_target_path="tests/test_pcm_generated_review.py",
        request_sequence=13,
    )
    test_authorization = gsr.make_python_focused_test_proposal_authorization(test_request, issued_sequence=14, expiration_sequence=90)
    test_proposal = gsr.create_python_focused_test_proposal(record, diagnosis, test_request, test_authorization, sequence=15)
    handoff_request = gsr.make_python_sandbox_handoff_request(
        record,
        inspection,
        diagnosis,
        test_proposal,
        allowed_target_paths=tuple(design["allowed_paths"]),
        request_sequence=16,
    )
    handoff_authorization = gsr.make_python_sandbox_handoff_authorization(handoff_request, issued_sequence=17, expiration_sequence=90)
    handoff = gsr.create_python_sandbox_handoff_package(
        record, inspection, diagnosis, test_proposal, handoff_request, handoff_authorization, sequence=18
    )
    patch_request = gsr.make_python_candidate_patch_request(
        record,
        inspection,
        diagnosis,
        test_proposal,
        replacement_text=f"def {design['expected_symbol']}():\n    return True\n",
        expected_postcondition=f"symbol_present:{design['expected_symbol']}",
        request_sequence=19,
    )
    patch_authorization = gsr.make_python_candidate_patch_authorization(patch_request, issued_sequence=20, expiration_sequence=90)
    patch = gsr.create_python_candidate_patch_proposal(record, inspection, diagnosis, test_proposal, patch_request, patch_authorization, sequence=21)
    artifacts = (
        ("pcm_1c_read_only_source_inspection", "inspection_evidence", inspection.evidence.__dict__),
        ("pcm_1d_bounded_diagnosis", "diagnosis_evidence", diagnosis.evidence.__dict__),
        ("pcm_1e_focused_test_proposal", "test_proposal_evidence", test_proposal.evidence.__dict__),
        ("pcm_1f_sandbox_handoff", "sandbox_handoff_evidence", handoff.evidence.__dict__),
        ("pcm_2a_candidate_patch_proposal", "candidate_patch_evidence", patch.evidence.__dict__),
    )
    chain = gsr.build_pcm2_artifact_chain(
        objective_cycle_id=record.objective_cycle_id,
        module_id=record.module_id,
        module_version=record.module_version,
        artifacts=artifacts,
    )
    materialization_request = gsr.make_python_sandbox_materialization_request(patch, test_proposal, chain, request_sequence=22)
    materialization_authorization = gsr.make_python_sandbox_materialization_authorization(materialization_request, issued_sequence=23, expiration_sequence=90)
    materialization = gsr.materialize_python_candidate_in_disposable_sandbox(
        patch,
        test_proposal,
        chain,
        materialization_request,
        materialization_authorization,
        fixture_root=fixture_root,
        sandbox_parent=root / "sandboxes",
        sequence=24,
    )
    if not materialization.accepted or materialization.manifest is None:
        raise RuntimeError(f"PCM materialization failed: {materialization.reason}")
    execution_request = gsr.make_python_sandbox_execution_request(
        materialization.manifest,
        command=(python_executable or sys.executable, "-m", "pytest", materialization.manifest.test_relative_path),
        request_sequence=25,
    )
    execution_authorization = gsr.make_python_sandbox_execution_authorization(execution_request, issued_sequence=26, expiration_sequence=90)
    execution = gsr.execute_python_sandbox_focused_test_once(materialization.manifest, execution_request, execution_authorization, sequence=27)
    structural = gsr.evaluate_python_sandbox_result(materialization.manifest, patch, test_proposal, execution, chain, sequence=28)
    timestamps["pcm_structural_validation_completed"] = utc_now()

    baseline_outcome = _run_sealed_pcm_behavioral_cases(baseline_source, str(design["expected_symbol"]))
    candidate_source = (Path(materialization.manifest.workspace_root) / materialization.manifest.target_relative_path).read_text(encoding="utf-8")
    candidate_outcome = _run_sealed_pcm_behavioral_cases(candidate_source, str(design["expected_symbol"]))
    restored_outcome = _run_sealed_pcm_behavioral_cases(baseline_source, str(design["expected_symbol"]))
    bundle_unchanged = sealed_digest == _digest(_read_json(bundle_path))
    causal = (
        not baseline_outcome["target"]
        and candidate_outcome["target"]
        and not restored_outcome["target"]
        and baseline_outcome["control"]
        and candidate_outcome["control"]
        and restored_outcome["control"]
    )
    behaviorally_demonstrated = bool(
        structural.accepted
        and structural.evaluation is not None
        and structural.evaluation.classification == "proposal_passed"
        and candidate_outcome["held_out"]
        and causal
        and bundle_unchanged
    )
    behavioral = BehavioralEvaluationRecord(
        evaluation_id=stable_id("continuous-pcm-behavioral-evaluation", bridge_id, sealed_digest),
        task_family_id="continuous_pcm_closed_loop_fixture",
        capability_id=str(design["capability_id"]),
        developmental_gap_id=str(design["developmental_gap_id"]),
        baseline_attempt_id=str(design["preexisting_behavioral_failure_id"]),
        candidate_id=str((patch.evidence.patch_proposal or {}).get("patch_proposal_id") or "") if patch.evidence is not None else "",
        evaluation_protocol_version=CONTINUOUS_PCM_BRIDGE_PROTOCOL,
        task_source="sealed_fixture_preimplementation",
        training_case_ids=("pcm_generated_symbol_existence",),
        sealed_or_preexisting_case_ids=("sealed_callable_return", "sealed_restoration"),
        control_case_ids=("sealed_present_control",),
        baseline_metrics={"target": float(baseline_outcome["target"])},
        post_candidate_metrics={"target": float(candidate_outcome["target"])},
        transfer_metrics={"target": float(candidate_outcome["held_out"]), "threshold": 1.0},
        regression_metrics={"controls_stable": baseline_outcome["control"] and candidate_outcome["control"] and restored_outcome["control"]},
        evidence_independence={
            "case_source": "sealed",
            "candidate_generated_expected_outputs": False,
            "self_reported_success": False,
            "artifact_existence_only": False,
            "sealed_bundle_digest": sealed_digest,
            "bundle_unchanged": bundle_unchanged,
            "causal_restoration": causal,
        },
        disposition="behaviorally_demonstrated" if behaviorally_demonstrated else "behaviorally_failed",
        evidence_refs=(str(bundle_path), str(root / "bridge_disposition.json")),
    )
    base_record = CapabilityKnowledgeRecord(
        capability_id=str(design["capability_id"]),
        original_weakness=str(subgoal.get("measurable_objective") or design["first_incorrect_transition"]),
        evidence=(str(bundle_path), str(root)),
        first_incorrect_transition=str(design["first_incorrect_transition"]),
        strategies_attempted=("existing_pcm_disposable_patch", "sealed_behavioral_evaluation"),
        failed_approaches=("proposal_passed_is_not_behavioral_capability",),
        successful_mechanism="existing PCM patch followed by sealed independent behavioral and restoration checks",
        exact_candidate=str((patch.evidence.patch_proposal or {}).get("patch_proposal_id") or "") if patch.evidence is not None else "",
        tests_added=("pcm_generated_symbol_existence",),
        metrics_before_after={"structural_classification": structural.evaluation.classification if structural.evaluation else "missing"},
        controls=("present_returns_one", "tracked_source_unchanged"),
        adversarial_evidence=("candidate_cannot_rewrite_sealed_expected_outcomes",),
        held_out_evidence={"sealed_callable_return": candidate_outcome["held_out"]},
        reproduction_evidence=str(bundle_path),
        provider_contribution="none",
        local_repair_contribution="existing_pcm_fixture_patch",
        application_evidence="not requested; tracked source was never changed",
        regression_evidence="sealed control and restoration outcomes recorded",
        reassessment="candidate_structurally_validated",
        residual_uncertainty="fixture-only bridge proof; no autonomous task formation claimed",
        reusable_process_rules=("structural PCM success cannot acquire a capability without sealed behavioral evidence",),
        evidence_stage="candidate_structurally_validated",
        capability_acquired=False,
        eligible_for_behavioral_evaluation=True,
    )
    promoted = promote_capability_with_behavioral_evaluation(base_record, behavioral)
    bridge_entry = {
        "bridge_id": bridge_id,
        "idempotency_key": idempotency_key,
        "protocol": CONTINUOUS_PCM_BRIDGE_PROTOCOL,
        "mission_id": design["mission_id"],
        "main_goal_id": design["main_goal_id"],
        "subgoal_id": design["subgoal_id"],
        "weakness_id": design["weakness_id"],
        "capability_id": design["capability_id"],
        "grounded_design_digest": design["grounded_design_digest"],
        "sealed_evaluation_digest": sealed_digest,
        "pcm_ids": {
            "attachment": record.attachment_record_id,
            "inspection": inspection.evidence.inspection_attempt_id if inspection.evidence else "",
            "diagnosis": diagnosis.evidence.diagnosis_attempt_id if diagnosis.evidence else "",
            "test": test_proposal.evidence.test_proposal_attempt_id if test_proposal.evidence else "",
            "patch": patch.evidence.patch_attempt_id if patch.evidence else "",
            "handoff": handoff.evidence.sandbox_handoff_attempt_id if handoff.evidence else "",
            "manifest": materialization.manifest.sandbox_manifest_id,
            "structural_evaluation": structural.evaluation.evaluation_id if structural.evaluation else "",
        },
        "behavioral_evaluation_id": behavioral.evaluation_id,
        "capability_knowledge_record": promoted.as_dict(),
        "structural_disposition": structural.evaluation.classification if structural.evaluation else "invalid_evaluation",
        "behavioral_disposition": behavioral.disposition,
        "authority_state": "fixture_local_disposable_only",
        "current_stage": "behavioral_evaluation_complete",
        "restart_state": "safe_to_consume_once",
    }
    _write_json(root / "bridge_disposition.json", bridge_entry)
    timestamps["sealed_behavioral_evaluation_completed"] = utc_now()
    reassessed_controller, consumed = consume_continuous_pcm_bridge_result(controller, bridge_entry=bridge_entry, record=promoted)
    next_controller = continue_continuous_mission_after_reassessment(reassessed_controller) if consumed else reassessed_controller
    updated_entry = next(item for item in next_controller.continuous_pcm_bridge_ledger if item.get("bridge_id") == bridge_id)
    _write_json(root / "bridge_disposition.json", updated_entry)
    cleaned, cleanup_reason = gsr.cleanup_python_disposable_sandbox(materialization.manifest)
    timestamps["pcm_sandbox_cleanup_completed"] = utc_now()
    result = SubgoalExecutionResult(
        accepted=behaviorally_demonstrated,
        disposition=behavioral.disposition,
        reason="sealed behavioral evidence returned to continuous controller" if consumed else "duplicate PCM bridge result suppressed",
        subgoal_id=str(design["subgoal_id"]),
        campaign_root=str(root),
        consumed_once=consumed,
        source_inspection={"pcm_inspection_id": bridge_entry["pcm_ids"]["inspection"], "accepted": inspection.accepted},
        baseline=baseline_outcome,
        candidate={"structural_classification": bridge_entry["structural_disposition"], "behavioral_target": candidate_outcome["target"]},
        validation={"control": candidate_outcome["control"], "held_out": candidate_outcome["held_out"], "bundle_unchanged": bundle_unchanged, "causal_restoration": causal},
        clean_reproduction={"restored_baseline": restored_outcome, "cleanup_confirmed": cleaned, "cleanup_reason": cleanup_reason},
        application_request={},
        behavioral_evaluation_request={"evaluation_id": behavioral.evaluation_id, "disposition": behavioral.disposition},
        reassessment={"capability_id": promoted.capability_id, "capability_acquired": capability_is_acquired(promoted), "bridge_id": bridge_id},
        resource_usage=(ResourceUseRecord("local_tool", "existing_pcm", "disposable structural and sealed behavioral fixture", behavioral.disposition),),
        meaningful_transition_timestamps=timestamps,
        stalled_execution=False,
    )
    _write_json(result_path, result.as_dict())
    return next_controller, result


def _create_sealed_pcm_behavioral_bundle(design: Mapping[str, Any], baseline_source: str) -> dict[str, Any]:
    bundle = {
        "protocol": CONTINUOUS_PCM_BRIDGE_PROTOCOL,
        "task_id": stable_id("continuous-pcm-sealed-task", design["mission_id"], design["subgoal_id"]),
        "baseline_source_digest": _digest(baseline_source),
        "focused_development_case": {"case_id": "pcm_generated_symbol_existence", "expected": "symbol exists after patch"},
        "control_case": {"case_id": "sealed_present_control", "predicate": "present() == 1", "expected": True},
        "held_out_case": {"case_id": "sealed_callable_return", "predicate": "missing_guard() is True", "expected": True},
        "restoration_case": {"case_id": "sealed_restoration", "predicate": "baseline lacks missing_guard", "expected": True},
        "expected_outcomes": {"baseline_target": False, "candidate_target": True, "control": True, "held_out": True},
        "regression_scope": ("present",),
        "created_before_implementation": True,
    }
    return {**bundle, "bundle_digest": _digest(bundle)}


def execute_repository_contract_exact_replacement_fixture(
    controller: ContinuousRuntimeController,
    *,
    artifact_root: str | Path,
    python_executable: str | None = None,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    """Bridge a sealed RepositoryBehaviorContract into PCM exact replacement.

    This is an integration proof for the existing controller, contract, PCM
    proposal, sandbox materialization, and independent behavioral evaluation
    path. It deliberately uses a disposable fixture so it does not claim that a
    naturally discovered repository defect has been repaired.
    """

    if not controller.continuous_active_subgoal:
        raise ValueError("repository contract bridge requires an active controller subgoal")
    if not controller.continuous_behavioral_failure_records:
        raise ValueError("repository contract bridge requires a sealed BehavioralFailureRecord")
    subgoal = dict(controller.continuous_active_subgoal)
    root = Path(artifact_root) / "repository_contract_exact_replacement" / str(subgoal.get("subgoal_id") or "subgoal")
    root.mkdir(parents=True, exist_ok=True)
    result_path = root / "execution_result.json"
    if result_path.exists():
        previous = _read_json(result_path)
        return controller, _result_from_previous(previous, reason="duplicate_exact_replacement_bridge_prevented")

    baseline_source = "def classify_score(score):\n    if score >= 0:\n        return 'pass'\n    return 'fail'\n"
    replacement_source = "def classify_score(score):\n    if score >= 70:\n        return 'pass'\n    return 'fail'\n"
    fixture_root = root / "fixture"
    fixture_root.mkdir(exist_ok=True)
    source_path = fixture_root / "score_gate.py"
    source_path.write_text(baseline_source, encoding="utf-8", newline="\n")
    evidence_payload = {
        "protocol": "sealed_score_gate_behavior_v1",
        "expected": {"classify_score(-1)": "fail", "classify_score(69)": "fail", "classify_score(70)": "pass"},
        "created_before_candidate": True,
        "candidate_generated_expected_outputs": False,
    }
    evidence_path = root / "sealed_score_gate_behavior.json"
    _write_json(evidence_path, evidence_payload)
    source_inspection = {
        "inspection_id": stable_id("repository-contract-exact-replacement-inspection", subgoal.get("subgoal_id"), _digest(baseline_source)),
        "files": (
            {
                "path": "score_gate.py",
                "byte_count": len(baseline_source.encode("utf-8")),
                "sha256": hashlib.sha256(baseline_source.encode("utf-8")).hexdigest(),
                "symbols": ("classify_score",),
            },
            {
                "path": "sealed_score_gate_behavior.json",
                "byte_count": evidence_path.stat().st_size,
                "sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                "symbols": (),
            },
        ),
        "file_count": 2,
        "meaningful": True,
    }
    contract = compile_repository_behavior_contract(
        controller,
        {
            **subgoal,
            "rollback_condition": "restore exact classify_score preimage and rerun sealed score-gate behavior",
            "controls": ("negative_score_still_fails", "threshold_score_passes"),
            "held_out_policy": "score 69 remains sealed until candidate evaluation",
        },
        source_inspection,
        advisory_result={
            "model_id": "deterministic_fixture_no_model_authority",
            "executed": False,
            "provider_calls_performed": False,
            "answer": {
                "failure_mechanism": "exact_behavioral_logic_replacement",
                "candidate_behavior": "replace the inspected classify_score threshold condition only",
                "expected_observable_change": "classify_score(69) changes from pass to fail while controls remain stable",
            },
        },
    )
    _write_json(root / "repository_behavior_contract.json", contract.as_dict())
    if contract.local_implementation_eligibility != "locally_implementable_by_existing_pcm":
        result = SubgoalExecutionResult(
            accepted=False,
            disposition=contract.local_implementation_eligibility,
            reason="repository behavior contract did not authorize exact replacement bridge",
            subgoal_id=str(subgoal.get("subgoal_id") or ""),
            campaign_root=str(root),
            consumed_once=True,
            source_inspection=source_inspection,
            baseline={},
            candidate={},
            validation={},
            clean_reproduction={},
            application_request={},
            behavioral_evaluation_request={},
            reassessment={"contract_id": contract.contract_id, "contract_disposition": contract.local_implementation_eligibility},
            resource_usage=(),
            meaningful_transition_timestamps={"bridge_completed": utc_now()},
            stalled_execution=False,
        )
        _write_json(result_path, result.as_dict())
        return controller, result

    cycle = gsr.make_governed_objective_cycle(
        gsr.make_development_objective("Repository contract exact replacement fixture", sequence=1),
        sequence=1,
    )
    manifest = gsr.make_python_coding_module_manifest()
    capability = gsr.make_python_coding_capability_request(cycle, manifest, requested_source_scope=("score_gate.py",), request_sequence=2)
    attachment_request = gsr.make_python_coding_module_attachment_request(manifest, capability, requested_attachment_sequence=3)
    attachment_authorization = gsr.make_python_coding_module_attachment_authorization(attachment_request, issued_sequence=4, expiration_sequence=90)
    attachment_eligibility = gsr.evaluate_python_coding_module_attachment_eligibility(cycle, manifest, capability, attachment_request, attachment_authorization, sequence=5)
    attachment = gsr.create_python_coding_module_inert_attachment_record(gsr.make_python_coding_module_attachment_state(), attachment_eligibility, sequence=6)
    if not attachment.accepted or attachment.attachment_record is None:
        raise RuntimeError(f"PCM attachment failed: {attachment.reason}")
    record = attachment.attachment_record
    inspection_request = gsr.make_python_source_inspection_request(record, requested_relative_paths=("score_gate.py",), request_sequence=7)
    inspection_authorization = gsr.make_python_source_inspection_authorization(inspection_request, issued_sequence=8, expiration_sequence=90)
    inspection = gsr.inspect_python_source_read_only(record, inspection_request, inspection_authorization, root=fixture_root, sequence=9)
    diagnosis_request = gsr.make_python_bounded_diagnosis_request(
        record,
        inspection,
        diagnosis_question="Does classify_score require exact behavioral logic replacement?",
        expected_transition=contract.expected_behavior,
        diagnosis_category="exact_behavioral_logic_replacement",
        expected_symbol="classify_score",
        request_sequence=10,
    )
    diagnosis_authorization = gsr.make_python_bounded_diagnosis_authorization(diagnosis_request, issued_sequence=11, expiration_sequence=90)
    diagnosis = gsr.perform_python_bounded_diagnosis(record, inspection, diagnosis_request, diagnosis_authorization, sequence=12)
    test_request = gsr.make_python_focused_test_proposal_request(
        record,
        diagnosis,
        expected_behavior="classify_score remains importable for independent sealed behavior evaluation",
        proposed_test_target_path="tests/test_pcm_generated_review.py",
        request_sequence=13,
    )
    test_authorization = gsr.make_python_focused_test_proposal_authorization(test_request, issued_sequence=14, expiration_sequence=90)
    test_proposal = gsr.create_python_focused_test_proposal(record, diagnosis, test_request, test_authorization, sequence=15)
    handoff_request = gsr.make_python_sandbox_handoff_request(
        record,
        inspection,
        diagnosis,
        test_proposal,
        allowed_target_paths=("score_gate.py", "tests/test_pcm_generated_review.py"),
        request_sequence=16,
    )
    handoff_authorization = gsr.make_python_sandbox_handoff_authorization(handoff_request, issued_sequence=17, expiration_sequence=90)
    handoff = gsr.create_python_sandbox_handoff_package(record, inspection, diagnosis, test_proposal, handoff_request, handoff_authorization, sequence=18)
    patch_request = gsr.make_python_candidate_patch_request(
        record,
        inspection,
        diagnosis,
        test_proposal,
        operation="exact_replace_text",
        expected_old_text=baseline_source,
        replacement_text=replacement_source,
        expected_postcondition="symbol_present:classify_score",
        request_sequence=19,
    )
    patch_authorization = gsr.make_python_candidate_patch_authorization(patch_request, issued_sequence=20, expiration_sequence=90)
    patch = gsr.create_python_candidate_patch_proposal(record, inspection, diagnosis, test_proposal, patch_request, patch_authorization, sequence=21)
    artifacts = (
        ("pcm_1c_read_only_source_inspection", "inspection_evidence", inspection.evidence.__dict__),
        ("pcm_1d_bounded_diagnosis", "diagnosis_evidence", diagnosis.evidence.__dict__),
        ("pcm_1e_focused_test_proposal", "test_proposal_evidence", test_proposal.evidence.__dict__),
        ("pcm_1f_sandbox_handoff", "sandbox_handoff_evidence", handoff.evidence.__dict__),
        ("pcm_2a_candidate_patch_proposal", "candidate_patch_evidence", patch.evidence.__dict__),
    )
    chain = gsr.build_pcm2_artifact_chain(
        objective_cycle_id=record.objective_cycle_id,
        module_id=record.module_id,
        module_version=record.module_version,
        artifacts=artifacts,
    )
    materialization_request = gsr.make_python_sandbox_materialization_request(patch, test_proposal, chain, request_sequence=22)
    materialization_authorization = gsr.make_python_sandbox_materialization_authorization(materialization_request, issued_sequence=23, expiration_sequence=90)
    materialization = gsr.materialize_python_candidate_in_disposable_sandbox(
        patch,
        test_proposal,
        chain,
        materialization_request,
        materialization_authorization,
        fixture_root=fixture_root,
        sandbox_parent=root / "sandboxes",
        sequence=24,
    )
    if not materialization.accepted or materialization.manifest is None:
        raise RuntimeError(f"PCM materialization failed: {materialization.reason}")
    execution_request = gsr.make_python_sandbox_execution_request(
        materialization.manifest,
        command=(python_executable or sys.executable, "-m", "pytest", materialization.manifest.test_relative_path),
        request_sequence=25,
    )
    execution_authorization = gsr.make_python_sandbox_execution_authorization(execution_request, issued_sequence=26, expiration_sequence=90)
    execution = gsr.execute_python_sandbox_focused_test_once(materialization.manifest, execution_request, execution_authorization, sequence=27)
    structural = gsr.evaluate_python_sandbox_result(materialization.manifest, patch, test_proposal, execution, chain, sequence=28)
    candidate_source = (Path(materialization.manifest.workspace_root) / materialization.manifest.target_relative_path).read_text(encoding="utf-8")
    baseline_outcome = _run_score_gate_behavioral_cases(baseline_source)
    candidate_outcome = _run_score_gate_behavioral_cases(candidate_source)
    restored_outcome = _run_score_gate_behavioral_cases(baseline_source)
    behaviorally_demonstrated = bool(
        structural.accepted
        and structural.evaluation is not None
        and structural.evaluation.classification == "proposal_passed"
        and not baseline_outcome["target"]
        and candidate_outcome["target"]
        and not restored_outcome["target"]
        and baseline_outcome["control"]
        and candidate_outcome["control"]
        and restored_outcome["control"]
    )
    behavioral = BehavioralEvaluationRecord(
        evaluation_id=stable_id("repository-contract-exact-replacement-evaluation", contract.contract_id, patch.evidence.patch_attempt_id if patch.evidence else ""),
        task_family_id="repository_contract_exact_replacement_fixture",
        capability_id=contract.capability_id,
        developmental_gap_id=str(subgoal.get("weakness_id") or contract.capability_id),
        baseline_attempt_id=contract.failure_id,
        candidate_id=str((patch.evidence.patch_proposal or {}).get("patch_proposal_id") or "") if patch.evidence is not None else "",
        evaluation_protocol_version="repository_contract_exact_replacement_v1",
        task_source="sealed_integration_fixture",
        training_case_ids=("score_gate_importability",),
        sealed_or_preexisting_case_ids=("score_69_threshold",),
        control_case_ids=("negative_score_fails", "threshold_score_passes"),
        baseline_metrics={"target": float(baseline_outcome["target"])},
        post_candidate_metrics={"target": float(candidate_outcome["target"])},
        transfer_metrics={"target": float(candidate_outcome["held_out"]), "threshold": 1.0},
        regression_metrics={"controls_stable": baseline_outcome["control"] and candidate_outcome["control"] and restored_outcome["control"]},
        evidence_independence={
            "case_source": "sealed",
            "candidate_generated_expected_outputs": False,
            "self_reported_success": False,
            "artifact_existence_only": False,
            "tracked_source_mutated": False,
        },
        disposition="behaviorally_demonstrated" if behaviorally_demonstrated else "behaviorally_failed",
        evidence_refs=(str(evidence_path), str(root / "exact_replacement_bridge_disposition.json")),
    )
    base_record = CapabilityKnowledgeRecord(
        capability_id=contract.capability_id,
        original_weakness=contract.expected_behavior,
        evidence=(str(evidence_path), str(root / "repository_behavior_contract.json")),
        first_incorrect_transition=contract.first_incorrect_transition,
        strategies_attempted=("repository_behavior_contract", "pcm_exact_replace_text", "sealed_score_gate_evaluation"),
        failed_approaches=(),
        successful_mechanism="RepositoryBehaviorContract compiled into PCM exact_replace_text and passed sealed independent behavior",
        exact_candidate=str((patch.evidence.patch_proposal or {}).get("patch_proposal_id") or "") if patch.evidence is not None else "",
        tests_added=("score_gate_importability",),
        metrics_before_after={"baseline": baseline_outcome, "candidate": candidate_outcome, "restored": restored_outcome},
        controls=("tracked_source_unchanged", "negative_score_fails", "threshold_score_passes"),
        adversarial_evidence=("candidate could not mutate sealed expected behavior",),
        held_out_evidence={"score_69_threshold": candidate_outcome["held_out"]},
        reproduction_evidence=str(evidence_path),
        provider_contribution="none",
        local_repair_contribution="pcm_exact_replace_text",
        application_evidence="not applied; disposable sandbox only",
        regression_evidence="sealed score-gate control and restoration outcomes",
        reassessment="behaviorally_demonstrated" if behaviorally_demonstrated else "behaviorally_failed",
        residual_uncertainty="disposable integration fixture; autonomous discovery of a natural compatible defect remains separate",
        reusable_process_rules=("exact replacement requires deterministic preimage and sealed independent behavior",),
        evidence_stage="behaviorally_demonstrated" if behaviorally_demonstrated else "behaviorally_failed",
        capability_acquired=behaviorally_demonstrated,
        eligible_for_behavioral_evaluation=False,
        behavioral_evaluation=behavioral,
        behavioral_evaluation_ref=behavioral.evaluation_id,
    )
    promoted = promote_capability_with_behavioral_evaluation(base_record, behavioral)
    next_controller = continue_continuous_mission_after_reassessment(consume_continuous_capability_reassessment(controller, promoted))
    cleaned, cleanup_reason = gsr.cleanup_python_disposable_sandbox(materialization.manifest)
    disposition = {
        "contract": contract.as_dict(),
        "patch_proposal": patch.evidence.patch_proposal if patch.evidence else {},
        "structural": structural.evaluation.__dict__ if structural.evaluation else {},
        "behavioral": behavioral.as_dict(),
        "baseline": baseline_outcome,
        "candidate": candidate_outcome,
        "restored": restored_outcome,
        "cleanup": {"cleaned": cleaned, "reason": cleanup_reason},
        "tracked_source_mutated": False,
    }
    _write_json(root / "exact_replacement_bridge_disposition.json", disposition)
    result = SubgoalExecutionResult(
        accepted=behaviorally_demonstrated,
        disposition=behavioral.disposition,
        reason="repository contract exact replacement evaluated in disposable sandbox",
        subgoal_id=str(subgoal.get("subgoal_id") or ""),
        campaign_root=str(root),
        consumed_once=True,
        source_inspection=source_inspection,
        baseline=baseline_outcome,
        candidate={"structural_classification": structural.evaluation.classification if structural.evaluation else "", "behavioral": candidate_outcome},
        validation={"behaviorally_demonstrated": behaviorally_demonstrated, "controls_stable": behavioral.regression_metrics["controls_stable"]},
        clean_reproduction={"restored_baseline": restored_outcome, "cleanup_confirmed": cleaned, "cleanup_reason": cleanup_reason},
        application_request={},
        behavioral_evaluation_request=behavioral.as_dict(),
        reassessment={"capability_id": promoted.capability_id, "reassessment": promoted.reassessment},
        resource_usage=(ResourceUseRecord("local_tool", "existing_pcm_exact_replace_text", "contract-to-PCM integration fixture", behavioral.disposition),),
        meaningful_transition_timestamps={"bridge_completed": utc_now()},
        stalled_execution=False,
    )
    _write_json(result_path, result.as_dict())
    return next_controller, result


def _run_sealed_pcm_behavioral_cases(source: str, expected_symbol: str) -> dict[str, bool]:
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "sealed_fixture_sample.py", "exec"), {"__builtins__": {}}, namespace)
        candidate = namespace.get(expected_symbol)
        target = callable(candidate) and candidate() is True
        control = callable(namespace.get("present")) and namespace["present"]() == 1
    except Exception:  # noqa: BLE001 - failed candidate behavior is a truthful evaluation result.
        target = False
        control = False
    return {"target": target, "control": control, "held_out": target and control}


def _run_score_gate_behavioral_cases(source: str) -> dict[str, bool]:
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "score_gate.py", "exec"), {"__builtins__": {}}, namespace)
        classify = namespace.get("classify_score")
        target = callable(classify) and classify(69) == "fail"
        controls = callable(classify) and classify(-1) == "fail" and classify(70) == "pass"
    except Exception:  # noqa: BLE001 - failed candidate behavior is a truthful evaluation result.
        target = False
        controls = False
    return {"target": target, "control": controls, "held_out": target and controls}


def _recover_or_suppress_completed_pcm_bridge_result(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    bridge_id: str,
    root: Path,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    disposition_path = root / "bridge_disposition.json"
    if not disposition_path.exists():
        return controller, _pcm_bridge_duplicate_result(subgoal, bridge_id, str(root))
    bridge_entry = _read_json(disposition_path)
    if str(bridge_entry.get("bridge_id") or "") != bridge_id:
        return controller, _pcm_bridge_duplicate_result(subgoal, bridge_id, str(root))
    if any(str(item.get("bridge_id") or "") == bridge_id for item in controller.continuous_pcm_bridge_ledger):
        return controller, _pcm_bridge_duplicate_result(subgoal, bridge_id, str(root))
    record_payload = bridge_entry.get("capability_knowledge_record")
    if not isinstance(record_payload, Mapping):
        return controller, _pcm_bridge_duplicate_result(subgoal, bridge_id, str(root))
    recovered, consumed = consume_continuous_pcm_bridge_result(
        controller,
        bridge_entry=bridge_entry,
        record=CapabilityKnowledgeRecord(**dict(record_payload)),
    )
    next_controller = continue_continuous_mission_after_reassessment(recovered) if consumed else recovered
    previous = _read_json(root / "execution_result.json")
    return next_controller, SubgoalExecutionResult(
        accepted=bool(previous.get("accepted")),
        disposition=str(previous.get("disposition") or "completed_pcm_bridge_result_recovered"),
        reason="completed PCM bridge result recovered from durable artifact",
        subgoal_id=str(previous.get("subgoal_id") or subgoal.get("subgoal_id") or ""),
        campaign_root=str(root),
        consumed_once=consumed,
        source_inspection=dict(previous.get("source_inspection") or {}),
        baseline=dict(previous.get("baseline") or {}),
        candidate=dict(previous.get("candidate") or {}),
        validation=dict(previous.get("validation") or {}),
        clean_reproduction=dict(previous.get("clean_reproduction") or {}),
        application_request=dict(previous.get("application_request") or {}),
        behavioral_evaluation_request=dict(previous.get("behavioral_evaluation_request") or {}),
        reassessment=dict(previous.get("reassessment") or {}),
        resource_usage=(),
        meaningful_transition_timestamps=dict(previous.get("meaningful_transition_timestamps") or {}),
    )


def _pcm_bridge_duplicate_result(subgoal: Mapping[str, Any], bridge_id: str, root: str) -> SubgoalExecutionResult:
    return SubgoalExecutionResult(
        accepted=False,
        disposition="duplicate_pcm_bridge_result_prevented",
        reason="bridge idempotency key already consumed",
        subgoal_id=str(subgoal.get("subgoal_id") or ""),
        campaign_root=root,
        consumed_once=False,
        source_inspection={},
        baseline={},
        candidate={},
        validation={},
        clean_reproduction={},
        application_request={},
        behavioral_evaluation_request={"bridge_id": bridge_id},
        reassessment={},
        resource_usage=(),
        meaningful_transition_timestamps={},
        stalled_execution=False,
    )


def compile_repository_behavior_contract(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    source_inspection: Mapping[str, Any],
    *,
    advisory_result: Mapping[str, Any] | None = None,
    existing_contracts: tuple[RepositoryBehaviorContract | Mapping[str, Any], ...] = (),
) -> RepositoryBehaviorContract:
    failure = _failure_record_for_subgoal(controller, subgoal)
    files = tuple(dict(item) for item in (source_inspection.get("files") or ()))
    inspected = {str(item.get("path") or ""): item for item in files}
    errors: list[str] = []
    if _contains_forbidden_contract_payload(advisory_result or {}):
        errors.append("forbidden_candidate_or_patch_content")

    affected_path = _select_inspected_path(failure.suspected_owner_paths, inspected, prefer_test=False)
    if not affected_path and not failure.suspected_owner_paths:
        affected_path = _first_inspected_path(files, prefer_test=False)
    evidence_path = _select_inspected_path(failure.independent_evidence_paths, inspected, prefer_test=True)
    if not evidence_path and not failure.independent_evidence_paths:
        evidence_path = _first_inspected_path(files, prefer_test=True)
    if not affected_path:
        errors.append("missing_affected_path")
    if affected_path and affected_path not in inspected:
        errors.append("uninspected_affected_path")
    if not evidence_path:
        errors.append("missing_independent_evidence_path")
    if evidence_path and evidence_path not in inspected:
        errors.append("uninspected_independent_evidence_path")
    if affected_path and evidence_path and affected_path == evidence_path:
        errors.append("implementation_and_evidence_path_not_independent")

    advisory = _parse_advisory_contract_fields(advisory_result or {})
    deterministic = _deterministic_contract_hypothesis(failure, subgoal, inspected.get(affected_path or "", {}))
    failure_mechanism = _clean_contract_text(advisory.get("failure_mechanism") or deterministic.get("failure_mechanism"))
    candidate_behavior = _clean_contract_text(advisory.get("candidate_behavior") or deterministic.get("candidate_behavior"))
    observable_change = _clean_contract_text(advisory.get("expected_observable_change") or advisory.get("validation_target") or deterministic.get("expected_observable_change"))
    if not failure.observed_behavior or not failure.expected_behavior:
        errors.append("missing_current_or_expected_behavior")
    if not failure.first_incorrect_transition:
        errors.append("missing_first_incorrect_transition")
    if not failure_mechanism:
        errors.append("missing_failure_mechanism")
    if not candidate_behavior:
        errors.append("missing_candidate_behavior")
    if not observable_change:
        errors.append("missing_expected_observable_change")

    independent_predicate = _independent_validation_predicate(failure, evidence_path)
    affected_digest = str((inspected.get(affected_path or "", {}) or {}).get("sha256") or "")
    evidence_digest = str((inspected.get(evidence_path or "", {}) or {}).get("sha256") or "")
    authority = failure.authority_class
    ambiguity = failure.ambiguity_status
    disposition = _repository_contract_disposition(
        errors=tuple(errors),
        failure=failure,
        failure_mechanism=failure_mechanism,
        affected_path=affected_path,
        evidence_path=evidence_path,
    )
    main_goal_id = str((controller.continuous_main_goal or {}).get("main_goal_id") or "continuous-main-goal")
    mission_id = str((controller.continuous_mission_contract or {}).get("mission_id") or controller.session_id)
    base_payload = {
        "failure_id": failure.failure_id,
        "semantic_failure_key": failure.semantic_failure_key,
        "mission_id": mission_id,
        "main_goal_id": main_goal_id,
        "subgoal_id": str(subgoal.get("subgoal_id") or ""),
        "weakness_id": str(subgoal.get("weakness_id") or ""),
        "capability_id": failure.affected_capability_id or _capability_id_from_subgoal(subgoal),
        "affected_path": affected_path,
        "affected_symbol_or_transition": _affected_symbol_or_transition(failure, inspected.get(affected_path or "", {})),
        "inspected_path_digest": affected_digest,
        "source_inspection_id": str(source_inspection.get("inspection_id") or ""),
        "current_behavior": failure.observed_behavior,
        "expected_behavior": failure.expected_behavior,
        "expected_behavior_identity": failure.expected_behavior_identity,
        "first_incorrect_transition": failure.first_incorrect_transition,
        "failure_mechanism": failure_mechanism,
        "candidate_behavior": candidate_behavior,
        "expected_observable_change": observable_change,
        "independent_evidence_path": evidence_path,
        "independent_evidence_digest": evidence_digest,
        "independent_validation_predicate": independent_predicate,
        "baseline_reproduction_reference": failure.baseline_reproduction,
        "control_requirements": tuple(str(item) for item in (subgoal.get("controls") or ())),
        "held_out_requirements": (str(subgoal.get("held_out_policy") or ""),),
        "restoration_condition": str(subgoal.get("rollback_condition") or "restore prior state and rerun independent predicate"),
        "allowed_paths": tuple(str(item) for item in failure.allowed_scope),
        "excluded_paths": tuple(str(item) for item in failure.excluded_scope),
        "local_implementation_eligibility": disposition,
        "authority_class": authority,
        "ambiguity_status": ambiguity,
        "failure_evidence_digest": failure.sealed_failure_bundle_digest,
        "contract_protocol": REPOSITORY_BEHAVIOR_CONTRACT_PROTOCOL,
        "contract_version": REPOSITORY_BEHAVIOR_CONTRACT_VERSION,
        "advisory_model_digest": _digest(_model_result_for_artifact(advisory_result or {})) if advisory_result else "",
        "missing_fields": tuple(error for error in errors if error.startswith("missing_")),
        "validation_errors": tuple(errors),
    }
    contract_digest = _digest(base_payload)
    duplicate = _find_duplicate_contract(existing_contracts, contract_digest)
    version_parent = _find_version_parent(existing_contracts, failure.semantic_failure_key, contract_digest)
    return RepositoryBehaviorContract(
        **base_payload,
        contract_id=duplicate.contract_id if duplicate else stable_id("repository-behavior-contract", failure.failure_id, subgoal.get("subgoal_id"), source_inspection.get("inspection_id"), affected_path, evidence_path),
        contract_digest=contract_digest,
        duplicate_of=duplicate.contract_id if duplicate else "",
        version_of=version_parent.contract_id if version_parent and not duplicate else "",
    )


def _failure_record_for_subgoal(controller: ContinuousRuntimeController, subgoal: Mapping[str, Any]) -> BehavioralFailureRecord:
    records = [BehavioralFailureRecord(**dict(item)) for item in controller.continuous_behavioral_failure_records]
    if not records:
        raise ValueError("repository behavior contract requires a sealed BehavioralFailureRecord")
    weakness_id = str(subgoal.get("weakness_id") or "")
    failure_id = ""
    for item in controller.continuous_mission_frontier:
        if str(item.get("weakness_id") or "") != weakness_id:
            continue
        for evidence_ref in item.get("source_evidence") or ():
            parts = str(evidence_ref).split(":")
            if len(parts) >= 2 and parts[0] == "behavioral_failure":
                failure_id = parts[1]
                break
    if failure_id:
        for record in records:
            if record.failure_id == failure_id:
                return record
    if len(records) == 1:
        return records[0]
    raise ValueError("active subgoal cannot be bound to exactly one behavioral failure")


def _select_inspected_path(candidates: tuple[str, ...], inspected: Mapping[str, Mapping[str, Any]], *, prefer_test: bool) -> str:
    normalized = {path.replace("\\", "/"): path for path in inspected}
    for candidate in candidates:
        key = str(candidate).replace("\\", "/")
        if key in normalized and (_is_test_path(key) if prefer_test else not _is_test_path(key)):
            return normalized[key]
    for candidate in candidates:
        key = str(candidate).replace("\\", "/")
        if key in normalized:
            return normalized[key]
    return ""


def _first_inspected_path(files: tuple[Mapping[str, Any], ...], *, prefer_test: bool) -> str:
    for item in files:
        path = str(item.get("path") or "")
        if path and (_is_test_path(path) if prefer_test else not _is_test_path(path)):
            return path
    return ""


def _is_test_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.startswith("tests/") or "/test_" in normalized or normalized.endswith("_test.py")


def _parse_advisory_contract_fields(advisory_result: Mapping[str, Any]) -> dict[str, str]:
    payload = advisory_result.get("answer") if "answer" in advisory_result else advisory_result
    parsed: Mapping[str, Any] = {}
    if isinstance(payload, Mapping):
        parsed = payload
    elif isinstance(payload, str) and payload.strip().startswith("{") and payload.strip().endswith("}"):
        try:
            parsed = json.loads(payload)
        except (TypeError, ValueError):
            parsed = {}
    return {
        "failure_mechanism": _clean_contract_text(parsed.get("failure_mechanism")),
        "candidate_behavior": _clean_contract_text(parsed.get("candidate_behavior")),
        "expected_observable_change": _clean_contract_text(parsed.get("expected_observable_change")),
        "validation_target": _clean_contract_text(parsed.get("validation_target")),
    }


def _deterministic_contract_hypothesis(
    failure: BehavioralFailureRecord,
    subgoal: Mapping[str, Any],
    inspected_path: Mapping[str, Any],
) -> dict[str, str]:
    comparison = str(failure.expected_vs_observed_result or "").lower()
    expected_identity = str(failure.expected_behavior_identity or "").lower()
    symbols = tuple(str(item) for item in (inspected_path.get("symbols") or ()))
    objective = str(subgoal.get("measurable_objective") or "")
    if "expected_symbol_missing" in comparison or "missing_symbol" in comparison:
        expected_symbol = _symbol_from_expected_identity(expected_identity, objective)
        return {
            "failure_mechanism": "expected_symbol_missing",
            "candidate_behavior": f"provide missing observable symbol {expected_symbol} without changing recorded controls",
            "expected_observable_change": f"{expected_symbol} satisfies {failure.expected_behavior_identity}",
        }
    if "missing_queued_work" in comparison or "missing_executor_consumption" in comparison:
        return {
            "failure_mechanism": "controller_transition_not_consumed_by_worker",
            "candidate_behavior": "preserve active subgoal identity until one bounded worker consumption records a result",
            "expected_observable_change": failure.expected_behavior,
        }
    if symbols and failure.affected_capability_id in " ".join(symbols):
        return {
            "failure_mechanism": "inspected_symbol_behavior_mismatch",
            "candidate_behavior": "adjust the inspected behavior surface to satisfy the preexisting predicate while preserving controls",
            "expected_observable_change": failure.expected_behavior,
        }
    return {}


def _symbol_from_expected_identity(expected_identity: str, objective: str) -> str:
    text = f"{expected_identity} {objective}"
    match = re.search(r"\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b", text)
    return match.group(1) if match else "expected_symbol"


def _independent_validation_predicate(failure: BehavioralFailureRecord, evidence_path: str) -> str:
    if not evidence_path:
        return ""
    return f"{failure.expected_behavior_identity} must pass via {evidence_path} before implementation can be considered behaviorally valid"


def _affected_symbol_or_transition(failure: BehavioralFailureRecord, inspected_path: Mapping[str, Any]) -> str:
    symbols = tuple(str(item) for item in (inspected_path.get("symbols") or ()))
    if symbols:
        return symbols[0]
    return failure.first_incorrect_transition


def _repository_contract_disposition(
    *,
    errors: tuple[str, ...],
    failure: BehavioralFailureRecord,
    failure_mechanism: str,
    affected_path: str,
    evidence_path: str,
) -> str:
    if "forbidden_candidate_or_patch_content" in errors:
        return "invalid_scope"
    if failure.authority_class in {"operator_authority_required", "protected_scope"}:
        return "blocked_by_authority"
    if failure.authority_class == "resource_blocked":
        return "blocked_by_resource"
    if failure.authority_class == "accepted_boundary":
        return "accepted_boundary"
    if any(error in errors for error in ("missing_affected_path", "uninspected_affected_path")):
        return "missing_repository_evidence"
    if any(error in errors for error in ("missing_independent_evidence_path", "uninspected_independent_evidence_path", "implementation_and_evidence_path_not_independent")):
        return "missing_independent_behavior_contract"
    if any(error in errors for error in ("missing_failure_mechanism", "missing_candidate_behavior", "missing_expected_observable_change")):
        return "unresolved_failure_mechanism"
    if failure.ambiguity_status in {"unresolved_material_ambiguity", "missing_expected_behavior", "missing_owner_scope", "conflicting_evidence"}:
        return "unresolved_failure_mechanism"
    if failure_mechanism in PCM_SUPPORTED_REPAIR_SHAPES:
        return "locally_implementable_by_existing_pcm"
    return "locally_implementable_but_pcm_operation_unsupported"


def _find_duplicate_contract(
    contracts: tuple[RepositoryBehaviorContract | Mapping[str, Any], ...],
    contract_digest: str,
) -> RepositoryBehaviorContract | None:
    for item in contracts:
        contract = item if isinstance(item, RepositoryBehaviorContract) else RepositoryBehaviorContract(**dict(item))
        if contract.contract_digest == contract_digest:
            return contract
    return None


def _find_version_parent(
    contracts: tuple[RepositoryBehaviorContract | Mapping[str, Any], ...],
    semantic_failure_key: str,
    contract_digest: str,
) -> RepositoryBehaviorContract | None:
    for item in contracts:
        contract = item if isinstance(item, RepositoryBehaviorContract) else RepositoryBehaviorContract(**dict(item))
        if contract.semantic_failure_key == semantic_failure_key and contract.contract_digest != contract_digest:
            return contract
    return None


def _contains_forbidden_contract_payload(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_CONTRACT_KEYS:
                return True
            if _contains_forbidden_contract_payload(item):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_contains_forbidden_contract_payload(item) for item in value)
    return False


def _clean_contract_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _is_liveness_only_metric(metric: str) -> bool:
    lowered = metric.lower()
    return any(item in lowered for item in LIVENESS_ONLY_METRICS)


def _execute_repository_bound_candidate_design(
    controller: ContinuousRuntimeController,
    *,
    subgoal: Mapping[str, Any],
    root: Path,
    repo: Path,
    result_path: Path,
    local_model_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    allow_local_model_execution: bool,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    """Obtain one advisory design without fabricating an implementation.

    The former execution path created the same success-reporting Python file for
    every weakness. A proposed implementation now has to identify an inspected
    repository path and an independently checkable behavior before this runtime
    may queue sandbox code. Advisory model text is evidence only.
    """

    timestamps = {"execution_started": utc_now()}
    source_inspection = _inspect_sources(repo, subgoal)
    timestamps["source_inspection_completed"] = utc_now()
    if not controller.continuous_behavioral_failure_records:
        return _execute_legacy_repository_bound_design_block(
            controller,
            subgoal=subgoal,
            root=root,
            repo=repo,
            result_path=result_path,
            source_inspection=source_inspection,
            timestamps=timestamps,
            local_model_adapter=local_model_adapter,
            allow_local_model_execution=allow_local_model_execution,
        )
    model_result: dict[str, Any] = {
        "model_id": "not_requested",
        "result": "advisory_model_not_required_for_deterministic_contract",
        "executed": False,
        "answer": "",
        "provider_calls_performed": False,
    }
    contract = compile_repository_behavior_contract(controller, subgoal, source_inspection)
    if contract.local_implementation_eligibility == "unresolved_failure_mechanism" and allow_local_model_execution:
        prompt = _repository_bound_design_prompt(subgoal, source_inspection, repo)
        adapter = local_model_adapter or _default_local_model_adapter
        try:
            model_result = dict(
                adapter(
                    {
                        "task": "repository_bound_candidate_design",
                        "protocol": CANDIDATE_DESIGN_PROTOCOL,
                        "prompt": prompt,
                        "subgoal": dict(subgoal),
                        "source_inspection": source_inspection,
                        "allow_local_model_execution": allow_local_model_execution,
                    }
                )
            )
        except Exception as exc:  # noqa: BLE001 - advisory execution failure becomes visible evidence.
            model_result = {
                "model_id": "configured_local_model",
                "result": "local_model_failed",
                "executed": False,
                "answer": "",
                "reason": f"{type(exc).__name__}: {exc}",
                "provider_calls_performed": False,
            }
        contract = compile_repository_behavior_contract(controller, subgoal, source_inspection, advisory_result=model_result)
    timestamps["local_candidate_design_completed"] = utc_now()

    design = _validate_repository_bound_design(model_result, source_inspection, contract)
    contract_path = root / "repository_behavior_contract.json"
    _write_json(contract_path, contract.as_dict())
    design_path = root / "repository_bound_candidate_design.json"
    _write_json(
        design_path,
        {
            "protocol": CANDIDATE_DESIGN_PROTOCOL,
            "subgoal_id": subgoal.get("subgoal_id"),
            "source_inspection": source_inspection,
            "repository_behavior_contract": contract.as_dict(),
            "model_result": _model_result_for_artifact(model_result),
            "design_validation": design,
            "tracked_source_mutated": False,
            "provider_calls_performed": False,
        },
    )
    resource = ResourceUseRecord(
        "local_model",
        str(model_result.get("model_id") or "configured_local_model"),
        "repository-bound advisory candidate design",
        str(model_result.get("result") or "local_model_completed"),
        {
            "authoritative": False,
            "executed": bool(model_result.get("executed")),
            "provider_calls_performed": bool(model_result.get("provider_calls_performed")),
            "answer_digest": _digest(str(model_result.get("answer") or "")),
            "design_grounded": bool(design["grounded"]),
            "contract_disposition": contract.local_implementation_eligibility,
        },
    )
    record = _candidate_design_record(subgoal, source_inspection, design_path, design, model_result)
    reassessed = consume_continuous_capability_reassessment(controller, record)
    next_controller = _controller_after_repository_contract(reassessed, subgoal, contract, contract_path, design_path)
    timestamps["controller_handoff_completed"] = utc_now()
    result = SubgoalExecutionResult(
        accepted=contract.local_implementation_eligibility == "locally_implementable_by_existing_pcm",
        disposition=contract.local_implementation_eligibility,
        reason=_repository_contract_result_reason(contract),
        subgoal_id=str(subgoal["subgoal_id"]),
        campaign_root=str(root),
        consumed_once=True,
        source_inspection=source_inspection,
        baseline={"not_run": "repository behavior contract precedes patch materialization"},
        candidate={"state": "not_created", "reason": "generic success-reporting candidate strategy prohibited"},
        validation={"passed": False, "not_run": "no concrete candidate source exists"},
        clean_reproduction={"not_run": "no concrete candidate source exists"},
        application_request={},
        behavioral_evaluation_request={},
        reassessment={
            "capability_id": record.capability_id,
            "reassessment": record.reassessment,
            "contract_id": contract.contract_id,
            "contract_disposition": contract.local_implementation_eligibility,
        },
        resource_usage=(resource,),
        meaningful_transition_timestamps=timestamps,
        stalled_execution=False,
    )
    _write_json(result_path, result.as_dict())
    _write_json(root / "updated_restart_state_hint.json", {"controller_state": next_controller.continuous_mission_state})
    return next_controller, result


def _execute_legacy_repository_bound_design_block(
    controller: ContinuousRuntimeController,
    *,
    subgoal: Mapping[str, Any],
    root: Path,
    repo: Path,
    result_path: Path,
    source_inspection: Mapping[str, Any],
    timestamps: dict[str, str],
    local_model_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    allow_local_model_execution: bool,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    prompt = _repository_bound_design_prompt(subgoal, source_inspection, repo)
    adapter = local_model_adapter or _default_local_model_adapter
    try:
        model_result = dict(
            adapter(
                {
                    "task": "repository_bound_candidate_design",
                    "protocol": CANDIDATE_DESIGN_PROTOCOL,
                    "prompt": prompt,
                    "subgoal": dict(subgoal),
                    "source_inspection": source_inspection,
                    "allow_local_model_execution": allow_local_model_execution,
                }
            )
        )
    except Exception as exc:  # noqa: BLE001 - advisory execution failure becomes visible evidence.
        model_result = {
            "model_id": "configured_local_model",
            "result": "local_model_failed",
            "executed": False,
            "answer": "",
            "reason": f"{type(exc).__name__}: {exc}",
            "provider_calls_performed": False,
        }
    timestamps["local_candidate_design_completed"] = utc_now()
    design = _validate_repository_bound_design(model_result, source_inspection)
    design_path = root / "repository_bound_candidate_design.json"
    _write_json(
        design_path,
        {
            "protocol": CANDIDATE_DESIGN_PROTOCOL,
            "subgoal_id": subgoal.get("subgoal_id"),
            "source_inspection": source_inspection,
            "model_result": _model_result_for_artifact(model_result),
            "design_validation": design,
            "tracked_source_mutated": False,
            "provider_calls_performed": False,
        },
    )
    resource = ResourceUseRecord(
        "local_model",
        str(model_result.get("model_id") or "configured_local_model"),
        "repository-bound advisory candidate design",
        str(model_result.get("result") or "local_model_completed"),
        {
            "authoritative": False,
            "executed": bool(model_result.get("executed")),
            "provider_calls_performed": bool(model_result.get("provider_calls_performed")),
            "answer_digest": _digest(str(model_result.get("answer") or "")),
            "design_grounded": bool(design["grounded"]),
        },
    )
    record = _candidate_design_record(subgoal, source_inspection, design_path, design, model_result)
    failure_compilation = compile_behavioral_failure_record(
        _loose_behavioral_failure_evidence_packet(
            controller,
            subgoal,
            source_inspection,
            design_path,
            design,
            model_result,
        ),
        existing_records=controller.continuous_behavioral_failure_records,
    )
    failure_compilation_path = root / "behavioral_failure_compilation.json"
    _write_json(
        failure_compilation_path,
        {
            "accepted": failure_compilation.accepted,
            "record": failure_compilation.record.as_dict() if failure_compilation.record is not None else None,
            "rejection_reason": failure_compilation.rejection_reason,
            "missing_fields": failure_compilation.missing_fields,
            "source_classification": failure_compilation.source_classification,
            "duplicate_of": failure_compilation.duplicate_of,
            "version_of": failure_compilation.version_of,
            "tracked_source_mutated": False,
            "provider_calls_performed": False,
        },
    )
    reassessed = consume_continuous_capability_reassessment(controller, record)
    next_controller = _observe_missing_behavioral_failure_contract(
        reassessed,
        subgoal,
        design_path,
        failure_compilation_path,
        failure_compilation,
    )
    timestamps["controller_handoff_completed"] = utc_now()
    disposition = (
        "legacy_loose_evidence_compiled_to_behavioral_failure"
        if failure_compilation.accepted
        else "missing_behavioral_failure_contract"
    )
    reason = (
        "legacy loose evidence compiled into a sealed BehavioralFailureRecord"
        if failure_compilation.accepted
        else f"legacy loose evidence rejected before candidate creation: {failure_compilation.rejection_reason}"
    )
    result = SubgoalExecutionResult(
        accepted=False,
        disposition=disposition,
        reason=reason,
        subgoal_id=str(subgoal["subgoal_id"]),
        campaign_root=str(root),
        consumed_once=True,
        source_inspection=dict(source_inspection),
        baseline={"not_run": "candidate design precedes a behavior contract"},
        candidate={"state": "not_created", "reason": "generic success-reporting candidate strategy prohibited"},
        validation={"passed": False, "not_run": "no concrete candidate source exists"},
        clean_reproduction={"not_run": "no concrete candidate source exists"},
        application_request={},
        behavioral_evaluation_request={},
        reassessment={
            "capability_id": record.capability_id,
            "reassessment": record.reassessment,
            "behavioral_failure_compilation": {
                "accepted": failure_compilation.accepted,
                "rejection_reason": failure_compilation.rejection_reason,
                "missing_fields": failure_compilation.missing_fields,
                "source_classification": failure_compilation.source_classification,
                "path": str(failure_compilation_path),
            },
        },
        resource_usage=(resource,),
        meaningful_transition_timestamps=timestamps,
        stalled_execution=False,
    )
    _write_json(result_path, result.as_dict())
    _write_json(root / "updated_restart_state_hint.json", {"controller_state": next_controller.continuous_mission_state})
    return next_controller, result


def _loose_behavioral_failure_evidence_packet(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    source_inspection: Mapping[str, Any],
    design_path: Path,
    design: Mapping[str, Any],
    model_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize legacy loose runtime evidence without inventing expectations.

    The packet intentionally includes only authoritative fields that exist in
    the current runtime state. Missing expected behavior, reproduction, or
    independent evidence must be reported by the BehavioralFailureRecord
    compiler rather than patched over with a guessed diagnosis.
    """

    mission_id = str((controller.continuous_mission_contract or {}).get("mission_id") or controller.session_id)
    state_material = {
        "session_id": controller.session_id,
        "mission_id": mission_id,
        "main_goal_id": (controller.continuous_main_goal or {}).get("main_goal_id", ""),
        "subgoal_id": subgoal.get("subgoal_id", ""),
        "weakness_id": subgoal.get("weakness_id", ""),
        "design_path": str(design_path),
        "design_rejection_reason": design.get("rejection_reason", ""),
    }
    return {
        "source_type": "runtime_transition_violation",
        "source_reference": str(design_path),
        "source_digest": _digest(_read_json(design_path)),
        "observed_behavior": str(design.get("rejection_reason") or "legacy loose evidence cannot support candidate creation"),
        "expected_behavior_authority": "concrete_mission_success_criterion",
        "expected_vs_observed_result": "missing_behavioral_failure_contract",
        "baseline_reproduction": str(subgoal.get("baseline") or ""),
        "reproduction_command_or_predicate": "runtime packet inspection only; no deterministic reproduction predicate sealed",
        "first_incorrect_transition": "legacy loose runtime evidence -> candidate creation requested before sealed BehavioralFailureRecord",
        "affected_runtime_stage": "continuous_subgoal_execution",
        "affected_capability_id": _capability_id_from_subgoal(subgoal),
        "originating_mission_id": mission_id,
        "suspected_owner_paths": ("orchestration/runtime/continuous_subgoal_executor.py",),
        "independent_evidence_paths": (),
        "allowed_scope": ("orchestration/runtime", "tests/runtime_gsr"),
        "excluded_scope": ("DELTA-75", "reports/RC4_*"),
        "materiality_reason": "candidate creation would otherwise depend on unsealed loose evidence",
        "reproducibility_status": "reproduction_pending",
        "occurrence_count": 1,
        "first_seen": utc_now(),
        "last_seen": utc_now(),
        "environment_digest": _digest(
            {
                "source_inspection_id": source_inspection.get("inspection_id", ""),
                "file_count": source_inspection.get("file_count", 0),
            }
        ),
        "state_digest": _digest(state_material),
        "reproduction_output_digest": _digest(
            {
                "model_result": _model_result_for_artifact(model_result),
                "design_validation": dict(design),
            }
        ),
        "authority_class": "local_execution_allowed",
        "ambiguity_status": "missing_expected_behavior",
        "current_disposition": "reproduction_pending",
    }


def _observe_missing_behavioral_failure_contract(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    design_path: Path,
    compilation_path: Path,
    compilation_result: Any,
) -> ContinuousRuntimeController:
    scope_signature = stable_id(
        "behavioral-failure-contract-scope",
        str(subgoal.get("subgoal_id") or ""),
        tuple(str(item) for item in (subgoal.get("source_inspection_scope") or ())),
        compilation_result.rejection_reason,
        compilation_result.missing_fields,
    )
    return replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        active_work_item="observing_for_new_weaknesses",
        continuous_observation_state={
            **(controller.continuous_observation_state or {}),
            "observation_reason": "missing_behavioral_failure_contract",
            "expected_external_change": "authoritative behavioral failure evidence or bounded reproduction packet",
            "behavioral_failure_compilation": {
                "accepted": compilation_result.accepted,
                "rejection_reason": compilation_result.rejection_reason,
                "missing_fields": compilation_result.missing_fields,
                "source_classification": compilation_result.source_classification,
                "compilation_path": str(compilation_path),
                "design_path": str(design_path),
            },
            "candidate_design_evidence_exhausted": True,
            "candidate_design_evidence_scope_signature": scope_signature,
        },
    )


def _repository_bound_design_prompt(
    subgoal: Mapping[str, Any],
    source_inspection: Mapping[str, Any],
    repo: Path,
) -> str:
    files = tuple(source_inspection.get("files") or ())
    excerpts: list[str] = []
    terms = _source_relevance_terms(subgoal)
    implementation_files = [item for item in files if not str(item.get("path") or "").replace("\\", "/").startswith("tests/")]
    evidence_files = [item for item in files if str(item.get("path") or "").replace("\\", "/").startswith("tests/")]
    prompt_files = (*implementation_files[:3], *evidence_files[:1])
    for item in prompt_files:
        relative = str(item.get("path") or "")
        path = (repo / relative).resolve()
        if not relative or not str(path).startswith(str(repo)) or not path.is_file():
            continue
        content = _relevant_source_excerpt(path, terms)
        excerpts.append(f"PATH: {relative}\n{content}")
    allowed_paths = [str(item.get("path") or "") for item in files]
    excerpt_text = "\n\n".join(excerpts) or "(no readable source excerpts)"
    return (
        "You are an advisory local development planner. You have no authority to edit files, run tools, approve work, or claim success. "
        "Identify an implementation target only when the supplied repository evidence supports it. "
        "Return JSON only, with no markdown or explanation outside the object. Use short values and exactly these keys: "
        "affected_path, evidence_path, failure_mechanism, candidate_behavior, independent_evidence_needed, validation_target. "
        "affected_path and evidence_path must each be one of the supplied paths; evidence_path must name a test or independent evidence file. "
        "If the evidence is insufficient, use an empty affected_path and state exactly what independent evidence is missing.\n\n"
        f"OBJECTIVE: {str(subgoal.get('measurable_objective') or '')}\n"
        f"BASELINE: {str(subgoal.get('baseline') or '')}\n"
        f"ALLOWED_PATHS: {json.dumps(allowed_paths)}\n"
        f"REPOSITORY_EXCERPTS:\n{excerpt_text}"
    )


def _validate_repository_bound_design(
    model_result: Mapping[str, Any],
    source_inspection: Mapping[str, Any],
    contract: RepositoryBehaviorContract | None = None,
) -> dict[str, Any]:
    if contract is not None:
        grounded = contract.local_implementation_eligibility in {
            "locally_implementable_by_existing_pcm",
            "locally_implementable_but_pcm_operation_unsupported",
        }
        return {
            "grounded": grounded,
            "answer_format": "repository_behavior_contract",
            "affected_path": contract.affected_path,
            "evidence_path": contract.independent_evidence_path,
            "evidence_path_is_independent": bool(contract.independent_evidence_path and contract.independent_evidence_path != contract.affected_path),
            "allowed_paths": contract.allowed_paths,
            "missing_fields": contract.missing_fields,
            "failure_mechanism": contract.failure_mechanism,
            "candidate_behavior": contract.candidate_behavior,
            "independent_evidence_needed": "" if contract.independent_evidence_path else "preexisting independent evidence path",
            "validation_target": contract.independent_validation_predicate,
            "contract_id": contract.contract_id,
            "contract_digest": contract.contract_digest,
            "contract_disposition": contract.local_implementation_eligibility,
            "pcm_operation_supported": contract.local_implementation_eligibility == "locally_implementable_by_existing_pcm",
            "rejection_reason": (
                "repository_behavior_contract_ready_for_existing_pcm"
                if contract.local_implementation_eligibility == "locally_implementable_by_existing_pcm"
                else contract.local_implementation_eligibility
            ),
        }
    answer = str(model_result.get("answer") or "").strip()
    parsed: dict[str, Any] = {}
    if answer.startswith("{") and answer.endswith("}"):
        try:
            parsed = dict(json.loads(answer))
        except (TypeError, ValueError):
            parsed = {}
    allowed_paths = {str(item.get("path") or "") for item in (source_inspection.get("files") or ())}
    affected_path = str(parsed.get("affected_path") or "")
    evidence_path = str(parsed.get("evidence_path") or "")
    normalized_evidence_path = evidence_path.replace("\\", "/")
    required = ("failure_mechanism", "candidate_behavior", "independent_evidence_needed", "validation_target")
    missing = tuple(name for name in required if not str(parsed.get(name) or "").strip())
    evidence_path_is_independent = evidence_path in allowed_paths and (
        normalized_evidence_path.startswith("tests/")
    )
    grounded = bool(model_result.get("executed")) and affected_path in allowed_paths and evidence_path_is_independent and not missing
    return {
        "grounded": grounded,
        "answer_format": "json_object" if parsed else "unstructured_or_invalid_json",
        "affected_path": affected_path,
        "evidence_path": evidence_path,
        "evidence_path_is_independent": evidence_path_is_independent,
        "allowed_paths": tuple(sorted(allowed_paths)),
        "missing_fields": missing,
        "failure_mechanism": str(parsed.get("failure_mechanism") or ""),
        "candidate_behavior": str(parsed.get("candidate_behavior") or ""),
        "independent_evidence_needed": str(parsed.get("independent_evidence_needed") or ""),
        "validation_target": str(parsed.get("validation_target") or ""),
        "rejection_reason": (
            "advisory_design_did_not_bind_to_inspected_repository_evidence"
            if not grounded
            else "implementation_backend_not_enabled_without_separate_sandbox_candidate_contract"
        ),
    }


def _model_result_for_artifact(model_result: Mapping[str, Any]) -> dict[str, Any]:
    """Persist bounded advisory evidence without prompts or any secret-bearing state."""

    return {
        "model_id": str(model_result.get("model_id") or ""),
        "result": str(model_result.get("result") or ""),
        "executed": bool(model_result.get("executed")),
        "answer": str(model_result.get("answer") or ""),
        "answer_digest": _digest(str(model_result.get("answer") or "")),
        "confidence_score": model_result.get("confidence_score"),
        "latency_seconds": model_result.get("latency_seconds"),
        "response_tokens": model_result.get("response_tokens"),
        "provider_calls_performed": bool(model_result.get("provider_calls_performed")),
        "reason": str(model_result.get("reason") or ""),
    }


def _candidate_design_record(
    subgoal: Mapping[str, Any],
    source_inspection: Mapping[str, Any],
    design_path: Path,
    design: Mapping[str, Any],
    model_result: Mapping[str, Any],
) -> CapabilityKnowledgeRecord:
    capability_id = _capability_id_from_subgoal(subgoal)
    return CapabilityKnowledgeRecord(
        capability_id=capability_id,
        original_weakness=str(subgoal.get("measurable_objective") or ""),
        evidence=(str(source_inspection.get("inspection_id") or ""), str(design_path)),
        first_incorrect_transition="broad weakness label -> static self-reporting candidate -> no independently checkable behavior contract",
        strategies_attempted=("repository_bound_candidate_design",),
        failed_approaches=("generic_static_candidate_metric_prohibited", str(design.get("rejection_reason") or "")),
        successful_mechanism="bounded local model advisory recorded without granting code, tool, authority, or mutation rights",
        exact_candidate="",
        tests_added=(),
        metrics_before_after={
            "candidate_design_grounded": bool(design.get("grounded")),
            "model_executed": bool(model_result.get("executed")),
            "model_answer_digest": _digest(str(model_result.get("answer") or "")),
        },
        controls=("tracked_source_remains_unchanged", "advisory_output_cannot_authorize_implementation"),
        adversarial_evidence=("uninspected_or_unstructured_model_target_rejected",),
        held_out_evidence={"independent_behavior_contract_available": False},
        reproduction_evidence=str(design_path),
        provider_contribution="none",
        local_repair_contribution="repository_bound_local_model_candidate_design",
        application_evidence="not applicable; no implementation candidate was created",
        regression_evidence="candidate design validation is deterministic and path-bound",
        reassessment="blocked_missing_concrete_behavior_contract",
        residual_uncertainty="a concrete repository target and preexisting independent behavior case are required before sandbox implementation",
        reusable_process_rules=("do not fabricate a generic success-reporting candidate from an abstract weakness",),
        evidence_stage="hypothesis",
        capability_acquired=False,
        eligible_for_behavioral_evaluation=False,
    )


def _controller_after_repository_contract(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    contract: RepositoryBehaviorContract,
    contract_path: Path,
    design_path: Path,
) -> ContinuousRuntimeController:
    disposition = contract.local_implementation_eligibility
    if disposition == "locally_implementable_by_existing_pcm":
        return replace(
            controller,
            continuous_mission_state="grounded_design_eligible",
            active_work_item="repository_behavior_contract_ready",
            continuous_observation_state={
                **(controller.continuous_observation_state or {}),
                "repository_behavior_contract": {
                    "contract_id": contract.contract_id,
                    "contract_path": str(contract_path),
                    "design_path": str(design_path),
                    "disposition": disposition,
                    "pcm_operation_supported": True,
                },
            },
        )
    if disposition == "blocked_by_authority":
        return _create_repository_contract_authority_request(controller, subgoal, contract, contract_path)
    if disposition == "unresolved_failure_mechanism":
        return _create_repository_contract_operator_question(controller, subgoal, contract, contract_path)
    reason_map = {
        "locally_implementable_but_pcm_operation_unsupported": "patch_expressiveness_blocker",
        "missing_repository_evidence": "repository_evidence_needed",
        "missing_independent_behavior_contract": "independent_behavior_contract_needed",
        "blocked_by_resource": "resource_blocked",
        "accepted_boundary": "accepted_boundary",
        "invalid_scope": "invalid_scope",
    }
    return replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        active_work_item="observing_for_new_weaknesses",
        continuous_observation_state={
            **(controller.continuous_observation_state or {}),
            "repository_behavior_contract": {
                "contract_id": contract.contract_id,
                "contract_path": str(contract_path),
                "design_path": str(design_path),
                "disposition": disposition,
                "observation_reason": reason_map.get(disposition, disposition),
                "missing_fields": contract.missing_fields,
                "validation_errors": contract.validation_errors,
            },
        },
    )


def _create_repository_contract_operator_question(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    contract: RepositoryBehaviorContract,
    contract_path: Path,
) -> ContinuousRuntimeController:
    request_id = stable_id("operator-insight-repository-contract", controller.session_id, contract.contract_id)
    request = {
        "request_id": request_id,
        "request_kind": "clarification",
        "request_source": "repository_behavior_contract",
        "status": "pending",
        "exact_question": "Which concrete failure mechanism, if any, links the inspected implementation path to the sealed expected behavior?",
        "rationale": "The runtime has affected/evidence paths but cannot derive a failure mechanism without fabricating a diagnosis.",
        "evidence_refs": (str(contract_path),),
        "source_gap_ids": (str(subgoal.get("weakness_id") or ""),),
        "affected_gap": str(subgoal.get("weakness_id") or ""),
        "blocked_transition": "repository behavior contract -> grounded design eligibility",
        "authority_scope": "none; clarification grants no mutation, application, provider, Git, or deployment authority",
        "blocking_scope": "one repository behavior contract",
        "permitted_responses": ("defer", "treat as accepted boundary", "provide failure mechanism"),
        "authority_granted": False,
        "created_at": utc_now(),
    }
    if any(item.get("request_id") == request_id and item.get("status") == "pending" for item in controller.continuous_developmental_insight_requests):
        return replace(controller, continuous_mission_state="awaiting_operator_insight", active_work_item="awaiting_operator_insight")
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        continuous_active_subgoal={},
        active_work_item="awaiting_operator_insight",
        continuous_developmental_insight_requests=controller.continuous_developmental_insight_requests + (request,),
    )


def _create_repository_contract_authority_request(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    contract: RepositoryBehaviorContract,
    contract_path: Path,
) -> ContinuousRuntimeController:
    request_id = stable_id("operator-authority-repository-contract", controller.session_id, contract.contract_id)
    request = {
        "request_id": request_id,
        "request_kind": "tracked_application_authority",
        "request_source": "repository_behavior_contract",
        "status": "pending",
        "exact_question": "A repository behavior contract requires authority outside the current local execution envelope. Approve only an exact scoped authority expansion or defer.",
        "rationale": "Authority boundary came from the sealed failure record, not advisory output.",
        "evidence_refs": (str(contract_path),),
        "source_gap_ids": (str(subgoal.get("weakness_id") or ""),),
        "affected_gap": str(subgoal.get("weakness_id") or ""),
        "blocked_transition": "repository behavior contract -> grounded design eligibility",
        "authority_scope": contract.authority_class,
        "blocking_scope": "one repository behavior contract",
        "permitted_responses": ("defer", "approve exact scoped authority"),
        "authority_granted": False,
        "created_at": utc_now(),
    }
    if any(item.get("request_id") == request_id and item.get("status") == "pending" for item in controller.continuous_developmental_insight_requests):
        return replace(controller, continuous_mission_state="awaiting_operator_authority", active_work_item="awaiting_operator_authority")
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_authority",
        continuous_active_subgoal={},
        active_work_item="awaiting_operator_authority",
        continuous_developmental_insight_requests=controller.continuous_developmental_insight_requests + (request,),
    )


def _repository_contract_result_reason(contract: RepositoryBehaviorContract) -> str:
    reasons = {
        "locally_implementable_by_existing_pcm": "repository behavior contract is grounded and matches the existing expected-symbol PCM operation; patch materialization was intentionally not invoked in this gate",
        "locally_implementable_but_pcm_operation_unsupported": "repository behavior contract is grounded but requires a repair shape outside current PCM patch semantics",
        "missing_repository_evidence": "no inspected implementation path could be bound to the sealed failure",
        "missing_independent_behavior_contract": "no inspected independent evidence path could validate the behavior without candidate self-reporting",
        "unresolved_failure_mechanism": "affected and evidence paths are present but the failure mechanism cannot be derived without fabricating a diagnosis",
        "blocked_by_authority": "sealed failure record requires authority outside the current local envelope",
        "blocked_by_resource": "sealed failure record is blocked by unavailable resource authority",
        "accepted_boundary": "sealed failure record marks this caveat as an accepted boundary",
        "invalid_scope": "contract requested forbidden or protected scope",
    }
    return reasons.get(contract.local_implementation_eligibility, contract.local_implementation_eligibility)


def _pause_for_candidate_design_evidence(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    design_path: Path,
    design: Mapping[str, Any],
) -> ContinuousRuntimeController:
    scope_signature = stable_id(
        "repository-bound-candidate-design-scope",
        tuple(str(item) for item in (subgoal.get("source_inspection_scope") or ())),
        str((controller.continuous_observation_state or {}).get("operator_supplied_candidate_target") or ""),
    )
    request_id = stable_id(
        "operator-insight-repository-bound-candidate",
        controller.session_id,
        subgoal.get("subgoal_id"),
        design.get("rejection_reason"),
    )
    request = {
        "request_id": request_id,
        "request_kind": "insight",
        "request_source": "repository_bound_candidate_design",
        "status": "pending",
        "exact_question": "The local design lane could not identify a concrete inspected implementation target and independent behavior case. Should DELTA defer this abstract gap, treat it as an accepted boundary, or provide an exact path and preexisting failing case?",
        "rationale": "The previous generic candidate strategy was rejected because it only self-reported success. No implementation will be fabricated from an abstract metric.",
        "evidence_refs": (str(design_path),),
        "source_gap_ids": (str(subgoal.get("weakness_id") or ""),),
        "affected_gap": str(subgoal.get("weakness_id") or ""),
        "blocked_transition": "repository-bound candidate design -> safe sandbox implementation",
        "authority_scope": "none; an insight response cannot authorize mutation, application, API use, Git, or deployment",
        "blocking_scope": "one abstract development branch",
        "permitted_responses": ("provide exact target and case", "treat as accepted boundary", "defer"),
        "authority_granted": False,
        "created_at": utc_now(),
    }
    existing = tuple(
        {
            **dict(item),
            "status": "superseded_by_repository_bound_candidate_design",
            "superseded_at": utc_now(),
        }
        if str(item.get("status") or "pending") == "pending"
        else dict(item)
        for item in controller.continuous_developmental_insight_requests
    )
    if any(item.get("request_id") == request_id and item.get("status") == "pending" for item in existing):
        return replace(
            controller,
            continuous_mission_state="awaiting_operator_insight",
            active_work_item="awaiting_operator_insight",
        )
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        continuous_active_subgoal={},
        active_work_item="awaiting_operator_insight",
        continuous_developmental_insight_requests=existing + (request,),
        continuous_observation_state={
            **(controller.continuous_observation_state or {}),
            "candidate_design_blocker": {
                "request_id": request_id,
                "design_path": str(design_path),
                "reason": str(design.get("rejection_reason") or ""),
            },
            "candidate_design_evidence_exhausted": True,
            "candidate_design_evidence_scope_signature": scope_signature,
        },
    )


def _subgoal_requests_model(subgoal: Mapping[str, Any]) -> bool:
    text = json.dumps(subgoal, sort_keys=True).lower()
    return (
        "model" in text
        or "advisor" in text
        or "advisory" in text
        or "diagnosis" in text
        or "resource_usage" in text
        or "resource-bearing" in text
        or "available_resource" in text
        or "resource_selection" in text
        or "authority_boundary_resource_filter" in text
        or "local_model_advisory_probe" in text
        or "resource_evidence_integration" in text
    )


def _subgoal_requests_reference(subgoal: Mapping[str, Any]) -> bool:
    text = json.dumps(subgoal, sort_keys=True).lower()
    return (
        "wiki" in text
        or "reference" in text
        or "documentation" in text
        or "resource_usage" in text
        or "resource-bearing" in text
        or "available_resource" in text
        or "resource_selection" in text
        or "reference_retrieval_probe" in text
        or "resource_evidence_integration" in text
    )


def _default_local_model_adapter(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    subgoal = dict(payload.get("subgoal") or {})
    prompt = str(payload.get("prompt") or subgoal.get("measurable_objective") or "Analyze continuous runtime subgoal.")
    lane = select_model_lane(prompt, "coding")
    if not payload.get("allow_local_model_execution"):
        return {
            "model_id": lane.get("selected_model_id") or lane.get("support_identifier"),
            "result": "local_model_execution_not_authorized_for_this_call",
            "lane": lane.get("lane"),
            "available": bool(lane.get("available")),
            "executed": False,
            "answer": "",
            "provider_calls_performed": False,
            "provenance": "rc2_conversational_mode_router.select_model_lane",
        }
    result = execute_local_model_answer(prompt, lane)
    return {
        "model_id": result.get("model_id") or lane.get("selected_model_id") or lane.get("support_identifier"),
        "result": "local_model_executed" if result.get("executed") else "local_model_unavailable_or_failed",
        "lane": lane.get("lane"),
        "available": bool(result.get("available", lane.get("available"))),
        "executed": bool(result.get("executed")),
        "answer": str(result.get("answer") or ""),
        "confidence_score": result.get("confidence_score"),
        "latency_seconds": result.get("latency_seconds"),
        "response_tokens": result.get("response_tokens"),
        "reason": result.get("reason"),
        "provider_calls_performed": bool(result.get("provider_calls_performed")),
        "provenance": "rc2_conversational_mode_router.execute_local_model_answer",
    }


def _default_reference_adapter(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    from orchestration.runtime.delta_1_4_live_wikipedia_runtime import activated_wikipedia_profile, retrieve_wikipedia_text

    subgoal = dict(payload.get("subgoal") or {})
    text = json.dumps(subgoal, sort_keys=True).lower()
    default_query = "Evidence" if "reference_retrieval_probe" in text or "resource_evidence_integration" in text else "software testing"
    query = str(subgoal.get("wiki_query") or subgoal.get("reference_query") or default_query)
    profile = activated_wikipedia_profile(max_queries_per_objective=1)
    result = retrieve_wikipedia_text(query, profile=profile)
    return {
        "source": "wikipedia_rest_summary",
        "result": "reference_complete",
        "title": result.title,
        "canonical_url": result.canonical_url,
        "provenance": {
            "query": result.query,
            "retrieved_at": result.retrieved_at,
            "revision_timestamp": result.revision_timestamp,
            "chars_used": result.chars_used,
        },
    }


def _substantive_evidence_check(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
    source_inspection: Mapping[str, Any],
    resource_usage: tuple[ResourceUseRecord, ...],
) -> dict[str, Any]:
    capability = _capability_id_from_subgoal(subgoal)
    checks: dict[str, bool] = {
        "source_inspection_meaningful": bool(source_inspection.get("meaningful")),
    }
    if capability in {
        "knowledge_retrieval_index",
        "prior_failure_avoidance_check",
        "next_goal_evidence_reuse_record",
    }:
        ledger = tuple(dict(item) for item in controller.continuous_knowledge_ledger)
        checks.update(
            {
                "knowledge_ledger_nonempty": bool(ledger),
                "residual_uncertainty_present": any(item.get("residual_uncertainty") for item in ledger),
                "process_rules_present": any(item.get("reusable_process_rules") for item in ledger),
            }
        )
    if capability in {
        "available_resource_inventory",
        "local_resource_selection_trace",
        "authority_boundary_resource_filter",
    }:
        resource_types = {item.resource_type for item in resource_usage}
        checks.update(
            {
                "local_model_lane_recorded": "local_model" in resource_types,
                "reference_lane_recorded": "built_in_reference" in resource_types,
                "all_resource_outputs_non_authoritative": all(item.provenance.get("authoritative") is False for item in resource_usage) if resource_usage else False,
            }
        )
    if capability in {
        "local_model_advisory_probe",
        "reference_retrieval_probe",
        "resource_evidence_integration",
    }:
        resources = {item.resource_type: item for item in resource_usage}
        checks.update(
            {
                "local_model_advisory_recorded": "local_model" in resources,
                "reference_recorded": "built_in_reference" in resources,
                "reference_not_failed": resources.get("built_in_reference", ResourceUseRecord("", "", "", "")).result != "reference_failed",
                "advisory_outputs_non_authoritative": all(item.provenance.get("authoritative") is False for item in resource_usage) if resource_usage else False,
            }
        )
    failed = tuple(name for name, passed in checks.items() if not passed)
    evidence_path = Path(str(subgoal.get("subgoal_id") or "subgoal"))  # stable label only; real path is stored by caller context.
    return {
        "capability_id": capability,
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "evidence_label": str(evidence_path),
    }


def _inspect_sources(repo: Path, subgoal: Mapping[str, Any]) -> dict[str, Any]:
    scopes = tuple(str(item) for item in subgoal.get("source_inspection_scope") or ("orchestration/runtime", "tests/runtime_gsr"))
    inspected: list[dict[str, Any]] = []
    terms = _source_relevance_terms(subgoal)
    for scope in scopes:
        path = (repo / scope).resolve()
        if not str(path).startswith(str(repo)):
            continue
        candidates = [path] if path.is_file() else list(path.rglob("*.py")) if path.exists() else []
        files = sorted(
            candidates,
            key=lambda candidate: (
                -_source_path_relevance(str(candidate.relative_to(repo)), terms),
                str(candidate.relative_to(repo)),
            ),
        )[:8]
        for file_path in files:
            if file_path.is_file():
                raw = file_path.read_bytes()
                inspected.append(
                    {
                        "path": str(file_path.relative_to(repo)),
                        "byte_count": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "symbols": _python_symbols(file_path),
                    }
                )
    return {
        "inspection_id": stable_id("continuous-source-inspection", subgoal.get("subgoal_id"), inspected),
        "files": inspected,
        "file_count": len(inspected),
        "meaningful": bool(inspected),
    }


def _python_symbols(path: Path) -> tuple[str, ...]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ()
    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
    return tuple(sorted(set(symbols)))[:32]


def _source_relevance_terms(subgoal: Mapping[str, Any]) -> tuple[str, ...]:
    text = " ".join(
        str(subgoal.get(key) or "")
        for key in ("subgoal_id", "weakness_id", "measurable_objective", "baseline", "source_mission_id")
    ).lower()
    tokens = {token for token in re.findall(r"[a-z][a-z0-9_]{3,}", text)}
    # The executor and its tests are always direct evidence for this runtime's
    # implementation boundary, regardless of the abstract weakness wording.
    tokens.update({"continuous", "subgoal", "candidate", "executor", "worker", "operator", "test"})
    return tuple(sorted(tokens))


def _source_path_relevance(relative: str, terms: tuple[str, ...]) -> int:
    normalized = relative.replace("\\", "/").lower()
    score = sum(3 for term in terms if term in normalized)
    if normalized.startswith("tests/"):
        score += 2
    if "continuous_" in normalized:
        score += 4
    return score


def _relevant_source_excerpt(path: Path, terms: tuple[str, ...], *, limit: int = 1400) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not positions:
        return text[:limit]
    start = max(0, min(positions) - 220)
    return text[start : start + limit]


def _run_baseline(root: Path, repo: Path, python_executable: str, subgoal: Mapping[str, Any]) -> dict[str, Any]:
    script = root / "baseline_check.py"
    script.write_text(
        "from pathlib import Path\n"
        "assert Path('orchestration/runtime/continuous_runtime_controller.py').exists()\n"
        "print('baseline_metric=0.0')\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [python_executable, str(script)],
        cwd=str(repo),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    return {
        "command": [python_executable, str(script)],
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr_digest": _digest(completed.stderr),
        "metric": subgoal.get("baseline"),
        "passed": completed.returncode == 0,
    }


def _write_candidate(root: Path, subgoal: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = stable_id("continuous-subgoal-candidate", subgoal.get("subgoal_id"), subgoal.get("measurable_objective"))
    path = root / "candidate" / "continuous_candidate.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    objective = str(subgoal.get("measurable_objective") or "")
    objective_digest = _digest(objective)
    capability_key = str(subgoal.get("baseline") or "continuous_subgoal").split("=", 1)[0]
    path.write_text(
        f"OBJECTIVE_DIGEST = {objective_digest!r}\n"
        f"CAPABILITY_KEY = {capability_key!r}\n"
        "\n"
        "def candidate_metric():\n"
        "    return {\n"
        "        'target_metric': 1.0,\n"
        "        'control_stable': True,\n"
        "        'tracked_source_mutated': False,\n"
        "        'objective_digest': OBJECTIVE_DIGEST,\n"
        "        'capability_key': CAPABILITY_KEY,\n"
        "    }\n",
        encoding="utf-8",
    )
    return {
        "candidate_id": candidate_id,
        "path": str(path),
        "digest": _digest(path.read_text(encoding="utf-8")),
        "objective_digest": objective_digest,
        "capability_key": capability_key,
        "tracked_source_mutated": False,
    }


def _run_validation(root: Path, python_executable: str) -> dict[str, Any]:
    script = root / "validate_candidate.py"
    script.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path('candidate').resolve()))\n"
        "import continuous_candidate\n"
        "from continuous_candidate import candidate_metric\n"
        "result = candidate_metric()\n"
        "assert result['target_metric'] == 1.0\n"
        "assert result['control_stable'] is True\n"
        "assert result['tracked_source_mutated'] is False\n"
        "assert result['objective_digest'] == continuous_candidate.OBJECTIVE_DIGEST\n"
        "assert result['capability_key'] == continuous_candidate.CAPABILITY_KEY\n"
        "print('focused_validation=passed')\n",
        encoding="utf-8",
    )
    completed = subprocess.run([python_executable, str(script)], cwd=str(root), text=True, capture_output=True, timeout=20, check=False)
    return {
        "command": [python_executable, str(script)],
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr_digest": _digest(completed.stderr),
        "passed": completed.returncode == 0,
        "digest": _digest({"stdout": completed.stdout, "returncode": completed.returncode}),
    }


def _run_clean_reproduction(root: Path, python_executable: str) -> dict[str, Any]:
    reproduction = root / "clean_reproduction"
    if reproduction.exists():
        shutil.rmtree(reproduction)
    shutil.copytree(root / "candidate", reproduction / "candidate")
    shutil.copy2(root / "validate_candidate.py", reproduction / "validate_candidate.py")
    completed = subprocess.run([python_executable, "validate_candidate.py"], cwd=str(reproduction), text=True, capture_output=True, timeout=20, check=False)
    return {
        "root": str(reproduction),
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr_digest": _digest(completed.stderr),
        "passed": completed.returncode == 0,
    }


def _behavioral_evaluation_request(
    subgoal: Mapping[str, Any],
    candidate: Mapping[str, Any],
    record: CapabilityKnowledgeRecord,
) -> dict[str, Any]:
    capability_id = record.capability_id
    task_family_id = stable_id("task-family", capability_id, subgoal.get("measurable_objective"))
    evaluation_id = stable_id("behavioral-evaluation", task_family_id, candidate.get("candidate_id"))
    return {
        "evaluation_id": evaluation_id,
        "task_family_id": task_family_id,
        "capability_id": capability_id,
        "developmental_gap_id": str(subgoal.get("weakness_id") or capability_id),
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "disposition": "evaluation_pending",
        "required_evidence": (
            "baseline_attempt_id",
            "sealed_or_preexisting_case_ids",
            "control_case_ids",
            "post_candidate_metrics",
            "transfer_metrics",
            "regression_metrics",
            "evidence_independence",
        ),
        "promotion_blocker": "independent_behavioral_evaluation_required",
        "structural_validation_is_not_capability_acquisition": True,
    }


def _capability_record(
    subgoal: Mapping[str, Any],
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
    validation: Mapping[str, Any],
    reproduction: Mapping[str, Any],
    source_inspection: Mapping[str, Any],
) -> CapabilityKnowledgeRecord:
    return CapabilityKnowledgeRecord(
        capability_id=_capability_id_from_subgoal(subgoal, candidate),
        original_weakness=str(subgoal.get("measurable_objective") or ""),
        evidence=(str(source_inspection.get("inspection_id")), str(validation.get("digest"))),
        first_incorrect_transition="controller-owned active_subgoal -> sandbox_development_active -> no executor consumed it",
        strategies_attempted=("continuous_subgoal_execution_bridge",),
        failed_approaches=() if validation.get("passed") else ("candidate_validation_failed",),
        successful_mechanism="active subgoal consumed into local sandbox candidate, validation, and clean reproduction",
        exact_candidate=str(candidate.get("path")),
        tests_added=(),
        metrics_before_after={
            "baseline": baseline.get("metric"),
            "validation_passed": validation.get("passed"),
            "substantive_evidence": validation.get("substantive_evidence"),
            "candidate_id": candidate.get("candidate_id"),
            "candidate_digest": candidate.get("digest"),
        },
        controls=("tracked_source_remains_unchanged_before_application",),
        adversarial_evidence=("liveness-only metric rejected",),
        held_out_evidence={"clean_reproduction": reproduction.get("passed")},
        reproduction_evidence=str(reproduction.get("root")),
        provider_contribution="none",
        local_repair_contribution=_local_contribution_summary(subgoal),
        application_evidence="not applied; tracked source remains operator-gated",
        regression_evidence="focused continuous subgoal executor tests",
        reassessment="candidate_structurally_validated" if validation.get("passed") and reproduction.get("passed") else "failed",
        residual_uncertainty="candidate is local diagnostic unless application review is separately requested",
        reusable_process_rules=("heartbeat does not count as development progress",),
        evidence_stage="candidate_structurally_validated" if validation.get("passed") and reproduction.get("passed") else "behaviorally_failed",
        capability_acquired=False,
        eligible_for_behavioral_evaluation=bool(validation.get("passed") and reproduction.get("passed")),
        behavioral_evaluation_ref="",
    )


def _execute_independent_behavioral_evaluation(
    controller: ContinuousRuntimeController,
    *,
    subgoal: Mapping[str, Any],
    root: Path,
    result_path: Path,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    """Evaluate a structural candidate without trusting its own reported metric."""

    request = dict(subgoal.get("behavioral_evaluation") or {})
    structural_payload = dict(request.get("structural_record") or {})
    if not structural_payload:
        raise ValueError("behavioral evaluation subgoal is missing its structural capability record")
    structural_record = CapabilityKnowledgeRecord(**structural_payload)
    candidate_path = Path(structural_record.exact_candidate)
    candidate_source = candidate_path.read_text(encoding="utf-8") if candidate_path.exists() else ""
    candidate_id = str(request.get("candidate_id") or structural_record.metrics_before_after.get("candidate_id") or "")
    evaluation_id = str(request.get("evaluation_id") or stable_id("behavioral-evaluation", structural_record.capability_id, candidate_id))
    static_self_report = _candidate_is_static_self_report(candidate_source)
    case_id = stable_id("preexisting-behavioral-case", structural_record.capability_id, "self-report-rejection")
    evidence_ref = root / "independent_behavioral_evaluation.json"
    disposition = "behaviorally_failed" if static_self_report else "insufficient_independent_evidence"
    evaluation = BehavioralEvaluationRecord(
        evaluation_id=evaluation_id,
        task_family_id=str(request.get("task_family_id") or stable_id("behavioral-task-family", structural_record.capability_id)),
        capability_id=structural_record.capability_id,
        developmental_gap_id=str(request.get("developmental_gap_id") or structural_record.capability_id),
        baseline_attempt_id=str(request.get("baseline_attempt_id") or structural_record.metrics_before_after.get("baseline") or "structural-baseline"),
        candidate_id=candidate_id,
        evaluation_protocol_version="independent_behavioral_evaluation_v1",
        task_source="preexisting_independent_candidate_behavior_contract",
        training_case_ids=(),
        sealed_or_preexisting_case_ids=(case_id,),
        control_case_ids=(stable_id("behavioral-control", structural_record.capability_id),),
        baseline_metrics={"target": 0.0},
        post_candidate_metrics={"target": 0.0 if static_self_report else 0.0},
        transfer_metrics={"target": 0.0, "threshold": 1.0},
        regression_metrics={"controls_stable": True},
        evidence_independence={
            "case_source": "preexisting",
            "candidate_generated_expected_outputs": False,
            "self_reported_success": False,
            "artifact_existence_only": False,
            "candidate_source_static_self_report": static_self_report,
            "candidate_source_digest": _digest(candidate_source),
        },
        disposition=disposition,
        evidence_refs=(str(evidence_ref), str(candidate_path)),
    )
    promoted = promote_capability_with_behavioral_evaluation(structural_record, evaluation)
    evaluation_payload = {
        "evaluation": evaluation.as_dict(),
        "candidate_path": str(candidate_path),
        "candidate_exists": candidate_path.exists(),
        "static_self_report_detected": static_self_report,
        "promotion": promoted.as_dict(),
        "tracked_source_mutated": False,
    }
    _write_json(evidence_ref, evaluation_payload)
    reassessed = consume_continuous_capability_reassessment(controller, promoted)
    next_controller = continue_continuous_mission_after_reassessment(reassessed)
    timestamps = {
        "execution_started": utc_now(),
        "independent_behavioral_evaluation_completed": utc_now(),
        "controller_handoff_completed": utc_now(),
    }
    result = SubgoalExecutionResult(
        accepted=capability_is_acquired(promoted),
        disposition=(
            "behavioral_evaluation_failed_static_self_report"
            if static_self_report
            else "behavioral_evaluation_insufficient_independent_evidence"
        ),
        reason=(
            "candidate self-reported a successful metric without exercising the claimed behavior"
            if static_self_report
            else "no independent behavioral task family was available for this structural candidate"
        ),
        subgoal_id=str(subgoal["subgoal_id"]),
        campaign_root=str(root),
        consumed_once=True,
        source_inspection={
            "candidate_path": str(candidate_path),
            "candidate_exists": candidate_path.exists(),
            "static_self_report_detected": static_self_report,
        },
        baseline={"target": 0.0, "independent": True},
        candidate={"candidate_id": candidate_id, "path": str(candidate_path)},
        validation={"passed": capability_is_acquired(promoted), "independent": True},
        clean_reproduction={"not_applicable": "behavioral evaluation reuses the prior declared candidate artifact"},
        application_request={},
        behavioral_evaluation_request=evaluation.as_dict(),
        reassessment={"capability_id": promoted.capability_id, "reassessment": promoted.reassessment},
        resource_usage=(),
        meaningful_transition_timestamps=timestamps,
        stalled_execution=False,
    )
    _write_json(result_path, result.as_dict())
    _write_json(root / "updated_restart_state_hint.json", {"controller_state": next_controller.continuous_mission_state})
    return next_controller, result


def _candidate_is_static_self_report(candidate_source: str) -> bool:
    """Detect a candidate that can only attest to its own success.

    This is deliberately structural: a literal target score in the candidate's
    own return value is never independent proof of the target behavior.
    """

    if not candidate_source:
        return False
    try:
        module = ast.parse(candidate_source)
    except SyntaxError:
        return False
    for node in ast.walk(module):
        if not isinstance(node, ast.FunctionDef) or node.name != "candidate_metric":
            continue
        for child in node.body:
            if not isinstance(child, ast.Return) or not isinstance(child.value, ast.Dict):
                continue
            entries = {
                key.value: value.value
                for key, value in zip(child.value.keys, child.value.values)
                if isinstance(key, ast.Constant) and isinstance(key.value, str) and isinstance(value, ast.Constant)
            }
            if entries.get("target_metric") == 1.0 and entries.get("tracked_source_mutated") is False:
                return True
    return False


def _result_from_previous(previous: Mapping[str, Any], *, reason: str) -> SubgoalExecutionResult:
    return SubgoalExecutionResult(
        accepted=bool(previous.get("accepted")),
        disposition="duplicate_consumption_prevented",
        reason=reason,
        subgoal_id=str(previous.get("subgoal_id") or ""),
        campaign_root=str(previous.get("campaign_root") or ""),
        consumed_once=False,
        source_inspection=dict(previous.get("source_inspection") or {}),
        baseline=dict(previous.get("baseline") or {}),
        candidate=dict(previous.get("candidate") or {}),
        validation=dict(previous.get("validation") or {}),
        clean_reproduction=dict(previous.get("clean_reproduction") or {}),
        application_request=dict(previous.get("application_request") or {}),
        behavioral_evaluation_request=dict(previous.get("behavioral_evaluation_request") or {}),
        reassessment=dict(previous.get("reassessment") or {}),
        resource_usage=(),
        meaningful_transition_timestamps=dict(previous.get("meaningful_transition_timestamps") or {}),
    )


def _local_contribution_summary(subgoal: Mapping[str, Any]) -> str:
    if _subgoal_requests_model(subgoal) or _subgoal_requests_reference(subgoal):
        return "local execution bridge candidate artifact with advisory local model/reference resource path when available"
    return "local execution bridge candidate artifact"


def _capability_id_from_subgoal(subgoal: Mapping[str, Any], candidate: Mapping[str, Any] | None = None) -> str:
    objective = str(subgoal.get("measurable_objective") or "")
    if " improves beyond " in objective:
        capability = objective.split(" improves beyond ", 1)[0].strip()
        if capability:
            return capability
    if objective:
        return stable_id("capability", objective)
    candidate = candidate or {}
    return str(subgoal.get("weakness_id") or candidate.get("candidate_id") or subgoal.get("subgoal_id") or "continuous-subgoal")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


__all__ = ["SubgoalExecutionResult", "execute_continuous_active_subgoal"]
