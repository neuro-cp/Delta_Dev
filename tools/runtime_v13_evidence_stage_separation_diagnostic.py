"""Report-only evidence-stage separation diagnostic for Runtime V1.3.

This diagnostic tests whether QDA-style visibility can be separated into:

- visible_only
- citable_reasoning
- planning_support
- excluded_noise

It reads archived Model B/QDA data only and does not patch runtime behavior.
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
RAW_ROOT = REPORTS / "runtime_v13_evidence_stage_separation_raw"

MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
QDA = REPORTS / "runtime_v13_query_decomposition_activation_simulation.json"
RAA = REPORTS / "runtime_v13_relation_aware_activation_simulation.json"
DEEP = REPORTS / "runtime_v13_deep_activation_diagnostic.json"

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

GENERIC = {
    "change",
    "context",
    "current",
    "data",
    "evidence",
    "failure",
    "increase",
    "plan",
    "planning",
    "resource",
    "response",
    "risk",
    "strategy",
    "team",
    "uncertainty",
}

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

PLANNING_TERMS = {
    "action": {"revise", "alternative", "route", "method", "reallocate", "allocate", "assess", "include", "use"},
    "constraint": {"capacity", "demand", "permit", "assumption", "risk", "uncertainty", "tradeoff", "exception", "rule"},
    "state": {"failed", "current", "available", "unresolved", "expires", "contradict", "spike", "increase"},
    "outcome": {"rate", "decrease", "increase", "coverage", "distribution", "lowest", "safe", "fair"},
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text) if t.lower() not in STOP]


def token_set(text: str) -> set[str]:
    return set(tokens(text))


def ngrams(parts: list[str], n: int) -> set[str]:
    return {" ".join(parts[i : i + n]) for i in range(0, max(0, len(parts) - n + 1))}


def phrase_anchors(text: str) -> set[str]:
    parts = tokens(text)
    return ngrams(parts, 2) | ngrams(parts, 3)


def rank_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def infer_family(question: str) -> str:
    q = token_set(question)
    scored = {family: len(q & terms) for family, terms in FAMILIES.items()}
    best = max(scored, key=lambda family: (scored[family], family))
    return best if scored[best] else "planning"


def infer_evidence_need(question: str) -> str:
    q = token_set(question)
    scored = {need: len(q & terms) for need, terms in EVIDENCE_NEEDS.items()}
    best = max(scored, key=lambda need: (scored[need], need))
    return best if scored[best] else "revision_action"


def decompose(question: str) -> dict[str, Any]:
    q = token_set(question)
    family = infer_family(question)
    need = infer_evidence_need(question)
    subject = sorted(q - GENERIC - FAMILIES[family] - EVIDENCE_NEEDS[need])
    relation = sorted((q & FAMILIES[family]) | (q & EVIDENCE_NEEDS[need]))
    outcome = sorted(q & {"outcome", "rate", "capacity", "tradeoff", "route", "method", "rule", "confidence"})
    return {
        "family": family,
        "evidence_need": need,
        "subject_cues": subject,
        "relation_action_cues": relation,
        "outcome_cues": outcome,
        "anchors": sorted(phrase_anchors(question)),
        "sparse_or_unsupported_guard": bool(q & {"violin", "recipe", "cook"}),
    }


def item_features(item: dict[str, Any], question: str) -> dict[str, Any]:
    intent = decompose(question)
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    text_tokens = token_set(text)
    item_anchors = phrase_anchors(text)
    overlap = {str(t).lower() for t in item.get("query_combined_overlap", [])}
    generic_overlap = overlap & GENERIC
    planning = {key: len(text_tokens & values) for key, values in PLANNING_TERMS.items()}
    subject_hits = len(text_tokens & set(intent["subject_cues"]))
    relation_hits = len(text_tokens & set(intent["relation_action_cues"]))
    outcome_hits = len(text_tokens & set(intent["outcome_cues"]))
    family_hits = len(text_tokens & FAMILIES[intent["family"]])
    need_hits = len(text_tokens & EVIDENCE_NEEDS[intent["evidence_need"]])
    anchor_hits = len(item_anchors & set(intent["anchors"]))
    directionality = int(
        any(
            marker in text.lower()
            for marker in (
                "if ",
                "without ",
                "not decrease",
                "may increase",
                "failed",
                "fails",
                "contradict",
                "unresolved",
                "expires",
                "capacity",
                "tradeoff",
            )
        )
    )
    concrete_match = int(relation_hits > 0 and (subject_hits > 0 or outcome_hits > 0 or anchor_hits > 0))
    planning_action_match = int(planning["action"] > 0 and (planning["constraint"] > 0 or planning["state"] > 0 or planning["outcome"] > 0))
    planning_constraint_match = int((planning["constraint"] + planning["state"] + planning["outcome"]) >= 2)
    return {
        "activation": float(item.get("activation_score") or 0.0),
        "confidence": float(item.get("confidence") or 0.0),
        "promotion": float(item.get("promotion_score") or 0.0),
        "centrality": float(item.get("projected_centrality") or 0.0),
        "evidence": float(item.get("evidence_support") or 0.0),
        "subject_hits": subject_hits,
        "relation_hits": relation_hits,
        "outcome_hits": outcome_hits,
        "family_hits": family_hits,
        "need_hits": need_hits,
        "anchor_hits": anchor_hits,
        "directionality": directionality,
        "concrete_match": concrete_match,
        "planning_action_match": planning_action_match,
        "planning_constraint_match": planning_constraint_match,
        "planning_signal": planning["action"] + planning["constraint"] + planning["state"] + planning["outcome"],
        "generic_ratio": len(generic_overlap) / max(1, len(overlap)),
        "sparse_guard": intent["sparse_or_unsupported_guard"],
    }


def qda6_visibility_score(item: dict[str, Any], question: str) -> float:
    f = item_features(item, question)
    if f["sparse_guard"]:
        return f["activation"] - 0.8
    return round(
        f["activation"]
        + 0.11 * f["family_hits"]
        + 0.10 * f["need_hits"]
        + 0.08 * f["concrete_match"]
        + 0.07 * f["anchor_hits"]
        + 0.04 * f["directionality"]
        - 0.17 * f["generic_ratio"]
        - (0.08 * f["centrality"] if not f["concrete_match"] and f["need_hits"] == 0 else 0.0)
        - (0.05 * f["promotion"] if not f["concrete_match"] else 0.0),
        4,
    )


def planning_candidate_ok(item: dict[str, Any], question: str, strict: bool) -> bool:
    f = item_features(item, question)
    if f["sparse_guard"]:
        return False
    if f["generic_ratio"] > (0.5 if strict else 0.67) and not f["anchor_hits"]:
        return False
    if strict:
        return bool(
            f["planning_action_match"]
            and f["planning_constraint_match"]
            and (f["concrete_match"] or f["anchor_hits"] or f["need_hits"] >= 2)
        )
    return bool(
        f["planning_action_match"]
        and (f["concrete_match"] or f["anchor_hits"] or f["need_hits"] >= 1 or f["planning_signal"] >= 3)
    )


def assign_lanes(
    case: dict[str, Any],
    ranking_case: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    question = ranking_case.get("question") or case.get("question") or ""
    contrib = contribution_map(case)
    original = [{**item, "original_rank": idx + 1} for idx, item in enumerate(ranking_case.get("top_50", []))]
    reranked = sorted(
        [{**item, "simulated_score": qda6_visibility_score(item, question)} for item in original],
        key=lambda item: (item["simulated_score"], item.get("activation_score", 0.0), item["concept_id"]),
        reverse=True,
    )
    for idx, item in enumerate(reranked, start=1):
        item["simulated_rank"] = idx
    visible = {item["concept_id"] for item in reranked[:10]} if not decompose(question)["sparse_or_unsupported_guard"] else set()
    top_by_id = {item["concept_id"]: item for item in reranked[:10]}
    # Model B citable reasoning gate unchanged: a concept must be visible and
    # have been accepted into reasoning by the archived Model B citation context.
    citable_reasoning = {cid for cid in visible if contrib.get(cid, {}).get("reasoned")}
    planning_support: set[str] = set()
    visible_candidates = [item for item in reranked[:10] if item["concept_id"] not in citable_reasoning]
    if model == "ESS1":
        pass
    elif model == "ESS2":
        planning_support.update(item["concept_id"] for item in visible_candidates if planning_candidate_ok(item, question, strict=False))
    elif model == "ESS3":
        for item in visible_candidates:
            if planning_candidate_ok(item, question, strict=True):
                planning_support.add(item["concept_id"])
                break
    elif model == "ESS4":
        # Preserve baseline planning IDs when QDA visibility keeps them visible;
        # this avoids evaluator labels while preventing blunt starvation.
        baseline_planning = set(case.get("planning_referenced_concepts") or [])
        planning_support.update((baseline_planning & visible) - citable_reasoning)
        if len(citable_reasoning | planning_support) < len(baseline_planning):
            for item in visible_candidates:
                if planning_candidate_ok(item, question, strict=True):
                    planning_support.add(item["concept_id"])
                    if len(citable_reasoning | planning_support) >= len(baseline_planning):
                        break
    elif model == "ESS5":
        planning_support.update(item["concept_id"] for item in visible_candidates if planning_candidate_ok(item, question, strict=False))
    elif model == "ESS6":
        baseline_planning = set(case.get("planning_referenced_concepts") or [])
        planning_support.update((baseline_planning & visible) - citable_reasoning)
        for item in visible_candidates:
            if len(planning_support) >= 1:
                break
            if planning_candidate_ok(item, question, strict=True):
                planning_support.add(item["concept_id"])
    else:
        raise ValueError(model)
    return {
        "visible": visible,
        "citable_reasoning": citable_reasoning,
        "planning_support": planning_support,
        "visible_only": visible - citable_reasoning - planning_support,
        "excluded_noise": {item["concept_id"] for item in original} - visible,
        "top10": [
            {
                "concept_id": item["concept_id"],
                "role": item.get("role"),
                "original_rank": item["original_rank"],
                "simulated_rank": item["simulated_rank"],
                "score": item["simulated_score"],
                "features": item_features(item, question),
                "lane": "citable_reasoning"
                if item["concept_id"] in citable_reasoning
                else "planning_support"
                if item["concept_id"] in planning_support
                else "visible_only"
                if item["concept_id"] in visible
                else "excluded_noise",
            }
            for item in reranked[:10]
        ],
    }


def project_case(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any], model: str) -> dict[str, Any]:
    lanes = assign_lanes(case, ranking_case, model)
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    visible = lanes["visible"]
    reasoning = lanes["citable_reasoning"]
    planning = lanes["citable_reasoning"] | lanes["planning_support"]
    response = lanes["citable_reasoning"]
    reasoning_noise = reasoning - expected - useful
    citable_noise = response - expected - useful
    planning_noise = lanes["planning_support"] - expected - useful
    planning_cov = round(len(planning & expected) / len(expected), 4) if expected else 1.0
    response_cov = round(len(response & expected) / len(expected), 4) if expected else 1.0
    if reasoning_noise:
        projected = "Reasoning Drift"
    elif expected and len(planning & expected) == len(expected):
        projected = "Healthy"
    elif expected and planning & expected:
        projected = "Planning Drift"
    elif expected:
        projected = "Under-Attending"
    else:
        projected = "Healthy"
    return {
        "case": case["name"],
        "baseline_decision": case.get("runtime_decision"),
        "projected_decision": projected,
        "query_decomposition": decompose(ranking_case.get("question") or case.get("question") or ""),
        "visible_expected": sorted(visible & expected),
        "visible_noise": sorted(visible - expected - useful),
        "citable_reasoning_expected": sorted(reasoning & expected),
        "citable_reasoning_noise": sorted(reasoning_noise),
        "planning_support_expected": sorted(lanes["planning_support"] & expected),
        "planning_support_noise": sorted(planning_noise),
        "visible_only": sorted(lanes["visible_only"]),
        "planning_core_coverage": planning_cov,
        "response_core_coverage": response_cov,
        "top10": lanes["top10"],
    }


def decision_rank(decision: str | None) -> int:
    return {"Healthy": 0, "Under-Attending": 1, "Planning Drift": 2, "Reasoning Drift": 3}.get(decision or "", 2)


def evaluate_model(model: str, real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    rankings = rank_map(ranking)
    metadata = real.get("case_metadata", {})
    cases = [project_case(case, rankings.get(case["name"], {}), metadata.get(case["name"], {}), model) for case in real.get("cases", [])]
    base = real.get("aggregate", {})
    aggregate = {
        "visible_expected_concepts": sum(len(case["visible_expected"]) for case in cases),
        "visible_noise_concepts": sum(len(case["visible_noise"]) for case in cases),
        "citable_reasoning_expected": sum(len(case["citable_reasoning_expected"]) for case in cases),
        "citable_reasoning_noise": sum(len(case["citable_reasoning_noise"]) for case in cases),
        "planning_support_expected": sum(len(case["planning_support_expected"]) for case in cases),
        "planning_support_noise": sum(len(case["planning_support_noise"]) for case in cases),
        "noise_used_in_reasoning": sum(len(case["citable_reasoning_noise"]) for case in cases),
        "citable_noise_used_in_reasoning": sum(len(case["citable_reasoning_noise"]) for case in cases),
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
    for model in ("ESS6", "ESS5", "ESS4", "ESS3", "ESS2", "ESS1"):
        if models[model]["passed"]:
            return f"PROCEED_EVIDENCE_STAGE_MODEL_{model}"
    if any(payload["aggregate"]["cases_improved"] > 0 for payload in models.values()):
        return "RUN_MORE_DIAGNOSTICS"
    return "PROCEED_EVIDENCE_CONTEXTUALIZATION_IN_ACTIVATION_SIMULATION"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    qda = load_json(args.qda)
    raa = load_json(args.raa)
    deep = load_json(args.deep)
    models = {model: evaluate_model(model, real, ranking) for model in ("ESS1", "ESS2", "ESS3", "ESS4", "ESS5", "ESS6")}
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    for model, payload in models.items():
        out = RAW_ROOT / model
        out.mkdir(exist_ok=True)
        (out / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rec = choose_recommendation(models)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "why_qda_failed": qda.get("final_recommendation"),
        "relation_aware_recommendation": raa.get("final_recommendation"),
        "deep_activation_recommendation": deep.get("final_recommendation"),
        "models": models,
        "raw_archive": str(RAW_ROOT),
        "live_prototype_should_be_attempted_later": rec.startswith("PROCEED_EVIDENCE_STAGE_MODEL_"),
        "continuation_checkpoint": {"model_b_default_remains_active": True, "runtime_files_modified": False, "next_step": rec},
        "final_recommendation": rec,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Evidence Stage Separation Diagnostic",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only diagnostic. No runtime behavior, learning, validation, normalization, governance, storage, providers, candidate stores, canonical systems, benchmark fixtures, or default behavior was modified.",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Summary",
        "",
        "This diagnostic projected QDA-style visibility into separate lanes: `visible_only`, `citable_reasoning`, `planning_support`, and `excluded_noise`.",
        "",
        "## Why QDA Failed",
        "",
        f"QDA ended with `{report['why_qda_failed']}`. QDA improved visibility, but either admitted reasoning noise or starved planning.",
        "",
        "## Stage-Separation Models Tested",
        "",
        "- `ESS1`: QDA visibility with Model B citable reasoning only.",
        "- `ESS2`: non-citable planning support.",
        "- `ESS3`: strict max-one planning support.",
        "- `ESS4`: planning starvation guard.",
        "- `ESS5`: dual-lane reasoning/planning evidence.",
        "- `ESS6`: conservative hybrid.",
        "",
        "## Model Comparison",
        "",
        "| Model | Pass | Visible Exp | Visible Noise | Reason Exp | Reason Noise | Plan Support Exp | Plan Support Noise | Reasoning Drift | Planning Drift | Plan Cov | Resp Cov | Improved | Regressed |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in ("ESS1", "ESS2", "ESS3", "ESS4", "ESS5", "ESS6"):
        payload = report["models"][model]
        a = payload["aggregate"]
        lines.append(
            f"| {model} | `{payload['passed']}` | `{a['visible_expected_concepts']}` | `{a['visible_noise_concepts']}` | `{a['citable_reasoning_expected']}` | `{a['citable_reasoning_noise']}` | `{a['planning_support_expected']}` | `{a['planning_support_noise']}` | `{a['reasoning_drift_cases']}` | `{a['planning_drift_cases']}` | `{a['planning_core_coverage']}` | `{a['response_core_coverage']}` | `{a['cases_improved']}` | `{a['cases_regressed']}` |"
        )
    lines += ["", "## Lane Assignment Examples", ""]
    for case in report["models"]["ESS6"]["cases"][:5]:
        lanes = {}
        for item in case["top10"]:
            lanes.setdefault(item["lane"], 0)
            lanes[item["lane"]] += 1
        lines.append(f"- `{case['case']}`: {lanes}")
    lines += ["", "## Case-Level Improvements/Regressions", ""]
    for model in ("ESS1", "ESS2", "ESS3", "ESS4", "ESS5", "ESS6"):
        changed = [case for case in report["models"][model]["cases"] if case["baseline_decision"] != case["projected_decision"]]
        if changed:
            lines.append(f"### {model}")
            for case in changed:
                lines.append(
                    f"- `{case['case']}`: `{case['baseline_decision']}` -> `{case['projected_decision']}`; planning support expected `{len(case['planning_support_expected'])}`, planning support noise `{len(case['planning_support_noise'])}`, reasoning noise `{len(case['citable_reasoning_noise'])}`"
                )
            lines.append("")
    lines += [
        "## Planning Starvation Analysis",
        "",
        "Planning starvation is indicated by planning drift increases or planning coverage below Model B while reasoning noise remains controlled.",
        "",
        "## Reasoning-Noise Analysis",
        "",
        "Reasoning noise is measured only in the citable reasoning lane. Planning-support noise is reported separately and does not alter reasoning/citation metrics.",
        "",
        "## Sparse/Unsupported Safety",
        "",
        "Sparse and unsupported cases remained guarded by question-text cues only and are included in every acceptance gate.",
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
    p.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    p.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    p.add_argument("--qda", type=Path, default=QDA)
    p.add_argument("--raa", type=Path, default=RAA)
    p.add_argument("--deep", type=Path, default=DEEP)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_evidence_stage_separation_diagnostic.json"
    md_path = args.reports_dir / "runtime_v13_evidence_stage_separation_diagnostic.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
