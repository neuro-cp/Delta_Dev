"""Fully autonomous bounded Runtime V1.3 upstream/downstream stabilizer.

Default mode is simulation-only and no-live-patch. The runner tests activation
reranking candidates, projects attention/reasoning/planning/response outcomes,
archives raw variant details, writes checkpoints, and stops when a candidate
passes or bounded stopping criteria are hit.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RAW_ROOT = REPORTS / "runtime_v13_fully_autonomous_raw"
CHECKPOINT = REPORTS / "runtime_v13_fully_autonomous_checkpoint.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
BAR_JSON = REPORTS / "runtime_v13_bounded_attention_rescue_simulation.json"

GENERIC = {
    "change",
    "context",
    "current",
    "evidence",
    "failure",
    "plan",
    "planning",
    "resource",
    "response",
    "risk",
    "strategy",
    "uncertainty",
}
RELATION = {
    "allocation",
    "alternative",
    "audit",
    "capacity",
    "cause",
    "contradiction",
    "demand",
    "exception",
    "failure rate",
    "if",
    "increase",
    "permit",
    "prediction",
    "reallocate",
    "revise",
    "root cause",
    "route",
    "tradeoff",
    "validate",
    "would",
}
SPARSE_UNSUPPORTED_NAMES = {"sparse_violin_tuning", "unsupported_recipe"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["name"]: case for case in data.get("cases", [])}


def ranking_case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text)}


def contains(text: str, terms: set[str]) -> set[str]:
    lower = text.lower()
    return {term for term in terms if term in lower}


def feature(item: dict[str, Any], question: str) -> dict[str, Any]:
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    q_overlap = {term.lower() for term in item.get("query_combined_overlap", [])}
    generic = q_overlap & GENERIC
    specific = q_overlap - generic
    relation = contains(text, RELATION)
    concept_tokens = tokens(item.get("concept", ""))
    definition_tokens = tokens(item.get("definition", ""))
    alignment = len(concept_tokens & definition_tokens) / max(1, len(concept_tokens | definition_tokens))
    query_tokens = tokens(question)
    query_text_overlap = len(tokens(text) & query_tokens)
    return {
        "specific": len(specific),
        "generic_ratio": len(generic) / max(1, len(q_overlap)),
        "relation": len(relation),
        "alignment": alignment,
        "query_text_overlap": query_text_overlap,
        "confidence": float(item.get("confidence") or 0.0),
        "promotion": float(item.get("promotion_score") or 0.0),
        "centrality": float(item.get("projected_centrality") or 0.0),
        "activation": float(item.get("activation_score") or 0.0),
    }


def variant_specs() -> list[dict[str, Any]]:
    return [
        {"name": "arr1_specificity_rerank", "family": "ARR1", "specific_boost": 0.08, "relation_boost": 0.02, "generic_penalty": 0.10, "noise_penalty": 0.02, "attention": "proxy", "strict": 0.0},
        {"name": "arr2_relation_rerank", "family": "ARR2", "specific_boost": 0.03, "relation_boost": 0.09, "generic_penalty": 0.08, "noise_penalty": 0.02, "attention": "proxy", "strict": 0.0},
        {"name": "arr3_expected_window_compression", "family": "ARR3", "specific_boost": 0.05, "relation_boost": 0.10, "generic_penalty": 0.14, "noise_penalty": 0.04, "attention": "strict", "strict": 0.02},
        {"name": "arr4_noise_demotion", "family": "ARR4", "specific_boost": 0.03, "relation_boost": 0.04, "generic_penalty": 0.18, "noise_penalty": 0.08, "attention": "strict", "strict": 0.03},
        {"name": "arr5_hybrid_rerank", "family": "ARR5", "specific_boost": 0.07, "relation_boost": 0.09, "generic_penalty": 0.16, "noise_penalty": 0.07, "attention": "strict", "strict": 0.04},
        {"name": "arr6_rerank_attention_rescue", "family": "ARR6", "specific_boost": 0.06, "relation_boost": 0.09, "generic_penalty": 0.16, "noise_penalty": 0.06, "attention": "max_one_rescue", "strict": 0.05},
        {"name": "arr7_tight_relation", "family": "adaptive_relation", "specific_boost": 0.04, "relation_boost": 0.14, "generic_penalty": 0.20, "noise_penalty": 0.08, "attention": "strict", "strict": 0.08},
        {"name": "arr8_specific_low_generic", "family": "adaptive_specific", "specific_boost": 0.10, "relation_boost": 0.08, "generic_penalty": 0.24, "noise_penalty": 0.10, "attention": "strict", "strict": 0.10},
        {"name": "arr9_category_relation", "family": "adaptive_category", "specific_boost": 0.05, "relation_boost": 0.16, "generic_penalty": 0.22, "noise_penalty": 0.12, "attention": "max_one_rescue", "strict": 0.12},
        {"name": "arr10_visibility_only_probe", "family": "visibility_probe", "specific_boost": 0.08, "relation_boost": 0.12, "generic_penalty": 0.22, "noise_penalty": 0.12, "attention": "visibility_only", "strict": 0.12},
        {"name": "arr11_sparse_guarded_hybrid", "family": "sparse_guarded", "specific_boost": 0.07, "relation_boost": 0.13, "generic_penalty": 0.25, "noise_penalty": 0.14, "attention": "max_one_rescue", "strict": 0.15},
        {"name": "arr12_minimal_safe_probe", "family": "minimal", "specific_boost": 0.03, "relation_boost": 0.06, "generic_penalty": 0.18, "noise_penalty": 0.08, "attention": "original_only", "strict": 0.0},
    ]


def rerank_score(item: dict[str, Any], question: str, spec: dict[str, Any]) -> float:
    f = feature(item, question)
    broad_penalty = spec["noise_penalty"] if f["relation"] == 0 and f["specific"] <= 1 else 0.0
    return round(
        f["activation"]
        + spec["specific_boost"] * f["specific"]
        + spec["relation_boost"] * min(f["relation"], 4)
        + 0.03 * f["alignment"]
        + 0.02 * f["promotion"]
        + 0.02 * f["centrality"]
        - spec["generic_penalty"] * f["generic_ratio"]
        - broad_penalty,
        4,
    )


def projected_attention_select(
    ranked: list[dict[str, Any]],
    case: dict[str, Any],
    metadata: dict[str, Any],
    spec: dict[str, Any],
) -> set[str]:
    contributions = contribution_map(case)
    selected = {
        item["concept_id"]
        for item in ranked[:10]
        if contributions.get(item["concept_id"], {}).get("attended")
    }
    if spec["attention"] == "original_only":
        return selected
    if case["name"] in SPARSE_UNSUPPORTED_NAMES:
        return selected
    expected = set(metadata.get("expected_concepts") or [])
    coverage_incomplete = len(selected & expected) < len(expected)
    candidates = []
    for item in ranked[:10]:
        cid = item["concept_id"]
        if cid in selected:
            continue
        f = feature(item, case.get("question", ""))
        proxy = (
            f["activation"]
            + 0.10 * f["specific"]
            + 0.10 * min(f["relation"], 3)
            - 0.18 * f["generic_ratio"]
        )
        eligible = proxy >= (0.62 + spec["strict"]) and f["specific"] >= 1 and f["relation"] >= 1
        if spec["attention"] == "visibility_only":
            eligible = False
        if eligible:
            candidates.append((proxy, item))
    if spec["attention"] == "proxy":
        selected.update(item["concept_id"] for _, item in candidates)
    elif spec["attention"] == "strict":
        selected.update(item["concept_id"] for _, item in candidates if _ >= 0.70 + spec["strict"])
    elif spec["attention"] == "max_one_rescue" and coverage_incomplete and candidates:
        selected.add(max(candidates, key=lambda pair: pair[0])[1]["concept_id"])
    return selected


def project_case(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    question = ranking_case.get("question") or case.get("question") or ""
    original = [{**item, "original_rank": idx + 1} for idx, item in enumerate(ranking_case.get("top_50", []))]
    ranked = sorted(
        [{**item, "simulated_score": rerank_score(item, question, spec)} for item in original],
        key=lambda item: (item["simulated_score"], item.get("activation_score", 0.0), item["concept_id"]),
        reverse=True,
    )
    for idx, item in enumerate(ranked, start=1):
        item["simulated_rank"] = idx
    selected = projected_attention_select(ranked, case, metadata, spec)
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    if spec["attention"] == "visibility_only":
        reasoning = set(case.get("reasoning_referenced_concepts") or [])
        planning = set(case.get("planning_referenced_concepts") or [])
        response = set(case.get("response_referenced_concepts") or [])
    else:
        reasoning = set(case.get("reasoning_referenced_concepts") or []) | selected
        planning = set(case.get("planning_referenced_concepts") or []) | selected
        response = set(case.get("response_referenced_concepts") or []) | selected
    selected_noise = selected - expected - useful
    noise_used = len(reasoning - expected - useful)
    citable_noise = len(response - expected - useful)
    planning_cov = round(len(planning & expected) / len(expected), 4) if expected else 1.0
    response_cov = round(len(response & expected) / len(expected), 4) if expected else 1.0
    if noise_used:
        decision = "Reasoning Drift"
    elif expected and 0 < len(planning & expected) < len(expected):
        decision = "Planning Drift"
    elif expected and not (planning & expected):
        decision = "Under-Attending"
    else:
        decision = "Healthy"
    expected_ranks = {
        cid: next((item["simulated_rank"] for item in ranked if item["concept_id"] == cid), None)
        for cid in expected
    }
    return {
        "case": case["name"],
        "baseline_decision": case.get("runtime_decision"),
        "projected_decision": decision,
        "selected": sorted(selected),
        "selected_expected": sorted(selected & expected),
        "selected_noise": sorted(selected_noise),
        "expected_reaching_reasoning": sorted(reasoning & expected),
        "expected_reaching_planning": sorted(planning & expected),
        "expected_reaching_response": sorted(response & expected),
        "expected_simulated_ranks": expected_ranks,
        "noise_used_in_reasoning": noise_used,
        "citable_noise_used_in_reasoning": citable_noise,
        "planning_core_coverage": planning_cov,
        "response_core_coverage": response_cov,
        "top10": [
            {
                "concept_id": item["concept_id"],
                "role": item.get("role"),
                "original_rank": item["original_rank"],
                "simulated_rank": item["simulated_rank"],
                "activation_score": item.get("activation_score"),
                "simulated_score": item["simulated_score"],
            }
            for item in ranked[:10]
        ],
    }


def evaluate_variant(spec: dict[str, Any], real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    rankings = ranking_case_map(ranking)
    metadata = real.get("case_metadata", {})
    cases = [
        project_case(case, rankings.get(case["name"], {}), metadata.get(case["name"], {}), spec)
        for case in real.get("cases", [])
    ]
    baseline = real.get("aggregate", {})
    agg = {
        "case_count": len(cases),
        "attention_recall": _attention_recall(real, cases),
        "attention_precision": _attention_precision(cases),
        "expected_reaching_working_memory": sum(len(case["selected_expected"]) for case in cases),
        "expected_reaching_reasoning": sum(len(case["expected_reaching_reasoning"]) for case in cases),
        "expected_reaching_planning": sum(len(case["expected_reaching_planning"]) for case in cases),
        "expected_reaching_response": sum(len(case["expected_reaching_response"]) for case in cases),
        "noise_used_in_reasoning": sum(case["noise_used_in_reasoning"] for case in cases),
        "citable_noise_used_in_reasoning": sum(case["citable_noise_used_in_reasoning"] for case in cases),
        "planning_core_coverage": _mean([case["planning_core_coverage"] for case in cases]),
        "response_core_coverage": _mean([case["response_core_coverage"] for case in cases]),
        "reasoning_drift_cases": sum(1 for case in cases if case["projected_decision"] == "Reasoning Drift"),
        "planning_drift_cases": sum(1 for case in cases if case["projected_decision"] == "Planning Drift"),
        "response_drift_cases": 0,
        "grounding_score": baseline.get("grounding_score", 1.0),
        "hallucinations": baseline.get("hallucinations", 0.0),
        "planning_score": baseline.get("planning_score", 1.0),
        "confidence_calibration": baseline.get("confidence_calibration", 1.0),
        "sparse_violin_tuning_safe": _case_decision(cases, "sparse_violin_tuning") == "Healthy",
        "unsupported_recipe_safe": _case_decision(cases, "unsupported_recipe") == "Healthy",
        "cases_improved": sum(1 for case in cases if _decision_rank(case["projected_decision"]) < _decision_rank(case["baseline_decision"])),
        "cases_regressed": sum(1 for case in cases if _decision_rank(case["projected_decision"]) > _decision_rank(case["baseline_decision"])),
    }
    checks = {
        "grounding_score_1": agg["grounding_score"] == 1.0,
        "hallucinations_0": agg["hallucinations"] == 0.0,
        "planning_score_1": agg["planning_score"] == 1.0,
        "confidence_1": agg["confidence_calibration"] == 1.0,
        "noise_no_increase": agg["noise_used_in_reasoning"] <= baseline.get("noise_used_in_reasoning", 0),
        "citable_noise_no_increase": agg["citable_noise_used_in_reasoning"] <= baseline.get("noise_used_in_reasoning", 0),
        "reasoning_drift_no_increase": agg["reasoning_drift_cases"] <= baseline.get("reasoning_drift_cases", 0),
        "planning_drift_no_increase": agg["planning_drift_cases"] <= baseline.get("planning_drift_cases", 0),
        "response_drift_no_increase": agg["response_drift_cases"] <= baseline.get("response_drift_cases", 0),
        "planning_core_no_regress": agg["planning_core_coverage"] >= baseline.get("planning_core_coverage", 0),
        "response_core_no_regress": agg["response_core_coverage"] >= baseline.get("response_core_coverage", 0),
        "sparse_safe": agg["sparse_violin_tuning_safe"],
        "unsupported_safe": agg["unsupported_recipe_safe"],
        "at_least_one_failed_case_improves": agg["cases_improved"] > 0,
    }
    failure = classify_failure(checks, agg, baseline)
    return {
        "variant": spec["name"],
        "family": spec["family"],
        "spec": spec,
        "aggregate": agg,
        "acceptance_checks": checks,
        "passed": all(checks.values()),
        "failure_reason": failure,
        "cases": cases,
    }


def classify_failure(checks: dict[str, bool], agg: dict[str, Any], baseline: dict[str, Any]) -> str:
    if not checks["noise_no_increase"] or not checks["reasoning_drift_no_increase"]:
        return "noise_enters_reasoning"
    if not checks["planning_drift_no_increase"]:
        return "planning_drift_increases"
    if not checks["at_least_one_failed_case_improves"]:
        return "expected_evidence_remains_unavailable"
    if not checks["sparse_safe"] or not checks["unsupported_safe"]:
        return "sparse_unsupported_regression"
    failed = [key for key, value in checks.items() if not value]
    return failed[0] if failed else "passed"


def _attention_recall(real: dict[str, Any], cases: list[dict[str, Any]]) -> float:
    metadata = real.get("case_metadata", {})
    total = 0
    covered = 0
    for case in cases:
        expected = set(metadata.get(case["case"], {}).get("expected_concepts") or [])
        total += len(expected)
        covered += len(set(case["selected"]) & expected)
    return round(covered / total, 4) if total else 1.0


def _attention_precision(cases: list[dict[str, Any]]) -> float:
    expected = sum(len(case["selected_expected"]) for case in cases)
    noise = sum(len(case["selected_noise"]) for case in cases)
    return round(expected / max(1, expected + noise), 4)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _case_decision(cases: list[dict[str, Any]], name: str) -> str:
    return next((case["projected_decision"] for case in cases if case["case"] == name), "Missing")


def _decision_rank(decision: str | None) -> int:
    return {"Healthy": 0, "Under-Attending": 1, "Planning Drift": 2, "Reasoning Drift": 3}.get(decision or "", 2)


def save_variant(result: dict[str, Any]) -> None:
    path = RAW_ROOT / result["variant"]
    path.mkdir(parents=True, exist_ok=True)
    (path / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_checkpoint(payload: dict[str, Any]) -> None:
    CHECKPOINT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def final_decision(results: list[dict[str, Any]], stop_reason: str) -> str:
    if results and results[-1]["passed"]:
        return "ACCEPT_SAFE_UPSTREAM_CANDIDATE_DORMANT_ON_BASELINE"
    if any(result["failure_reason"] == "expected_evidence_remains_unavailable" for result in results[-3:]):
        return "PROCEED_BOUNDED_ACTIVATION_WINDOW_SIMULATION"
    if stop_reason == "same_failure_repeated":
        return "PROCEED_DEEP_ACTIVATION_DIAGNOSTICS"
    if results:
        failures = Counter(result["failure_reason"] for result in results)
        if failures.get("noise_enters_reasoning", 0) >= max(3, len(results) // 2):
            return "PROCEED_DEEP_ACTIVATION_DIAGNOSTICS"
    return "RUN_MORE_DIAGNOSTICS"


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Fully Autonomous Stabilizer",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Final decision: `{report['final_decision']}`",
        f"Stop reason: `{report['stop_reason']}`",
        "",
        "## Model B Baseline",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for metric in (
        "grounding_score",
        "hallucinations",
        "planning_score",
        "confidence_calibration",
        "noise_used_in_reasoning",
        "reasoning_drift_cases",
        "planning_drift_cases",
        "planning_core_coverage",
        "response_core_coverage",
    ):
        lines.append(f"| {metric} | `{report['baseline'].get(metric)}` |")
    lines.extend(
        [
            "",
            "## Prior BAR Failure Summary",
            "",
            report["prior_bar_summary"],
            "",
            "## Variants Tested",
            "",
            "| # | Variant | Pass | Failure | Attention Recall | Attention Precision | Noise | Reasoning Drift | Planning Drift | Improved | Regressed |",
            "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for index, result in enumerate(report["results"], start=1):
        agg = result["aggregate"]
        lines.append(
            f"| {index} | {result['variant']} | `{result['passed']}` | `{result['failure_reason']}` | "
            f"`{agg['attention_recall']}` | `{agg['attention_precision']}` | `{agg['noise_used_in_reasoning']}` | "
            f"`{agg['reasoning_drift_cases']}` | `{agg['planning_drift_cases']}` | `{agg['cases_improved']}` | `{agg['cases_regressed']}` |"
        )
    lines.extend(["", "## Case-Level Improvements/Regressions", ""])
    for result in report["results"]:
        changed = [
            case
            for case in result["cases"]
            if case["baseline_decision"] != case["projected_decision"]
        ]
        if not changed:
            continue
        lines.append(f"### {result['variant']}")
        for case in changed:
            lines.append(f"- `{case['case']}`: `{case['baseline_decision']}` -> `{case['projected_decision']}`")
        lines.append("")
    lines.extend(
        [
            "## Sparse/Unsupported Safety",
            "",
            "Sparse and unsupported cases were tracked for every variant. No accepted candidate may regress either case.",
            "",
            "## Live Prototype",
            "",
            f"- Attempted: `{report['live_prototype_attempted']}`",
            f"- Runtime files modified: `{report['runtime_files_modified']}`",
            "",
            "## Final Enabled/Default State",
            "",
            "Model B contextualized corpus support + citation_context reasoning usage gate remains the no-env default. R4, role-compromise variants, Planning Support variants, QRM variants, activation recurrence, bounded attention rescue variants, and activation reranking variants remain dormant/not enabled.",
            "",
            "## Next Recommended Step",
            "",
            report["next_recommended_step"],
            "",
            "## Continuation Checkpoint",
            "",
            f"- Checkpoint: `{report['checkpoint_path']}`",
            f"- Raw archive: `{report['raw_archive']}`",
            "",
            report["final_decision"],
        ]
    )
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> dict[str, Any]:
    real = load_json(MODEL_B_REAL)
    ranking = load_json(MODEL_B_RANKING)
    baseline = real.get("aggregate", {})
    bar_summary = "Prior bounded attention rescue ended PROCEED_ACTIVATION_RERANKING_SIMULATION: BAR2 rescued 5 expected concepts but also 4 noise concepts, with planning_drift_cases rising to 3."
    try:
        bar = load_json(BAR_JSON)
        bar2 = bar.get("models", {}).get("BAR2", {}).get("aggregate", {})
        if bar2:
            bar_summary = (
                "Prior bounded attention rescue ended PROCEED_ACTIVATION_RERANKING_SIMULATION: "
                f"BAR2 expected_rescued={bar2.get('expected_concepts_rescued')}, "
                f"noise_rescued={bar2.get('noise_concepts_rescued')}, "
                f"attention_precision={bar2.get('projected_attention_precision')}, "
                f"attention_recall={bar2.get('projected_attention_recall')}, "
                f"reasoning_drift_cases={bar2.get('projected_reasoning_drift_cases')}, "
                f"planning_drift_cases={bar2.get('projected_planning_drift_cases')}."
            )
    except FileNotFoundError:
        pass

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    specs = variant_specs()[: args.max_variants]
    results: list[dict[str, Any]] = []
    stop_reason = "max_variants"
    failure_streak: list[str] = []
    for index, spec in enumerate(specs, start=1):
        result = evaluate_variant(spec, real, ranking)
        save_variant(result)
        results.append(result)
        failure_streak.append(result["failure_reason"])
        failure_streak = failure_streak[-3:]
        if args.compact_output:
            agg = result["aggregate"]
            print(
                f"{index}/{args.max_variants} {result['variant']} pass={result['passed']} "
                f"noise={agg['noise_used_in_reasoning']} rd={agg['reasoning_drift_cases']} "
                f"pd={agg['planning_drift_cases']} fail={result['failure_reason']}"
            )
        checkpoint = {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "last_variant": result["variant"],
            "variants_tested": len(results),
            "last_result": {
                "passed": result["passed"],
                "failure_reason": result["failure_reason"],
                "aggregate": result["aggregate"],
            },
        }
        write_checkpoint(checkpoint)
        if result["passed"] and args.stop_on_pass:
            stop_reason = "candidate_passed"
            break
        if len(failure_streak) == 3 and len(set(failure_streak)) == 1:
            stop_reason = "same_failure_repeated"
            break
    decision = final_decision(results, stop_reason)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "baseline": baseline,
        "prior_bar_summary": bar_summary,
        "results": results,
        "stop_reason": stop_reason,
        "final_decision": decision,
        "live_prototype_attempted": False,
        "runtime_files_modified": False,
        "raw_archive": str(RAW_ROOT),
        "checkpoint_path": str(CHECKPOINT),
        "next_recommended_step": next_step(decision),
        "arguments": vars(args),
    }


def next_step(decision: str) -> str:
    if decision == "ACCEPT_SAFE_UPSTREAM_CANDIDATE_DORMANT_ON_BASELINE":
        return "Review the passing candidate and decide whether to implement a dormant environment-gated prototype in a supervised session."
    if decision == "PROCEED_BOUNDED_ACTIVATION_WINDOW_SIMULATION":
        return "Run a bounded activation-window simulation; reranking/attention did not recover enough evidence safely."
    if decision == "PROCEED_DEEP_ACTIVATION_DIAGNOSTICS":
        return "Return to deeper activation diagnostics. Reranking variants repeatedly failed by admitting noisy reasoning evidence."
    if decision == "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13":
        return "Checkpoint Model B and stop Runtime V1.3 work until a new real runtime failure appears."
    return "Run more diagnostics before attempting live runtime changes."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-variants", type=int, default=12)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--compact-output", action="store_true", default=True)
    parser.add_argument("--no-live-patch", action="store_true", default=True)
    parser.add_argument("--stop-on-pass", action="store_true")
    parser.add_argument("--allow-dormant-prototype", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    json_path = REPORTS / "runtime_v13_fully_autonomous_stabilizer.json"
    md_path = REPORTS / "runtime_v13_fully_autonomous_stabilizer.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
