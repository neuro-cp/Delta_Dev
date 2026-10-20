"""Reproducible mock-runtime experiments; never use the operator's live stores."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import platform
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge import ContradictionEngine, PredictionEngine, SemanticKnowledgeStore
from knowledge.bootstrap import KnowledgeBootstrapper
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.agency import GoalStore
from orchestration.runtime import CognitiveRuntime
from orchestration.self_model import SelfModelRegion
from tools.delta_cli import build_loop


def run_experiment(root: Path, ticks: int) -> dict:
    if ticks < 1:
        raise ValueError("ticks must be positive")
    root.mkdir(parents=True, exist_ok=False)
    memory = MemoryStore(root / "memory.jsonl")
    knowledge = SemanticKnowledgeStore(root / "knowledge.jsonl")
    predictions = PredictionEngine(root / "predictions.jsonl")
    relationships = RelationshipStore(root / "relationships.jsonl")
    learning = LearningStore(root / "learning.jsonl")
    contradictions = ContradictionEngine(root / "contradictions.jsonl")
    goals = GoalStore(root / "goals.jsonl")
    bootstrap = KnowledgeBootstrapper(
        semantic_store=knowledge, memory_store=memory,
        prediction_engine=predictions, goal_store=goals,
    )
    seed = bootstrap.seed()
    second_seed = bootstrap.seed()
    runtime = CognitiveRuntime(
        loop=build_loop("mock", enable_recall=False, enable_replay_prompt=False),
        memory_store=memory, semantic_store=knowledge,
        prediction_engine=predictions, relationship_store=relationships,
        learning_store=learning, contradiction_engine=contradictions,
        goal_store=goals, event_path=root / "events.jsonl",
    )
    timeline = []
    started = time.perf_counter()
    cpu_started = time.process_time()
    for index in range(1, ticks + 1):
        tick_started = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            result = runtime.tick(tick_index=index)
        elapsed = time.perf_counter() - tick_started
        semantic_records = knowledge.latest()
        prediction_records = predictions.latest()
        timeline.append({
            "tick": index,
            "seconds": round(elapsed, 6),
            "memories": len(memory.all()),
            "semantic": len(semantic_records),
            "semantic_history": len(knowledge.all()),
            "predictions": len(prediction_records),
            "prediction_history": len(predictions.all()),
            "prediction_statuses": dict(Counter(p.status for p in prediction_records)),
            "contradictions": len(contradictions.all()),
            "relationships": len(relationships.all()),
            "learning": len(learning.all()),
            "goals": len(goals.latest()),
            "event_memories": result.self_model["experience_count"],
            "execution_authority": result.agency["metadata"]["execution_authority"],
        })
    wall_seconds = time.perf_counter() - started
    cpu_seconds = time.process_time() - cpu_started
    records = knowledge.latest()
    durations = sorted(item["seconds"] for item in timeline)
    memory_ids = {item.memory_id for item in memory.all()}
    snapshot = SelfModelRegion(
        memory_store=memory, relationship_store=relationships, learning_store=learning,
        semantic_store=knowledge, contradiction_engine=contradictions, prediction_engine=predictions,
    ).generate()
    checks = {
        "no_internal_knowledge_promotion": len(knowledge.all()) == len(seed["semantic_created"]),
        "no_self_validated_predictions": all(p.status == "open" for p in predictions.latest()),
        "no_internal_contradictions": not contradictions.all(),
        "post_tick_counts_match": all(t["memories"] == t["event_memories"] for t in timeline),
        "bounded_agency": all(t["execution_authority"] is False for t in timeline),
        "expected_experience_growth": len(memory_ids) == len(seed["semantic_created"]) + 2 * ticks,
        "no_duplicate_bootstrap": not any(second_seed.values()),
    }
    summary = {
        "ticks": ticks,
        "seed_concepts": len(seed["semantic_created"]),
        "bootstrap_idempotent": not any(second_seed.values()),
        "wall_seconds": round(wall_seconds, 4),
        "cpu_seconds": round(cpu_seconds, 4),
        "tick_mean_seconds": round(sum(durations) / ticks, 6),
        "tick_p95_seconds": durations[math.ceil(ticks * .95) - 1],
        "final": timeline[-1],
        "event_counts_match": all(t["memories"] == t["event_memories"] for t in timeline),
        "execution_bounded": all(t["execution_authority"] is False for t in timeline),
        "provenance_complete": all(
            r.creation_source and r.supporting_evidence
            and set(r.supporting_evidence) <= memory_ids for r in records
        ),
        "store_bytes": sum(path.stat().st_size for path in root.glob("*.jsonl")),
        "semantic_confidence": [r.confidence for r in records],
        "prediction_confidence": [r.confidence for r in predictions.latest()],
        "prediction_accuracy": snapshot.metrics["prediction_accuracy"],
        "checks": checks,
        "limitations": [
            "Mock reasoning, internal prompts only; no external outcomes or factual learning measured.",
            "Wall time includes instrumentation; store bytes are disk size, not process RAM.",
            "Region timings, predictive competence and real-model quality are not measured.",
        ],
    }
    (root / "result.json").write_text(
        json.dumps({"summary": summary, "timeline": timeline}, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New experiment directory.")
    parser.add_argument("--ticks", type=int, nargs="+", default=[10, 25, 50, 100])
    args = parser.parse_args()
    if any(count < 1 for count in args.ticks) or len(set(args.ticks)) != len(args.ticks):
        parser.error("tick counts must be positive and unique")
    args.output.mkdir(parents=True, exist_ok=False)
    summaries = []
    for count in args.ticks:
        summary = run_experiment(args.output / str(count), count)
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    (args.output / "summary.json").write_text(json.dumps({
        "python": platform.python_version(), "model": "mock", "experiments": summaries,
    }, indent=2), encoding="utf-8")
    return 0 if all(all(s["checks"].values()) for s in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
