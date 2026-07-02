from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
import sys
import time
from collections import defaultdict
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
from orchestration.curriculum import CalibrationCurriculumGenerator, broad_profile_names
from orchestration.curriculum.calibration_curriculum import ScoredCalibrationObjective
from orchestration.loop.cognitive_loop import CognitiveLoop
from orchestration.runtime import CognitiveRuntime
from orchestration.self_model import SelfModelRegion


CAPABILITY_PROVIDER_HINTS = {
    "prediction": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "planning": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "cross_domain": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "causal_reasoning": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "scientific_reasoning": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "tool_use": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "long_dependency": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
    "probabilistic_reasoning": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "resource_allocation": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "multi_agent_coordination": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "economics": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "medical_reasoning": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "mechanical_diagnosis": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "software_debugging": "phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m",
    "systems_engineering": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
    "cybersecurity_defense": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "experimental_design": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "ethical_tradeoffs": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
    "negotiation": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
    "risk_assessment": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "failure_analysis": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "counterfactual_reasoning": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "analogical_reasoning": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
    "cross_domain_transfer": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
    "hierarchical_planning": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "information_synthesis": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
    "hypothesis_revision": "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    "contradiction": "mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m",
    "transfer": "meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m",
}


STRUCTURED_PROPOSITION_CONTRACT = (
    "Output contract for Delta semantic extraction:\n"
    "- Answer naturally and complete the requested reasoning.\n"
    "- Do not refer to this prompt, this task, the question, the user, or Delta training data.\n"
    "- Complete conditional statements; avoid dangling if/when clauses and sentence fragments.\n"
    "- Avoid procedural commentary such as 'the cycle can be completed by predicting that'.\n"
    "- Prefer general reusable knowledge over task-specific wording.\n"
    "- End with a section titled 'Reusable propositions:' containing 3-5 complete bullet propositions.\n"
)


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
        if "causal" in text or "counterfactual" in text:
            return CAPABILITY_PROVIDER_HINTS["causal_reasoning"]
        if "hypothesis" in text or "scientific" in text:
            return CAPABILITY_PROVIDER_HINTS["scientific_reasoning"]
        if "tool" in text or "logs" in text or "invoice" in text:
            return CAPABILITY_PROVIDER_HINTS["tool_use"]
        if "dependency" in text or "downstream" in text:
            return CAPABILITY_PROVIDER_HINTS["long_dependency"]
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


def _prediction_quality_score(quality: dict[str, Any]) -> float:
    coverage = float(quality.get("coverage") or 0.0)
    accuracy = float(quality.get("accuracy") or 0.0)
    evidence = float(quality.get("average_evidence_score") or 0.0)
    return round((coverage * 0.45) + (accuracy * 0.35) + (evidence * 0.20), 4)


def _objective_profiles(item: ScoredCalibrationObjective) -> tuple[str, ...]:
    profiles = item.objective.metadata.get("profiles", ())
    if isinstance(profiles, str):
        profiles = (profiles,)
    cleaned = tuple(str(profile).strip().lower() for profile in profiles if str(profile).strip())
    return cleaned or (item.objective.capability,)


def _primary_profile(
    item: ScoredCalibrationObjective,
    selected_profiles: tuple[str, ...],
) -> str:
    profiles = _objective_profiles(item)
    selected = {profile.lower() for profile in selected_profiles}
    for profile in profiles:
        if profile in selected:
            return profile
    return profiles[0]


def _balanced_schedule(
    objectives: list[ScoredCalibrationObjective],
    *,
    cycles: int,
    selected_profiles: tuple[str, ...],
    seed: int,
    balance: bool,
) -> list[ScoredCalibrationObjective]:
    if not objectives or cycles <= 0:
        return []
    rng = random.Random(seed)
    if not balance:
        pool = list(objectives)
        rng.shuffle(pool)
        schedule = []
        while len(schedule) < cycles:
            if not pool:
                pool = list(objectives)
                rng.shuffle(pool)
            schedule.append(pool.pop())
        return schedule

    groups: dict[str, list[ScoredCalibrationObjective]] = defaultdict(list)
    for item in objectives:
        groups[_primary_profile(item, selected_profiles)].append(item)
    for group in groups.values():
        rng.shuffle(group)

    ordered_profiles = list(selected_profiles or broad_profile_names())
    ordered_profiles = [profile for profile in ordered_profiles if profile in groups]
    for profile in sorted(groups):
        if profile not in ordered_profiles:
            ordered_profiles.append(profile)

    schedule = []
    while len(schedule) < cycles and any(groups.values()):
        for profile in ordered_profiles:
            if groups[profile]:
                schedule.append(groups[profile].pop())
                if len(schedule) >= cycles:
                    break
    return schedule


def saturation_status(
    history: list[dict[str, Any]],
    *,
    window: int,
    min_semantic_delta: int,
    min_prediction_quality_delta: float,
    repetition_threshold: float,
) -> dict[str, Any]:
    if len(history) < max(2, int(window)):
        return {"saturated": False, "reason": "insufficient_history"}
    recent = history[-max(2, int(window)) :]
    semantic_delta = int(recent[-1]["semantic_knowledge"]) - int(
        recent[0]["semantic_knowledge"]
    )
    quality_delta = float(recent[-1]["prediction_quality_score"]) - float(
        recent[0]["prediction_quality_score"]
    )
    unique_objectives = len({str(item["objective_id"]) for item in recent})
    repetition_ratio = 1.0 - (unique_objectives / len(recent))
    saturated = (
        semantic_delta < int(min_semantic_delta)
        and quality_delta < float(min_prediction_quality_delta)
        and repetition_ratio >= float(repetition_threshold)
    )
    return {
        "saturated": saturated,
        "semantic_delta": semantic_delta,
        "prediction_quality_delta": round(quality_delta, 4),
        "unique_objectives": unique_objectives,
        "window": len(recent),
        "objective_repetition_ratio": round(repetition_ratio, 4),
        "reason": (
            "learning_saturation"
            if saturated
            else "semantic_or_quality_growth_still_detected"
        ),
    }


def run_training(
    *,
    cycles: int,
    store_root: Path,
    objective_count: int,
    default_model: str,
    curriculum_profiles: tuple[str, ...] = (),
    random_seed: int = 15,
    curriculum_balancing: bool = False,
    stop_on_saturation: bool = False,
    saturation_window: int = 20,
    min_semantic_delta: int = 2,
    min_prediction_quality_delta: float = 0.05,
    repetition_threshold: float = 0.75,
    gold_curriculum_path: Path | None = None,
    structured_output_contract: bool = False,
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

    candidate_count = max(1, int(objective_count))
    if curriculum_balancing:
        profile_count = len(curriculum_profiles or broad_profile_names())
        candidate_count = max(candidate_count, int(objective_count) * max(1, profile_count))
    objectives = CalibrationCurriculumGenerator().generate(
        count=candidate_count,
        min_utility=0.4,
        profiles=curriculum_profiles,
    )
    if not objectives:
        raise RuntimeError("No calibration objectives were generated.")
    schedule = _balanced_schedule(
        objectives,
        cycles=max(0, int(cycles)),
        selected_profiles=curriculum_profiles,
        seed=random_seed,
        balance=curriculum_balancing,
    )

    started = time.perf_counter()
    cycle_summaries = []
    saturation_checks = []
    stop_reason = None
    objective_metrics: dict[str, dict[str, Any]] = {}
    profile_metrics: dict[str, dict[str, Any]] = {}
    provider_metrics: dict[str, dict[str, Any]] = {}
    for index, scored in enumerate(schedule, start=1):
        objective = scored.objective
        provider_model = CAPABILITY_PROVIDER_HINTS.get(objective.capability, default_model)
        profile = _primary_profile(scored, curriculum_profiles)
        before_counts = _counts(
            memory=memory,
            relationships=relationships,
            learning=learning,
            knowledge=knowledge,
            contradictions=contradictions,
            predictions=predictions,
            goals=goals,
        )
        prompt = (
            f"{objective.prompt}\n\n"
            "Complete the cycle as Delta training data: answer, make at least one "
            "testable prediction when possible, identify evidence that would change "
            "the answer, and reflect on uncertainty."
        )
        if structured_output_contract:
            prompt = f"{prompt}\n\n{STRUCTURED_PROPOSITION_CONTRACT}"
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
        current_counts = _counts(
            memory=memory,
            relationships=relationships,
            learning=learning,
            knowledge=knowledge,
            contradictions=contradictions,
            predictions=predictions,
            goals=goals,
        )
        current_quality = predictions.quality_metrics()
        semantic_delta = (
            current_counts["semantic_knowledge"] - before_counts["semantic_knowledge"]
        )
        prediction_delta = current_counts["predictions"] - before_counts["predictions"]
        contradiction_delta = (
            current_counts["contradictions"] - before_counts["contradictions"]
        )
        for bucket, key in (
            (objective_metrics, objective.objective_id),
            (profile_metrics, profile),
            (provider_metrics, provider_model),
        ):
            metric = bucket.setdefault(
                key,
                {
                    "cycles": 0,
                    "semantic_gain": 0,
                    "prediction_gain": 0,
                    "contradiction_gain": 0,
                },
            )
            metric["cycles"] += 1
            metric["semantic_gain"] += semantic_delta
            metric["prediction_gain"] += prediction_delta
            metric["contradiction_gain"] += contradiction_delta
        cycle_summaries.append(
            {
                "tick": index,
                "objective_id": objective.objective_id,
                "capability": objective.capability,
                "profile": profile,
                "provider_model": provider_model,
                "consolidation": result.consolidation,
                "self_model": result.self_model,
                "semantic_knowledge": current_counts["semantic_knowledge"],
                "semantic_delta": semantic_delta,
                "prediction_delta": prediction_delta,
                "contradiction_delta": contradiction_delta,
                "prediction_quality_score": _prediction_quality_score(current_quality),
            }
        )
        if stop_on_saturation:
            check = saturation_status(
                cycle_summaries,
                window=saturation_window,
                min_semantic_delta=min_semantic_delta,
                min_prediction_quality_delta=min_prediction_quality_delta,
                repetition_threshold=repetition_threshold,
            )
            check["tick"] = index
            if check["reason"] != "insufficient_history":
                saturation_checks.append(check)
            if check["saturated"]:
                stop_reason = check
                break
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
    gold_items = _gold_curriculum_items(
        objectives=objectives,
        objective_metrics=objective_metrics,
        selected_profiles=curriculum_profiles,
    )
    if gold_curriculum_path is not None:
        gold_curriculum_path.parent.mkdir(parents=True, exist_ok=True)
        gold_curriculum_path.write_text(
            json.dumps(_jsonable(gold_items), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {
        "run_id": f"governed_training_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "cycles_requested": cycles,
        "cycles_completed": len(cycle_summaries),
        "stopped_early": stop_reason is not None,
        "stop_reason": stop_reason,
        "elapsed_seconds": round(elapsed, 4),
        "cycles_per_second": round(len(cycle_summaries) / elapsed, 4) if elapsed else None,
        "store_root": str(store_root),
        "curriculum_profiles": list(curriculum_profiles),
        "random_seed": random_seed,
        "curriculum_balancing": curriculum_balancing,
        "saturation_policy": {
            "enabled": stop_on_saturation,
            "window": saturation_window,
            "min_semantic_delta": min_semantic_delta,
            "min_prediction_quality_delta": min_prediction_quality_delta,
            "repetition_threshold": repetition_threshold,
        },
        "structured_output_contract": bool(structured_output_contract),
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
                "profiles": list(_objective_profiles(item)),
                "calibration_score": item.calibration_score,
                "utility": item.novelty_report.experience_utility_score,
                "surprise": item.novelty_report.surprise_score,
            }
            for item in objectives
        ],
        "provider_hints": dict(CAPABILITY_PROVIDER_HINTS),
        "objective_metrics": objective_metrics,
        "profile_metrics": profile_metrics,
        "provider_metrics": provider_metrics,
        "gold_curriculum_items": gold_items[:50],
        "saturation_checks": saturation_checks[-10:],
        "cycle_summaries": cycle_summaries[-10:],
    }


def _gold_curriculum_items(
    *,
    objectives: list[ScoredCalibrationObjective],
    objective_metrics: dict[str, dict[str, Any]],
    selected_profiles: tuple[str, ...],
) -> list[dict[str, Any]]:
    by_id = {item.objective.objective_id: item for item in objectives}
    gold = []
    for objective_id, metrics in objective_metrics.items():
        if metrics.get("semantic_gain", 0) <= 0:
            continue
        if metrics.get("contradiction_gain", 0) > 0:
            continue
        item = by_id.get(objective_id)
        if item is None:
            continue
        gold.append(
            {
                "objective_id": objective_id,
                "profile": _primary_profile(item, selected_profiles),
                "capability": item.objective.capability,
                "prompt": item.objective.prompt,
                "semantic_gain": metrics.get("semantic_gain", 0),
                "prediction_gain": metrics.get("prediction_gain", 0),
                "contradiction_gain": metrics.get("contradiction_gain", 0),
                "calibration_score": item.calibration_score,
                "utility": item.novelty_report.experience_utility_score,
                "surprise": item.novelty_report.surprise_score,
            }
        )
    return sorted(
        gold,
        key=lambda item: (
            -int(item["semantic_gain"]),
            int(item["contradiction_gain"]),
            -float(item["calibration_score"]),
            item["objective_id"],
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run governed local-provider Delta training cycles.")
    parser.add_argument("--cycles", type=int, required=True)
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--summary-path", required=True)
    parser.add_argument("--objective-count", type=int, default=8)
    parser.add_argument(
        "--curriculum-profile",
        action="append",
        default=[],
        help="Restrict calibration objectives to a profile; may be repeated.",
    )
    parser.add_argument("--stop-on-saturation", action="store_true")
    parser.add_argument("--curriculum-balancing", action="store_true")
    parser.add_argument("--random-seed", type=int, default=15)
    parser.add_argument("--saturation-window", type=int, default=20)
    parser.add_argument("--min-semantic-delta", type=int, default=2)
    parser.add_argument("--min-prediction-quality-delta", type=float, default=0.05)
    parser.add_argument("--repetition-threshold", type=float, default=0.75)
    parser.add_argument("--gold-curriculum-path")
    parser.add_argument(
        "--structured-output-contract",
        action="store_true",
        help="Ask providers to emit complete reusable propositions for semantic extraction.",
    )
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
        curriculum_profiles=tuple(args.curriculum_profile),
        random_seed=args.random_seed,
        curriculum_balancing=args.curriculum_balancing,
        stop_on_saturation=args.stop_on_saturation,
        saturation_window=args.saturation_window,
        min_semantic_delta=args.min_semantic_delta,
        min_prediction_quality_delta=args.min_prediction_quality_delta,
        repetition_threshold=args.repetition_threshold,
        gold_curriculum_path=(
            Path(args.gold_curriculum_path) if args.gold_curriculum_path else None
        ),
        structured_output_contract=args.structured_output_contract,
    )
    payload = json.dumps(_jsonable(summary), indent=2, sort_keys=True)
    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
