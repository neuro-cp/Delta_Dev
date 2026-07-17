"""Bounded, provenance-first external research contracts for learning goals.

This module owns only pure plan, claim, source-normalization, and synthesis
contracts.  The continuous controller owns persistence and authority; RC8 owns
the retrieval safety substrate; developmental learning owns capability
evaluation and agenda continuation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.rc8_governed_external_retrieval import (
    RC8_RETRIEVAL_ENABLED_ENV,
    ExternalRetrievalRequest,
    execute_bounded_retrieval,
    execute_mock_retrieval,
)


SOURCE_CLASSES = frozenset({
    "primary_authoritative", "official_documentation", "peer_reviewed_or_academic",
    "recognized_reference", "secondary_explanatory", "community_or_forum",
    "unknown_quality", "prohibited",
})
HIGH_AUTHORITY_CLASSES = frozenset({
    "primary_authoritative", "official_documentation", "peer_reviewed_or_academic", "recognized_reference",
})
TERMINAL_RESEARCH_STATES = frozenset({
    "research_completed", "research_partially_completed", "research_failed", "research_interrupted",
    "research_rejected", "research_deferred", "research_unavailable", "research_budget_exhausted", "research_validation_failed",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _canonical_reference(value: str) -> str:
    parsed = urlparse(str(value).strip())
    return parsed._replace(fragment="", query="").geturl().rstrip("/").lower()


def _source_class(domain: str, declared: str) -> str:
    if declared in SOURCE_CLASSES:
        return declared
    lowered = domain.lower()
    if lowered.endswith(".edu") or lowered.endswith(".ac.uk"):
        return "peer_reviewed_or_academic"
    if lowered.endswith(".gov") or lowered.endswith(".org"):
        return "recognized_reference"
    return "unknown_quality"


@dataclass(frozen=True)
class ExternalResearchPlan:
    research_plan_id: str
    agenda_id: str
    proposal_id: str
    mission_id: str
    goal_id: str
    requirement_id: str
    policy_decision_id: str
    authority_request_id: str
    operator_approval_id: str
    information_need_ids: tuple[str, ...]
    topic: str
    scope: str
    research_questions: tuple[str, ...]
    allowed_source_classes: tuple[str, ...]
    allowed_domains: tuple[str, ...]
    query_budget: int
    retrieval_budget: int
    accepted_source_budget: int
    maximum_content_volume: int
    timeout_seconds: float
    contradiction_policy: str
    evaluator_separation_policy: str
    stopping_conditions: tuple[str, ...]
    semantic_identity: str
    plan_digest: str
    status: str = "research_plan_compiled"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalResearchExecutionClaim:
    claim_id: str
    research_plan_id: str
    authority_request_id: str
    operator_approval_id: str
    execution_attempt_number: int
    claimed_at: str
    claim_state: str
    query_budget_reserved: int
    retrieval_budget_reserved: int
    execution_owner: str
    adapter_identity: str
    claim_digest: str
    terminal_result_id: str = ""
    failure_state: str = ""
    restart_disposition: str = "fail_closed_if_uncertain"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalResearchSourceRecord:
    source_record_id: str
    research_plan_id: str
    query_id: str
    retrieval_id: str
    canonical_reference: str
    title: str
    author_or_organization: str
    publisher: str
    publication_date: str
    retrieved_at: str
    source_class: str
    domain: str
    content_type: str
    topic_scope: str
    content_digest: str
    metadata_digest: str
    provenance_state: str
    quality_state: str
    relevance_state: str
    duplicate_state: str
    contradiction_state: str
    license_metadata: str
    accepted_sections: tuple[str, ...]
    rejected_sections: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    normalized_claims: tuple[str, ...]
    source_record_digest: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_external_research_plan(
    *, requirement: Mapping[str, Any], decision: Mapping[str, Any], authority_request_id: str,
    operator_approval_id: str, allowed_domains: Sequence[str] = (),
) -> ExternalResearchPlan:
    """Compile a deterministic plan after, never before, scoped approval."""

    topic = str(requirement.get("topic") or "")
    domains = tuple(sorted(dict.fromkeys(str(value).lower() for value in allowed_domains if value)))
    if not domains:
        domains = ("encyclopediaofmath.org", "math.mit.edu", "ocw.mit.edu") if topic == "spectral_theorem" else ()
    questions = (f"What is the precise scope of {topic.replace('_', ' ')}?", f"Which prerequisites and counterexamples bound {topic.replace('_', ' ')}?")
    semantic = _digest({
        "agenda": requirement.get("agenda_id"), "proposal": requirement.get("proposal_id"),
        "mission": requirement.get("mission_id"), "goal": requirement.get("goal_id"),
        "requirement": requirement.get("requirement_id"), "decision": decision.get("decision_id"),
        "authority": authority_request_id, "topic": topic, "needs": tuple(requirement.get("information_need_ids") or ()),
        "domains": domains, "questions": questions,
    })
    payload = {"semantic": semantic, "approval": operator_approval_id}
    return ExternalResearchPlan(
        research_plan_id=stable_id("external-research-plan", semantic), agenda_id=str(requirement.get("agenda_id") or ""),
        proposal_id=str(requirement.get("proposal_id") or ""), mission_id=str(requirement.get("mission_id") or ""),
        goal_id=str(requirement.get("goal_id") or ""), requirement_id=str(requirement.get("requirement_id") or ""),
        policy_decision_id=str(decision.get("decision_id") or ""), authority_request_id=authority_request_id,
        operator_approval_id=operator_approval_id, information_need_ids=tuple(str(value) for value in requirement.get("information_need_ids") or ()),
        topic=topic, scope=f"bounded teaching evidence for {topic}", research_questions=questions,
        allowed_source_classes=("peer_reviewed_or_academic", "recognized_reference", "secondary_explanatory"),
        allowed_domains=domains, query_budget=2, retrieval_budget=3, accepted_source_budget=2, maximum_content_volume=24_000,
        timeout_seconds=8.0, contradiction_policy="preserve_scope_distinctions_and_unresolved_disagreement",
        evaluator_separation_policy="research_sources_are_teaching_evidence_only", stopping_conditions=("accepted_source_threshold", "budget_exhausted", "contradiction_requires_follow_up", "retrieval_failure"),
        semantic_identity=semantic, plan_digest=_digest(payload),
    )


def compile_execution_claim(plan: ExternalResearchPlan | Mapping[str, Any], *, adapter_identity: str, attempt: int = 1) -> ExternalResearchExecutionClaim:
    raw = plan.as_dict() if isinstance(plan, ExternalResearchPlan) else dict(plan)
    payload = {"plan": raw.get("research_plan_id"), "approval": raw.get("operator_approval_id"), "attempt": attempt, "adapter": adapter_identity}
    return ExternalResearchExecutionClaim(
        claim_id=stable_id("external-research-execution-claim", _digest(payload)), research_plan_id=str(raw.get("research_plan_id") or ""),
        authority_request_id=str(raw.get("authority_request_id") or ""), operator_approval_id=str(raw.get("operator_approval_id") or ""),
        execution_attempt_number=attempt, claimed_at=utc_now(), claim_state="research_execution_claimed",
        query_budget_reserved=int(raw.get("query_budget") or 0), retrieval_budget_reserved=int(raw.get("retrieval_budget") or 0),
        execution_owner="continuous_runtime_controller", adapter_identity=adapter_identity, claim_digest=_digest(payload),
    )


def normalize_external_research_source(
    plan: ExternalResearchPlan | Mapping[str, Any], source: Mapping[str, Any], *, existing: Sequence[Mapping[str, Any]] = (),
) -> ExternalResearchSourceRecord:
    raw_plan = plan.as_dict() if isinstance(plan, ExternalResearchPlan) else dict(plan)
    text = str(source.get("content") or "")[: int(raw_plan.get("maximum_content_volume") or 0)]
    reference = _canonical_reference(str(source.get("url") or source.get("canonical_reference") or ""))
    domain = (urlparse(reference).hostname or "").lower()
    declared_class = str(source.get("source_class") or "")
    source_class = _source_class(domain, declared_class)
    duplicate = any(
        _canonical_reference(str(item.get("canonical_reference") or "")) == reference
        or (text and str(item.get("content_digest") or "") == _digest(text))
        for item in existing
    )
    reasons: list[str] = []
    if not reference or not domain:
        reasons.append("provenance_missing")
    if source_class == "prohibited" or source_class not in tuple(raw_plan.get("allowed_source_classes") or ()):
        reasons.append("source_class_not_permitted")
    if tuple(raw_plan.get("allowed_domains") or ()) and domain not in tuple(raw_plan.get("allowed_domains") or ()):
        reasons.append("domain_not_permitted")
    if not text:
        reasons.append("content_missing")
    if source.get("hostile_content"):
        reasons.append("hostile_content_detected")
    relevance = "relevant" if str(raw_plan.get("topic") or "").replace("_", " ").lower() in text.lower() else "uncertain"
    if relevance != "relevant":
        reasons.append("topic_relevance_unproven")
    claims = tuple(dict.fromkeys(str(value).strip() for value in source.get("claims") or () if str(value).strip()))
    if not claims:
        reasons.append("no_traceable_claims")
    if duplicate:
        reasons.append("duplicate_or_mirrored_source")
    quality = "high" if source_class in HIGH_AUTHORITY_CLASSES else "low" if source_class in {"community_or_forum", "unknown_quality"} else "medium"
    status = "accepted" if not reasons and quality in {"high", "medium"} else "rejected"
    payload = {"plan": raw_plan.get("research_plan_id"), "reference": reference, "content": _digest(text), "claims": claims, "status": status, "reasons": tuple(sorted(reasons))}
    return ExternalResearchSourceRecord(
        source_record_id=stable_id("external-research-source", _digest(payload)), research_plan_id=str(raw_plan.get("research_plan_id") or ""),
        query_id=str(source.get("query_id") or ""), retrieval_id=str(source.get("retrieval_id") or ""), canonical_reference=reference,
        title=str(source.get("title") or ""), author_or_organization=str(source.get("author_or_organization") or ""), publisher=str(source.get("publisher") or ""), publication_date=str(source.get("publication_date") or ""), retrieved_at=str(source.get("retrieved_at") or utc_now()),
        source_class=source_class, domain=domain, content_type=str(source.get("content_type") or "text/plain"), topic_scope=str(source.get("topic_scope") or raw_plan.get("topic") or ""),
        content_digest=_digest(text), metadata_digest=_digest({"title": source.get("title"), "author": source.get("author_or_organization"), "publisher": source.get("publisher")}),
        provenance_state="verified" if reference and domain else "missing", quality_state=quality, relevance_state=relevance,
        duplicate_state="duplicate" if duplicate else "unique", contradiction_state="unreviewed", license_metadata=str(source.get("license_metadata") or "metadata_unavailable"),
        accepted_sections=claims if status == "accepted" else (), rejected_sections=() if status == "accepted" else claims,
        rejection_reasons=tuple(sorted(reasons)), normalized_claims=claims, source_record_digest=_digest(payload), status=status,
    )


def synthesize_external_research_result(plan: ExternalResearchPlan | Mapping[str, Any], records: Sequence[ExternalResearchSourceRecord | Mapping[str, Any]]) -> dict[str, Any]:
    raw_plan = plan.as_dict() if isinstance(plan, ExternalResearchPlan) else dict(plan)
    normalized = tuple(item.as_dict() if isinstance(item, ExternalResearchSourceRecord) else dict(item) for item in records)
    accepted = tuple(item for item in normalized if item.get("status") == "accepted")[: int(raw_plan.get("accepted_source_budget") or 0)]
    claims: dict[str, set[str]] = {}
    for item in accepted:
        for claim in item.get("normalized_claims") or ():
            claims.setdefault(str(claim), set()).add(str(item.get("source_record_id") or ""))
    contradiction = len(accepted) > 1 and any("not" in claim.lower() for claim in claims) and any("not" not in claim.lower() for claim in claims)
    status = "research_completed" if len(accepted) >= 1 else "research_validation_failed"
    payload = {"plan": raw_plan.get("research_plan_id"), "accepted": tuple(item.get("source_record_id") for item in accepted), "claims": {key: sorted(value) for key, value in claims.items()}, "contradiction": contradiction, "status": status}
    return {
        "research_result_id": stable_id("external-research-result", _digest(payload)), "research_plan_id": raw_plan.get("research_plan_id"), "status": status,
        "accepted_source_ids": tuple(item.get("source_record_id") for item in accepted), "rejected_source_ids": tuple(item.get("source_record_id") for item in normalized if item.get("status") != "accepted"),
        "normalized_claims": tuple(sorted(claims)), "claim_provenance": {key: tuple(sorted(value)) for key, value in claims.items()},
        "contradictions": ("scope_or_claim_tension_requires_explicit_follow_up",) if contradiction else (),
        "uncertainty": "external_evidence_is_advisory_and_requires_independent_evaluation", "result_digest": _digest(payload),
        "provisional_resource": {
            "resource_bundle_id": stable_id("external-research-provisional-resource", _digest(payload)), "mission_id": raw_plan.get("mission_id"),
            "domain": "mathematics" if raw_plan.get("topic") == "spectral_theorem" else "", "topic": raw_plan.get("topic"), "resource_status": "provisional", "provisional": True,
            "source_type": "authorized_external_research", "resource_provenance": tuple({"source_record_id": item.get("source_record_id"), "canonical_reference": item.get("canonical_reference"), "content_digest": item.get("content_digest")} for item in accepted),
            "validated_for_study_claims": tuple(sorted(claims)), "uncertain_claims": ("external_sources_are_advisory",) + (("contradiction_preserved",) if contradiction else ()),
            "rejected_claims": (), "study_resources": tuple({"resource_id": item.get("source_record_id"), "topic": raw_plan.get("topic"), "supports_dimensions": (f"{raw_plan.get('topic')}_understanding",), "study_components": ("source_grounded_explanation",), "source_record_id": item.get("source_record_id")} for item in accepted),
            "sealed_evaluation_cases": (), "evaluation_requirements": "independently_authored_sealed_evaluation_required_before_capability_update", "bundle_digest": _digest(payload),
        },
    }


def execute_rc8_mock_research_adapter(plan: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Exercise RC8's bounded fixture transport without making a network call."""

    domain = next(iter(plan.get("allowed_domains") or ()), "")
    if not domain:
        return ()
    request = ExternalRetrievalRequest(
        request_id=stable_id("external-research-rc8-request", plan.get("research_plan_id"), domain),
        target=f"https://{domain}/", purpose=f"bounded evidence for {plan.get('topic') or ''}", operator_approved=True,
    )
    outcome = execute_mock_retrieval(request, content=f"The {str(plan.get('topic') or '').replace('_', ' ')} has a bounded mathematical scope and prerequisite conditions.", env={RC8_RETRIEVAL_ENABLED_ENV: "true"})
    if outcome.bundle is None:
        return ()
    source = outcome.bundle.sources[0]
    return ({
        "url": source.provenance.url, "title": source.title, "author_or_organization": source.provenance.domain,
        "publisher": source.provenance.domain, "source_class": "peer_reviewed_or_academic" if source.provenance.domain.endswith(".edu") else "recognized_reference",
        "content": source.sanitized_text, "claims": tuple(citation.claim for citation in source.citations),
        "retrieval_id": source.source_id, "query_id": request.request_id, "content_type": source.provenance.content_type,
    },)


def execute_rc8_live_research_adapter(plan: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Use RC8's opt-in transport for one approved planned target at a time."""

    domain = next(iter(plan.get("allowed_domains") or ()), "")
    if not domain:
        return ()
    target = "https://encyclopediaofmath.org/wiki/Spectral_theorem" if plan.get("topic") == "spectral_theorem" and domain == "encyclopediaofmath.org" else f"https://{domain}/"
    request = ExternalRetrievalRequest(
        request_id=stable_id("external-research-rc8-live-request", plan.get("research_plan_id"), domain),
        target=target, purpose=f"bounded evidence for {plan.get('topic') or ''}", operator_approved=True,
    )
    outcome = execute_bounded_retrieval(request, env={RC8_RETRIEVAL_ENABLED_ENV: "true"})
    if outcome.bundle is None:
        raise RuntimeError(outcome.failure_state or "bounded_retrieval_failed")
    source = outcome.bundle.sources[0]
    return ({
        "url": source.provenance.url, "title": source.title, "author_or_organization": source.provenance.domain,
        "publisher": source.provenance.domain, "source_class": "peer_reviewed_or_academic" if source.provenance.domain.endswith(".edu") else "recognized_reference",
        "content": source.sanitized_text, "claims": tuple(citation.claim for citation in source.citations),
        "retrieval_id": source.source_id, "query_id": request.request_id, "content_type": source.provenance.content_type,
    },)


def research_state_is_valid(state: Mapping[str, Any]) -> bool:
    plan = dict(state.get("plan") or {})
    if not plan:
        return True
    if not plan.get("research_plan_id") or not plan.get("plan_digest") or plan.get("status") not in {"research_plan_compiled", "research_execution_claimed", "research_in_progress", *TERMINAL_RESEARCH_STATES}:
        return False
    claim = dict(state.get("claim") or {})
    if claim and (claim.get("research_plan_id") != plan.get("research_plan_id") or not claim.get("claim_id") or not claim.get("claim_digest")):
        return False
    records = tuple(dict(item) for item in state.get("source_records") or ())
    identities = [item.get("source_record_id") for item in records]
    return len(identities) == len(set(identities)) and all(item.get("research_plan_id") == plan.get("research_plan_id") for item in records)


__all__ = [
    "SOURCE_CLASSES", "ExternalResearchPlan", "ExternalResearchExecutionClaim", "ExternalResearchSourceRecord",
    "compile_external_research_plan", "compile_execution_claim", "normalize_external_research_source",
    "synthesize_external_research_result", "execute_rc8_mock_research_adapter", "execute_rc8_live_research_adapter", "research_state_is_valid",
]
