"""Evaluator-binding amendment records for grounded CognitiveProposals."""
from __future__ import annotations

import inspect
from typing import Any, Callable, Mapping

from orchestration.runtime.cognitive_evaluator_qualification import (
    evaluate_stale_pass_observation,
    qualification_result,
)
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.delta_1_0_common import stable_id


PROPOSAL_ID = "cognitive-proposal-a6777613a9e0784f"
OLD_EVALUATOR = "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py"
REPLACEMENT_EVALUATOR = "orchestration/runtime/cognitive_evaluator_qualification.py"
REPLACEMENT_ENTRY_POINT = "evaluate_stale_pass_observation"
REPLACEMENT_DIGEST = "ee33648e27532241b9078791a48f694c408c320d00041166c1863317742a0f73"
EFFECTIVE_BINDING_STATUS = "evaluator_amended_pending_sandbox_candidate_authorization"
SEMANTIC_FIELDS = (
    "problem_id",
    "bounded_objective",
    "diagnosis",
    "first_incorrect_transition",
    "implementation_path",
    "focused_test_path",
    "bounded_strategy",
    "expected_behavioral_change",
    "limitations",
    "uncertainty",
    "required_authority",
    "prohibited_authority",
    "evidence_references",
)


def evaluator_boundary_audit(entry_point: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> dict[str, Any]:
    """Describe whether the evaluator callable can run outside qualification orchestration."""

    source = inspect.getsource(entry_point)
    forbidden_read_patterns = (
        "qualification_result.json",
        "final_status.json",
        '.get("candidate_id"',
        ".get('candidate_id'",
        '.get("strategy_label"',
        ".get('strategy_label'",
        '.get("fixture_name"',
        ".get('fixture_name'",
        '.get("expected_answer"',
        ".get('expected_answer'",
        '.get("expected_status"',
        ".get('expected_status'",
    )
    return {
        "schema": "evaluator_boundary_audit_v1",
        "entry_point": entry_point.__name__,
        "input_schema": "Mapping[str, Any] with public behavior observation fields",
        "output_schema": "behavioral judgment mapping with accepted, classification, reasons, and observed_status",
        "reads_qualification_result_files": any(name in source for name in ("qualification_result.json", "final_status.json")),
        "reads_candidate_ids": '.get("candidate_id"' in source or ".get('candidate_id'" in source,
        "reads_strategy_names": '.get("strategy_label"' in source or ".get('strategy_label'" in source,
        "reads_fixture_filenames": '.get("fixture_name"' in source or ".get('fixture_name'" in source,
        "reads_expected_evaluator_outcomes": any(name in source for name in ('.get("expected_answer"', ".get('expected_answer'", '.get("expected_status"', ".get('expected_status'")),
        "can_modify_implementation_source": False,
        "can_modify_own_source": False,
        "performs_candidate_generation": False,
        "performs_proposal_validation": False,
        "contains_default_passing_result": "accepted\": True" in source or "'accepted': True" in source,
        "shares_mutable_global_state": False,
        "forbidden_tokens_present": tuple(token for token in forbidden_read_patterns if token in source),
        "independently_usable": not any(token in source for token in forbidden_read_patterns),
    }


def evaluator_self_certification_audit(entry_point: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> dict[str, Any]:
    source = inspect.getsource(entry_point)
    forbidden = (
        "qualification_result.json",
        "final_status.json",
        "COGNITIVE_EVALUATOR_QUALIFICATION_1_PASSED",
        '.get("candidate_id"',
        ".get('candidate_id'",
        '.get("strategy_label"',
        ".get('strategy_label'",
        '.get("fixture_name"',
        ".get('fixture_name'",
        "hardcoded",
    )
    hits = tuple(item for item in forbidden if item in source)
    return {"schema": "evaluator_self_certification_audit_v1", "accepted": not hits, "forbidden_hits": hits}


def verify_operator_authorization(authorization: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if authorization.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_proposal_id")
    if authorization.get("old_evaluator_path") != OLD_EVALUATOR:
        reasons.append("wrong_old_evaluator")
    if authorization.get("replacement_evaluator_path") != REPLACEMENT_EVALUATOR:
        reasons.append("wrong_replacement_evaluator")
    if authorization.get("replacement_evaluator_digest") != REPLACEMENT_DIGEST:
        reasons.append("wrong_replacement_evaluator_digest")
    permitted = set(authorization.get("permitted_actions") or ())
    if "evaluator_binding_amendment" not in permitted:
        reasons.append("missing_binding_amendment_authority")
    prohibited = set(authorization.get("prohibited_actions") or ())
    if not {"candidate_generation", "candidate_application", "sandbox_implementation"} <= prohibited:
        reasons.append("missing_candidate_generation_block")
    return {"schema": "operator_authorization_validation_v1", "accepted": not reasons, "reasons": tuple(reasons)}


def unchanged_semantic_fields(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    changed = tuple(field for field in SEMANTIC_FIELDS if before.get(field) != after.get(field))
    return {"schema": "unchanged_semantic_fields_v1", "accepted": not changed, "changed_fields": changed, "fields": SEMANTIC_FIELDS}


def create_amendment_record(
    *,
    proposal: Mapping[str, Any],
    proposal_digest: str,
    previous_evaluator_digest: str,
    replacement_behavior_contract_digest: str,
    qualification_report_digest: str,
    operator_authorization_record: Mapping[str, Any],
    created_at: str,
) -> dict[str, Any]:
    duplicate_key = bootstrap_digest({
        "proposal_id": PROPOSAL_ID,
        "replacement_evaluator_path": REPLACEMENT_EVALUATOR,
        "replacement_evaluator_digest": REPLACEMENT_DIGEST,
        "qualification_report_digest": qualification_report_digest,
    })
    amendment_id = stable_id("cognitive-evaluator-binding-amendment", duplicate_key)
    return {
        "schema": "cognitive_evaluator_binding_amendment_v1",
        "amendment_id": amendment_id,
        "proposal_id": PROPOSAL_ID,
        "proposal_digest": proposal_digest,
        "amendment_type": "evaluator_binding_replacement",
        "previous_evaluator_path": OLD_EVALUATOR,
        "previous_evaluator_digest": previous_evaluator_digest,
        "previous_binding_status": "behaviorally_insensitive_baseline_blocked",
        "replacement_evaluator_path": REPLACEMENT_EVALUATOR,
        "replacement_evaluator_digest": REPLACEMENT_DIGEST,
        "replacement_evaluator_entry_point": REPLACEMENT_ENTRY_POINT,
        "diagnosed_previous_blind_spot": "selected evaluator did not exercise stale-pass replay path",
        "replacement_behavior_contract_digest": replacement_behavior_contract_digest,
        "qualification_report_digest": qualification_report_digest,
        "operator_authorization_record": dict(operator_authorization_record),
        "authorization_scope": "evaluator binding amendment only; no candidate generation or application",
        "unchanged_proposal_fields": tuple(field for field in SEMANTIC_FIELDS if field in proposal),
        "amended_binding_disposition": EFFECTIVE_BINDING_STATUS,
        "created_at": created_at,
        "duplicate_key": duplicate_key,
    }


def validate_amendment_record(
    record: Mapping[str, Any],
    *,
    proposal: Mapping[str, Any],
    proposal_digest: str,
    replacement_evaluator_digest: str,
    qualification_report_digest: str,
    authorization_validation: Mapping[str, Any],
    boundary_audit: Mapping[str, Any],
    self_certification: Mapping[str, Any],
    semantic_check: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if record.get("proposal_id") != PROPOSAL_ID or proposal.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_proposal_id")
    if record.get("proposal_digest") != proposal_digest:
        reasons.append("wrong_proposal_digest")
    if record.get("replacement_evaluator_digest") != replacement_evaluator_digest:
        reasons.append("wrong_replacement_evaluator_digest")
    if record.get("qualification_report_digest") != qualification_report_digest:
        reasons.append("wrong_qualification_report_digest")
    if not authorization_validation.get("accepted"):
        reasons.append("operator_authorization_rejected")
    if not boundary_audit.get("independently_usable"):
        reasons.append("evaluator_boundary_rejected")
    if not self_certification.get("accepted"):
        reasons.append("evaluator_self_certification_rejected")
    if not semantic_check.get("accepted"):
        reasons.append("proposal_semantic_drift")
    if record.get("amended_binding_disposition") != EFFECTIVE_BINDING_STATUS:
        reasons.append("wrong_disposition")
    return {"schema": "evaluator_binding_amendment_validation_v1", "accepted": not reasons, "reasons": tuple(reasons)}


def baseline_sensitivity_recheck(cases: Mapping[str, Mapping[str, Any]], *, evaluator_digest_before: str, evaluator_digest_after: str) -> dict[str, Any]:
    return qualification_result(cases, evaluator_digest_before=evaluator_digest_before, evaluator_digest_after=evaluator_digest_after)


def candidate_generation_block(amendment: Mapping[str, Any]) -> dict[str, Any]:
    blocked = amendment.get("amended_binding_disposition") == EFFECTIVE_BINDING_STATUS
    return {
        "schema": "candidate_generation_block_v1",
        "blocked": blocked,
        "fresh_authorization_required": True,
        "candidate_generated": False,
        "candidate_applied": False,
    }


def duplicate_amendment_result(first: Mapping[str, Any], second: Mapping[str, Any]) -> dict[str, Any]:
    same_id = first.get("amendment_id") == second.get("amendment_id")
    same_key = first.get("duplicate_key") == second.get("duplicate_key")
    return {"schema": "duplicate_amendment_v1", "suppressed": same_id and same_key, "same_id": same_id, "same_duplicate_key": same_key}


def default_authorization_record() -> dict[str, Any]:
    return {
        "schema": "operator_evaluator_binding_authorization_v1",
        "proposal_id": PROPOSAL_ID,
        "old_evaluator_path": OLD_EVALUATOR,
        "replacement_evaluator_path": REPLACEMENT_EVALUATOR,
        "replacement_evaluator_digest": REPLACEMENT_DIGEST,
        "permitted_actions": ("evaluator_binding_amendment",),
        "prohibited_actions": ("candidate_generation", "candidate_application", "sandbox_implementation"),
    }


def replacement_evaluator_callable() -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    return evaluate_stale_pass_observation
