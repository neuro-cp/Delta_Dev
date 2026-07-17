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
FAILURE_CLASSIFICATIONS = {
    "HTTPError": ("http_rejection", True, True),
    "content_type_rejected": ("unsupported_content_type", True, True),
    "redirect_rejected": ("prohibited_redirect", True, True),
    "content_budget_exhausted": ("content_unavailable", True, True),
    "TimeoutError": ("timeout", False, False),
    "URLError": ("transport_unreachable", False, False),
    "SSLError": ("tls_or_certificate_failure", False, False),
    "OSError": ("transport_unreachable", False, False),
    "RuntimeError": ("unknown_transport_failure", False, False),
}
TOPIC_SOURCE_TARGETS = {
    "spectral_theorem": (
        {
            "canonical_target": "https://encyclopediaofmath.org/wiki/Spectral_theorem",
            "source_class": "recognized_reference",
            "organization": "Encyclopedia of Mathematics",
            "expected_scope": "precise spectral-theorem scope and prerequisites",
        },
        {
            "canonical_target": "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/",
            "source_class": "recognized_reference",
            "organization": "MIT OpenCourseWare",
            "expected_scope": "university linear-algebra material relevant to spectral-theorem prerequisites",
        },
        {
            "canonical_target": "https://ocw.mit.edu/courses/18-701-algebra-i-fall-2010/resources/mit18_701f10_spthm/",
            "source_class": "recognized_reference",
            "organization": "MIT OpenCourseWare",
            "expected_scope": "the spectral theorem for hermitian matrices, including its complex inner-product-space scope",
            "required_topic_terms": ("spectral theorem", "hermitian"),
            "target_kind": "direct_topic_specific",
        },
    ),
}


class ExternalResearchRetrievalError(RuntimeError):
    """A bounded transport failure safe to persist in the research ledger."""

    def __init__(self, failure_state: str) -> None:
        self.failure_state = str(failure_state or "bounded_retrieval_failed")
        super().__init__(self.failure_state)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _canonical_reference(value: str) -> str:
    parsed = urlparse(str(value).strip())
    return parsed._replace(fragment="", query="").geturl().rstrip("/").lower()


def _direct_retrieval_target(value: str) -> str:
    """Preserve a direct locator's path semantics while removing only fragments."""

    parsed = urlparse(str(value).strip())
    return parsed._replace(fragment="", query="").geturl()


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
    source_target: str = ""
    source_class: str = ""
    source_organization: str = ""
    plan_version: int = 1
    prior_plan_id: str = ""
    prior_failure_id: str = ""
    fallback_candidate_id: str = ""
    prior_query_usage: int = 0
    prior_retrieval_usage: int = 0
    required_topic_terms: tuple[str, ...] = ()
    source_target_kind: str = "registry_default"

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
class ExternalResearchRetrievalAttempt:
    retrieval_attempt_id: str
    research_plan_id: str
    claim_id: str
    query_id: str
    target_reference: str
    attempt_number: int
    claimed_at: str
    status: str
    adapter_identity: str
    attempt_digest: str

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
    operator_approval_id: str, allowed_domains: Sequence[str] = (), source_target: str = "",
    source_class: str = "", source_organization: str = "", plan_version: int = 1,
    prior_plan_id: str = "", prior_failure_id: str = "", fallback_candidate_id: str = "",
    prior_query_usage: int = 0, prior_retrieval_usage: int = 0, query_budget: int = 2,
    retrieval_budget: int = 3, accepted_source_budget: int = 2, required_topic_terms: Sequence[str] = (),
    source_target_kind: str = "registry_default",
) -> ExternalResearchPlan:
    """Compile a deterministic plan after, never before, scoped approval."""

    topic = str(requirement.get("topic") or "")
    domains = tuple(sorted(dict.fromkeys(str(value).lower() for value in allowed_domains if value)))
    if not domains:
        domains = ("encyclopediaofmath.org", "math.mit.edu", "ocw.mit.edu") if topic == "spectral_theorem" else ()
    default_target = next(iter(TOPIC_SOURCE_TARGETS.get(topic, ())), {})
    target = str(source_target or default_target.get("canonical_target") or (f"https://{domains[0]}/" if domains else ""))
    target_domain = urlparse(target).hostname or ""
    if target_domain and target_domain not in domains:
        domains = tuple(sorted(dict.fromkeys((*domains, target_domain))))
    selected_class = str(source_class or default_target.get("source_class") or "recognized_reference")
    organization = str(source_organization or default_target.get("organization") or target_domain)
    required_terms = tuple(dict.fromkeys(
        str(value).strip().lower()
        for value in (required_topic_terms or default_target.get("required_topic_terms") or (topic.replace("_", " "),))
        if str(value).strip()
    ))
    questions = (f"What is the precise scope of {topic.replace('_', ' ')}?", f"Which prerequisites and counterexamples bound {topic.replace('_', ' ')}?")
    semantic = _digest({
        "agenda": requirement.get("agenda_id"), "proposal": requirement.get("proposal_id"),
        "mission": requirement.get("mission_id"), "goal": requirement.get("goal_id"),
        "requirement": requirement.get("requirement_id"), "decision": decision.get("decision_id"),
        "authority": authority_request_id, "topic": topic, "needs": tuple(requirement.get("information_need_ids") or ()),
        "domains": domains, "questions": questions, "target": target, "source_class": selected_class,
        "organization": organization, "version": plan_version, "prior_plan": prior_plan_id,
        "prior_failure": prior_failure_id, "fallback_candidate": fallback_candidate_id,
        "prior_budget": (prior_query_usage, prior_retrieval_usage), "required_topic_terms": required_terms,
        "source_target_kind": source_target_kind,
    })
    payload = {"semantic": semantic, "approval": operator_approval_id}
    return ExternalResearchPlan(
        research_plan_id=stable_id("external-research-plan", semantic), agenda_id=str(requirement.get("agenda_id") or ""),
        proposal_id=str(requirement.get("proposal_id") or ""), mission_id=str(requirement.get("mission_id") or ""),
        goal_id=str(requirement.get("goal_id") or ""), requirement_id=str(requirement.get("requirement_id") or ""),
        policy_decision_id=str(decision.get("decision_id") or ""), authority_request_id=authority_request_id,
        operator_approval_id=operator_approval_id, information_need_ids=tuple(str(value) for value in requirement.get("information_need_ids") or ()),
        topic=topic, scope=f"bounded teaching evidence for {topic}", research_questions=questions,
        allowed_source_classes=("official_documentation", "peer_reviewed_or_academic", "recognized_reference", "secondary_explanatory"),
        allowed_domains=domains, query_budget=query_budget, retrieval_budget=retrieval_budget, accepted_source_budget=accepted_source_budget, maximum_content_volume=24_000,
        timeout_seconds=8.0, contradiction_policy="preserve_scope_distinctions_and_unresolved_disagreement",
        evaluator_separation_policy="research_sources_are_teaching_evidence_only", stopping_conditions=("accepted_source_threshold", "budget_exhausted", "contradiction_requires_follow_up", "retrieval_failure"),
        semantic_identity=semantic, plan_digest=_digest(payload), source_target=target, source_class=selected_class,
        source_organization=organization, plan_version=plan_version, prior_plan_id=prior_plan_id,
        prior_failure_id=prior_failure_id, fallback_candidate_id=fallback_candidate_id,
        prior_query_usage=prior_query_usage, prior_retrieval_usage=prior_retrieval_usage,
        required_topic_terms=required_terms, source_target_kind=source_target_kind,
    )


def classify_terminal_research_failure(research: Mapping[str, Any]) -> dict[str, Any]:
    """Classify only durable terminal failure evidence; legacy ambiguity fails closed."""

    plan = dict(research.get("plan") or {})
    claim = dict(research.get("claim") or {})
    result = dict(research.get("result") or {})
    attempts = tuple(dict(item) for item in (research.get("retrieval_attempts") or ()))
    state = str(result.get("failure_state") or result.get("failure") or claim.get("failure_state") or "")
    normalized, source_specific, retryable = FAILURE_CLASSIFICATIONS.get(state, ("unknown_transport_failure", False, False))
    target = str(next((item.get("target_reference") for item in attempts if item.get("target_reference")), plan.get("source_target") or ""))
    payload = {
        "plan": plan.get("research_plan_id"), "claim": claim.get("claim_id"), "attempt": next((item.get("retrieval_attempt_id") for item in attempts), ""),
        "target": target, "adapter": claim.get("adapter_identity"), "raw": state, "normalized": normalized,
    }
    return {
        "failure_id": stable_id("external-research-failure", _digest(payload)),
        "plan_id": str(plan.get("research_plan_id") or ""),
        "execution_claim_id": str(claim.get("claim_id") or ""),
        "retrieval_claim_id": str(next((item.get("retrieval_attempt_id") for item in attempts), "")),
        "source_target": target, "adapter_identity": str(claim.get("adapter_identity") or ""),
        "normalized_failure_type": normalized, "raw_failure_reference": state,
        "retryable": retryable, "source_specific": source_specific,
        "budget_effect": {"queries_used": len(attempts), "retrievals_used": len(attempts)},
        "fallback_eligible": bool(
            plan.get("status") == "research_failed" and claim.get("claim_state") == "research_failed"
            and source_specific and retryable and bool(plan.get("information_need_ids"))
        ),
        "created_at": utc_now(), "terminal_state": str(plan.get("status") or ""), "failure_digest": _digest(payload),
    }


def compile_historical_transport_interpretation(
    research: Mapping[str, Any], diagnostics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Interpret a prior immutable failure only from new bounded diagnostic evidence."""

    failure = classify_terminal_research_failure(research)
    target = _canonical_reference(str(failure.get("source_target") or ""))
    normalized = tuple(dict(item) for item in diagnostics)
    target_diagnostic = next((item for item in normalized if _canonical_reference(str(item.get("canonical_target") or "")) == target), {})
    successful_other = any(
        item.get("terminal_state") == "diagnostic_completed"
        and _canonical_reference(str(item.get("canonical_target") or "")) != target
        for item in normalized
    )
    if target_diagnostic and target_diagnostic.get("terminal_state") == "diagnostic_failed" and successful_other:
        classification, confidence, fallback_eligible = "source_specific", "high", True
    elif normalized and not any(item.get("terminal_state") == "diagnostic_completed" for item in normalized) and all(item.get("systemic_indicator") for item in normalized):
        classification, confidence, fallback_eligible = "systemic", "high", False
    else:
        classification, confidence, fallback_eligible = "insufficient", "low", False
    payload = {
        "failure": failure.get("failure_id"), "diagnostics": tuple(item.get("diagnostic_id") for item in normalized),
        "classification": classification, "fallback": fallback_eligible,
    }
    return {
        "interpretation_id": stable_id("external-research-historical-transport-interpretation", _digest(payload)),
        "historical_failure_id": failure.get("failure_id"), "historical_plan_id": failure.get("plan_id"),
        "diagnostic_ids": payload["diagnostics"], "classification": classification, "confidence": confidence,
        "fallback_eligible": fallback_eligible, "historical_failure_unchanged": True,
        "derived_failure_type": str(target_diagnostic.get("normalized_exception_class") or failure.get("normalized_failure_type") or "unknown_transport_failure"),
        "interpretation_digest": _digest(payload), "created_at": utc_now(),
    }


def compile_fallback_source_candidates(
    plan: Mapping[str, Any], failure: Mapping[str, Any], *, maximum_candidates: int = 3,
) -> tuple[dict[str, Any], ...]:
    """Offer only policy-allowed, canonically distinct direct targets."""

    if not bool(failure.get("fallback_eligible")):
        return ()
    failed_target = _canonical_reference(str(failure.get("source_target") or ""))
    allowed_domains = tuple(str(value) for value in (plan.get("allowed_domains") or ()))
    allowed_classes = tuple(str(value) for value in (plan.get("allowed_source_classes") or ()))
    candidates: list[dict[str, Any]] = []
    for rank, target in enumerate(TOPIC_SOURCE_TARGETS.get(str(plan.get("topic") or ""), ()), start=1):
        retrieval_target = _direct_retrieval_target(str(target["canonical_target"]))
        canonical = _canonical_reference(retrieval_target)
        domain = urlparse(canonical).hostname or ""
        reasons = []
        if canonical == failed_target:
            reasons.append("same_canonical_target_as_failed_plan")
        if domain not in allowed_domains:
            reasons.append("domain_not_permitted")
        if str(target["source_class"]) not in allowed_classes:
            reasons.append("source_class_not_permitted")
        payload = {"failed_plan": failure.get("plan_id"), "failure": failure.get("failure_id"), "target": canonical}
        candidates.append({
            "fallback_candidate_id": stable_id("external-research-fallback-candidate", _digest(payload)),
            "failed_plan_id": str(failure.get("plan_id") or ""),
            "unresolved_information_need_ids": tuple(str(value) for value in (plan.get("information_need_ids") or ())),
            "canonical_target": canonical, "retrieval_target": retrieval_target, "source_class": str(target["source_class"]),
            "organization": str(target["organization"]), "expected_scope": str(target["expected_scope"]),
            "required_topic_terms": tuple(target.get("required_topic_terms") or (str(plan.get("topic") or "").replace("_", " "),)),
            "target_kind": str(target.get("target_kind") or "registry_fallback"),
            "permitted_domain": domain in allowed_domains, "provenance_expectations": "direct_https_get_with_content_digest",
            "direct_access_expectation": "one_direct_allowlisted_target_without_redirects",
            "relationship_to_failed_target": "distinct_organization_and_canonical_target",
            "material_difference_rationale": "different canonical target, publisher, locator, plan, execution, and retrieval identity",
            "expected_information_value": max(0.1, 1.0 - rank * 0.1), "risk": 0.12, "budget_cost": {"queries": 1, "retrievals": 1},
            "rejection_reasons": tuple(reasons), "rank": rank, "candidate_digest": _digest(payload),
        })
    return tuple(item for item in candidates if not item["rejection_reasons"])[:maximum_candidates]


def compile_direct_topic_source_candidates(
    research: Mapping[str, Any], *, maximum_candidates: int = 1,
) -> tuple[dict[str, Any], ...]:
    """Compile untried exact topic locators after a relevance-only terminal result."""

    plan = dict(research.get("plan") or {})
    result = dict(research.get("result") or {})
    records = tuple(dict(item) for item in (research.get("source_records") or ()))
    if result.get("status") != "research_validation_failed" or not any(
        "topic_relevance_unproven" in tuple(item.get("rejection_reasons") or ()) for item in records
    ):
        return ()
    prior_targets = {
        _canonical_reference(str(value))
        for value in (
            str(plan.get("source_target") or ""),
            *(str(item.get("canonical_reference") or "") for item in records),
            *(str(item.get("target_reference") or "") for item in (research.get("retrieval_attempts") or ())),
            *(str(dict(item).get("plan", {}).get("source_target") or "") for item in (research.get("history") or ())),
        )
        if value
    }
    domains = tuple(str(value).lower() for value in (plan.get("allowed_domains") or ()))
    classes = tuple(str(value) for value in (plan.get("allowed_source_classes") or ()))
    candidates: list[dict[str, Any]] = []
    for rank, target in enumerate(TOPIC_SOURCE_TARGETS.get(str(plan.get("topic") or ""), ()), start=1):
        if str(target.get("target_kind") or "") != "direct_topic_specific":
            continue
        retrieval_target = _direct_retrieval_target(str(target.get("canonical_target") or ""))
        canonical = _canonical_reference(retrieval_target)
        domain = (urlparse(canonical).hostname or "").lower()
        required_terms = tuple(str(value).strip().lower() for value in (target.get("required_topic_terms") or ()) if str(value).strip())
        reasons = []
        if not canonical or canonical in prior_targets:
            reasons.append("already_attempted_or_non_direct_target")
        if domain not in domains:
            reasons.append("domain_not_permitted")
        if str(target.get("source_class") or "") not in classes:
            reasons.append("source_class_not_permitted")
        if not required_terms:
            reasons.append("required_topic_terms_missing")
        payload = {"prior_plan": plan.get("research_plan_id"), "target": canonical, "terms": required_terms}
        candidates.append({
            "fallback_candidate_id": stable_id("external-research-direct-topic-candidate", _digest(payload)),
            "failed_plan_id": str(plan.get("research_plan_id") or ""),
            "canonical_target": canonical, "retrieval_target": retrieval_target,
            "source_class": str(target.get("source_class") or ""), "organization": str(target.get("organization") or ""),
            "expected_scope": str(target.get("expected_scope") or ""), "required_topic_terms": required_terms,
            "target_kind": "direct_topic_specific", "permitted_domain": domain in domains,
            "direct_access_expectation": "one_exact_allowlisted_topic_locator_without_redirects",
            "material_difference_rationale": "exact topic resource distinct from prior generic landing locator",
            "budget_cost": {"queries": 1, "retrievals": 1}, "rank": rank,
            "rejection_reasons": tuple(reasons), "candidate_digest": _digest(payload),
        })
    return tuple(item for item in candidates if not item["rejection_reasons"])[:maximum_candidates]


def compile_adapter_repair_retry_candidate(
    plan: Mapping[str, Any],
    failure: Mapping[str, Any],
    diagnostics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Permit one corrected-locator retry only after diagnostics prove the adapter defect."""

    failed_target = str(failure.get("source_target") or "")
    canonical = _canonical_reference(failed_target)
    working = next(
        (
            dict(item)
            for item in diagnostics
            if _canonical_reference(str(item.get("canonical_target") or "")) == canonical
            and item.get("terminal_state") == "diagnostic_completed"
            and str(item.get("canonical_target") or "") != failed_target
        ),
        {},
    )
    if not working or str(failure.get("normalized_failure_type") or "") not in {"http_rejection", "http_client_error", "prohibited_redirect"}:
        return {}
    target = str(working.get("canonical_target") or "")
    source = next(
        (item for item in TOPIC_SOURCE_TARGETS.get(str(plan.get("topic") or ""), ()) if _canonical_reference(str(item["canonical_target"])) == canonical),
        {},
    )
    if not source:
        return {}
    payload = {"prior_plan": plan.get("research_plan_id"), "failure": failure.get("failure_id"), "target": target, "diagnostic": working.get("diagnostic_id")}
    return {
        "retry_candidate_id": stable_id("external-research-adapter-repair-retry", _digest(payload)),
        "canonical_target": canonical, "retrieval_target": target,
        "source_class": str(source["source_class"]), "organization": str(source["organization"]),
        "repair_reason": "direct_locator_path_semantics_preserved_after_diagnostic_proof",
        "diagnostic_id": str(working.get("diagnostic_id") or ""), "candidate_digest": _digest(payload),
    }


def compile_fallback_external_research_plan(
    *, prior_plan: Mapping[str, Any], failure: Mapping[str, Any], candidate: Mapping[str, Any],
    authority_request_id: str, operator_approval_id: str,
) -> ExternalResearchPlan:
    """Compile a one-retrieval version two plan without changing the failed plan."""

    requirement = {
        "agenda_id": prior_plan.get("agenda_id"), "proposal_id": prior_plan.get("proposal_id"), "mission_id": prior_plan.get("mission_id"),
        "goal_id": prior_plan.get("goal_id"), "requirement_id": prior_plan.get("requirement_id"), "information_need_ids": prior_plan.get("information_need_ids"),
        "topic": prior_plan.get("topic"),
    }
    decision = {"decision_id": prior_plan.get("policy_decision_id")}
    return compile_external_research_plan(
        requirement=requirement, decision=decision, authority_request_id=authority_request_id, operator_approval_id=operator_approval_id,
        allowed_domains=(urlparse(str(candidate.get("retrieval_target") or candidate.get("canonical_target") or "")).hostname or "",),
        source_target=str(candidate.get("retrieval_target") or candidate.get("canonical_target") or ""), source_class=str(candidate.get("source_class") or ""),
        source_organization=str(candidate.get("organization") or ""), plan_version=int(prior_plan.get("plan_version") or 1) + 1,
        prior_plan_id=str(prior_plan.get("research_plan_id") or ""), prior_failure_id=str(failure.get("failure_id") or ""),
        fallback_candidate_id=str(candidate.get("fallback_candidate_id") or ""),
        prior_query_usage=int(dict(failure.get("budget_effect") or {}).get("queries_used") or 0),
        prior_retrieval_usage=int(dict(failure.get("budget_effect") or {}).get("retrievals_used") or 0),
        query_budget=1, retrieval_budget=1, accepted_source_budget=1,
        required_topic_terms=tuple(candidate.get("required_topic_terms") or ()),
        source_target_kind=str(candidate.get("target_kind") or "registry_fallback"),
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


def compile_retrieval_attempt(
    plan: ExternalResearchPlan | Mapping[str, Any], claim: ExternalResearchExecutionClaim | Mapping[str, Any], *, adapter_identity: str,
) -> ExternalResearchRetrievalAttempt:
    """Claim one bounded retrieval after the durable plan claim is restored."""

    raw_plan = plan.as_dict() if isinstance(plan, ExternalResearchPlan) else dict(plan)
    raw_claim = claim.as_dict() if isinstance(claim, ExternalResearchExecutionClaim) else dict(claim)
    target = str(raw_plan.get("source_target") or "")
    query_id = stable_id("external-research-query", raw_plan.get("research_plan_id"), raw_plan.get("research_questions"))
    payload = {"plan": raw_plan.get("research_plan_id"), "claim": raw_claim.get("claim_id"), "query": query_id, "target": target, "adapter": adapter_identity}
    return ExternalResearchRetrievalAttempt(
        retrieval_attempt_id=stable_id("external-research-retrieval-attempt", _digest(payload)), research_plan_id=str(raw_plan.get("research_plan_id") or ""),
        claim_id=str(raw_claim.get("claim_id") or ""), query_id=query_id, target_reference=target, attempt_number=1,
        claimed_at=utc_now(), status="retrieval_claimed", adapter_identity=adapter_identity, attempt_digest=_digest(payload),
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
    required_terms = tuple(
        str(value).strip().lower()
        for value in (raw_plan.get("required_topic_terms") or (str(raw_plan.get("topic") or "").replace("_", " "),))
        if str(value).strip()
    )
    missing_terms = tuple(term for term in required_terms if term not in text.lower())
    relevance = "relevant" if not missing_terms else "uncertain"
    if relevance != "relevant":
        reasons.append("topic_relevance_unproven")
    if str(raw_plan.get("source_target_kind") or "") == "direct_topic_specific" and reference != _canonical_reference(str(raw_plan.get("source_target") or "")):
        reasons.append("direct_target_mismatch")
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


def synthesize_external_research_result(
    plan: ExternalResearchPlan | Mapping[str, Any],
    records: Sequence[ExternalResearchSourceRecord | Mapping[str, Any]],
    *,
    retrieval_attempts: Sequence[Mapping[str, Any]] = (),
    stopping_reason: str = "accepted_source_threshold",
) -> dict[str, Any]:
    raw_plan = plan.as_dict() if isinstance(plan, ExternalResearchPlan) else dict(plan)
    normalized = tuple(item.as_dict() if isinstance(item, ExternalResearchSourceRecord) else dict(item) for item in records)
    accepted = tuple(item for item in normalized if item.get("status") == "accepted")[: int(raw_plan.get("accepted_source_budget") or 0)]
    claims: dict[str, set[str]] = {}
    for item in accepted:
        for claim in item.get("normalized_claims") or ():
            claims.setdefault(str(claim), set()).add(str(item.get("source_record_id") or ""))
    contradiction = len(accepted) > 1 and any("not" in claim.lower() for claim in claims) and any("not" not in claim.lower() for claim in claims)
    status = "research_completed" if len(accepted) >= 1 else "research_validation_failed"
    payload = {"plan": raw_plan.get("research_plan_id"), "accepted": tuple(item.get("source_record_id") for item in accepted), "claims": {key: sorted(value) for key, value in claims.items()}, "contradiction": contradiction, "status": status, "attempts": tuple(item.get("retrieval_attempt_id") for item in retrieval_attempts), "stopping_reason": stopping_reason}
    return {
        "research_result_id": stable_id("external-research-result", _digest(payload)), "research_plan_id": raw_plan.get("research_plan_id"), "claim_id": str(next(iter(retrieval_attempts), {}).get("claim_id") or ""), "status": status,
        "query_ids": tuple(item.get("query_id") for item in retrieval_attempts), "attempted_source_count": len(normalized), "accepted_source_count": len(accepted), "rejected_source_count": len(normalized) - len(accepted),
        "accepted_source_ids": tuple(item.get("source_record_id") for item in accepted), "rejected_source_ids": tuple(item.get("source_record_id") for item in normalized if item.get("status") != "accepted"),
        "normalized_claims": tuple(sorted(claims)), "claim_provenance": {key: tuple(sorted(value)) for key, value in claims.items()},
        "contradictions": ("scope_or_claim_tension_requires_explicit_follow_up",) if contradiction else (), "unresolved_needs": ("independent_sealed_evaluation_required",),
        "budget_used": {"queries": len(tuple(retrieval_attempts)), "retrievals": len(normalized), "accepted_sources": len(accepted), "content_bytes": sum(len(str(item.get("content_digest") or "")) for item in normalized)},
        "stopping_reason": stopping_reason, "provenance_summary": tuple({"source_record_id": item.get("source_record_id"), "canonical_reference": item.get("canonical_reference"), "content_digest": item.get("content_digest")} for item in accepted),
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

    target = str(plan.get("source_target") or "")
    if not target:
        return ()
    domain = urlparse(target).hostname or ""
    request = ExternalRetrievalRequest(
        request_id=stable_id("external-research-rc8-request", plan.get("research_plan_id"), domain),
        target=target, purpose=f"bounded evidence for {plan.get('topic') or ''}", operator_approved=True,
    )
    outcome = execute_mock_retrieval(request, content=f"The {str(plan.get('topic') or '').replace('_', ' ')} has a bounded mathematical scope and prerequisite conditions.", env={RC8_RETRIEVAL_ENABLED_ENV: "true"})
    if outcome.bundle is None:
        return ()
    source = outcome.bundle.sources[0]
    return ({
        "url": source.provenance.url, "title": "", "author_or_organization": "",
        "publisher": "", "source_class": "peer_reviewed_or_academic" if source.provenance.domain.endswith(".edu") else "recognized_reference",
        "content": source.sanitized_text, "claims": tuple(citation.claim for citation in source.citations),
        "retrieval_id": source.source_id, "query_id": request.request_id, "content_type": source.provenance.content_type, "hostile_content": bool(source.hostile_findings),
    },)


def execute_rc8_live_research_adapter(plan: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Use RC8's opt-in transport for one approved planned target at a time."""

    target = str(plan.get("source_target") or "")
    if not target:
        return ()
    domain = urlparse(target).hostname or ""
    request = ExternalRetrievalRequest(
        request_id=stable_id("external-research-rc8-live-request", plan.get("research_plan_id"), domain),
        target=target, purpose=f"bounded evidence for {plan.get('topic') or ''}", operator_approved=True,
    )
    outcome = execute_bounded_retrieval(request, env={RC8_RETRIEVAL_ENABLED_ENV: "true"})
    if outcome.bundle is None:
        raise ExternalResearchRetrievalError(outcome.failure_state or "bounded_retrieval_failed")
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
    attempts = tuple(dict(item) for item in state.get("retrieval_attempts") or ())
    if any(item.get("research_plan_id") != plan.get("research_plan_id") or item.get("claim_id") != claim.get("claim_id") or not item.get("retrieval_attempt_id") or not item.get("attempt_digest") for item in attempts):
        return False
    records = tuple(dict(item) for item in state.get("source_records") or ())
    identities = [item.get("source_record_id") for item in records]
    return len(identities) == len(set(identities)) and all(item.get("research_plan_id") == plan.get("research_plan_id") for item in records)


__all__ = [
    "SOURCE_CLASSES", "FAILURE_CLASSIFICATIONS", "ExternalResearchRetrievalError", "ExternalResearchPlan", "ExternalResearchExecutionClaim", "ExternalResearchSourceRecord",
    "compile_external_research_plan", "compile_fallback_external_research_plan", "classify_terminal_research_failure", "compile_historical_transport_interpretation", "compile_fallback_source_candidates", "compile_direct_topic_source_candidates", "compile_adapter_repair_retry_candidate", "compile_execution_claim", "compile_retrieval_attempt", "normalize_external_research_source",
    "synthesize_external_research_result", "execute_rc8_mock_research_adapter", "execute_rc8_live_research_adapter", "research_state_is_valid",
]
