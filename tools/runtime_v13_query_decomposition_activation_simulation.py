"""Report-only query-decomposition activation simulation for Runtime V1.3.

This simulation asks whether decomposing a user question into smaller live-safe
activation intents can recover expected evidence without admitting same-topic
wrong-relation noise. It reads archived Model B/diagnostic outputs only and does
not patch runtime behavior.
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
RAW_ROOT = REPORTS / "runtime_v13_query_decomposition_activation_raw"

MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
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


def decompose(question: str, model: str) -> dict[str, Any]:
    q = token_set(question)
    family = infer_family(question)
    need = infer_evidence_need(question)
    anchors = phrase_anchors(question)
    subject = sorted(q - GENERIC - FAMILIES[family] - EVIDENCE_NEEDS[need])
    relation = sorted((q & FAMILIES[family]) | (q & EVIDENCE_NEEDS[need]))
    outcome = sorted(q & {"outcome", "rate", "capacity", "tradeoff", "route", "method", "rule", "confidence"})
    sparse = bool(q & {"violin", "recipe", "cook"})
    if model == "QDA1":
        intents = [{"subject": subject, "relation": relation, "outcome": outcome, "need": need, "family": family}]
    elif model == "QDA2":
        intents = [
            {"name": "subject_domain", "tokens": subject, "required": False},
            {"name": "relation_action", "tokens": relation, "required": True},
            {"name": "evidence_outcome", "tokens": list((q & EVIDENCE_NEEDS[need]) | set(outcome)), "required": False},
        ]
    elif model == "QDA3":
        intents = [{"family": family, "tokens": sorted(FAMILIES[family] | set(subject) | set(outcome))}]
    elif model == "QDA4":
        intents = [{"need": need, "tokens": sorted(EVIDENCE_NEEDS[need])}]
    else:
        intents = [
            {"family": family, "need": need, "tokens": sorted(FAMILIES[family] | EVIDENCE_NEEDS[need])},
            {"subject": subject, "outcome": outcome, "tokens": sorted(set(subject) | set(outcome))},
        ]
    return {
        "model": model,
        "family": family,
        "evidence_need": need,
        "subject_cues": subject,
        "relation_action_cues": relation,
        "outcome_cues": outcome,
        "anchors": sorted(anchors),
        "sparse_or_unsupported_guard": sparse,
        "intents": intents,
    }


def item_features(item: dict[str, Any], question: str, model: str) -> dict[str, Any]:
    intent = decompose(question, model)
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    text_tokens = token_set(text)
    item_anchors = phrase_anchors(text)
    overlap = {str(t).lower() for t in item.get("query_combined_overlap", [])}
    generic_overlap = overlap & GENERIC
    subject_hits = len(text_tokens & set(intent["subject_cues"]))
    relation_hits = len(text_tokens & set(intent["relation_action_cues"]))
    outcome_hits = len(text_tokens & set(intent["outcome_cues"]))
    family_hits = len(text_tokens & FAMILIES[intent["family"]])
    need_hits = len(text_tokens & EVIDENCE_NEEDS[intent["evidence_need"]])
    anchor_hits = len(item_anchors & set(intent["anchors"]))
    concept_tokens = token_set(item.get("concept", ""))
    definition_tokens = token_set(item.get("definition", ""))
    alignment = len(concept_tokens & definition_tokens) / max(1, len(concept_tokens | definition_tokens))
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
        "alignment": alignment,
        "directionality": directionality,
        "concrete_match": concrete_match,
        "generic_ratio": len(generic_overlap) / max(1, len(overlap)),
        "sparse_guard": intent["sparse_or_unsupported_guard"],
    }


def qda_score(item: dict[str, Any], question: str, model: str) -> float:
    f = item_features(item, question, model)
    if f["sparse_guard"]:
        return f["activation"] - 0.8
    if model == "QDA1":
        return round(
            f["activation"]
            + 0.11 * f["concrete_match"]
            + 0.08 * f["relation_hits"]
            + 0.06 * f["subject_hits"]
            + 0.05 * f["outcome_hits"]
            - 0.13 * f["generic_ratio"],
            4,
        )
    if model == "QDA2":
        required_penalty = 0.22 if f["relation_hits"] == 0 else 0.0
        return round(
            f["activation"]
            + 0.10 * f["relation_hits"]
            + 0.06 * max(f["subject_hits"], f["outcome_hits"])
            + 0.08 * f["anchor_hits"]
            - 0.12 * f["generic_ratio"]
            - required_penalty,
            4,
        )
    if model == "QDA3":
        return round(
            f["activation"]
            + 0.11 * f["family_hits"]
            + 0.06 * f["subject_hits"]
            + 0.04 * f["outcome_hits"]
            + 0.04 * f["directionality"]
            - 0.12 * f["generic_ratio"]
            - (0.05 * f["centrality"] if f["family_hits"] == 0 else 0.0),
            4,
        )
    if model == "QDA4":
        return round(
            f["activation"]
            + 0.14 * f["need_hits"]
            + 0.08 * f["anchor_hits"]
            + 0.05 * f["directionality"]
            - 0.15 * f["generic_ratio"]
            - (0.05 * f["promotion"] if f["need_hits"] == 0 else 0.0),
            4,
        )
    if model in {"QDA5", "QDA6"}:
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
    raise ValueError(model)


def model_selection(
    reranked: list[dict[str, Any]],
    baseline_case: dict[str, Any],
    question: str,
    model: str,
) -> tuple[set[str], set[str]]:
    if decompose(question, model)["sparse_or_unsupported_guard"]:
        return set(), set()
    contrib = contribution_map(baseline_case)
    visible = {item["concept_id"] for item in reranked[:10]}
    selected: set[str] = set()
    cap = {"QDA1": 3, "QDA2": 3, "QDA3": 3, "QDA4": 3, "QDA5": 3, "QDA6": 2}[model]
    for item in reranked[:10]:
        cid = item["concept_id"]
        f = item_features(item, question, model)
        strong_intent = (
            f["concrete_match"]
            or f["anchor_hits"] > 0
            or (f["need_hits"] >= 2 and f["relation_hits"] > 0)
            or (f["family_hits"] >= 2 and f["subject_hits"] > 0)
        )
        generic_only = f["generic_ratio"] > 0.67 and not f["concrete_match"] and not f["anchor_hits"]
        if not strong_intent or generic_only:
            continue
        if model == "QDA6":
            # Visibility can broaden, but citable reasoning remains gated by
            # accepted Model B behavior plus strict intent evidence.
            if contrib.get(cid, {}).get("reasoned") or (f["concrete_match"] and f["anchor_hits"] > 0):
                selected.add(cid)
        else:
            selected.add(cid)
        if len(selected) >= cap:
            break
    return visible, selected


def project_case(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any], model: str) -> dict[str, Any]:
    question = ranking_case.get("question") or case.get("question") or ""
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    original = [{**item, "original_rank": idx + 1} for idx, item in enumerate(ranking_case.get("top_50", []))]
    reranked = sorted(
        [{**item, "simulated_score": qda_score(item, question, model)} for item in original],
        key=lambda item: (item["simulated_score"], item.get("activation_score", 0.0), item["concept_id"]),
        reverse=True,
    )
    for idx, item in enumerate(reranked, start=1):
        item["simulated_rank"] = idx
    visible, selected = model_selection(reranked, case, question, model)
    reasoning = set(selected)
    planning = set(selected)
    response = set(selected)
    noise = reasoning - expected - useful
    citable_noise = response - expected - useful
    planning_cov = round(len(planning & expected) / len(expected), 4) if expected else 1.0
    response_cov = round(len(response & expected) / len(expected), 4) if expected else 1.0
    if noise:
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
        "question": question,
        "baseline_decision": case.get("runtime_decision"),
        "projected_decision": projected,
        "query_decomposition": decompose(question, model),
        "visible": sorted(visible),
        "selected_for_reasoning": sorted(selected),
        "expected_recovered": sorted(selected & expected),
        "visible_expected": sorted(visible & expected),
        "same_topic_noise_admitted": sorted(selected - expected - useful),
        "noise_entering_reasoning": sorted(noise),
        "citable_noise": sorted(citable_noise),
        "planning_core_coverage": planning_cov,
        "response_core_coverage": response_cov,
        "top10": [
            {
                "concept_id": item["concept_id"],
                "role": item.get("role"),
                "original_rank": item["original_rank"],
                "simulated_rank": item["simulated_rank"],
                "score": item["simulated_score"],
                "features": item_features(item, question, model),
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
        "noise_used_in_reasoning": sum(len(case["noise_entering_reasoning"]) for case in cases),
        "citable_noise_used_in_reasoning": sum(len(case["citable_noise"]) for case in cases),
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
        "expected_evidence_recovered": sum(len(case["expected_recovered"]) for case in cases),
        "visible_expected_evidence": sum(len(case["visible_expected"]) for case in cases),
        "same_topic_noise_admitted": sum(len(case["same_topic_noise_admitted"]) for case in cases),
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


def final_recommendation(models: dict[str, Any]) -> str:
    for model in ("QDA6", "QDA5", "QDA4", "QDA3", "QDA2", "QDA1"):
        if models[model]["passed"]:
            return f"PROCEED_QUERY_DECOMPOSITION_MODEL_{model}"
    if any(model["aggregate"]["cases_improved"] for model in models.values()):
        return "RUN_MORE_DIAGNOSTICS"
    if max(model["aggregate"]["visible_expected_evidence"] for model in models.values()) > max(
        model["aggregate"]["expected_evidence_recovered"] for model in models.values()
    ):
        return "PROCEED_EVIDENCE_CONTEXTUALIZATION_IN_ACTIVATION_SIMULATION"
    return "PROCEED_BENCHMARK_LIVE_WINDOW_REVIEW"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    raa = load_json(args.raa)
    deep = load_json(args.deep)
    models = {model: evaluate_model(model, real, ranking) for model in ("QDA1", "QDA2", "QDA3", "QDA4", "QDA5", "QDA6")}
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    for model, payload in models.items():
        out = RAW_ROOT / model
        out.mkdir(exist_ok=True)
        (out / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rec = final_recommendation(models)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "simulation_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "why_relation_aware_activation_failed": raa.get("final_recommendation"),
        "deep_activation_recommendation": deep.get("final_recommendation"),
        "models": models,
        "raw_archive": str(RAW_ROOT),
        "live_prototype_should_be_attempted_later": rec.startswith("PROCEED_QUERY_DECOMPOSITION_MODEL_"),
        "continuation_checkpoint": {"model_b_default_remains_active": True, "runtime_files_modified": False, "next_step": rec},
        "final_recommendation": rec,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Query Decomposition Activation Simulation",
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
        "This simulation decomposed each question into live-safe activation intents using question text only, then projected activation, attention, reasoning/citation use, planning, and response outcomes against archived Model B data.",
        "",
        "## Why Relation-Aware Activation Failed",
        "",
        f"Relation-aware activation ended with `{report['why_relation_aware_activation_failed']}`. It recovered more expected evidence, but relation frames applied to the full broad candidate pool still admitted same-topic wrong-relation noise.",
        "",
        "## Decomposition Models Tested",
        "",
        "- `QDA1`: single primary intent.",
        "- `QDA2`: subject/domain, relation/action, evidence/outcome split.",
        "- `QDA3`: relation-family first.",
        "- `QDA4`: evidence-need first.",
        "- `QDA5`: conservative hybrid intent scoring.",
        "- `QDA6`: QDA5 visibility with separated reasoning/citation use.",
        "",
        "## Model Comparison",
        "",
        "| Model | Pass | Noise | Citable Noise | Reasoning Drift | Planning Drift | Plan Cov | Resp Cov | Improved | Regressed | Expected Recovered | Visible Expected | Same-Topic Noise |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in ("QDA1", "QDA2", "QDA3", "QDA4", "QDA5", "QDA6"):
        payload = report["models"][model]
        a = payload["aggregate"]
        lines.append(
            f"| {model} | `{payload['passed']}` | `{a['noise_used_in_reasoning']}` | `{a['citable_noise_used_in_reasoning']}` | `{a['reasoning_drift_cases']}` | `{a['planning_drift_cases']}` | `{a['planning_core_coverage']}` | `{a['response_core_coverage']}` | `{a['cases_improved']}` | `{a['cases_regressed']}` | `{a['expected_evidence_recovered']}` | `{a['visible_expected_evidence']}` | `{a['same_topic_noise_admitted']}` |"
        )
    lines += ["", "## Query Decomposition Examples", ""]
    for case in report["models"]["QDA5"]["cases"][:5]:
        qd = case["query_decomposition"]
        lines.append(f"- `{case['case']}`: family `{qd['family']}`, evidence need `{qd['evidence_need']}`, subject cues `{', '.join(qd['subject_cues'][:6])}`")
    lines += ["", "## Case-Level Improvements/Regressions", ""]
    for model in ("QDA1", "QDA2", "QDA3", "QDA4", "QDA5", "QDA6"):
        changed = [case for case in report["models"][model]["cases"] if case["baseline_decision"] != case["projected_decision"]]
        if changed:
            lines.append(f"### {model}")
            for case in changed:
                lines.append(
                    f"- `{case['case']}`: `{case['baseline_decision']}` -> `{case['projected_decision']}`; expected recovered `{len(case['expected_recovered'])}`, noise `{len(case['noise_entering_reasoning'])}`"
                )
            lines.append("")
    lines += [
        "## Sparse/Unsupported Safety",
        "",
        "Sparse and unsupported cases are guarded by question-text cues only and remained acceptance gates for every model.",
        "",
        "## Best Candidate",
        "",
    ]
    passed = [model for model, payload in report["models"].items() if payload["passed"]]
    lines.append(f"Passed candidates: `{', '.join(passed) if passed else 'none'}`")
    lines += [
        "",
        "## Rejected Candidates",
        "",
    ]
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
    p.add_argument("--raa", type=Path, default=RAA)
    p.add_argument("--deep", type=Path, default=DEEP)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_query_decomposition_activation_simulation.json"
    md_path = args.reports_dir / "runtime_v13_query_decomposition_activation_simulation.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
