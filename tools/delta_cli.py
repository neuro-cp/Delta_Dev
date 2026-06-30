from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from integration.model_runtime.model_registry import list_available_models
from integration.model_runtime.model_router import ModelRouter
from knowledge import (
    ContradictionEngine,
    PredictionEngine,
    SemanticConsolidationEngine,
    SemanticKnowledgeStore,
)
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.cycle import CognitiveCycle
from orchestration.loop.cognitive_loop import CognitiveLoop


class MockModelRouter:
    """
    Developer-only model plugin.

    This gives the orchestration path a runnable LLM-like surface without
    requiring local GGUF models.
    """

    def route(self, payload: Dict[str, Any]) -> AIOutputBundle:
        question = str(payload.get("question", "")).strip()
        answer = (
            "Mock model response: "
            + (question if question else "no question supplied")
        )
        return AIOutputBundle(
            role="assistant",
            mode="mock",
            payload={
                "raw_model_output": json.dumps({
                    "answer": answer,
                    "confidence": 0.7,
                })
            },
            confidence_band=0.7,
        )


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "value"):
        return value.value
    return value


def build_loop(
    model_mode: str,
    *,
    enable_recall: bool,
    enable_replay_prompt: bool,
) -> CognitiveLoop:
    if model_mode == "real":
        return CognitiveLoop(
            model_router=ModelRouter(),
            enable_recall=enable_recall,
            enable_replay_prompt=enable_replay_prompt,
        )
    if model_mode == "mock":
        return CognitiveLoop(
            model_router=MockModelRouter(),
            enable_recall=enable_recall,
            enable_replay_prompt=enable_replay_prompt,
        )
    return CognitiveLoop(
        enable_recall=enable_recall,
        enable_replay_prompt=enable_replay_prompt,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the DELTA orchestration loop from the command line."
    )
    parser.add_argument("prompt", nargs="*", help="Prompt to run through Delta.")
    parser.add_argument(
        "--model",
        choices=("none", "mock", "real"),
        default="mock",
        help="Model plugin mode. Use 'mock' for fast local development.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full orchestration result as JSON.",
    )
    parser.add_argument(
        "--recall",
        action="store_true",
        help="Enable runtime-backed recall bridge construction.",
    )
    parser.add_argument(
        "--replay-prompt",
        action="store_true",
        help="Prompt to enqueue successful answers into replay storage.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List configured local models that are present on disk.",
    )
    parser.add_argument(
        "--memory-path",
        default=str(ROOT / "data" / "memory" / "persistent_memory.jsonl"),
        help="Path to Delta's append-only persistent memory store.",
    )
    parser.add_argument(
        "--relationship-path",
        default=str(ROOT / "data" / "memory" / "relationships.jsonl"),
        help="Path to Delta's append-only relationship store.",
    )
    parser.add_argument(
        "--learning-path",
        default=str(ROOT / "data" / "learning" / "learning_records.jsonl"),
        help="Path to Delta's append-only learning record store.",
    )
    parser.add_argument(
        "--knowledge-path",
        default=str(ROOT / "data" / "knowledge" / "semantic_knowledge.jsonl"),
        help="Path to Delta's append-only semantic knowledge store.",
    )
    parser.add_argument(
        "--contradiction-path",
        default=str(ROOT / "data" / "knowledge" / "contradictions.jsonl"),
        help="Path to Delta's append-only contradiction store.",
    )
    parser.add_argument(
        "--prediction-path",
        default=str(ROOT / "data" / "knowledge" / "predictions.jsonl"),
        help="Path to Delta's append-only prediction store.",
    )
    parser.add_argument(
        "--remember",
        help="Store an explicit memory record and exit.",
    )
    parser.add_argument(
        "--recall-memory",
        help="Recall matching persistent memory records and exit.",
    )
    parser.add_argument(
        "--remember-output",
        action="store_true",
        help="Store the successful orchestration output as persistent memory.",
    )
    parser.add_argument(
        "--list-learning",
        action="store_true",
        help="List stored non-authoritative learning records.",
    )
    parser.add_argument(
        "--consolidate-knowledge",
        action="store_true",
        help="Promote learning semantic candidates into semantic knowledge.",
    )
    parser.add_argument(
        "--list-knowledge",
        action="store_true",
        help="List latest semantic knowledge records.",
    )
    parser.add_argument(
        "--list-predictions",
        action="store_true",
        help="List generated open prediction records.",
    )
    parser.add_argument(
        "--cycle",
        action="store_true",
        help="Run one explicit observe-interpret-store-reflect cognitive cycle.",
    )
    args = parser.parse_args()

    if args.list_models:
        for name, spec in list_available_models().items():
            print(f"{name}: {spec.path}")
        return 0

    memory = MemoryStore(args.memory_path)
    relationships = RelationshipStore(args.relationship_path)
    learning = LearningStore(args.learning_path)
    knowledge = SemanticKnowledgeStore(args.knowledge_path)
    contradictions = ContradictionEngine(args.contradiction_path)
    predictions = PredictionEngine(args.prediction_path)

    if args.remember:
        record = memory.add(
            text=args.remember,
            kind="operator_note",
            source="operator",
            tags=("operator",),
        )
        print(f"remembered: {record.memory_id}")
        return 0

    if args.recall_memory:
        records = memory.recall(args.recall_memory)
        if not records:
            print("no memory matches")
            return 0
        for record in records:
            print(f"{record.memory_id} [{record.kind}] {record.created_at}")
            print(record.text)
            print()
        return 0

    if args.list_learning:
        records = learning.all()
        if not records:
            print("no learning records")
            return 0
        for record in records[-10:]:
            print(f"{record.learning_id} cycle={record.cycle_id}")
            print("semantic_candidates:", len(record.semantic_candidates))
            print("confidence_updates:", len(record.confidence_updates))
            print("questions:", len(record.questions))
            print("goal_candidates:", len(record.goal_candidates))
            print()
        return 0

    if args.consolidate_knowledge:
        engine = SemanticConsolidationEngine(
            semantic_store=knowledge,
            contradiction_engine=contradictions,
            prediction_engine=predictions,
        )
        result = engine.consolidate(learning.all())
        print("semantic_created:", len(result["created"]))
        print("contradictions_detected:", len(result["contradictions"]))
        print("predictions_generated:", len(result["predictions"]))
        return 0

    if args.list_knowledge:
        records = knowledge.latest()
        if not records:
            print("no semantic knowledge")
            return 0
        for record in records[-10:]:
            print(f"{record.concept_id} confidence={record.confidence:.3f}")
            print("concept:", record.concept)
            print("definition:", record.definition)
            print("support:", len(record.supporting_evidence))
            print("contradictions:", len(record.contradicting_evidence))
            print()
        return 0

    if args.list_predictions:
        records = predictions.all()
        if not records:
            print("no predictions")
            return 0
        for record in records[-10:]:
            print(f"{record.prediction_id} confidence={record.confidence:.3f}")
            print("source:", record.source_concept_id)
            print(record.expectation)
            print()
        return 0

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        prompt = input("delta> ").strip()
    if not prompt:
        raise SystemExit("No prompt supplied")

    loop = build_loop(
        args.model,
        enable_recall=args.recall,
        enable_replay_prompt=args.replay_prompt,
    )

    if args.cycle:
        cycle = CognitiveCycle(
            loop=loop,
            memory_store=memory,
            relationship_store=relationships,
            learning_store=learning,
            semantic_store=knowledge,
            prediction_engine=predictions,
        )
        cycle_result = cycle.run(prompt)
        if args.json:
            print(json.dumps(_to_jsonable(cycle_result), indent=2, sort_keys=True))
            return 0

        print("\nDELTA CYCLE")
        print("cycle_id:", cycle_result.cycle_id)
        print("route:", cycle_result.route_type)
        print("success:", cycle_result.success)
        print("confidence:", cycle_result.confidence)
        print("memory_ids:", ", ".join(cycle_result.memory_ids))
        print("relationship_ids:", ", ".join(cycle_result.relationship_ids))
        print("learning_ids:", ", ".join(cycle_result.learning_ids))
        print("output:", cycle_result.output)
        return 0

    result = loop.run(prompt)

    if args.json:
        print(json.dumps(_to_jsonable(result), indent=2, sort_keys=True))
        return 0

    execution = result["result"]
    if args.remember_output and execution.success:
        record = memory.add(
            text=str(execution.output),
            kind="orchestration_output",
            source=f"delta:{execution.route_type}",
            confidence=float(execution.confidence),
            tags=("orchestration", execution.route_type),
            metadata={"prompt": prompt},
        )
        print(f"remembered output: {record.memory_id}")

    print("\nDELTA RESULT")
    print("task_type:", result["task_type"].value)
    print("route:", execution.route_type)
    print("success:", execution.success)
    print("confidence:", execution.confidence)
    print("output:", execution.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
