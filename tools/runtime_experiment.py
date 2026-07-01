from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from knowledge import (
    ContradictionEngine,
    PredictionEngine,
    SemanticKnowledgeStore,
)
from knowledge.bootstrap import KnowledgeBootstrapper
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.agency import GoalStore
from orchestration.curriculum import CurriculumEngine
from orchestration.loop.cognitive_loop import CognitiveLoop
from orchestration.runtime import CognitiveRuntime
from orchestration.self_model import SelfModelRegion


class MockRouter:
    def route(self, payload):
        return AIOutputBundle(
            role="assistant",
            mode="mock",
            payload={"raw_model_output": '{"answer": "runtime ok", "confidence": 0.7}'},
            confidence_band=0.7,
        )


def _jsonable(value):
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


SUPPORTED_EXPERIMENT_TICKS = (1000, 5000, 10000, 25000, 100000)


def run_experiment(
    *,
    ticks: int,
    store_root: Path,
    experiment_kind: str = "runtime",
    curriculum_domains: tuple[str, ...] = (),
) -> dict:
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    learning = LearningStore(store_root / "learning.jsonl")
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    contradictions = ContradictionEngine(store_root / "contradictions.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    goals = GoalStore(store_root / "goals.jsonl")

    bootstrap = KnowledgeBootstrapper(
        semantic_store=knowledge,
        memory_store=memory,
        goal_store=goals,
        prediction_engine=predictions,
    ).seed()

    runtime = CognitiveRuntime(
        loop=CognitiveLoop(
            model_router=MockRouter(),
            enable_recall=False,
            enable_replay_prompt=False,
        ),
        memory_store=memory,
        relationship_store=relationships,
        learning_store=learning,
        semantic_store=knowledge,
        contradiction_engine=contradictions,
        prediction_engine=predictions,
        goal_store=goals,
        event_path=store_root / "events.jsonl",
    )

    curriculum_cases = []
    if experiment_kind == "curriculum":
        curriculum_cases = CurriculumEngine().generate_sequence(
            count=ticks,
            domains=curriculum_domains or CurriculumEngine.DOMAINS,
        )

    started = time.perf_counter()
    results = []
    for index in range(1, ticks + 1):
        curriculum_case = (
            curriculum_cases[(index - 1) % len(curriculum_cases)]
            if curriculum_cases
            else None
        )
        with contextlib.redirect_stdout(io.StringIO()):
            results.append(
                runtime.tick(
                    tick_index=index,
                    prompt_override=curriculum_case.prompt if curriculum_case else None,
                    tags=(
                        ("runtime", "experiment", experiment_kind, curriculum_case.domain)
                        if curriculum_case
                        else ("runtime", "experiment", experiment_kind)
                    ),
                )
            )
    elapsed = time.perf_counter() - started

    snapshot = SelfModelRegion(
        memory_store=memory,
        relationship_store=relationships,
        learning_store=learning,
        semantic_store=knowledge,
        contradiction_engine=contradictions,
        prediction_engine=predictions,
    ).generate()

    return {
        "ticks_requested": ticks,
        "ticks_completed": len(results),
        "experiment_kind": experiment_kind,
        "supported_large_tick_targets": list(SUPPORTED_EXPERIMENT_TICKS),
        "large_tick_target": ticks in SUPPORTED_EXPERIMENT_TICKS,
        "elapsed_seconds": round(elapsed, 4),
        "ticks_per_second": round(len(results) / elapsed, 4) if elapsed else None,
        "store_root": str(store_root),
        "bootstrap": {
            "semantic_created": len(bootstrap["semantic_created"]),
            "predictions_created": len(bootstrap["predictions_created"]),
            "goals_created": len(bootstrap["goals_created"]),
        },
        "last_tick": _jsonable(results[-1]) if results else None,
        "self_model": snapshot.to_dict(),
        "prediction_quality": predictions.quality_metrics(),
        "curriculum": _curriculum_summary(curriculum_cases),
        "counts": {
            "memories": len(memory.all()),
            "relationships": len(relationships.latest()),
            "learning": len(learning.all()),
            "semantic_knowledge": len(knowledge.latest()),
            "contradictions": len(contradictions.latest()),
            "predictions": len(predictions.latest()),
            "goals": len(goals.active()),
        },
    }


def _curriculum_summary(cases) -> dict:
    if not cases:
        return {"enabled": False}
    domains: dict[str, int] = {}
    difficulties: dict[int, int] = {}
    capabilities: dict[str, int] = {}
    for case in cases:
        domains[case.domain] = domains.get(case.domain, 0) + 1
        difficulties[case.difficulty] = difficulties.get(case.difficulty, 0) + 1
        for capability in case.required_capabilities:
            capabilities[capability] = capabilities.get(capability, 0) + 1
    return {
        "enabled": True,
        "case_count": len(cases),
        "domains": dict(sorted(domains.items())),
        "difficulties": {str(key): value for key, value in sorted(difficulties.items())},
        "required_capabilities": dict(sorted(capabilities.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded Delta runtime experiment.")
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--summary-path")
    parser.add_argument(
        "--experiment-kind",
        choices=("runtime", "curriculum", "planning", "research", "software", "scientific"),
        default="runtime",
    )
    parser.add_argument("--curriculum-domain", action="append", default=[])
    args = parser.parse_args()

    summary = run_experiment(
        ticks=max(0, int(args.ticks)),
        store_root=Path(args.store_root),
        experiment_kind=args.experiment_kind,
        curriculum_domains=tuple(args.curriculum_domain),
    )
    payload = json.dumps(summary, indent=2, sort_keys=True)
    if args.summary_path:
        path = Path(args.summary_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
