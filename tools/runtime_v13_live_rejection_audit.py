from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the rejected Runtime V1.3 recurring-noise live prototype.")
    parser.add_argument("--baseline-real", type=Path, required=True)
    parser.add_argument("--baseline-ranking", type=Path, required=True)
    parser.add_argument("--prototype-real", type=Path, required=True)
    parser.add_argument("--prototype-ranking", type=Path, required=True)
    parser.add_argument("--prototype-report", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    baseline_real = _load_json(args.baseline_real)
    baseline_ranking = _load_json(args.baseline_ranking)
    prototype_real = _load_json(args.prototype_real)
    prototype_ranking = _load_json(args.prototype_ranking)
    prototype_report = _load_json(args.prototype_report)
    audit = _audit(
        baseline_real=baseline_real,
        baseline_ranking=baseline_ranking,
        prototype_real=prototype_real,
        prototype_ranking=prototype_ranking,
        prototype_report=prototype_report,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_live_rejection_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_live_rejection_audit.md").write_text(
        _markdown(audit),
        encoding="utf-8",
    )
    return 0


def _audit(
    *,
    baseline_real: dict[str, Any],
    baseline_ranking: dict[str, Any],
    prototype_real: dict[str, Any],
    prototype_ranking: dict[str, Any],
    prototype_report: dict[str, Any],
) -> dict[str, Any]:
    baseline_cases = {case["name"]: case for case in baseline_real["cases"]}
    prototype_cases = {case["name"]: case for case in prototype_real["cases"]}
    baseline_rank_cases = {case["case"]: case for case in baseline_ranking["cases"]}
    prototype_rank_cases = {case["case"]: case for case in prototype_ranking["cases"]}
    per_case = []
    newly_used_noise_counter: Counter[str] = Counter()
    newly_used_counter: Counter[str] = Counter()
    no_longer_used_counter: Counter[str] = Counter()
    for case_name in sorted(baseline_cases):
        row = _audit_case(
            case_name=case_name,
            baseline=baseline_cases[case_name],
            prototype=prototype_cases[case_name],
            baseline_ranking=baseline_rank_cases.get(case_name, {}),
            prototype_ranking=prototype_rank_cases.get(case_name, {}),
        )
        per_case.append(row)
        newly_used_counter.update(row["newly_used_concepts"])
        no_longer_used_counter.update(row["no_longer_used_concepts"])
        newly_used_noise_counter.update(row["newly_used_noisy_concepts"])

    baseline_agg = baseline_real["aggregate"]
    prototype_agg = prototype_real["aggregate"]
    acceptance_failures = {
        key: value
        for key, value in prototype_report.get("acceptance_criteria", {}).items()
        if value is False
    }
    summary = {
        "read_only_verified": [baseline_real["read_only_verified"], prototype_real["read_only_verified"]],
        "grounding_score": [baseline_agg["grounding_score"], prototype_agg["grounding_score"]],
        "hallucinations": [baseline_agg["hallucinations"], prototype_agg["hallucinations"]],
        "retrieval_precision": [baseline_agg["retrieval_precision"], prototype_agg["retrieval_precision"]],
        "retrieval_recall": [baseline_agg["retrieval_recall"], prototype_agg["retrieval_recall"]],
        "attention_precision": [baseline_agg["attention_precision"], prototype_agg["attention_precision"]],
        "attention_recall": [baseline_agg["attention_recall"], prototype_agg["attention_recall"]],
        "noise_used_in_reasoning": [baseline_agg["noise_used_in_reasoning"], prototype_agg["noise_used_in_reasoning"]],
        "reasoning_drift_cases": [baseline_agg["reasoning_drift_cases"], prototype_agg["reasoning_drift_cases"]],
        "expected_outside_top10": [
            baseline_ranking["aggregate"]["expected_outside_top_10"],
            prototype_ranking["aggregate"]["expected_outside_top_10"],
        ],
        "expected_outside_top20": [
            baseline_ranking["aggregate"]["expected_outside_top_20"],
            prototype_ranking["aggregate"]["expected_outside_top_20"],
        ],
        "mean_expected_rank": [
            baseline_ranking["aggregate"]["mean_expected_rank"],
            prototype_ranking["aggregate"]["mean_expected_rank"],
        ],
        "mean_noise_above_expected": [
            baseline_ranking["aggregate"]["mean_noise_above_expected"],
            prototype_ranking["aggregate"]["mean_noise_above_expected"],
        ],
    }
    replacement_noise = _replacement_noise_analysis(per_case)
    conclusion = _conclusion(per_case, replacement_noise, acceptance_failures)
    return {
        "source_reports": {
            "baseline_real": "reports/runtime_v12_baseline_before_v13/runtime_v12_real_knowledge.json",
            "baseline_ranking": "reports/runtime_v12_baseline_before_v13/runtime_v12_activation_ranking_diagnostic.json",
            "prototype_real": "reports/runtime_v13_recurring_noise_live_raw/runtime_v12_real_knowledge.json",
            "prototype_ranking": "reports/runtime_v13_recurring_noise_live_raw/runtime_v12_activation_ranking_diagnostic.json",
            "prototype_report": "reports/runtime_v13_recurring_noise_live_prototype.json",
        },
        "summary": summary,
        "acceptance_criteria_failures": acceptance_failures,
        "per_case": per_case,
        "newly_used_concepts": newly_used_counter.most_common(),
        "newly_used_noisy_concepts": newly_used_noise_counter.most_common(),
        "no_longer_used_concepts": no_longer_used_counter.most_common(),
        "replacement_noise_analysis": replacement_noise,
        "why_isolated_passed_live_failed": (
            "The isolated simulation measured activation rank movement only. In live runtime, the altered activation distribution "
            "changed which candidates attention selected and reasoning consumed. Ranking improved, but selected replacement "
            "concepts were often noise, doubling noise_used_in_reasoning."
        ),
        "decision_assessment": {
            "abandoned": False,
            "diagnostic_only": True,
            "tiebreaker_only": False,
            "move_signal_to_attention_gating": True,
            "combined_with_usage_gating": True,
            "retested_with_stricter_cap": "not before attention/usage diagnostics",
        },
        "recommended_next_experiment": (
            "Test recurrence as attention-side diagnostic metadata or a reasoning usage gate, not as direct activation score mutation."
        ),
        "experiments_explicitly_rejected": [
            "direct activation-score recurring-noise suppression",
            "stronger recurrence penalty",
            "global attention threshold loosening",
            "learning/governance/promotion changes",
        ],
        "final_decision": conclusion,
    }


def _audit_case(
    *,
    case_name: str,
    baseline: dict[str, Any],
    prototype: dict[str, Any],
    baseline_ranking: dict[str, Any],
    prototype_ranking: dict[str, Any],
) -> dict[str, Any]:
    baseline_used = set(baseline["used_concepts"])
    prototype_used = set(prototype["used_concepts"])
    newly_used = sorted(prototype_used - baseline_used)
    no_longer_used = sorted(baseline_used - prototype_used)
    prototype_contrib = {item["concept_id"]: item for item in prototype["concept_contributions"]}
    baseline_contrib = {item["concept_id"]: item for item in baseline["concept_contributions"]}
    newly_used_noise = sorted(
        concept_id
        for concept_id in newly_used
        if prototype_contrib.get(concept_id, {}).get("classification") == "Noise"
    )
    no_longer_used_noise = sorted(
        concept_id
        for concept_id in no_longer_used
        if baseline_contrib.get(concept_id, {}).get("classification") == "Noise"
    )
    baseline_top10 = [item["concept_id"] for item in baseline_ranking.get("top_50", [])[:10]]
    prototype_top10 = [item["concept_id"] for item in prototype_ranking.get("top_50", [])[:10]]
    entered_top10 = sorted(set(prototype_top10) - set(baseline_top10))
    left_top10 = sorted(set(baseline_top10) - set(prototype_top10))
    return {
        "case": case_name,
        "category": baseline["category"],
        "noise_used_delta": prototype["noise_used_in_reasoning"] - baseline["noise_used_in_reasoning"],
        "attention_precision_delta": round(prototype["attention_precision"] - baseline["attention_precision"], 4),
        "reasoning_drift_before": baseline["runtime_decision"] == "Reasoning Drift",
        "reasoning_drift_after": prototype["runtime_decision"] == "Reasoning Drift",
        "baseline_noise_used": baseline["noise_used_in_reasoning"],
        "prototype_noise_used": prototype["noise_used_in_reasoning"],
        "baseline_attention_precision": baseline["attention_precision"],
        "prototype_attention_precision": prototype["attention_precision"],
        "newly_used_concepts": newly_used,
        "no_longer_used_concepts": no_longer_used,
        "newly_used_noisy_concepts": newly_used_noise,
        "no_longer_used_noisy_concepts": no_longer_used_noise,
        "entered_activation_top10": entered_top10,
        "left_activation_top10": left_top10,
        "newly_used_details": [
            _concept_use_detail(concept_id, prototype_contrib.get(concept_id, {}), prototype_ranking)
            for concept_id in newly_used
        ],
        "no_longer_used_details": [
            _concept_use_detail(concept_id, baseline_contrib.get(concept_id, {}), baseline_ranking)
            for concept_id in no_longer_used
        ],
    }


def _concept_use_detail(
    concept_id: str,
    contribution: dict[str, Any],
    ranking_case: dict[str, Any],
) -> dict[str, Any]:
    rank_item = next((item for item in ranking_case.get("top_50", []) if item["concept_id"] == concept_id), {})
    return {
        "concept_id": concept_id,
        "classification": contribution.get("classification", "Unknown"),
        "attended": contribution.get("attended"),
        "reasoned": contribution.get("reasoned"),
        "planned": contribution.get("planned"),
        "responded": contribution.get("responded"),
        "attention_classification": contribution.get("attention_classification"),
        "attention_score": contribution.get("attention_score"),
        "activation_rank": _rank_in_case(concept_id, ranking_case),
        "activation_score": rank_item.get("activation_score"),
        "role": rank_item.get("role"),
        "generic_terms": rank_item.get("generic_query_terms_matched", []),
        "query_overlap": rank_item.get("query_combined_overlap", []),
    }


def _rank_in_case(concept_id: str, ranking_case: dict[str, Any]) -> int | None:
    for index, item in enumerate(ranking_case.get("top_50", [])):
        if item["concept_id"] == concept_id:
            return index + 1
    return None


def _replacement_noise_analysis(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    increased_cases = [case for case in per_case if case["noise_used_delta"] > 0]
    entered_top10_noise = Counter(
        concept_id
        for case in increased_cases
        for concept_id in case["entered_activation_top10"]
    )
    newly_used_noise = Counter(
        concept_id
        for case in increased_cases
        for concept_id in case["newly_used_noisy_concepts"]
    )
    return {
        "cases_with_noise_increase": [case["case"] for case in increased_cases],
        "total_noise_delta": sum(case["noise_used_delta"] for case in per_case),
        "newly_used_noise_frequency": newly_used_noise.most_common(),
        "entered_top10_frequency": entered_top10_noise.most_common(),
        "interpretation": (
            "Recurring-noise suppression removed or demoted some repeat offenders, but the newly opened activation slots "
            "were filled by other weak candidates that attention treated as usable."
        ),
    }


def _conclusion(
    per_case: list[dict[str, Any]],
    replacement_noise: dict[str, Any],
    acceptance_failures: dict[str, Any],
) -> str:
    if acceptance_failures.get("noise_used_in_reasoning_not_increase") is False:
        if replacement_noise["total_noise_delta"] > 0:
            return "MOVE_SIGNAL_TO_ATTENTION_GATING"
        return "KEEP_RECURRING_NOISE_AS_DIAGNOSTIC_ONLY"
    if any(case["noise_used_delta"] > 0 for case in per_case):
        return "RUN_MORE_DIAGNOSTICS"
    return "RETEST_AS_TIEBREAKER_ONLY"


def _markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Live Rejection Audit",
        "",
        f"Final decision: `{audit['final_decision']}`",
        "",
        "## Baseline vs Rejected Prototype Summary",
        "",
        "| Metric | Baseline | Rejected Prototype |",
        "| --- | ---: | ---: |",
    ]
    for key, value in audit["summary"].items():
        lines.append(f"| {key} | `{value[0]}` | `{value[1]}` |")
    lines.extend(["", "## Acceptance Criteria Failures", ""])
    if not audit["acceptance_criteria_failures"]:
        lines.append("- none")
    for key in audit["acceptance_criteria_failures"]:
        lines.append(f"- `{key}`")
    lines.extend(
        [
            "",
            "## Per-Case Noise And Attention Deltas",
            "",
            "| Case | Noise Delta | Attention Precision Delta | Reasoning Drift Before | Reasoning Drift After |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for case in audit["per_case"]:
        lines.append(
            f"| {case['case']} | `{case['noise_used_delta']}` | `{case['attention_precision_delta']}` | "
            f"`{case['reasoning_drift_before']}` | `{case['reasoning_drift_after']}` |"
        )
    lines.extend(["", "## Newly Used Noisy Concepts", ""])
    if not audit["newly_used_noisy_concepts"]:
        lines.append("- none")
    for concept_id, count in audit["newly_used_noisy_concepts"]:
        lines.append(f"- `{concept_id}` used as noise in `{count}` case(s)")
    lines.extend(["", "## Suppressed Or No-Longer-Used Concepts", ""])
    if not audit["no_longer_used_concepts"]:
        lines.append("- none")
    for concept_id, count in audit["no_longer_used_concepts"]:
        lines.append(f"- `{concept_id}` no longer used in `{count}` case(s)")
    lines.extend(["", "## Replacement-Noise Analysis", "", audit["replacement_noise_analysis"]["interpretation"]])
    lines.append("")
    lines.append("Cases with noise increase:")
    for case in audit["replacement_noise_analysis"]["cases_with_noise_increase"]:
        lines.append(f"- `{case}`")
    lines.extend(
        [
            "",
            "## Why Isolated Simulation Passed But Live Benchmark Failed",
            "",
            audit["why_isolated_passed_live_failed"],
            "",
            "## Recommended Next Experiment",
            "",
            audit["recommended_next_experiment"],
            "",
            "## Experiments Explicitly Rejected",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in audit["experiments_explicitly_rejected"])
    lines.extend(["", f"`{audit['final_decision']}`", ""])
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input report: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
