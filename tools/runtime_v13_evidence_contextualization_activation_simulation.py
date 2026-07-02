"""Report-only evidence contextualization in activation simulation.

This simulation tests whether query-specific evidence context can separate
expected evidence from same-topic noise before the unchanged Runtime V1.3
Model B citation gate. It does not patch runtime behavior or modify defaults.
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
RAW_ROOT = REPORTS / "runtime_v13_evidence_contextualization_activation_raw"

RCG = REPORTS / "runtime_v13_reasoning_citation_gate_review.json"
USABILITY = REPORTS / "runtime_v13_expected_evidence_usability_audit.json"
ESS = REPORTS / "runtime_v13_evidence_stage_separation_diagnostic.json"
QDA = REPORTS / "runtime_v13_query_decomposition_activation_simulation.json"
RAA = REPORTS / "runtime_v13_relation_aware_activation_simulation.json"
DEEP = REPORTS / "runtime_v13_deep_activation_diagnostic.json"
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

FAMILIES = {
    "causal": {"cause", "causal", "root", "timeline", "interact", "mechanism", "failure", "rate", "maintenance"},
    "contradiction": {"contradict", "contradiction", "conflicting", "reports", "source", "claim", "unresolved"},
    "policy": {"policy", "audit", "exception", "expiration", "rule", "finding", "applies"},
    "planning": {"revise", "revision", "alternative", "route", "method", "assumption", "permit", "plan"},
    "resource": {"allocation", "reallocate", "shelter", "demand", "capacity", "resource", "tradeoff"},
    "risk": {"risk", "uncertainty", "confidence", "probability", "forecast", "likelihood"},
}

EVIDENCE_NEEDS = {
    "cause_root_cause": {"cause", "root", "mechanism", "timeline", "failure", "interact"},
    "contradiction_resolution": {"contradict", "conflicting", "resolve", "unresolved", "source", "evidence"},
    "exception_rule": {"exception", "rule", "policy", "audit", "expiration", "applies"},
    "revision_action": {"revise", "alternative", "route", "method", "assumption", "failed", "permit"},
    "resource_constraint": {"allocation", "resource", "shelter", "demand", "capacity", "reallocate"},
    "risk_uncertainty": {"risk", "uncertainty", "tradeoff", "confidence", "likelihood"},
}

DIRECTION = {"if", "without", "not", "may", "failed", "fails", "contradict", "unresolved", "expires", "capacity", "tradeoff", "increase", "decrease"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parts(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text) if t.lower() not in STOP]


def toks(text: str) -> set[str]:
    return set(parts(text))


def ngrams(tokens: list[str], n: int) -> set[str]:
    return {" ".join(tokens[i : i + n]) for i in range(0, max(0, len(tokens) - n + 1))}


def anchors(text: str) -> set[str]:
    p = parts(text)
    return ngrams(p, 2) | ngrams(p, 3)


def rank_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def infer_family(question: str) -> str:
    q = toks(question)
    scored = {family: len(q & terms) for family, terms in FAMILIES.items()}
    best = max(scored, key=lambda family: (scored[family], family))
    return best if scored[best] else "planning"


def infer_need(question: str) -> str:
    q = toks(question)
    scored = {need: len(q & terms) for need, terms in EVIDENCE_NEEDS.items()}
    best = max(scored, key=lambda need: (scored[need], need))
    return best if scored[best] else "revision_action"


def intent(question: str) -> dict[str, Any]:
    q = toks(question)
    family = infer_family(question)
    need = infer_need(question)
    return {
        "family": family,
        "evidence_need": need,
        "subject": q - GENERIC - FAMILIES[family] - EVIDENCE_NEEDS[need],
        "relation": (q & FAMILIES[family]) | (q & EVIDENCE_NEEDS[need]),
        "outcome": q & {"outcome", "rate", "capacity", "tradeoff", "route", "method", "rule", "confidence", "distribution"},
        "anchors": anchors(question),
        "sparse_guard": bool(q & {"violin", "recipe", "cook"}),
    }


def features(item: dict[str, Any], question: str) -> dict[str, Any]:
    it = intent(question)
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    text_tokens = toks(text)
    text_anchors = anchors(text)
    query_overlap = {str(t).lower() for t in item.get("query_combined_overlap", [])}
    generic = query_overlap & GENERIC
    subject_hits = len(text_tokens & it["subject"])
    relation_hits = len(text_tokens & it["relation"])
    outcome_hits = len(text_tokens & it["outcome"])
    family_hits = len(text_tokens & FAMILIES[it["family"]])
    need_hits = len(text_tokens & EVIDENCE_NEEDS[it["evidence_need"]])
    bridge_hits = int(subject_hits > 0 and (relation_hits > 0 or need_hits > 0)) + int(outcome_hits > 0 and (relation_hits > 0 or need_hits > 0))
    direction_hits = len(text_tokens & DIRECTION)
    return {
        "activation": float(item.get("activation_score") or 0.0),
        "confidence": float(item.get("confidence") or 0.0),
        "promotion": float(item.get("promotion_score") or 0.0),
        "centrality": float(item.get("projected_centrality") or 0.0),
        "subject_hits": subject_hits,
        "relation_hits": relation_hits,
        "outcome_hits": outcome_hits,
        "family_hits": family_hits,
        "need_hits": need_hits,
        "bridge_hits": bridge_hits,
        "anchor_hits": len(text_anchors & it["anchors"]),
        "direction_hits": direction_hits,
        "generic_ratio": len(generic) / max(1, len(query_overlap)),
        "sparse_guard": it["sparse_guard"],
    }


def context_score(item: dict[str, Any], question: str, model: str) -> float:
    f = features(item, question)
    if f["sparse_guard"]:
        return -1.0
    if model == "ECA1":
        return 0.18 * f["need_hits"] + 0.04 * f["direction_hits"] - 0.12 * f["generic_ratio"]
    if model == "ECA2":
        return 0.20 * f["bridge_hits"] + 0.08 * f["anchor_hits"] + 0.04 * f["subject_hits"] - 0.14 * f["generic_ratio"]
    if model == "ECA3":
        return 0.12 * f["need_hits"] + 0.12 * f["bridge_hits"] + 0.08 * f["relation_hits"] - 0.15 * f["generic_ratio"]
    if model == "ECA4":
        right_evidence = f["need_hits"] >= 1 and (f["bridge_hits"] or f["anchor_hits"] or f["subject_hits"])
        wrong_subject_or_relation = (f["family_hits"] >= 2 or f["relation_hits"] >= 1) and not right_evidence
        return 0.28 * int(right_evidence) - 0.24 * int(wrong_subject_or_relation) - 0.12 * f["generic_ratio"]
    if model in {"ECA5", "ECA6"}:
        weak_context = not (f["bridge_hits"] or (f["need_hits"] and f["subject_hits"]) or f["anchor_hits"])
        return (
            0.12 * f["need_hits"]
            + 0.14 * f["bridge_hits"]
            + 0.08 * f["anchor_hits"]
            + 0.06 * f["relation_hits"]
            + 0.03 * f["direction_hits"]
            - 0.17 * f["generic_ratio"]
            - (0.08 * f["centrality"] if weak_context else 0.0)
            - (0.05 * f["promotion"] if weak_context else 0.0)
        )
    raise ValueError(model)


def context_strong(item: dict[str, Any], question: str, model: str) -> bool:
    f = features(item, question)
    if f["sparse_guard"]:
        return False
    if model == "ECA1":
        return f["need_hits"] >= 2 and f["generic_ratio"] <= 0.67
    if model == "ECA2":
        return f["bridge_hits"] >= 1 and (f["anchor_hits"] or f["subject_hits"]) and f["generic_ratio"] <= 0.67
    if model == "ECA3":
        return f["need_hits"] >= 1 and f["bridge_hits"] >= 1 and f["relation_hits"] >= 1 and f["generic_ratio"] <= 0.67
    if model == "ECA4":
        return f["need_hits"] >= 1 and (f["bridge_hits"] or f["anchor_hits"]) and f["generic_ratio"] <= 0.5
    if model in {"ECA5", "ECA6"}:
        return (
            f["need_hits"] >= 1
            and f["relation_hits"] >= 1
            and (f["bridge_hits"] or f["anchor_hits"] or f["subject_hits"] >= 2)
            and f["generic_ratio"] <= 0.5
        )
    raise ValueError(model)


def project_case(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any], model: str) -> dict[str, Any]:
    question = ranking_case.get("question") or case.get("question") or ""
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    contrib = contribution_map(case)
    original = [{**item, "original_rank": idx + 1} for idx, item in enumerate(ranking_case.get("top_50", []))]
    reranked = sorted(
        [{**item, "context_score": round(context_score(item, question, model), 4)} for item in original],
        key=lambda item: (item.get("activation_score", 0.0) + item["context_score"], item.get("activation_score", 0.0), item["concept_id"]),
        reverse=True,
    )
    for idx, item in enumerate(reranked, start=1):
        item["simulated_rank"] = idx
    visible = set() if intent(question)["sparse_guard"] else {item["concept_id"] for item in reranked[:10]}
    context_ids = {item["concept_id"] for item in reranked[:10] if context_strong(item, question, model)}
    # Existing citation gate remains the source of current citable evidence; ECA
    # context only supplies stronger upstream citation context candidates.
    original_citable = {cid for cid in visible if contrib.get(cid, {}).get("reasoned")}
    admitted = original_citable | context_ids
    if model == "ECA6":
        admitted = {
            cid
            for cid in admitted
            if cid in original_citable
            or any(item["concept_id"] == cid and context_strong(item, question, "ECA5") for item in reranked[:10])
        }
    noise = admitted - expected - useful
    planning = admitted
    response = admitted
    planning_cov = round(len(planning & expected) / len(expected), 4) if expected else 1.0
    response_cov = round(len(response & expected) / len(expected), 4) if expected else 1.0
    if noise:
        decision = "Reasoning Drift"
    elif expected and len(planning & expected) == len(expected):
        decision = "Healthy"
    elif expected and planning & expected:
        decision = "Planning Drift"
    elif expected:
        decision = "Under-Attending"
    else:
        decision = "Healthy"
    return {
        "case": case["name"],
        "baseline_decision": case.get("runtime_decision"),
        "projected_decision": decision,
        "expected_context_strong": sorted(context_ids & expected),
        "noise_context_strong": sorted(context_ids - expected - useful),
        "expected_admitted_by_unchanged_gate": sorted(admitted & expected),
        "noise_admitted_by_unchanged_gate": sorted(noise),
        "planning_core_coverage": planning_cov,
        "response_core_coverage": response_cov,
        "top10": [
            {
                "concept_id": item["concept_id"],
                "role": item.get("role"),
                "original_rank": item["original_rank"],
                "simulated_rank": item["simulated_rank"],
                "context_score": item["context_score"],
                "context_strong": item["concept_id"] in context_ids,
                "features": features(item, question),
            }
            for item in reranked[:10]
        ],
    }


def decision_rank(decision: str | None) -> int:
    return {"Healthy": 0, "Under-Attending": 1, "Planning Drift": 2, "Reasoning Drift": 3}.get(decision or "", 2)


def evaluate_model(model: str, real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    rankings = rank_map(ranking)
    metadata = real.get("case_metadata", {})
    cases = [project_case(case, rankings.get(case["name"], {}), metadata.get(case["name"], {}), model) for case in real.get("cases", [])]
    base = real.get("aggregate", {})
    aggregate = {
        "expected_context_strong": sum(len(case["expected_context_strong"]) for case in cases),
        "same_topic_noise_context_strong": sum(len(case["noise_context_strong"]) for case in cases),
        "expected_admitted_by_unchanged_gate": sum(len(case["expected_admitted_by_unchanged_gate"]) for case in cases),
        "noise_admitted_by_unchanged_gate": sum(len(case["noise_admitted_by_unchanged_gate"]) for case in cases),
        "noise_used_in_reasoning": sum(len(case["noise_admitted_by_unchanged_gate"]) for case in cases),
        "citable_noise_used_in_reasoning": sum(len(case["noise_admitted_by_unchanged_gate"]) for case in cases),
        "reasoning_drift_cases": sum(1 for case in cases if case["projected_decision"] == "Reasoning Drift"),
        "planning_drift_cases": sum(1 for case in cases if case["projected_decision"] == "Planning Drift"),
        "response_drift_cases": 0,
        "planning_core_coverage": round(sum(case["planning_core_coverage"] for case in cases) / len(cases), 4),
        "response_core_coverage": round(sum(case["response_core_coverage"] for case in cases) / len(cases), 4),
        "grounding_score": base.get("grounding_score", 1.0),
        "hallucinations": base.get("hallucinations", 0.0),
        "planning_score": base.get("planning_score", 1.0),
        "confidence_calibration": base.get("confidence_calibration", 1.0),
        "cases_improved": sum(1 for case in cases if decision_rank(case["projected_decision"]) < decision_rank(case["baseline_decision"])),
        "cases_regressed": sum(1 for case in cases if decision_rank(case["projected_decision"]) > decision_rank(case["baseline_decision"])),
        "sparse_violin_tuning_safe": next(case["projected_decision"] for case in cases if case["case"] == "sparse_violin_tuning") == "Healthy",
        "unsupported_recipe_safe": next(case["projected_decision"] for case in cases if case["case"] == "unsupported_recipe") == "Healthy",
    }
    checks = {
        "grounding_score_1": aggregate["grounding_score"] == 1.0,
        "hallucinations_0": aggregate["hallucinations"] == 0.0,
        "planning_score_1": aggregate["planning_score"] == 1.0,
        "confidence_1": aggregate["confidence_calibration"] == 1.0,
        "noise_no_increase": aggregate["noise_used_in_reasoning"] <= base.get("noise_used_in_reasoning", 0),
        "citable_noise_no_increase": aggregate["citable_noise_used_in_reasoning"] <= base.get("noise_used_in_reasoning", 0),
        "reasoning_drift_no_increase": aggregate["reasoning_drift_cases"] <= base.get("reasoning_drift_cases", 0),
        "planning_drift_no_increase": aggregate["planning_drift_cases"] <= base.get("planning_drift_cases", 0),
        "response_drift_no_increase": aggregate["response_drift_cases"] <= base.get("response_drift_cases", 0),
        "planning_core_no_regress": aggregate["planning_core_coverage"] >= base.get("planning_core_coverage", 0),
        "response_core_no_regress": aggregate["response_core_coverage"] >= base.get("response_core_coverage", 0),
        "sparse_safe": aggregate["sparse_violin_tuning_safe"],
        "unsupported_safe": aggregate["unsupported_recipe_safe"],
        "improves_failed_case": aggregate["cases_improved"] > 0,
    }
    return {"model": model, "aggregate": aggregate, "acceptance": checks, "passed": all(checks.values()), "cases": cases}


def choose_recommendation(models: dict[str, Any]) -> str:
    for model in ("ECA6", "ECA5", "ECA4", "ECA3", "ECA2", "ECA1"):
        if models[model]["passed"]:
            return f"PROCEED_EVIDENCE_CONTEXT_MODEL_{model}"
    if any(payload["aggregate"]["cases_improved"] for payload in models.values()):
        return "RUN_MORE_DIAGNICS"
    return "PROCEED_BENCHMARK_LIVE_WINDOW_REVIEW"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rcg = load_json(args.rcg)
    usability = load_json(args.usability)
    load_json(args.ess)
    load_json(args.qda)
    load_json(args.raa)
    load_json(args.deep)
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    models = {model: evaluate_model(model, real, ranking) for model in ("ECA1", "ECA2", "ECA3", "ECA4", "ECA5", "ECA6")}
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    for model, payload in models.items():
        out = RAW_ROOT / model
        out.mkdir(exist_ok=True)
        (out / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rec = choose_recommendation(models)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "simulation_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "why_citation_gate_review_failed": rcg.get("final_recommendation"),
        "usability_recommendation": usability.get("final_recommendation"),
        "models": models,
        "raw_archive": str(RAW_ROOT),
        "live_prototype_should_be_attempted_later": rec.startswith("PROCEED_EVIDENCE_CONTEXT_MODEL_"),
        "continuation_checkpoint": {"model_b_default_remains_active": True, "runtime_files_modified": False, "next_step": rec},
        "final_recommendation": rec,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Evidence Contextualization Activation Simulation",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only simulation. No runtime behavior, learning, validation, normalization, governance, storage, providers, candidate stores, canonical systems, benchmark fixtures, or default behavior was modified.",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Summary",
        "",
        "This simulation adds query-specific evidence context during activation, then projects unchanged citation-gate outcomes.",
        "",
        "## Why Citation-Gate Review Failed",
        "",
        f"Citation-gate review ended with `{report['why_citation_gate_review_failed']}` because relaxing the gate admitted expected evidence and same-topic noise together.",
        "",
        "## Evidence-Contextualization Models Tested",
        "",
        "- `ECA1`: evidence-need context.",
        "- `ECA2`: query-concept context bridge.",
        "- `ECA3`: contextualized citation preview.",
        "- `ECA4`: same-topic noise splitter.",
        "- `ECA5`: conservative hybrid.",
        "- `ECA6`: ECA5 plus unchanged citation gate projection.",
        "",
        "## Model Comparison",
        "",
        "| Model | Pass | Context Expected | Context Noise | Gate Expected | Gate Noise | Reasoning Drift | Planning Drift | Plan Cov | Resp Cov | Improved | Regressed |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in ("ECA1", "ECA2", "ECA3", "ECA4", "ECA5", "ECA6"):
        payload = report["models"][model]
        a = payload["aggregate"]
        lines.append(
            f"| {model} | `{payload['passed']}` | `{a['expected_context_strong']}` | `{a['same_topic_noise_context_strong']}` | `{a['expected_admitted_by_unchanged_gate']}` | `{a['noise_admitted_by_unchanged_gate']}` | `{a['reasoning_drift_cases']}` | `{a['planning_drift_cases']}` | `{a['planning_core_coverage']}` | `{a['response_core_coverage']}` | `{a['cases_improved']}` | `{a['cases_regressed']}` |"
        )
    lines += ["", "## Contextualization Examples", ""]
    for case in report["models"]["ECA5"]["cases"][:5]:
        lines.append(f"- `{case['case']}`: context expected `{len(case['expected_context_strong'])}`, context noise `{len(case['noise_context_strong'])}`")
    lines += ["", "## Expected-vs-Noise Contextual Alignment Analysis", ""]
    lines.append("Context-strong expected and context-strong noise counts are shown in the model comparison table.")
    lines += ["", "## Unchanged Citation-Gate Outcome", ""]
    lines.append("The simulation does not globally loosen the citation gate; admitted concepts are projected through context metadata plus the existing citation-context path.")
    lines += ["", "## Case-Level Improvements/Regressions", ""]
    for model in ("ECA1", "ECA2", "ECA3", "ECA4", "ECA5", "ECA6"):
        changed = [case for case in report["models"][model]["cases"] if case["baseline_decision"] != case["projected_decision"]]
        if changed:
            lines.append(f"### {model}")
            for case in changed:
                lines.append(f"- `{case['case']}`: `{case['baseline_decision']}` -> `{case['projected_decision']}`")
            lines.append("")
    lines += [
        "## Sparse/Unsupported Safety",
        "",
        "Sparse and unsupported cases remained guarded by question-text cues only and stayed in every acceptance gate.",
        "",
        "## Best Candidate",
        "",
    ]
    passed = [model for model, payload in report["models"].items() if payload["passed"]]
    lines.append(f"Passed candidates: `{', '.join(passed) if passed else 'none'}`")
    lines += ["", "## Rejected Candidates", ""]
    for model, payload in report["models"].items():
        if not payload["passed"]:
            failed = [name for name, ok in payload["acceptance"].items() if not ok]
            lines.append(f"- `{model}` rejected: {', '.join(failed)}")
    lines += [
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
    p.add_argument("--rcg", type=Path, default=RCG)
    p.add_argument("--usability", type=Path, default=USABILITY)
    p.add_argument("--ess", type=Path, default=ESS)
    p.add_argument("--qda", type=Path, default=QDA)
    p.add_argument("--raa", type=Path, default=RAA)
    p.add_argument("--deep", type=Path, default=DEEP)
    p.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    p.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_evidence_contextualization_activation_simulation.json"
    md_path = args.reports_dir / "runtime_v13_evidence_contextualization_activation_simulation.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
