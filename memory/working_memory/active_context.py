from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class WorkingMemoryContextItem:
    key: str
    kind: str
    source: str
    text: str
    priority: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkingMemoryContext:
    """
    Per-cycle active cognition context.

    This is not durable memory. It is assembled for one cognitive cycle and
    discarded after reflection/learning inspect it.
    """

    cycle_id: str
    items: List[WorkingMemoryContextItem] = field(default_factory=list)

    def as_advisory_payload(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": item.key,
                "kind": item.kind,
                "source": item.source,
                "text": item.text,
                "priority": item.priority,
                "metadata": dict(item.metadata),
            }
            for item in self.items
        ]

    def summary(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for item in self.items:
            counts[item.kind] = counts.get(item.kind, 0) + 1

        return {
            "item_count": len(self.items),
            "counts_by_kind": counts,
            "top_items": [
                {
                    "key": item.key,
                    "kind": item.kind,
                    "priority": item.priority,
                    "source": item.source,
                }
                for item in sorted(
                    self.items,
                    key=lambda candidate: candidate.priority,
                    reverse=True,
                )[:5]
            ],
        }


class WorkingMemoryContextBuilder:
    """
    Builds the active working context for a single cycle.
    """

    def build(
        self,
        *,
        cycle_id: str,
        observation: str,
        attended_context: Iterable[Dict[str, Any]],
        semantic_knowledge: Iterable[Any] = (),
        predictions: Iterable[Any] = (),
    ) -> WorkingMemoryContext:
        items: List[WorkingMemoryContextItem] = [
            WorkingMemoryContextItem(
                key=f"{cycle_id}:observation",
                kind="observation",
                source="operator",
                text=observation,
                priority=1.0,
                metadata={},
            )
        ]

        for item in attended_context:
            items.append(
                WorkingMemoryContextItem(
                    key=str(item.get("memory_id", item.get("key", ""))),
                    kind="attended_experience",
                    source=str(item.get("source", "memory")),
                    text=str(item.get("text", "")),
                    priority=float(item.get("score", 0.0)),
                    metadata={
                        "factors": dict(item.get("factors", {})),
                        "source_metadata": dict(item.get("metadata", {})),
                    },
                )
            )

        for record in semantic_knowledge:
            items.append(
                WorkingMemoryContextItem(
                    key=getattr(record, "concept_id", ""),
                    kind="semantic_knowledge",
                    source="knowledge",
                    text=getattr(record, "definition", ""),
                    priority=float(getattr(record, "confidence", 0.0)),
                    metadata={
                        "concept": getattr(record, "concept", ""),
                        "supporting_evidence": list(
                            getattr(record, "supporting_evidence", [])
                        ),
                    },
                )
            )

        for prediction in predictions:
            items.append(
                WorkingMemoryContextItem(
                    key=getattr(prediction, "prediction_id", ""),
                    kind="prediction",
                    source="prediction",
                    text=getattr(prediction, "expectation", ""),
                    priority=float(getattr(prediction, "confidence", 0.0)),
                    metadata={
                        "source_concept_id": getattr(
                            prediction,
                            "source_concept_id",
                            "",
                        ),
                        "status": getattr(prediction, "status", ""),
                    },
                )
            )

        return WorkingMemoryContext(cycle_id=cycle_id, items=items)
