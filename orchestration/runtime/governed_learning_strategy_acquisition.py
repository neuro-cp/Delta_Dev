"""Exact-source acquisition for a validated governed learning strategy."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping
import unicodedata
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.governed_pdf_extraction import extract_governed_pdf_text


def _digest(value: Any) -> str:
    body = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_same_exact_resource_chain(requested_locator: str, canonical_locator: str) -> bool:
    """Allow only URL canonicalization that preserves the approved resource."""

    requested = urlparse(requested_locator)
    canonical = urlparse(canonical_locator)
    return (
        requested.scheme == canonical.scheme == "https"
        and requested.hostname == canonical.hostname
        and requested.port == canonical.port
        and requested.path.rstrip("/") == canonical.path.rstrip("/")
        and requested.params == canonical.params
        and requested.query == canonical.query
        and not canonical.fragment
    )


class _SameHostRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        if urlparse(newurl).hostname != urlparse(req.full_url).hostname:
            raise ValueError("exact_source_redirect_left_approved_host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def retrieve_exact_source(locator: str) -> dict[str, Any]:
    """Fetch one approved HTTPS source while allowing same-host redirects only."""

    parsed = urlparse(locator)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("exact_source_locator_requires_https_host")
    response = build_opener(_SameHostRedirects()).open(Request(locator, headers={"User-Agent": "DELTA-governed-learning/1.0"}), timeout=30)
    with response:
        final = str(response.geturl())
        if urlparse(final).hostname != parsed.hostname:
            raise ValueError("exact_source_final_host_mismatch")
        raw = response.read(2_000_000)
        content_type = str(response.headers.get("Content-Type") or "").lower()
    if "pdf" in content_type or final.lower().endswith(".pdf"):
        source_digest = _digest(raw)
        extraction = extract_governed_pdf_text(
            pdf_bytes=raw, source_locator=final, source_digest=source_digest, retrieval_claim_id=stable_id("exact-source-parser", locator, source_digest),
            content_type=content_type or "application/pdf",
        )
        if extraction.get("status") != "completed":
            raise ValueError(f"exact_source_pdf_parse_failed:{extraction.get('failure_reason') or 'unknown'}")
        repeated = extract_governed_pdf_text(
            pdf_bytes=raw, source_locator=final, source_digest=source_digest, retrieval_claim_id=stable_id("exact-source-parser-repeat", locator, source_digest),
            content_type=content_type or "application/pdf",
        )
        if repeated.get("status") != "completed" or repeated.get("extraction_digest") != extraction.get("extraction_digest"):
            raise ValueError("exact_source_pdf_extraction_nondeterministic")
        text = str(extraction["text"])
        method = "https_pdf_text_extraction"
        pdf_extraction = {
            "parser_identity": extraction["parser_identity"], "parser_version": extraction["parser_version"],
            "page_count": extraction["page_count"], "page_records": tuple(dict(item) for item in extraction["page_records"]),
            "normalized_page_records": tuple({"page_number": item["page_number"], "normalized_text": normalize_source_text_for_matching(str(item["text"]))} for item in extraction["page_records"]),
            "extraction_digest": extraction["extraction_digest"], "repeat_extraction_digest": repeated["extraction_digest"],
            "repeat_extraction_identical": True, "source_bytes_digest": source_digest,
        }
    else:
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw.decode("utf-8", errors="replace"))).strip()
        method = "https_html_text_extraction"
    if not text:
        raise ValueError("exact_source_no_extractable_text")
    result = {"canonical_locator": final, "retrieved_at": _now(), "retrieval_method": method, "content_text": text, "content_digest": _digest(raw)}
    if "pdf_extraction" in locals():
        result["pdf_extraction"] = pdf_extraction
    return result


def _question_term(question: Mapping[str, Any]) -> str:
    match = re.search(r"What does (.+?) mean", str(question.get("question") or ""), flags=re.I)
    return match.group(1).strip().lower() if match else ""


def normalize_source_text_for_matching(value: str) -> str:
    """Normalize common PDF representation artifacts without changing stored text."""

    normalized = unicodedata.normalize("NFKC", str(value or "")).lower()
    normalized = re.sub(r"(?<=\w)-\s+(?=\w)", "", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def source_text_matches_question_term(*, term: str, source_text: str) -> bool:
    """Compare a hyphenated learner term to normalized, original-text-backed text."""

    parts = tuple(part for part in str(term or "").lower().split("-") if part)
    if not parts:
        return False
    return bool(re.search(r"[-\s]*".join(re.escape(part) for part in parts), normalize_source_text_for_matching(source_text)))


def compile_strategy_acquisition_result(
    *,
    strategy: Mapping[str, Any],
    authority_request: Mapping[str, Any],
    retrieval: Mapping[str, Any],
) -> dict[str, Any]:
    """Select source excerpts only for strategy-authored learner questions."""

    text = re.sub(r"\s+", " ", str(retrieval.get("content_text") or "")).strip()
    page_records = tuple(dict(item) for item in (dict(retrieval.get("pdf_extraction") or {}).get("page_records") or ()) if isinstance(item, Mapping))
    sentence_records = tuple(
        {"page_number": int(page.get("page_number") or 0), "text": sentence.strip()}
        for page in page_records for sentence in re.split(r"(?<=[.!?])\s+", str(page.get("text") or "")) if sentence.strip()
    ) or tuple({"page_number": 0, "text": item.strip()} for item in re.split(r"(?<=[.!?])\s+", text) if item.strip())
    claims: list[dict[str, Any]] = []
    sufficiency: list[dict[str, Any]] = []
    questions = tuple(dict(item) for item in (strategy.get("learning_questions") or ()) if isinstance(item, Mapping))
    hypotheses = {str(item.get("prerequisite_id") or ""): item for item in (strategy.get("prerequisite_hypotheses") or ()) if isinstance(item, Mapping)}
    for question in questions:
        term = _question_term(question)
        match_record = next((item for item in sentence_records if term and source_text_matches_question_term(term=term, source_text=str(item["text"]))), {})
        matched = str(match_record.get("text") or "")
        evidence_ids: tuple[str, ...] = ()
        if matched:
            claim_id = stable_id("strategy-source-claim", strategy.get("strategy_id"), question.get("question_id"), retrieval.get("content_digest"), matched)
            claims.append({
                "claim_id": claim_id, "claim_text": matched[:1000], "source_excerpt_reference": (f"page:{match_record['page_number']}/sentence:{len(claims) + 1}" if match_record.get("page_number") else f"sentence:{len(claims) + 1}"),
                "source_digest": retrieval.get("content_digest"), "learning_question_ids": (question.get("question_id"),),
                "prerequisite_hypothesis_ids": tuple(question.get("prerequisite_ids") or ()), "confidence": 0.75,
                "support_type": "directly_stated", "uncertainty": "source excerpt may not cover every requested relationship",
            })
            evidence_ids = (claim_id,)
        sufficiency.append({
            "question_id": question.get("question_id"), "status": "answered" if matched else "unanswered",
            "supporting_evidence_ids": evidence_ids, "missing_information": "" if matched else f"source text did not directly answer the strategy question about {term}",
            "confidence": 0.75 if matched else 0.9,
        })
    answered = sum(item["status"] == "answered" for item in sufficiency)
    outcome = "learning_strategy_source_sufficient" if answered == len(sufficiency) else "learning_strategy_source_partially_sufficient" if answered else "learning_strategy_source_insufficient"
    artifact_id = stable_id("strategy-study-artifact", strategy.get("strategy_id"), retrieval.get("content_digest")) if claims else ""
    study_artifact = {
        "artifact_id": artifact_id,
        "strategy_id": strategy.get("strategy_id"),
        "source_locator": retrieval.get("canonical_locator"),
        "source_digest": retrieval.get("content_digest"),
        "claims": tuple(claims), "unresolved_questions": tuple(item["question_id"] for item in sufficiency if item["status"] != "answered"),
        "capability_claim_prohibited": True,
        "evaluator_material_present": False,
    } if claims else {}
    verification = {
        "all_high_priority_questions_grounded": bool(sufficiency) and answered == len(sufficiency),
        "hypotheses_resolved_or_unresolved": True,
        "study_artifact_ready_for_revised_attempt": outcome == "learning_strategy_source_sufficient",
        "capability_promotion_prohibited": True,
    }
    return {
        "acquisition_result_id": stable_id("learning-strategy-acquisition", strategy.get("strategy_id"), retrieval.get("content_digest")),
        "strategy_id": strategy.get("strategy_id"), "strategy_evidence_digest": strategy.get("evidence_digest"),
        "authority_request_id": authority_request.get("request_id"), "authority_receipt_id": authority_request.get("request_id"),
        "source_identity": authority_request.get("source_identity"), "source_locator": retrieval.get("canonical_locator"),
        "source_digest": retrieval.get("content_digest"), "retrieved_at": retrieval.get("retrieved_at"), "retrieval_method": retrieval.get("retrieval_method"),
        "pdf_extraction": dict(retrieval.get("pdf_extraction") or {}),
        "retrieval_count": 1, "claims": tuple(claims), "question_sufficiency": tuple(sufficiency),
        "outcome": outcome, "study_artifact": study_artifact, "internal_verification": verification,
        "recommended_next_action": "request_narrower_authority" if outcome != "learning_strategy_source_sufficient" else "await_operator_authorization_for_revised_attempt",
        "result_digest": _digest({"strategy": strategy.get("strategy_id"), "source": retrieval.get("content_digest"), "sufficiency": sufficiency}),
    }


def compile_strategy_acquisition_evidence_linkage_reassessment(
    *,
    strategy: Mapping[str, Any],
    acquisition_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Relink retained excerpts conservatively without rewriting acquisition history.

    A normalized match creates contextual support only.  It cannot itself satisfy
    a question's original teaching-evidence condition or promote a capability.
    """

    questions = {
        str(item.get("question_id") or ""): dict(item)
        for item in (strategy.get("learning_questions") or ()) if isinstance(item, Mapping)
    }
    original_sufficiency = {
        str(item.get("question_id") or ""): dict(item)
        for item in (acquisition_result.get("question_sufficiency") or ()) if isinstance(item, Mapping)
    }
    links: list[dict[str, Any]] = []
    for question_id, sufficiency in original_sufficiency.items():
        if sufficiency.get("status") == "answered" or question_id not in questions:
            continue
        term = _question_term(questions[question_id])
        for claim in acquisition_result.get("claims") or ():
            if not isinstance(claim, Mapping) or not source_text_matches_question_term(term=term, source_text=str(claim.get("claim_text") or "")):
                continue
            if term in str(claim.get("claim_text") or "").lower():
                continue
            links.append({
                "question_id": question_id,
                "claim_id": str(claim.get("claim_id") or ""),
                "source_excerpt_reference": str(claim.get("source_excerpt_reference") or ""),
                "original_claim_text": str(claim.get("claim_text") or ""),
                "normalized_match_term": term,
                "support_type": "contextual_reference_only",
                "sufficiency_status": "linked_but_not_sufficient",
                "reason": "normalized text reveals a retained contextual reference, but the original direct-explanation condition remains unproven",
            })
    payload = {
        "strategy_id": strategy.get("strategy_id"), "acquisition_result_digest": acquisition_result.get("result_digest"), "links": links,
    }
    return {
        "reassessment_id": stable_id("strategy-acquisition-evidence-linkage-reassessment", _digest(payload)),
        "strategy_id": strategy.get("strategy_id"),
        "acquisition_result_id": acquisition_result.get("acquisition_result_id"),
        "acquisition_result_digest": acquisition_result.get("result_digest"),
        "links": tuple(links),
        "outcome": "evidence_linked_but_sufficiency_unchanged" if links else "no_normalization_linkage_found",
        "historical_acquisition_immutable": True,
        "capability_promotion_prohibited": True,
        "retrieval_not_performed": True,
        "created_at": _now(),
        "reassessment_digest": _digest(payload),
    }
