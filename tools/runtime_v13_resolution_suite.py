from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

VARIANTS = [
    {
        "name": "baseline_reference",
        "description": "Preserved V1.2 baseline reports.",
        "live": False,
        "usage_gate_mode": None,
        "recurrence_mode": None,
    },
    {
        "name": "usage_gate_standard",
        "description": "Accepted usage gate, activation recurrence disabled.",
        "live": True,
        "usage_gate_mode": "standard",
        "recurrence_mode": "off",
    },
    {
        "name": "strict_context_usage_gate",
        "description": "Usage gate treats evidence_support as query-contextual only with specific overlap.",
        "live": True,
        "usage_gate_mode": "strict_context",
        "recurrence_mode": "off",
    },
    {
        "name": "citation_context_usage_gate",
        "description": "Middle-ground usage gate requiring stronger contextual support for citation-like use.",
        "live": True,
        "usage_gate_mode": "citation_context",
        "recurrence_mode": "off",
    },
    {
        "name": "conservative_recurrence_strict_gate",
        "description": "Conservative activation recurrence plus strict contextual usage gate.",
        "live": True,
        "usage_gate_mode": "strict_context",
        "recurrence_mode": "conservative",
    },
    {
        "name": "tiebreaker_recurrence_strict_gate",
        "description": "Tiebreaker activation recurrence plus strict contextual usage gate.",
        "live": True,
        "usage_gate_mode": "strict_context",
        "recurrence_mode": "tiebreaker",
    },
    {
        "name": "metadata_recurrence_strict_gate",
        "description": "Recurrence metadata only plus strict contextual usage gate.",
        "live": True,
        "usage_gate_mode": "strict_context",
        "recurrence_mode": "metadata",
    },
]

METRIC_KEYS = [
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
    "pass_rate",
    "expected_outside_top10",
    "expected_outside_top20",
    "mean_expected_rank",
    "mean_noise_above_expected",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Runtime V1.3 resolution suite.")
    parser.add_argument("--campaign-root", type=Path, default=Path(".tmp/experiments/phaseA_architecture_graduation"))
    parser.add_argument("--campaign", default="overnight_3000")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--prior", type=Path, default=Path("reports/runtime_v13_isolated_simulations.json"))
    args = parser.parse_args()

    raw_root = args.reports_dir / "runtime_v13_resolution_suite_raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    baseline_dir = args.reports_dir / "runtime_v12_baseline_before_v13"
    results = []
    for variant in VARIANTS:
        out_dir = raw_root / variant["name"]
        out_dir.mkdir(parents=True, exist_ok=True)
        if variant["live"]:
            status = _run_variant(
                variant=variant,
                campaign_root=args.campaign_root,
                campaign=args.campaign,
                reports_dir=args.reports_dir,
                prior=args.prior,
            )
            _archive(args.reports_dir, out_dir)
        else:
            status = {"returncode": 0, "commands": [], "live": False}
            _copy_baseline(baseline_dir, out_dir)
        results.append(_variant_result(variant=variant, out_dir=out_dir, baseline_dir=baseline_dir, status=status))

    audit = _evidence_support_audit(results)
    suite = _suite_report(results=results, audit=audit)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_evidence_support_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_evidence_support_audit.md").write_text(_audit_markdown(audit), encoding="utf-8")
    (args.reports_dir / "runtime_v13_resolution_suite.json").write_text(
        json.dumps(suite, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_resolution_suite.md").write_text(_suite_markdown(suite), encoding="utf-8")
    return 0


def _run_variant(*, variant: dict[str, Any], campaign_root: Path, campaign: str, reports_dir: Path, prior: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["DELTA_RUNTIME_V13_USAGE_GATE_MODE"] = str(variant["usage_gate_mode"])
    env["DELTA_RUNTIME_V13_RECURRENCE_MODE"] = str(variant["recurrence_mode"])
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
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
        statuses.append(
            {
                "command": " ".join(command),
                "returncode": completed.returncode,
                "stdout": completed.stdout[-2000:],
                "stderr": completed.stderr[-2000:],
            }
        )
        if completed.returncode:
            break
    return {"returncode": max(item["returncode"] for item in statuses), "commands": statuses, "live": True}


def _copy_baseline(baseline_dir: Path, out_dir: Path) -> None:
    for name in _REPORT_FILES:
        shutil.copy2(baseline_dir / name, out_dir / name)


def _archive(reports_dir: Path, out_dir: Path) -> None:
    for name in _REPORT_FILES:
        shutil.copy2(reports_dir / name, out_dir / name)


def _variant_result(*, variant: dict[str, Any], out_dir: Path, baseline_dir: Path, status: dict[str, Any]) -> dict[str, Any]:
    real = _load_json(out_dir / "runtime_v12_real_knowledge.json")
    ranking = _load_json(out_dir / "runtime_v12_activation_ranking_diagnostic.json")
    baseline_real = _load_json(baseline_dir / "runtime_v12_real_knowledge.json")
    baseline_ranking = _load_json(baseline_dir / "runtime_v12_activation_ranking_diagnostic.json")
    metrics = _combined(real, ranking)
    baseline = _combined(baseline_real, baseline_ranking)
    comparison = {
        key: {"baseline": baseline.get(key), "variant": metrics.get(key), "delta": _delta(baseline.get(key), metrics.get(key))}
        for key in METRIC_KEYS
    }
    acceptance = _acceptance(comparison, baseline_real, real, baseline_ranking, ranking, status)
    return {
        **variant,
        "raw_dir": str(out_dir),
        "status": status,
        "metrics": metrics,
        "comparison": comparison,
        "acceptance": acceptance,
        "accepted": variant["live"] and all(acceptance.values()),
        "per_case": _per_case(baseline_real, real),
        "gated_evidence_count": _gated_evidence_count(out_dir),
    }


def _combined(real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
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


def _acceptance(
    comparison: dict[str, dict[str, Any]],
    baseline_real: dict[str, Any],
    real: dict[str, Any],
    baseline_ranking: dict[str, Any],
    ranking: dict[str, Any],
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
        "noise_used_in_reasoning_not_increase": c["noise_used_in_reasoning"]["variant"] <= c["noise_used_in_reasoning"]["baseline"],
        "reasoning_drift_cases_not_increase": c["reasoning_drift_cases"]["variant"] <= c["reasoning_drift_cases"]["baseline"],
        "planning_drift_cases_not_increase": c["planning_drift_cases"]["variant"] <= c["planning_drift_cases"]["baseline"],
        "response_drift_cases_not_increase": c["response_drift_cases"]["variant"] <= c["response_drift_cases"]["baseline"],
        "planning_core_coverage_not_regress": c["planning_core_coverage"]["variant"] >= c["planning_core_coverage"]["baseline"],
        "response_core_coverage_not_regress": c["response_core_coverage"]["variant"] >= c["response_core_coverage"]["baseline"],
        "retrieval_recall_not_regress": c["retrieval_recall"]["variant"] >= c["retrieval_recall"]["baseline"],
        "expected_outside_top10_not_regress": c["expected_outside_top10"]["variant"] <= c["expected_outside_top10"]["baseline"],
        "expected_outside_top20_not_regress": c["expected_outside_top20"]["variant"] <= c["expected_outside_top20"]["baseline"],
        "mean_expected_rank_not_materially_regress": c["mean_expected_rank"]["variant"] <= c["mean_expected_rank"]["baseline"] + 0.25,
        "mean_noise_above_expected_not_materially_regress": c["mean_noise_above_expected"]["variant"] <= c["mean_noise_above_expected"]["baseline"] + 0.25,
        "sparse_behavior_not_regress": _sparse_ok(baseline_real, real),
        "expected_top10_not_pushed_out": not _expected_top10_pushed_out(baseline_ranking, ranking),
    }


def _per_case(baseline_real: dict[str, Any], real: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = {case["name"]: case for case in baseline_real.get("cases", [])}
    rows = []
    for case in real.get("cases", []):
        base = baseline.get(case["name"], {})
        rows.append(
            {
                "case": case["name"],
                "noise_used_in_reasoning": [base.get("noise_used_in_reasoning"), case.get("noise_used_in_reasoning")],
                "attention_precision": [base.get("attention_precision"), case.get("attention_precision")],
                "decision": [base.get("runtime_decision"), case.get("runtime_decision")],
                "planning_core_coverage": [base.get("planning_core_coverage"), case.get("planning_core_coverage")],
                "response_core_coverage": [base.get("response_core_coverage"), case.get("response_core_coverage")],
            }
        )
    return rows


def _evidence_support_audit(results: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = next(result for result in results if result["name"] == "baseline_reference")
    baseline_real = _load_json(Path(baseline["raw_dir"]) / "runtime_v12_real_knowledge.json")
    noisy_reasoned = []
    high_support_noise = []
    class_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    for case in baseline_real.get("cases", []):
        for contribution in case.get("concept_contributions", []):
            if contribution.get("classification") == "Noise" and contribution.get("reasoned"):
                noisy_reasoned.append({"case": case["name"], **contribution})
                class_counts[contribution.get("attention_classification", "Unknown")] += 1
                if contribution.get("attention_score", 0) >= 0.35:
                    high_support_noise.append({"case": case["name"], **contribution})
    for result in results:
        decision_counts[result["name"]] = int(result["metrics"].get("noise_used_in_reasoning", 0))
    final = "PROCEED_USAGE_GATE_REFINEMENT" if high_support_noise else "RUN_MORE_DIAGNOSTICS"
    return {
        "final_decision": final,
        "noisy_reasoned_count": len(noisy_reasoned),
        "high_attention_noisy_reasoned_count": len(high_support_noise),
        "attention_classifications": dict(class_counts),
        "noise_used_by_variant": dict(decision_counts),
        "interpretation": (
            "Evidence support appears to behave as corpus support rather than query-context support: noisy concepts "
            "can still be marked usable when their attention classification is Core/Supporting and query specificity is weak."
        ),
        "sample_noisy_reasoned": noisy_reasoned[:20],
    }


def _suite_report(*, results: list[dict[str, Any]], audit: dict[str, Any]) -> dict[str, Any]:
    accepted = [result for result in results if result["accepted"] and result["name"] != "usage_gate_standard"]
    final = "KEEP_USAGE_GATE_ONLY_RUN_MORE_DIAGNOSTICS"
    if accepted:
        chosen = accepted[0]["name"]
        if chosen in {"strict_context_usage_gate", "citation_context_usage_gate"}:
            final = "ACCEPT_RUNTIME_V13_REFINED_USAGE_GATE"
        else:
            final = "ACCEPT_SAFE_GUARD_DORMANT_ON_BASELINE"
    return {
        "final_decision": final,
        "evidence_support_audit": audit,
        "variants": results,
        "recommendation": _recommendation(final),
        "live_behavior": {
            "usage_gate_remains_enabled": True,
            "activation_recurrence_default_enabled": False,
            "selected_refinement_enabled_by_default": final == "ACCEPT_RUNTIME_V13_REFINED_USAGE_GATE",
        },
    }


def _recommendation(final: str) -> str:
    if final == "ACCEPT_RUNTIME_V13_REFINED_USAGE_GATE":
        return "Make the accepted refined usage gate the default and keep activation recurrence disabled."
    return "Keep current usage gate only; do not enable activation recurrence. More diagnostics are needed around query-context support."


def _suite_markdown(suite: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Resolution Suite",
        "",
        f"Final decision: `{suite['final_decision']}`",
        "",
        suite["recommendation"],
        "",
        "## Variant Table",
        "",
        "| Variant | Accepted | Noise Used | Reasoning Drift | Attention Precision | Retrieval Recall | Mean Expected Rank | Mean Noise Above |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in suite["variants"]:
        m = result["metrics"]
        lines.append(
            f"| {result['name']} | `{result['accepted']}` | `{m.get('noise_used_in_reasoning')}` | "
            f"`{m.get('reasoning_drift_cases')}` | `{m.get('attention_precision')}` | "
            f"`{m.get('retrieval_recall')}` | `{m.get('mean_expected_rank')}` | `{m.get('mean_noise_above_expected')}` |"
        )
    lines.extend(["", "## Evidence-Support Audit", "", suite["evidence_support_audit"]["interpretation"], ""])
    lines.extend(["## Variant Acceptance", ""])
    for result in suite["variants"]:
        lines.extend([f"### {result['name']}", "", result["description"], ""])
        failed = [key for key, value in result["acceptance"].items() if not value]
        lines.append(f"- failed gates: `{', '.join(failed) if failed else 'none'}`")
        lines.append(f"- raw output: `{result['raw_dir']}`")
        lines.append("")
    lines.extend(["## Live Behavior", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in suite["live_behavior"].items())
    lines.extend(["", f"`{suite['final_decision']}`", ""])
    return "\n".join(lines)


def _audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Evidence-Support Audit",
        "",
        f"Final decision: `{audit['final_decision']}`",
        "",
        audit["interpretation"],
        "",
        f"- noisy reasoned concepts: `{audit['noisy_reasoned_count']}`",
        f"- high-attention noisy reasoned concepts: `{audit['high_attention_noisy_reasoned_count']}`",
        "",
        "## Attention Classifications",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in audit["attention_classifications"].items())
    lines.extend(["", "## Noise Used By Variant", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in audit["noise_used_by_variant"].items())
    lines.extend(["", f"`{audit['final_decision']}`", ""])
    return "\n".join(lines)


def _gated_evidence_count(out_dir: Path) -> int:
    # The current benchmark scorecard does not serialize usage_gated_items. This
    # placeholder keeps the metric stable until the evaluator exposes it.
    return 0


def _sparse_ok(baseline_real: dict[str, Any], real: dict[str, Any]) -> bool:
    baseline = {case["name"]: case for case in baseline_real.get("cases", []) if case.get("category") in {"sparse_knowledge", "unsupported_questions"}}
    current = {case["name"]: case for case in real.get("cases", []) if case.get("category") in {"sparse_knowledge", "unsupported_questions"}}
    for name, case in current.items():
        base = baseline.get(name, {})
        if case.get("runtime_decision") != base.get("runtime_decision"):
            return False
        if case.get("hallucination_count", 0) > base.get("hallucination_count", 0):
            return False
    return True


def _expected_top10_pushed_out(baseline_ranking: dict[str, Any], ranking: dict[str, Any]) -> bool:
    current = {case["case"]: case for case in ranking.get("cases", [])}
    for base_case in baseline_ranking.get("cases", []):
        now = current.get(base_case["case"], {})
        before = {item["concept_id"] for item in base_case.get("expected_results", []) if item.get("baseline_rank", 999) <= 10}
        after = {item["concept_id"] for item in now.get("expected_results", []) if item.get("baseline_rank", 999) <= 10}
        if before - after:
            return True
    return False


def _delta(left: Any, right: Any) -> Any:
    if isinstance(left, bool) or isinstance(right, bool):
        return None
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return round(right - left, 4)
    return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_REPORT_FILES = [
    "runtime_v12_real_knowledge.json",
    "runtime_v12_real_knowledge.md",
    "runtime_v12_activation_ranking_diagnostic.json",
    "runtime_v12_activation_ranking_diagnostic.md",
]


if __name__ == "__main__":
    raise SystemExit(main())
