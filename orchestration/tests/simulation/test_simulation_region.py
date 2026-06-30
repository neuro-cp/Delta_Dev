from __future__ import annotations

from datetime import datetime, timezone

from knowledge.prediction_record import PredictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord
from memory.working_memory import WorkingMemoryContext, WorkingMemoryContextItem
from orchestration.simulation import SimulationRegion


def test_simulation_region_compares_multiple_non_executing_futures():
    now = datetime.now(timezone.utc).isoformat()
    working_memory = WorkingMemoryContext(
        cycle_id="cycle-1",
        items=[
            WorkingMemoryContextItem(
                key="obs",
                kind="observation",
                source="operator",
                text="Evaluate knowledge consolidation.",
                priority=1.0,
            )
        ],
    )
    knowledge = [
        SemanticKnowledgeRecord(
            concept_id="k1",
            created_at=now,
            updated_at=now,
            concept="knowledge consolidation",
            definition="Consolidation can turn learning records into semantic knowledge.",
            confidence=0.8,
        )
    ]
    predictions = [
        PredictionRecord(
            prediction_id="p1",
            created_at=now,
            source_concept_id="k1",
            expectation="If knowledge consolidation is run, expect semantic knowledge growth.",
            confidence=0.7,
        )
    ]

    report = SimulationRegion().simulate(
        options=[
            "run knowledge consolidation",
            "skip knowledge consolidation",
        ],
        working_memory=working_memory,
        semantic_knowledge=knowledge,
        predictions=predictions,
        goals=("increase semantic knowledge",),
    )

    assert report.cycle_id == "cycle-1"
    assert report.metadata["non_executing"] is True
    assert len(report.outcomes) == 2
    assert report.outcomes[0].supporting_prediction_ids == ["p1"]
    assert report.outcomes[0].confidence >= report.outcomes[1].confidence
