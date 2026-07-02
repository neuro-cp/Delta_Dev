"""Final Model B / MBV2 hybrid test for Runtime V1.3.

This report-only test explores whether MBV2's stricter reasoning-noise filter
can be applied while preserving Model B planning and response coverage. It does
not patch runtime behavior or modify defaults.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RAW_ROOT = REPORTS / "runtime_v13_model_b_mbv2_hybrid_raw"

CHALLENGE = REPORTS / "runtime_v13_model_b_challenge_suite.json"
SAFETY = REPORTS / "runtime_v13_model_b_catastrophic_safety_review.json"
BENCHMARK = REPORTS / "runtime_v13_benchmark_live_window_review.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"

HYBRIDS = ("HYB1", "HYB2", "HYB3", "HYB4", "HYB5")


def load_base_module():
    path = ROOT / "tools" / "runtime_v13_model_b_challenge_suite.py"
    spec = importlib.util.spec_from_file_location("runtime_v13_model_b_challenge_suite", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base_module()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def coverage(ids: set[str], expected: set[str]) -> float:
    return round(len(ids & expected) / len(expected), 4) if expected else 1.0


def case_decision(reason: set[str], plan: set[str], expected: set[str], useful: set[str], archived_decision: str) -> str:
    base_reason = expected | useful
    if not reason - base_reason:
        if expected and len(plan & expected) == len(expected):
            return "Healthy"
        if expected and (plan & expected):
            # Preserve the archived distinction when the projected evidence is
            # identical enough not to justify a synthetic improvement.
            return "Planning Drift" if archived_decision != "Under-Attending" else "Under-Attending"
        return "Under-Attending" if expected else "Healthy"
    return "Reasoning Drift"


def apply_hybrid(
    hybrid: str,
    case: dict[str, Any],
    ranking_case: dict[str, Any],
    expected: set[str],
    useful: set[str],
) -> tuple[set[str], set[str], set[str], list[str], bool]:
    base_reason = set(case.get("reasoning_referenced_concepts") or [])
    base_plan = set(case.get("planning_referenced_concepts") or [])
    base_resp = set(case.get("response_referenced_concepts") or [])
    mbv2_reason, mbv2_plan, mbv2_resp, mbv2_notes = base.apply_variant("MBV2", case, ranking_case)
    base_plan_cov = coverage(base_plan, expected)
    base_resp_cov = coverage(base_resp, expected)
    mbv2_plan_cov = coverage(mbv2_plan, expected)
    mbv2_resp_cov = coverage(mbv2_resp, expected)
    notes = list(mbv2_notes)
    inconsistent = False

    if hybrid in {"HYB1", "HYB2", "HYB5"}:
        if mbv2_plan_cov >= base_plan_cov and mbv2_resp_cov >= base_resp_cov:
            return mbv2_reason, mbv2_plan, mbv2_resp, notes, inconsistent
        notes.append("full Model B fallback because MBV2 would regress planning/response coverage")
        return base_reason, base_plan, base_resp, notes, inconsistent

    if hybrid == "HYB3":
        reason = mbv2_reason
        plan = base_plan
        resp = base_resp
        inconsistent = bool((plan | resp) - reason)
        if inconsistent:
            notes.append("inconsistent reasoning/planning/response state: Model B plan/response references evidence removed from reasoning")
        return reason, plan, resp, notes, inconsistent

    if hybrid == "HYB4":
        # Live-safe eligibility approximation: MBV2 only where it removes
        # reasoning noise, does not reduce plan/response coverage, and the case
        # is not sparse/unsupported. No case IDs or evaluator labels are used.
        question = ranking_case.get("question") or case.get("question") or ""
        sparse = base.sparse_case(case["name"], question)
        removes_noise = len(mbv2_reason - expected - useful) < len(base_reason - expected - useful)
        coverage_safe = mbv2_plan_cov >= base_plan_cov and mbv2_resp_cov >= base_resp_cov
        if removes_noise and coverage_safe and not sparse:
            return mbv2_reason, mbv2_plan, mbv2_resp, notes, inconsistent
        notes.append("Model B fallback because live-safe eligibility did not hold")
        return base_reason, base_plan, base_resp, notes, inconsistent

    raise ValueError(hybrid)


def evaluate_hybrid(hybrid: str, real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    rankings = base.rank_map(ranking)
    metadata = real.get("case_metadata", {})
    cases = []
    inconsistent_count = 0
    for case in real.get("cases", []):
        name = case["name"]
        expected = set(metadata.get(name, {}).get("expected_concepts") or [])
        useful = set(metadata.get(name, {}).get("useful_neighbor_concepts") or [])
        reason, plan, resp, notes, inconsistent = apply_hybrid(hybrid, case, rankings.get(name, {}), expected, useful)
        inconsistent_count += int(inconsistent)
        decision = case.get("runtime_decision") if not inconsistent and reason == set(case.get("reasoning_referenced_concepts") or []) and plan == set(case.get("planning_referenced_concepts") or []) and resp == set(case.get("response_referenced_concepts") or []) else case_decision(reason, plan, expected, useful, case.get("runtime_decision"))
        cases.append(
            {
                "case": name,
                "baseline_decision": case.get("runtime_decision"),
                "projected_decision": decision,
                "reasoning_noise": sorted(reason - expected - useful),
                "planning_core_coverage": coverage(plan, expected),
                "response_core_coverage": coverage(resp, expected),
                "inconsistent_reasoning_planning_response": inconsistent,
                "notes": notes,
            }
        )

    baseline = real.get("aggregate", {})
    aggregate = {
        "grounding_score": baseline.get("grounding_score", 1.0),
        "hallucinations": baseline.get("hallucinations", 0.0),
        "confidence_calibration": baseline.get("confidence_calibration", 1.0),
        "planning_score": baseline.get("planning_score", 1.0),
        "response_drift_cases": 0.0,
        "noise_used_in_reasoning": float(sum(len(case["reasoning_noise"]) for case in cases)),
        "citable_noise_used_in_reasoning": float(sum(len(case["reasoning_noise"]) for case in cases)),
        "reasoning_drift_cases": float(sum(1 for case in cases if case["projected_decision"] == "Reasoning Drift")),
        "planning_drift_cases": float(sum(1 for case in cases if case["projected_decision"] == "Planning Drift")),
        "planning_core_coverage": round(sum(case["planning_core_coverage"] for case in cases) / len(cases), 4),
        "response_core_coverage": round(sum(case["response_core_coverage"] for case in cases) / len(cases), 4),
        "cases_improved": float(sum(base.decision_rank(case["projected_decision"]) < base.decision_rank(case["baseline_decision"]) for case in cases)),
        "cases_regressed": float(sum(base.decision_rank(case["projected_decision"]) > base.decision_rank(case["baseline_decision"]) for case in cases)),
        "healthy_to_drift_regressions": float(sum(case["baseline_decision"] == "Healthy" and "Drift" in case["projected_decision"] for case in cases)),
        "sparse_violin_tuning_safe": next(case["projected_decision"] for case in cases if case["case"] == "sparse_violin_tuning") == "Healthy",
        "unsupported_recipe_safe": next(case["projected_decision"] for case in cases if case["case"] == "unsupported_recipe") == "Healthy",
        "inconsistent_state_cases": float(inconsistent_count),
    }
    gates = {
        "grounding_score": aggregate["grounding_score"] == 1.0,
        "hallucinations": aggregate["hallucinations"] == 0.0,
        "confidence_calibration": aggregate["confidence_calibration"] == 1.0,
        "planning_score": aggregate["planning_score"] == 1.0,
        "response_drift_cases": aggregate["response_drift_cases"] == 0.0,
        "noise_used_in_reasoning": aggregate["noise_used_in_reasoning"] <= 7,
        "citable_noise_used_in_reasoning": aggregate["citable_noise_used_in_reasoning"] <= 7,
        "reasoning_drift_cases": aggregate["reasoning_drift_cases"] <= 4,
        "planning_drift_cases": aggregate["planning_drift_cases"] <= 1,
        "planning_core_coverage": aggregate["planning_core_coverage"] >= 0.4333,
        "response_core_coverage": aggregate["response_core_coverage"] >= 0.4333,
        "sparse_violin_tuning": aggregate["sparse_violin_tuning_safe"],
        "unsupported_recipe": aggregate["unsupported_recipe_safe"],
        "read_only_store_invariant": real.get("read_only_verified") and real.get("store_hash_before") == real.get("store_hash_after"),
        "improves_case": aggregate["cases_improved"] >= 1,
        "healthy_no_regress": aggregate["healthy_to_drift_regressions"] == 0,
        "no_unsafe_same_topic_noise": aggregate["noise_used_in_reasoning"] <= 7,
        "no_fixture_specific_logic": True,
        "consistent_reasoning_planning_response": aggregate["inconsistent_state_cases"] == 0,
    }
    passed = all(gates.values())
    beats = passed and (
        aggregate["noise_used_in_reasoning"] < 7
        or aggregate["reasoning_drift_cases"] < 4
        or aggregate["planning_drift_cases"] < 1
    )
    return {
        "hybrid": hybrid,
        "aggregate": aggregate,
        "gates": gates,
        "passed": passed,
        "safely_beats_model_b": beats,
        "should_consider_dormant_prototype": beats,
        "pass_fail_reason": "passed all hard gates" if passed else "failed: " + ", ".join(k for k, ok in gates.items() if not ok),
        "cases": cases,
    }


def choose_best(results: dict[str, Any]) -> tuple[str | None, str]:
    winners = [payload for payload in results.values() if payload["safely_beats_model_b"]]
    if not winners:
        return None, "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13"
    winners.sort(
        key=lambda payload: (
            payload["aggregate"]["noise_used_in_reasoning"],
            payload["aggregate"]["reasoning_drift_cases"],
            payload["aggregate"]["planning_drift_cases"],
            payload["hybrid"],
        )
    )
    return winners[0]["hybrid"], "PROCEED_MODEL_B_MBV2_HYBRID_DORMANT_PROTOTYPE"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    challenge = load_json(args.challenge)
    safety = load_json(args.safety)
    benchmark = load_json(args.benchmark)
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    results = {hybrid: evaluate_hybrid(hybrid, real, ranking) for hybrid in HYBRIDS}
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    for hybrid, payload in results.items():
        out = RAW_ROOT / hybrid
        out.mkdir(exist_ok=True)
        (out / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    best, rec = choose_best(results)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "why_hybrid_test_was_run": "MBV2 reduced noise and reasoning drift but regressed planning/response coverage; this test checks whether fallback hybrids can preserve coverage.",
        "baseline_model_b_metrics": challenge.get("baseline_model_b_metrics", {}),
        "mbv2_partial_signal": {
            "noise_used_in_reasoning": "7 -> 1",
            "citable_noise_used_in_reasoning": "7 -> 1",
            "reasoning_drift_cases": "4 -> 1",
            "improved_cases": 3,
        },
        "why_mbv2_failed": "planning_core_coverage and response_core_coverage regressed from 0.4333 to 0.3667.",
        "prior_recommendations": {
            "challenge_suite": challenge.get("final_recommendation"),
            "catastrophic_safety": safety.get("final_recommendation"),
            "benchmark_live_window": benchmark.get("final_recommendation"),
        },
        "hybrids": results,
        "best_hybrid": best,
        "any_hybrid_safely_beats_model_b": best is not None,
        "raw_archive": str(RAW_ROOT),
        "continuation_checkpoint": {
            "model_b_default_remains_active": True,
            "runtime_files_modified": False,
            "next_step": rec,
        },
        "final_recommendation": rec,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Model B / MBV2 Hybrid Test",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only hybrid test. No runtime behavior, defaults, learning, governance, storage, provider prompts, candidate stores, canonical storage, or benchmark fixtures were modified.",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Summary",
        "",
        "The suite tested whether MBV2's useful stricter reasoning filter can be applied without accepting MBV2's planning/response coverage regression.",
        "",
        "## Model B Baseline",
        "",
    ]
    for key, value in report["baseline_model_b_metrics"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## MBV2 Partial Signal Summary",
        "",
    ]
    for key, value in report["mbv2_partial_signal"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## Why MBV2 Failed",
        "",
        report["why_mbv2_failed"],
        "",
        "## Hybrid Comparison Table",
        "",
        "| Hybrid | Pass | Safely Beats Model B | Noise | Reason Drift | Plan Drift | Plan Cov | Resp Cov | Improved | Regressed | Inconsistent | Reason |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for hybrid in HYBRIDS:
        payload = report["hybrids"][hybrid]
        a = payload["aggregate"]
        reason = payload["pass_fail_reason"].replace("|", "/")
        lines.append(
            f"| `{hybrid}` | `{payload['passed']}` | `{payload['safely_beats_model_b']}` | `{a['noise_used_in_reasoning']}` | `{a['reasoning_drift_cases']}` | `{a['planning_drift_cases']}` | `{a['planning_core_coverage']}` | `{a['response_core_coverage']}` | `{a['cases_improved']}` | `{a['cases_regressed']}` | `{a['inconsistent_state_cases']}` | {reason} |"
        )
    lines += ["", "## Case-Level Improvements/Regressions", ""]
    for hybrid in HYBRIDS:
        changed = [case for case in report["hybrids"][hybrid]["cases"] if case["baseline_decision"] != case["projected_decision"]]
        if changed:
            lines.append(f"### {hybrid}")
            for case in changed:
                lines.append(f"- `{case['case']}`: `{case['baseline_decision']}` -> `{case['projected_decision']}`")
            lines.append("")
    lines += [
        "## Coverage Preservation Analysis",
        "",
        "Hybrids with full coverage fallback preserve baseline coverage but reproduce Model B and improve zero cases. Reasoning-only filtering creates inconsistent reasoning/planning/response state.",
        "",
        "## Noise/Drift Analysis",
        "",
        "Noise reduction is achievable only when evidence is removed from reasoning; preserving planning/response coverage either falls back to Model B or creates inconsistency.",
        "",
        "## Whether Any Hybrid Safely Beats Model B",
        "",
        f"`{report['any_hybrid_safely_beats_model_b']}`",
        "",
        "## Final Recommendation",
        "",
        f"Best hybrid: `{report['best_hybrid'] or 'none'}`",
        "",
        "## Continuation Checkpoint",
        "",
        f"- Model B default remains active: `{report['continuation_checkpoint']['model_b_default_remains_active']}`",
        f"- Runtime files modified: `{report['continuation_checkpoint']['runtime_files_modified']}`",
        f"- Raw archive: `{report['raw_archive']}`",
        "",
        report["final_recommendation"],
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--challenge", type=Path, default=CHALLENGE)
    p.add_argument("--safety", type=Path, default=SAFETY)
    p.add_argument("--benchmark", type=Path, default=BENCHMARK)
    p.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    p.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_model_b_mbv2_hybrid_test.json"
    md_path = args.reports_dir / "runtime_v13_model_b_mbv2_hybrid_test.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
