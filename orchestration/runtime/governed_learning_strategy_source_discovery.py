"""Metadata-only source discovery for approved learning-strategy revisions."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse, urlsplit, urlunsplit

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


_ALLOWED_SOURCE_TYPES = frozenset({
    "authoritative_course_material", "institutional_notes", "open_access_reference", "open_textbook",
})
_FORBIDDEN_CONTENT_KEYS = frozenset({"body", "content", "content_text", "sanitized_text", "excerpt", "study_resources", "answer_key", "evaluator_view"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _canonical_locator(value: str) -> str:
    """Normalize scheme/host only; source paths can be case-sensitive."""

    parsed = urlsplit(str(value).strip())
    host = (parsed.hostname or "").lower()
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme.lower(), host, parsed.path, parsed.query, parsed.fragment))


def _candidate_rejection_reason(
    candidate: Mapping[str, Any], *, unresolved_question_ids: set[str], exhausted_locators: set[str],
) -> str:
    locator = _canonical_locator(str(candidate.get("canonical_locator") or ""))
    parsed = urlparse(locator)
    if any(key in _FORBIDDEN_CONTENT_KEYS for key in candidate):
        return "source_body_or_prohibited_material_present"
    if parsed.scheme != "https" or not parsed.hostname:
        return "locator_not_canonical_https"
    if not str(candidate.get("title") or "").strip() or not str(candidate.get("organization") or "").strip():
        return "public_metadata_identity_incomplete"
    if str(candidate.get("source_type") or "") not in _ALLOWED_SOURCE_TYPES:
        return "source_type_not_authoritative_or_open"
    if not set(str(item) for item in (candidate.get("question_ids") or ())).intersection(unresolved_question_ids):
        return "does_not_map_to_unresolved_question"
    if locator in exhausted_locators:
        return "duplicate_or_exhausted_retained_source"
    if not str(candidate.get("relevance_rationale") or "").strip():
        return "metadata_relevance_unproven"
    provenance = candidate.get("provenance")
    if not isinstance(provenance, Mapping) or not str(provenance.get("discovery_method") or "").strip() or not str(provenance.get("observed_at") or "").strip():
        return "metadata_provenance_incomplete"
    return ""


def compile_metadata_only_source_discovery_result(
    *,
    revision: Mapping[str, Any],
    metadata_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate, retain, and rank at most three metadata-only candidates."""

    request = dict(revision.get("authority_request") or {})
    constraints = dict(request.get("discovery_constraints") or {})
    unresolved = tuple(str(item) for item in (revision.get("unresolved_question_ids") or ()))
    limit = int(constraints.get("maximum_result_count") or 0)
    if limit < 1 or limit > 3:
        raise ValueError("source_discovery_limit_invalid")
    exhausted = {
        _canonical_locator(str(item.get("source_locator") or ""))
        for item in (revision.get("retained_source_inventory") or ()) if isinstance(item, Mapping)
    }
    retained: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in metadata_candidates:
        candidate = dict(raw)
        locator = _canonical_locator(str(candidate.get("canonical_locator") or ""))
        reason = _candidate_rejection_reason(candidate, unresolved_question_ids=set(unresolved), exhausted_locators=exhausted)
        if not reason and locator in seen:
            reason = "duplicate_discovered_locator"
        if reason:
            rejected.append({
                "candidate_reference": str(candidate.get("candidate_id") or locator or "unknown"),
                "canonical_locator": locator,
                "rejection_reason": reason,
            })
            continue
        seen.add(locator)
        coverage = len(set(str(item) for item in (candidate.get("question_ids") or ())).intersection(unresolved))
        authority = {"authoritative_course_material": 1.0, "institutional_notes": 0.9, "open_textbook": 0.85, "open_access_reference": 0.8}[str(candidate["source_type"])]
        access = 1.0 if str(candidate.get("access_type") or "") == "open_access" else 0.6
        confidence = float(candidate.get("metadata_confidence") or 0.0)
        score = round((authority * 0.35) + (coverage / max(1, len(unresolved)) * 0.35) + (access * 0.15) + (confidence * 0.15), 6)
        retained.append({
            "candidate_id": stable_id("learning-strategy-discovered-source", revision.get("revision_id"), locator),
            "title": str(candidate["title"]),
            "canonical_locator": locator,
            "organization": str(candidate["organization"]),
            "source_type": str(candidate["source_type"]),
            "access_type": str(candidate.get("access_type") or "unknown"),
            "publication_or_course_identity": str(candidate.get("publication_or_course_identity") or ""),
            "provenance": dict(candidate.get("provenance") or {}),
            "question_ids": tuple(sorted(set(str(item) for item in (candidate.get("question_ids") or ())).intersection(unresolved))),
            "relevance_rationale": str(candidate["relevance_rationale"]),
            "retrieval_authority_required": True,
            "retrieval_not_authorized": True,
            "duplication_relationship": "distinct_from_retained_sources",
            "metadata_confidence": confidence,
            "uncertainty": str(candidate.get("uncertainty") or "metadata-only relevance; body content has not been inspected"),
            "expected_information_gain": round(coverage / max(1, len(unresolved)) * authority, 6),
            "retrieval_cost": float(candidate.get("retrieval_cost") or 0.2),
            "ranking_score": score,
        })
    retained = sorted(retained, key=lambda item: (-float(item["ranking_score"]), float(item["retrieval_cost"]), item["canonical_locator"]))[:limit]
    payload = {
        "revision_id": revision.get("revision_id"), "authority_request_id": request.get("request_id"),
        "retained": retained, "rejected": rejected, "unresolved": unresolved,
    }
    return {
        "discovery_result_id": stable_id("learning-strategy-source-discovery", _digest(payload)),
        "revision_id": revision.get("revision_id"),
        "authority_request_id": request.get("request_id"),
        "discovery_scope_digest": _digest(constraints),
        "metadata_only": True,
        "source_body_retention_prohibited": True,
        "retrieval_not_performed": True,
        "candidates": tuple(retained),
        "rejected_candidates": tuple(rejected),
        "recommended_candidate_id": retained[0]["candidate_id"] if retained else "",
        "status": "learning_strategy_source_discovery_completed" if retained else "learning_strategy_source_discovery_insufficient",
        "result_digest": _digest(payload),
        "created_at": utc_now(),
    }


def validate_metadata_only_source_discovery_result(
    result: Mapping[str, Any], *, revision: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify bounded metadata discovery without acquisition authority leakage."""

    errors: list[str] = []
    request = dict(revision.get("authority_request") or {})
    if result.get("revision_id") != revision.get("revision_id") or result.get("authority_request_id") != request.get("request_id"):
        errors.append("revision_or_authority_binding_mismatch")
    candidates = tuple(result.get("candidates") or ())
    if len(candidates) > 3:
        errors.append("candidate_limit_exceeded")
    if not result.get("metadata_only") or not result.get("source_body_retention_prohibited") or not result.get("retrieval_not_performed"):
        errors.append("metadata_only_boundary_missing")
    unresolved = set(str(item) for item in (revision.get("unresolved_question_ids") or ()))
    for candidate in candidates:
        reason = _candidate_rejection_reason(dict(candidate), unresolved_question_ids=unresolved, exhausted_locators={
            _canonical_locator(str(item.get("source_locator") or ""))
            for item in (revision.get("retained_source_inventory") or ()) if isinstance(item, Mapping)
        })
        if reason:
            errors.append(f"invalid_candidate:{reason}")
        if not candidate.get("retrieval_not_authorized"):
            errors.append("candidate_implies_retrieval_authority")
    return {"accepted": not errors, "errors": tuple(errors)}


def compile_discovered_source_retrieval_authority_request(
    *,
    strategy: Mapping[str, Any],
    revision: Mapping[str, Any],
    discovery_result: Mapping[str, Any],
    replacement_nonce: str = "",
) -> dict[str, Any]:
    """Compile one retrieval boundary for the discovery-ranked candidate only."""

    candidate_id = str(discovery_result.get("recommended_candidate_id") or "")
    candidate = next((dict(item) for item in (discovery_result.get("candidates") or ()) if isinstance(item, Mapping) and item.get("candidate_id") == candidate_id), {})
    if not candidate:
        raise ValueError("recommended_discovery_candidate_missing")
    unresolved = tuple(str(item) for item in (revision.get("unresolved_question_ids") or ()))
    if set(str(item) for item in (candidate.get("question_ids") or ())) != set(unresolved):
        raise ValueError("recommended_candidate_question_set_mismatch")
    discovery_digest = str(discovery_result.get("result_digest") or _digest(discovery_result))
    request = {
        "request_id": stable_id("learning-strategy-discovered-source-retrieval-authority", revision.get("revision_id"), discovery_digest, candidate_id, replacement_nonce or "initial"),
        "request_kind": "governed_learning_strategy_discovered_source_retrieval_authority",
        "status": "pending",
        "strategy_id": strategy.get("strategy_id"),
        "revision_id": revision.get("revision_id"),
        "discovery_result_id": discovery_result.get("discovery_result_id"),
        "discovery_result_digest": discovery_digest,
        "prior_acquisition_result_digest": revision.get("acquisition_result_digest"),
        "candidate_id": candidate_id,
        "canonical_locator": candidate.get("canonical_locator"),
        "question_ids": unresolved,
        "maximum_retrieval_count": 1,
        "scope": "retrieve one exact discovered source for the unresolved strategy questions only",
        "authority_scope": "retrieve one exact discovered source for the unresolved strategy questions only",
        "permitted_responses": (
            "approve_learning_strategy_discovered_source_retrieval_authority",
            "reject_learning_strategy_discovered_source_retrieval_authority",
            "defer_learning_strategy_discovered_source_retrieval_authority",
            "ask_for_clarification",
        ),
        "authority_granted": False,
        "replacement_nonce": replacement_nonce,
        "same_resource_canonicalization_allowed": "https_same_host_port_path_trailing_slash_only",
        "prohibited_actions": (
            "alternative_candidate_retrieval", "additional_discovery", "broad_browsing", "provider_call",
            "learner_retry", "evaluator_run", "capability_update", "pcm_action", "git_action", "deployment",
        ),
        "created_at": utc_now(),
    }
    return request


def validate_discovered_source_retrieval_authority_request(
    request: Mapping[str, Any],
    *,
    strategy: Mapping[str, Any],
    revision: Mapping[str, Any],
    discovery_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate exact candidate, discovery, and unresolved-question bindings."""

    errors: list[str] = []
    discovery_digest = str(discovery_result.get("result_digest") or _digest(discovery_result))
    candidate_id = str(discovery_result.get("recommended_candidate_id") or "")
    candidate = next((dict(item) for item in (discovery_result.get("candidates") or ()) if isinstance(item, Mapping) and item.get("candidate_id") == candidate_id), {})
    if not candidate:
        errors.append("recommended_discovery_candidate_missing")
    if request.get("strategy_id") != strategy.get("strategy_id"):
        errors.append("strategy_binding_mismatch")
    if request.get("revision_id") != revision.get("revision_id"):
        errors.append("revision_binding_mismatch")
    if request.get("discovery_result_id") != discovery_result.get("discovery_result_id") or request.get("discovery_result_digest") != discovery_digest:
        errors.append("discovery_binding_mismatch")
    if request.get("candidate_id") != candidate_id or request.get("canonical_locator") != candidate.get("canonical_locator"):
        errors.append("candidate_substitution_or_locator_mismatch")
    if set(str(item) for item in (request.get("question_ids") or ())) != set(str(item) for item in (revision.get("unresolved_question_ids") or ())):
        errors.append("question_set_mismatch")
    if request.get("prior_acquisition_result_digest") != revision.get("acquisition_result_digest"):
        errors.append("prior_acquisition_binding_mismatch")
    if int(request.get("maximum_retrieval_count") or 0) != 1:
        errors.append("retrieval_budget_mismatch")
    if request.get("authority_granted"):
        errors.append("authority_self_granted")
    if request.get("request_kind") != "governed_learning_strategy_discovered_source_retrieval_authority":
        errors.append("request_kind_mismatch")
    if tuple(request.get("permitted_responses") or ())[:1] != ("approve_learning_strategy_discovered_source_retrieval_authority",):
        errors.append("request_token_mismatch")
    return {"accepted": not errors, "errors": tuple(errors)}
