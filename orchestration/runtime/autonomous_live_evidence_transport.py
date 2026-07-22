"""Bridge autonomous evidence campaigns to the existing RC8/PDF transport."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import unquote, urlparse

from orchestration.runtime.autonomous_evidence_acquisition_return_loop import run_autonomous_evidence_acquisition_return_loop
from orchestration.runtime.rc8_governed_external_retrieval import (
    RC8_RETRIEVAL_ENABLED_ENV, ContentTypePolicy, DomainPolicy, ExternalRetrievalRequest,
    RetrievalBudget, build_retrieval_policy, execute_bounded_retrieval,
)
from orchestration.runtime.governed_learning_strategy_acquisition import retrieve_exact_source


def _digest(value: Any) -> str:
    body = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _sentences(text: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip())


def _claim_extraction(*, text: str, label: str) -> tuple[dict[str, Any], ...]:
    """Extract only explicit definition/scope sentences, never keyword-only hits."""
    token = re.compile(rf"\b{re.escape(label.replace('_', ' '))}\b", flags=re.I)
    definition_markers = re.compile(r"\b(is|means|refers to|defined as)\b", flags=re.I)
    scope_markers = re.compile(r"\b(only|when|if|under|within|unless|not)\b", flags=re.I)
    claims = []
    for index, sentence in enumerate(_sentences(text)):
        if not token.search(sentence):
            continue
        if definition_markers.search(sentence):
            claims.append({"label": label, "claim_kind": "definition", "text": sentence, "excerpt_reference": f"sentence:{index + 1}"})
        if scope_markers.search(sentence):
            claims.append({"label": label, "claim_kind": "scope_limit", "text": sentence, "excerpt_reference": f"sentence:{index + 1}"})
    # One original sentence is enough for each facet; retaining duplicate prose
    # would inflate evidence without increasing support.
    result: dict[str, dict[str, Any]] = {}
    for claim in claims:
        result.setdefault(claim["claim_kind"], claim)
    return tuple(result[key] for key in sorted(result))


def _candidate_policy(candidate: Mapping[str, Any]):
    host = (urlparse(str(candidate["canonical_locator"])).hostname or "").lower()
    base = build_retrieval_policy()
    return replace(
        base,
        domain_policy=DomainPolicy((host,), base.domain_policy.denylist, subdomains_allowed=False),
        content_type_policy=ContentTypePolicy(("text/html", "text/plain", "application/pdf"), base.content_type_policy.blocked_content_types),
        budget=RetrievalBudget(max_requests=1, max_sources=1, max_bytes=250_000, timeout_seconds=base.budget.timeout_seconds, max_redirects=base.budget.max_redirects, max_queries=0),
    )


def _bounded_wikipedia_summary(locator: str) -> dict[str, Any]:
    """Retrieve a bounded existing summary only after RC8 rejects page size."""
    from orchestration.runtime.delta_1_4_live_wikipedia_runtime import (
        activated_wikipedia_profile,
        retrieve_wikipedia_text,
    )

    title = unquote(urlparse(locator).path.rsplit("/", 1)[-1]).replace("_", " ").strip()
    if not title:
        raise ValueError("wikipedia_summary_title_missing")
    result = retrieve_wikipedia_text(title, profile=activated_wikipedia_profile())
    text = str(result.extract)
    return {
        "canonical_locator": str(result.canonical_url),
        "source_record_id": _digest({"locator": locator, "source": text})[:24],
        "content_digest": _digest(text),
        "extraction_digest": _digest({"method": "wikipedia_bounded_summary", "text": text}),
        "provenance": "wikipedia_bounded_summary_extract",
        "content_text": text,
        "bounded_extract": True,
    }


def retrieve_candidate_via_existing_governed_transport(
    candidate: Mapping[str, Any],
    *,
    rc8_executor: Callable[..., Any] = execute_bounded_retrieval,
    pdf_retriever: Callable[[str], Mapping[str, Any]] = retrieve_exact_source,
    wikipedia_retriever: Callable[[str], Mapping[str, Any]] = _bounded_wikipedia_summary,
) -> dict[str, Any]:
    """Use RC8 for HTML/text and the existing exact-source path for PDFs."""
    locator = str(candidate["canonical_locator"])
    if locator.lower().endswith(".pdf"):
        retrieved = dict(pdf_retriever(locator))
        text = str(retrieved.get("content_text") or "")
        return {"canonical_locator": str(retrieved.get("canonical_locator") or locator), "source_record_id": _digest({"locator": locator, "source": retrieved.get("content_digest")})[:24], "content_digest": str(retrieved.get("content_digest") or _digest(text)), "extraction_digest": str(dict(retrieved.get("pdf_extraction") or {}).get("extraction_digest") or _digest(text)), "provenance": str(retrieved.get("retrieval_method") or "https_pdf_text_extraction"), "content_text": text}
    if str(candidate.get("extraction_strategy") or "") == "wikipedia_bounded_summary":
        host = (urlparse(locator).hostname or "").lower()
        if host != "en.wikipedia.org" or not bool(candidate.get("bounded_extract_permitted")):
            raise ValueError("wikipedia_bounded_summary_strategy_not_authorized")
        return dict(wikipedia_retriever(locator))
    request = ExternalRetrievalRequest(request_id=f"autonomous-live-evidence-{_digest(locator)[:16]}", target=locator, purpose="autonomous evidence contract", operator_approved=True, max_sources=1)
    result = rc8_executor(request, env={RC8_RETRIEVAL_ENABLED_ENV: "1"}, policy=_candidate_policy(candidate))
    if not result.bundle or not result.bundle.sources:
        host = (urlparse(locator).hostname or "").lower()
        if (
            getattr(result, "failure_state", "") == "content_budget_exhausted"
            and host == "en.wikipedia.org"
            and bool(candidate.get("bounded_extract_permitted"))
        ):
            # This is a smaller representation of the exact same page, not a
            # retry against a different source or a global budget increase.
            return dict(wikipedia_retriever(locator))
        raise ValueError(f"rc8_retrieval_failed:{getattr(result, 'failure_state', '') or result.decision.outcome}")
    source = result.bundle.sources[0]
    return {"canonical_locator": source.provenance.url, "source_record_id": source.source_id, "content_digest": _digest(source.sanitized_text), "extraction_digest": _digest({"method": "rc8_html_text", "text": source.sanitized_text}), "provenance": source.provenance.provenance_id, "content_text": source.sanitized_text}


def run_autonomous_live_evidence_transport_integration(*, campaign: Mapping[str, Any], planner_package: Mapping[str, Any], workspace: Path, metadata_discovery: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]], rc8_executor: Callable[..., Any] = execute_bounded_retrieval, pdf_retriever: Callable[[str], Mapping[str, Any]] = retrieve_exact_source) -> dict[str, Any]:
    """Connect the generic loop to real transport; it owns no source list."""
    workspace.mkdir(parents=True, exist_ok=True)
    claims_path = workspace / "AUTONOMOUS_LIVE_TRANSPORT_CLAIMS.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8")) if claims_path.exists() else {"claims": {}}

    def persist_claims() -> None:
        claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def retrieval_adapter(candidate: Mapping[str, Any]) -> dict[str, Any]:
        locator = str(candidate["canonical_locator"])
        claim_id = _digest({"campaign": campaign.get("campaign_id"), "locator": locator})[:24]
        prior = dict(claims["claims"].get(claim_id) or {})
        if prior.get("state") in {"completed", "failed"}:
            return {"canonical_locator": locator, "transport_failure": f"terminal_transport_claim:{prior.get('state')}"}
        claims["claims"][claim_id] = {"claim_id": claim_id, "canonical_locator": locator, "state": "claimed", "attempt_count": 1, "campaign_id": campaign.get("campaign_id")}
        persist_claims()
        try:
            raw = retrieve_candidate_via_existing_governed_transport(candidate, rc8_executor=rc8_executor, pdf_retriever=pdf_retriever)
        except Exception as exc:
            claims["claims"][claim_id] = {**claims["claims"][claim_id], "state": "failed", "terminal_reason": f"transport_failure:{type(exc).__name__}"}
            persist_claims()
            return {"canonical_locator": locator, "transport_failure": f"transport_failure:{type(exc).__name__}"}
        claims["claims"][claim_id] = {**claims["claims"][claim_id], "state": "completed", "source_digest": raw.get("content_digest"), "extraction_digest": raw.get("extraction_digest", "")}
        persist_claims()
        extracted_claims = _claim_extraction(text=str(raw.pop("content_text")), label=str(candidate["supports_labels"][0]))
        return {**raw, "claims": extracted_claims}
    result = run_autonomous_evidence_acquisition_return_loop(campaign=campaign, planner_package=planner_package, workspace=workspace, discovery_adapter=metadata_discovery, retrieval_adapter=retrieval_adapter)
    return {**result, "integration_id": _digest({"campaign": campaign.get("campaign_id"), "transport": "rc8_governed_external_retrieval"})[:24], "transport_owner": "rc8_governed_external_retrieval_and_governed_pdf_extraction", "metadata_discovery_owner": "existing_metadata_only_source_discovery_contract", "transport_claims_path": str(claims_path), "transport_claims": tuple(dict(value) for value in claims["claims"].values()), "live_transport": True}
