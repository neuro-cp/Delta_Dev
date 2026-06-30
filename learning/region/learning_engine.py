from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterable

from learning.region.learning_record import (
    ConfidenceUpdate,
    LearningRecord,
    SemanticCandidate,
)
from orchestration.attention import AttentionItem
from orchestration.reflection import ReflectionRecord


class LearningEngine:
    """
    First Learning Region.

    This engine performs structural learning only. It emits proposals,
    confidence-change suggestions, and questions. It does not apply them.
    """

    def learn(
        self,
        *,
        cycle_id: str,
        prompt: str,
        output: str,
        success: bool,
        attended_items: Iterable[AttentionItem],
        reflection: ReflectionRecord,
    ) -> LearningRecord:
        attended = list(attended_items)
        repeated_ids = list(reflection.repeated)
        semantic_candidates = []
        confidence_updates = []
        questions = []
        goal_candidates = []

        if success and repeated_ids:
            semantic_candidates.append(
                SemanticCandidate(
                    text=(
                        "Repeated attended context appears relevant to the "
                        f"prompt: {prompt}"
                    ),
                    evidence_memory_ids=repeated_ids[:5],
                    confidence=min(0.85, 0.45 + (0.08 * len(repeated_ids))),
                    rationale="Repeated attended memories overlapped with the current task.",
                )
            )

        for item in attended:
            if item.factors.get("task_relevance", 0.0) > 0.0:
                confidence_updates.append(
                    ConfidenceUpdate(
                        target_id=item.item_id,
                        delta=0.03,
                        reason="Memory was attended during a successful cycle.",
                    )
                )

        if not attended:
            questions.append(f"What prior knowledge would help answer: {prompt}")
            goal_candidates.append(f"Acquire context for: {prompt}")

        if not success:
            questions.append(f"Why did this cycle fail: {prompt}")
            goal_candidates.append(f"Resolve failed cycle for: {prompt}")

        for conflict in reflection.conflicts:
            questions.append(f"Resolve conflict: {conflict}")
            goal_candidates.append(f"Investigate contradiction: {conflict}")

        return LearningRecord(
            learning_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            cycle_id=cycle_id,
            semantic_candidates=semantic_candidates,
            confidence_updates=confidence_updates,
            questions=questions,
            goal_candidates=goal_candidates,
            consolidation_candidates=list(reflection.consolidation_candidates),
            metadata={
                "success": bool(success),
                "attended_count": len(attended),
                "prompt_length": len(prompt),
                "output_length": len(str(output)),
            },
        )
