"""Topic-neutral constructive-grounding assessment for a strategy prerequisite."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


_FORBIDDEN_KEYS = frozenset({
    "answer_key", "scoring_rule", "rubric", "threshold", "pass_threshold",
    "required_concepts", "forbidden_concepts", "evaluator_provenance",
    "evaluator_view", "evaluation_predicate", "study_resources",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(str(key) in _FORBIDDEN_KEYS or _contains_forbidden(item) for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return any(_contains_forbidden(item) for item in value)
    return False


def _relation_slug(question: Mapping[str, Any]) -> str:
    match = re.search(r"What does (.+?) mean", str(question.get("question") or ""), flags=re.I)
    raw = match.group(1) if match else str(question.get("question_id") or "constructive_grounding")
    return re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_") or "constructive_grounding"


def _rank_candidates(
    candidates: Sequence[Mapping[str, Any]], *, question_id: str, exhausted_locator: str,
) -> tuple[dict[str, Any], ...]:
    weights = {"authoritative_course_material": 1.0, "institutional_notes": 0.9, "open_textbook": 0.85, "open_access_reference": 0.8}
    ranked: list[dict[str, Any]] = []
    for raw in candidates:
        candidate = dict(raw)
        if question_id not in set(str(value) for value in (candidate.get("question_ids") or ())):
            continue
        locator = str(candidate.get("canonical_locator") or "")
        if locator.rstrip("/").lower() == exhausted_locator.rstrip("/").lower():
            continue
        authority = weights.get(str(candidate.get("source_type") or ""), 0.0)
        confidence = float(candidate.get("metadata_confidence") or 0.0)
        cost = float(candidate.get("retrieval_cost") or 1.0)
        score = round(authority * 0.45 + confidence * 0.35 + (1.0 - min(cost, 1.0)) * 0.20, 6)
        ranked.append({
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "title": str(candidate.get("title") or ""),
            "canonical_locator": locator,
            "organization": str(candidate.get("organization") or ""),
            "source_type": str(candidate.get("source_type") or ""),
            "question_ids": (question_id,),
            "relevance_rationale": str(candidate.get("relevance_rationale") or ""),
            "expected_information_gain": float(candidate.get("expected_information_gain") or 0.0),
            "retrieval_cost": cost,
            "metadata_confidence": confidence,
            "uncertainty": str(candidate.get("uncertainty") or "metadata-only relevance"),
            "ranking_score": score,
        })
    return tuple(sorted(ranked, key=lambda item: (-float(item["ranking_score"]), item["canonical_locator"])))


def compile_constructive_grounding_assessment(
    *,
    strategy: Mapping[str, Any],
    latest_revision: Mapping[str, Any],
    acquisition_result: Mapping[str, Any],
    linkage_reassessment: Mapping[str, Any],
    discovery_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Assess one linked-but-insufficient prerequisite using retained evidence only."""

    links = tuple(dict(item) for item in (linkage_reassessment.get("links") or ()) if isinstance(item, Mapping))
    question_ids = tuple(sorted({str(item.get("question_id") or "") for item in links if item.get("sufficiency_status") == "linked_but_not_sufficient"}))
    if len(question_ids) != 1:
        raise ValueError("constructive_grounding_requires_one_linked_insufficient_question")
    question_id = question_ids[0]
    question = next((dict(item) for item in (strategy.get("learning_questions") or ()) if isinstance(item, Mapping) and item.get("question_id") == question_id), {})
    if not question:
        raise ValueError("constructive_grounding_question_not_in_strategy")
    prerequisite_ids = tuple(str(item) for item in (question.get("prerequisite_ids") or ()))
    claims = {str(item.get("claim_id") or ""): dict(item) for item in (acquisition_result.get("claims") or ()) if isinstance(item, Mapping)}
    premise_ids = tuple(str(item.get("claim_id") or "") for item in links)
    if any(premise_id not in claims for premise_id in premise_ids):
        raise ValueError("constructive_grounding_premise_not_retained")
    candidates = _rank_candidates(
        tuple(dict(item) for item in (discovery_result.get("candidates") or ()) if isinstance(item, Mapping)),
        question_id=question_id,
        exhausted_locator=str(acquisition_result.get("source_locator") or ""),
    )
    selected = candidates[0] if candidates else {}
    relation_slug = _relation_slug(question)
    relation_id = stable_id("constructive-grounding-relation", strategy.get("strategy_id"), question_id, acquisition_result.get("result_digest"))
    outcome = f"{relation_slug}_exact_source_authority_pending" if selected else f"{relation_slug}_constructive_grounding_unresolved"
    request = {}
    if selected:
        request = {
            "request_id": stable_id("constructive-grounding-exact-source-authority", relation_id, selected["candidate_id"]),
            "request_kind": "governed_constructive_grounding_exact_source_authority",
            "status": "pending",
            "strategy_id": strategy.get("strategy_id"),
            "latest_revision_id": latest_revision.get("revision_id"),
            "acquisition_result_id": acquisition_result.get("acquisition_result_id"),
            "acquisition_result_digest": acquisition_result.get("result_digest"),
            "linkage_reassessment_id": linkage_reassessment.get("reassessment_id"),
            "relation_id": relation_id,
            "question_id": question_id,
            "candidate_id": selected["candidate_id"],
            "canonical_locator": selected["canonical_locator"],
            "maximum_retrieval_count": 1,
            "authority_scope": "retrieve one exact previously discovered source only to ground one unresolved constructive prerequisite relation",
            "scope": "retrieve one exact previously discovered source only to ground one unresolved constructive prerequisite relation",
            "permitted_responses": (
                "approve_constructive_grounding_exact_source_authority",
                "reject_constructive_grounding_exact_source_authority",
                "defer_constructive_grounding_exact_source_authority",
                "ask_for_clarification",
            ),
            "authority_granted": False,
            "prohibited_actions": (
                "additional_source_retrieval", "new_discovery", "broad_research", "provider_call", "learner_retry",
                "evaluator_run", "capability_update", "pcm_action", "git_action", "deployment",
            ),
            "created_at": utc_now(),
        }
    assessment = {
        "assessment_id": stable_id("constructive-grounding-assessment", relation_id, linkage_reassessment.get("reassessment_digest")),
        "strategy_id": strategy.get("strategy_id"),
        "relation_id": relation_id,
        "relation_proposal": {
            "proposal_origin": "learner_visible_strategy_compilation",
            "target_question_id": question_id,
            "target_question": str(question.get("question") or ""),
            "prerequisite_node_ids": prerequisite_ids,
            "required_relation_facets": (
                "scope contribution", "dependent structural guarantee", "scope limit", "target-concept consequence",
            ),
        },
        "supporting_evidence_ids": premise_ids,
        "supporting_excerpts": tuple({
            "claim_id": premise_id,
            "source_excerpt_reference": str(claims[premise_id].get("source_excerpt_reference") or ""),
            "original_claim_text": str(claims[premise_id].get("claim_text") or ""),
            "support_type": "contextual_reference_only",
        } for premise_id in premise_ids),
        "missing_constructive_relation": "The retained excerpts identify the prerequisite's scope context but do not establish the requested dependency, proof/structural guarantee, scope limit, and target-concept consequence.",
        "derivation_steps": (),
        "constructive_artifact": {},
        "candidate_ranking": candidates,
        "selected_path": "existing_metadata_candidate" if selected else "unresolved",
        "selected_candidate_id": str(selected.get("candidate_id") or ""),
        "authority_request": request,
        "outcome": outcome,
        "sufficiency_status": "unresolved",
        "uncertainty": "No retained learner-visible premise establishes the full constructive relation; candidate metadata is not teaching evidence.",
        "historical_evidence_immutable": True,
        "retrieval_not_performed": True,
        "learner_retry_prohibited": True,
        "evaluator_run_prohibited": True,
        "capability_update_prohibited": True,
        "created_at": utc_now(),
    }
    assessment["assessment_digest"] = _digest(assessment)
    return assessment


def validate_constructive_grounding_assessment(
    assessment: Mapping[str, Any], *, strategy: Mapping[str, Any], acquisition_result: Mapping[str, Any], linkage_reassessment: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if _contains_forbidden(assessment):
        errors.append("evaluator_only_material_present")
    if assessment.get("strategy_id") != strategy.get("strategy_id"):
        errors.append("strategy_binding_mismatch")
    links = {str(item.get("claim_id") or "") for item in (linkage_reassessment.get("links") or ()) if isinstance(item, Mapping)}
    claims = {str(item.get("claim_id") or "") for item in (acquisition_result.get("claims") or ()) if isinstance(item, Mapping)}
    if not set(str(item) for item in (assessment.get("supporting_evidence_ids") or ())).issubset(links & claims):
        errors.append("constructive_premise_not_linked_and_retained")
    if assessment.get("derivation_steps"):
        errors.append("unsupported_derivation_present")
    if assessment.get("constructive_artifact"):
        errors.append("constructive_artifact_without_grounded_derivation")
    request = dict(assessment.get("authority_request") or {})
    if request:
        if request.get("candidate_id") != assessment.get("selected_candidate_id") or int(request.get("maximum_retrieval_count") or 0) != 1:
            errors.append("authority_binding_or_budget_mismatch")
        if request.get("authority_granted"):
            errors.append("authority_self_granted")
    if not assessment.get("retrieval_not_performed") or not assessment.get("learner_retry_prohibited") or not assessment.get("capability_update_prohibited"):
        errors.append("execution_boundary_missing")
    return {"accepted": not errors, "errors": tuple(errors)}


def compile_constructive_grounding_source_review(
    *, assessment: Mapping[str, Any], acquisition_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep acquisition coverage separate from constructive-relation sufficiency."""

    required_facets = tuple(assessment.get("relation_proposal", {}).get("required_relation_facets") or ())
    claims = tuple(dict(item) for item in (acquisition_result.get("claims") or ()) if isinstance(item, Mapping))
    if not claims:
        raise ValueError("constructive_source_review_requires_retained_claim")
    # Source acquisition records only direct excerpts; it has no independently
    # verified derivation/facet structure, so it cannot close this higher gate.
    review = {
        "review_id": stable_id("constructive-grounding-source-review", assessment.get("assessment_id"), acquisition_result.get("result_digest")),
        "assessment_id": assessment.get("assessment_id"),
        "acquisition_result_id": acquisition_result.get("acquisition_result_id"),
        "acquisition_result_digest": acquisition_result.get("result_digest"),
        "source_claim_ids": tuple(str(item.get("claim_id") or "") for item in claims),
        "source_excerpt_references": tuple(str(item.get("source_excerpt_reference") or "") for item in claims),
        "acquisition_term_coverage": str(acquisition_result.get("outcome") or ""),
        "required_relation_facets": required_facets,
        "verified_relation_facets": (),
        "missing_relation_facets": required_facets,
        "derivation_steps": (),
        "outcome": "constructive_grounding_partial",
        "sufficiency_status": "partial",
        "reason": "A retained source excerpt can establish term/scope coverage, but no explicit, source-grounded derivation verifies the required structural relation facets.",
        "historical_acquisition_immutable": True,
        "capability_promotion_prohibited": True,
        "learner_retry_prohibited": True,
        "created_at": utc_now(),
    }
    review["review_digest"] = _digest(review)
    return review


def compile_independent_constructive_grounding_verification(*, assessment: Mapping[str, Any], provider_result: Mapping[str, Any]) -> dict[str, Any]:
    """Compare advisory claims with retained facet evidence without trusting prose.

    This is intentionally generic: a prior retained-source review with no
    verified facets cannot be upgraded merely because an advisory packet is
    well-formed.  A future retained derivation can provide the missing input.
    """
    required = tuple(str(item) for item in (assessment.get("relation_proposal", {}).get("required_relation_facets") or ()))
    sealed = dict(provider_result.get("sealed_advisory_packet") or {})
    source_reviews = tuple(dict(item) for item in (assessment.get("source_review") or {}, assessment.get("followup_source_review") or {}) if isinstance(item, Mapping))
    evidence_ids = tuple(str(item) for review in source_reviews for item in (review.get("source_claim_ids") or ()))
    reviewed: list[dict[str, Any]] = []
    entries = tuple(dict(item) for item in (sealed.get("facet_explanations") or ()) if isinstance(item, Mapping))
    for entry in entries:
        facet = str(entry.get("facet") or "")
        reviewed.append({"advisory_claim_id": stable_id("constructive-advisory-claim", provider_result.get("response_digest"), facet), "provider_claim_text": str(entry.get("explanation") or ""), "relation_facet": facet, "implied_premises": tuple(str(item) for item in (entry.get("assumptions") or ())), "status": "unsupported", "supporting_retained_evidence_ids": (), "derivation_steps": (), "confidence": 0.0, "uncertainty": "no retained evidence or explicit derivation maps this advisory explanation to the requested facet", "verification_method": "retained_source_review_requires_explicit_facet_derivation"})
    decisions = []
    for facet in required:
        claim = next((item for item in reviewed if item["relation_facet"] == facet), {})
        decisions.append({"facet": facet, "status": "unsupported", "supporting_retained_evidence_ids": (), "supporting_advisory_claim_ids": (claim.get("advisory_claim_id"),) if claim else (), "derivation_steps": (), "confidence": 0.0, "unresolved_limitations": "retained sources provided context but no explicit facet derivation; advisory text supplies no independently verifiable premise linkage"})
    result = {"verification_id": stable_id("independent-constructive-grounding-verification", assessment.get("relation_id"), provider_result.get("response_digest")), "relation_id": assessment.get("relation_id"), "question_id": assessment.get("relation_proposal", {}).get("target_question_id"), "advisory_packet_digest": sealed.get("packet_digest"), "raw_provider_response_digest": provider_result.get("response_digest"), "provider_packet_advisory_only": True, "advisory_claims_reviewed": tuple(reviewed), "facet_decisions": tuple(decisions), "retained_source_evidence_considered": evidence_ids, "evaluator_material_present": False, "capability_update_prohibited": True, "learner_attempt_prohibited": True, "outcome": "finite_dimensional_constructive_grounding_partial", "recommended_next_action": "retain_unresolved_facets_and_plan_narrowest_independent_derivation_or_source_action", "created_at": utc_now()}
    result["verification_digest"] = _digest(result)
    return result


def compile_advisory_claim_verification_targets(*, assessment: Mapping[str, Any], provider_result: Mapping[str, Any]) -> dict[str, Any]:
    """Extract only relation-specific propositions from advisory wording.

    It intentionally does not manufacture a source query from a generic
    explanation: that would turn the controller into the ungrounded teacher.
    """
    question = str(assessment.get("relation_proposal", {}).get("target_question") or "")
    anchors = {word for word in re.findall(r"[a-z]{4,}", question.lower()) if word not in {"what", "does", "mean", "relate", "conditions", "that", "with", "from", "this", "theorem"}}
    sealed = dict(provider_result.get("sealed_advisory_packet") or {})
    targets = []
    rejected = []
    for entry in (sealed.get("facet_explanations") or ()):
        if not isinstance(entry, Mapping):
            continue
        text = str(entry.get("explanation") or "")
        matched = sorted(set(re.findall(r"[a-z]{4,}", text.lower())) & anchors)
        claim_id = stable_id("constructive-advisory-claim", provider_result.get("response_digest"), entry.get("facet"))
        if not matched:
            rejected.append({"advisory_claim_id": claim_id, "relation_facet": str(entry.get("facet") or ""), "exact_claim_text": text, "reason": "generic_advisory_explanation_contains_no_relation_specific_proposition"})
            continue
        targets.append({"target_id": stable_id("advisory-claim-verification-target", claim_id, tuple(matched)), "exact_proposition": text, "advisory_claim_id": claim_id, "relation_facet": str(entry.get("facet") or ""), "assumptions": tuple(str(item) for item in (entry.get("assumptions") or ())), "verification_route": "retained_evidence_or_explicit_derivation", "source_or_verification_type": "relation_specific_retained_evidence", "matched_relation_terms": tuple(matched)})
    result = {"target_compilation_id": stable_id("advisory-claim-verification-target-compilation", assessment.get("relation_id"), provider_result.get("response_digest")), "relation_id": assessment.get("relation_id"), "question_id": assessment.get("relation_proposal", {}).get("target_question_id"), "advisory_packet_digest": sealed.get("packet_digest"), "targets": tuple(targets), "rejected_advisory_claims": tuple(rejected), "outcome": "atomic_verification_targets_unavailable" if not targets else "atomic_verification_targets_compiled", "first_incorrect_transition": "validated_advisory_explanation -> no claim-level verification targets -> independent verifier cannot establish or reject proposed premises" if not targets else "atomic_targets -> controlled verification routing", "provider_count_unchanged": True, "created_at": utc_now()}
    result["target_compilation_digest"] = _digest(result)
    return result
