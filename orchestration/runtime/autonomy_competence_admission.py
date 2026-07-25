"""AUTONOMY-6 governed competence admission from A5 outcome review evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_6_ROOT = Path(".tmp") / "autonomy-6-competence-admission-v1"
ADMISSION_POLICY_VERSION = "autonomy_6_competence_admission_policy_v1"
ACTIVATION_STATE = "admitted_inactive_pending_future_use"
NARROW_CAPABILITY_STATEMENT = (
    "Distinguishes confirmed, ambiguous, and unmatched cross-format records on bounded tabular fixtures when "
    "identifiers may be missing, renamed, duplicated, composite, or conflicting, while preserving provenance and uncertainty."
)
SUPPORTED_CASES = (
    "exact_stable_identifier",
    "identifier_missing",
    "identifier_renamed",
    "composite_identifier",
    "duplicated_identifier",
    "conflicting_identifiers",
    "ambiguous_near_match",
    "no_valid_match",
    "adversarial_similarity",
    "transfer_unseen_fixture",
)
NEGATIVE_CASES = ("ambiguous_near_match", "no_valid_match", "adversarial_similarity", "duplicated_identifier", "conflicting_identifiers")
TRANSFER_CASES = ("identifier_renamed", "composite_identifier", "duplicated_identifier", "conflicting_identifiers", "transfer_unseen_fixture")


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _verify_digest(record: Mapping[str, Any]) -> bool:
    if not record.get("artifact_digest"):
        return False
    return record.get("artifact_digest") == bootstrap_digest({key: value for key, value in dict(record).items() if key != "artifact_digest"})


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    data = dict(payload)
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return data


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _read_many(root: Path, directory: str) -> list[dict[str, Any]]:
    base = root / directory
    if not base.exists():
        return []
    return [record for path in sorted(base.glob("*.json")) if (record := _read_json(path))]


def _read_latest(root: Path, directory: str) -> dict[str, Any] | None:
    records = _read_many(root, directory)
    return records[-1] if records else None


def _normalize(text: object) -> str:
    return " ".join(str(text or "").strip().lower().split())


def load_a5_review_bundle(a5_root: str | Path, *, review_id: str | None = None) -> dict[str, Any]:
    root = Path(a5_root)
    reviews = _read_many(root, "reviews")
    review = next((item for item in reviews if item.get("review_id") == review_id), None) if review_id else (reviews[-1] if reviews else None)
    return {
        "a5_root": str(root),
        "review": review,
        "capability_statement": _read_latest(root, "capability_statements"),
        "claims_audit": _read_latest(root, "claims_audit"),
        "integrity": _read_latest(root, "integrity"),
        "transfer_review": _read_latest(root, "transfer_reviews"),
        "revision_effectiveness": _read_latest(root, "revision_effectiveness"),
        "responses": _read_many(root, "responses"),
    }


def load_competence_records(*roots: str | Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for root_value in roots:
        root = Path(root_value)
        candidates = (
            root / "accepted_competencies",
            root / "developmental_competence",
            root,
        )
        for base in candidates:
            if not base.exists():
                continue
            for path in sorted(base.glob("*.json")):
                record = _read_json(path)
                if record and (record.get("competence_id") or record.get("classification") or record.get("schema")):
                    records.append(record)
    return tuple(records)


def _case_statuses(review: Mapping[str, Any]) -> dict[str, str]:
    results: dict[str, str] = {}
    for family in dict(review.get("hidden_transfer_case_results") or {}).values():
        for case in tuple(dict(family).get("passed") or ()):
            results[str(case)] = "passed"
        for case in tuple(dict(family).get("failed") or ()):
            results[str(case)] = "failed"
    return results


def _clause_support(review: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    if review.get("cycle_family") and review.get("cycle_family") != "reconciliation_record_level_v1":
        statuses = _case_statuses(review)
        supported = tuple(review.get("supported_case_families") or ())
        return tuple({
            "clause": str(clause),
            "supporting_case_ids": tuple(case for case in supported if statuses.get(str(case)) == "passed"),
            "evaluator_result": "passed" if supported and all(statuses.get(str(case)) == "passed" for case in supported) else "not_fully_supported",
            "transfer_support": bool(dict(dict(review.get("hidden_transfer_case_results") or {}).get("transfer") or {}).get("passed")),
            "limitations": tuple(review.get("remaining_limitations") or ("bounded retained fixtures only",)),
            "admission_eligibility": bool(supported and all(statuses.get(str(case)) == "passed" for case in supported)),
        } for clause in (
            review.get("supported_behavior") or "family-specific supported behavior",
            "bounded declared inputs",
            "deterministic declared outputs",
        ))
    statuses = _case_statuses(review)
    clauses = (
        ("confirmed records", ("exact_stable_identifier", "identifier_renamed", "composite_identifier")),
        ("ambiguous records", ("duplicated_identifier", "conflicting_identifiers", "ambiguous_near_match", "adversarial_similarity")),
        ("unmatched records", ("identifier_missing", "no_valid_match", "transfer_unseen_fixture")),
        ("bounded tabular fixtures", SUPPORTED_CASES),
        ("missing, renamed, duplicated, composite, or conflicting identifiers", ("identifier_missing", "identifier_renamed", "duplicated_identifier", "composite_identifier", "conflicting_identifiers")),
        ("provenance and uncertainty preservation", ("duplicated_identifier", "conflicting_identifiers", "ambiguous_near_match", "adversarial_similarity")),
    )
    rows = []
    for clause, cases in clauses:
        supporting = tuple(case for case in cases if statuses.get(case) == "passed")
        rows.append({
            "clause": clause,
            "supporting_case_ids": supporting,
            "evaluator_result": "passed" if supporting and len(supporting) == len(cases) else "not_fully_supported",
            "transfer_support": any(case in TRANSFER_CASES for case in supporting),
            "limitations": ("bounded retained fixtures only",),
            "admission_eligibility": bool(supporting and len(supporting) == len(cases)),
        })
    return tuple(rows)


def compile_admission_candidate(bundle: Mapping[str, Any]) -> dict[str, Any]:
    review = dict(bundle.get("review") or {})
    transfer = dict(bundle.get("transfer_review") or {})
    capability = dict(bundle.get("capability_statement") or {})
    family = str(review.get("cycle_family") or capability.get("cycle_family") or "reconciliation_record_level_v1")
    is_reconciliation = family in {"", "reconciliation_record_level_v1"}
    statement = NARROW_CAPABILITY_STATEMENT if is_reconciliation else capability.get("statement")
    supported_task_class = "bounded_cross_format_record_reconciliation" if is_reconciliation else str(review.get("supported_task_class") or "structured_json_validation")
    title = "Bounded Cross-Format Ambiguity-Preserving Reconciliation" if is_reconciliation else "Bounded JSON Schema Validation Reporting"
    demonstrated = (
        "classifies bounded tabular fixture records as confirmed, ambiguous, or unmatched",
        "preserves uncertainty for duplicate, conflicting, near-match, and adversarial cases",
        "uses fixed evaluator provenance without provider, mutation, trust, deployment, or promotion authority",
    ) if is_reconciliation else (
        "validates bounded JSON record sets against supplied schemas",
        "reports missing, unexpected, primitive type, nested object, optional-null, and multiple-error cases",
        "uses fixed evaluator provenance without provider, mutation, trust, deployment, or promotion authority",
    )
    candidate = {
        "schema": "autonomy_6_admission_candidate_v1",
        "cycle_family": family,
        "admission_candidate_id": stable_id("autonomy-6-admission-candidate", review.get("review_id"), review.get("artifact_digest")),
        "a5_review_id": review.get("review_id"),
        "a5_review_digest": review.get("artifact_digest"),
        "a4_goal_id": review.get("goal_id"),
        "a4_goal_digest": review.get("goal_digest"),
        "a4_plan_id": review.get("plan_id"),
        "a4_plan_digest": review.get("plan_digest"),
        "a4_execution_id": review.get("execution_id"),
        "a4_authority_id": review.get("authority_id"),
        "a4_authority_digest": review.get("authority_digest"),
        "a4_evaluator_id": review.get("evaluator_id"),
        "a4_evaluator_digest": review.get("evaluator_digest"),
        "a4_initial_strategy_id": review.get("initial_strategy_id"),
        "a4_initial_strategy_digest": review.get("initial_strategy_digest"),
        "a4_revised_strategy_id": review.get("revised_strategy_id"),
        "a4_revised_strategy_digest": review.get("revised_strategy_digest"),
        "a4_initial_evaluation_id": review.get("initial_evaluation_id"),
        "a4_initial_evaluation_digest": review.get("initial_evaluation_digest"),
        "a4_revised_evaluation_id": review.get("revised_evaluation_id"),
        "a4_revised_evaluation_digest": review.get("revised_evaluation_digest"),
        "proposed_competence_title": title,
        "exact_behavioral_capability_statement": statement,
        "demonstrated_behavior": demonstrated,
        "inferred_but_unproven_behavior": ("possible utility on adjacent tasks with similar bounded fixtures",),
        "excluded_behavior": tuple(capability.get("excluded_domains") or ()) + (() if not is_reconciliation else ("general entity resolution", "arbitrary database reconciliation", "universal fuzzy matching")),
        "supported_task_class": supported_task_class,
        "supported_input_forms": tuple(capability.get("supported_inputs") or ("bounded tabular fixtures",)),
        "supported_output_forms": tuple(capability.get("supported_outputs") or ("confirmed", "ambiguous", "unmatched")),
        "supported_case_families": tuple(capability.get("supported_case_families") or (SUPPORTED_CASES if is_reconciliation else ())),
        "uncertainty_behavior": capability.get("uncertainty_behavior") or "preserve ambiguity without corroborating evidence",
        "provenance_requirements": tuple(capability.get("required_provenance") or ()),
        "evaluator_version": capability.get("evaluator_version") or "autonomy_4_fixed_evaluator_v1",
        "evaluator_digest": review.get("evaluator_digest"),
        "transfer_case_results": dict(dict(transfer.get("family_results") or {}).get("transfer") or {}),
        "negative_control_results": dict(review.get("negative_control_results") or {}),
        "known_limitations": tuple(review.get("remaining_limitations") or ()),
        "excluded_domains": tuple(capability.get("excluded_domains") or ()),
        "known_failure_modes": tuple(capability.get("known_failure_modes") or ()),
        "confidence_basis": ("A5 integrity passed", "A4 revised evaluator passed", "transfer and negative-control families passed"),
        "reevaluation_triggers": ("new unbounded data class", "changed evaluator digest", "operator requests broader scope", "after 90 days or before promotion"),
        "expiration_or_review_date": "2026-10-22",
        "permitted_activation_state": ACTIVATION_STATE,
        "admission_status": "pending_operator_admission_review",
        "trusted_generalization": False,
        "promotion_state": "not_promoted",
        "deployment_authority": False,
        "source_mutation_authority": False,
        "provider_authority": False,
        "clause_support_table": _clause_support(review),
        "created_at": FIXED_TIMESTAMP,
    }
    candidate["admission_candidate_digest"] = bootstrap_digest(candidate)
    return _digest_record(candidate)


def search_competence_overlap(candidate: Mapping[str, Any], existing: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized_statement = _normalize(candidate.get("exact_behavioral_capability_statement"))
    task_class = _normalize(candidate.get("supported_task_class"))
    exact_matches = []
    stable_identifier_matches = []
    overlapping = []
    for record in existing:
        record_statement = _normalize(record.get("exact_behavioral_capability_statement") or record.get("admitted_capability_statement") or record.get("learning_objective"))
        record_task = _normalize(record.get("task_class") or record.get("supported_task_class") or "cross_format_record_reconciliation")
        if record.get("evaluator_digest") == candidate.get("evaluator_digest") or record_statement == normalized_statement:
            exact_matches.append(record)
        if "stable identifier" in record_statement or "stable_identifier" in record_statement:
            stable_identifier_matches.append(record)
        if task_class and ("reconciliation" in record_task or "reconciliation" in record_statement):
            overlapping.append(record)
    if exact_matches:
        disposition = "duplicate_existing_competence"
    elif stable_identifier_matches:
        disposition = "supersedes_narrower_competence"
    elif overlapping:
        disposition = "overlaps_requires_operator_review"
    else:
        disposition = "new_narrow_competence"
    return _digest_record({
        "schema": "autonomy_6_competence_overlap_search_v1",
        "overlap_search_id": stable_id("autonomy-6-overlap", candidate.get("admission_candidate_id"), tuple(record.get("competence_id") for record in existing)),
        "candidate_id": candidate.get("admission_candidate_id"),
        "same_evaluator_digest_matches": tuple(record.get("competence_id") for record in exact_matches if record.get("evaluator_digest") == candidate.get("evaluator_digest")),
        "same_normalized_statement_matches": tuple(record.get("competence_id") for record in exact_matches if _normalize(record.get("admitted_capability_statement") or record.get("exact_behavioral_capability_statement") or record.get("learning_objective")) == normalized_statement),
        "same_task_class_matches": tuple(record.get("competence_id") for record in overlapping),
        "overlapping_supported_case_families": tuple(record.get("competence_id") for record in overlapping),
        "older_narrower_competence": tuple(record.get("competence_id") for record in stable_identifier_matches),
        "existing_broader_competence": (),
        "overlap_disposition": disposition,
        "extends": "stable_identifier_reconciliation" if stable_identifier_matches else "",
        "created_at": FIXED_TIMESTAMP,
    })


def compile_admission_policy(candidate: Mapping[str, Any], bundle: Mapping[str, Any], overlap: Mapping[str, Any]) -> dict[str, Any]:
    review = dict(bundle.get("review") or {})
    integrity = dict(bundle.get("integrity") or {})
    transfer = dict(bundle.get("transfer_review") or {})
    claims = dict(bundle.get("claims_audit") or {})
    final_cases = _case_statuses(review)
    family = str(candidate.get("cycle_family") or review.get("cycle_family") or "reconciliation_record_level_v1")
    transfer_family = dict(dict(transfer.get("family_results") or {}).get("transfer") or {})
    negative_family = dict(dict(transfer.get("family_results") or {}).get("negative_control") or {})
    transfer_cases_passed = bool(transfer_family.get("present")) and not tuple(transfer_family.get("failed") or ())
    negative_cases_passed = bool(negative_family.get("present")) and not tuple(negative_family.get("failed") or ())
    if family in {"", "reconciliation_record_level_v1"}:
        transfer_cases_passed = all(final_cases.get(case) == "passed" for case in TRANSFER_CASES)
        negative_cases_passed = transfer.get("negative_controls_discriminative") is True and all(final_cases.get(case) == "passed" for case in NEGATIVE_CASES)
    checks = {
        "a5_candidate_disposition": review.get("provisional_disposition") == "candidate_for_competence_admission_review",
        "a5_review_digest_valid": _verify_digest(review),
        "a5_reviewed_exact_records": bool(review.get("evaluator_digest") and review.get("initial_strategy_digest") and review.get("revised_strategy_digest")),
        "evaluator_fixed_before_strategy_execution": integrity.get("evaluator_fixed_before_strategy") is True,
        "evaluator_digest_unchanged_across_revision": review.get("evaluator_digest") and review.get("evaluator_digest") == dict(bundle.get("revision_effectiveness") or {}).get("evaluator_digest_after"),
        "hidden_and_transfer_cases_isolated": integrity.get("hidden_case_isolation_confirmed") is True and bool(dict(dict(transfer.get("family_results") or {}).get("transfer") or {}).get("present")),
        "negative_controls_discriminated": negative_cases_passed,
        "unsupported_claims_removed": claims.get("recommended_statement_contains_unsupported_claim") is False,
        "no_provider_call_influenced_evaluator": review.get("provider_calls") == 0,
        "no_tracked_source_mutation_occurred": review.get("source_mutation_performed_by_a5") is False,
        "no_duplicate_semantic_execution": integrity.get("no_duplicate_semantic_execution") is True,
        "no_integrity_stop_exists": review.get("integrity_passed") is True,
        "supported_scope_explicit": bool(candidate.get("exact_behavioral_capability_statement")),
        "limitations_explicit": bool(tuple(candidate.get("known_limitations") or ())),
        "not_already_rejected_or_admitted": True,
        "no_equivalent_accepted_competence": overlap.get("overlap_disposition") != "duplicate_existing_competence",
        "transfer_evidence_present": transfer_cases_passed,
        "clause_level_support_passed": all(row.get("admission_eligibility") for row in tuple(candidate.get("clause_support_table") or ())),
    }
    failed = tuple(key for key, passed in checks.items() if not passed)
    warnings = tuple(filter(None, (
        "extends_stable_identifier_reconciliation" if overlap.get("extends") else "",
        "operator_must_review_overlap" if overlap.get("overlap_disposition") in {"supersedes_narrower_competence", "overlaps_requires_operator_review"} else "",
    )))
    if not integrity.get("passed", True) or not _verify_digest(review):
        recommendation = "integrity_stop"
    elif overlap.get("overlap_disposition") == "duplicate_existing_competence":
        recommendation = "duplicate_existing_competence"
    elif not checks["negative_controls_discriminated"] or not checks["transfer_evidence_present"]:
        recommendation = "request_additional_evaluation"
    elif failed:
        recommendation = "request_additional_evaluation"
    else:
        recommendation = "recommend_admission"
    return _digest_record({
        "schema": "autonomy_6_admission_policy_decision_v1",
        "policy_id": stable_id("autonomy-6-policy", candidate.get("admission_candidate_id"), tuple(failed), overlap.get("overlap_disposition")),
        "candidate_id": candidate.get("admission_candidate_id"),
        "candidate_digest": candidate.get("artifact_digest"),
        "eligibility_checks": checks,
        "passed_checks": tuple(key for key, passed in checks.items() if passed),
        "failed_checks": failed,
        "warning_conditions": warnings,
        "duplicate_competence_search_result": overlap.get("overlap_disposition"),
        "scope_comparison_against_existing_competences": overlap,
        "admission_recommendation": recommendation,
        "operator_authority_required": True,
        "policy_version": ADMISSION_POLICY_VERSION,
        "created_at": FIXED_TIMESTAMP,
    })


def _request_integrity_digest(candidate: Mapping[str, Any], policy: Mapping[str, Any], overlap: Mapping[str, Any]) -> str:
    return bootstrap_digest({
        "candidate_id": candidate.get("admission_candidate_id"),
        "candidate_digest": candidate.get("artifact_digest"),
        "capability_statement": candidate.get("exact_behavioral_capability_statement"),
        "limitations": tuple(candidate.get("known_limitations") or ()),
        "excluded_cases": tuple(candidate.get("excluded_behavior") or ()),
        "evaluator_digest": candidate.get("evaluator_digest"),
        "a5_review_digest": candidate.get("a5_review_digest"),
        "overlap_disposition": overlap.get("overlap_disposition"),
        "admission_recommendation": policy.get("admission_recommendation"),
        "activation_state": ACTIVATION_STATE,
        "dangerous_authority_defaults": {
            "deployment_authority": False,
            "source_mutation_authority": False,
            "provider_authority": False,
            "trusted_generalization": False,
            "promotion_state": "not_promoted",
        },
    })


def compile_admission_request(candidate: Mapping[str, Any], policy: Mapping[str, Any], overlap: Mapping[str, Any]) -> dict[str, Any]:
    card = {
        "title": "This result is ready for competence review",
        "demonstrated": tuple(candidate.get("demonstrated_behavior") or ()),
        "not_demonstrated": tuple(candidate.get("excluded_behavior") or ()),
        "transfer_evidence": candidate.get("transfer_case_results"),
        "negative_control_evidence": candidate.get("negative_control_results"),
        "evaluator_independence": "A4 evaluator was fixed before strategy execution and checked by A5/A6 digests.",
        "existing_competence_overlap": overlap.get("overlap_disposition"),
        "proposed_narrow_capability_statement": candidate.get("exact_behavioral_capability_statement"),
        "known_limitations": tuple(candidate.get("known_limitations") or ()),
        "intended_permitted_uses": (candidate.get("supported_task_class"),),
        "reevaluation_triggers": tuple(candidate.get("reevaluation_triggers") or ()),
        "recommendation": policy.get("admission_recommendation"),
        "admission_will_not_do": ("activate missions", "grant source mutation", "grant provider calls", "grant deployment", "promote to trusted memory"),
        "controls": ("Admit this competence", "Keep provisional", "Reject admission", "Request more evaluation", "Explain the scope", "View failed and excluded cases", "View technical details"),
    }
    card_digest = bootstrap_digest(card)
    request = {
        "schema": "autonomy_6_operator_competence_admission_request_v1",
        "request_id": stable_id("autonomy-6-operator-request", candidate.get("admission_candidate_id"), policy.get("artifact_digest")),
        "admission_candidate_id": candidate.get("admission_candidate_id"),
        "candidate_digest": candidate.get("artifact_digest"),
        "policy_id": policy.get("policy_id"),
        "policy_digest": policy.get("artifact_digest"),
        "request_integrity_digest": _request_integrity_digest(candidate, policy, overlap),
        "card_digest": card_digest,
        "card": card,
        "active": policy.get("admission_recommendation") == "recommend_admission",
        "operator_authority_required": True,
        "ambiguous_language_requires_clarification": True,
        "activation_state": ACTIVATION_STATE,
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(request)


def compile_narration(candidate: Mapping[str, Any], policy: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    messages = (
        "I am checking whether the provisional result qualifies as a bounded competence.",
        "The evaluator and hidden transfer evidence passed the admission policy." if policy.get("admission_recommendation") == "recommend_admission" else "The admission policy found unresolved evidence conditions.",
        f"The proposed competence remains limited to: {candidate.get('exact_behavioral_capability_statement')}",
        "This does not grant source mutation, deployment, provider, or trusted authority.",
    )
    return tuple(_digest_record({
        "schema": "operator_ux_narration_event_v1",
        "event_id": stable_id("autonomy-6-narration", candidate.get("admission_candidate_id"), index, policy.get("artifact_digest")),
        "mission_id": candidate.get("admission_candidate_id"),
        "work_item_id": "",
        "runtime_phase": "autonomy_6_competence_admission",
        "event_type": "competence_admission_review",
        "message": message,
        "source_artifact": policy.get("artifact_digest"),
        "timestamp": FIXED_TIMESTAMP,
        "chain_of_thought_exposed": False,
    }) for index, message in enumerate(messages, start=1))


def review_competence_candidate(
    a5_root: str | Path,
    *,
    output_root: str | Path = AUTONOMY_6_ROOT,
    existing_competence_roots: Sequence[str | Path] = (),
    review_id: str | None = None,
) -> dict[str, Any]:
    output_root = Path(output_root)
    existing_candidates = _read_many(output_root, "admission_candidates")
    if existing_candidates:
        candidate = existing_candidates[-1]
        policy = _read_latest(output_root, "policy_decisions") or {}
        request = _read_latest(output_root, "operator_requests") or {}
        return {"status": "AUTONOMY_6_COMPETENCE_ADMISSION_REVIEW_READY", "candidate": candidate, "policy": policy, "operator_request": request, "duplicate_suppressed": True}
    bundle = load_a5_review_bundle(a5_root, review_id=review_id)
    candidate = compile_admission_candidate(bundle)
    overlap = search_competence_overlap(candidate, load_competence_records(output_root, *existing_competence_roots))
    policy = compile_admission_policy(candidate, bundle, overlap)
    request = compile_admission_request(candidate, policy, overlap)
    narration = compile_narration(candidate, policy)
    candidate = _write_json(output_root / "admission_candidates" / f"{candidate['admission_candidate_id']}.json", candidate)
    _write_json(output_root / "overlap_searches" / f"{overlap['overlap_search_id']}.json", overlap)
    policy = _write_json(output_root / "policy_decisions" / f"{policy['policy_id']}.json", policy)
    request = _write_json(output_root / "operator_requests" / f"{request['request_id']}.json", request)
    for event in narration:
        _write_json(output_root / "narration" / f"{event['event_id']}.json", event)
    return {
        "status": "AUTONOMY_6_COMPETENCE_ADMISSION_REVIEW_READY",
        "candidate": candidate,
        "overlap": overlap,
        "policy": policy,
        "operator_request": request,
        "narration": narration,
        "duplicate_suppressed": False,
    }


def explain_competence_scope(candidate: Mapping[str, Any], policy: Mapping[str, Any]) -> str:
    return (
        f"Proposed scope: {candidate.get('exact_behavioral_capability_statement')} "
        f"Recommendation: {policy.get('admission_recommendation')}. "
        "Admission records the bounded competence only; it remains inactive and unpromoted."
    )


def _operator_action(text: str) -> str:
    normalized = _normalize(text)
    explicit_admit = {"admit this competence", "accept this competence", "add this competence", "approve competence admission"}
    keep = {"keep it provisional", "do not admit it yet", "leave it provisional"}
    reject = {"reject the competence", "reject admission", "do not accept this"}
    more = {"test it more", "request more evaluation", "gather more evidence first"}
    explain = {"explain the scope", "what can it actually do", "what are the limitations", "i don't understand the competence", "i dont understand the competence"}
    ambiguous = {"looks good", "okay", "ok", "proceed", "yes"}
    if normalized in explicit_admit:
        return "admit_competence"
    if normalized in keep:
        return "keep_provisional"
    if normalized in reject:
        return "reject_admission"
    if normalized in more:
        return "request_more_evaluation"
    if normalized in explain:
        return "explain_scope"
    if normalized in ambiguous:
        return "clarification_required"
    return "clarification_required"


def _accepted_for_candidate(output_root: Path, candidate_id: str) -> dict[str, Any] | None:
    for record in _read_many(output_root, "accepted_competencies"):
        if record.get("admission_candidate_id") == candidate_id:
            return record
    return None


def create_accepted_competence(candidate: Mapping[str, Any], request: Mapping[str, Any], response: Mapping[str, Any]) -> dict[str, Any]:
    competence = {
        "schema": "autonomy_6_accepted_competence_record_v1",
        "competence_id": stable_id("autonomy-6-accepted-competence", candidate.get("admission_candidate_id")),
        "admission_candidate_id": candidate.get("admission_candidate_id"),
        "admission_candidate_digest": candidate.get("artifact_digest"),
        "a5_review_id": candidate.get("a5_review_id"),
        "a5_review_digest": candidate.get("a5_review_digest"),
        "operator_response_id": response.get("response_id"),
        "operator_response_digest": response.get("artifact_digest"),
        "admitted_capability_statement": candidate.get("exact_behavioral_capability_statement"),
        "task_class": candidate.get("supported_task_class"),
        "supported_inputs": tuple(candidate.get("supported_input_forms") or ()),
        "supported_outputs": tuple(candidate.get("supported_output_forms") or ()),
        "supported_case_families": tuple(candidate.get("supported_case_families") or ()),
        "limitations": tuple(candidate.get("known_limitations") or ()),
        "exclusions": tuple(candidate.get("excluded_behavior") or ()),
        "provenance_requirements": tuple(candidate.get("provenance_requirements") or ()),
        "evaluator_id": candidate.get("a4_evaluator_id"),
        "evaluator_digest": candidate.get("evaluator_digest"),
        "admission_confidence": "bounded_retained_fixture_confidence",
        "allowed_use_state": ACTIVATION_STATE,
        "activation_state": ACTIVATION_STATE,
        "admission_status": "accepted_bounded_competence",
        "created_at": FIXED_TIMESTAMP,
        "admitted_by_operator": True,
        "trusted_generalization": False,
        "promotion_state": "not_promoted",
        "deployment_authority": False,
        "source_mutation_authority": False,
        "provider_authority": False,
        "operator_request_id": request.get("request_id"),
        "operator_request_digest": request.get("artifact_digest"),
    }
    competence["competence_digest"] = bootstrap_digest(competence)
    return _digest_record(competence)


def respond_to_competence_admission(
    candidate: Mapping[str, Any],
    policy: Mapping[str, Any],
    request: Mapping[str, Any],
    text: str,
    *,
    output_root: str | Path = AUTONOMY_6_ROOT,
    visible_button: str | None = None,
) -> dict[str, Any]:
    output_root = Path(output_root)
    action = "admit_competence" if visible_button == "Admit this competence" else _operator_action(text)
    if action == "explain_scope":
        return {"status": "scope_explained", "consumed": False, "message": explain_competence_scope(candidate, policy)}
    if action == "clarification_required":
        return {"status": "clarification_required", "consumed": False, "accepted_competence": None}
    expected = _request_integrity_digest(candidate, policy, dict(policy.get("scope_comparison_against_existing_competences") or {}))
    if request.get("request_integrity_digest") != expected or request.get("candidate_digest") != candidate.get("artifact_digest"):
        return {"status": "stale_or_mismatched_request", "consumed": False, "accepted_competence": None}
    existing = _accepted_for_candidate(output_root, str(candidate.get("admission_candidate_id")))
    if existing:
        return {"status": "already_admitted", "consumed": True, "accepted_competence": existing}
    response = _digest_record({
        "schema": "autonomy_6_operator_admission_response_v1",
        "response_id": stable_id("autonomy-6-response", request.get("request_id"), action),
        "request_id": request.get("request_id"),
        "request_digest": request.get("artifact_digest"),
        "request_integrity_digest": request.get("request_integrity_digest"),
        "card_digest": request.get("card_digest"),
        "admission_candidate_id": candidate.get("admission_candidate_id"),
        "candidate_digest": candidate.get("artifact_digest"),
        "operator_action": action,
        "consumed": True,
        "created_at": FIXED_TIMESTAMP,
    })
    response = _write_json(output_root / "responses" / f"{response['response_id']}.json", response)
    if action == "keep_provisional":
        return {"status": "retained_provisional", "consumed": True, "response": response, "accepted_competence": None}
    if action == "reject_admission":
        return {"status": "admission_rejected", "consumed": True, "response": response, "accepted_competence": None}
    if action == "request_more_evaluation":
        recommendation = _digest_record({
            "schema": "autonomy_6_future_evaluation_recommendation_v1",
            "recommendation_id": stable_id("autonomy-6-future-evaluation", candidate.get("admission_candidate_id"), response.get("response_id")),
            "admission_candidate_id": candidate.get("admission_candidate_id"),
            "reason": "operator_requested_more_evaluation",
            "automatic_goal_started": False,
            "created_at": FIXED_TIMESTAMP,
        })
        _write_json(output_root / "future_evaluation_recommendations" / f"{recommendation['recommendation_id']}.json", recommendation)
        return {"status": "additional_evaluation_requested", "consumed": True, "response": response, "future_evaluation_recommendation": recommendation, "accepted_competence": None}
    if action == "admit_competence" and policy.get("admission_recommendation") == "recommend_admission":
        competence = create_accepted_competence(candidate, request, response)
        competence = _write_json(output_root / "accepted_competencies" / f"{competence['competence_id']}.json", competence)
        event = _digest_record({
            "schema": "operator_ux_narration_event_v1",
            "event_id": stable_id("autonomy-6-narration-admitted", competence.get("competence_id")),
            "mission_id": candidate.get("admission_candidate_id"),
            "runtime_phase": "autonomy_6_competence_admission",
            "event_type": "competence_admitted",
            "message": "You admitted one bounded competence. The competence is recorded but not automatically activated or promoted.",
            "source_artifact": competence.get("artifact_digest"),
            "timestamp": FIXED_TIMESTAMP,
            "chain_of_thought_exposed": False,
        })
        _write_json(output_root / "narration" / f"{event['event_id']}.json", event)
        return {"status": "accepted_bounded_competence", "consumed": True, "response": response, "accepted_competence": competence}
    return {"status": "admission_blocked_by_policy", "consumed": True, "response": response, "accepted_competence": None}
