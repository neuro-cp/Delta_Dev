"""Non-applying candidate revision helpers for exact sandbox patch checks."""
from __future__ import annotations

import difflib
import json
from typing import Any, Mapping

from orchestration.runtime.cognitive_sandbox_execution import FOCUSED_TEST_PATH, IMPLEMENTATION_PATH, PROPOSAL_ID, path_prohibited
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


RETAINED_CANDIDATE_DIGEST = "2cdd4426d68d3cbe476546307c40a8b46c6f2b0fef07cb4d407faf0f6f49eba4"
VALID_OPS = {"replace_block", "insert_before", "insert_after"}


def classify_patch_failure(*, stderr: str, anchor_count: int, source_digest_matches: bool) -> dict[str, Any]:
    text = str(stderr or "").lower()
    if not source_digest_matches:
        label = "stale_source_digest"
    elif anchor_count == 0:
        label = "anchor_not_found"
    elif anchor_count > 1:
        label = "anchor_not_unique"
    elif "patch does not apply" in text:
        label = "insufficient_patch_context"
    elif "corrupt patch" in text:
        label = "invalid_hunk_header"
    else:
        label = "unknown_application_failure"
    return {"schema": "candidate_revision_failure_classification_v1", "classification": label, "stderr": stderr, "anchor_count": anchor_count, "source_digest_matches": source_digest_matches}


def validate_revised_candidate(candidate: Mapping[str, Any], *, full_source: str) -> dict[str, Any]:
    reasons: list[str] = []
    if candidate.get("result_type") != "sandbox_candidate_plan":
        reasons.append("wrong_result_type")
    if candidate.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_proposal_id")
    if candidate.get("revises_candidate_digest") != RETAINED_CANDIDATE_DIGEST:
        reasons.append("wrong_prior_candidate_digest")
    if candidate.get("implementation_path") != IMPLEMENTATION_PATH:
        reasons.append("implementation_path_mismatch")
    if candidate.get("focused_test_path") != FOCUSED_TEST_PATH:
        reasons.append("focused_test_path_mismatch")
    if set(candidate.get("authority_used") or ()) != {"bounded_local_sandbox"}:
        reasons.append("authority_not_bounded")
    if not candidate.get("limitations"):
        reasons.append("limitations_required")
    uncertainty = candidate.get("uncertainty")
    if not isinstance(uncertainty, Mapping) or "score" not in uncertainty or not uncertainty.get("reason"):
        reasons.append("uncertainty_required")
    edits = candidate.get("edits")
    if not isinstance(edits, list) or not edits:
        reasons.append("edits_required")
        edits = []
    for edit in edits:
        if not isinstance(edit, Mapping):
            reasons.append("edit_invalid")
            continue
        target = str(edit.get("target") or "")
        if target != IMPLEMENTATION_PATH or path_prohibited(target):
            reasons.append("unauthorized_target")
        if edit.get("operation") not in VALID_OPS:
            reasons.append("unsupported_operation")
        anchor = str(edit.get("anchor") or "")
        if not anchor:
            reasons.append("anchor_required")
        if "..." in anchor:
            reasons.append("approximate_anchor_rejected")
        if anchor.strip().isdigit() or anchor.lower().startswith("line "):
            reasons.append("line_number_anchor_rejected")
        count = full_source.count(anchor) if anchor else 0
        if count == 0:
            reasons.append("anchor_not_found")
        elif count > 1:
            reasons.append("anchor_not_unique")
        if edit.get("expected_anchor_count") != count:
            reasons.append("expected_anchor_count_mismatch")
        if not str(edit.get("replacement") or "").strip():
            reasons.append("replacement_required")
    text = json.dumps(candidate, sort_keys=True).lower()
    if any(marker in text for marker in ("delta-75", "reports/rc4_", "../", "http://", "https://", "pip install", "token=", "api_key", "deploy")):
        reasons.append("prohibited_content")
    if any(marker in text for marker in ("tests pass", "successfully fixed", "production ready")):
        reasons.append("success_claim_rejected")
    return {"schema": "revised_candidate_validation_v1", "accepted": not reasons, "reasons": tuple(dict.fromkeys(reasons))}


def render_revised_patch(candidate: Mapping[str, Any], *, full_source: str) -> dict[str, Any]:
    validation = validate_revised_candidate(candidate, full_source=full_source)
    if not validation["accepted"]:
        return {"schema": "revised_patch_render_v1", "accepted": False, "reason": "candidate_invalid", "validation": validation}
    proposed = full_source
    for edit in candidate.get("edits") or ():
        anchor = str(edit["anchor"])
        repl = str(edit["replacement"])
        op = str(edit["operation"])
        if proposed.count(anchor) != 1:
            return {"schema": "revised_patch_render_v1", "accepted": False, "reason": "anchor_not_unique_at_render"}
        if op == "replace_block":
            proposed = proposed.replace(anchor, repl, 1)
        elif op == "insert_before":
            proposed = proposed.replace(anchor, repl + "\n" + anchor, 1)
        else:
            proposed = proposed.replace(anchor, anchor + "\n" + repl, 1)
    diff = "".join(difflib.unified_diff(
        full_source.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile=f"a/{IMPLEMENTATION_PATH}",
        tofile=f"b/{IMPLEMENTATION_PATH}",
    ))
    return {
        "schema": "revised_patch_render_v1",
        "accepted": bool(diff),
        "patch": diff,
        "patch_digest": bootstrap_digest(diff),
        "original_source_digest": bootstrap_digest(full_source),
        "proposed_source_digest": bootstrap_digest(proposed),
        "hunk_count": sum(1 for line in diff.splitlines() if line.startswith("@@")),
        "target": IMPLEMENTATION_PATH,
        "source_modified": False,
    }


def negative_controls(valid: Mapping[str, Any], *, full_source: str) -> dict[str, Any]:
    edit = dict((valid.get("edits") or [{}])[0])
    controls = {
        "wrong_prior_candidate_digest": {**dict(valid), "revises_candidate_digest": "wrong"},
        "anchor_absent": {**dict(valid), "edits": [{**edit, "anchor": "not present", "expected_anchor_count": 1}]},
        "anchor_multiple": {**dict(valid), "edits": [{**edit, "anchor": "return", "expected_anchor_count": full_source.count("return")}]},
        "ellipsis_anchor": {**dict(valid), "edits": [{**edit, "anchor": "if ... accepted", "expected_anchor_count": 1}]},
        "line_number_anchor": {**dict(valid), "edits": [{**edit, "anchor": "line 214", "expected_anchor_count": 1}]},
        "additional_path": {**dict(valid), "edits": [{**edit, "target": "extra.py"}]},
        "evaluator_mutation": {**dict(valid), "edits": [{**edit, "target": "orchestration/runtime/cognitive_evaluator_qualification.py"}]},
        "source_digest_mismatch": {"accepted": False, "reason": "source_digest_mismatch"},
        "success_claim": {**dict(valid), "change_intent": "tests pass and successfully fixed"},
        "missing_uncertainty_or_limitations": {k: v for k, v in dict(valid).items() if k not in {"uncertainty", "limitations"}},
    }
    return {name: validate_revised_candidate(case, full_source=full_source) if isinstance(case, Mapping) and "result_type" in case else case for name, case in controls.items()}
