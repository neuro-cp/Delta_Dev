from __future__ import annotations

from typing import Iterable, List

from memory.persistent import MemoryRecord
from orchestration.attention.attention_item import AttentionItem


class AttentionService:
    """
    Application-level attention.

    Retrieval supplies candidates. Attention ranks what matters now.
    """

    def rank_memory(
        self,
        *,
        current_task: str,
        memories: Iterable[MemoryRecord],
        limit: int = 5,
    ) -> List[AttentionItem]:
        task_tokens = self._tokens(current_task)
        ranked: List[AttentionItem] = []

        for memory in memories:
            memory_tokens = self._tokens(
                " ".join([memory.text, memory.layer, " ".join(memory.tags)])
            )
            overlap = len(task_tokens & memory_tokens)
            task_relevance = overlap / max(1, len(task_tokens))
            confidence = max(0.0, min(1.0, memory.confidence))
            operator_priority = 1.0 if "operator" in memory.tags else 0.0
            experience_bias = 0.2 if memory.layer == "experience" else 0.0

            score = (
                (0.55 * task_relevance)
                + (0.25 * confidence)
                + (0.15 * operator_priority)
                + (0.05 * experience_bias)
            )

            ranked.append(
                AttentionItem(
                    item_id=memory.memory_id,
                    source=f"memory:{memory.layer}",
                    text=memory.text,
                    score=round(score, 4),
                    factors={
                        "task_relevance": round(task_relevance, 4),
                        "confidence": confidence,
                        "operator_priority": operator_priority,
                        "experience_bias": experience_bias,
                    },
                    metadata={"kind": memory.kind, "created_at": memory.created_at},
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[: max(1, int(limit))]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        import re

        return set(re.findall(r"[a-z0-9_]+", str(text).lower()))
