from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from integration.model_runtime import ProviderManager
from knowledge import ContradictionEngine, PredictionEngine, SemanticKnowledgeStore
from knowledge.bootstrap import KnowledgeBootstrapper
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.agency import GoalStore
from orchestration.curriculum import CalibrationCurriculumGenerator
from orchestration.loop.cognitive_loop import CognitiveLoop
from orchestration.runtime import CognitiveRuntime
from orchestration.self_model import SelfModelRegion


CAPABILITY_PROVIDER_HINTS = {
    "prediction": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "planning": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "cross_domain": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "contradiction": "mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m",
    "transfer": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
}


class LocalProviderRouter:
    def __init__(self, *, manager: ProviderManager, default_model: str) -> None:
        self.manager = manager
        self.default_model = default_model

    def route(self, payload: dict[str, Any]) -> AIOutputBundle:
        question = str(payload.get("question") or "").strip()
        metadata = dict(payload.get("metadata") or {})
        model_name = metadata.get("provider_model") or self._model_for_question(question)
        inference = self.manager.infer(
            model_name=str(model_name),
            prompt=question,
            task_type=str(metadata.get("task_type") or "training"),
            metadata=metadata,
        )
        raw = json.dumps(
            {
                "answer": inference.answer,
                "confidence": inference.confidence,
            },
            ensure_ascii=True,
        )
        return AIOutputBundle(
            role="assistant",
            mode="local_gguf",
            payload={
                "raw_model_output": raw,
                "answer": inference.answer,
                "canonical_inference": asdict(inference),
            },
            confidence_band=inference.confidence,
        )

    def _model_for_question(self, question: str) -> str:
        text = question.lower()
        if "contradiction" in text or "conflict" in text or "provenance" in text:
            return CAPABILITY_PROVIDER_HINTS["contradiction"]
        if "transfer" in text or "triage" in text:
            return CAPABILITY_PROVIDER_HINTS["transfer"]
        if "predict" in text or "prediction" in text or "falsify" in text:
            return CAPABILITY_PROVIDER_HINTS["prediction"]
        if "plan" in text or "staffing" in text:
            return CAPABILITY_PROVIDER_HINTS["planning"]
        return self.default_model


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _counts(
    *,
    memory: MemoryStore,
    relationships: RelationshipStore,
    learning: LearningStore,
    knowledge: SemanticKnowledgeStore,
    contradictions: ContradictionEngine,
    predictions: PredictionEngine,
    goals: GoalStore,
) -> dict[str, int]:
    return {
        "memories": len(memory.all()),
        "relationships": len(relationships.latest()),
        "learning": len(learning.all()),
        "semantic_knowledge": len(knowledge.latest()),
        "contradictions": len(contradictions.latest()),
        "predictions": len(predictions.latest()),
        "goals": len(goals.active()),
    }


def run_training(
    *,
    cycles: int,
    store_root: Path,
    objective_count: int,
    default_model: str,
) -> dict[str, Any]:
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
    baseline_counts = _counts(
        memory=memory,
        relationships=relationships,
        learning=learning,
        knowledge=knowledge,
        contradictions=contradictions,
        predictions=predictions,
        goals=goals,
    )
    baseline_prediction_quality = predictions.quality_metrics()

    manager = ProviderManager(
        status_path=ROOT / "data" / "model_runtime" / "provider_status.json",
        capability_db_path=ROOT / "data" / "model_runtime" / "provider_capabilities.json",
    )
    router = LocalProviderRouter(manager=manager, default_model=default_model)
    runtime = CognitiveRuntime(
        loop=CognitiveLoop(
            model_router=router,
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

    objectives = CalibrationCurriculumGenerator().generate(
        count=max(1, int(objective_count)),
        min_utility=0.4,
    )
    if not objectives:
        raise RuntimeError("No calibration objectives were generated.")

    started = time.perf_counter()
    cycle_summaries = []
    for index in range(1, max(0, int(cycles)) + 1):
        scored = objectives[(index - 1) % len(objectives)]
        objective = scored.objective
        provider_model = CAPABILITY_PROVIDER_HINTS.get(objective.capability, default_model)
        prompt = (
            f"{objective.prompt}\n\n"
            "Complete the cycle as Delta training data: answer, make at least one "
            "testable prediction when possible, identify evidence that would change "
            "the answer, and reflect on uncertainty."
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = runtime.tick(
                tick_index=index,
                prompt_override=prompt,
                tags=(
                    "training",
                    "governed",
                    "calibration",
                    objective.capability,
                    objective.objective_id,
                    provider_model,
                ),
            )
        cycle_summaries.append(
            {
                "tick": index,
                "objective_id": objective.objective_id,
                "capability": objective.capability,
                "provider_model": provider_model,
                "consolidation": result.consolidation,
                "self_model": result.self_model,
            }
        )
    manager.unload()
    elapsed = time.perf_counter() - started

    final_counts = _counts(
        memory=memory,
        relationships=relationships,
        learning=learning,
        knowledge=knowledge,
        contradictions=contradictions,
        predictions=predictions,
        goals=goals,
    )
    self_model = SelfModelRegion(
        memory_store=memory,
        relationship_store=relationships,
        learning_store=learning,
        semantic_store=knowledge,
        contradiction_engine=contradictions,
        prediction_engine=predictions,
    ).generate()
    return {
        "run_id": f"governed_training_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "cycles_requested": cycles,
        "cycles_completed": len(cycle_summaries),
        "elapsed_seconds": round(elapsed, 4),
        "cycles_per_second": round(len(cycle_summaries) / elapsed, 4) if elapsed else None,
        "store_root": str(store_root),
        "bootstrap": {
            "semantic_created": len(bootstrap["semantic_created"]),
            "predictions_created": len(bootstrap["predictions_created"]),
            "goals_created": len(bootstrap["goals_created"]),
        },
        "baseline_counts": baseline_counts,
        "final_counts": final_counts,
        "count_delta": {
            key: final_counts.get(key, 0) - baseline_counts.get(key, 0)
            for key in sorted(set(baseline_counts) | set(final_counts))
        },
        "baseline_prediction_quality": baseline_prediction_quality,
        "final_prediction_quality": predictions.quality_metrics(),
        "self_model": self_model.to_dict(),
        "objectives": [
            {
                "objective_id": item.objective.objective_id,
                "capability": item.objective.capability,
                "calibration_score": item.calibration_score,
                "utility": item.novelty_report.experience_utility_score,
                "surprise": item.novelty_report.surprise_score,
            }
            for item in objectives
        ],
        "provider_hints": dict(CAPABILITY_PROVIDER_HINTS),
        "cycle_summaries": cycle_summaries[-10:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run governed local-provider Delta training cycles.")
    parser.add_argument("--cycles", type=int, required=True)
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--summary-path", required=True)
    parser.add_argument("--objective-count", type=int, default=8)
    parser.add_argument(
        "--default-model",
        default="qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    )
    args = parser.parse_args()

    summary = run_training(
        cycles=args.cycles,
        store_root=Path(args.store_root),
        objective_count=args.objective_count,
        default_model=args.default_model,
    )
    payload = json.dumps(_jsonable(summary), indent=2, sort_keys=True)
    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
