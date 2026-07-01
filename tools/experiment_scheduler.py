from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.model_runtime import ProviderManager
from integration.model_runtime.provider_qualification import load_capability_database
from orchestration.curriculum import CalibrationCurriculumGenerator
from orchestration.experiments import ExperimentQueueStore, ExperimentScheduler
from orchestration.experience import ExperienceStore


DEFAULT_PROMPTS = {
    "planning": (
        "Create a plan, then revise it after a trusted observation contradicts step two.",
        "Predict which part of this plan will fail under uncertainty and explain why.",
    ),
    "coding": (
        "Find a likely integration boundary bug in a small runtime adapter and propose a test.",
        "Explain how to preserve provenance while transforming structured input.",
    ),
    "prediction": (
        "Predict the outcome of a workflow, then name the evidence that would falsify it.",
        "Generate a falsifiable prediction about provider disagreement on identical evidence.",
    ),
    "reflection": (
        "Reflect on why repeated low-novelty experiences fail to improve learning.",
        "Identify what evidence would justify changing a high-confidence belief.",
    ),
}

SMOKE_PROMPTS = (
    ("deterministic", "What is 2 + 2?"),
    ("explanation", "Explain why the sky appears blue in one paragraph."),
    (
        "json",
        'Return ONLY JSON: {"planet":"Earth","moons":1}',
    ),
    ("planning", "Create a five-step plan for organizing a construction project."),
    ("reflection", "Explain one weakness in your previous answer."),
    ("coding", "Write a small Python function that validates a provider status record."),
    ("reasoning", "Compare two explanations and identify the stronger argument."),
)


def _paths(root: Path) -> tuple[ExperimentQueueStore, ExperienceStore, Path, Path]:
    data = root / "data"
    return (
        ExperimentQueueStore(
            data / "experiments" / "experiment_queue.jsonl",
            data / "experiments" / "experiment_results.jsonl",
        ),
        ExperienceStore(data / "experience" / "generated_experiences.jsonl"),
        data / "model_runtime" / "provider_status.json",
        data / "model_runtime" / "provider_capabilities.json",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Queue and run Delta provider experiments serially."
    )
    parser.add_argument("--capability", default="planning")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--provider-model", default=None)
    parser.add_argument("--prompt", action="append", default=[])
    parser.add_argument("--enqueue-defaults", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--allow-cloud", action="store_true")
    parser.add_argument("--n-gpu-layers", type=int, default=None)
    parser.add_argument("--ignore-qualification-db", action="store_true")
    parser.add_argument(
        "--enqueue-provider-smoke",
        action="store_true",
        help="Queue five diagnostic prompts for every qualified provider.",
    )
    parser.add_argument(
        "--enqueue-calibration",
        action="store_true",
        help="Queue high-utility cognitive calibration prompts for every qualified provider.",
    )
    parser.add_argument(
        "--calibration-count",
        type=int,
        default=8,
        help="Number of calibration objectives to select before provider fan-out.",
    )
    args = parser.parse_args()

    store, experience_store, provider_status_path, capability_db_path = _paths(ROOT)
    manager = ProviderManager(
        n_gpu_layers=args.n_gpu_layers,
        status_path=provider_status_path,
        capability_db_path=capability_db_path,
    )
    scheduler = ExperimentScheduler(
        store=store,
        provider_manager=manager,
        experience_store=experience_store,
        allow_cloud=args.allow_cloud,
        capability_db_path=None
        if args.ignore_qualification_db
        else capability_db_path,
    )

    prompts = list(args.prompt)
    if args.enqueue_provider_smoke:
        smoke_run_id = f"provider_smoke_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        database = load_capability_database(capability_db_path)
        qualified = [
            name
            for name, profile in sorted(database.items())
            if isinstance(profile, dict) and profile.get("qualified") is True
        ]
        total = 0
        for provider_model in qualified:
            for capability, prompt in SMOKE_PROMPTS:
                total += len(
                    scheduler.enqueue_capability_batch(
                        capability=capability,
                        task_type=capability,
                        prompts=[prompt],
                        provider_model=provider_model,
                        metadata={
                            "source": "provider_smoke",
                            "phase": "phase_1_provider_smoke",
                            "run_id": smoke_run_id,
                        },
                    )
                )
        print(f"enqueued_provider_smoke={total} providers={len(qualified)} run_id={smoke_run_id}")
    if args.enqueue_calibration:
        calibration_run_id = f"calibration_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        database = load_capability_database(capability_db_path)
        qualified = [
            name
            for name, profile in sorted(database.items())
            if isinstance(profile, dict) and profile.get("qualified") is True
        ]
        previous_prompts = [item.prompt for item in store.items()]
        objectives = CalibrationCurriculumGenerator().generate(
            count=args.calibration_count,
            previous_prompts=previous_prompts,
            min_utility=0.4,
        )
        total = 0
        for provider_model in qualified:
            for scored in objectives:
                objective = scored.objective
                total += len(
                    scheduler.enqueue_capability_batch(
                        capability=objective.capability,
                        task_type=objective.task_type,
                        prompts=[objective.prompt],
                        provider_model=provider_model,
                        priority=int(scored.calibration_score * 1000),
                        metadata={
                            "source": "calibration_curriculum",
                            "phase": "phase_14_cognitive_calibration",
                            "run_id": calibration_run_id,
                            "objective_id": objective.objective_id,
                            "expected_signals": list(objective.expected_signals),
                            "required_capabilities": list(objective.required_capabilities),
                            "selection_utility": scored.novelty_report.experience_utility_score,
                            "selection_information_gain": scored.novelty_report.information_gain_score,
                            "selection_surprise": scored.novelty_report.surprise_score,
                            "selection_diversity": scored.diversity_score,
                            "selection_calibration_score": scored.calibration_score,
                        },
                    )
                )
        print(
            "enqueued_calibration="
            f"{total} providers={len(qualified)} objectives={len(objectives)} "
            f"run_id={calibration_run_id}"
        )
    if args.enqueue_defaults:
        prompts.extend(DEFAULT_PROMPTS.get(args.capability, ()))
    if prompts:
        items = scheduler.enqueue_capability_batch(
            capability=args.capability,
            task_type=args.task_type or args.capability,
            prompts=prompts,
            provider_model=args.provider_model,
            metadata={"source": "tools/experiment_scheduler.py"},
        )
        print(f"enqueued={len(items)} capability={args.capability}")

    if args.run:
        results = scheduler.run_next(limit=args.limit)
        for result in results:
            print(
                "result "
                f"item_id={result.item_id} status={result.status} "
                f"route={result.route} provider={result.provider_model} "
                f"utility={result.utility_score}"
            )

    summary = scheduler.summary()
    print(
        "summary "
        f"queued={summary.queued} completed={summary.completed} "
        f"failed={summary.failed} cumulative_utility={summary.cumulative_utility}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
