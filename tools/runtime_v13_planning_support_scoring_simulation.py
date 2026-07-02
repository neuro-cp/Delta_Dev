"""Report-only Planning Support scoring simulation for Runtime V1.3.

The accepted runtime remains Model B. This tool simulates Planning Support
selection models against archived reports and evaluates them with labels only
after scoring. It does not patch or import live runtime behavior.
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
AUDIT_JSON = REPORTS / "runtime_v13_variant_c_planning_drift_audit.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
VARIANT_C_REAL = (
    REPORTS
    / "runtime_v13_role_compromise_suite_raw"
    / "variant_c_response_citation_gate"
    / "runtime_v12_real_knowledge.json"
)
VARIANT_C_RANKING = (
    REPORTS
    / "runtime_v13_role_compromise_suite_raw"
    / "variant_c_response_citation_gate"
    / "runtime_v12_activation_ranking_diagnostic.json"
)
V12_REAL = REPORTS / "runtime_v12_baseline_before_v13" / "runtime_v12_real_knowledge.json"
V12_RANKING = REPORTS / "runtime_v12_baseline_before_v13" / "runtime_v12_activation_ranking_diagnostic.json"

GENERIC_TERMS = {
    "approach",
    "change",
    "complex",
    "complexity",
    "context",
    "current",
    "evidence",
    "factor",
    "factors",
    "important",
    "plan",
    "planning",
    "potential",
    "process",
    "resource",
    "risk",
    "scenario",
    "situation",
    "strategy",
    "uncertain",
    "uncertainty",
    "various",
}

BROAD_CONTEXT_TERMS = {
    "complex",
    "complexity",
    "confounding",
    "current understanding",
    "real world",
    "uncertainty",
    "various factors",
}

CONCRETE_TERMS = {
    "action",
    "allocate",
    "allocation",
    "assess",
    "criterion",
    "decision",
    "decrease",
    "determine",
    "failure rate",
    "if",
    "increase",
    "not decrease",
    "predict",
    "prediction",
    "prioritize",
    "reduce",
    "root cause",
    "should",
    "testable",
    "would",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "or",
    "should",
    "that",
    "the",
    "this",
    "to",
    "when",
    "with",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_token(token: str) -> str:
    token = token.lower()
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def tokens(text: str) -> set[str]:
    return {
        normalize_token(token)
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
        if normalize_token(token) not in STOPWORDS
    }


def contains_any(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["name"]: case for case in data.get("cases", [])}


def ranking_case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def as_set(case: dict[str, Any], key: str) -> set[str]:
    return set(case.get(key) or [])


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def rank_items(case: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for rank, item in enumerate(case.get("top_50", []), start=1):
        items.append({**item, "rank": rank})
    return items


def domain_terms(metadata: dict[str, Any], question: str) -> set[str]:
    terms = {normalize_token(term) for term in metadata.get("terms", [])}
    terms.update(tokens(question))
    return {term for term in terms if term not in GENERIC_TERMS and term not in STOPWORDS}


def support_features(item: dict[str, Any], metadata: dict[str, Any], question: str) -> dict[str, Any]:
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    query_terms = {normalize_token(term) for term in item.get("query_combined_overlap", [])}
    specific_overlap = sorted(term for term in query_terms if term not in GENERIC_TERMS and term not in STOPWORDS)
    domain_overlap = sorted(tokens(text) & domain_terms(metadata, question))
    concrete_count = contains_any(text, CONCRETE_TERMS)
    broad_count = contains_any(text, BROAD_CONTEXT_TERMS)
    generic_count = len([term for term in query_terms if term in GENERIC_TERMS])
    score = (
        0.20 * len(specific_overlap)
        + 0.12 * len(domain_overlap)
        + 0.18 * min(concrete_count, 4)
        + 0.16 * float(item.get("promotion_score") or 0.0)
        + 0.10 * float(item.get("confidence") or 0.0)
        + 0.08 * float(item.get("projected_centrality") or 0.0)
        - 0.24 * min(broad_count, 3)
        - 0.12 * generic_count
    )
    return {
        "score": round(score, 4),
        "specific_overlap": specific_overlap,
        "domain_overlap": domain_overlap,
        "concrete_count": concrete_count,
        "broad_context_count": broad_count,
        "generic_overlap_count": generic_count,
        "rank": item.get("rank"),
        "activation_score": item.get("activation_score"),
        "attention_score": item.get("attention_score"),
    }


def candidate_record(
    item: dict[str, Any],
    *,
    selected: bool,
    reason: str,
    metadata: dict[str, Any],
    question: str,
    expected: set[str],
    useful: set[str],
) -> dict[str, Any]:
    features = support_features(item, metadata, question)
    cid = item["concept_id"]
    if cid in expected:
        evaluator_role = "expected"
    elif cid in useful:
        evaluator_role = "useful_neighbor"
    else:
        evaluator_role = "noise"
    return {
        "concept_id": cid,
        "selected": selected,
        "selection_reason": reason,
        "evaluator_role": evaluator_role,
        "score": features["score"],
        "rank": features["rank"],
        "activation_score": features["activation_score"],
        "specific_overlap": features["specific_overlap"],
        "domain_overlap": features["domain_overlap"],
        "concrete_count": features["concrete_count"],
        "broad_context_count": features["broad_context_count"],
        "generic_overlap_count": features["generic_overlap_count"],
        "concept": item.get("concept") or item.get("definition") or "",
    }


def select_support(
    model: str,
    *,
    variant_case: dict[str, Any],
    model_b_case: dict[str, Any],
    ranking_case: dict[str, Any],
    metadata: dict[str, Any],
) -> tuple[set[str], list[dict[str, Any]]]:
    question = ranking_case.get("question") or variant_case.get("question") or model_b_case.get("question") or ""
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    items = rank_items(ranking_case)
    item_by_id = {item["concept_id"]: item for item in items}
    variant_plan = as_set(variant_case, "planning_referenced_concepts")
    variant_response = as_set(variant_case, "response_referenced_concepts")
    variant_existing_support = variant_plan - variant_response
    selected: set[str] = set()
    records: list[dict[str, Any]] = []

    if model == "PS1":
        pool = [item_by_id[cid] for cid in variant_existing_support if cid in item_by_id]
        for item in sorted(pool, key=lambda record: record["rank"]):
            features = support_features(item, metadata, question)
            keep = (
                len(features["specific_overlap"]) >= 2
                and features["broad_context_count"] == 0
                and features["score"] >= 0.82
            )
            if keep:
                selected.add(item["concept_id"])
            records.append(
                candidate_record(
                    item,
                    selected=keep,
                    reason="strict overlap accepted" if keep else "strict overlap rejected",
                    metadata=metadata,
                    question=question,
                    expected=expected,
                    useful=useful,
                )
            )
    elif model == "PS2":
        for item in items[:50]:
            features = support_features(item, metadata, question)
            keep = (
                features["score"] >= 1.02
                and features["concrete_count"] >= 2
                and features["broad_context_count"] <= 1
                and len(features["domain_overlap"]) >= 2
            )
            if keep:
                selected.add(item["concept_id"])
            records.append(
                candidate_record(
                    item,
                    selected=keep,
                    reason="specific lower-rank recall accepted" if keep else "specific lower-rank recall rejected",
                    metadata=metadata,
                    question=question,
                    expected=expected,
                    useful=useful,
                )
            )
    elif model == "PS3":
        pool = [item_by_id[cid] for cid in variant_existing_support if cid in item_by_id]
        for item in sorted(pool, key=lambda record: record["rank"]):
            features = support_features(item, metadata, question)
            keep = (
                features["concrete_count"] >= 1
                and features["broad_context_count"] == 0
                and not _confounding_only(item)
            )
            if keep:
                selected.add(item["concept_id"])
            records.append(
                candidate_record(
                    item,
                    selected=keep,
                    reason="concrete planning criterion accepted" if keep else "broad/confounding support rejected",
                    metadata=metadata,
                    question=question,
                    expected=expected,
                    useful=useful,
                )
            )
    elif model == "PS4":
        selected = as_set(model_b_case, "planning_referenced_concepts") - as_set(variant_case, "response_referenced_concepts")
        for cid in sorted(selected):
            if cid in item_by_id:
                records.append(
                    candidate_record(
                        item_by_id[cid],
                        selected=True,
                        reason="Model B planning behavior retained",
                        metadata=metadata,
                        question=question,
                        expected=expected,
                        useful=useful,
                    )
                )
    elif model == "PS5":
        selected = set()
    else:
        raise ValueError(f"Unknown model {model}")
    return selected, records


def _confounding_only(item: dict[str, Any]) -> bool:
    text = f"{item.get('concept', '')} {item.get('definition', '')}".lower()
    if "confounding" in text or "uncertainty" in text or "complex" in text:
        return contains_any(text, {"root cause", "decision", "prediction", "failure rate", "not decrease"}) == 0
    return False


def projected_case(
    model: str,
    *,
    name: str,
    model_b_case: dict[str, Any],
    variant_case: dict[str, Any],
    ranking_case: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    variant_core = as_set(variant_case, "response_referenced_concepts") | as_set(variant_case, "reasoning_referenced_concepts")
    support, support_records = select_support(
        model,
        variant_case=variant_case,
        model_b_case=model_b_case,
        ranking_case=ranking_case,
        metadata=metadata,
    )

    if model == "PS4":
        reasoning_refs = as_set(model_b_case, "reasoning_referenced_concepts")
        response_refs = as_set(variant_case, "response_referenced_concepts")
        planning_refs = as_set(model_b_case, "planning_referenced_concepts")
        citable_noise = len(response_refs - expected - useful)
    elif model == "PS5":
        reasoning_refs = as_set(model_b_case, "reasoning_referenced_concepts")
        response_refs = as_set(model_b_case, "response_referenced_concepts")
        planning_refs = as_set(model_b_case, "planning_referenced_concepts")
        citable_noise = len(response_refs - expected - useful)
    else:
        reasoning_refs = as_set(variant_case, "reasoning_referenced_concepts")
        response_refs = as_set(variant_case, "response_referenced_concepts")
        planning_refs = variant_core | support
        citable_noise = len(response_refs - expected - useful)

    reasoning_noise = len(reasoning_refs - expected - useful)
    planning_expected = planning_refs & expected
    planning_noise = planning_refs - expected - useful
    planning_core_coverage = round(len(planning_expected) / len(expected), 4) if expected else 1.0
    response_core_coverage = round(len(response_refs & expected) / len(expected), 4) if expected else 1.0

    if reasoning_noise > 0:
        decision = "Reasoning Drift"
    elif expected and 0 < len(planning_expected) < len(expected):
        decision = "Planning Drift"
    elif expected and not planning_expected:
        decision = "Under-Attending"
    else:
        decision = "Healthy"

    return {
        "case": name,
        "question": ranking_case.get("question") or variant_case.get("question"),
        "runtime_decision": decision,
        "planning_refs": sorted(planning_refs),
        "reasoning_refs": sorted(reasoning_refs),
        "response_refs": sorted(response_refs),
        "planning_support_refs": sorted(support),
        "planning_support_candidates": support_records,
        "expected_retained_in_planning": sorted(planning_expected),
        "expected_lost_from_planning": sorted(expected - planning_refs),
        "noise_planning_support_retained": sorted((support | planning_refs) - expected - useful),
        "noise_planning_support_removed": _removed_variant_noise_support(variant_case, support, expected, useful),
        "noise_used_in_reasoning": reasoning_noise,
        "citable_noise_used_in_reasoning": citable_noise,
        "planning_core_coverage": planning_core_coverage,
        "response_core_coverage": response_core_coverage,
        "planning_drift": decision == "Planning Drift",
        "reasoning_drift": decision == "Reasoning Drift",
        "response_drift": False,
    }


def _removed_variant_noise_support(
    variant_case: dict[str, Any],
    selected_support: set[str],
    expected: set[str],
    useful: set[str],
) -> list[str]:
    variant_support = as_set(variant_case, "planning_referenced_concepts") - as_set(variant_case, "response_referenced_concepts")
    variant_noise_support = variant_support - expected - useful
    return sorted(variant_noise_support - selected_support)


def model_projection(
    model: str,
    *,
    model_b: dict[str, Any],
    variant_c: dict[str, Any],
    ranking: dict[str, Any],
) -> dict[str, Any]:
    model_cases = case_map(model_b)
    variant_cases = case_map(variant_c)
    ranking_cases = ranking_case_map(ranking)
    metadata = variant_c.get("case_metadata") or model_b.get("case_metadata") or {}
    cases = []
    for name in sorted(set(model_cases) & set(variant_cases) & set(ranking_cases)):
        cases.append(
            projected_case(
                model,
                name=name,
                model_b_case=model_cases[name],
                variant_case=variant_cases[name],
                ranking_case=ranking_cases[name],
                metadata=metadata.get(name, {}),
            )
        )
    aggregate = {
        "case_count": len(cases),
        "projected_planning_drift_cases": sum(1 for case in cases if case["planning_drift"]),
        "projected_reasoning_drift_cases": sum(1 for case in cases if case["reasoning_drift"]),
        "projected_response_drift_cases": sum(1 for case in cases if case["response_drift"]),
        "projected_noise_used_in_reasoning": sum(case["noise_used_in_reasoning"] for case in cases),
        "projected_citable_noise_used_in_reasoning": sum(case["citable_noise_used_in_reasoning"] for case in cases),
        "projected_planning_support_count": sum(len(case["planning_support_refs"]) for case in cases),
        "projected_planning_core_coverage": _mean([case["planning_core_coverage"] for case in cases]),
        "projected_response_core_coverage": _mean([case["response_core_coverage"] for case in cases]),
        "expected_concepts_retained": sum(len(case["expected_retained_in_planning"]) for case in cases),
        "expected_concepts_lost": sum(len(case["expected_lost_from_planning"]) for case in cases),
        "evaluator_noise_planning_support_retained": sum(len(case["noise_planning_support_retained"]) for case in cases),
        "evaluator_noise_planning_support_removed": sum(len(case["noise_planning_support_removed"]) for case in cases),
        "can_be_implemented_with_live_signals_only": True,
    }
    return {
        "model": model,
        "description": MODEL_DESCRIPTIONS[model],
        "aggregate": aggregate,
        "acceptance": acceptance(aggregate, model_b.get("aggregate", {})),
        "cases": cases,
        "focus_cases": {
            "causal_industrial_failure": next((case for case in cases if case["case"] == "causal_industrial_failure"), None),
            "policy_audit_conflict": next((case for case in cases if case["case"] == "policy_audit_conflict"), None),
        },
    }


def acceptance(aggregate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, bool]:
    return {
        "planning_drift_no_increase": aggregate["projected_planning_drift_cases"] <= baseline.get("planning_drift_cases", 0),
        "reasoning_drift_below_or_equal_model_b": aggregate["projected_reasoning_drift_cases"] <= baseline.get("reasoning_drift_cases", 0),
        "response_drift_no_increase": aggregate["projected_response_drift_cases"] <= baseline.get("response_drift_cases", 0),
        "planning_core_no_regress": aggregate["projected_planning_core_coverage"] >= baseline.get("planning_core_coverage", 0),
        "response_core_no_regress": aggregate["projected_response_core_coverage"] >= baseline.get("response_core_coverage", 0),
        "citable_noise_below_model_b": aggregate["projected_citable_noise_used_in_reasoning"] < baseline.get("noise_used_in_reasoning", 999),
        "activation_attention_retrieval_unchanged": True,
        "uses_live_signals_only": aggregate["can_be_implemented_with_live_signals_only"],
    }


MODEL_DESCRIPTIONS = {
    "PS1": "Strict Planning Support: existing Planning Support requires strong query-specific overlap and no broad-context penalty.",
    "PS2": "Expected Planning Support Recall: lower-ranked concepts may enter planning support when concrete prediction/failure-condition signals and domain specificity are high.",
    "PS3": "Planning Support Exclusion: keep Variant C's lane but reject broad/confounding-only context unless it adds concrete action, prediction, failure condition, or decision criterion.",
    "PS4": "Citation-Safe Model B: keep Model B planning behavior while applying Variant C response citation protection.",
    "PS5": "No Active Planning Support: keep Model B default and treat Planning Support as report-only metadata.",
}


def final_recommendation(projections: dict[str, Any]) -> str:
    candidate_order = [
        ("PS3", "PROCEED_PLANNING_SUPPORT_MODEL_PS3"),
        ("PS2", "PROCEED_PLANNING_SUPPORT_MODEL_PS2"),
        ("PS1", "PROCEED_PLANNING_SUPPORT_MODEL_PS1"),
        ("PS4", "PROCEED_PLANNING_SUPPORT_MODEL_PS4"),
    ]
    for model, recommendation in candidate_order:
        checks = projections[model]["acceptance"]
        if all(checks.values()):
            return recommendation
    ps5 = projections["PS5"]["acceptance"]
    if ps5["planning_drift_no_increase"] and ps5["planning_core_no_regress"]:
        return "KEEP_MODEL_B_DEFAULT_NO_ACTIVE_PLANNING_SUPPORT"
    return "RUN_MORE_DIAGNOSTICS"


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    audit = load_json(args.audit)
    model_b = load_json(args.model_b_real)
    variant_c = load_json(args.variant_c_real)
    ranking = load_json(args.variant_c_ranking)
    v12_real_exists = args.v12_real.exists()
    v12_ranking_exists = args.v12_ranking.exists()
    projections = {
        model: model_projection(model, model_b=model_b, variant_c=variant_c, ranking=ranking)
        for model in ("PS1", "PS2", "PS3", "PS4", "PS5")
    }
    final = final_recommendation(projections)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "simulation_only": True,
        "live_runtime_changed": False,
        "source_reports": {
            "audit": str(args.audit),
            "model_b_real": str(args.model_b_real),
            "model_b_ranking": str(args.model_b_ranking),
            "variant_c_real": str(args.variant_c_real),
            "variant_c_ranking": str(args.variant_c_ranking),
            "v12_real": str(args.v12_real) if v12_real_exists else None,
            "v12_ranking": str(args.v12_ranking) if v12_ranking_exists else None,
        },
        "audit_recommendation": audit.get("final_recommendation"),
        "baseline_aggregate": model_b.get("aggregate", {}),
        "variant_c_aggregate": variant_c.get("aggregate", {}),
        "models": projections,
        "final_recommendation": final,
        "interpretation": interpretation(projections, final),
    }


def interpretation(projections: dict[str, Any], final: str) -> str:
    ps2 = projections["PS2"]["focus_cases"]["causal_industrial_failure"]
    ps3 = projections["PS3"]["focus_cases"]["causal_industrial_failure"]
    if final == "PROCEED_PLANNING_SUPPORT_MODEL_PS2":
        return (
            "The only simulated model that both recovers the missing causal maintenance prediction and removes "
            "the Variant C planning-support noise is PS2. This suggests the next safe work is still simulation/prototype-gated: "
            "Planning Support needs a narrow lower-ranked recall path for concrete prediction/failure-condition concepts, not broader role gating."
        )
    if final == "PROCEED_PLANNING_SUPPORT_MODEL_PS3":
        return (
            "PS3 removes broad/confounding planning-support noise while preserving acceptance gates. "
            "It is the narrowest live-candidate shape because it does not reach below the attended/Variant C planning-support lane."
        )
    if final == "KEEP_MODEL_B_DEFAULT_NO_ACTIVE_PLANNING_SUPPORT":
        return (
            "No active Planning Support scorer cleanly passed the projected gates. Model B should remain default and Planning Support should stay metadata-only."
        )
    return (
        "No model produced a clean enough projection. PS2 causal result: "
        f"{ps2['runtime_decision'] if ps2 else 'missing'}; PS3 causal result: {ps3['runtime_decision'] if ps3 else 'missing'}."
    )


def markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Runtime V1.3 Planning Support Scoring Simulation")
    lines.append("")
    lines.append(f"Generated: `{report['generated_at']}`")
    lines.append("")
    lines.append("Report-only simulation. Model B remains default. No live runtime, learning, governance, storage, provider, activation, attention, candidate-store, or canonical behavior was modified.")
    lines.append("")
    lines.append("## Baseline")
    lines.append("")
    lines.append("| Metric | Model B | Variant C |")
    lines.append("| --- | ---: | ---: |")
    for metric in (
        "planning_score",
        "planning_drift_cases",
        "reasoning_drift_cases",
        "noise_used_in_reasoning",
        "citable_noise_used_in_reasoning",
        "planning_support_count",
        "planning_core_coverage",
        "response_core_coverage",
    ):
        lines.append(f"| {metric} | `{report['baseline_aggregate'].get(metric)}` | `{report['variant_c_aggregate'].get(metric)}` |")
    lines.append("")
    lines.append("## Model Results")
    lines.append("")
    lines.append("| Model | Planning Drift | Reasoning Drift | Citable Noise | Support Count | Expected Lost | Noise Support Retained | Acceptance |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for model in ("PS1", "PS2", "PS3", "PS4", "PS5"):
        projection = report["models"][model]
        aggregate = projection["aggregate"]
        passed = all(projection["acceptance"].values())
        lines.append(
            f"| {model} | `{aggregate['projected_planning_drift_cases']}` | `{aggregate['projected_reasoning_drift_cases']}` | "
            f"`{aggregate['projected_citable_noise_used_in_reasoning']}` | `{aggregate['projected_planning_support_count']}` | "
            f"`{aggregate['expected_concepts_lost']}` | `{aggregate['evaluator_noise_planning_support_retained']}` | `{passed}` |"
        )
    lines.append("")
    lines.append("## Focus Case: causal_industrial_failure")
    lines.append("")
    lines.append("| Model | Decision | Expected Retained | Expected Lost | Noise Support Retained | Noise Support Removed |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for model in ("PS1", "PS2", "PS3", "PS4", "PS5"):
        case = report["models"][model]["focus_cases"]["causal_industrial_failure"]
        lines.append(
            f"| {model} | `{case['runtime_decision']}` | `{', '.join(case['expected_retained_in_planning']) or 'none'}` | "
            f"`{', '.join(case['expected_lost_from_planning']) or 'none'}` | "
            f"`{', '.join(case['noise_planning_support_retained']) or 'none'}` | "
            f"`{', '.join(case['noise_planning_support_removed']) or 'none'}` |"
        )
    lines.append("")
    lines.append("## Focus Case: policy_audit_conflict")
    lines.append("")
    lines.append("| Model | Decision | Expected Retained | Expected Lost | Noise Support Retained |")
    lines.append("| --- | --- | --- | --- | --- |")
    for model in ("PS1", "PS2", "PS3", "PS4", "PS5"):
        case = report["models"][model]["focus_cases"]["policy_audit_conflict"]
        lines.append(
            f"| {model} | `{case['runtime_decision']}` | `{', '.join(case['expected_retained_in_planning']) or 'none'}` | "
            f"`{', '.join(case['expected_lost_from_planning']) or 'none'}` | "
            f"`{', '.join(case['noise_planning_support_retained']) or 'none'}` |"
        )
    lines.append("")
    lines.append("## PS2 Selected Candidates For causal_industrial_failure")
    lines.append("")
    ps2_case = report["models"]["PS2"]["focus_cases"]["causal_industrial_failure"]
    lines.append("| Selected | Eval Role | Score | Rank | Specific | Domain | Concrete | Broad | Text |")
    lines.append("| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | --- |")
    for candidate in ps2_case["planning_support_candidates"]:
        if not candidate["selected"] and candidate["evaluator_role"] != "expected":
            continue
        text = candidate["concept"].replace("|", "\\|")
        if len(text) > 130:
            text = text[:127] + "..."
        lines.append(
            f"| `{candidate['selected']}` | `{candidate['evaluator_role']}` | `{candidate['score']}` | `{candidate['rank']}` | "
            f"`{', '.join(candidate['specific_overlap'])}` | `{', '.join(candidate['domain_overlap'])}` | "
            f"`{candidate['concrete_count']}` | `{candidate['broad_context_count']}` | {text} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(report["interpretation"])
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This is not a runtime patch. Evaluation labels were used only to score simulated outputs after candidate selection, not as simulated live signals.")
    lines.append("")
    lines.append(report["final_recommendation"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=AUDIT_JSON)
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    parser.add_argument("--variant-c-real", type=Path, default=VARIANT_C_REAL)
    parser.add_argument("--variant-c-ranking", type=Path, default=VARIANT_C_RANKING)
    parser.add_argument("--v12-real", type=Path, default=V12_REAL)
    parser.add_argument("--v12-ranking", type=Path, default=V12_RANKING)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_planning_support_scoring_simulation.json"
    md_path = args.reports_dir / "runtime_v13_planning_support_scoring_simulation.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
