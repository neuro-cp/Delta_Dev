from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from memory.working_memory.active_context import WorkingMemoryContext, WorkingMemoryContextItem
from orchestration.runtime.candidate_knowledge_retrieval import (
    ActivatedKnowledgeItem,
    KnowledgeActivation,
)


@dataclass(frozen=True)
class AttentionDecision:
    concept_id: str
    classification: str
    attention_score: float
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeAttention:
    query: str
    decisions: list[AttentionDecision]
    selected_items: list[ActivatedKnowledgeItem]

    def as_working_memory_context(self, *, cycle_id: str) -> WorkingMemoryContext:
        decisions = {decision.concept_id: decision for decision in self.decisions}
        return WorkingMemoryContext(
            cycle_id=cycle_id,
            items=[
                WorkingMemoryContextItem(
                    key=item.concept_id,
                    kind="candidate_knowledge",
                    source="candidate_knowledge_attention",
                    text=f"{item.concept}: {item.definition}",
                    priority=decisions[item.concept_id].attention_score,
                    metadata={
                        "confidence": item.confidence,
                        "recommendation": item.recommendation,
                        "promotion_score": item.promotion_score,
                        "source_store": item.source_store,
                        "attention_classification": decisions[item.concept_id].classification,
                        "activation_score": item.score,
                        **dict(item.metadata),
                    },
                )
                for item in self.selected_items
            ],
        )


class KnowledgeAttentionFilter:
    """
    Read-only attention layer between activation and working memory.

    Activation remains broad candidate retrieval. Attention decides which
    activated candidates deserve immediate working-memory resources.
    """

    def filter(self, activation: KnowledgeActivation) -> KnowledgeAttention:
        query_tokens = _expanded_tokens(activation.query)
        item_tokens = {
            item.concept_id: _expanded_tokens(f"{item.concept} {item.definition}")
            for item in activation.items
        }
        rare_query_tokens = _rare_query_tokens(query_tokens, item_tokens)
        decisions: list[AttentionDecision] = []
        selected: list[ActivatedKnowledgeItem] = []
        for item in activation.items:
            tokens = item_tokens[item.concept_id]
            focus_overlap = len(rare_query_tokens & tokens)
            domain_anchor_overlap = len((query_tokens & _DOMAIN_ANCHOR_TERMS) & tokens)
            total_overlap = len(query_tokens & tokens)
            lexical_score = (0.65 * _ratio(focus_overlap, max(1, len(rare_query_tokens)))) + (
                0.35 * _ratio(total_overlap, max(1, len(query_tokens)))
            )
            centrality = float(item.metadata.get("projected_centrality", 0.0) or 0.0)
            evidence_support = float(item.metadata.get("evidence_support", 0.0) or 0.0)
            attention_score = _clamp(
                (0.62 * lexical_score)
                + (0.18 * item.score)
                + (0.10 * item.confidence)
                + (0.06 * centrality)
                + (0.04 * evidence_support)
            )
            classification, rationale = _classify(
                focus_overlap=focus_overlap,
                domain_anchor_overlap=domain_anchor_overlap,
                total_overlap=total_overlap,
                attention_score=attention_score,
                rare_query_tokens=rare_query_tokens,
            )
            decision = AttentionDecision(
                concept_id=item.concept_id,
                classification=classification,
                attention_score=round(attention_score, 4),
                rationale=rationale,
                metadata={
                    "focus_overlap": focus_overlap,
                    "domain_anchor_overlap": domain_anchor_overlap,
                    "total_overlap": total_overlap,
                    "rare_query_tokens": sorted(rare_query_tokens),
                    "activation_score": item.score,
                },
            )
            decisions.append(decision)
            if classification in {"Core", "Supporting"}:
                selected.append(item)
        return KnowledgeAttention(
            query=activation.query,
            decisions=decisions,
            selected_items=selected,
        )


def _classify(
    *,
    focus_overlap: int,
    domain_anchor_overlap: int,
    total_overlap: int,
    attention_score: float,
    rare_query_tokens: set[str],
) -> tuple[str, str]:
    if rare_query_tokens and focus_overlap >= 2 and attention_score >= 0.22:
        return "Core", "multiple distinctive query terms matched"
    if rare_query_tokens and focus_overlap >= 1 and attention_score >= 0.18:
        return "Supporting", "one distinctive query term matched with sufficient support"
    if domain_anchor_overlap >= 1 and total_overlap >= 3 and attention_score >= 0.25:
        return "Supporting", "domain anchor matched with sufficient expanded question overlap"
    if not rare_query_tokens and total_overlap >= 2 and attention_score >= 0.2:
        return "Supporting", "no distinctive query terms; general overlap is sufficient"
    if total_overlap > 0:
        return "Peripheral", "weak overlap retained outside working memory"
    return "Discarded", "no meaningful query overlap"


def _rare_query_tokens(query_tokens: set[str], item_tokens: dict[str, set[str]]) -> set[str]:
    counts: dict[str, int] = {token: 0 for token in query_tokens}
    for tokens in item_tokens.values():
        for token in query_tokens & tokens:
            counts[token] += 1
    rare = {
        token
        for token, count in counts.items()
        if 0 < count <= 2 and token not in _GENERIC_FOCUS_TERMS
    }
    return rare or {token for token in query_tokens if token not in _GENERIC_FOCUS_TERMS}


def _expanded_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-z0-9_]+", str(text).lower()):
        if len(raw) < 3 or raw in _STOPWORDS:
            continue
        normalized = _normalize_token(raw)
        tokens.add(normalized)
        tokens.update(_TOKEN_EXPANSIONS.get(normalized, ()))
        if "snowstorm" in normalized:
            tokens.update({"snow", "storm"})
    return tokens


def _normalize_token(token: str) -> str:
    if token == "cities":
        return "city"
    if token in {"allocated", "allocating", "allocation"}:
        return "allocate"
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


_STOPWORDS = {
    "and",
    "are",
    "before",
    "during",
    "for",
    "from",
    "how",
    "into",
    "should",
    "that",
    "the",
    "what",
    "when",
    "where",
    "why",
    "with",
}

_GENERIC_FOCUS_TERMS = {
    "city",
    "cause",
    "increase",
    "limited",
    "prepare",
    "severe",
}

_DOMAIN_ANCHOR_TERMS = {
    "gps",
}

_TOKEN_EXPANSIONS = {
    "allocate": {"allocation", "priority", "triage"},
    "flood": {"risk", "impact", "mitigation"},
    "gps": {"accuracy", "signal"},
}
