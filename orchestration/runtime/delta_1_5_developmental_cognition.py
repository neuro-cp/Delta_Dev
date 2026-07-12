"""DELTA 1.5 governed developmental cognition primitives.

This module compares operator-approved external text evidence against the local
approved concept substrate, produces a bounded observation, and prepares a
promotion candidate for operator review. It is intentionally inert: it does not
retrieve externally, call providers, write memory, execute code, approve its own
objectives, commit, push, or persist hidden state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
import unicodedata
from typing import Any, Callable

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.rc2_developmental_concept_memory import query_approved_concepts


REPORT_ROOT = Path("reports") / "delta_1_5"


LocalConceptQuery = Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class EvidenceComparison:
    classification: str
    confidence: float
    local_match_count: int
    overlapping_terms: tuple[str, ...]
    novel_terms: tuple[str, ...]
    conflict_signals: tuple[str, ...]
    explanation: str
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class KnowledgeGap:
    gap_id: str
    summary: str
    missing_terms: tuple[str, ...]
    why_it_matters: str
    evidence_source: str
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentObjective:
    objective_id: str
    summary: str
    value: str
    effort: str
    risk: str
    success_criteria: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    requires_operator_approval: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class PromotionCandidate:
    candidate_id: str
    title: str
    source_url: str
    proposed_status: str
    proposed_changes: tuple[str, ...]
    evidence_terms: tuple[str, ...]
    approval_required: bool = True
    automatic_memory_write: bool = False
    canonical_write_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperatorInquiry:
    inquiry_id: str
    prompt: str
    options: tuple[str, ...]
    blocks_promotion: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentalCognitionResult:
    cycle_id: str
    observed_at: str
    evidence_title: str
    evidence_url: str
    observation: str
    comparison: EvidenceComparison
    knowledge_gap: KnowledgeGap
    objective: DevelopmentObjective
    promotion_candidate: PromotionCandidate
    operator_inquiry: OperatorInquiry
    local_concept_snapshot: dict[str, Any]
    safety: dict[str, bool] = field(default_factory=safety_metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_wikipedia_developmental_cognition(
    evidence: Any,
    *,
    local_query: LocalConceptQuery = query_approved_concepts,
) -> DevelopmentalCognitionResult:
    """Compare one Wikipedia text result with approved local concepts."""

    title = str(getattr(evidence, "title", "") or "").strip() or str(getattr(evidence, "query", "") or "Wikipedia evidence")
    query = str(getattr(evidence, "query", "") or title).strip()
    extract = str(getattr(evidence, "extract", "") or "")
    url = str(getattr(evidence, "canonical_url", "") or "")
    local = local_query(query)
    matches = tuple(local.get("matches") or ())
    local_text = _local_text(local)
    terms = _extract_evidence_terms(title, extract)
    overlapping = tuple(term for term in terms if _contains_term(local_text, term))
    novel = tuple(term for term in terms if not _contains_term(local_text, term))
    conflicts = _detect_conflict_signals(extract, local_text)
    comparison = _build_comparison(matches, overlapping, novel, conflicts)
    gap_terms = novel[:6] or terms[:3]
    gap = KnowledgeGap(
        gap_id=stable_id("delta15-gap", title, gap_terms),
        summary=_gap_summary(comparison.classification, title, gap_terms),
        missing_terms=gap_terms,
        why_it_matters=(
            "The runtime can answer the immediate question from external text, but it cannot improve its local model "
            "unless novel or higher-resolution evidence is surfaced as a governed review item."
        ),
        evidence_source=url,
    )
    objective = DevelopmentObjective(
        objective_id=stable_id("delta15-objective", title, comparison.classification, gap_terms),
        summary=f"Prepare a noncanonical review proposal for {title} from Wikipedia evidence.",
        value="medium: converts one retrieved article into a reviewable local-knowledge improvement opportunity",
        effort="low: reuse the existing approved-concept substrate and operator gates",
        risk="low: no memory write, provider call, or canonical promotion is performed automatically",
        success_criteria=(
            "external evidence is compared against local approved concepts",
            "known, novel, conflicting, or higher-resolution status is explicit",
            "a promotion candidate is prepared without being written",
            "the operator receives a concise approval question",
        ),
        stop_conditions=(
            "no reliable source text is available",
            "comparison cannot identify any reviewable delta",
            "operator approval is absent",
            "governance flags indicate provider, memory, canonical, commit, or push authority was used",
        ),
    )
    changes = tuple(f"Review whether `{term}` should become a noncanonical concept, relation, or evidence note." for term in gap_terms)
    candidate = PromotionCandidate(
        candidate_id=stable_id("delta15-promotion", title, url, gap_terms),
        title=f"{title} local knowledge review",
        source_url=url,
        proposed_status="operator_review_required_noncanonical_candidate",
        proposed_changes=changes or (f"Review whether {title} adds a useful local concept.",),
        evidence_terms=terms,
    )
    inquiry = OperatorInquiry(
        inquiry_id=stable_id("delta15-inquiry", candidate.candidate_id),
        prompt=(
            f"I found {comparison.classification.lower().replace('_', ' ')} evidence in `{title}`. "
            "Approve preparing a noncanonical expansion proposal for review?"
        ),
        options=("approve_prepare_proposal", "discuss_first", "reject_candidate"),
    )
    observation = _observation_sentence(comparison, title, gap_terms)
    return DevelopmentalCognitionResult(
        cycle_id=stable_id("delta15-cycle", title, url, utc_now()),
        observed_at=utc_now(),
        evidence_title=title,
        evidence_url=url,
        observation=observation,
        comparison=comparison,
        knowledge_gap=gap,
        objective=objective,
        promotion_candidate=candidate,
        operator_inquiry=inquiry,
        local_concept_snapshot=_snapshot_local(local),
    )


def render_developmental_observation(result: DevelopmentalCognitionResult) -> str:
    terms = ", ".join(result.knowledge_gap.missing_terms[:4]) or "no specific new term"
    return "\n".join([
        "Developmental observation:",
        result.observation,
        f"Candidate terms: {terms}.",
        result.operator_inquiry.prompt,
        "No memory was written; this is a gated promotion candidate only.",
    ])


def write_delta_1_5_campaign_reports(result: DevelopmentalCognitionResult, *, validation: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "campaign": "DELTA_1_5_GOVERNED_DEVELOPMENTAL_COGNITION",
        "objective": "Wikipedia evidence -> local comparison -> reviewable promotion candidate -> operator inquiry",
        "developmental_cognition": result.as_dict(),
        "validation": validation,
        "governance": {
            "provider_calls_performed": False,
            "automatic_memory_write_performed": False,
            "canonical_write_performed": False,
            "hidden_persistence_performed": False,
            "autonomous_execution_performed": False,
        },
    }
    write_json(REPORT_ROOT / "developmental_cognition_campaign.json", payload)
    write_markdown(REPORT_ROOT / "developmental_cognition_campaign.md", "DELTA 1.5 Developmental Cognition Campaign", payload)
    return payload


def _build_comparison(
    matches: tuple[dict[str, Any], ...],
    overlapping: tuple[str, ...],
    novel: tuple[str, ...],
    conflicts: tuple[str, ...],
) -> EvidenceComparison:
    if conflicts:
        classification = "POTENTIAL_CONFLICT"
        confidence = 0.55
        explanation = "External evidence contains cautious contradiction signals that require operator review."
    elif not matches:
        classification = "NOVEL"
        confidence = 0.74 if novel else 0.62
        explanation = "No approved local concept was retrieved for the evidence query."
    elif len(novel) >= 2:
        classification = "HIGHER_RESOLUTION"
        confidence = 0.78
        explanation = "Local concepts exist, but the external text introduces reviewable terms not represented in the retrieved local material."
    elif novel:
        classification = "PARTIAL_NOVELTY"
        confidence = 0.7
        explanation = "Local concepts overlap with the evidence, with one reviewable missing detail."
    else:
        classification = "KNOWN"
        confidence = 0.66
        explanation = "The extracted evidence terms are already represented in the retrieved local material."
    return EvidenceComparison(
        classification=classification,
        confidence=confidence,
        local_match_count=len(matches),
        overlapping_terms=overlapping,
        novel_terms=novel,
        conflict_signals=conflicts,
        explanation=explanation,
    )


def _extract_evidence_terms(title: str, extract: str) -> tuple[str, ...]:
    normalized = _normalize_text(f"{title}. {extract}")
    terms: list[str] = []
    known_terms = {
        "acid-base reaction": "acid-base reaction",
        "acid base reaction": "acid-base reaction",
        "chemical reaction": "chemical reaction",
        "ph": "pH",
        "titration": "titration",
        "acid-base theories": "acid-base theories",
        "acid base theories": "acid-base theories",
        "arrhenius acid-base theory": "Arrhenius acid-base theory",
        "arrhenius acid base theory": "Arrhenius acid-base theory",
        "bronsted-lowry acid-base theory": "Bronsted-Lowry acid-base theory",
        "bronsted lowry acid base theory": "Bronsted-Lowry acid-base theory",
        "lewis acid-base theory": "Lewis acid-base theory",
        "lewis acid base theory": "Lewis acid-base theory",
        "reaction mechanisms": "reaction mechanisms",
    }
    for needle, label in known_terms.items():
        if needle in normalized:
            _append_unique(terms, label)
    for match in re.finditer(r"(?:called|for example|such as)\s+([a-z][a-z0-9 -]{4,80})", normalized):
        phrase = re.split(r"[,.;:]", match.group(1))[0].strip()
        phrase = re.sub(r"^(the|a|an)\s+", "", phrase).strip()
        phrase = re.sub(r"\b(the|a|an|and|or)$", "", phrase).strip()
        if " for example " in f" {phrase} " or len(phrase.split()) > 6:
            continue
        if _term_is_useful(phrase):
            _append_unique(terms, phrase[:80])
    if not terms:
        for token in re.findall(r"\b[a-z][a-z0-9-]{4,}\b", normalized):
            if _term_is_useful(token):
                _append_unique(terms, token)
            if len(terms) >= 8:
                break
    return tuple(terms[:10])


def _detect_conflict_signals(extract: str, local_text: str) -> tuple[str, ...]:
    normalized_evidence = _normalize_text(extract)
    normalized_local = _normalize_text(local_text)
    signals: list[str] = []
    for phrase in ("is not", "does not", "cannot", "unlike", "rather than"):
        if phrase in normalized_evidence and phrase not in normalized_local:
            signals.append(phrase)
    return tuple(signals[:3])


def _local_text(local: dict[str, Any]) -> str:
    parts = [str(local.get("answer") or "")]
    for row in local.get("matches") or ():
        parts.append(str(row.get("concept_name") or ""))
        parts.append(str(row.get("short_definition") or ""))
        parts.extend(str(item) for item in row.get("propositions") or ())
        parts.extend(str(item) for item in row.get("related_concepts") or ())
    return _normalize_text(" ".join(parts))


def _snapshot_local(local: dict[str, Any]) -> dict[str, Any]:
    return {
        "matched": bool(local.get("matched")),
        "match_count": len(local.get("matches") or ()),
        "search_query": local.get("search_query"),
        "matches": [
            {
                "concept_name": row.get("concept_name"),
                "domain": row.get("domain"),
                "memory_type": row.get("memory_type"),
            }
            for row in (local.get("matches") or ())[:5]
        ],
    }


def _observation_sentence(comparison: EvidenceComparison, title: str, terms: tuple[str, ...]) -> str:
    term_text = ", ".join(terms[:3]) if terms else "no extracted term"
    if comparison.classification == "KNOWN":
        return f"`{title}` appears mostly represented locally; the retrieved evidence did not create an immediate review gap."
    return f"`{title}` produced {comparison.classification.lower().replace('_', ' ')} evidence: {term_text}."


def _gap_summary(classification: str, title: str, terms: tuple[str, ...]) -> str:
    term_text = ", ".join(terms[:4]) if terms else "article-level evidence"
    return f"{classification}: {title} may improve local knowledge around {term_text}."


def _contains_term(text: str, term: str) -> bool:
    normalized = _normalize_text(term)
    if not normalized:
        return False
    return normalized in text


def _normalize_text(text: str) -> str:
    cleaned = str(text or "").replace("–", "-").replace("—", "-")
    ascii_text = unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _term_is_useful(term: str) -> bool:
    stop = {
        "about",
        "alternative",
        "between",
        "called",
        "example",
        "several",
        "their",
        "there",
        "these",
        "those",
        "which",
    }
    normalized = _normalize_text(term)
    if len(normalized) < 3 or normalized in stop:
        return False
    return bool(re.search(r"[a-z]", normalized))


def _append_unique(items: list[str], value: str) -> None:
    key = _normalize_text(value)
    if not key:
        return
    if all(_normalize_text(item) != key for item in items):
        items.append(value)
