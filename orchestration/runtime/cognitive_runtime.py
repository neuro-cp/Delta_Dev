from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge import (
    ContradictionEngine,
    PredictionEngine,
    SemanticConsolidationEngine,
    SemanticKnowledgeStore,
)
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.agency import AgencyRegion, GoalStore
from orchestration.cycle import CognitiveCycle
from orchestration.loop.cognitive_loop import CognitiveLoop
from orchestration.self_model import SelfModelRegion
from orchestration.simulation import SimulationRegion


@dataclass(frozen=True)
class RuntimeTickResult:
    tick_id: str
    created_at: str
    prompt: str
    cycle_id: str
    consolidation: dict[str, int]
    agency: dict[str, Any]
    self_model: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class CognitiveRuntime:
    """
    Bounded runtime scheduler for Delta.

    This is not a daemon. It executes explicit ticks for a fixed count or
    duration and records inspectable runtime events.
    """

    def __init__(
        self,
        *,
        loop: CognitiveLoop,
        memory_store: MemoryStore,
        relationship_store: RelationshipStore,
        learning_store: LearningStore,
        semantic_store: SemanticKnowledgeStore,
        contradiction_engine: ContradictionEngine,
        prediction_engine: PredictionEngine,
        goal_store: GoalStore,
        event_path: str | Path,
    ) -> None:
        self._loop = loop
        self._memory_store = memory_store
        self._relationship_store = relationship_store
        self._learning_store = learning_store
        self._semantic_store = semantic_store
        self._contradiction_engine = contradiction_engine
        self._prediction_engine = prediction_engine
        self._goal_store = goal_store
        self._event_path = Path(event_path)

    def run(
        self,
        *,
        duration_seconds: int,
        interval_seconds: int = 30,
        max_ticks: int | None = None,
    ) -> list[RuntimeTickResult]:
        duration = max(0, int(duration_seconds))
        deadline = time.monotonic() + duration
        results: list[RuntimeTickResult] = []
        tick_index = 0
        while max_ticks is not None or time.monotonic() < deadline:
            if max_ticks is not None and tick_index >= max_ticks:
                break
            if max_ticks is None and time.monotonic() >= deadline:
                break
            tick_index += 1
            results.append(self.tick(tick_index=tick_index))
            if max_ticks is not None and tick_index >= max_ticks:
                break
            remaining = deadline - time.monotonic() if duration else interval_seconds
            if max_ticks is None and remaining <= 0:
                break
            time.sleep(min(max(0, int(interval_seconds)), remaining))
        return results

    def tick(
        self,
        *,
        tick_index: int,
        prompt_override: str | None = None,
        tags: tuple[str, ...] = ("runtime",),
    ) -> RuntimeTickResult:
        self_model = self._self_model().generate()
        active_goals = self._goal_store.active()
        prompt = (
            str(prompt_override).strip()
            if prompt_override is not None and str(prompt_override).strip()
            else self._prompt_for_tick(tick_index=tick_index, self_model=self_model.to_dict())
        )

        cycle = CognitiveCycle(
            loop=self._loop,
            memory_store=self._memory_store,
            relationship_store=self._relationship_store,
            learning_store=self._learning_store,
            semantic_store=self._semantic_store,
            prediction_engine=self._prediction_engine,
        )
        cycle_result = cycle.run(prompt, tags=tags)
        validated_predictions = self._prediction_engine.validate_against_observations(
            self._memory_store.all()[-20:]
        )

        consolidation = SemanticConsolidationEngine(
            semantic_store=self._semantic_store,
            contradiction_engine=self._contradiction_engine,
            prediction_engine=self._prediction_engine,
        ).consolidate(self._learning_store.all()[-3:])

        simulation = SimulationRegion().simulate(
            options=[f"pursue goal: {goal.description}" for goal in active_goals[:3]]
            or [f"investigate: {item['summary']}" for item in self_model.self_observations[:3]],
            semantic_knowledge=self._semantic_store.latest(),
            relationships=self._relationship_store.all(),
            predictions=self._prediction_engine.all(),
            goals=[goal.description for goal in active_goals],
        )
        agency = AgencyRegion().propose(
            goals=active_goals,
            simulation=simulation,
            self_model=self_model.to_dict(),
        )

        result = RuntimeTickResult(
            tick_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            prompt=prompt,
            cycle_id=cycle_result.cycle_id,
            consolidation={
                "semantic_created": len(consolidation["created"]),
                "contradictions_detected": len(consolidation["contradictions"]),
                "predictions_generated": len(consolidation["predictions"]),
                "predictions_validated": len(validated_predictions),
            },
            agency=agency.to_dict(),
            self_model={
                "experience_count": self_model.metrics["experience_count"],
                "semantic_knowledge_count": self_model.metrics["semantic_knowledge_count"],
                "learning_record_count": self_model.metrics["learning_record_count"],
                "warnings": list(self_model.cognitive_health.get("warnings", [])),
            },
            metadata={"tick_index": tick_index, "non_daemon": True},
        )
        self._append_event(result)
        return result

    def _self_model(self) -> SelfModelRegion:
        return SelfModelRegion(
            memory_store=self._memory_store,
            relationship_store=self._relationship_store,
            learning_store=self._learning_store,
            semantic_store=self._semantic_store,
            contradiction_engine=self._contradiction_engine,
            prediction_engine=self._prediction_engine,
        )

    @staticmethod
    def _prompt_for_tick(*, tick_index: int, self_model: dict[str, Any]) -> str:
        warnings = ", ".join(self_model.get("cognitive_health", {}).get("warnings", []))
        if warnings:
            return f"Runtime tick {tick_index}: reflect on cognitive health warning: {warnings}"
        return f"Runtime tick {tick_index}: review current goals, knowledge, and prediction gaps."

    def _append_event(self, result: RuntimeTickResult) -> None:
        self._event_path.parent.mkdir(parents=True, exist_ok=True)
        with self._event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(result), sort_keys=True) + "\n")
