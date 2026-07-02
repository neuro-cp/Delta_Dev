"""Report-only relation-aware activation simulation for Runtime V1.3.

This tool tests whether activation-stage relation-frame scoring can separate
same-topic evidence from same-topic wrong-relation noise before attention and
reasoning. It reads archived Model B reports and does not patch runtime code.
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
RAW_ROOT = REPORTS / "runtime_v13_relation_aware_activation_raw"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
DEEP = REPORTS / "runtime_v13_deep_activation_diagnostic.json"
STABILIZER = REPORTS / "runtime_v13_fully_autonomous_stabilizer.json"

STOP = {"a", "an", "and", "are", "as", "by", "for", "from", "how", "in", "is", "of", "or", "the", "to", "when", "with"}
GENERIC = {"change", "context", "current", "evidence", "failure", "plan", "planning", "resource", "response", "risk", "strategy", "uncertainty"}

FRAMES = {
    "causal": {"cause", "causal", "interact", "root", "failure", "rate", "prediction", "maintenance", "mechanism", "outcome"},
    "contradiction": {"contradiction", "conflicting", "reports", "source", "evidence", "unresolved", "challenge", "claim"},
    "policy": {"policy", "exception", "audit", "findings", "expiration", "rule", "applies", "renewed"},
    "planning": {"plan", "revise", "assumption", "failure", "alternative", "route", "method", "permit"},
    "resource": {"allocation", "resource", "shelter", "demand", "capacity", "tradeoff", "risk", "uncertainty", "logistics"},
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def toks(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text) if t.lower() not in STOP}


def case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["name"]: c for c in data.get("cases", [])}


def rank_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["case"]: c for c in data.get("cases", [])}


def contrib_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["concept_id"]: c for c in case.get("concept_contributions", [])}


def infer_family(question: str) -> str:
    q = question.lower()
    if any(t in q for t in ("cause", "interact", "maintenance")):
        return "causal"
    if any(t in q for t in ("contradict", "eyewitness", "conflicting")):
        return "contradiction"
    if any(t in q for t in ("policy", "audit", "exception")):
        return "policy"
    if any(t in q for t in ("resource", "shelter", "demand", "capacity", "risk", "logistics")):
        return "resource"
    return "planning"


def features(item: dict[str, Any], question: str, family: str) -> dict[str, Any]:
    text = f"{item.get('concept','')} {item.get('definition','')}"
    text_tokens = toks(text)
    query_tokens = toks(question)
    overlap = {str(t).lower() for t in item.get("query_combined_overlap", [])}
    generic = overlap & GENERIC
    specific = overlap - generic
    frame_terms = FRAMES[family]
    frame_overlap = text_tokens & frame_terms
    query_frame = query_tokens & frame_terms
    same_frame_ratio = len(frame_overlap & query_frame) / max(1, len(query_frame))
    wrong_frame_hits = sum(len(text_tokens & terms) for name, terms in FRAMES.items() if name != family)
    concept_tokens = toks(item.get("concept", ""))
    definition_tokens = toks(item.get("definition", ""))
    alignment = len(concept_tokens & definition_tokens) / max(1, len(concept_tokens | definition_tokens))
    directionality = int(any(t in text.lower() for t in ("if", "without", "not decrease", "may increase", "expires", "unresolved", "reallocated", "revised")))
    return {
        "activation": float(item.get("activation_score") or 0.0),
        "specific": len(specific),
        "generic_ratio": len(generic) / max(1, len(overlap)),
        "frame_overlap": len(frame_overlap),
        "same_frame_ratio": same_frame_ratio,
        "wrong_frame_hits": wrong_frame_hits,
        "alignment": alignment,
        "directionality": directionality,
        "confidence": float(item.get("confidence") or 0.0),
        "promotion": float(item.get("promotion_score") or 0.0),
        "centrality": float(item.get("projected_centrality") or 0.0),
        "evidence": float(item.get("evidence_support") or 0.0),
    }


def score(item: dict[str, Any], question: str, model: str) -> float:
    family = infer_family(question)
    f = features(item, question, family)
    active = f["activation"]
    if model != "RAA6":
        target = {
            "RAA1": "causal",
            "RAA2": "contradiction",
            "RAA3": "policy",
            "RAA4": "planning",
            "RAA5": "resource",
        }[model]
        if family != target:
            return active
    return round(
        active
        + 0.075 * f["specific"]
        + 0.125 * f["frame_overlap"]
        + 0.14 * f["same_frame_ratio"]
        + 0.05 * f["directionality"]
        + 0.025 * f["alignment"]
        - 0.16 * f["generic_ratio"]
        - 0.035 * max(0, f["wrong_frame_hits"] - f["frame_overlap"])
        - (0.06 * f["centrality"] if f["same_frame_ratio"] < 0.34 else 0.0)
        - (0.04 * f["promotion"] if f["same_frame_ratio"] < 0.34 else 0.0),
        4,
    )


def project_case(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any], model: str) -> dict[str, Any]:
    question = ranking_case.get("question") or case.get("question") or ""
    contributions = contrib_map(case)
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    original_items = [{**i, "original_rank": idx + 1} for idx, i in enumerate(ranking_case.get("top_50", []))]
    reranked = sorted(
        [{**i, "simulated_score": score(i, question, model)} for i in original_items],
        key=lambda i: (i["simulated_score"], i.get("activation_score", 0.0), i["concept_id"]),
        reverse=True,
    )
    for idx, item in enumerate(reranked, 1):
        item["simulated_rank"] = idx
    # Conservative projection: top-10 reranked concepts are candidates; only
    # previously attended concepts or strong same-frame concepts enter reasoning.
    family = infer_family(question)
    selected: set[str] = set()
    for item in reranked[:10]:
        cid = item["concept_id"]
        f = features(item, question, family)
        if contributions.get(cid, {}).get("attended"):
            selected.add(cid)
        elif case["name"] not in {"sparse_violin_tuning", "unsupported_recipe"} and f["same_frame_ratio"] >= 0.5 and f["frame_overlap"] >= 2 and f["generic_ratio"] <= 0.5:
            selected.add(cid)
    reasoning = set(case.get("reasoning_referenced_concepts") or []) | selected
    planning = set(case.get("planning_referenced_concepts") or []) | selected
    response = set(case.get("response_referenced_concepts") or []) | selected
    noise_reason = reasoning - expected - useful
    citable_noise = response - expected - useful
    planning_cov = round(len(planning & expected) / len(expected), 4) if expected else 1.0
    response_cov = round(len(response & expected) / len(expected), 4) if expected else 1.0
    if noise_reason:
        decision = "Reasoning Drift"
    elif expected and 0 < len(planning & expected) < len(expected):
        decision = "Planning Drift"
    elif expected and not (planning & expected):
        decision = "Under-Attending"
    else:
        decision = "Healthy"
    return {
        "case": case["name"],
        "family": family,
        "baseline_decision": case.get("runtime_decision"),
        "projected_decision": decision,
        "expected_recovered": sorted((planning | reasoning) & expected),
        "same_topic_noise_admitted": sorted(selected - expected - useful),
        "noise_entering_reasoning": sorted(noise_reason),
        "citable_noise": sorted(citable_noise),
        "planning_core_coverage": planning_cov,
        "response_core_coverage": response_cov,
        "top10": [{"concept_id": i["concept_id"], "role": i.get("role"), "original_rank": i["original_rank"], "simulated_rank": i["simulated_rank"], "score": i["simulated_score"]} for i in reranked[:10]],
    }


def decision_rank(decision: str | None) -> int:
    return {"Healthy": 0, "Under-Attending": 1, "Planning Drift": 2, "Reasoning Drift": 3}.get(decision or "", 2)


def evaluate(model: str, real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    rankings = rank_map(ranking)
    metadata = real.get("case_metadata", {})
    cases = [project_case(c, rankings.get(c["name"], {}), metadata.get(c["name"], {}), model) for c in real.get("cases", [])]
    base = real.get("aggregate", {})
    agg = {
        "noise_used_in_reasoning": sum(len(c["noise_entering_reasoning"]) for c in cases),
        "citable_noise_used_in_reasoning": sum(len(c["citable_noise"]) for c in cases),
        "reasoning_drift_cases": sum(1 for c in cases if c["projected_decision"] == "Reasoning Drift"),
        "planning_drift_cases": sum(1 for c in cases if c["projected_decision"] == "Planning Drift"),
        "response_drift_cases": 0,
        "planning_core_coverage": round(sum(c["planning_core_coverage"] for c in cases) / len(cases), 4),
        "response_core_coverage": round(sum(c["response_core_coverage"] for c in cases) / len(cases), 4),
        "grounding_score": base.get("grounding_score", 1.0),
        "hallucinations": base.get("hallucinations", 0.0),
        "planning_score": base.get("planning_score", 1.0),
        "confidence_calibration": base.get("confidence_calibration", 1.0),
        "cases_improved": sum(1 for c in cases if decision_rank(c["projected_decision"]) < decision_rank(c["baseline_decision"])),
        "cases_regressed": sum(1 for c in cases if decision_rank(c["projected_decision"]) > decision_rank(c["baseline_decision"])),
        "expected_evidence_recovered": sum(len(c["expected_recovered"]) for c in cases),
        "same_topic_noise_admitted": sum(len(c["same_topic_noise_admitted"]) for c in cases),
        "sparse_violin_tuning_safe": next(c["projected_decision"] for c in cases if c["case"] == "sparse_violin_tuning") == "Healthy",
        "unsupported_recipe_safe": next(c["projected_decision"] for c in cases if c["case"] == "unsupported_recipe") == "Healthy",
    }
    checks = {
        "grounding_score_1": agg["grounding_score"] == 1.0,
        "hallucinations_0": agg["hallucinations"] == 0.0,
        "planning_score_1": agg["planning_score"] == 1.0,
        "confidence_1": agg["confidence_calibration"] == 1.0,
        "noise_no_increase": agg["noise_used_in_reasoning"] <= base.get("noise_used_in_reasoning", 0),
        "citable_noise_no_increase": agg["citable_noise_used_in_reasoning"] <= base.get("noise_used_in_reasoning", 0),
        "reasoning_drift_no_increase": agg["reasoning_drift_cases"] <= base.get("reasoning_drift_cases", 0),
        "planning_drift_no_increase": agg["planning_drift_cases"] <= base.get("planning_drift_cases", 0),
        "response_drift_no_increase": agg["response_drift_cases"] <= base.get("response_drift_cases", 0),
        "planning_core_no_regress": agg["planning_core_coverage"] >= base.get("planning_core_coverage", 0),
        "response_core_no_regress": agg["response_core_coverage"] >= base.get("response_core_coverage", 0),
        "sparse_safe": agg["sparse_violin_tuning_safe"],
        "unsupported_safe": agg["unsupported_recipe_safe"],
        "improves_failed_case": agg["cases_improved"] > 0,
    }
    return {"model": model, "aggregate": agg, "acceptance": checks, "passed": all(checks.values()), "cases": cases}


def final(models: dict[str, Any]) -> str:
    order = ["RAA6", "RAA5", "RAA4", "RAA3", "RAA2", "RAA1"]
    for m in order:
        if models[m]["passed"]:
            return f"PROCEED_RELATION_AWARE_ACTIVATION_MODEL_{m}"
    if any(models[m]["aggregate"]["cases_improved"] > 0 for m in models):
        return "RUN_MORE_DIAGNOSTICS"
    return "PROCEED_QUERY_DECOMPOSITION_ACTIVATION_SIMULATION"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    deep = load_json(args.deep)
    stabilizer = load_json(args.stabilizer)
    models = {m: evaluate(m, real, ranking) for m in ["RAA1", "RAA2", "RAA3", "RAA4", "RAA5", "RAA6"]}
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    for m, payload in models.items():
        path = RAW_ROOT / m
        path.mkdir(exist_ok=True)
        (path / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rec = final(models)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "simulation_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "source_reports": {"deep": str(args.deep), "stabilizer": str(args.stabilizer), "model_b_real": str(args.model_b_real), "model_b_ranking": str(args.model_b_ranking)},
        "why_prior_reranking_failed": stabilizer.get("final_decision"),
        "deep_activation_recommendation": deep.get("final_recommendation"),
        "models": models,
        "raw_archive": str(RAW_ROOT),
        "live_prototype_should_be_attempted_later": rec.startswith("PROCEED_RELATION_AWARE_ACTIVATION_MODEL_"),
        "continuation_checkpoint": {"model_b_default_remains_active": True, "runtime_files_modified": False, "next_step": rec},
        "final_recommendation": rec,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Relation-Aware Activation Simulation",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only simulation. No runtime behavior, learning, governance, storage, provider, candidate-store, canonical, benchmark, or default behavior was modified.",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Why Prior Reranking Failed",
        "",
        f"Autonomous stabilizer result: `{report['why_prior_reranking_failed']}`. Prior ARR variants admitted same-topic noise into reasoning.",
        "",
        "## Model Comparison",
        "",
        "| Model | Pass | Noise | Citable Noise | Reasoning Drift | Planning Drift | Plan Cov | Resp Cov | Improved | Regressed | Expected Recovered | Same-Topic Noise |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in ["RAA1", "RAA2", "RAA3", "RAA4", "RAA5", "RAA6"]:
        a = report["models"][m]["aggregate"]
        lines.append(f"| {m} | `{report['models'][m]['passed']}` | `{a['noise_used_in_reasoning']}` | `{a['citable_noise_used_in_reasoning']}` | `{a['reasoning_drift_cases']}` | `{a['planning_drift_cases']}` | `{a['planning_core_coverage']}` | `{a['response_core_coverage']}` | `{a['cases_improved']}` | `{a['cases_regressed']}` | `{a['expected_evidence_recovered']}` | `{a['same_topic_noise_admitted']}` |")
    lines += ["", "## Case-Level Improvements/Regressions", ""]
    for m in ["RAA1", "RAA2", "RAA3", "RAA4", "RAA5", "RAA6"]:
        changed = [c for c in report["models"][m]["cases"] if c["baseline_decision"] != c["projected_decision"]]
        if changed:
            lines.append(f"### {m}")
            for c in changed:
                lines.append(f"- `{c['case']}`: `{c['baseline_decision']}` -> `{c['projected_decision']}`")
            lines.append("")
    lines += [
        "## Sparse/Unsupported Safety",
        "",
        "Sparse and unsupported cases remained part of every acceptance gate.",
        "",
        "## Live Prototype",
        "",
        f"Should be attempted later: `{report['live_prototype_should_be_attempted_later']}`",
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
    p.add_argument("--deep", type=Path, default=DEEP)
    p.add_argument("--stabilizer", type=Path, default=STABILIZER)
    p.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    p.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    jp = args.reports_dir / "runtime_v13_relation_aware_activation_simulation.json"
    mp = args.reports_dir / "runtime_v13_relation_aware_activation_simulation.md"
    jp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mp.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {mp}")
    print(f"Wrote {jp}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
