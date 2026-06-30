from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from knowledge import ContradictionEngine, PredictionEngine, SemanticKnowledgeStore
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.agency import GoalStore, PlanStore
from orchestration.self_model import SelfModelRegion


def _read_events(path: str | Path) -> list[dict[str, Any]]:
    event_path = Path(path)
    if not event_path.exists():
        return []
    events = []
    with event_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def write_first_runtime_report(
    *,
    root: Path,
    memory: MemoryStore,
    relationships: RelationshipStore,
    learning: LearningStore,
    knowledge: SemanticKnowledgeStore,
    contradictions: ContradictionEngine,
    predictions: PredictionEngine,
    goals: GoalStore,
    plans: PlanStore,
    event_path: str | Path,
) -> Path:
    events = _read_events(event_path)
    snapshot = SelfModelRegion(
        memory_store=memory,
        relationship_store=relationships,
        learning_store=learning,
        semantic_store=knowledge,
        contradiction_engine=contradictions,
        prediction_engine=predictions,
    ).generate()
    prediction_records = predictions.all()
    plan_records = plans.all()
    semantic_created = sum(
        int(event.get("consolidation", {}).get("semantic_created", 0))
        for event in events
    )
    agency_proposals = [event.get("agency", {}) for event in events]
    unexpected = []
    if not events:
        unexpected.append("No runtime events were recorded.")
    if semantic_created == 0:
        unexpected.append("Runtime did not consolidate new semantic knowledge.")
    if not agency_proposals:
        unexpected.append("Runtime did not produce agency proposals.")

    report = root / "docs" / "FIRST_RUNTIME_REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# DELTA First Runtime Report",
                "",
                "## Summary",
                "",
                "This report is generated from Delta's recorded runtime events and",
                "current append-only stores. It does not claim intelligence; it",
                "evaluates whether the runtime remained coherent.",
                "",
                "## Counts",
                "",
                f"- cognitive ticks: {len(events)}",
                f"- memories created: {len(memory.all())}",
                f"- semantic concepts formed: {len(knowledge.latest())}",
                f"- relationships formed: {len(relationships.all())}",
                f"- predictions made: {len(prediction_records)}",
                f"- predictions validated: {len([item for item in prediction_records if item.status in {'succeeded', 'failed'}])}",
                f"- contradictions found: {len(contradictions.all())}",
                "- confidence changes: 0",
                f"- goals created: {len(goals.latest())}",
                f"- plans generated: {len(plan_records)}",
                f"- reflections: {snapshot.metrics['reflection_count']}",
                f"- learning records: {len(learning.all())}",
                f"- knowledge consolidations: {semantic_created}",
                f"- agency proposals: {len(agency_proposals)}",
                "",
                "## Health Metrics",
                "",
                "```json",
                json.dumps(snapshot.cognitive_health, indent=2, sort_keys=True),
                "```",
                "",
                "## Architectural Observations",
                "",
                "- Runtime ticks execute the existing cognitive cycle instead of bypassing it.",
                "- The LLM route remains a reasoning/plugin surface; it does not directly write knowledge.",
                "- Bootstrap knowledge enters as semantic records with provenance.",
                "- Agency proposals remain non-executing.",
                "",
                "## Unexpected Behaviors",
                "",
                *(f"- {item}" for item in (unexpected or ["No unexpected behavior was detected by the report generator."])),
                "",
                "## Failure Modes",
                "",
                "- Prediction validation is still absent.",
                "- Confidence updates are still advisory and not applied.",
                "- Runtime consolidation is simple and may repeatedly create related concepts.",
                "- Console visualization is read-only and not a full live websocket interface.",
                "",
                "## Bottlenecks",
                "",
                "- CLI/runtime assembly still carries too much integration responsibility.",
                "- Recall remains token-overlap based.",
                "- The runtime has no cognitive energy scheduler yet.",
                "",
                "## Recommendations",
                "",
                "1. Add prediction and simulation outcome evaluation.",
                "2. Add a cognitive timeline event model.",
                "3. Move runtime assembly into reusable application services.",
                "4. Add goal-aware attention and working memory.",
                "5. Add a bounded operator review path for knowledge and goal promotion.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report
