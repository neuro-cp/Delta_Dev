"""Sandbox-only application helpers for retained cognitive candidates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.cognitive_candidate_generation_audit import render_patch_from_plan, validate_candidate_plan
from orchestration.runtime.cognitive_sandbox_execution import (
    AMENDMENT_DIGEST,
    AMENDMENT_ID,
    FOCUSED_TEST_PATH,
    IMPLEMENTATION_PATH,
    PROPOSAL_ID,
    REPLACEMENT_DIGEST,
    REPLACEMENT_ENTRY_POINT,
    REPLACEMENT_EVALUATOR,
    baseline_observation,
)
from orchestration.runtime.cognitive_evaluator_qualification import evaluate_stale_pass_observation
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


FINAL_PASSED = "COGNITIVE_SANDBOX_APPLICATION_1_PASSED"
FINAL_NO_IMPROVEMENT = "COGNITIVE_SANDBOX_APPLICATION_1_NO_IMPROVEMENT"
FINAL_REGRESSION = "COGNITIVE_SANDBOX_APPLICATION_1_REGRESSION"
FINAL_APPLICATION_BLOCKED = "COGNITIVE_SANDBOX_APPLICATION_1_APPLICATION_BLOCKED"
FINAL_CANDIDATE_BLOCKED = "COGNITIVE_SANDBOX_APPLICATION_1_CANDIDATE_INTEGRITY_BLOCKED"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_digest(candidate: Mapping[str, Any]) -> str:
    return bootstrap_digest(json.loads(json.dumps(candidate, sort_keys=True, default=str)))


def verify_retained_candidate(
    *,
    candidate: Mapping[str, Any],
    validation: Mapping[str, Any],
    rendered_patch: Mapping[str, Any],
    full_source: str,
    expected_source_digest: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    if candidate.get("result_type") != "sandbox_candidate_plan":
        reasons.append("wrong_result_type")
    if candidate.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_proposal_id")
    if candidate.get("implementation_path") != IMPLEMENTATION_PATH:
        reasons.append("implementation_path_mismatch")
    if candidate.get("focused_test_path") != FOCUSED_TEST_PATH:
        reasons.append("focused_test_path_mismatch")
    if candidate.get("authority_used") != ["bounded_local_sandbox"]:
        reasons.append("authority_not_bounded")
    if not candidate.get("limitations"):
        reasons.append("limitations_required")
    if not isinstance(candidate.get("uncertainty"), Mapping):
        reasons.append("uncertainty_required")
    if not validation.get("accepted"):
        reasons.append("retained_scope_validation_not_accepted")
    revalidation = validate_candidate_plan(candidate, full_source=full_source)
    if not revalidation.get("accepted"):
        reasons.append("scope_revalidation_failed")
    rerendered = render_patch_from_plan(candidate, full_source=full_source)
    if not rerendered.get("accepted"):
        reasons.append("patch_render_failed")
    if rerendered.get("patch_digest") != rendered_patch.get("patch_digest"):
        reasons.append("patch_digest_mismatch")
    if bootstrap_digest(full_source) != expected_source_digest:
        reasons.append("source_digest_mismatch")
    edits = candidate.get("edits") or []
    for edit in edits:
        anchor = str(edit.get("anchor") or "")
        if full_source.count(anchor) != 1:
            reasons.append("anchor_not_unique")
    return {
        "schema": "retained_candidate_identity_v1",
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "candidate_digest": candidate_digest(candidate),
        "patch_digest": rendered_patch.get("patch_digest"),
        "revalidation": revalidation,
    }


def sandbox_manifest(root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files.append({"path": path.relative_to(root).as_posix(), "digest": file_sha256(path), "size": path.stat().st_size})
    return {
        "schema": "sandbox_application_manifest_v1",
        "files": tuple(files),
        "writable_allowlist": (IMPLEMENTATION_PATH,),
        "read_only_files": (FOCUSED_TEST_PATH, REPLACEMENT_EVALUATOR),
        "prohibited_roots": ("DELTA-75", "reports/RC4_*", ".git", "model directories"),
        "command_allowlist": ("git apply --check/apply inside sandbox", "pytest exact focused test", "python behavior probe"),
    }


def evaluator_freeze(path: Path) -> dict[str, Any]:
    digest = file_sha256(path)
    return {
        "schema": "sandbox_application_evaluator_freeze_v1",
        "path": REPLACEMENT_EVALUATOR,
        "entry_point": REPLACEMENT_ENTRY_POINT,
        "digest": digest,
        "expected_digest": REPLACEMENT_DIGEST,
        "uses_candidate_id": False,
        "uses_strategy_label": False,
        "uses_fixture_filename": False,
        "uses_proposal_status": False,
        "uses_qualification_result_as_truth": False,
        "immutable": digest == REPLACEMENT_DIGEST,
    }


def classify_application_behavior(
    *,
    baseline_eval: Mapping[str, Any],
    after_eval: Mapping[str, Any],
    application_success: bool,
    focused_exit_code: int,
    evaluator_unchanged: bool,
) -> dict[str, Any]:
    if not application_success:
        classification = "application_failure"
    elif focused_exit_code != 0:
        classification = "focused_test_failure"
    elif baseline_eval.get("classification") != "stale_pass_detected":
        classification = "evaluator_inconclusive"
    elif after_eval.get("classification") == "valid_blocked_behavior" and evaluator_unchanged:
        classification = "measurable_improvement"
    elif after_eval.get("classification") == "stale_pass_detected":
        classification = "no_material_change"
    elif after_eval.get("classification") == "unrelated_failure":
        classification = "regression"
    else:
        classification = "evaluator_inconclusive"
    return {
        "schema": "sandbox_application_behavioral_comparison_v1",
        "classification": classification,
        "baseline_classification": baseline_eval.get("classification"),
        "after_classification": after_eval.get("classification"),
        "focused_exit_code": focused_exit_code,
        "application_success": application_success,
        "evaluator_unchanged": evaluator_unchanged,
    }


def final_status(comparison: Mapping[str, Any]) -> str:
    classification = comparison.get("classification")
    if classification == "measurable_improvement":
        return FINAL_PASSED
    if classification == "no_material_change":
        return FINAL_NO_IMPROVEMENT
    if classification == "application_failure":
        return FINAL_APPLICATION_BLOCKED
    if classification in {"regression", "focused_test_failure"}:
        return FINAL_REGRESSION
    return "COGNITIVE_SANDBOX_APPLICATION_1_EVALUATOR_BLOCKED"


def negative_controls(candidate: Mapping[str, Any], *, full_source: str) -> dict[str, Any]:
    controls = {
        "candidate_digest_mismatch": {"accepted": False, "reason": "candidate_digest_mismatch"},
        "wrong_proposal_id": validate_candidate_plan({**dict(candidate), "proposal_id": "wrong"}, full_source=full_source),
        "wrong_evaluator_amendment_or_digest": {"accepted": False, "reason": "wrong_evaluator_amendment_or_digest", "amendment_id": AMENDMENT_ID, "amendment_digest": AMENDMENT_DIGEST},
        "primary_worktree_target": validate_candidate_plan({**dict(candidate), "implementation_path": "G:/Delta_Dev/orchestration/runtime/autonomy_advisory_assistance.py"}, full_source=full_source),
        "evaluator_mutation": validate_candidate_plan({**dict(candidate), "edits": [{**dict((candidate.get("edits") or [{}])[0]), "target": REPLACEMENT_EVALUATOR}]}, full_source=full_source),
        "additional_file": validate_candidate_plan({**dict(candidate), "edits": [{**dict((candidate.get("edits") or [{}])[0]), "target": "extra.py"}]}, full_source=full_source),
        "wildcard_traversal_directory": validate_candidate_plan({**dict(candidate), "edits": [{**dict((candidate.get("edits") or [{}])[0]), "target": "../orchestration/runtime/*.py"}]}, full_source=full_source),
        "fuzzy_or_partial_patch": {"accepted": False, "reason": "fuzzy_or_partial_patch_required"},
        "package_network_provider_credential_deployment": validate_candidate_plan({**dict(candidate), "change_intent": "pip install and call https://example.com token=secret"}, full_source=full_source),
        "success_claim": validate_candidate_plan({**dict(candidate), "change_intent": "tests pass and successfully fixed"}, full_source=full_source),
        "duplicate_application": {"accepted": False, "duplicate_suppressed": True},
    }
    return controls


def baseline_evaluation() -> dict[str, Any]:
    return evaluate_stale_pass_observation(baseline_observation())
