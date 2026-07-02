from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _failure_reasons(decision: dict[str, Any]) -> list[str]:
    dimensions = decision.get("dimensions", {})
    evidence = decision.get("evidence", {})
    reasons: list[str] = []
    if evidence.get("failed_predictions", 0) > evidence.get("effective_failed_predictions", evidence.get("failed_predictions", 0)):
        reasons.append("recovered_prior_failure")
    if evidence.get("failed_predictions", 0) > 0:
        reasons.append("failed_validation")
    if evidence.get("open_contradictions", 0) > 0:
        reasons.append("contradiction")
    if dimensions.get("redundancy_penalty", 0.0) >= 0.32:
        reasons.append("redundancy")
    if dimensions.get("prompt_artifact_penalty", 0.0) >= 0.32:
        reasons.append("prompt_artifact")
    if evidence.get("unresolved_predictions", 0) > 0:
        reasons.append("unresolved_prediction")
    if evidence.get("incomplete_proposition"):
        reasons.append("incomplete_proposition")
    if dimensions.get("evidence_support", 0.0) < 0.35:
        reasons.append("insufficient_evidence")
    if dimensions.get("relationship_centrality", 0.0) <= 0.0:
        reasons.append("low_centrality")
    return reasons or ["low_composite_score"]


def _provider_usage(training: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in training.get("cycle_summaries", []):
        provider = item.get("provider_model")
        if provider:
            counts[str(provider)] += 1
    if counts:
        return dict(counts)
    for provider, metrics in training.get("provider_metrics", {}).items():
        counts[str(provider)] += int(metrics.get("cycles", 0))
    return dict(counts)


def aggregate_campaigns(*, campaign_root: Path, reports_dir: Path) -> dict[str, Any]:
    runs = []
    failure_counts: Counter[str] = Counter()
    lifecycle_counts: Counter[str] = Counter()
    promotion_scores: list[float] = []
    centrality_values: list[float] = []
    provider_counts: Counter[str] = Counter()
    for run_dir in sorted(path for path in campaign_root.iterdir() if path.is_dir()):
        reports = run_dir / "reports"
        operator = _load_json(reports / "continuous_learning_operator_report.json")
        training = _load_json(reports / "continuous_learning_training_summary.json")
        phase16 = _load_json(reports / "phase16_validation_report.json")
        phase17 = _load_json(reports / "phase17_validation_report.json")
        phase18 = _load_json(reports / "phase18_normalization_report.json")
        governance = _load_json(reports / "promotion_governance_report.json")
        decisions = governance.get("decisions", [])
        run_failure_counts: Counter[str] = Counter()
        for decision in decisions:
            lifecycle_counts[decision.get("recommendation", "unknown")] += 1
            promotion_scores.append(float(decision.get("promotion_score", 0.0)))
            centrality_values.append(
                float(decision.get("dimensions", {}).get("relationship_centrality", 0.0))
            )
            if decision.get("recommendation") in {"Reject", "Hold for More Validation", "Experimental"}:
                reasons = _failure_reasons(decision)
                failure_counts.update(reasons)
                run_failure_counts.update(reasons)
        provider_counts.update(_provider_usage(training))
        final_counts = training.get("final_counts", {})
        baseline_counts = training.get("baseline_counts", {})
        after_quality = phase17.get("after_prediction_quality") or phase16.get("after_prediction_quality") or {}
        run_summary = {
            "run": run_dir.name,
            "cycles_requested": operator.get("cycles_requested", training.get("cycles_requested", 0)),
            "cycles_completed": training.get("cycles_completed", 0),
            "profiles": training.get("curriculum_profiles", []),
            "semantic_concepts": final_counts.get("semantic_knowledge", 0),
            "semantic_growth": final_counts.get("semantic_knowledge", 0)
            - baseline_counts.get("semantic_knowledge", 0),
            "relationship_growth": final_counts.get("relationships", 0)
            - baseline_counts.get("relationships", 0),
            "memory_growth": final_counts.get("memories", 0)
            - baseline_counts.get("memories", 0),
            "prediction_coverage": after_quality.get("coverage", 0.0),
            "supported_predictions": after_quality.get("supported", 0),
            "failed_predictions": after_quality.get("failed", 0),
            "contradictions": final_counts.get("contradictions", 0),
            "normalization_recovered": phase18.get("recovered_concepts", 0),
            "normalization_precision": phase18.get("normalization_precision", 0.0),
            "average_promotion_score": governance.get("average_promotion_score", 0.0),
            "promotion_counts": governance.get("recommendation_counts", {}),
            "dominant_failure_reason": (
                run_failure_counts.most_common(1)[0][0] if run_failure_counts else "none"
            ),
            "runtime_seconds": training.get("elapsed_seconds", 0.0),
        }
        runs.append(run_summary)

    aggregate = {
        "campaign_root": str(campaign_root),
        "runs": runs,
        "run_count": len(runs),
        "aggregate_failure_distribution": dict(failure_counts.most_common()),
        "aggregate_lifecycle_distribution": dict(lifecycle_counts.most_common()),
        "provider_usage": dict(provider_counts.most_common()),
        "promotion_score_average": round(mean(promotion_scores), 4) if promotion_scores else 0.0,
        "centrality_average": round(mean(centrality_values), 4) if centrality_values else 0.0,
        "promotion_eligible_total": sum(
            run["promotion_counts"].get("Promotion Eligible", 0) for run in runs
        ),
        "validated_total": sum(run["promotion_counts"].get("Validated", 0) for run in runs),
        "candidate_total": sum(run["promotion_counts"].get("Candidate", 0) for run in runs),
        "rejected_total": sum(run["promotion_counts"].get("Reject", 0) for run in runs),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase20_cross_run_report.json").write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(aggregate, reports_dir)
    return aggregate


def _write_markdown(aggregate: dict[str, Any], reports_dir: Path) -> None:
    runs = aggregate["runs"]
    run_rows = [
        (
            f"| {run['run']} | {run['cycles_completed']} | "
            f"{','.join(run['profiles']) or 'all'} | {run['semantic_growth']} | "
            f"{run['prediction_coverage']} | {run['average_promotion_score']} | "
            f"{run['promotion_counts'].get('Promotion Eligible', 0)} | "
            f"{run['promotion_counts'].get('Validated', 0)} | "
            f"{run['promotion_counts'].get('Reject', 0)} | "
            f"{run['dominant_failure_reason']} |"
        )
        for run in runs
    ]
    report = [
        "# Phase 20 Cross-Run Campaign Report",
        "",
        "| Run | Cycles | Profile | Semantic Growth | Prediction Coverage | Avg Promotion Score | Promotion Eligible | Validated | Rejected | Dominant Failure |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        *run_rows,
        "",
        "## Aggregate Failure Distribution",
        "",
        *[
            f"- `{reason}`: `{count}`"
            for reason, count in aggregate["aggregate_failure_distribution"].items()
        ],
        "",
        "## Lifecycle Distribution",
        "",
        *[
            f"- `{state}`: `{count}`"
            for state, count in aggregate["aggregate_lifecycle_distribution"].items()
        ],
        "",
        "## Promotion Trend",
        "",
        f"- Promotion eligible total: `{aggregate['promotion_eligible_total']}`",
        f"- Validated total: `{aggregate['validated_total']}`",
        f"- Candidate total: `{aggregate['candidate_total']}`",
        f"- Rejected total: `{aggregate['rejected_total']}`",
        f"- Average promotion score: `{aggregate['promotion_score_average']}`",
        f"- Average relationship centrality score: `{aggregate['centrality_average']}`",
        "",
    ]
    (reports_dir / "phase20_cross_run_report.md").write_text(
        "\n".join(report),
        encoding="utf-8",
    )
    (reports_dir / "phase20_failure_distribution.md").write_text(
        "\n".join(
            [
                "# Phase 20 Failure Distribution",
                "",
                *[
                    f"- `{reason}`: `{count}`"
                    for reason, count in aggregate["aggregate_failure_distribution"].items()
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phase20_governance_trend.md").write_text(
        "\n".join(
            [
                "# Phase 20 Governance Trend",
                "",
                *[
                    f"- `{run['run']}`: score `{run['average_promotion_score']}`, counts `{run['promotion_counts']}`"
                    for run in runs
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phase20_promotion_trend.md").write_text(
        "\n".join(
            [
                "# Phase 20 Promotion Trend",
                "",
                f"Promotion eligible total: `{aggregate['promotion_eligible_total']}`",
                "",
                "No canonical promotion was performed.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate bounded continuous learning campaign reports.")
    parser.add_argument("--campaign-root", required=True)
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    summary = aggregate_campaigns(
        campaign_root=Path(args.campaign_root),
        reports_dir=Path(args.reports_dir),
    )
    print(
        json.dumps(
            {
                "run_count": summary["run_count"],
                "promotion_eligible_total": summary["promotion_eligible_total"],
                "promotion_score_average": summary["promotion_score_average"],
                "top_failure": next(iter(summary["aggregate_failure_distribution"]), "none"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
