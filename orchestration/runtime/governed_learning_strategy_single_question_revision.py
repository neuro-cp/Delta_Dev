"""Single-question revisions from retained learner-visible acquisition evidence.

This module classifies one remaining strategy question without retrieving a
source or changing a prior acquisition result.  It is intentionally limited to
metadata and already retained learner-visible claims.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence
import unicodedata

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


_FORBIDDEN_KEYS = frozenset({
    "answer_key", "scoring_rule", "rubric", "threshold", "pass_threshold",
    "required_concepts", "forbidden_concepts", "evaluator_provenance",
    "evaluator_view", "evaluation_predicate", "study_resources",
})
_COMPILER_VERSION = 3


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(str(key) in _FORBIDDEN_KEYS or _contains_forbidden(item) for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return any(_contains_forbidden(item) for item in value)
    return False


def _topic_term(question: str) -> str:
    match = re.search(r"What does (.+?) mean", question, flags=re.I)
    return match.group(1).strip().lower() if match else ""


def _normalize_pdf_hyphenation(value: str) -> str:
    """Normalize only a line-break-like hyphen followed by whitespace."""

    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"(?<=\w)-\s+(?=\w)", "", normalized)
    return normalized


def _normalized_term_present(term: str, text: str) -> bool:
    """Match hyphenated learner terms after generic PDF dehyphenation."""

    parts = tuple(part for part in term.lower().split("-") if part)
    if not parts:
        return False
    return bool(re.search(r"[-\s]*".join(re.escape(part) for part in parts), _normalize_pdf_hyphenation(text)))


def _rank_existing_candidates(
    candidates: Sequence[Mapping[str, Any]], *, question_id: str, exhausted_locator: str,
) -> tuple[dict[str, Any], ...]:
    """Rank retained discovery metadata, without opening a candidate source."""

    ranked: list[dict[str, Any]] = []
    authority_weight = {
        "authoritative_course_material": 1.0,
        "institutional_notes": 0.9,
        "open_textbook": 0.85,
        "open_access_reference": 0.8,
    }
    for raw in candidates:
        candidate = dict(raw)
        if str(candidate.get("canonical_locator") or "").rstrip("/").lower() == exhausted_locator.rstrip("/").lower():
            continue
        if question_id not in set(str(item) for item in (candidate.get("question_ids") or ())):
            continue
        authority = authority_weight.get(str(candidate.get("source_type") or ""), 0.0)
        metadata_confidence = float(candidate.get("metadata_confidence") or 0.0)
        cost = float(candidate.get("retrieval_cost") or 1.0)
        score = round(authority * 0.45 + metadata_confidence * 0.35 + (1.0 - min(cost, 1.0)) * 0.20, 6)
        ranked.append({
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "title": str(candidate.get("title") or ""),
            "canonical_locator": str(candidate.get("canonical_locator") or ""),
            "organization": str(candidate.get("organization") or ""),
            "source_type": str(candidate.get("source_type") or ""),
            "question_ids": (question_id,),
            "expected_relevance": str(candidate.get("relevance_rationale") or ""),
            "authority_provenance_quality": authority,
            "expected_information_gain": float(candidate.get("expected_information_gain") or 0.0),
            "duplication_risk": "metadata_only_distinct_from_exhausted_sources",
            "retrieval_cost": cost,
            "confidence": metadata_confidence,
            "uncertainty": str(candidate.get("uncertainty") or "metadata-only relevance"),
            "ranking_score": score,
        })
    return tuple(sorted(ranked, key=lambda item: (-float(item["ranking_score"]), item["canonical_locator"])))


def compile_single_question_learning_strategy_revision(
    *,
    strategy: Mapping[str, Any],
    acquisition_result: Mapping[str, Any],
    discovery_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Record one unresolved question and classify retained-evidence linkage."""

    unresolved = tuple(
        dict(item) for item in (acquisition_result.get("question_sufficiency") or ())
        if isinstance(item, Mapping) and str(item.get("status") or "") != "answered"
    )
    if len(unresolved) != 1:
        raise ValueError("single_question_revision_requires_exactly_one_unresolved_question")
    question_id = str(unresolved[0].get("question_id") or "")
    question = next((dict(item) for item in (strategy.get("learning_questions") or ()) if isinstance(item, Mapping) and item.get("question_id") == question_id), {})
    if not question:
        raise ValueError("unresolved_question_not_present_in_strategy")
    term = _topic_term(str(question.get("question") or ""))
    relevant_claims = tuple(dict(item) for item in (acquisition_result.get("claims") or ()) if isinstance(item, Mapping))
    linkage_hits = tuple({
        "claim_id": str(claim.get("claim_id") or ""),
        "source_excerpt_reference": str(claim.get("source_excerpt_reference") or ""),
        "normalized_term_present": _normalized_term_present(term, str(claim.get("claim_text") or "")),
        "original_term_present": term in str(claim.get("claim_text") or "").lower(),
    } for claim in relevant_claims if _normalized_term_present(term, str(claim.get("claim_text") or "")))
    linkage_defect = bool(linkage_hits) and not any(hit["original_term_present"] for hit in linkage_hits)
    ranking = _rank_existing_candidates(
        tuple(dict(item) for item in (discovery_result.get("candidates") or ()) if isinstance(item, Mapping)),
        question_id=question_id,
        exhausted_locator=str(acquisition_result.get("source_locator") or ""),
    )
    outcome = "finite_dimensional_evidence_linkage_repair_required" if linkage_defect else "learning_strategy_single_question_revised"
    revision = {
        "revision_id": stable_id(
            "governed-learning-strategy-single-question-revision",
            _COMPILER_VERSION, strategy.get("strategy_id"), acquisition_result.get("result_digest"), discovery_result.get("result_digest"), question_id,
        ),
        "revision_version": _COMPILER_VERSION,
        "strategy_id": strategy.get("strategy_id"),
        "prior_acquisition_result_id": acquisition_result.get("acquisition_result_id"),
        "prior_acquisition_result_digest": acquisition_result.get("result_digest"),
        "discovery_result_id": discovery_result.get("discovery_result_id"),
        "discovery_result_digest": discovery_result.get("result_digest"),
        "active_question_id": question_id,
        "active_question": str(question.get("question") or ""),
        "question_disposition": "retained_unchanged",
        "sufficiency_condition": str(question.get("sufficiency_condition") or ""),
        "prior_missing_information": str(unresolved[0].get("missing_information") or ""),
        "reason_ucsB_insufficient": (
            "The raw acquisition matcher required literal source-text containment; it did not normalize PDF hyphenation before comparing the learner-authored term."
            if linkage_defect else "No retained learner-visible claim directly met the question's sufficiency condition."
        ),
        "evidence_classification": "topic_neutral_pdf_hyphenation_linkage_defect" if linkage_defect else "genuinely_missing_or_insufficient_teaching_evidence",
        "first_incorrect_transition": (
            "extracted_pdf_text -> raw_literal_question_term_match -> finite-dimensional claim left unlinked"
            if linkage_defect else "retained_claims -> sufficiency_evaluation -> no direct learner-visible support"
        ),
        "bounded_repair_proposal": (
            "Normalize only PDF line-break hyphenation before topic-neutral term matching, then rerun the existing sufficiency evaluation without mutating historical acquisition results."
            if linkage_defect else "None; candidate metadata may support a future separately approved retrieval."
        ),
        "linkage_evidence": linkage_hits,
        "existing_candidate_ranking": ranking,
        "recommended_candidate_id": "" if linkage_defect or not ranking else str(ranking[0]["candidate_id"]),
        "outcome": outcome,
        "retrieval_authority_compiled": False,
        "retrieval_not_performed": True,
        "learner_retry_prohibited": True,
        "evaluator_run_prohibited": True,
        "capability_update_prohibited": True,
        "created_at": utc_now(),
    }
    revision["revision_digest"] = _digest(revision)
    return revision


def validate_single_question_learning_strategy_revision(
    revision: Mapping[str, Any], *, strategy: Mapping[str, Any], acquisition_result: Mapping[str, Any], discovery_result: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if _contains_forbidden(revision):
        errors.append("evaluator_only_material_present")
    if revision.get("strategy_id") != strategy.get("strategy_id"):
        errors.append("strategy_binding_mismatch")
    if revision.get("prior_acquisition_result_digest") != acquisition_result.get("result_digest"):
        errors.append("acquisition_binding_mismatch")
    if revision.get("discovery_result_digest") != discovery_result.get("result_digest"):
        errors.append("discovery_binding_mismatch")
    unresolved = tuple(str(item.get("question_id") or "") for item in (acquisition_result.get("question_sufficiency") or ()) if isinstance(item, Mapping) and item.get("status") != "answered")
    if unresolved != (str(revision.get("active_question_id") or ""),):
        errors.append("single_unresolved_question_not_preserved")
    if revision.get("question_disposition") != "retained_unchanged":
        errors.append("historical_sufficiency_mutated")
    if revision.get("outcome") not in {"finite_dimensional_evidence_linkage_repair_required", "learning_strategy_single_question_revised"}:
        errors.append("invalid_single_question_outcome")
    if not revision.get("retrieval_not_performed") or revision.get("retrieval_authority_compiled"):
        errors.append("retrieval_boundary_violated")
    return {"accepted": not errors, "errors": tuple(errors)}
