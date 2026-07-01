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
        working_memory_summary: dict | None = None,
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
        quality = self._quality_score(
            success=success,
            output=output,
            attended_count=len(attended),
            working_memory_summary=working_memory_summary or {},
            consolidation_candidates=consolidation_candidates,
            repeated=repeated,
        )

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
                "working_memory": dict(working_memory_summary or {}),
                "quality": quality,
            },
        )

    @staticmethod
    def _quality_score(
        *,
        success: bool,
        output: str,
        attended_count: int,
        working_memory_summary: dict,
        consolidation_candidates: list[str],
        repeated: list[str],
    ) -> dict:
        dimensions = {
            "success_observed": bool(success),
            "output_present": bool(str(output).strip()),
            "attention_used": attended_count > 0,
            "working_memory_observed": bool(working_memory_summary),
            "consolidation_candidates_identified": bool(consolidation_candidates),
            "repetition_detected": bool(repeated),
        }
        score = round(
            sum(1 for value in dimensions.values() if value) / len(dimensions),
            4,
        )
        return {
            "score": score,
            "dimensions": dimensions,
            "method": "reflection_quality_v1",
        }
