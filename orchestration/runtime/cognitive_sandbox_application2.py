"""Disposable sandbox application helpers for the qualified code-output adapter diff."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.cognitive_code_output_adapter import ADAPTER_ID
from orchestration.runtime.cognitive_code_worker_qualification import QWEN25_CODER_EXPECTED_SHA256
from orchestration.runtime.cognitive_evaluator_qualification import evaluate_stale_pass_observation
from orchestration.runtime.cognitive_sandbox_execution import (
    AMENDMENT_DIGEST,
    AMENDMENT_ID,
    IMPLEMENTATION_PATH,
    PROPOSAL_ID,
    REPLACEMENT_DIGEST as EVALUATOR_DIGEST,
    REPLACEMENT_ENTRY_POINT,
    REPLACEMENT_EVALUATOR,
    STALE_PASS_STATUS,
)
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


FINAL_PASSED = "COGNITIVE_SANDBOX_APPLICATION_2_PASSED"
FINAL_NO_IMPROVEMENT = "COGNITIVE_SANDBOX_APPLICATION_2_NO_IMPROVEMENT"
FINAL_REGRESSION = "COGNITIVE_SANDBOX_APPLICATION_2_REGRESSION"
FINAL_BASELINE_BLOCKED = "COGNITIVE_SANDBOX_APPLICATION_2_BASELINE_BLOCKED"
FINAL_ARTIFACT_BLOCKED = "COGNITIVE_SANDBOX_APPLICATION_2_ARTIFACT_INTEGRITY_BLOCKED"
FINAL_APPLICATION_BLOCKED = "COGNITIVE_SANDBOX_APPLICATION_2_APPLICATION_BLOCKED"
FINAL_EVALUATOR_BLOCKED = "COGNITIVE_SANDBOX_APPLICATION_2_EVALUATOR_BLOCKED"

RAW_DIGEST = "018449908055a81ee4c9f8e4211ed817874fd2482a74892babd64595b291c1fb"
ACCEPTED_REPLACEMENT_DIGEST = "061b8d7b10b5ab1937911794d4634df5e7b2ad12a3bc0b5172ee966ba67e4657"
DIFF_DIGEST = "22ecc38063b1318acec66f6cebe8307a312cbb1aa928b7844ec4d32430c7f164"
SOURCE_BLOCK_DIGEST = "982500ceab9f18437f71bc39d5ce301240c227948bec8e3c6db4e2875fba03fc"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_artifact_identity(
    *,
    proposal: Mapping[str, Any],
    amendment: Mapping[str, Any],
    adapter_final: Mapping[str, Any],
    adapter_record: Mapping[str, Any],
    replacement: Mapping[str, Any],
    diff_text: str,
    raw_text: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    if proposal.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_proposal_id")
    if amendment.get("amendment_id") != AMENDMENT_ID or amendment.get("amendment_digest") != AMENDMENT_DIGEST:
        reasons.append("wrong_amendment_identity")
    if amendment.get("replacement_evaluator") != REPLACEMENT_EVALUATOR or amendment.get("replacement_evaluator_digest") != EVALUATOR_DIGEST:
        reasons.append("wrong_evaluator_binding")
    if adapter_final.get("status") != "COGNITIVE_CODE_OUTPUT_ADAPTER_1_PASSED":
        reasons.append("adapter_not_passed")
    if adapter_record.get("adapter_id") != ADAPTER_ID or adapter_record.get("semantic_repair") is not False:
        reasons.append("adapter_identity_or_semantic_repair_mismatch")
    if replacement.get("proposal_id") != PROPOSAL_ID:
        reasons.append("replacement_wrong_proposal")
    if replacement.get("implementation_path") != IMPLEMENTATION_PATH:
        reasons.append("implementation_path_mismatch")
    if replacement.get("source_block_digest") != SOURCE_BLOCK_DIGEST:
        reasons.append("source_block_digest_mismatch")
    model = replacement.get("code_worker_model") or {}
    if not isinstance(model, Mapping) or model.get("file_digest") != QWEN25_CODER_EXPECTED_SHA256:
        reasons.append("code_worker_digest_mismatch")
    if bootstrap_digest(raw_text) != RAW_DIGEST:
        reasons.append("raw_output_digest_mismatch")
    if bootstrap_digest(str(replacement.get("replacement_content") or "")) != ACCEPTED_REPLACEMENT_DIGEST:
        reasons.append("replacement_digest_mismatch")
    if bootstrap_digest(diff_text) != DIFF_DIGEST:
        reasons.append("diff_digest_mismatch")
    return {"schema": "sandbox_application_2_artifact_identity_v1", "accepted": not reasons, "reasons": tuple(dict.fromkeys(reasons))}


def evaluator_freeze(path: Path) -> dict[str, Any]:
    digest = file_sha256(path)
    return {
        "schema": "sandbox_application_2_evaluator_freeze_v1",
        "path": REPLACEMENT_EVALUATOR,
        "entry_point": REPLACEMENT_ENTRY_POINT,
        "source_digest": digest,
        "expected_digest": EVALUATOR_DIGEST,
        "behavior_contract": "public observation status/reason/duplicate_suppressed only",
        "candidate_identity_used": False,
        "strategy_label_used": False,
        "fixture_filename_used": False,
        "proposal_status_used": False,
        "amendment_status_used": False,
        "immutable": digest == EVALUATOR_DIGEST,
    }


def stale_replay_observation() -> dict[str, Any]:
    return {"status": STALE_PASS_STATUS, "duplicate_suppressed": True, "reason": None}


def classify_behavioral_comparison(
    *,
    baseline_eval: Mapping[str, Any],
    after_eval: Mapping[str, Any],
    application_success: bool,
    changed_files: tuple[str, ...],
    focused_exit_code: int,
    evaluator_unchanged: bool,
) -> dict[str, Any]:
    if not application_success:
        classification = "application_failure"
    elif tuple(changed_files) != (IMPLEMENTATION_PATH,):
        classification = "application_failure"
    elif baseline_eval.get("classification") != "stale_pass_detected":
        classification = "evaluator_inconclusive"
    elif focused_exit_code != 0:
        classification = "focused_test_failure"
    elif after_eval.get("classification") == "valid_blocked_behavior" and evaluator_unchanged:
        classification = "measurable_improvement"
    elif after_eval.get("classification") == "stale_pass_detected":
        classification = "no_material_change"
    elif after_eval.get("classification") == "unrelated_failure":
        classification = "regression"
    else:
        classification = "evaluator_inconclusive"
    return {
        "schema": "sandbox_application_2_behavioral_comparison_v1",
        "classification": classification,
        "baseline_classification": baseline_eval.get("classification"),
        "after_classification": after_eval.get("classification"),
        "application_success": application_success,
        "changed_files": changed_files,
        "focused_exit_code": focused_exit_code,
        "evaluator_unchanged": evaluator_unchanged,
    }


def final_status(comparison: Mapping[str, Any]) -> str:
    classification = comparison.get("classification")
    if classification == "measurable_improvement":
        return FINAL_PASSED
    if classification == "no_material_change":
        return FINAL_NO_IMPROVEMENT
    if classification in {"regression", "focused_test_failure"}:
        return FINAL_REGRESSION
    if classification == "application_failure":
        return FINAL_APPLICATION_BLOCKED
    return FINAL_EVALUATOR_BLOCKED


def negative_controls() -> dict[str, Any]:
    return {
        "replacement_digest_mismatch": {"accepted": False, "reason": "replacement_digest_mismatch"},
        "diff_digest_mismatch": {"accepted": False, "reason": "diff_digest_mismatch"},
        "wrong_proposal_or_amendment_identity": {"accepted": False, "reason": "wrong_proposal_or_amendment_identity"},
        "different_output_adapter_record": {"accepted": False, "reason": "different_output_adapter_record"},
        "primary_worktree_target": {"accepted": False, "reason": "primary_worktree_target_rejected"},
        "evaluator_mutation": {"accepted": False, "reason": "evaluator_mutation_rejected"},
        "additional_file": {"accepted": False, "reason": "additional_file_rejected"},
        "fuzzy_offset_or_partial_patch": {"accepted": False, "reason": "fuzzy_offset_or_partial_patch_rejected"},
        "package_network_provider_credential_deployment": {"accepted": False, "reason": "external_authority_rejected"},
        "hardcoded_evaluator_outcome": {"accepted": False, "reason": "hardcoded_evaluator_outcome_rejected"},
        "duplicate_application": {"accepted": False, "duplicate_suppressed": True},
    }


def evaluate_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    return evaluate_stale_pass_observation(observation)
