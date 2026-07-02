from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.governed_training_run import run_training
from tools.phase16_validation import run_validation
from tools.phase17_adversarial_validation import run_adversarial_validation
from tools.phase18_semantic_normalization import run_normalization
from tools.promotion_governance import run_promotion_governance


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def run_continuous_learning(
    *,
    store_root: Path,
    reports_dir: Path,
    cycles: int = 0,
    objective_count: int = 8,
    validation_limit: int = 40,
    adversarial_limit: int = 40,
    normalization_limit: int = 40,
    curriculum_profiles: tuple[str, ...] = (),
    default_model: str = "qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    structured_output_contract: bool = False,
    use_projection: bool = True,
) -> dict[str, Any]:
    if cycles > 200:
        raise ValueError("Continuous operator bounded campaign runs are limited to 200 cycles.")
    reports_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    training_summary = None
    if cycles > 0:
        training_summary = run_training(
            cycles=cycles,
            store_root=store_root,
            objective_count=objective_count,
            default_model=default_model,
            curriculum_profiles=curriculum_profiles,
            curriculum_balancing=bool(curriculum_profiles),
            stop_on_saturation=True,
            saturation_window=min(20, max(2, cycles)),
            gold_curriculum_path=reports_dir / "continuous_learning_gold_curriculum.json",
            structured_output_contract=structured_output_contract,
        )
        (reports_dir / "continuous_learning_training_summary.json").write_text(
            json.dumps(_jsonable(training_summary), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        steps.append(
            {
                "step": "learn",
                "cycles_completed": training_summary["cycles_completed"],
                "semantic_delta": training_summary["count_delta"]["semantic_knowledge"],
                "prediction_delta": training_summary["count_delta"]["predictions"],
            }
        )
    validation_summary = run_validation(
        store_root=store_root,
        max_predictions=validation_limit,
        reports_dir=reports_dir,
    )
    steps.append(
        {
            "step": "validate",
            "selected_predictions": validation_summary.get("predictions_selected", 0),
            "coverage_after": validation_summary.get("after_prediction_quality", {}).get("coverage"),
        }
    )
    adversarial_summary = run_adversarial_validation(
        store_root=store_root,
        max_predictions=adversarial_limit,
        reports_dir=reports_dir,
    )
    steps.append(
        {
            "step": "challenge_beliefs",
            "selected_predictions": adversarial_summary.get("predictions_selected", 0),
            "failed_predictions": adversarial_summary.get("validation_status_counts", {}).get("failed", 0),
        }
    )
    normalization_summary = run_normalization(
        store_root=store_root,
        reports_dir=reports_dir,
        max_items=normalization_limit,
    )
    steps.append(
        {
            "step": "normalize",
            "normalized_concepts": normalization_summary["normalized_concepts"],
            "recovered_concepts": normalization_summary["recovered_concepts"],
            "normalization_precision": normalization_summary["normalization_precision"],
        }
    )
    governance_summary = run_promotion_governance(
        store_root=store_root,
        reports_dir=reports_dir,
        use_projection=use_projection,
    )
    steps.append(
        {
            "step": "govern",
            "concepts_evaluated": governance_summary["concepts_evaluated"],
            "recommendation_counts": governance_summary["recommendation_counts"],
            "canonical_merge_performed": False,
        }
    )
    summary = {
        "run_id": f"continuous_learning_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "store_root": str(store_root),
        "reports_dir": str(reports_dir),
        "canonical_merge_performed": False,
        "cycles_requested": cycles,
        "structured_output_contract": bool(structured_output_contract),
        "virtual_projection_enabled": bool(use_projection),
        "steps": steps,
        "training_summary_path": (
            str(reports_dir / "continuous_learning_training_summary.json")
            if training_summary is not None
            else None
        ),
        "promotion_governance_report": str(reports_dir / "promotion_governance_report.md"),
    }
    (reports_dir / "continuous_learning_operator_report.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "continuous_learning_operator_report.md").write_text(
        "\n".join(
            [
                "# Continuous Learning Operator Report",
                "",
                "The operator executed the existing bounded learning pipeline and ended in "
                "promotion governance recommendations. Canonical knowledge was not merged.",
                "",
                "| Step | Result |",
                "| --- | --- |",
                *[
                    f"| {step['step']} | `{json.dumps(step, sort_keys=True)}` |"
                    for step in steps
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Delta's bounded continuous learning pipeline.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--cycles", type=int, default=0)
    parser.add_argument("--objective-count", type=int, default=8)
    parser.add_argument("--validation-limit", type=int, default=40)
    parser.add_argument("--adversarial-limit", type=int, default=40)
    parser.add_argument("--normalization-limit", type=int, default=40)
    parser.add_argument("--curriculum-profile", action="append", default=[])
    parser.add_argument(
        "--default-model",
        default="qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m",
    )
    parser.add_argument("--structured-output-contract", action="store_true")
    parser.add_argument(
        "--disable-projection",
        action="store_true",
        help="Disable virtual semantic relationship projection during governance.",
    )
    args = parser.parse_args()
    summary = run_continuous_learning(
        store_root=Path(args.store_root),
        reports_dir=Path(args.reports_dir),
        cycles=args.cycles,
        objective_count=args.objective_count,
        validation_limit=args.validation_limit,
        adversarial_limit=args.adversarial_limit,
        normalization_limit=args.normalization_limit,
        curriculum_profiles=tuple(args.curriculum_profile),
        default_model=args.default_model,
        structured_output_contract=args.structured_output_contract,
        use_projection=not args.disable_projection,
    )
    print(json.dumps(_jsonable(summary), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
