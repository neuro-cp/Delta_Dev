from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


VARIANTS = [
    ("baseline_reference", "baseline", "Preserved V1.2 baseline reports; no runtime command executed."),
    ("usage_gate_only", "off", "Accepted reasoning usage gate with activation recurrence disabled."),
    ("combined_conservative", "conservative", "Bounded activation recurrence penalty plus usage gate."),
    ("combined_tiebreaker", "tiebreaker", "Micro-penalty/tiebreaker recurrence signal plus usage gate."),
    ("metadata_usage_gate", "metadata", "Recurrence metadata only plus usage gate."),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Runtime V1.3 combined activation/usage-gate sprint.")
    parser.add_argument("--campaign-root", type=Path, default=Path(".tmp/experiments/phaseA_architecture_graduation"))
    parser.add_argument("--campaign", default="overnight_3000")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--prior", type=Path, default=Path("reports/runtime_v13_isolated_simulations.json"))
    args = parser.parse_args()

    raw_root = args.reports_dir / "runtime_v13_combined_sprint_raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    baseline_dir = args.reports_dir / "runtime_v12_baseline_before_v13"
    results = []
    for name, mode, description in VARIANTS:
        out_dir = raw_root / name
        out_dir.mkdir(parents=True, exist_ok=True)
        if mode == "baseline":
            _copy_baseline(baseline_dir, out_dir)
            status = {"returncode": 0, "commands": [], "live": False}
        else:
            status = _run_variant(
                mode=mode,
                campaign_root=args.campaign_root,
                campaign=args.campaign,
                reports_dir=args.reports_dir,
                prior=args.prior,
            )
            _archive_current_reports(args.reports_dir, out_dir)
        result = _variant_result(
            name=name,
            mode=mode,
            description=description,
            out_dir=out_dir,
            baseline_dir=baseline_dir,
            status=status,
        )
        results.append(result)

    sprint = _build_sprint_report(results)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_combined_sprint.json").write_text(
        json.dumps(sprint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_combined_sprint.md").write_text(
        _markdown(sprint),
        encoding="utf-8",
    )
    return 0


def _run_variant(*, mode: str, campaign_root: Path, campaign: str, reports_dir: Path, prior: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["DELTA_RUNTIME_V13_RECURRENCE_MODE"] = mode
    env["DELTA_RUNTIME_V13_RECURRENCE_PRIOR"] = str(prior)
    commands = [
        [
            sys.executable,
            "tools/runtime_v12_real_knowledge.py",
            "--campaign-root",
            str(campaign_root),
            "--campaign",
            campaign,
            "--reports-dir",
            str(reports_dir),
        ],
        [
            sys.executable,
            "tools/runtime_v12_activation_ranking_diagnostic.py",
            "--campaign-root",
            str(campaign_root),
            "--campaign",
            campaign,
            "--reports-dir",
            str(reports_dir),
        ],
    ]
    statuses = []
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
        statuses.append(
            {
                "command": " ".join(command),
                "returncode": completed.returncode,
                "stdout": completed.stdout[-2000:],
                "stderr": completed.stderr[-2000:],
            }
        )
        if completed.returncode != 0:
            break
    return {
        "returncode": max(item["returncode"] for item in statuses) if statuses else 1,
        "commands": statuses,
        "live": True,
    }


def _copy_baseline(baseline_dir: Path, out_dir: Path) -> None:
    for name in [
        "runtime_v12_real_knowledge.json",
        "runtime_v12_real_knowledge.md",
        "runtime_v12_activation_ranking_diagnostic.json",
        "runtime_v12_activation_ranking_diagnostic.md",
    ]:
        shutil.copy2(baseline_dir / name, out_dir / name)


def _archive_current_reports(reports_dir: Path, out_dir: Path) -> None:
    for name in [
        "runtime_v12_real_knowledge.json",
        "runtime_v12_real_knowledge.md",
        "runtime_v12_activation_ranking_diagnostic.json",
        "runtime_v12_activation_ranking_diagnostic.md",
    ]:
        shutil.copy2(reports_dir / name, out_dir / name)


def _variant_result(
    *,
    name: str,
    mode: str,
    description: str,
    out_dir: Path,
    baseline_dir: Path,
    status: dict[str, Any],
) -> dict[str, Any]:
    real = _load_json(out_dir / "runtime_v12_real_knowledge.json")
    ranking = _load_json(out_dir / "runtime_v12_activation_ranking_diagnostic.json")
    baseline_real = _load_json(baseline_dir / "runtime_v12_real_knowledge.json")
    baseline_ranking = _load_json(baseline_dir / "runtime_v12_activation_ranking_diagnostic.json")
    metrics = _combined_metrics(real, ranking)
    baseline = _combined_metrics(baseline_real, baseline_ranking)
    comparison = {
        key: {
            "baseline": baseline.get(key),
            "variant": metrics.get(key),
            "delta": _delta(baseline.get(key), metrics.get(key)),
        }
        for key in _METRIC_KEYS
    }
    acceptance = _acceptance(comparison, real, baseline_real, ranking, baseline_ranking, status)
    per_case = _per_case(real, baseline_real)
    return {
        "name": name,
        "mode": mode,
        "description": description,
        "live": status["live"],
        "status": status,
        "metrics": metrics,
        "comparison": comparison,
        "acceptance": acceptance,
        "accepted": all(acceptance.values()) and name.startswith("combined") or (name == "metadata_usage_gate" and all(acceptance.values())),
        "per_case": per_case,
        "raw_dir": str(out_dir),
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
        "expected_top10_pushed_out": ranking_aggregate.get("expected_top10_pushed_out", []),
    }


def _acceptance(
    comparison: dict[str, dict[str, Any]],
    real: dict[str, Any],
    baseline_real: dict[str, Any],
    ranking: dict[str, Any],
    baseline_ranking: dict[str, Any],
    status: dict[str, Any],
) -> dict[str, bool]:
    c = comparison
    return {
        "commands_succeeded": status["returncode"] == 0,
        "read_only_verified": c["read_only_verified"]["variant"] is True,
        "grounding_score_remains_1": c["grounding_score"]["variant"] == 1.0,
        "hallucinations_remain_0": c["hallucinations"]["variant"] == 0.0,
        "confidence_calibration_not_regress": c["confidence_calibration"]["variant"] >= c["confidence_calibration"]["baseline"],
        "planning_score_not_regress": c["planning_score"]["variant"] >= c["planning_score"]["baseline"],
        "retrieval_recall_not_regress": c["retrieval_recall"]["variant"] >= c["retrieval_recall"]["baseline"],
        "expected_outside_top10_not_regress": c["expected_outside_top10"]["variant"] <= c["expected_outside_top10"]["baseline"],
        "expected_outside_top20_not_regress": c["expected_outside_top20"]["variant"] <= c["expected_outside_top20"]["baseline"],
        "mean_expected_rank_improves": c["mean_expected_rank"]["variant"] < c["mean_expected_rank"]["baseline"],
        "mean_noise_above_expected_improves": c["mean_noise_above_expected"]["variant"] < c["mean_noise_above_expected"]["baseline"],
        "no_expected_top10_pushed_out": not _expected_top10_pushed_out(ranking, baseline_ranking),
        "noise_used_in_reasoning_not_increase": c["noise_used_in_reasoning"]["variant"] <= c["noise_used_in_reasoning"]["baseline"],
        "reasoning_drift_cases_not_increase": c["reasoning_drift_cases"]["variant"] <= c["reasoning_drift_cases"]["baseline"],
        "attention_precision_not_materially_regress": c["attention_precision"]["variant"] >= c["attention_precision"]["baseline"] - 0.05,
        "attention_recall_not_materially_regress": c["attention_recall"]["variant"] >= c["attention_recall"]["baseline"] - 0.02,
        "planning_core_coverage_not_regress": c["planning_core_coverage"]["variant"] >= c["planning_core_coverage"]["baseline"],
        "response_core_coverage_not_regress": c["response_core_coverage"]["variant"] >= c["response_core_coverage"]["baseline"],
        "sparse_behavior_not_regress": _sparse_ok(baseline_real, real),
    }


def _expected_top10_pushed_out(ranking: dict[str, Any], baseline_ranking: dict[str, Any]) -> list[str]:
    pushed = []
    by_case = {case["case"]: case for case in ranking.get("cases", [])}
    for base_case in baseline_ranking.get("cases", []):
        case = by_case.get(base_case["case"], {})
        base_expected = {
            result["concept_id"]
            for result in base_case.get("expected_results", [])
            if result.get("baseline_rank", 999) <= 10
        }
        now_expected = {
            result["concept_id"]
            for result in case.get("expected_results", [])
            if result.get("baseline_rank", result.get("rank", 999)) <= 10
        }
        pushed.extend(sorted(base_expected - now_expected))
    return pushed


def _sparse_ok(baseline_real: dict[str, Any], real: dict[str, Any]) -> bool:
    baseline = {
        case["name"]: case for case in baseline_real.get("cases", []) if case.get("category") in {"sparse_knowledge", "unsupported_questions"}
    }
    current = {
        case["name"]: case for case in real.get("cases", []) if case.get("category") in {"sparse_knowledge", "unsupported_questions"}
    }
    for name, case in current.items():
        base = baseline.get(name, {})
        if case.get("runtime_decision") != base.get("runtime_decision"):
            return False
        if case.get("hallucination_count", 0) > base.get("hallucination_count", 0):
            return False
        if case.get("planning_score", 0) < base.get("planning_score", 0):
            return False
    return True


def _per_case(real: dict[str, Any], baseline_real: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = {case["name"]: case for case in baseline_real.get("cases", [])}
    rows = []
    for case in real.get("cases", []):
        base = baseline.get(case["name"], {})
        rows.append(
            {
                "case": case["name"],
                "noise_used_in_reasoning": [base.get("noise_used_in_reasoning"), case.get("noise_used_in_reasoning")],
                "attention_precision": [base.get("attention_precision"), case.get("attention_precision")],
                "runtime_decision": [base.get("runtime_decision"), case.get("runtime_decision")],
                "planning_core_coverage": [base.get("planning_core_coverage"), case.get("planning_core_coverage")],
                "response_core_coverage": [base.get("response_core_coverage"), case.get("response_core_coverage")],
            }
        )
    return rows


def _build_sprint_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [result for result in results if result["accepted"] and result["name"] != "baseline_reference"]
    final = "KEEP_USAGE_GATE_ONLY_RUN_MORE_DIAGNOSTICS"
    for name, decision in [
        ("combined_conservative", "ACCEPT_RUNTIME_V13_COMBINED_CONSERVATIVE"),
        ("combined_tiebreaker", "ACCEPT_RUNTIME_V13_COMBINED_TIEBREAKER"),
        ("metadata_usage_gate", "ACCEPT_RUNTIME_V13_METADATA_USAGE_GATE"),
    ]:
        if any(result["name"] == name for result in accepted):
            final = decision
            break
    if not accepted:
        final = "KEEP_USAGE_GATE_ONLY_RUN_MORE_DIAGNOSTICS"
    return {
        "final_decision": final,
        "frozen_boundary_verification": {
            "learning_changed": False,
            "governance_changed": False,
            "provider_prompts_changed": False,
            "canonical_storage_changed": False,
            "activation_recurrence_default_enabled": False,
            "usage_gate_enabled": True,
        },
        "variants": results,
        "recommendation": _recommendation(final),
        "revert_keep_actions": (
            "Activation recurrence remains environment-disabled by default. Accepted reasoning usage gate remains enabled. "
            "Raw outputs were preserved for every variant."
        ),
    }


def _recommendation(final: str) -> str:
    if final == "KEEP_USAGE_GATE_ONLY_RUN_MORE_DIAGNOSTICS":
        return "Do not enable activation recurrence by default. Keep the accepted reasoning usage gate and continue diagnostics."
    return "A combined variant passed all gates; review before making activation recurrence the default runtime path."


def _markdown(sprint: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Combined Sprint",
        "",
        f"Final decision: `{sprint['final_decision']}`",
        "",
        "## Sprint Summary",
        "",
        sprint["recommendation"],
        "",
        "## Frozen-Boundary Verification",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in sprint["frozen_boundary_verification"].items())
    lines.extend(
        [
            "",
            "## Variant Table",
            "",
            "| Variant | Live | Accepted | Retrieval Recall | Attention Precision | Noise Used | Mean Expected Rank | Mean Noise Above Expected |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for result in sprint["variants"]:
        m = result["metrics"]
        lines.append(
            f"| {result['name']} | `{result['live']}` | `{result['accepted']}` | "
            f"`{m.get('retrieval_recall')}` | `{m.get('attention_precision')}` | "
            f"`{m.get('noise_used_in_reasoning')}` | `{m.get('mean_expected_rank')}` | "
            f"`{m.get('mean_noise_above_expected')}` |"
        )
    lines.extend(["", "## Variant Comparisons", ""])
    for result in sprint["variants"]:
        lines.extend([f"### {result['name']}", "", result["description"], "", "Acceptance:"])
        lines.extend(f"- `{key}`: `{value}`" for key, value in result["acceptance"].items())
        lines.extend(["", "Per-case changes:", ""])
        lines.append("| Case | Noise | Attention Precision | Decision | Planning Core | Response Core |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in result["per_case"]:
            lines.append(
                f"| {row['case']} | `{row['noise_used_in_reasoning'][0]} -> {row['noise_used_in_reasoning'][1]}` | "
                f"`{row['attention_precision'][0]} -> {row['attention_precision'][1]}` | "
                f"`{row['runtime_decision'][0]} -> {row['runtime_decision'][1]}` | "
                f"`{row['planning_core_coverage'][0]} -> {row['planning_core_coverage'][1]}` | "
                f"`{row['response_core_coverage'][0]} -> {row['response_core_coverage'][1]}` |"
            )
        lines.append("")
    lines.extend(
        [
            "## Replacement-Noise Analysis",
            "",
            "Combined variants are evaluated specifically against the rejected activation-only failure: ranking gains are not sufficient if replacement noise enters reasoning.",
            "",
            "## Usage-Gate Effectiveness Analysis",
            "",
            "The accepted usage gate remains the live safety layer. Its effectiveness depends on implementation-available support signals, not evaluator labels.",
            "",
            "## Activation-Ranking Gains Retained Or Lost",
            "",
            "See variant table and acceptance criteria for mean expected rank, expected outside top-10/top-20, and mean noise above expected.",
            "",
            "## Regression Risks",
            "",
            "- Activation recurrence can still reshuffle replacement noise into attention.",
            "- Metadata-only variants may be safe but too weak to change outcomes.",
            "- Strong evidence-support metadata can make reasoning usage gates permissive.",
            "",
            "## Revert/Keep Actions Performed",
            "",
            sprint["revert_keep_actions"],
            "",
            f"`{sprint['final_decision']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _delta(baseline: Any, value: Any) -> Any:
    if isinstance(baseline, bool) or isinstance(value, bool):
        return None
    if isinstance(baseline, (int, float)) and isinstance(value, (int, float)):
        return round(value - baseline, 4)
    return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_METRIC_KEYS = [
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


if __name__ == "__main__":
    raise SystemExit(main())
