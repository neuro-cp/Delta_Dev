from __future__ import annotations

from typing import Iterable

from orchestration.attention import AttentionItem
from orchestration.reflection.reflection_record import ReflectionRecord


class ReflectionEngine:
    """
    Structured self-evaluation for one cognitive cycle.
    """

    def reflect(
        self,
        *,
        prompt: str,
        output: str,
        success: bool,
        attended_items: Iterable[AttentionItem],
        memory_ids: Iterable[str],
    ) -> ReflectionRecord:
        learned = []
        if success and output:
            learned.append("A cycle produced a successful output.")

        attended = list(attended_items)
        repeated = [
            item.item_id
            for item in attended
            if item.factors.get("task_relevance", 0.0) > 0.0
        ]

        consolidation_candidates = list(memory_ids) if success else []

        return ReflectionRecord(
            learned=learned,
            repeated=repeated,
            surprises=[],
            conflicts=[],
            consolidation_candidates=consolidation_candidates,
            metadata={
                "prompt_length": len(prompt),
                "output_length": len(str(output)),
                "attended_count": len(attended),
                "success": bool(success),
            },
        )
