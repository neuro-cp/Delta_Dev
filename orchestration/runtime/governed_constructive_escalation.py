"""Evidence-bound method selection after constructive-grounding attempts fail."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


_CONSTRUCTIVE_PACKET_TYPE = "advisory_constructive_teaching_packet_v1"


def constructive_teaching_native_json_schema() -> dict[str, Any]:
    """Small closed schema; the two governance booleans are provider constants."""
    facet = {"type": "object", "additionalProperties": False, "required": ["facet", "explanation", "assumptions", "uncertainty"], "properties": {"facet": {"type": "string"}, "explanation": {"type": "string"}, "assumptions": {"type": "array", "items": {"type": "string"}}, "uncertainty": {"type": "string"}}}
    return {"type": "object", "additionalProperties": False, "required": ["packet_type", "relation_id", "question_id", "facet_explanations", "suggested_independent_verification", "advisory_only", "capability_claim"], "properties": {"packet_type": {"type": "string", "const": _CONSTRUCTIVE_PACKET_TYPE}, "relation_id": {"type": "string"}, "question_id": {"type": "string"}, "facet_explanations": {"type": "array", "items": facet}, "suggested_independent_verification": {"type": "array", "items": {"type": "string"}}, "advisory_only": {"type": "boolean", "const": True}, "capability_claim": {"type": "boolean", "const": False}}}


def compile_constructive_teaching_provider_packet(*, authority_request: Mapping[str, Any]) -> dict[str, Any]:
    """Compile the bounded, non-evaluative provider input from approved evidence IDs.

    The source bodies, learner attempts, evaluator material, and proposed patch
    are deliberately absent.  This packet can only request an advisory account
    of the still-unproven relation facets.
    """
    request = dict(authority_request)
    facets = tuple(str(item) for item in (request.get("unresolved_facets") or ()) if str(item))
    packet = {
        "packet_type": _CONSTRUCTIVE_PACKET_TYPE,
        "relation_id": str(request.get("relation_id") or ""),
        "question_id": str(request.get("question_id") or ""),
        "unresolved_facets": facets,
        "retained_evidence_ids": tuple(str(item) for item in (request.get("retained_evidence_ids") or ()) if str(item)),
        "constraints": {
            "advisory_only": True,
            "no_capability_claim": True,
            "no_evaluator_material": True,
            "no_study_resources": True,
            "no_learner_attempt": True,
        },
    }
    packet["packet_digest"] = _digest(packet)
    packet["native_json_schema"] = constructive_teaching_native_json_schema()
    return packet


def constructive_teaching_provider_prompts(*, packet: Mapping[str, Any]) -> tuple[str, str]:
    """Return a strict, topic-neutral request for one explanation per missing facet."""
    facets = tuple(str(item) for item in (packet.get("unresolved_facets") or ()))
    system = (
        "Return exactly one JSON object and no markdown. You author advisory teaching "
        "explanations only. Do not claim capability, write an evaluator, expose an "
        "answer key, or rely on unprovided source text."
    )
    user = json.dumps({
        "required_packet_type": _CONSTRUCTIVE_PACKET_TYPE,
        "relation_id": packet.get("relation_id"),
        "question_id": packet.get("question_id"),
        "unresolved_facets": facets,
        "required_output": {
            "packet_type": _CONSTRUCTIVE_PACKET_TYPE,
            "relation_id": "same input relation_id",
            "question_id": "same input question_id",
            "facet_explanations": [{"facet": "one requested facet", "explanation": "plain-language constructive explanation", "assumptions": ["explicit assumption"], "uncertainty": "what still needs independent verification"}],
            "suggested_independent_verification": ["one concrete verification question"],
            "advisory_only": True,
            "capability_claim": False,
        },
        "pre_dispatch_checklist": [
            "include every requested facet exactly once",
            "do not include evaluator answers, rubrics, or score thresholds",
            "do not claim the learner has acquired a capability",
        ],
    }, sort_keys=True)
    return system, user


def validate_constructive_teaching_provider_response(*, packet: Mapping[str, Any], raw_response: Mapping[str, Any] | str | None) -> dict[str, Any]:
    """Fail closed unless every requested facet has a bounded advisory explanation."""
    errors: list[str] = []
    response: Mapping[str, Any]
    if isinstance(raw_response, str):
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            parsed = {}
            errors.append("response_not_valid_json")
        response = parsed if isinstance(parsed, Mapping) else {}
    else:
        response = raw_response if isinstance(raw_response, Mapping) else {}
    expected_facets = tuple(str(item) for item in (packet.get("unresolved_facets") or ()))
    if response.get("packet_type") != _CONSTRUCTIVE_PACKET_TYPE:
        errors.append("packet_type_mismatch")
    if response.get("relation_id") != packet.get("relation_id"):
        errors.append("relation_id_mismatch")
    if response.get("question_id") != packet.get("question_id"):
        errors.append("question_id_mismatch")
    if response.get("advisory_only") is not True or response.get("capability_claim") is not False:
        errors.append("advisory_boundary_missing")
    entries = response.get("facet_explanations")
    if not isinstance(entries, list):
        errors.append("facet_explanations_missing")
        entries = []
    found: list[str] = []
    normalized_entries: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            errors.append("facet_explanation_not_object")
            continue
        facet = str(entry.get("facet") or "")
        explanation = str(entry.get("explanation") or "").strip()
        assumptions = entry.get("assumptions")
        uncertainty = str(entry.get("uncertainty") or "").strip()
        if not facet or not explanation or not isinstance(assumptions, list) or not uncertainty:
            errors.append(f"invalid_facet_explanation:{facet or 'unknown'}")
            continue
        found.append(facet)
        normalized_entries.append({"facet": facet, "explanation": explanation, "assumptions": tuple(str(item) for item in assumptions), "uncertainty": uncertainty})
    if tuple(sorted(found)) != tuple(sorted(expected_facets)) or len(found) != len(set(found)):
        errors.append("requested_facets_not_covered_exactly_once")
    verification = response.get("suggested_independent_verification")
    if not isinstance(verification, list) or not all(str(item).strip() for item in verification):
        errors.append("independent_verification_missing")
    sealed = {
        "packet_type": _CONSTRUCTIVE_PACKET_TYPE,
        "relation_id": packet.get("relation_id"),
        "question_id": packet.get("question_id"),
        "facet_explanations": tuple(normalized_entries),
        "suggested_independent_verification": tuple(str(item) for item in verification) if isinstance(verification, list) else (),
        "advisory_only": True,
        "capability_eligible": False,
    }
    response_digest = _digest(raw_response if raw_response is not None else {})
    sealed["packet_digest"] = _digest(sealed)
    return {"accepted": not errors, "errors": tuple(dict.fromkeys(errors)), "response_digest": response_digest, "sealed_packet": sealed if not errors else {}}


def adapt_constructive_teaching_response(*, raw_response: Mapping[str, Any] | str | None, source_claim_id: str, original_response_digest: str) -> dict[str, Any]:
    """Wrap preserved bytes only; no mathematical or provider content is repaired."""
    if raw_response is None:
        return {"accepted": False, "reason": "adaptation_unavailable_missing_raw_response"}
    provider_fields = dict(raw_response) if isinstance(raw_response, Mapping) else {"raw_text": raw_response}
    raw_digest = _digest(raw_response)
    if raw_digest != original_response_digest:
        return {"accepted": False, "reason": "raw_response_digest_mismatch"}
    artifact = {"adaptation_id": stable_id("constructive-teaching-response-adaptation", source_claim_id, raw_digest), "adapter_version": "constructive_teaching_response_adapter_v1", "source_provider_claim_id": source_claim_id, "raw_response_digest": raw_digest, "provider_emitted_fields": provider_fields, "controller_imposed_boundary_fields": {"advisory_only": True, "capability_claim": False}, "adaptation_reason": "provider omitted required governance declarations; controller assertions are not attributed to provider", "substantive_provider_content_changed": False}
    artifact["adapted_packet_digest"] = _digest(artifact)
    return {"accepted": True, "artifact": artifact}


def compile_constructive_failure_synthesis(*, assessment: Mapping[str, Any], source_attempts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Classify source attempts without turning repetition into proof."""
    facets = tuple(assessment.get("relation_proposal", {}).get("required_relation_facets") or ())
    sources = []
    conceptual_failures = 0
    evidence_ids: list[str] = []
    for attempt in source_attempts:
        item = dict(attempt)
        result = dict(item.get("result") or {})
        failed = str(item.get("failure_reason") or "")
        if failed:
            classification = "infrastructure_failure" if "404" in failed or "parser" in failed else "source_acquisition_failure"
        else:
            classification = "constructive_relation_failure"
            conceptual_failures += 1
            evidence_ids.extend(str(claim.get("claim_id") or "") for claim in (result.get("claims") or ()) if isinstance(claim, Mapping))
        sources.append({
            "source_identity": result.get("source_identity") or item.get("claim", {}).get("candidate_id"),
            "source_digest": result.get("source_digest") or "",
            "evidence_ids": tuple(str(claim.get("claim_id") or "") for claim in (result.get("claims") or ()) if isinstance(claim, Mapping)),
            "classification": classification,
            "supported_facets": (),
            "unproven_facets": facets,
            "information_gained": "scope or proposition context retained" if result else "transport failure retained as non-conceptual evidence",
            "duplication": "contextual repetition is not constructive proof",
        })
    methods = (
        {"method": "retained_premise_derivation", "information_gain": 0.1, "grounding": 0.9, "cost": 0.0, "risk": 0.9, "verifiability": 0.9, "eligible": False, "reason": "no explicit retained premises cover the required relation facets"},
        {"method": "targeted_constructive_source_discovery", "information_gain": 0.55, "grounding": 0.85, "cost": 0.3, "risk": 0.25, "verifiability": 0.85, "eligible": True, "reason": "would need a mechanism-specific search rather than another generic theorem note"},
        {"method": "provider_assisted_constructive_teaching", "information_gain": 0.72 if conceptual_failures >= 2 else 0.4, "grounding": 0.45, "cost": 0.35, "risk": 0.45, "verifiability": 0.75, "eligible": conceptual_failures >= 2, "reason": "multiple independent sources supplied context but not the dependency chain; advisory output remains independently unverified"},
        {"method": "defer", "information_gain": 0.0, "grounding": 1.0, "cost": 0.0, "risk": 0.1, "verifiability": 1.0, "eligible": True, "reason": "avoids a false capability claim but leaves the load-bearing prerequisite unresolved"},
    )
    ranked = tuple(sorted(methods, key=lambda item: (not item["eligible"], -(item["information_gain"] + item["grounding"] * .2 - item["cost"] * .1 - item["risk"] * .1), item["method"])))
    selected = next(item for item in ranked if item["eligible"])
    outcome = "provider_assisted_constructive_teaching_authority_pending" if selected["method"] == "provider_assisted_constructive_teaching" else "constructive_grounding_escalation_unresolved"
    synthesis = {"synthesis_id": stable_id("constructive-grounding-failure-synthesis", assessment.get("relation_id"), tuple(item["source_digest"] for item in sources)), "relation_id": assessment.get("relation_id"), "question_id": assessment.get("relation_proposal", {}).get("target_question_id"), "unresolved_facets": facets, "source_attempts": tuple(sources), "retained_evidence_ids": tuple(sorted(set(filter(None, evidence_ids)))), "ranked_methods": ranked, "selected_method": selected["method"], "outcome": outcome, "created_at": utc_now()}
    synthesis["synthesis_digest"] = _digest(synthesis)
    if outcome.startswith("provider_assisted"):
        synthesis["authority_request"] = {"request_id": stable_id("constructive-teaching-provider-authority", synthesis["synthesis_digest"]), "request_kind": "governed_constructive_teaching_provider_authority", "status": "pending", "relation_id": synthesis["relation_id"], "question_id": synthesis["question_id"], "synthesis_id": synthesis["synthesis_id"], "synthesis_digest": synthesis["synthesis_digest"], "unresolved_facets": facets, "retained_evidence_ids": synthesis["retained_evidence_ids"], "provider": "openai", "model": "gpt-4.1-mini", "maximum_call_count": 1, "maximum_tokens": 1800, "structured_output": "advisory_constructive_teaching_packet_v1", "authority_scope": "one advisory constructive-teaching packet; no evaluator access, web search, learner retry, capability update, or automatic grounding promotion", "permitted_responses": ("approve_constructive_teaching_provider_authority", "reject_constructive_teaching_provider_authority", "defer_constructive_teaching_provider_authority", "ask_for_clarification"), "authority_granted": False, "created_at": utc_now()}
    else:
        synthesis["authority_request"] = {}
    return synthesis
