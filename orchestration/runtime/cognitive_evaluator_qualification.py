"""Evaluator qualification for the cognitive sandbox stale-pass boundary."""
from __future__ import annotations

import json
from typing import Any, Mapping

from orchestration.runtime.developmental_bootstrap import bootstrap_digest


QUALIFICATION_SCHEMA = "cognitive_evaluator_qualification_v1"
STALE_PASS_STATUS = "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"
VALID_BLOCKED_STATUSES = {
    "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP",
    "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_BASELINE_BLOCKED",
    "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INSUFFICIENT_EVIDENCE",
}


def diagnosed_behavior_contract() -> dict[str, Any]:
    return {
        "schema": "evaluator_behavior_contract_v1",
        "initial_state": "existing advisory output, grounding audit, and report are present for replay",
        "triggering_input": "request_bounded_advice is invoked on an existing advisory output root",
        "expected_governed_behavior": "stale or insufficiently grounded replay must not emit PASSED solely from stale retained records",
        "actual_stale_pass_behavior": STALE_PASS_STATUS,
        "observable_output_fields": ("status", "duplicate_suppressed", "reason"),
        "repair_strategy_coupling": False,
    }


def evaluate_stale_pass_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Judge public behavior without checking patch text, labels, or implementation symbols."""

    status = str(observation.get("status") or "")
    reasons: list[str] = []
    classification = "unrelated_failure"
    if observation.get("parse_error") or observation.get("runtime_error"):
        classification = "unrelated_failure"
        reasons.append("unrelated_runtime_or_parse_failure")
    elif status == STALE_PASS_STATUS:
        classification = "stale_pass_detected"
        reasons.append("stale_pass_rejected")
    elif status in VALID_BLOCKED_STATUSES:
        classification = "valid_blocked_behavior"
    else:
        classification = "unknown_disposition"
        reasons.append("unknown_disposition")
    return {
        "schema": QUALIFICATION_SCHEMA,
        "accepted": not reasons,
        "classification": classification,
        "reasons": tuple(reasons),
        "observed_status": status,
        "behavior_contract_digest": bootstrap_digest(diagnosed_behavior_contract()),
        "strategy_label_used": False,
        "fixture_name_used": False,
        "candidate_identity_used": False,
        "implementation_symbol_used": False,
    }


def evaluator_candidate_audit(*, path: str, baseline_observation: Mapping[str, Any], original: bool = False) -> dict[str, Any]:
    result = evaluate_stale_pass_observation(baseline_observation)
    return {
        "schema": "evaluator_candidate_audit_v1",
        "path": path,
        "original_selected_evaluator": original,
        "behavior_exercised": "stale advisory replay public disposition",
        "independent_from_repair_strategy": True,
        "baseline_currently_fails": result["classification"] == "stale_pass_detected",
        "detects_false_pass": result["classification"] == "stale_pass_detected",
        "requires_hidden_implementation_knowledge": False,
        "modifies_source": False,
        "suitable_to_freeze": result["classification"] == "stale_pass_detected" and not original,
        "result": result,
    }


def qualification_result(cases: Mapping[str, Mapping[str, Any]], *, evaluator_digest_before: str, evaluator_digest_after: str) -> dict[str, Any]:
    required = {
        "case_a_current_baseline": False,
        "case_b_valid_behavior": True,
        "case_c_false_pass": False,
        "case_g_hardcoded_output": False,
    }
    reasons: list[str] = []
    for name, expected in required.items():
        accepted = bool(cases.get(name, {}).get("accepted"))
        if accepted is not expected:
            reasons.append(f"{name}_unexpected")
    if cases.get("case_d_unrelated_failure", {}).get("classification") != "unrelated_failure":
        reasons.append("unrelated_failure_misclassified")
    if cases.get("case_e_strategy_label") != cases.get("case_c_false_pass"):
        reasons.append("strategy_label_variant_changed_result")
    if cases.get("case_f_fixture_name") != cases.get("case_c_false_pass"):
        reasons.append("fixture_name_variant_changed_result")
    if evaluator_digest_before != evaluator_digest_after:
        reasons.append("evaluator_digest_changed")
    return {
        "schema": "evaluator_qualification_result_v1",
        "accepted": not reasons,
        "reasons": tuple(reasons),
        "evaluator_digest_before": evaluator_digest_before,
        "evaluator_digest_after": evaluator_digest_after,
        "deterministic": True,
        "implementation_source_mutation": False,
        "proposal_mutation": False,
    }


def stable_case_digest(case: Mapping[str, Any]) -> str:
    return bootstrap_digest(json.loads(json.dumps(case, sort_keys=True, default=str)))
