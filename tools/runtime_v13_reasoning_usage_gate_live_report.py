from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRICS = [
    "read_only_verified",
    "grounding_score",
    "hallucinations",
    "confidence_calibration",
    "planning_score",
    "retrieval_precision",
    "retrieval_recall",
    "attention_precision",
    "attention_recall",
    "noise_used_in_reasoning",
    "reasoning_drift_cases",
    "planning_drift_cases",
    "response_drift_cases",
    "working_memory_efficiency",
    "planning_core_coverage",
    "response_core_coverage",
    "expected_outside_top10",
    "expected_outside_top20",
    "mean_expected_rank",
    "mean_noise_above_expected",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Runtime V1.3 reasoning usage-gate live prototype results.")
    parser.add_argument("--baseline-real", type=Path, required=True)
    parser.add_argument("--baseline-ranking", type=Path, required=True)
    parser.add_argument("--live-real", type=Path, required=True)
    parser.add_argument("--live-ranking", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    baseline_real = _load_json(args.baseline_real)
    baseline_ranking = _load_json(args.baseline_ranking)
    live_real = _load_json(args.live_real)
    live_ranking = _load_json(args.live_ranking)
    report = build_report(
        baseline_real=baseline_real,
        baseline_ranking=baseline_ranking,
        live_real=live_real,
        live_ranking=live_ranking,
    )
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_reasoning_usage_gate_live_prototype.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_reasoning_usage_gate_live_prototype.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    return 0


def build_report(
    *,
    baseline_real: dict[str, Any],
    baseline_ranking: dict[str, Any],
    live_real: dict[str, Any],
    live_ranking: dict[str, Any],
) -> dict[str, Any]:
    baseline = _combined_metrics(baseline_real, baseline_ranking)
    live = _combined_metrics(live_real, live_ranking)
    comparison = {
        key: {
            "baseline": baseline.get(key),
            "live_usage_gate": live.get(key),
            "delta": _delta(baseline.get(key), live.get(key)),
        }
        for key in METRICS
    }
    acceptance = {
        "read_only_verified_remains_true": live.get("read_only_verified") is True,
        "grounding_score_remains_1": live.get("grounding_score") == 1.0,
        "hallucinations_remain_0": live.get("hallucinations") == 0.0,
        "confidence_calibration_not_regress": live.get("confidence_calibration", 0) >= baseline.get("confidence_calibration", 0),
        "planning_score_not_regress": live.get("planning_score", 0) >= baseline.get("planning_score", 0),
        "noise_used_in_reasoning_not_increase": live.get("noise_used_in_reasoning", 999) <= baseline.get("noise_used_in_reasoning", -1),
        "reasoning_drift_cases_not_increase": live.get("reasoning_drift_cases", 999) <= baseline.get("reasoning_drift_cases", -1),
        "attention_recall_not_materially_regress": live.get("attention_recall", 0) >= baseline.get("attention_recall", 0) - 0.02,
        "planning_core_coverage_not_regress": live.get("planning_core_coverage", 0) >= baseline.get("planning_core_coverage", 0),
        "response_core_coverage_not_regress": live.get("response_core_coverage", 0) >= baseline.get("response_core_coverage", 0),
        "sparse_behavior_not_regress": _sparse_ok(baseline_real, live_real),
    }
    changed_metrics = [
        key
        for key in METRICS
        if comparison[key]["delta"] not in (0, 0.0, None)
    ]
    final = (
        "ACCEPT_RUNTIME_V13_REASONING_USAGE_GATE"
        if all(acceptance.values())
        else "REJECT_LIVE_REASONING_USAGE_GATE"
    )
    if all(acceptance.values()) and not changed_metrics:
        interpretation = (
            "The live usage gate is safe against the restored V1.2 baseline but dormant on this activation path; "
            "it did not improve or regress aggregate metrics because current baseline candidates carry sufficient "
            "runtime support metadata to pass the gate."
        )
    elif all(acceptance.values()):
        interpretation = "The live usage gate passed acceptance criteria with measurable metric movement."
    else:
        interpretation = "The live usage gate failed at least one acceptance criterion and should be reverted."
    return {
        "final_decision": final,
        "comparison": comparison,
        "acceptance_criteria": acceptance,
        "changed_metrics": changed_metrics,
        "interpretation": interpretation,
        "raw_outputs": "reports/runtime_v13_reasoning_usage_gate_live_raw",
    }


def _combined_metrics(real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    aggregate = dict(real.get("aggregate", {}))
    ranking_aggregate = ranking.get("aggregate", {})
    return {
        **aggregate,
        "read_only_verified": real.get("read_only_verified"),
        "expected_outside_top10": ranking_aggregate.get("expected_outside_top_10"),
        "expected_outside_top20": ranking_aggregate.get("expected_outside_top_20"),
        "mean_expected_rank": ranking_aggregate.get("mean_expected_rank"),
        "mean_noise_above_expected": ranking_aggregate.get("mean_noise_above_expected"),
    }


def _sparse_ok(baseline_real: dict[str, Any], live_real: dict[str, Any]) -> bool:
    baseline_sparse = {
        case["name"]: case
        for case in baseline_real.get("cases", [])
        if case.get("category") in {"sparse_knowledge", "unsupported_questions"}
    }
    live_sparse = {
        case["name"]: case
        for case in live_real.get("cases", [])
        if case.get("category") in {"sparse_knowledge", "unsupported_questions"}
    }
    for name, live_case in live_sparse.items():
        baseline_case = baseline_sparse.get(name, {})
        if live_case.get("runtime_decision") != baseline_case.get("runtime_decision"):
            return False
        if live_case.get("hallucination_count", 0) > baseline_case.get("hallucination_count", 0):
            return False
        if live_case.get("planning_score", 0) < baseline_case.get("planning_score", 0):
            return False
    return True


def _delta(baseline: Any, live: Any) -> Any:
    if isinstance(baseline, bool) or isinstance(live, bool):
        return None
    if isinstance(baseline, (int, float)) and isinstance(live, (int, float)):
        return round(live - baseline, 4)
    return None


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Reasoning Usage-Gate Live Prototype",
        "",
        f"Final decision: `{report['final_decision']}`",
        "",
        report["interpretation"],
        "",
        "## Baseline vs Live Usage-Gate Prototype",
        "",
        "| Metric | V1.2 Baseline | Live Usage Gate | Delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key, values in report["comparison"].items():
        lines.append(f"| {key} | `{values['baseline']}` | `{values['live_usage_gate']}` | `{values['delta']}` |")
    lines.extend(["", "## Acceptance Criteria", ""])
    for key, value in report["acceptance_criteria"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Raw Outputs",
            "",
            f"- `{report['raw_outputs']}`",
            "",
            f"`{report['final_decision']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input report: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
