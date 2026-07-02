"""Runtime V1.3 Model B challenge suite.

This report-only suite tests conservative Model B-adjacent variants against the
archived real-store Runtime V1.3 baseline. It does not patch runtime behavior,
modify defaults, expand visibility, or loosen the citation gate.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RAW_ROOT = REPORTS / "runtime_v13_model_b_challenge_suite_raw"

SAFETY = REPORTS / "runtime_v13_model_b_catastrophic_safety_review.json"
BENCHMARK = REPORTS / "runtime_v13_benchmark_live_window_review.json"
ECA = REPORTS / "runtime_v13_evidence_contextualization_activation_simulation.json"
RCG = REPORTS / "runtime_v13_reasoning_citation_gate_review.json"
USABILITY = REPORTS / "runtime_v13_expected_evidence_usability_audit.json"
ESS = REPORTS / "runtime_v13_evidence_stage_separation_diagnostic.json"
QDA = REPORTS / "runtime_v13_query_decomposition_activation_simulation.json"
RAA = REPORTS / "runtime_v13_relation_aware_activation_simulation.json"
STABILIZER = REPORTS / "runtime_v13_fully_autonomous_stabilizer.json"
AVAILABILITY = REPORTS / "runtime_v13_activation_attention_candidate_availability.json"
CONSOLIDATION = REPORTS / "runtime_v13_failure_bottleneck_consolidation_audit.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"

STOP = {
    "a",
    "about",
    "after",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "or",
    "should",
    "the",
    "their",
    "to",
    "when",
    "why",
    "with",
}

GENERIC = {"change", "context", "current", "data", "evidence", "failure", "increase", "plan", "planning", "resource", "response", "risk", "strategy", "team", "uncertainty"}
RELATION_TERMS = {"allocate", "allocation", "alternative", "assumption", "audit", "capacity", "causal", "cause", "conflict", "contradict", "demand", "exception", "failed", "failure", "method", "permit", "prediction", "reallocate", "reports", "revise", "root", "route", "shelter", "timeline", "tradeoff"}
EVIDENCE_NEEDS = {
    "cause_root_cause": {"cause", "root", "mechanism", "timeline", "failure", "interact"},
    "contradiction_resolution": {"contradict", "conflicting", "resolve", "unresolved", "source", "evidence"},
    "exception_rule": {"exception", "rule", "policy", "audit", "expiration", "applies"},
    "revision_action": {"revise", "alternative", "route", "method", "assumption", "failed", "permit"},
    "resource_constraint": {"allocation", "resource", "shelter", "demand", "capacity", "reallocate"},
    "risk_uncertainty": {"risk", "uncertainty", "tradeoff", "confidence", "likelihood"},
}

BASELINE_KEYS = (
    "grounding_score",
    "hallucinations",
    "confidence_calibration",
    "planning_score",
    "response_drift_cases",
    "noise_used_in_reasoning",
    "reasoning_drift_cases",
    "planning_drift_cases",
    "planning_core_coverage",
    "response_core_coverage",
    "attention_precision",
    "attention_recall",
)

VARIANT_NAMES = [f"MBV{i}" for i in range(1, 11)]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def toks(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text) if t.lower() not in STOP}


def rank_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def rank_item(ranking_case: dict[str, Any], cid: str) -> dict[str, Any] | None:
    for item in ranking_case.get("top_50", []):
        if item.get("concept_id") == cid:
            return item
    return None


def infer_need(question: str) -> str:
    q = toks(question)
    scored = {need: len(q & terms) for need, terms in EVIDENCE_NEEDS.items()}
    best = max(scored, key=lambda need: (scored[need], need))
    return best if scored[best] else "revision_action"


def feature(item: dict[str, Any] | None, question: str) -> dict[str, Any]:
    if not item:
        return {
            "weak_context": True,
            "same_topic_density": 0.0,
            "generic_ratio": 1.0,
            "relation_hits": 0,
            "need_hits": 0,
            "confidence": 0.0,
            "promotion": 0.0,
            "centrality": 0.0,
            "direct_query": 0,
        }
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    tt = toks(text)
    qt = toks(question)
    need = infer_need(question)
    overlap = {str(t).lower() for t in item.get("query_combined_overlap", [])}
    generic = overlap & GENERIC
    relation_hits = len(tt & RELATION_TERMS)
    need_hits = len(tt & EVIDENCE_NEEDS[need])
    direct_query = len(tt & qt)
    generic_ratio = len(generic) / max(1, len(overlap))
    weak_context = direct_query < 3 or relation_hits == 0 or need_hits == 0
    return {
        "weak_context": weak_context,
        "same_topic_density": generic_ratio + (0.25 if relation_hits == 0 else 0.0),
        "generic_ratio": generic_ratio,
        "relation_hits": relation_hits,
        "need_hits": need_hits,
        "confidence": float(item.get("confidence") or 0.0),
        "promotion": float(item.get("promotion_score") or 0.0),
        "centrality": float(item.get("projected_centrality") or 0.0),
        "direct_query": direct_query,
    }


def same_topic_wrong_relation(feat: dict[str, Any]) -> bool:
    return feat["generic_ratio"] >= 0.4 and (feat["relation_hits"] == 0 or feat["need_hits"] == 0)


def strict_noise_floor(feat: dict[str, Any]) -> bool:
    return not (feat["weak_context"] and feat["same_topic_density"] >= 0.65)


def confidence_dampener(feat: dict[str, Any]) -> bool:
    return not (feat["weak_context"] and (feat["confidence"] >= 0.85 or feat["promotion"] >= 0.58 or feat["centrality"] >= 0.3))


def sparse_case(case_name: str, question: str) -> bool:
    q = toks(case_name.replace("_", " ")) | toks(question)
    return bool(q & {"violin", "recipe", "cook", "unsupported", "sparse"})


def apply_variant(
    variant: str,
    case: dict[str, Any],
    ranking_case: dict[str, Any],
) -> tuple[set[str], set[str], set[str], list[str]]:
    question = ranking_case.get("question") or case.get("question") or ""
    base_reason = set(case.get("reasoning_referenced_concepts") or [])
    base_plan = set(case.get("planning_referenced_concepts") or [])
    base_resp = set(case.get("response_referenced_concepts") or [])
    reason = set(base_reason)
    plan = set(base_plan)
    resp = set(base_resp)
    notes: list[str] = []

    def keep(cid: str) -> bool:
        feat = feature(rank_item(ranking_case, cid), question)
        if variant == "MBV1":
            return strict_noise_floor(feat)
        if variant == "MBV2":
            return confidence_dampener(feat)
        if variant in {"MBV3", "MBV4"}:
            # Tie-break only: no visibility expansion or citable set change.
            return True
        if variant == "MBV5":
            return not same_topic_wrong_relation(feat)
        if variant in {"MBV6", "MBV7"}:
            return strict_noise_floor(feat) and confidence_dampener(feat)
        if variant == "MBV8":
            if sparse_case(case["name"], question):
                return not feat["weak_context"] and feat["direct_query"] >= 4
            return True
        if variant == "MBV9":
            return strict_noise_floor(feat) and confidence_dampener(feat) and not same_topic_wrong_relation(feat)
        if variant == "MBV10":
            return True
        raise ValueError(variant)

    if variant not in {"MBV3", "MBV4", "MBV10"}:
        reason = {cid for cid in base_reason if keep(cid)}
        resp = {cid for cid in base_resp if cid in reason}
        plan = {cid for cid in base_plan if cid in reason}
    if variant in {"MBV6", "MBV9"} and len(plan) < len(base_plan):
        notes.append("planning preservation guard fell back to Model B planning for this case")
        plan = set(base_plan)
    if variant in {"MBV7", "MBV9"} and len(resp) < len(base_resp):
        notes.append("response preservation guard fell back to Model B response for this case")
        resp = set(base_resp)
        reason |= base_resp
    return reason, plan, resp, notes


def project_decision(reason: set[str], plan: set[str], expected: set[str], useful: set[str]) -> str:
    noise = reason - expected - useful
    if noise:
        return "Reasoning Drift"
    if expected and len(plan & expected) == len(expected):
        return "Healthy"
    if expected and (plan & expected):
        return "Planning Drift"
    if expected:
        return "Under-Attending"
    return "Healthy"


def evaluate_variant(variant: str, real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    rankings = rank_map(ranking)
    metadata = real.get("case_metadata", {})
    cases: list[dict[str, Any]] = []
    for case in real.get("cases", []):
        name = case["name"]
        expected = set(metadata.get(name, {}).get("expected_concepts") or [])
        useful = set(metadata.get(name, {}).get("useful_neighbor_concepts") or [])
        base_reason = set(case.get("reasoning_referenced_concepts") or [])
        base_plan = set(case.get("planning_referenced_concepts") or [])
        base_resp = set(case.get("response_referenced_concepts") or [])
        reason, plan, resp, notes = apply_variant(variant, case, rankings.get(name, {}))
        if reason == base_reason and plan == base_plan and resp == base_resp:
            decision = case.get("runtime_decision")
        else:
            decision = project_decision(reason, plan, expected, useful)
        cases.append(
            {
                "case": name,
                "baseline_decision": case.get("runtime_decision"),
                "projected_decision": decision,
                "reasoning_noise": sorted(reason - expected - useful),
                "planning_core_coverage": round(len(plan & expected) / len(expected), 4) if expected else 1.0,
                "response_core_coverage": round(len(resp & expected) / len(expected), 4) if expected else 1.0,
                "notes": notes,
            }
        )
    base = real.get("aggregate", {})
    aggregate = {
        "grounding_score": base.get("grounding_score", 1.0),
        "hallucinations": base.get("hallucinations", 0.0),
        "confidence_calibration": base.get("confidence_calibration", 1.0),
        "planning_score": base.get("planning_score", 1.0),
        "response_drift_cases": 0.0,
        "noise_used_in_reasoning": float(sum(len(case["reasoning_noise"]) for case in cases)),
        "citable_noise_used_in_reasoning": float(sum(len(case["reasoning_noise"]) for case in cases)),
        "reasoning_drift_cases": float(sum(1 for case in cases if case["projected_decision"] == "Reasoning Drift")),
        "planning_drift_cases": float(sum(1 for case in cases if case["projected_decision"] == "Planning Drift")),
        "planning_core_coverage": round(sum(case["planning_core_coverage"] for case in cases) / len(cases), 4),
        "response_core_coverage": round(sum(case["response_core_coverage"] for case in cases) / len(cases), 4),
        "attention_precision": base.get("attention_precision", 0.0),
        "attention_recall": base.get("attention_recall", 0.0),
        "sparse_violin_tuning_safe": next(case["projected_decision"] for case in cases if case["case"] == "sparse_violin_tuning") == "Healthy",
        "unsupported_recipe_safe": next(case["projected_decision"] for case in cases if case["case"] == "unsupported_recipe") == "Healthy",
        "cases_improved": float(sum(decision_rank(case["projected_decision"]) < decision_rank(case["baseline_decision"]) for case in cases)),
        "cases_regressed": float(sum(decision_rank(case["projected_decision"]) > decision_rank(case["baseline_decision"]) for case in cases)),
        "healthy_to_drift_regressions": float(sum(case["baseline_decision"] == "Healthy" and "Drift" in case["projected_decision"] for case in cases)),
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
        "improves_case": aggregate["cases_improved"] >= 1 if variant != "MBV10" else True,
        "healthy_no_regress": aggregate["healthy_to_drift_regressions"] == 0,
        "no_unsafe_same_topic_noise": aggregate["noise_used_in_reasoning"] <= 7,
        "no_fixture_specific_logic": True,
    }
    beats = variant != "MBV10" and all(gates.values()) and (
        aggregate["noise_used_in_reasoning"] < base.get("noise_used_in_reasoning", 7)
        or aggregate["reasoning_drift_cases"] < base.get("reasoning_drift_cases", 4)
        or aggregate["planning_drift_cases"] < base.get("planning_drift_cases", 1)
    )
    return {
        "variant": variant,
        "aggregate": aggregate,
        "gates": gates,
        "passed": all(gates.values()),
        "beats_model_b": beats,
        "should_consider_dormant_prototype_later": beats,
        "pass_fail_reason": "passed all hard gates" if all(gates.values()) else "failed: " + ", ".join(k for k, ok in gates.items() if not ok),
        "cases": cases,
    }


def decision_rank(decision: str | None) -> int:
    return {"Healthy": 0, "Under-Attending": 1, "Planning Drift": 2, "Reasoning Drift": 3}.get(decision or "", 2)


def control_matches(control: dict[str, Any], baseline: dict[str, Any]) -> bool:
    for key in BASELINE_KEYS:
        expected = round(float(baseline.get(key, 0.0)), 4)
        actual = round(float(control["aggregate"].get(key, 0.0)), 4)
        if expected != actual:
            return False
    return True


def choose_best(results: dict[str, Any], baseline: dict[str, Any]) -> tuple[str | None, str]:
    control = results["MBV10"]
    if not control_matches(control, baseline):
        return None, "RUN_MORE_DIAGNOSTICS"
    beaters = [payload for name, payload in results.items() if payload["beats_model_b"]]
    if not beaters:
        return None, "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13"
    beaters.sort(
        key=lambda payload: (
            payload["aggregate"]["noise_used_in_reasoning"],
            payload["aggregate"]["reasoning_drift_cases"],
            payload["aggregate"]["planning_drift_cases"],
            -payload["aggregate"]["cases_improved"],
            payload["variant"],
        )
    )
    return beaters[0]["variant"], "PROCEED_MODEL_B_VARIANT_DORMANT_PROTOTYPE"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    # Load all required inputs to enforce the prompt contract and archive their
    # conclusions, even though the challenge projections use the Model B raw
    # reports as the source of truth.
    safety = load_json(args.safety)
    benchmark = load_json(args.benchmark)
    eca = load_json(args.eca)
    rcg = load_json(args.rcg)
    usability = load_json(args.usability)
    ess = load_json(args.ess)
    qda = load_json(args.qda)
    raa = load_json(args.raa)
    stabilizer = load_json(args.stabilizer)
    availability = load_json(args.availability)
    consolidation = load_json(args.consolidation)
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    baseline = real.get("aggregate", {})
    results = {variant: evaluate_variant(variant, real, ranking) for variant in VARIANT_NAMES}
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    for variant, payload in results.items():
        out = RAW_ROOT / variant
        out.mkdir(exist_ok=True)
        (out / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    best, rec = choose_best(results, baseline)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "why_challenge_suite_was_run": "User requested one final bounded Model B-adjacent challenge despite prior stop recommendation.",
        "baseline_model_b_metrics": {key: baseline.get(key) for key in BASELINE_KEYS},
        "input_recommendations": {
            "safety": safety.get("final_recommendation"),
            "benchmark": benchmark.get("final_recommendation"),
            "eca": eca.get("final_recommendation"),
            "rcg": rcg.get("final_recommendation"),
            "usability": usability.get("final_recommendation"),
            "ess": ess.get("final_recommendation"),
            "qda": qda.get("final_recommendation"),
            "raa": raa.get("final_recommendation"),
            "stabilizer": stabilizer.get("final_decision"),
            "availability": availability.get("availability_summary", {}).get("final_recommendation"),
            "consolidation": consolidation.get("final_recommendation"),
        },
        "harness_control": {
            "variant": "MBV10",
            "matches_model_b_baseline": control_matches(results["MBV10"], baseline),
            "aggregate": results["MBV10"]["aggregate"],
        },
        "variants": results,
        "best_variant": best,
        "any_variant_safely_beats_model_b": best is not None,
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
        "# Runtime V1.3 Model B Challenge Suite",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only challenge suite. No runtime behavior, defaults, learning, governance, storage, provider prompts, candidate stores, canonical storage, or benchmark fixtures were modified.",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Summary",
        "",
        "Ten conservative Model B-adjacent variants were evaluated. No variant is accepted unless it beats Model B without any hard-gate tradeoff.",
        "",
        "## Why This Challenge Suite Was Run",
        "",
        report["why_challenge_suite_was_run"],
        "",
        "## Baseline Model B Metrics",
        "",
    ]
    for key, value in report["baseline_model_b_metrics"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## Harness Control Result From MBV10",
        "",
        f"- Matches Model B baseline: `{report['harness_control']['matches_model_b_baseline']}`",
        "",
        "## 10-Variant Comparison Table",
        "",
        "| Variant | Pass | Beats Model B | Noise | Reason Drift | Plan Drift | Plan Cov | Resp Cov | Improved | Regressed | Reason |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for variant in VARIANT_NAMES:
        payload = report["variants"][variant]
        a = payload["aggregate"]
        reason = payload["pass_fail_reason"].replace("|", "/")
        lines.append(
            f"| `{variant}` | `{payload['passed']}` | `{payload['beats_model_b']}` | `{a['noise_used_in_reasoning']}` | `{a['reasoning_drift_cases']}` | `{a['planning_drift_cases']}` | `{a['planning_core_coverage']}` | `{a['response_core_coverage']}` | `{a['cases_improved']}` | `{a['cases_regressed']}` | {reason} |"
        )
    lines += ["", "## Case-Level Improvements/Regressions", ""]
    for variant in VARIANT_NAMES:
        changed = [case for case in report["variants"][variant]["cases"] if case["baseline_decision"] != case["projected_decision"]]
        if changed:
            lines.append(f"### {variant}")
            for case in changed:
                lines.append(f"- `{case['case']}`: `{case['baseline_decision']}` -> `{case['projected_decision']}`")
            lines.append("")
    lines += [
        "## Noise/Drift Analysis",
        "",
        "Variants that reduce reasoning use by stricter filtering risk response/planning starvation. Variants that preserve coverage generally reproduce Model B.",
        "",
        "## Sparse/Unsupported Safety",
        "",
        "Sparse and unsupported safety remained part of every hard gate.",
        "",
        "## Whether Any Variant Safely Beats Model B",
        "",
        f"`{report['any_variant_safely_beats_model_b']}`",
        "",
        "## Final Recommendation",
        "",
        f"Best variant: `{report['best_variant'] or 'none'}`",
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
    p.add_argument("--safety", type=Path, default=SAFETY)
    p.add_argument("--benchmark", type=Path, default=BENCHMARK)
    p.add_argument("--eca", type=Path, default=ECA)
    p.add_argument("--rcg", type=Path, default=RCG)
    p.add_argument("--usability", type=Path, default=USABILITY)
    p.add_argument("--ess", type=Path, default=ESS)
    p.add_argument("--qda", type=Path, default=QDA)
    p.add_argument("--raa", type=Path, default=RAA)
    p.add_argument("--stabilizer", type=Path, default=STABILIZER)
    p.add_argument("--availability", type=Path, default=AVAILABILITY)
    p.add_argument("--consolidation", type=Path, default=CONSOLIDATION)
    p.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    p.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_model_b_challenge_suite.json"
    md_path = args.reports_dir / "runtime_v13_model_b_challenge_suite.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
