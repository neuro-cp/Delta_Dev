from __future__ import annotations

import uuid
from typing import Iterable, List

from learning.region import LearningEngine, LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.attention import AttentionService
from orchestration.cycle.cycle_result import CognitiveCycleResult, CycleStageRecord
from orchestration.loop.cognitive_loop import CognitiveLoop
from orchestration.reflection import ReflectionEngine


class CognitiveCycle:
    """
    First explicit Delta cognitive cycle.

    Current implemented stages:
    - observe
    - interpret/reason through the orchestration loop
    - store raw experience
    - record placeholders for relationship, consolidation, goals, attention,
      action, and reflection

    This creates a persistent organism-level loop without claiming that the
    later cognitive regions are complete.
    """

    def __init__(
        self,
        *,
        loop: CognitiveLoop,
        memory_store: MemoryStore,
        relationship_store: RelationshipStore | None = None,
        learning_store: LearningStore | None = None,
        attention_service: AttentionService | None = None,
        reflection_engine: ReflectionEngine | None = None,
        learning_engine: LearningEngine | None = None,
    ) -> None:
        self._loop = loop
        self._memory_store = memory_store
        self._relationship_store = relationship_store
        self._learning_store = learning_store
        self._attention = attention_service or AttentionService()
        self._reflection = reflection_engine or ReflectionEngine()
        self._learning = learning_engine or LearningEngine()

    def run(self, prompt: str, *, tags: Iterable[str] = ()) -> CognitiveCycleResult:
        normalized_prompt = str(prompt).strip()
        if not normalized_prompt:
            raise ValueError("cycle prompt cannot be empty")

        cycle_id = str(uuid.uuid4())
        stages: List[CycleStageRecord] = []
        memory_ids: List[str] = []
        relationship_ids: List[str] = []
        learning_ids: List[str] = []

        stages.append(
            CycleStageRecord(
                stage="observe",
                summary="Captured operator text input.",
                metadata={"input_length": len(normalized_prompt)},
            )
        )

        observation = self._memory_store.add(
            text=normalized_prompt,
            kind="observation",
            source="operator",
            layer="experience",
            tags=("cycle", "observation", *tuple(tags)),
            metadata={"cycle_id": cycle_id},
        )
        memory_ids.append(observation.memory_id)

        recalled = self._memory_store.recall(normalized_prompt, limit=8)
        attended = self._attention.rank_memory(
            current_task=normalized_prompt,
            memories=recalled,
            limit=5,
        )
        stages.append(
            CycleStageRecord(
                stage="attend",
                summary="Ranked recalled memories for current task relevance.",
                metadata={
                    "candidate_count": len(recalled),
                    "attended_count": len(attended),
                    "top_items": [
                        {
                            "item_id": item.item_id,
                            "score": item.score,
                            "source": item.source,
                        }
                        for item in attended
                    ],
                },
            )
        )

        attended_context = [
            {
                "memory_id": item.item_id,
                "source": item.source,
                "text": item.text,
                "score": item.score,
                "factors": dict(item.factors),
                "metadata": dict(item.metadata),
            }
            for item in attended
        ]

        result = self._loop.run(
            {
                "question": normalized_prompt,
                "cycle_id": cycle_id,
                "attended_context": attended_context,
            }
        )
        execution = result["result"]
        task_type = result["task_type"]

        stages.append(
            CycleStageRecord(
                stage="interpret_reason",
                summary="Ran prompt through orchestration with attended context as advisory metadata.",
                metadata={
                    "task_type": task_type.value,
                    "route_type": execution.route_type,
                    "success": execution.success,
                    "confidence": execution.confidence,
                    "attended_context_count": len(attended_context),
                },
            )
        )

        if execution.success:
            output_record = self._memory_store.add(
                text=str(execution.output),
                kind="orchestration_output",
                source=f"delta:{execution.route_type}",
                layer="experience",
                confidence=float(execution.confidence),
                tags=("cycle", "output", execution.route_type, *tuple(tags)),
                metadata={
                    "cycle_id": cycle_id,
                    "prompt_memory_id": observation.memory_id,
                    "prompt": normalized_prompt,
                },
            )
            memory_ids.append(output_record.memory_id)

            if self._relationship_store is not None:
                relationship = self._relationship_store.add(
                    source_id=observation.memory_id,
                    target_id=output_record.memory_id,
                    relationship_type="temporal_sequence",
                    confidence=float(execution.confidence),
                    evidence="Cycle output followed cycle observation.",
                    metadata={"cycle_id": cycle_id},
                )
                relationship_ids.append(relationship.relationship_id)

        stages.extend(
            [
                CycleStageRecord(
                    stage="form_relationships",
                    summary="Recorded direct temporal relationship for this cycle.",
                    metadata={
                        "relationship_count": len(relationship_ids),
                        "relationship_ids": list(relationship_ids),
                    },
                ),
                CycleStageRecord(
                    stage="plan",
                    summary="Deferred: planning region is not yet implemented.",
                    metadata={"status": "pending"},
                ),
                CycleStageRecord(
                    stage="act",
                    summary="Current action is limited to returning the orchestration result.",
                    metadata={"status": "bounded"},
                ),
                CycleStageRecord(
                    stage="evaluate",
                    summary="Evaluated execution success and confidence.",
                    metadata={
                        "success": bool(execution.success),
                        "confidence": float(execution.confidence),
                    },
                ),
            ]
        )

        reflection = self._reflection.reflect(
            prompt=normalized_prompt,
            output=str(execution.output),
            success=bool(execution.success),
            attended_items=attended,
            memory_ids=memory_ids,
        )
        stages.append(
            CycleStageRecord(
                stage="reflect",
                summary="Generated structured reflection for this cycle.",
                metadata={
                    "learned": reflection.learned,
                    "repeated": reflection.repeated,
                    "surprises": reflection.surprises,
                    "conflicts": reflection.conflicts,
                    "consolidation_candidates": reflection.consolidation_candidates,
                    "reflection_metadata": reflection.metadata,
                },
            )
        )

        learning_record = self._learning.learn(
            cycle_id=cycle_id,
            prompt=normalized_prompt,
            output=str(execution.output),
            success=bool(execution.success),
            attended_items=attended,
            reflection=reflection,
        )
        if self._learning_store is not None:
            self._learning_store.add(learning_record)
        learning_ids.append(learning_record.learning_id)
        stages.append(
            CycleStageRecord(
                stage="learn",
                summary="Generated structured non-authoritative learning output.",
                metadata={
                    "learning_id": learning_record.learning_id,
                    "semantic_candidate_count": len(
                        learning_record.semantic_candidates
                    ),
                    "confidence_update_count": len(
                        learning_record.confidence_updates
                    ),
                    "question_count": len(learning_record.questions),
                    "goal_candidate_count": len(learning_record.goal_candidates),
                    "stored": self._learning_store is not None,
                },
            )
        )
        stages.extend(
            [
                CycleStageRecord(
                    stage="consolidate_knowledge",
                    summary="Deferred: semantic consolidation is not yet implemented.",
                    metadata={
                        "status": "pending",
                        "learning_id": learning_record.learning_id,
                    },
                ),
                CycleStageRecord(
                    stage="update_goals",
                    summary="Deferred: goal state is not yet implemented.",
                    metadata={
                        "status": "pending",
                        "goal_candidate_count": len(learning_record.goal_candidates),
                    },
                ),
            ]
        )

        return CognitiveCycleResult(
            cycle_id=cycle_id,
            prompt=normalized_prompt,
            output=execution.output,
            route_type=execution.route_type,
            success=bool(execution.success),
            confidence=float(execution.confidence),
            memory_ids=memory_ids,
            relationship_ids=relationship_ids,
            learning_ids=learning_ids,
            stages=stages,
        )
