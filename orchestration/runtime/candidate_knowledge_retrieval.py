from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from knowledge.semantic_record import SemanticKnowledgeRecord
from memory.working_memory.active_context import (
    WorkingMemoryContext,
    WorkingMemoryContextItem,
)


@dataclass(frozen=True)
class ActivatedKnowledgeItem:
    concept_id: str
    concept: str
    definition: str
    score: float
    confidence: float
    recommendation: str
    promotion_score: float
    source_store: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeActivation:
    query: str
    items: list[ActivatedKnowledgeItem]

    def as_working_memory_context(self, *, cycle_id: str) -> WorkingMemoryContext:
        return WorkingMemoryContext(
            cycle_id=cycle_id,
            items=[
                WorkingMemoryContextItem(
                    key=item.concept_id,
                    kind="candidate_knowledge",
                    source="candidate_knowledge_store",
                    text=f"{item.concept}: {item.definition}",
                    priority=item.score,
                    metadata={
                        "confidence": item.confidence,
                        "recommendation": item.recommendation,
                        "promotion_score": item.promotion_score,
                        "source_store": item.source_store,
                        **dict(item.metadata),
                    },
                )
                for item in self.items
            ],
        )


class KnowledgeActivationEngine:
    """
    Read-only activation layer over candidate canonical knowledge.

    This does not promote, mutate, merge, or validate knowledge. It only ranks
    existing isolated-store concepts so the Runtime phase can test whether Delta
    can think with governed knowledge before freezing a canonical schema.
    """

    def __init__(self, *, store_root: str | Path, reports_dirs: Iterable[str | Path] = ()) -> None:
        self._store_root = Path(store_root)
        self._reports_dirs = tuple(Path(path) for path in reports_dirs)

    def activate(self, query: str, *, limit: int = 50) -> KnowledgeActivation:
        query_tokens = _tokens(query)
        if not query_tokens:
            return KnowledgeActivation(query=query, items=[])
        decisions = self._governance_by_concept_id()
        records = _latest_records(self._load_records())
        ranked: list[ActivatedKnowledgeItem] = []
        for record in records:
            text = f"{record.concept} {record.definition}"
            relevance = _jaccard(query_tokens, _tokens(text))
            if relevance <= 0.0:
                continue
            decision = decisions.get(record.concept_id, {})
            promotion_score = float(decision.get("promotion_score", 0.0) or 0.0)
            recommendation = str(decision.get("recommendation", "Unknown"))
            centrality = float(decision.get("dimensions", {}).get("projected_centrality", 0.0) or 0.0)
            support = float(decision.get("dimensions", {}).get("evidence_support", 0.0) or 0.0)
            score = _clamp(
                (0.55 * relevance)
                + (0.18 * float(record.confidence))
                + (0.14 * promotion_score)
                + (0.08 * centrality)
                + (0.05 * support)
            )
            ranked.append(
                ActivatedKnowledgeItem(
                    concept_id=record.concept_id,
                    concept=record.concept,
                    definition=record.definition,
                    score=round(score, 4),
                    confidence=float(record.confidence),
                    recommendation=recommendation,
                    promotion_score=promotion_score,
                    source_store=str(self._store_root),
                    metadata={
                        "relevance": round(relevance, 4),
                        "projected_centrality": centrality,
                        "evidence_support": support,
                        "supporting_evidence": list(record.supporting_evidence),
                        "relationship_ids": list(record.relationship_ids),
                    },
                )
            )
        ranked.sort(
            key=lambda item: (
                item.score,
                item.promotion_score,
                item.confidence,
                item.concept,
            ),
            reverse=True,
        )
        return KnowledgeActivation(query=query, items=ranked[: max(0, int(limit))])

    def _load_records(self) -> list[SemanticKnowledgeRecord]:
        path = self._store_root / "knowledge.jsonl"
        if not path.exists():
            return []
        records: list[SemanticKnowledgeRecord] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(SemanticKnowledgeRecord(**json.loads(line)))
        return records

    def _governance_by_concept_id(self) -> dict[str, dict[str, Any]]:
        decisions: dict[str, dict[str, Any]] = {}
        for reports_dir in self._reports_dirs:
            path = reports_dir / "promotion_governance_report.json"
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            for decision in payload.get("decisions", []):
                concept_id = decision.get("concept_id")
                if concept_id:
                    decisions[str(concept_id)] = decision
        return decisions


def _latest_records(records: list[SemanticKnowledgeRecord]) -> list[SemanticKnowledgeRecord]:
    superseded = {
        prior_id
        for record in records
        for prior_id in record.revision_history
    }
    return [record for record in records if record.concept_id not in superseded]


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", str(text).lower())
        if len(token) >= 3
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


CandidateKnowledgeItem = ActivatedKnowledgeItem
CandidateKnowledgeActivation = KnowledgeActivation
CandidateKnowledgeRetriever = KnowledgeActivationEngine
