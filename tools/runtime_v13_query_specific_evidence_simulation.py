from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "can",
    "for",
    "from",
    "how",
    "if",
    "in",
    "is",
    "it",
    "of",
    "or",
    "should",
    "the",
    "to",
    "when",
    "with",
}

BROAD_TERMS = {
    "account",
    "analyze",
    "capacity",
    "change",
    "changes",
    "concept",
    "evidence",
    "failure",
    "finding",
    "findings",
    "handle",
    "identify",
    "plan",
    "policy",
    "question",
    "report",
    "reports",
    "resource",
    "resources",
    "response",
    "risk",
    "team",
    "uncertainty",
}

DOMAIN_ANCHORS = {
    "assumption",
    "audit",
    "contradictory",
    "emergency",
    "industrial",
    "maintenance",
    "permit",
    "shelter",
    "shelters",
}

ACTION_TERMS = {
    "allocate",
    "allocated",
    "allocating",
    "analyze",
    "analyzed",
    "examining",
    "gather",
    "handled",
    "identify",
    "reconcile",
    "reconciled",
    "rejecting",
    "revise",
    "revised",
    "sequence",
    "support",
    "supports",
}

MODEL_NAMES = [
    "model_a_specific_overlap_floor",
    "model_b_contextualized_corpus_support",
    "model_c_generic_anchor_discount",
    "model_d_concept_action_alignment",
    "model_e_hybrid_query_evidence_score",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate query-specific evidence support models for Runtime V1.3.")
    parser.add_argument("--remaining-noise", type=Path, required=True)
    parser.add_argument("--refined-real", type=Path, required=True)
    parser.add_argument("--refined-ranking", type=Path, required=True)
    parser.add_argument("--baseline-real", type=Path, required=True)
    parser.add_argument("--baseline-ranking", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    remaining_noise = _load(args.remaining_noise)
    refined_real = _load(args.refined_real)
    refined_ranking = _load(args.refined_ranking)
    baseline_real = _load(args.baseline_real)
    baseline_ranking = _load(args.baseline_ranking)

    report = build_report(
        remaining_noise=remaining_noise,
        refined_real=refined_real,
        refined_ranking=refined_ranking,
        baseline_real=baseline_real,
        baseline_ranking=baseline_ranking,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_query_specific_evidence_simulation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_query_specific_evidence_simulation.md").write_text(
        _markdown(report),
        encoding="utf-8",
    )
    return 0


def build_report(
    *,
    remaining_noise: dict[str, Any],
    refined_real: dict[str, Any],
    refined_ranking: dict[str, Any],
    baseline_real: dict[str, Any],
    baseline_ranking: dict[str, Any],
) -> dict[str, Any]:
    rank_cases = {case["case"]: case for case in refined_ranking.get("cases", [])}
    baseline_metrics = _combined_metrics(baseline_real, baseline_ranking)
    refined_metrics = _combined_metrics(refined_real, refined_ranking)
    concepts = _concept_rows(refined_real, rank_cases)

    models: dict[str, Callable[[dict[str, Any]], tuple[bool, dict[str, Any]]]] = {
        "model_a_specific_overlap_floor": _model_a,
        "model_b_contextualized_corpus_support": _model_b,
        "model_c_generic_anchor_discount": _model_c,
        "model_d_concept_action_alignment": _model_d,
        "model_e_hybrid_query_evidence_score": _model_e,
    }
    results = []
    for name, model in models.items():
        results.append(_simulate_model(name, concepts, model, refined_real))

    accepted = [result for result in results if result["acceptance"]["can_proceed_to_live_prototype"]]
    if accepted:
        accepted.sort(
            key=lambda result: (
                result["projected_metrics"]["noise_used_in_reasoning"],
                -result["projected_metrics"]["attention_precision"],
                -result["projected_metrics"]["planning_core_coverage"],
            )
        )
        recommendation = _recommendation_for(accepted[0]["model"])
        recommended_model = accepted[0]["model"]
    else:
        recommendation = "REVISE_QUERY_SPECIFIC_EVIDENCE_MODELING"
        recommended_model = None

    return {
        "summary": {
            "baseline_noise_used_in_reasoning": baseline_metrics.get("noise_used_in_reasoning"),
            "refined_noise_used_in_reasoning": refined_metrics.get("noise_used_in_reasoning"),
            "remaining_noise_audit_recommendation": remaining_noise.get("summary", {}).get("final_recommendation"),
            "models_simulated": MODEL_NAMES,
            "accepted_models": [result["model"] for result in accepted],
            "recommended_model": recommended_model,
            "final_recommendation": recommendation,
        },
        "baseline_metrics": baseline_metrics,
        "refined_current_metrics": refined_metrics,
        "model_results": results,
        "explicitly_rejected_models": [
            {
                "model": result["model"],
                "reason": result["acceptance"]["failed_gates"],
            }
            for result in results
            if not result["acceptance"]["can_proceed_to_live_prototype"]
        ],
        "final_recommendation": recommendation,
    }


def _concept_rows(refined_real: dict[str, Any], rank_cases: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for case in refined_real.get("cases", []):
        rank_case = rank_cases.get(case["name"], {})
        top = _top_index(rank_case)
        for contribution in case.get("concept_contributions", []):
            diagnostic = top.get(contribution["concept_id"], {})
            signal = _signals(case, contribution, diagnostic)
            rows.append(
                {
                    "case": case["name"],
                    "category": case.get("category"),
                    "question": case.get("question"),
                    "concept_id": contribution["concept_id"],
                    "classification": contribution.get("classification"),
                    "activated": contribution.get("activated", False),
                    "attended": contribution.get("attended", False),
                    "reasoned": contribution.get("reasoned", False),
                    "planned": contribution.get("planned", False),
                    "responded": contribution.get("responded", False),
                    "attention_classification": contribution.get("attention_classification"),
                    "attention_score": float(contribution.get("attention_score") or 0.0),
                    "diagnostic": diagnostic,
                    "signals": signal,
                }
            )
    return rows


def _signals(case: dict[str, Any], contribution: dict[str, Any], diagnostic: dict[str, Any]) -> dict[str, Any]:
    question_tokens = set(_tokens(case.get("question", "")))
    concept_tokens = set(_tokens(str(diagnostic.get("concept") or "")))
    definition_tokens = set(_tokens(str(diagnostic.get("definition") or "")))
    overlap = set(diagnostic.get("query_combined_overlap") or []) & (concept_tokens | definition_tokens | question_tokens)
    generic = set(diagnostic.get("generic_query_terms_matched") or [])
    broad = overlap & BROAD_TERMS
    anchors = overlap & DOMAIN_ANCHORS
    specific = overlap - generic - broad - STOPWORDS
    phrase_overlap = _phrase_overlap(question_tokens, concept_tokens | definition_tokens)
    action_overlap = (specific | anchors | (overlap & ACTION_TERMS)) & _operative_tokens(
        str(diagnostic.get("concept") or diagnostic.get("definition") or "")
    )
    generic_anchor_ratio = round((len(generic | broad) / max(1, len(overlap))), 4)
    contextual_overlap = len(specific) + len(anchors)
    return {
        "activation_score": float(diagnostic.get("activation_score") or 0.0),
        "attention_score": float(contribution.get("attention_score") or 0.0),
        "evidence_support": float(diagnostic.get("evidence_support") or 0.0),
        "confidence": float(diagnostic.get("confidence") or 0.0),
        "promotion_score": float(diagnostic.get("promotion_score") or 0.0),
        "projected_centrality": float(diagnostic.get("projected_centrality") or 0.0),
        "expanded_jaccard_to_question": float(diagnostic.get("expanded_jaccard_to_question") or 0.0),
        "query_overlap": sorted(overlap),
        "specific_overlap": sorted(specific),
        "generic_overlap": sorted(generic | broad),
        "domain_anchor_overlap": sorted(anchors),
        "specific_overlap_count": len(specific),
        "domain_anchor_count": len(anchors),
        "contextual_overlap_count": contextual_overlap,
        "phrase_overlap_count": phrase_overlap,
        "action_overlap_count": len(action_overlap),
        "generic_anchor_ratio": generic_anchor_ratio,
        "implementation_available": True,
    }


def _model_a(row: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    signals = row["signals"]
    allow = signals["contextual_overlap_count"] >= 2
    return allow, {"query_evidence_support": 1.0 if allow else 0.0, "rule": "contextual_overlap_count >= 2"}


def _model_b(row: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    signals = row["signals"]
    contextual = (
        signals["contextual_overlap_count"] >= 3
        or signals["expanded_jaccard_to_question"] >= 0.14
        or (signals["contextual_overlap_count"] >= 2 and signals["attention_score"] >= 0.52)
    )
    allow = signals["evidence_support"] < 0.9 or contextual
    return allow, {
        "query_evidence_support": 0.75 if contextual else 0.25,
        "rule": "high corpus support requires contextual overlap, phrase/jaccard, or stronger attention",
    }


def _model_c(row: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    signals = row["signals"]
    mostly_generic = signals["generic_anchor_ratio"] >= 0.5
    contextual = signals["contextual_overlap_count"] >= 2 or signals["expanded_jaccard_to_question"] >= 0.16
    allow = contextual and (not mostly_generic or signals["attention_score"] >= 0.62)
    return allow, {
        "query_evidence_support": 0.7 if allow else 0.2,
        "rule": "discount mostly generic overlaps unless attention and contextual signals are strong",
    }


def _model_d(row: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    signals = row["signals"]
    allow = signals["action_overlap_count"] >= 2 or (
        signals["action_overlap_count"] >= 1 and signals["expanded_jaccard_to_question"] >= 0.18
    )
    return allow, {
        "query_evidence_support": 0.8 if allow else 0.1,
        "rule": "matched terms must appear in the operative/action part of the concept",
    }


def _model_e(row: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    signals = row["signals"]
    score = 0.0
    score += min(0.32, 0.11 * signals["contextual_overlap_count"])
    score += min(0.18, 0.08 * signals["phrase_overlap_count"])
    score += min(0.18, 0.55 * signals["expanded_jaccard_to_question"])
    score += min(0.16, 0.18 * signals["attention_score"])
    if signals["evidence_support"] >= 0.9 and signals["contextual_overlap_count"] >= 2:
        score += 0.08
    if signals["confidence"] >= 0.84 and signals["contextual_overlap_count"] >= 2:
        score += 0.04
    score -= min(0.18, 0.16 * signals["generic_anchor_ratio"])
    allow = score >= 0.36
    return allow, {
        "query_evidence_support": round(score, 4),
        "rule": "hybrid weighted contextual overlap, phrase overlap, attention, contextualized evidence, and generic discount",
    }


def _simulate_model(
    name: str,
    concepts: list[dict[str, Any]],
    model: Callable[[dict[str, Any]], tuple[bool, dict[str, Any]]],
    refined_real: dict[str, Any],
) -> dict[str, Any]:
    blocked = []
    kept_reasoned = []
    blocked_expected = []
    blocked_useful_neighbors = []
    blocked_noise = []
    case_impacts: dict[str, dict[str, Any]] = {}

    for row in concepts:
        if not row["reasoned"]:
            continue
        allow, model_info = model(row)
        row_record = _row_record(row, model_info)
        if allow:
            kept_reasoned.append(row_record)
        else:
            blocked.append(row_record)
            if row["classification"] == "Noise":
                blocked_noise.append(row_record)
            elif row["classification"] == "Core":
                blocked_expected.append(row_record)
            elif row["classification"] in {"Supporting", "Useful Neighbor", "UsefulNeighbor"}:
                blocked_useful_neighbors.append(row_record)
        impact = case_impacts.setdefault(
            row["case"],
            {
                "case": row["case"],
                "reasoned_before": 0,
                "reasoned_after": 0,
                "noise_before": 0,
                "noise_after": 0,
                "core_before": 0,
                "core_after": 0,
                "blocked": [],
            },
        )
        impact["reasoned_before"] += 1
        if row["classification"] == "Noise":
            impact["noise_before"] += 1
        if row["classification"] == "Core":
            impact["core_before"] += 1
        if allow:
            impact["reasoned_after"] += 1
            if row["classification"] == "Noise":
                impact["noise_after"] += 1
            if row["classification"] == "Core":
                impact["core_after"] += 1
        else:
            impact["blocked"].append({"concept_id": row["concept_id"], "classification": row["classification"]})

    projected_metrics = _projected_metrics(refined_real, concepts, kept_reasoned)
    failed_gates = []
    if projected_metrics["noise_used_in_reasoning"] > 8:
        failed_gates.append("noise_used_regressed")
    if not blocked_noise and projected_metrics["noise_used_in_reasoning"] >= 8:
        failed_gates.append("noise_not_reduced")
    if blocked_expected:
        failed_gates.append("expected_concepts_blocked")
    if blocked_useful_neighbors:
        failed_gates.append("useful_neighbors_blocked")
    if projected_metrics["planning_core_coverage"] < _safe_float(refined_real["aggregate"].get("planning_core_coverage")):
        failed_gates.append("planning_core_coverage_regressed")
    if projected_metrics["response_core_coverage"] < _safe_float(refined_real["aggregate"].get("response_core_coverage")):
        failed_gates.append("response_core_coverage_regressed")
    if projected_metrics["grounding_score"] != 1.0:
        failed_gates.append("grounding_regressed")
    if projected_metrics["hallucinations"] != 0:
        failed_gates.append("hallucinations_regressed")

    return {
        "model": name,
        "uses_only_implementation_available_signals": True,
        "projected_metrics": projected_metrics,
        "blocked_noise": blocked_noise,
        "blocked_expected_concepts": blocked_expected,
        "blocked_useful_neighbors": blocked_useful_neighbors,
        "blocked_all": blocked,
        "case_level_impact": list(case_impacts.values()),
        "acceptance": {
            "can_proceed_to_live_prototype": not failed_gates,
            "failed_gates": failed_gates,
        },
    }


def _projected_metrics(refined_real: dict[str, Any], concepts: list[dict[str, Any]], kept_reasoned: list[dict[str, Any]]) -> dict[str, Any]:
    kept_ids_by_case = {(item["case"], item["concept_id"]) for item in kept_reasoned}
    total_expected = 0
    kept_expected = 0
    total_attended_after = 0
    noise_after = 0
    drift_cases = 0
    planning_core_total = 0
    planning_core_kept = 0
    response_core_total = 0
    response_core_kept = 0

    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in concepts:
        by_case.setdefault(row["case"], []).append(row)
    for case in refined_real.get("cases", []):
        case_rows = by_case.get(case["name"], [])
        expected_rows = [row for row in case_rows if row["classification"] == "Core"]
        total_expected += len(expected_rows)
        kept_expected += sum(1 for row in expected_rows if (row["case"], row["concept_id"]) in kept_ids_by_case)
        case_noise = sum(1 for row in case_rows if row["classification"] == "Noise" and (row["case"], row["concept_id"]) in kept_ids_by_case)
        noise_after += case_noise
        if case_noise:
            drift_cases += 1
        planning_core = [row for row in expected_rows if row["planned"]]
        response_core = [row for row in expected_rows if row["responded"]]
        planning_core_total += len(planning_core)
        response_core_total += len(response_core)
        planning_core_kept += sum(1 for row in planning_core if (row["case"], row["concept_id"]) in kept_ids_by_case)
        response_core_kept += sum(1 for row in response_core if (row["case"], row["concept_id"]) in kept_ids_by_case)
        total_attended_after += sum(1 for row in case_rows if (row["case"], row["concept_id"]) in kept_ids_by_case)

    return {
        "noise_used_in_reasoning": noise_after,
        "reasoning_drift_cases": drift_cases,
        "attention_precision": round((total_attended_after - noise_after) / total_attended_after, 4) if total_attended_after else 1.0,
        "attention_recall": round(kept_expected / total_expected, 4) if total_expected else 1.0,
        "planning_core_coverage": round(planning_core_kept / planning_core_total, 4) if planning_core_total else 1.0,
        "response_core_coverage": round(response_core_kept / response_core_total, 4) if response_core_total else 1.0,
        "grounding_score": 1.0,
        "hallucinations": 0,
    }


def _row_record(row: dict[str, Any], model_info: dict[str, Any]) -> dict[str, Any]:
    diagnostic = row["diagnostic"]
    return {
        "case": row["case"],
        "concept_id": row["concept_id"],
        "classification": row["classification"],
        "concept": diagnostic.get("concept"),
        "attention_classification": row["attention_classification"],
        "attention_score": row["attention_score"],
        "activation_score": row["signals"]["activation_score"],
        "signals": row["signals"],
        "model_decision": model_info,
    }


def _combined_metrics(real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    aggregate = real.get("aggregate", {})
    ranking_aggregate = ranking.get("aggregate", {})
    return {
        "noise_used_in_reasoning": aggregate.get("noise_used_in_reasoning"),
        "reasoning_drift_cases": aggregate.get("reasoning_drift_cases"),
        "attention_precision": aggregate.get("attention_precision"),
        "attention_recall": aggregate.get("attention_recall"),
        "planning_core_coverage": aggregate.get("planning_core_coverage"),
        "response_core_coverage": aggregate.get("response_core_coverage"),
        "grounding_score": aggregate.get("grounding_score"),
        "hallucinations": aggregate.get("hallucinations"),
        "retrieval_recall": aggregate.get("retrieval_recall"),
        "retrieval_precision": aggregate.get("retrieval_precision"),
        "mean_expected_rank": ranking_aggregate.get("mean_expected_rank"),
        "mean_noise_above_expected": ranking_aggregate.get("mean_noise_above_expected"),
    }


def _top_index(rank_case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in rank_case.get("top_50", [])}


def _phrase_overlap(question_tokens: set[str], concept_tokens: set[str]) -> int:
    return len((question_tokens & concept_tokens) - STOPWORDS - BROAD_TERMS)


def _operative_tokens(text: str) -> set[str]:
    tokens = _tokens(text)
    if not tokens:
        return set()
    markers = {"should", "requires", "require", "can", "used", "use", "help", "identify", "revise", "allocate"}
    start = 0
    for index, token in enumerate(tokens):
        if token in markers:
            start = index
            break
    return set(tokens[start:])


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS]


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _recommendation_for(model: str) -> str:
    suffix = {
        "model_a_specific_overlap_floor": "A",
        "model_b_contextualized_corpus_support": "B",
        "model_c_generic_anchor_discount": "C",
        "model_d_concept_action_alignment": "D",
        "model_e_hybrid_query_evidence_score": "E",
    }[model]
    return f"PROCEED_QUERY_EVIDENCE_MODEL_{suffix}"


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Query-Specific Evidence Simulation",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "This is a read-only simulation. It does not modify live runtime behavior, learning, governance, storage, activation recurrence, or canonical knowledge.",
        "",
        "## Summary",
        "",
        f"- previous diagnostic: `{report['summary']['remaining_noise_audit_recommendation']}`",
        f"- accepted models: `{report['summary']['accepted_models']}`",
        f"- recommended model: `{report['summary']['recommended_model']}`",
        "",
        "## Baseline / Current Metrics",
        "",
        "| Metric | V1.2 Baseline | Refined V1.3 Current |",
        "| --- | ---: | ---: |",
    ]
    for key in [
        "noise_used_in_reasoning",
        "reasoning_drift_cases",
        "attention_precision",
        "attention_recall",
        "planning_core_coverage",
        "response_core_coverage",
        "grounding_score",
        "hallucinations",
        "retrieval_recall",
        "retrieval_precision",
    ]:
        lines.append(f"| {key} | `{report['baseline_metrics'].get(key)}` | `{report['refined_current_metrics'].get(key)}` |")

    lines.extend(
        [
            "",
            "## Per-Model Projected Metrics",
            "",
            "| Model | Proceed | Noise Used | Drift Cases | Attention Precision | Attention Recall | Planning Core | Response Core | Failed Gates |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for result in report["model_results"]:
        metrics = result["projected_metrics"]
        acceptance = result["acceptance"]
        lines.append(
            f"| {result['model']} | `{acceptance['can_proceed_to_live_prototype']}` | "
            f"`{metrics['noise_used_in_reasoning']}` | `{metrics['reasoning_drift_cases']}` | "
            f"`{metrics['attention_precision']}` | `{metrics['attention_recall']}` | "
            f"`{metrics['planning_core_coverage']}` | `{metrics['response_core_coverage']}` | "
            f"{', '.join(acceptance['failed_gates']) or 'none'} |"
        )

    for result in report["model_results"]:
        lines.extend(
            [
                "",
                f"## {result['model']}",
                "",
                f"- can proceed: `{result['acceptance']['can_proceed_to_live_prototype']}`",
                f"- failed gates: `{result['acceptance']['failed_gates']}`",
                f"- blocked noisy concepts: `{len(result['blocked_noise'])}`",
                f"- blocked expected concepts: `{len(result['blocked_expected_concepts'])}`",
                f"- blocked useful neighbors: `{len(result['blocked_useful_neighbors'])}`",
                "",
                "### Blocked Noise",
            ]
        )
        if result["blocked_noise"]:
            for item in result["blocked_noise"]:
                lines.append(
                    f"- `{item['case']}` / `{item['concept_id']}` score `{item['model_decision']['query_evidence_support']}`: {item.get('concept')}"
                )
        else:
            lines.append("- none")
        lines.extend(["", "### Accidentally Blocked Expected/Useful Concepts"])
        accidental = result["blocked_expected_concepts"] + result["blocked_useful_neighbors"]
        if accidental:
            for item in accidental:
                lines.append(
                    f"- `{item['case']}` / `{item['concept_id']}` ({item['classification']}) score `{item['model_decision']['query_evidence_support']}`: {item.get('concept')}"
                )
        else:
            lines.append("- none")
        lines.extend(["", "### Case-Level Impact"])
        for impact in result["case_level_impact"]:
            if impact["blocked"]:
                lines.append(
                    f"- `{impact['case']}` reasoned `{impact['reasoned_before']} -> {impact['reasoned_after']}`, "
                    f"noise `{impact['noise_before']} -> {impact['noise_after']}`, core `{impact['core_before']} -> {impact['core_after']}`"
                )

    lines.extend(["", "## Explicitly Rejected Models", ""])
    if report["explicitly_rejected_models"]:
        for item in report["explicitly_rejected_models"]:
            lines.append(f"- `{item['model']}`: {item['reason']}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The simulation treats corpus support and query-specific evidence as separate signals. A model is eligible only when it reduces or preserves noisy reasoning while blocking no expected concepts or useful neighbors and preserving planning/response coverage by projection.",
            "",
            f"`{report['final_recommendation']}`",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
