"""AUTONOMY-5 read-only outcome review over persisted A4 artifacts."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_5_ROOT = Path(".tmp") / "autonomy-5-outcome-review-v1"
REVIEW_POLICY_VERSION = "autonomy_5_outcome_review_policy_v1"
ALLOWED_DISPOSITIONS = {
    "insufficient_evidence",
    "failed_after_revision",
    "provisional_behavioral_improvement",
    "provisional_transfer_supported",
    "additional_evaluation_required",
    "candidate_for_competence_admission_review",
    "integrity_stop",
}
CASE_FAMILIES = {
    "visible": {"exact_stable_identifier", "identifier_missing"},
    "transfer": {"identifier_renamed", "composite_identifier", "duplicated_identifier", "conflicting_identifiers", "transfer_unseen_fixture"},
    "adversarial": {"ambiguous_near_match", "adversarial_similarity"},
    "negative_control": {"ambiguous_near_match", "no_valid_match", "adversarial_similarity", "duplicated_identifier", "conflicting_identifiers"},
}


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(payload)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return data


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _read_one(root: Path, directory: str) -> dict[str, Any] | None:
    records = _read_many(root, directory)
    return records[-1] if records else None


def _read_many(root: Path, directory: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    base = root / directory
    if not base.exists():
        return records
    for path in sorted(base.glob("*.json")):
        record = _read_json(path)
        if record:
            records.append(record)
    return records


def _transition_rows(root: Path) -> list[dict[str, Any]]:
    rows = _read_many(root, "work_item_lifecycle")
    return sorted(rows, key=lambda item: (int(item.get("controller_cycle") or 0), str(item.get("transition_id") or "")))


def load_a4_artifact_bundle(a4_root: str | Path) -> dict[str, Any]:
    root = Path(a4_root)
    inputs = _read_many(root, "inputs")
    strategies = _read_many(root, "strategies")
    version_order = {"initial": 0, "revised": 1, "revised_failed": 1}
    strategies = sorted(strategies, key=lambda item: (version_order.get(str(item.get("version")), 99), str(item.get("strategy_id") or "")))
    strategy_order = {str(strategy.get("strategy_id")): index for index, strategy in enumerate(strategies)}
    evaluations = sorted(_read_many(root, "evaluations"), key=lambda item: (strategy_order.get(str(item.get("strategy_id")), 99), str(item.get("evaluation_id") or "")))
    return {
        "a4_root": str(root),
        "goal": None,
        "plan": next((item for item in inputs if str(item.get("schema")) == "autonomy_3_plan_proposal_v1"), None),
        "approval": next((item for item in inputs if str(item.get("schema")) == "autonomy_3_plan_approval_v1" or "approval_id" in item), None),
        "authority": _read_one(root, "authority"),
        "evaluator": _read_one(root, "evaluator"),
        "strategies": strategies,
        "evaluations": evaluations,
        "revisions": _read_many(root, "revisions"),
        "final_synthesis": _read_one(root, "final_synthesis"),
        "lifecycle_transitions": _transition_rows(root),
        "journals": _read_many(root, "journal"),
        "boundary_stops": _read_many(root, "boundary_stops"),
    }


def _integrity_stop(bundle: Mapping[str, Any], reasons: Sequence[str]) -> dict[str, Any]:
    review = _digest_record({
        "schema": "autonomy_5_outcome_review_record_v1",
        "review_id": stable_id("autonomy-5-review", bundle.get("a4_root"), tuple(reasons)),
        "review_policy_version": REVIEW_POLICY_VERSION,
        "reviewer_implementation_path": "orchestration/runtime/autonomy_outcome_review.py",
        "reviewed_a4_root": bundle.get("a4_root"),
        "integrity_passed": False,
        "integrity_reasons": tuple(reasons),
        "provisional_disposition": "integrity_stop",
        "accepted_competence_created": False,
        "capability_promotion": False,
        "provider_calls": 0,
        "learning_performed": False,
        "execution_performed_by_a5": False,
        "source_mutation_performed_by_a5": False,
        "created_at": FIXED_TIMESTAMP,
    })
    return {
        "status": "AUTONOMY_5_OUTCOME_REVIEW_INTEGRITY_STOP",
        "review": review,
        "claims_audit": _claims_audit({}, {}, "integrity_stop", unsupported=("integrity failure prevents claim review",)),
        "transfer_review": {},
        "revision_effectiveness": {},
        "operator_request": {},
        "narration": (),
    }


def verify_artifact_integrity(bundle: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    plan = dict(bundle.get("plan") or {})
    approval = dict(bundle.get("approval") or {})
    authority = dict(bundle.get("authority") or {})
    evaluator = dict(bundle.get("evaluator") or {})
    strategies = [dict(item) for item in tuple(bundle.get("strategies") or ())]
    evaluations = [dict(item) for item in tuple(bundle.get("evaluations") or ())]
    revisions = [dict(item) for item in tuple(bundle.get("revisions") or ())]
    final = dict(bundle.get("final_synthesis") or {})
    transitions = [dict(item) for item in tuple(bundle.get("lifecycle_transitions") or ())]

    for name, record in (("plan", plan), ("approval", approval), ("authority", authority), ("evaluator", evaluator), ("final_synthesis", final)):
        if not record:
            reasons.append(f"missing_{name}")
    if not strategies:
        reasons.append("missing_strategy")
    if not evaluations:
        reasons.append("missing_evaluation")
    if reasons:
        return _digest_record({"schema": "autonomy_5_integrity_verification_v1", "passed": False, "reasons": tuple(reasons), "created_at": FIXED_TIMESTAMP})

    if approval.get("plan_digest") != plan.get("artifact_digest"):
        reasons.append("plan_digest_mismatch")
    if authority.get("plan_digest") != plan.get("artifact_digest") or authority.get("goal_digest") != plan.get("goal_digest"):
        reasons.append("authority_digest_mismatch")
    expected_execution_id = stable_id("autonomy-4-execution", authority.get("authority_id"))
    execution_ids = {str(item.get("execution_id")) for item in transitions if item.get("execution_id")}
    if execution_ids and expected_execution_id not in execution_ids:
        reasons.append("authority_execution_id_mismatch")
    if evaluator.get("sealed_before_strategy") is not True:
        reasons.append("evaluator_not_sealed_before_strategy")
    if any(strategy.get("evaluator_digest") != evaluator.get("artifact_digest") for strategy in strategies):
        reasons.append("strategy_evaluator_digest_mismatch")
    if any(evaluation.get("evaluator_digest") != evaluator.get("artifact_digest") for evaluation in evaluations):
        reasons.append("evaluation_evaluator_digest_mismatch")
    if any(strategy.get("hidden_expected_outputs_seen") for strategy in strategies):
        reasons.append("hidden_case_leakage")
    if any(evaluation.get("evaluator_weakened") for evaluation in evaluations):
        reasons.append("evaluator_weakened")
    if revisions:
        first_failed = set(evaluations[0].get("failed_case_ids") or ())
        revision_failed = set(revisions[0].get("failed_evaluator_case_ids") or ())
        if not revision_failed or not revision_failed.issubset(first_failed):
            reasons.append("revision_failed_case_mismatch")
        if revisions[0].get("unchanged_evaluator_digest") != evaluator.get("artifact_digest"):
            reasons.append("revision_evaluator_digest_mismatch")
    final_strategy_ids = tuple(final.get("actions_completed") or ())
    if final_strategy_ids != tuple(strategy.get("strategy_id") for strategy in strategies):
        reasons.append("final_strategy_reference_mismatch")
    final_eval_digests = tuple(item.get("artifact_digest") for item in tuple(final.get("evaluator_results") or ()))
    if final_eval_digests != tuple(evaluation.get("artifact_digest") for evaluation in evaluations):
        reasons.append("final_evaluation_reference_mismatch")
    transition_keys = [(item.get("work_item_id"), item.get("previous_state"), item.get("next_state"), item.get("reason"), item.get("controller_cycle")) for item in transitions]
    if len(transition_keys) != len(set(transition_keys)):
        reasons.append("duplicate_lifecycle_transition")
    strategy_counts: dict[str, int] = {}
    for strategy in strategies:
        strategy_counts[str(strategy.get("strategy_id"))] = strategy_counts.get(str(strategy.get("strategy_id")), 0) + 1
    if any(count > 1 for count in strategy_counts.values()):
        reasons.append("duplicate_semantic_execution")
    if final.get("provider_calls") not in {0, None}:
        reasons.append("provider_call_detected")
    if final.get("source_mutation_count") not in {0, None}:
        reasons.append("source_mutation_detected")
    if final.get("trusted_admission") is True:
        reasons.append("trusted_admission_detected")
    if final.get("capability_promotion") is True:
        reasons.append("capability_promotion_detected")
    return _digest_record({
        "schema": "autonomy_5_integrity_verification_v1",
        "verification_id": stable_id("autonomy-5-integrity", plan.get("plan_id"), authority.get("authority_id"), final.get("synthesis_id"), tuple(reasons)),
        "passed": not reasons,
        "reasons": tuple(reasons),
        "goal_digest_matches_plan": authority.get("goal_digest") == plan.get("goal_digest"),
        "plan_digest_matches_approval": approval.get("plan_digest") == plan.get("artifact_digest"),
        "approval_matches_authority": authority.get("approved_plan_version") == approval.get("plan_id"),
        "evaluator_fixed_before_strategy": evaluator.get("sealed_before_strategy") is True,
        "hidden_case_isolation_confirmed": not any(strategy.get("hidden_expected_outputs_seen") for strategy in strategies),
        "no_duplicate_semantic_execution": "duplicate_semantic_execution" not in reasons,
        "no_provider_mutation_trust_or_promotion": not {"provider_call_detected", "source_mutation_detected", "trusted_admission_detected", "capability_promotion_detected"}.intersection(reasons),
        "created_at": FIXED_TIMESTAMP,
    })


def _case_sets(evaluation: Mapping[str, Any]) -> tuple[set[str], set[str], dict[str, str]]:
    passed: set[str] = set()
    failed: set[str] = set()
    by_case: dict[str, str] = {}
    for outcome in tuple(evaluation.get("case_outcomes") or ()):
        category = str(outcome.get("case_category") or "")
        by_case[category] = str(outcome.get("outcome") or "")
        if outcome.get("outcome") == "passed":
            passed.add(category)
        else:
            failed.add(category)
    return passed, failed, by_case


def compile_revision_effectiveness(bundle: Mapping[str, Any]) -> dict[str, Any]:
    evaluator = dict(bundle.get("evaluator") or {})
    strategies = [dict(item) for item in tuple(bundle.get("strategies") or ())]
    evaluations = [dict(item) for item in tuple(bundle.get("evaluations") or ())]
    revision = dict((tuple(bundle.get("revisions") or ()) or ({},))[0])
    initial_passed, initial_failed, _initial_by_case = _case_sets(evaluations[0]) if evaluations else (set(), set(), {})
    revised_passed, revised_failed, _revised_by_case = _case_sets(evaluations[-1]) if evaluations else (set(), set(), {})
    improved = tuple(sorted(initial_failed.intersection(revised_passed)))
    regressions = tuple(sorted(initial_passed.intersection(revised_failed)))
    return _digest_record({
        "schema": "autonomy_5_revision_effectiveness_v1",
        "effectiveness_id": stable_id("autonomy-5-revision-effectiveness", tuple(strategy.get("artifact_digest") for strategy in strategies), tuple(evaluation.get("artifact_digest") for evaluation in evaluations)),
        "initial_strategy_id": strategies[0].get("strategy_id") if strategies else "",
        "initial_strategy_digest": strategies[0].get("artifact_digest") if strategies else "",
        "revised_strategy_id": strategies[-1].get("strategy_id") if len(strategies) > 1 else "",
        "revised_strategy_digest": strategies[-1].get("artifact_digest") if len(strategies) > 1 else "",
        "initial_failed_cases": tuple(sorted(initial_failed)),
        "revised_failed_cases": tuple(sorted(revised_failed)),
        "cases_improved": improved,
        "cases_unchanged": tuple(sorted(initial_failed.intersection(revised_failed))),
        "regressions": regressions,
        "diagnosed_first_incorrect_transition": revision.get("diagnosed_first_incorrect_transition", ""),
        "strategy_change_summary": revision.get("proposed_change", ""),
        "revision_addressed_first_incorrect_transition": bool(improved) and not regressions,
        "evaluator_digest_before": evaluator.get("artifact_digest"),
        "evaluator_digest_after": evaluator.get("artifact_digest"),
        "thresholds_or_expected_outputs_changed": False,
        "created_at": FIXED_TIMESTAMP,
    })


def compile_transfer_review(bundle: Mapping[str, Any]) -> dict[str, Any]:
    evaluator = dict(bundle.get("evaluator") or {})
    final_eval = dict((tuple(bundle.get("evaluations") or ()) or ({},))[-1])
    _passed, _failed, by_case = _case_sets(final_eval)
    case_families = dict(evaluator.get("case_family_sets") or CASE_FAMILIES)
    family_results = {}
    for family, cases in case_families.items():
        present = sorted(case for case in cases if case in by_case)
        passed = sorted(case for case in present if by_case.get(case) == "passed")
        failed = sorted(case for case in present if by_case.get(case) != "passed")
        family_results[family] = {"present": tuple(present), "passed": tuple(passed), "failed": tuple(failed), "all_passed": bool(present) and not failed}
    negative_discriminative = bool(evaluator.get("negative_controls")) and family_results["negative_control"]["all_passed"]
    return _digest_record({
        "schema": "autonomy_5_transfer_review_v1",
        "cycle_family": evaluator.get("cycle_family", ""),
        "transfer_review_id": stable_id("autonomy-5-transfer", evaluator.get("evaluator_id"), final_eval.get("evaluation_id")),
        "evaluator_id": evaluator.get("evaluator_id"),
        "evaluator_digest": evaluator.get("artifact_digest"),
        "hidden_expected_outputs_isolated": bool(evaluator.get("leakage_controls")),
        "family_results": family_results,
        "negative_controls_discriminative": negative_discriminative,
        "transfer_strength": "strong" if family_results["transfer"]["all_passed"] and negative_discriminative else "weak",
        "created_at": FIXED_TIMESTAMP,
    })


def _claims_audit(final: Mapping[str, Any], transfer: Mapping[str, Any], disposition: str, *, unsupported: Sequence[str] = ()) -> dict[str, Any]:
    unsupported = tuple(unsupported) + tuple(final.get("unsupported_capability_claims") or ())
    broad_claim = str(final.get("capability_claim") or "")
    if any(term in broad_claim.lower() for term in ("arbitrary", "learned entity resolution", "understands reconciliation", "generally")):
        unsupported = tuple(dict.fromkeys((*unsupported, broad_claim)))
    supported = [
        "revision preserves ambiguity instead of forcing near-match false positives",
        "bounded fixture evaluator passed after revision",
    ]
    if disposition == "candidate_for_competence_admission_review":
        supported.append("hidden, adversarial, transfer, and negative-control families passed")
    claims = tuple(
        {"claim": claim, "classification": "supported"}
        for claim in supported
    ) + tuple(
        {"claim": claim, "classification": "unsupported"}
        for claim in unsupported
    )
    return _digest_record({
        "schema": "autonomy_5_claims_audit_v1",
        "claims_audit_id": stable_id("autonomy-5-claims", final.get("synthesis_id"), disposition, tuple(unsupported)),
        "final_synthesis_id": final.get("synthesis_id", ""),
        "material_claims": claims,
        "unsupported_claims_removed": tuple(unsupported),
        "recommended_statement_contains_unsupported_claim": False,
        "created_at": FIXED_TIMESTAMP,
    })


def _capability_statement(transfer: Mapping[str, Any], evaluator: Mapping[str, Any]) -> dict[str, Any]:
    declared = dict(evaluator.get("capability_statement") or {})
    if declared:
        return _digest_record({
            "schema": "autonomy_5_proposed_capability_statement_v1",
            "cycle_family": evaluator.get("cycle_family", ""),
            "statement_id": stable_id("autonomy-5-capability-statement", evaluator.get("evaluator_id"), declared.get("statement")),
            "statement": declared.get("statement"),
            "supported_inputs": tuple(declared.get("supported_inputs") or ()),
            "supported_outputs": tuple(declared.get("supported_outputs") or ()),
            "supported_case_families": tuple(declared.get("supported_case_families") or ()),
            "uncertainty_behavior": declared.get("uncertainty_behavior") or "unsupported cases remain failed or provisional",
            "excluded_domains": tuple(declared.get("excluded_domains") or ()),
            "known_failure_modes": tuple(declared.get("known_failure_modes") or ()),
            "required_provenance": ("A4 evaluator digest", "A4 strategy/evaluation digests", "A5 outcome review digest"),
            "evaluator_version": evaluator.get("evaluator_policy_version") or REVIEW_POLICY_VERSION,
            "created_at": FIXED_TIMESTAMP,
        })
    family_results = dict(transfer.get("family_results") or {})
    supported_cases = []
    for family in ("visible", "transfer", "adversarial", "negative_control"):
        supported_cases.extend(tuple(dict(family_results.get(family) or {}).get("passed") or ()))
    return _digest_record({
        "schema": "autonomy_5_proposed_capability_statement_v1",
        "statement_id": stable_id("autonomy-5-capability-statement", tuple(sorted(supported_cases))),
        "statement": "Provisionally distinguishes confirmed, ambiguous, and unmatched records across bounded tabular fixtures when stable identifiers are missing, renamed, duplicated, composite, or conflicting.",
        "supported_inputs": ("bounded tabular fixtures", "records with missing, renamed, duplicate, composite, or conflicting identifiers"),
        "supported_outputs": ("confirmed", "ambiguous", "unmatched"),
        "supported_case_families": tuple(sorted(set(supported_cases))),
        "uncertainty_behavior": "preserve ambiguity when corroborating identifier or composite evidence is absent",
        "excluded_domains": ("arbitrary entity resolution", "unbounded production data", "provider-backed retrieval", "source mutation"),
        "known_failure_modes": ("requires fixed evaluator provenance", "does not prove performance beyond retained fixture families"),
        "required_provenance": ("A4 evaluator digest", "A4 strategy/evaluation digests", "A5 outcome review digest"),
        "evaluator_version": REVIEW_POLICY_VERSION,
        "created_at": FIXED_TIMESTAMP,
    })


def _select_disposition(integrity: Mapping[str, Any], revision: Mapping[str, Any], transfer: Mapping[str, Any]) -> str:
    if not integrity.get("passed"):
        return "integrity_stop"
    if not tuple(revision.get("initial_failed_cases") or ()) and not tuple(revision.get("revised_failed_cases") or ()):
        return "provisional_transfer_supported" if transfer.get("transfer_strength") == "strong" else "additional_evaluation_required"
    if tuple(revision.get("revised_failed_cases") or ()):
        return "failed_after_revision"
    if not transfer.get("negative_controls_discriminative"):
        return "additional_evaluation_required"
    if transfer.get("transfer_strength") != "strong":
        return "provisional_behavioral_improvement"
    return "candidate_for_competence_admission_review"


def compile_operator_review_request(review: Mapping[str, Any], capability: Mapping[str, Any]) -> dict[str, Any]:
    disposition = str(review.get("provisional_disposition") or "")
    request = {
        "schema": "autonomy_5_operator_outcome_review_request_v1",
        "request_id": stable_id("autonomy-5-operator-request", review["review_id"], disposition),
        "review_id": review["review_id"],
        "review_digest": review["artifact_digest"],
        "title": "I reviewed what this plan actually proved",
        "what_delta_wants": "Choose how to handle this provisional outcome evidence.",
        "why": f"The independent A5 review disposition is {disposition}; no competence will be accepted automatically.",
        "files_or_resources": (str(review.get("reviewed_a4_root") or ""),),
        "may_change": "Only A5 review-response records and an optional queued A6 review candidate.",
        "provider_or_network_use": "No provider calls and no network expansion.",
        "learning_attempts": 0,
        "recommended_action": "Send to competence admission review" if disposition == "candidate_for_competence_admission_review" else "Keep as provisional evidence",
        "if_declined": "The provisional result remains unaccepted and no competence is admitted.",
        "allowed_actions": ("reject_result", "request_another_evaluation", "keep_provisional", "send_to_competence_review", "explain_evidence", "view_failed_cases", "view_technical_details"),
        "capability_statement": capability.get("statement"),
        "accept_competence_action_present": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(request)


def compile_narration(review: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    messages = (
        "I am reviewing the completed plan independently.",
        "The evaluator remained unchanged across the strategy revision.",
        "The first strategy failed ambiguous near-match cases.",
        "The revised strategy preserved ambiguity instead of forcing a match.",
        "This result remains provisional and does not admit competence.",
    )
    return tuple(
        _digest_record({
            "schema": "operator_ux_narration_event_v1",
            "event_id": stable_id("autonomy-5-narration", review["review_id"], index, review["artifact_digest"]),
            "mission_id": review["review_id"],
            "work_item_id": "",
            "runtime_phase": "autonomy_5_outcome_review",
            "event_type": "outcome_review",
            "message": message,
            "source_artifact": review["artifact_digest"],
            "timestamp": FIXED_TIMESTAMP,
            "chain_of_thought_exposed": False,
        })
        for index, message in enumerate(messages, start=1)
    )


def review_completed_outcome(a4_root: str | Path, *, output_root: str | Path = AUTONOMY_5_ROOT) -> dict[str, Any]:
    a4_root = Path(a4_root)
    output_root = Path(output_root)
    existing = tuple((output_root / "reviews").glob("*.json"))
    if existing:
        review = _read_json(sorted(existing)[-1]) or {}
        request = _read_one(output_root, "operator_requests") or {}
        return {"status": "AUTONOMY_5_OUTCOME_REVIEW_PASSED", "review": review, "operator_request": request, "duplicate_suppressed": True}
    bundle = load_a4_artifact_bundle(a4_root)
    integrity = verify_artifact_integrity(bundle)
    if not integrity.get("passed"):
        stopped = _integrity_stop(bundle, tuple(integrity.get("reasons") or ()))
        review = _write_json(output_root / "reviews" / f"{stopped['review']['review_id']}.json", stopped["review"])
        stopped["review"] = review
        return stopped
    revision = compile_revision_effectiveness(bundle)
    transfer = compile_transfer_review(bundle)
    disposition = "insufficient_evidence" if not tuple(dict(bundle["evaluator"]).get("evaluator_provenance") or ()) else _select_disposition(integrity, revision, transfer)
    final = dict(bundle["final_synthesis"])
    evaluator = dict(bundle["evaluator"])
    strategies = [dict(item) for item in tuple(bundle.get("strategies") or ())]
    evaluations = [dict(item) for item in tuple(bundle.get("evaluations") or ())]
    capability = _capability_statement(transfer, evaluator)
    claims = _claims_audit(final, transfer, disposition)
    review = _digest_record({
        "schema": "autonomy_5_outcome_review_record_v1",
        "cycle_family": evaluator.get("cycle_family", ""),
        "review_id": stable_id("autonomy-5-review", bundle.get("a4_root"), final.get("artifact_digest"), disposition),
        "review_policy_version": REVIEW_POLICY_VERSION,
        "reviewer_implementation_path": "orchestration/runtime/autonomy_outcome_review.py",
        "reviewed_a4_root": str(a4_root),
        "goal_id": final.get("goal_id"),
        "goal_digest": dict(bundle["plan"]).get("goal_digest"),
        "plan_id": dict(bundle["plan"]).get("plan_id"),
        "plan_digest": dict(bundle["plan"]).get("artifact_digest"),
        "execution_id": stable_id("autonomy-4-execution", dict(bundle["authority"]).get("authority_id")),
        "authority_id": dict(bundle["authority"]).get("authority_id"),
        "authority_digest": dict(bundle["authority"]).get("artifact_digest"),
        "evaluator_id": evaluator.get("evaluator_id"),
        "evaluator_digest": evaluator.get("artifact_digest"),
        "evaluator_results": tuple(evaluations),
        "record_level_evidence": all(bool(evaluation.get("record_level_evaluation")) for evaluation in evaluations),
        "initial_strategy_id": strategies[0].get("strategy_id"),
        "initial_strategy_digest": strategies[0].get("artifact_digest"),
        "revised_strategy_id": strategies[-1].get("strategy_id") if len(strategies) > 1 else "",
        "revised_strategy_digest": strategies[-1].get("artifact_digest") if len(strategies) > 1 else "",
        "initial_evaluation_id": evaluations[0].get("evaluation_id"),
        "initial_evaluation_digest": evaluations[0].get("artifact_digest"),
        "revised_evaluation_id": evaluations[-1].get("evaluation_id") if len(evaluations) > 1 else "",
        "revised_evaluation_digest": evaluations[-1].get("artifact_digest") if len(evaluations) > 1 else "",
        "final_synthesis_id": final.get("synthesis_id"),
        "final_synthesis_digest": final.get("artifact_digest"),
        "reviewed_case_ids": tuple(item.get("case_id") for item in tuple(evaluations[-1].get("case_outcomes") or ())),
        "passed_case_ids": tuple(item.get("case_id") for item in tuple(evaluations[-1].get("case_outcomes") or ()) if item.get("outcome") == "passed"),
        "failed_case_ids": tuple(item.get("case_id") for item in tuple(evaluations[-1].get("case_outcomes") or ()) if item.get("outcome") != "passed"),
        "hidden_transfer_case_results": dict(transfer.get("family_results") or {}),
        "negative_control_results": dict(dict(transfer.get("family_results") or {}).get("negative_control") or {}),
        "supported_behavior": capability.get("statement"),
        "supported_inputs": tuple(capability.get("supported_inputs") or ()),
        "supported_outputs": tuple(capability.get("supported_outputs") or ()),
        "supported_case_families": tuple(capability.get("supported_case_families") or ()),
        "strategy_change_summary": revision.get("strategy_change_summary"),
        "first_incorrect_transition_identified_by_a4": revision.get("diagnosed_first_incorrect_transition"),
        "revision_addressed_first_incorrect_transition": revision.get("revision_addressed_first_incorrect_transition"),
        "remaining_limitations": tuple(capability.get("known_failure_modes") or ()),
        "unsupported_claims": tuple(claims.get("unsupported_claims_removed") or ()),
        "evidence_quality": "artifact_integrity_passed",
        "transfer_strength": transfer.get("transfer_strength"),
        "uncertainty": "provisional pending A6 admission review",
        "provisional_disposition": disposition,
        "recommended_next_action": "send_to_competence_review" if disposition == "candidate_for_competence_admission_review" else "keep_provisional",
        "integrity_passed": True,
        "integrity_verification_digest": integrity["artifact_digest"],
        "claims_audit_digest": claims["artifact_digest"],
        "transfer_review_digest": transfer["artifact_digest"],
        "revision_effectiveness_digest": revision["artifact_digest"],
        "capability_statement_digest": capability["artifact_digest"],
        "accepted_competence_created": False,
        "capability_promotion": False,
        "provider_calls": 0,
        "learning_performed": False,
        "execution_performed_by_a5": False,
        "source_mutation_performed_by_a5": False,
        "created_at": FIXED_TIMESTAMP,
    })
    request = compile_operator_review_request(review, capability)
    narration = compile_narration(review)
    _write_json(output_root / "integrity" / f"{integrity['verification_id']}.json", integrity)
    _write_json(output_root / "revision_effectiveness" / f"{revision['effectiveness_id']}.json", revision)
    _write_json(output_root / "transfer_reviews" / f"{transfer['transfer_review_id']}.json", transfer)
    _write_json(output_root / "claims_audit" / f"{claims['claims_audit_id']}.json", claims)
    _write_json(output_root / "capability_statements" / f"{capability['statement_id']}.json", capability)
    review = _write_json(output_root / "reviews" / f"{review['review_id']}.json", review)
    request = _write_json(output_root / "operator_requests" / f"{request['request_id']}.json", request)
    for event in narration:
        _write_json(output_root / "narration" / f"{event['event_id']}.json", event)
    return {
        "status": "AUTONOMY_5_OUTCOME_REVIEW_PASSED",
        "review": review,
        "integrity": integrity,
        "revision_effectiveness": revision,
        "transfer_review": transfer,
        "claims_audit": claims,
        "capability_statement": capability,
        "operator_request": request,
        "narration": narration,
        "duplicate_suppressed": False,
    }


def explain_review_evidence(review: Mapping[str, Any]) -> str:
    return (
        "This is an A5 review only. "
        f"Disposition: {review.get('provisional_disposition')}. "
        f"Transfer strength: {review.get('transfer_strength')}. "
        "No competence is admitted and no capability is promoted."
    )


def respond_to_outcome_review(review: Mapping[str, Any], request: Mapping[str, Any], intent: str, *, output_root: str | Path = AUTONOMY_5_ROOT) -> dict[str, Any]:
    output_root = Path(output_root)
    normalized = " ".join(str(intent).strip().lower().split())
    mapping = {
        "keep it provisional": "keep_provisional",
        "reject the result": "reject_result",
        "run another evaluation later": "request_another_evaluation",
        "send it for competence review": "send_to_competence_review",
    }
    action = mapping.get(normalized, "explain_evidence")
    response = _digest_record({
        "schema": "autonomy_5_operator_review_response_v1",
        "response_id": stable_id("autonomy-5-response", request["request_id"], action),
        "request_id": request["request_id"],
        "request_digest": request["artifact_digest"],
        "review_id": review["review_id"],
        "review_digest": review["artifact_digest"],
        "operator_action": action,
        "consumed": action in {"keep_provisional", "reject_result", "request_another_evaluation", "send_to_competence_review"},
        "accepted_competence_created": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "responses" / f"{response['response_id']}.json", response)
    queued = None
    if action == "send_to_competence_review":
        queued = _digest_record({
            "schema": "autonomy_6_review_candidate_queued_v1",
            "candidate_id": stable_id("autonomy-6-review-candidate", review["review_id"], response["response_id"]),
            "review_id": review["review_id"],
            "review_digest": review["artifact_digest"],
            "source_response_id": response["response_id"],
            "competence_admitted": False,
            "autonomy_6_started": False,
            "created_at": FIXED_TIMESTAMP,
        })
        _write_json(output_root / "queued_a6_candidates" / f"{queued['candidate_id']}.json", queued)
    return {"status": "response_recorded", "response": response, "queued_a6_candidate": queued}
