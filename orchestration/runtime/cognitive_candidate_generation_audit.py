"""Candidate-generation audit helpers for non-applying cognitive sandbox probes."""
from __future__ import annotations

import difflib
import json
from typing import Any, Mapping, Sequence

from orchestration.runtime.cognitive_sandbox_execution import (
    FOCUSED_TEST_PATH,
    IMPLEMENTATION_PATH,
    PROPOSAL_ID,
    PROHIBITED_AUTHORITY,
    REPLACEMENT_DIGEST,
    REPLACEMENT_ENTRY_POINT,
    REPLACEMENT_EVALUATOR,
    path_prohibited,
)
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


CANDIDATE_PLAN_SCHEMA = "sandbox_candidate_plan_v1"
VALID_OPERATIONS = {"replace_block", "insert_before", "insert_after"}


def compact_candidate_schema() -> dict[str, Any]:
    return {
        "result_type": "sandbox_candidate_plan",
        "proposal_id": PROPOSAL_ID,
        "candidate_id": "string",
        "implementation_path": IMPLEMENTATION_PATH,
        "focused_test_path": FOCUSED_TEST_PATH,
        "change_intent": "string",
        "edits": [{
            "target": IMPLEMENTATION_PATH,
            "operation": "replace_block | insert_before | insert_after",
            "anchor": "exact short source anchor",
            "replacement": "model supplied replacement string",
            "purpose": "string",
        }],
        "expected_behavioral_change": "string",
        "limitations": ["string"],
        "uncertainty": {"score": 0.0, "reason": "string"},
        "authority_used": ["bounded_local_sandbox"],
    }


def classify_timeout_phase(events: Sequence[Mapping[str, Any]], *, process_alive_after_timeout: bool, forced_termination: bool) -> dict[str, Any]:
    names = tuple(str(event.get("event") or "") for event in events)
    if "backend_returned" in names:
        classification = "backend_returned"
    elif "first_token" in names:
        classification = "timed_out_during_generation"
    elif "prompt_processing_started" in names or "load_done" in names:
        classification = "timed_out_before_first_token"
    elif "load_started" in names:
        classification = "prompt_processing_timeout_or_model_load_timeout"
    else:
        classification = "backend_call_hung"
    if forced_termination:
        cleanup = "process_required_forced_termination"
    elif process_alive_after_timeout:
        cleanup = "process_cancel_status_unknown"
    else:
        cleanup = "process_cancelled_cleanly"
    return {
        "schema": "candidate_timeout_phase_v1",
        "classification": classification,
        "events": names,
        "process_alive_after_timeout": process_alive_after_timeout,
        "forced_termination": forced_termination,
        "cleanup": cleanup,
    }


def contract_audit(candidate_schema: Mapping[str, Any], *, prompt_characters: int, source_characters: int) -> dict[str, Any]:
    text = json.dumps(candidate_schema, sort_keys=True)
    flags = {
        "requires_unified_diff_inside_json": "patch" in text and "unified" in text.lower(),
        "requires_escaped_newlines": "\\n" in text or "patch" in text,
        "nested_evaluator_metadata": "independent_evaluator" in text,
        "repeated_authority_lists": text.count("authority") > 2,
        "large_source_content": source_characters > 4000,
        "large_prompt": prompt_characters > 8000,
    }
    return {
        "schema": "candidate_contract_audit_v1",
        "serialization_complexity": flags,
        "deterministically_attachable_fields": (
            "independent_evaluator",
            "proposal_digest",
            "amendment_digest",
            "prohibited_authority_acknowledged",
        ),
        "model_required_fields": (
            "candidate_id",
            "change_intent",
            "edits",
            "expected_behavioral_change",
            "limitations",
            "uncertainty",
        ),
        "recommendation": "use_compact_candidate_plan_then_deterministic_patch_render",
    }


def source_window(source: str, *, anchor: str, before: int = 12, after: int = 18) -> dict[str, Any]:
    lines = source.splitlines()
    matches = [index for index, line in enumerate(lines) if anchor in line]
    if not matches:
        return {"schema": "source_window_v1", "accepted": False, "reason": "anchor_not_found"}
    index = matches[0]
    start = max(0, index - before)
    end = min(len(lines), index + after + 1)
    window = "\n".join(lines[start:end])
    return {
        "schema": "source_window_v1",
        "accepted": True,
        "anchor": anchor,
        "anchor_match_count": len(matches),
        "start_line": start + 1,
        "end_line": end,
        "text": window,
        "source_window_digest": bootstrap_digest(window),
        "full_source_digest": bootstrap_digest(source),
        "validatable_against_full_file": len(matches) == 1,
    }


def validate_candidate_plan(plan: Mapping[str, Any], *, full_source: str) -> dict[str, Any]:
    reasons: list[str] = []
    if plan.get("result_type") != "sandbox_candidate_plan":
        reasons.append("wrong_result_type")
    if plan.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_or_missing_proposal_id")
    if plan.get("implementation_path") != IMPLEMENTATION_PATH:
        reasons.append("implementation_path_mismatch")
    if plan.get("focused_test_path") != FOCUSED_TEST_PATH:
        reasons.append("focused_test_path_mismatch")
    if not plan.get("candidate_id"):
        reasons.append("candidate_id_required")
    edits = plan.get("edits")
    if not isinstance(edits, list) or not edits:
        reasons.append("edits_required")
        edits = []
    for edit in edits:
        if not isinstance(edit, Mapping):
            reasons.append("edit_invalid")
            continue
        target = str(edit.get("target") or "")
        if target != IMPLEMENTATION_PATH:
            reasons.append("unauthorized_edit_target")
        if path_prohibited(target):
            reasons.append("prohibited_edit_target")
        if edit.get("operation") not in VALID_OPERATIONS:
            reasons.append("unsupported_operation")
        anchor = str(edit.get("anchor") or "")
        if not anchor:
            reasons.append("anchor_required")
        elif full_source.count(anchor) == 0:
            reasons.append("anchor_not_found")
        elif full_source.count(anchor) > 1:
            reasons.append("anchor_not_unique")
        if not str(edit.get("replacement") or "").strip():
            reasons.append("replacement_required")
        if not str(edit.get("purpose") or "").strip():
            reasons.append("purpose_required")
    text = json.dumps(plan, sort_keys=True).lower()
    if any(marker in text for marker in ("delta-75", "reports/rc4_", "../", "http://", "https://", "pip install", "api_key", "token=", "deploy")):
        reasons.append("prohibited_path_or_authority")
    if any(marker in text for marker in ("tests pass", "successfully fixed", "production ready")):
        reasons.append("success_claim_rejected")
    if set(plan.get("authority_used") or ()) != {"bounded_local_sandbox"}:
        reasons.append("authority_not_bounded")
    if not plan.get("limitations"):
        reasons.append("limitations_required")
    uncertainty = plan.get("uncertainty")
    if not isinstance(uncertainty, Mapping) or "score" not in uncertainty or not uncertainty.get("reason"):
        reasons.append("uncertainty_required")
    return {
        "schema": "candidate_plan_validation_v1",
        "accepted": not reasons,
        "classification": "candidate_scope_valid" if not reasons else "candidate_scope_invalid",
        "reasons": tuple(dict.fromkeys(reasons)),
    }


def render_patch_from_plan(plan: Mapping[str, Any], *, full_source: str) -> dict[str, Any]:
    validation = validate_candidate_plan(plan, full_source=full_source)
    if not validation["accepted"]:
        return {"schema": "deterministic_patch_render_v1", "accepted": False, "reason": "candidate_plan_invalid", "validation": validation}
    edited = full_source
    for edit in plan.get("edits") or ():
        anchor = str(edit["anchor"])
        replacement = str(edit["replacement"])
        operation = str(edit["operation"])
        if edited.count(anchor) != 1:
            return {"schema": "deterministic_patch_render_v1", "accepted": False, "reason": "anchor_not_unique_at_render"}
        if operation == "replace_block":
            edited = edited.replace(anchor, replacement, 1)
        elif operation == "insert_before":
            edited = edited.replace(anchor, replacement + "\n" + anchor, 1)
        elif operation == "insert_after":
            edited = edited.replace(anchor, anchor + "\n" + replacement, 1)
    diff = "".join(difflib.unified_diff(
        full_source.splitlines(keepends=True),
        edited.splitlines(keepends=True),
        fromfile=f"a/{IMPLEMENTATION_PATH}",
        tofile=f"b/{IMPLEMENTATION_PATH}",
    ))
    return {
        "schema": "deterministic_patch_render_v1",
        "accepted": bool(diff),
        "reason": "" if diff else "empty_diff",
        "patch": diff,
        "patch_digest": bootstrap_digest(diff),
        "target": IMPLEMENTATION_PATH,
        "source_modified": False,
    }


def attach_deterministic_metadata(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(plan),
        "independent_evaluator": {
            "path": REPLACEMENT_EVALUATOR,
            "entry_point": REPLACEMENT_ENTRY_POINT,
            "digest": REPLACEMENT_DIGEST,
        },
        "prohibited_authority_acknowledged": PROHIBITED_AUTHORITY,
    }


def negative_controls(valid_plan: Mapping[str, Any], *, full_source: str) -> dict[str, Any]:
    duplicate_anchor = "if "
    cases = {
        "additional_file": {**dict(valid_plan), "edits": [{**dict((valid_plan.get("edits") or [{}])[0]), "target": "extra.py"}]},
        "evaluator_mutation": {**dict(valid_plan), "edits": [{**dict((valid_plan.get("edits") or [{}])[0]), "target": REPLACEMENT_EVALUATOR}]},
        "primary_worktree_path": {**dict(valid_plan), "implementation_path": "G:/Delta_Dev/orchestration/runtime/autonomy_advisory_assistance.py"},
        "missing_proposal_id": {key: value for key, value in dict(valid_plan).items() if key != "proposal_id"},
        "invented_anchor": {**dict(valid_plan), "edits": [{**dict((valid_plan.get("edits") or [{}])[0]), "anchor": "not present in source"}]},
        "non_unique_anchor": {**dict(valid_plan), "edits": [{**dict((valid_plan.get("edits") or [{}])[0]), "anchor": duplicate_anchor}]},
        "wildcard_or_traversal": {**dict(valid_plan), "edits": [{**dict((valid_plan.get("edits") or [{}])[0]), "target": "../orchestration/runtime/*.py"}]},
        "network_provider_package": {**dict(valid_plan), "change_intent": "pip install and call https://example.com"},
        "success_claim": {**dict(valid_plan), "change_intent": "tests pass and successfully fixed"},
        "missing_uncertainty_or_limitations": {key: value for key, value in dict(valid_plan).items() if key not in {"uncertainty", "limitations"}},
    }
    return {name: validate_candidate_plan(case, full_source=full_source) for name, case in cases.items()}
