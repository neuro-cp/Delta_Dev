from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, time as clock_time, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.continuous_learning_operator import run_continuous_learning


@dataclass(frozen=True)
class CampaignSpec:
    name: str
    cycles: int
    profiles: tuple[str, ...]
    objective_count: int
    random_seed_note: str
    question: str


DEFAULT_CAMPAIGNS: tuple[CampaignSpec, ...] = (
    CampaignSpec(
        name="planning_100",
        cycles=100,
        profiles=("planning",),
        objective_count=100,
        random_seed_note="default training seed",
        question="Does planning curriculum compound after Phase 25 filtering?",
    ),
    CampaignSpec(
        name="contradiction_100",
        cycles=100,
        profiles=("contradiction",),
        objective_count=100,
        random_seed_note="default training seed",
        question="Does contradiction curriculum produce stronger validation and falsification?",
    ),
    CampaignSpec(
        name="causal_reasoning_100",
        cycles=100,
        profiles=("causal_reasoning",),
        objective_count=100,
        random_seed_note="default training seed",
        question="Does causal reasoning curriculum improve recurrence and graph structure?",
    ),
    CampaignSpec(
        name="broad_balanced_100",
        cycles=100,
        profiles=(
            "planning",
            "contradiction",
            "causal_reasoning",
            "risk_assessment",
            "resource_allocation",
        ),
        objective_count=100,
        random_seed_note="default training seed",
        question="Does broader profile diversity improve survival and promotion scores?",
    ),
    CampaignSpec(
        name="broad_balanced_200",
        cycles=200,
        profiles=(
            "planning",
            "contradiction",
            "causal_reasoning",
            "risk_assessment",
            "resource_allocation",
        ),
        objective_count=200,
        random_seed_note="default training seed",
        question="Do cleaner candidates compound across the maximum bounded window?",
    ),
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_reset_dir(path: Path, root: Path) -> None:
    resolved = path.resolve()
    resolved_root = root.resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise ValueError(f"Refusing to remove path outside campaign root: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _deadline_reached(deadline: datetime | None) -> bool:
    return deadline is not None and datetime.now().astimezone() >= deadline


def _deadline_for_today(value: str | None) -> datetime | None:
    if not value:
        return None
    hour, minute = [int(part) for part in value.split(":", 1)]
    now = datetime.now().astimezone()
    return datetime.combine(now.date(), clock_time(hour, minute), tzinfo=now.tzinfo)


def _recommendation_counts(governance: dict[str, Any]) -> Counter[str]:
    return Counter(governance.get("recommendation_counts", {}))


def _decision_values(decisions: list[dict[str, Any]], key: str) -> list[float]:
    values = []
    for decision in decisions:
        value = decision.get("dimensions", {}).get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _mean(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _failure_reasons(decision: dict[str, Any]) -> list[str]:
    dimensions = decision.get("dimensions", {})
    evidence = decision.get("evidence", {})
    reasons: list[str] = []
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
    for provider, metrics in training.get("provider_metrics", {}).items():
        counts[str(provider)] += int(metrics.get("cycles", 0))
    return dict(counts)


def _semantic_diversity(decisions: list[dict[str, Any]]) -> float:
    tokens: Counter[str] = Counter()
    total = 0
    for decision in decisions:
        words = [
            word.strip(".,;:()[]{}\"'").lower()
            for word in str(decision.get("concept", "")).split()
            if len(word.strip(".,;:()[]{}\"'")) >= 4
        ]
        total += len(words)
        tokens.update(words)
    return round(len(tokens) / max(1, total), 4)


def _concept_recurrence(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    phrases: Counter[str] = Counter(
        " ".join(str(item.get("concept", "")).lower().split())
        for item in decisions
        if item.get("concept")
    )
    recurring = {text: count for text, count in phrases.items() if count > 1}
    return {
        "recurring_concept_texts": len(recurring),
        "max_exact_recurrence": max(recurring.values(), default=1),
        "top_recurring": dict(Counter(recurring).most_common(10)),
    }


def _survival_curve(
    *,
    training: dict[str, Any],
    phase16: dict[str, Any],
    phase17: dict[str, Any],
    phase18: dict[str, Any],
    governance: dict[str, Any],
) -> dict[str, Any]:
    final_counts = training.get("final_counts", {})
    baseline_counts = training.get("baseline_counts", {})
    created = max(
        0,
        int(final_counts.get("semantic_knowledge", 0))
        - int(baseline_counts.get("semantic_knowledge", 0)),
    )
    decisions = governance.get("decisions", [])
    recs = _recommendation_counts(governance)
    non_rejected = sum(
        recs.get(name, 0)
        for name in (
            "Experimental",
            "Candidate",
            "Validated",
            "Promotion Eligible",
            "Hold for More Validation",
        )
    )
    validation_quality = phase17.get("after_prediction_quality") or phase16.get(
        "after_prediction_quality",
        {},
    )
    validated_predictions = int(validation_quality.get("supported", 0)) + int(
        validation_quality.get("failed", 0)
    )
    return {
        "extracted_candidates": created,
        "semantic_records_evaluated": len(decisions),
        "predictions_validated": validated_predictions,
        "survived_normalization": len(decisions) - int(phase18.get("still_rejected", 0) or 0),
        "survived_governance": non_rejected,
        "promotion_candidates": recs.get("Candidate", 0)
        + recs.get("Validated", 0)
        + recs.get("Promotion Eligible", 0),
        "promotion_eligible": recs.get("Promotion Eligible", 0),
        "canonical_ready": 0,
    }


def _summarize_run(run_dir: Path, spec: CampaignSpec, started: float, error: str | None) -> dict[str, Any]:
    reports = run_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    training = _load_json(reports / "continuous_learning_training_summary.json")
    phase16 = _load_json(reports / "phase16_validation_report.json")
    phase17 = _load_json(reports / "phase17_validation_report.json")
    phase18 = _load_json(reports / "phase18_normalization_report.json")
    governance = _load_json(reports / "promotion_governance_report.json")
    operator = _load_json(reports / "continuous_learning_operator_report.json")
    decisions = governance.get("decisions", [])
    recs = _recommendation_counts(governance)
    final_counts = training.get("final_counts", {})
    baseline_counts = training.get("baseline_counts", {})
    after_quality = phase17.get("after_prediction_quality") or phase16.get(
        "after_prediction_quality",
        {},
    )
    failure_counts: Counter[str] = Counter()
    for decision in decisions:
        if decision.get("recommendation") in {"Reject", "Hold for More Validation", "Experimental"}:
            failure_counts.update(_failure_reasons(decision))
    scores = [float(item.get("promotion_score", 0.0)) for item in decisions]
    summary = {
        "run": spec.name,
        "question": spec.question,
        "status": "failed" if error else "completed",
        "error": error,
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "cycles_requested": spec.cycles,
        "cycles_completed": int(training.get("cycles_completed", 0)),
        "profiles": list(spec.profiles),
        "objective_count": spec.objective_count,
        "stopped_early": bool(training.get("stopped_early")),
        "stop_reason": training.get("stop_reason"),
        "semantic_growth": int(final_counts.get("semantic_knowledge", 0))
        - int(baseline_counts.get("semantic_knowledge", 0)),
        "memory_growth": int(final_counts.get("memories", 0))
        - int(baseline_counts.get("memories", 0)),
        "relationship_growth": int(final_counts.get("relationships", 0))
        - int(baseline_counts.get("relationships", 0)),
        "prediction_growth": int(final_counts.get("predictions", 0))
        - int(baseline_counts.get("predictions", 0)),
        "contradictions": int(final_counts.get("contradictions", 0)),
        "prediction_coverage": after_quality.get("coverage", 0.0),
        "supported_predictions": int(after_quality.get("supported", 0)),
        "failed_predictions": int(after_quality.get("failed", 0)),
        "inconclusive_predictions": int(after_quality.get("inconclusive", 0)),
        "open_predictions": int(after_quality.get("open", 0)),
        "normalization_recovered": int(phase18.get("recovered_concepts", 0) or 0),
        "normalization_precision": float(phase18.get("normalization_precision", 0.0) or 0.0),
        "average_promotion_score": governance.get("average_promotion_score", _mean(scores)),
        "promotion_score_max": round(max(scores), 4) if scores else 0.0,
        "promotion_score_min": round(min(scores), 4) if scores else 0.0,
        "promotion_counts": dict(recs),
        "promotion_eligible": int(recs.get("Promotion Eligible", 0)),
        "validated_concepts": int(recs.get("Validated", 0)),
        "candidate_concepts": int(recs.get("Candidate", 0)),
        "rejected_concepts": int(recs.get("Reject", 0)),
        "artifact_rate": _mean(_decision_values(decisions, "prompt_artifact_penalty")),
        "incomplete_rate": _mean(_decision_values(decisions, "incomplete_proposition")),
        "redundancy_average": _mean(_decision_values(decisions, "redundancy_penalty")),
        "centrality_average": _mean(_decision_values(decisions, "relationship_centrality")),
        "projected_centrality_average": _mean(_decision_values(decisions, "projected_centrality")),
        "relationship_diversity_average": _mean(
            _decision_values(decisions, "projected_relationship_diversity")
        ),
        "semantic_diversity": _semantic_diversity(decisions),
        "concept_recurrence": _concept_recurrence(decisions),
        "failure_distribution": dict(failure_counts.most_common()),
        "dominant_failure": failure_counts.most_common(1)[0][0] if failure_counts else "none",
        "provider_usage": _provider_usage(training),
        "virtual_projection_enabled": bool(
            operator.get(
                "virtual_projection_enabled",
                governance.get("virtual_projection_enabled", False),
            )
        ),
        "survival_curve": _survival_curve(
            training=training,
            phase16=phase16,
            phase17=phase17,
            phase18=phase18,
            governance=governance,
        ),
        "reports_dir": str(reports),
    }
    (reports / "phase26_run_summary.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def _aggregate(runs: list[dict[str, Any]], campaign_root: Path) -> dict[str, Any]:
    failure_counts: Counter[str] = Counter()
    lifecycle_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    survival_totals: Counter[str] = Counter()
    for run in runs:
        failure_counts.update(run.get("failure_distribution", {}))
        lifecycle_counts.update(run.get("promotion_counts", {}))
        provider_counts.update(run.get("provider_usage", {}))
        survival_totals.update(run.get("survival_curve", {}))
    scores = [float(run.get("average_promotion_score", 0.0)) for run in runs if not run.get("error")]
    centrality = [float(run.get("centrality_average", 0.0)) for run in runs if not run.get("error")]
    projection = [
        float(run.get("projected_centrality_average", 0.0)) for run in runs if not run.get("error")
    ]
    return {
        "run_id": f"phase26_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "campaign_root": str(campaign_root),
        "canonical_merge_performed": False,
        "run_count": len(runs),
        "completed_run_count": sum(1 for run in runs if not run.get("error")),
        "runs": runs,
        "aggregate_failure_distribution": dict(failure_counts.most_common()),
        "aggregate_lifecycle_distribution": dict(lifecycle_counts.most_common()),
        "aggregate_provider_usage": dict(provider_counts.most_common()),
        "aggregate_survival_curve": dict(survival_totals),
        "average_promotion_score": _mean(scores),
        "average_relationship_centrality": _mean(centrality),
        "average_projected_centrality": _mean(projection),
        "promotion_eligible_total": lifecycle_counts.get("Promotion Eligible", 0),
        "validated_total": lifecycle_counts.get("Validated", 0),
        "candidate_total": lifecycle_counts.get("Candidate", 0),
        "rejected_total": lifecycle_counts.get("Reject", 0),
    }


def _write_reports(aggregate: dict[str, Any], reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase26_autonomous_campaign_report.json").write_text(
        json.dumps(_jsonable(aggregate), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    runs = aggregate["runs"]
    run_rows = [
        (
            f"| {run['run']} | {run['cycles_completed']}/{run['cycles_requested']} | "
            f"{','.join(run['profiles'])} | {run['semantic_growth']} | "
            f"{run['prediction_coverage']} | {run['failed_predictions']} | "
            f"{run['average_promotion_score']} | {run['promotion_eligible']} | "
            f"{run['validated_concepts']} | {run['centrality_average']} | "
            f"{run['dominant_failure']} |"
        )
        for run in runs
    ]
    survival_rows = [
        f"| {name} | {count} |"
        for name, count in aggregate["aggregate_survival_curve"].items()
    ]
    report = [
        "# Phase 26 Autonomous Curriculum Validation Campaign",
        "",
        "Canonical knowledge was not modified. Each campaign used a fresh isolated store and the existing continuous operator pipeline.",
        "",
        "## Executive Summary",
        "",
        f"- Runs completed: `{aggregate['completed_run_count']}` of `{aggregate['run_count']}`",
        f"- Average promotion score: `{aggregate['average_promotion_score']}`",
        f"- Average projected centrality: `{aggregate['average_projected_centrality']}`",
        f"- Promotion eligible concepts: `{aggregate['promotion_eligible_total']}`",
        f"- Validated concepts: `{aggregate['validated_total']}`",
        f"- Dominant aggregate failure: `{next(iter(aggregate['aggregate_failure_distribution']), 'none')}`",
        "",
        "## Experiment Chronology",
        "",
        "| Run | Cycles | Profiles | Semantic Growth | Prediction Coverage | Failed Predictions | Avg Promotion Score | Eligible | Validated | Centrality | Dominant Failure |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        *run_rows,
        "",
        "## Aggregate Survival Curve",
        "",
        "| Stage | Count |",
        "| --- | ---: |",
        *survival_rows,
        "",
        "## Failure Distribution",
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
        "## Provider Usage",
        "",
        *[
            f"- `{provider}`: `{count}` cycles"
            for provider, count in aggregate["aggregate_provider_usage"].items()
        ],
        "",
        "## Recommendation",
        "",
        _recommend_next_direction(aggregate),
        "",
    ]
    (reports_dir / "phase26_autonomous_campaign_report.md").write_text(
        "\n".join(report),
        encoding="utf-8",
    )
    (reports_dir / "phase26_survival_curves.md").write_text(
        "\n".join(
            [
                "# Phase 26 Survival Curves",
                "",
                "| Run | Extracted | Evaluated | Validated Predictions | Survived Governance | Promotion Candidates | Eligible |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
                *[
                    (
                        f"| {run['run']} | {run['survival_curve']['extracted_candidates']} | "
                        f"{run['survival_curve']['semantic_records_evaluated']} | "
                        f"{run['survival_curve']['predictions_validated']} | "
                        f"{run['survival_curve']['survived_governance']} | "
                        f"{run['survival_curve']['promotion_candidates']} | "
                        f"{run['survival_curve']['promotion_eligible']} |"
                    )
                    for run in runs
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phase26_promotion_trends.md").write_text(
        "\n".join(
            [
                "# Phase 26 Promotion Trends",
                "",
                *[
                    (
                        f"- `{run['run']}`: avg score `{run['average_promotion_score']}`, "
                        f"max `{run['promotion_score_max']}`, counts `{run['promotion_counts']}`"
                    )
                    for run in runs
                ],
                "",
                "No canonical promotion was performed.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phase26_governance_trends.md").write_text(
        "\n".join(
            [
                "# Phase 26 Governance Trends",
                "",
                *[
                    (
                        f"- `{run['run']}`: centrality `{run['centrality_average']}`, "
                        f"projected centrality `{run['projected_centrality_average']}`, "
                        f"artifact `{run['artifact_rate']}`, incomplete `{run['incomplete_rate']}`, "
                        f"redundancy `{run['redundancy_average']}`"
                    )
                    for run in runs
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )


def _recommend_next_direction(aggregate: dict[str, Any]) -> str:
    if aggregate["promotion_eligible_total"] > 0:
        return (
            "Inspect promotion-eligible concepts manually before any canonical merge. "
            "Do not loosen governance; verify provenance and survival first."
        )
    top_failure = next(iter(aggregate["aggregate_failure_distribution"]), "none")
    if top_failure in {"unresolved_prediction", "insufficient_evidence"}:
        return (
            "The next justified investigation is validation/evidence throughput: "
            "concepts are being generated faster than evidence resolves them."
        )
    if top_failure == "low_centrality":
        return (
            "The next justified investigation is whether recurring concepts need "
            "stronger provenance linkage, not persistent semantic edge generation yet."
        )
    if top_failure in {"prompt_artifact", "incomplete_proposition"}:
        return (
            "Artifact or incompleteness regressed during broader operation. Revisit "
            "the deterministic boundary filter only with fresh examples."
        )
    return (
        "Continue bounded campaigns with one-variable curriculum changes; the current "
        "evidence does not justify a new architecture."
    )


def run_campaigns(
    *,
    campaign_root: Path,
    reports_dir: Path,
    deadline: datetime | None = None,
    max_campaigns: int | None = None,
) -> dict[str, Any]:
    campaign_root.mkdir(parents=True, exist_ok=True)
    completed: list[dict[str, Any]] = []
    for spec in DEFAULT_CAMPAIGNS[: max_campaigns or len(DEFAULT_CAMPAIGNS)]:
        if _deadline_reached(deadline):
            break
        run_dir = campaign_root / spec.name
        _safe_reset_dir(run_dir, campaign_root)
        store_root = run_dir / "store"
        run_reports = run_dir / "reports"
        started = time.perf_counter()
        error: str | None = None
        try:
            run_continuous_learning(
                store_root=store_root,
                reports_dir=run_reports,
                cycles=spec.cycles,
                objective_count=spec.objective_count,
                validation_limit=min(200, max(40, spec.cycles)),
                adversarial_limit=min(200, max(40, spec.cycles)),
                normalization_limit=min(120, max(40, spec.cycles // 2)),
                curriculum_profiles=spec.profiles,
                structured_output_contract=False,
                use_projection=True,
            )
        except Exception as exc:  # keep the campaign moving and preserve evidence.
            error = f"{type(exc).__name__}: {exc}"
        completed.append(_summarize_run(run_dir, spec, started, error))
        aggregate = _aggregate(completed, campaign_root)
        _write_reports(aggregate, reports_dir)
    aggregate = _aggregate(completed, campaign_root)
    _write_reports(aggregate, reports_dir)
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 26 autonomous bounded campaigns.")
    parser.add_argument(
        "--campaign-root",
        default=".tmp/experiments/phase26_autonomous_campaign",
    )
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument(
        "--deadline",
        default=None,
        help="Local time HH:MM after which no new campaign starts.",
    )
    parser.add_argument("--max-campaigns", type=int, default=None)
    args = parser.parse_args()
    summary = run_campaigns(
        campaign_root=Path(args.campaign_root),
        reports_dir=Path(args.reports_dir),
        deadline=_deadline_for_today(args.deadline),
        max_campaigns=args.max_campaigns,
    )
    print(
        json.dumps(
            {
                "run_count": summary["run_count"],
                "completed_run_count": summary["completed_run_count"],
                "average_promotion_score": summary["average_promotion_score"],
                "promotion_eligible_total": summary["promotion_eligible_total"],
                "top_failure": next(iter(summary["aggregate_failure_distribution"]), "none"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
