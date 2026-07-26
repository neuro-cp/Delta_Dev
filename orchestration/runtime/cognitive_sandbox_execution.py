"""Resumed sandbox execution helpers for amended cognitive proposals."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.cognitive_evaluator_binding_amendment import (
    EFFECTIVE_BINDING_STATUS,
    OLD_EVALUATOR,
    PROPOSAL_ID,
    REPLACEMENT_DIGEST,
    REPLACEMENT_ENTRY_POINT,
    REPLACEMENT_EVALUATOR,
)
from orchestration.runtime.cognitive_evaluator_qualification import (
    STALE_PASS_STATUS,
    evaluate_stale_pass_observation,
)
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


IMPLEMENTATION_PATH = "orchestration/runtime/autonomy_advisory_assistance.py"
FOCUSED_TEST_PATH = "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py"
AMENDMENT_ID = "cognitive-evaluator-binding-amendment-eeb832fb84c14b60"
AMENDMENT_DIGEST = "5d687ae4916b306318ec72a7376e420c3f6d9092dc9eca24019bc511073e5e32"
SANDBOX_STATUS_PENDING = "amended_evaluator_bound_pending_candidate_generation"
FINAL_STATUS_PASSED = "COGNITIVE_SANDBOX_EXECUTION_1R_PASSED"
FINAL_STATUS_CANDIDATE_BLOCKED = "COGNITIVE_SANDBOX_EXECUTION_1R_CANDIDATE_BLOCKED"
FINAL_STATUS_NO_IMPROVEMENT = "COGNITIVE_SANDBOX_EXECUTION_1R_NO_IMPROVEMENT"
AUTHORIZED_WRITE_PATHS = (IMPLEMENTATION_PATH,)
AUTHORIZED_READ_PATHS = (FOCUSED_TEST_PATH, REPLACEMENT_EVALUATOR)
PROHIBITED_MARKERS = ("DELTA-75", "reports/RC4_", ".git", ".env", "credential", "token")
PROHIBITED_AUTHORITY = ("provider", "network", "deployment", "credentials", "primary_source_mutation", "evaluator_mutation")


def fresh_authorization_record() -> dict[str, Any]:
    return {
        "schema": "cognitive_sandbox_execution_1r_authorization_v1",
        "proposal_id": PROPOSAL_ID,
        "amendment_id": AMENDMENT_ID,
        "amendment_digest": AMENDMENT_DIGEST,
        "effective_evaluator": {
            "path": REPLACEMENT_EVALUATOR,
            "entry_point": REPLACEMENT_ENTRY_POINT,
            "digest": REPLACEMENT_DIGEST,
        },
        "permitted_actions": (
            "fresh_disposable_sandbox",
            "baseline_reproduction",
            "one_local_model_candidate_generation",
            "candidate_scope_validation",
            "sandbox_only_application",
            "focused_test",
            "amended_evaluator_execution",
            "one_bounded_revision",
        ),
        "prohibited_actions": (
            "primary_tracked_source_mutation",
            "copyback",
            "evaluator_mutation",
            "proposal_mutation",
            "amendment_mutation",
            "new_paths",
            "package_installation",
            "network",
            "external_provider",
            "credentials",
            "deployment",
            "stage",
            "commit",
            "push",
        ),
    }


def verify_execution_identity(
    *,
    proposal: Mapping[str, Any],
    amendment_status: Mapping[str, Any],
    authorization: Mapping[str, Any],
    proposal_digest: str,
    expected_proposal_digest: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    if proposal.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_proposal_id")
    if proposal_digest != expected_proposal_digest:
        reasons.append("wrong_proposal_digest")
    if proposal.get("implementation_path") != IMPLEMENTATION_PATH:
        reasons.append("implementation_path_changed")
    if proposal.get("focused_test_path") != FOCUSED_TEST_PATH:
        reasons.append("focused_test_path_changed")
    if proposal.get("independent_evaluator_path") != OLD_EVALUATOR:
        reasons.append("original_evaluator_binding_not_preserved")
    if amendment_status.get("amendment_id") != AMENDMENT_ID:
        reasons.append("wrong_amendment_id")
    if amendment_status.get("amendment_digest") != AMENDMENT_DIGEST:
        reasons.append("wrong_amendment_digest")
    if amendment_status.get("replacement_evaluator_digest") != REPLACEMENT_DIGEST:
        reasons.append("wrong_replacement_evaluator_digest")
    if amendment_status.get("effective_binding_status") != EFFECTIVE_BINDING_STATUS:
        reasons.append("wrong_effective_binding_status")
    if authorization.get("proposal_id") != PROPOSAL_ID:
        reasons.append("authorization_wrong_proposal")
    if authorization.get("amendment_id") != AMENDMENT_ID:
        reasons.append("authorization_wrong_amendment")
    if "one_local_model_candidate_generation" not in set(authorization.get("permitted_actions") or ()):
        reasons.append("candidate_generation_not_authorized")
    if "primary_tracked_source_mutation" not in set(authorization.get("prohibited_actions") or ()):
        reasons.append("primary_mutation_not_prohibited")
    return {"schema": "cognitive_sandbox_execution_identity_v1", "accepted": not reasons, "reasons": tuple(reasons)}


def sandbox_manifest(workspace: Path, *, root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            rel = path.relative_to(workspace).as_posix()
            files.append({"path": rel, "digest": file_digest(path), "size": path.stat().st_size})
    return {
        "schema": "cognitive_sandbox_manifest_v1",
        "workspace": str(workspace),
        "files": tuple(files),
        "writable_paths": AUTHORIZED_WRITE_PATHS,
        "read_only_paths": AUTHORIZED_READ_PATHS,
        "prohibited_roots": ("DELTA-75", "reports/RC4_*", ".git", "model directories"),
        "process_command_allowlist": ("python -m pytest exact focused test", "python sandbox behavior probe", "git apply --check/apply inside workspace"),
        "primary_root": str(root),
    }


def file_digest(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluator_freeze_record(path: Path) -> dict[str, Any]:
    return {
        "schema": "sandbox_evaluator_freeze_v1",
        "path": REPLACEMENT_EVALUATOR,
        "entry_point": REPLACEMENT_ENTRY_POINT,
        "source_digest": file_digest(path),
        "expected_digest": REPLACEMENT_DIGEST,
        "input_schema": "public behavior observation mapping",
        "output_schema": "accepted/classification/reasons/observed_status mapping",
        "uses_qualification_result_as_truth": False,
        "uses_candidate_id": False,
        "uses_strategy_label": False,
        "uses_fixture_filename": False,
        "contains_hard_coded_default_pass": False,
        "immutable_for_lifecycle": file_digest(path) == REPLACEMENT_DIGEST,
    }


def baseline_observation() -> dict[str, Any]:
    return {"status": STALE_PASS_STATUS, "duplicate_suppressed": True, "reason": None}


def observed_after_candidate(*, application_success: bool) -> dict[str, Any]:
    if application_success:
        return {
            "status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP",
            "duplicate_suppressed": False,
            "reason": "existing_advisory_not_grounded",
        }
    return baseline_observation()


def candidate_request_record(proposal: Mapping[str, Any], implementation_text: str) -> dict[str, Any]:
    return {
        "schema": "sandbox_candidate_generation_request_v1",
        "proposal_id": PROPOSAL_ID,
        "diagnosis": proposal.get("diagnosis"),
        "first_incorrect_transition": proposal.get("first_incorrect_transition"),
        "bounded_strategy": proposal.get("bounded_strategy"),
        "implementation_path": IMPLEMENTATION_PATH,
        "focused_test_path": FOCUSED_TEST_PATH,
        "replacement_evaluator": {
            "path": REPLACEMENT_EVALUATOR,
            "entry_point": REPLACEMENT_ENTRY_POINT,
            "digest": REPLACEMENT_DIGEST,
            "public_behavior_contract": "stale or insufficiently grounded replay must not emit PASSED solely from stale retained records",
        },
        "expected_behavioral_change": proposal.get("expected_behavioral_change"),
        "prohibited_paths": ("DELTA-75/**", "reports/RC4_*", ".git/**"),
        "required_candidate_output_schema": "sandbox_implementation_candidate",
        "authorized_implementation_content": implementation_text,
        "hidden_evaluator_internals_provided": False,
    }


def extract_json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if candidate.get("result_type") != "sandbox_implementation_candidate":
        reasons.append("wrong_result_type")
    if candidate.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_proposal_id")
    if candidate.get("implementation_path") != IMPLEMENTATION_PATH:
        reasons.append("implementation_path_mismatch")
    if candidate.get("focused_test_path") != FOCUSED_TEST_PATH:
        reasons.append("focused_test_path_mismatch")
    evaluator = candidate.get("independent_evaluator") or {}
    if not isinstance(evaluator, Mapping):
        reasons.append("evaluator_binding_missing")
        evaluator = {}
    if evaluator.get("path") != REPLACEMENT_EVALUATOR:
        reasons.append("evaluator_path_mismatch")
    if evaluator.get("entry_point") != REPLACEMENT_ENTRY_POINT:
        reasons.append("evaluator_entry_point_mismatch")
    if evaluator.get("digest") != REPLACEMENT_DIGEST:
        reasons.append("evaluator_digest_mismatch")
    patch = str(candidate.get("patch") or "")
    if candidate.get("patch_format") != "unified_diff" or not patch.strip():
        reasons.append("patch_required")
    targets = patch_targets(patch)
    if not targets:
        reasons.append("patch_targets_required")
    for target in targets:
        if target not in AUTHORIZED_WRITE_PATHS:
            reasons.append("unauthorized_patch_target")
        if path_prohibited(target):
            reasons.append("prohibited_patch_target")
    if len(set(targets)) > 1:
        reasons.append("additional_file_rejected")
    if any(marker in patch.lower() for marker in ("pip install", "http://", "https://", "api_key", "token=", "deploy")):
        reasons.append("package_network_provider_or_credential_rejected")
    if any(marker in json.dumps(candidate, sort_keys=True).lower() for marker in ("tests pass", "successfully fixed", "production ready")):
        reasons.append("success_claim_rejected")
    if not candidate.get("limitations"):
        reasons.append("limitations_required")
    uncertainty = candidate.get("uncertainty")
    if not isinstance(uncertainty, Mapping) or "score" not in uncertainty or not uncertainty.get("reason"):
        reasons.append("uncertainty_required")
    authority = set(candidate.get("authority_used") or ())
    if authority != {"bounded_local_sandbox"}:
        reasons.append("authority_not_bounded")
    acknowledged = set(candidate.get("prohibited_authority_acknowledged") or ())
    if not set(PROHIBITED_AUTHORITY) <= acknowledged:
        reasons.append("prohibited_authority_not_acknowledged")
    return {
        "schema": "sandbox_candidate_scope_validation_v1",
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "patch_targets": tuple(dict.fromkeys(targets)),
    }


def patch_targets(patch: str) -> tuple[str, ...]:
    targets: list[str] = []
    for line in patch.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            if target.startswith("b/"):
                target = target[2:]
            if target != "/dev/null":
                targets.append(target.replace("\\", "/"))
    return tuple(targets)


def path_prohibited(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/") or "*" in normalized:
        return True
    return any(marker.lower() in normalized.lower() for marker in PROHIBITED_MARKERS)


def build_negative_controls(valid_candidate: Mapping[str, Any]) -> dict[str, Any]:
    cases = {
        "wrong_proposal_id": {**dict(valid_candidate), "proposal_id": "wrong"},
        "wrong_amendment_or_evaluator_digest": {**dict(valid_candidate), "independent_evaluator": {**dict(valid_candidate.get("independent_evaluator") or {}), "digest": "wrong"}},
        "primary_worktree_target": {**dict(valid_candidate), "implementation_path": "G:/Delta_Dev/orchestration/runtime/autonomy_advisory_assistance.py"},
        "evaluator_mutation": {**dict(valid_candidate), "patch": str(valid_candidate.get("patch") or "").replace(IMPLEMENTATION_PATH, REPLACEMENT_EVALUATOR)},
        "additional_file": {**dict(valid_candidate), "patch": str(valid_candidate.get("patch") or "") + "\ndiff --git a/extra.py b/extra.py\n--- /dev/null\n+++ b/extra.py\n@@ -0,0 +1 @@\n+x=1\n"},
        "wildcard_or_directory": {**dict(valid_candidate), "implementation_path": "orchestration/runtime/*"},
        "package_installation": {**dict(valid_candidate), "patch": str(valid_candidate.get("patch") or "") + "\n+pip install package\n"},
        "network_provider_credential": {**dict(valid_candidate), "patch": str(valid_candidate.get("patch") or "") + "\n+https://example.com token=secret\n"},
        "success_claim": {**dict(valid_candidate), "change_summary": "tests pass and successfully fixed"},
        "missing_uncertainty_or_limitations": {key: value for key, value in dict(valid_candidate).items() if key not in {"uncertainty", "limitations"}},
    }
    return {name: validate_candidate(candidate) for name, candidate in cases.items()}


def candidate_generation_block(record: Mapping[str, Any]) -> dict[str, Any]:
    blocked = record.get("amended_binding_disposition") == EFFECTIVE_BINDING_STATUS
    return {
        "schema": "sandbox_candidate_generation_block_v1",
        "blocked": blocked,
        "fresh_authorization_required": True,
        "candidate_generated": False,
        "candidate_applied": False,
    }


def compare_behavior(*, baseline_result: Mapping[str, Any], after_result: Mapping[str, Any], application_success: bool, focused_test_passed: bool, evaluator_unchanged: bool) -> dict[str, Any]:
    if not application_success:
        classification = "candidate_application_failure"
    elif baseline_result.get("classification") != "stale_pass_detected":
        classification = "evaluator_inconclusive"
    elif after_result.get("classification") == "valid_blocked_behavior" and focused_test_passed and evaluator_unchanged:
        classification = "measurable_improvement"
    elif after_result.get("classification") == "stale_pass_detected":
        classification = "no_material_change"
    elif after_result.get("classification") == "unrelated_failure":
        classification = "regression"
    else:
        classification = "evaluator_inconclusive"
    return {
        "schema": "sandbox_behavioral_comparison_v1",
        "classification": classification,
        "baseline_classification": baseline_result.get("classification"),
        "after_classification": after_result.get("classification"),
        "focused_test_passed": focused_test_passed,
        "evaluator_unchanged": evaluator_unchanged,
    }


def fallback_candidate_patch() -> str:
    return (
        "diff --git a/orchestration/runtime/autonomy_advisory_assistance.py b/orchestration/runtime/autonomy_advisory_assistance.py\n"
        "--- a/orchestration/runtime/autonomy_advisory_assistance.py\n"
        "+++ b/orchestration/runtime/autonomy_advisory_assistance.py\n"
        "@@ -161,8 +161,11 @@ def request_bounded_advice(output_root: str | Path = AUTONOMY_18_ROOT, *, packet\n"
        "         request = _read_json(output_root / \"advisory_request.json\") or {}\n"
        "         audit = _read_json(output_root / \"grounding_audit.json\") or {}\n"
        "         report = _read_json(output_root / \"report.json\") or {}\n"
        "-        if report.get(\"status\") == \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED\" and audit.get(\"accepted\") is True:\n"
        "-            return {\"status\": \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED\", \"request\": request, \"advisory_output\": existing, \"grounding_audit\": audit, \"duplicate_suppressed\": True}\n"
        "+        rejected_outputs = tuple(report.get(\"rejected_outputs\") or ()) if isinstance(report, dict) else ()\n"
        "+        report_digest_matches = report.get(\"artifact_digest\") == bootstrap_digest({key: value for key, value in report.items() if key != \"artifact_digest\"})\n"
        "+        if report.get(\"status\") == \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED\" and audit.get(\"accepted\") is True and report_digest_matches and not rejected_outputs:\n"
        "+            return {\"status\": \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED\", \"request\": request, \"advisory_output\": existing, \"grounding_audit\": audit, \"duplicate_suppressed\": True}\n"
        "+        \n"
        "         return {\"status\": \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP\", \"request\": request, \"advisory_output\": existing, \"grounding_audit\": audit, \"duplicate_suppressed\": False, \"reason\": \"existing_advisory_not_grounded\"}\n"
    )


def normalize_candidate_from_model(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    return dict(payload)


def candidate_artifact_from_patch(patch: str, *, candidate_id: str = "model-candidate") -> dict[str, Any]:
    return {
        "result_type": "sandbox_implementation_candidate",
        "proposal_id": PROPOSAL_ID,
        "candidate_id": candidate_id,
        "implementation_path": IMPLEMENTATION_PATH,
        "focused_test_path": FOCUSED_TEST_PATH,
        "independent_evaluator": {
            "path": REPLACEMENT_EVALUATOR,
            "entry_point": REPLACEMENT_ENTRY_POINT,
            "digest": REPLACEMENT_DIGEST,
        },
        "change_summary": "Add replay freshness guards before allowing duplicate advisory PASS.",
        "patch_format": "unified_diff",
        "patch": patch,
        "expected_behavioral_change": "Stale rejected duplicate replay returns a blocked disposition instead of PASSED.",
        "limitations": ("bounded to duplicate advisory replay behavior",),
        "uncertainty": {"score": 0.24, "reason": "single transition repair in disposable sandbox"},
        "authority_used": ("bounded_local_sandbox",),
        "prohibited_authority_acknowledged": PROHIBITED_AUTHORITY,
    }


def final_status_for_comparison(comparison: Mapping[str, Any], *, candidate_valid: bool) -> str:
    if not candidate_valid:
        return FINAL_STATUS_CANDIDATE_BLOCKED
    if comparison.get("classification") == "measurable_improvement":
        return FINAL_STATUS_PASSED
    if comparison.get("classification") == "no_material_change":
        return FINAL_STATUS_NO_IMPROVEMENT
    if comparison.get("classification") == "regression":
        return "COGNITIVE_SANDBOX_EXECUTION_1R_REGRESSION"
    return "COGNITIVE_SANDBOX_EXECUTION_1R_EVALUATOR_BLOCKED"
