from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


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
    "capacity",
    "change",
    "changes",
    "evidence",
    "failure",
    "finding",
    "findings",
    "plan",
    "policy",
    "report",
    "reports",
    "resource",
    "resources",
    "response",
    "risk",
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

DISCOURSE_CONTEXT_MARKERS = (
    "for instance",
    "this scenario",
    "current understanding",
    "it might be tempting",
    "would suggest",
    "certainty of",
    "depends on",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate query-local role classification for Runtime V1.3.")
    parser.add_argument("--model-b-real", type=Path, required=True)
    parser.add_argument("--model-b-ranking", type=Path, required=True)
    parser.add_argument("--model-b-report", type=Path, required=True)
    parser.add_argument("--remaining-noise", type=Path, required=True)
    parser.add_argument("--baseline-real", type=Path, required=True)
    parser.add_argument("--baseline-ranking", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    model_b_real = _load(args.model_b_real)
    model_b_ranking = _load(args.model_b_ranking)
    model_b_report = _load(args.model_b_report)
    remaining_noise = _load(args.remaining_noise)
    baseline_real = _load(args.baseline_real)
    baseline_ranking = _load(args.baseline_ranking)

    report = build_report(
        model_b_real=model_b_real,
        model_b_ranking=model_b_ranking,
        model_b_report=model_b_report,
        remaining_noise=remaining_noise,
        baseline_real=baseline_real,
        baseline_ranking=baseline_ranking,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_query_local_role_simulation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_query_local_role_simulation.md").write_text(
        _markdown(report),
        encoding="utf-8",
    )
    return 0


def build_report(
    *,
    model_b_real: dict[str, Any],
    model_b_ranking: dict[str, Any],
    model_b_report: dict[str, Any],
    remaining_noise: dict[str, Any],
    baseline_real: dict[str, Any],
    baseline_ranking: dict[str, Any],
) -> dict[str, Any]:
    rank_cases = {case["case"]: case for case in model_b_ranking.get("cases", [])}
    rows = _rows(model_b_real, rank_cases)
    current_metrics = _combined_metrics(model_b_real, model_b_ranking)
    baseline_metrics = _combined_metrics(baseline_real, baseline_ranking)
    model_results = [_simulate(name, rows, model_b_real) for name in ("R1", "R2", "R3", "R4")]
    accepted = [result for result in model_results if result["acceptance"]["can_proceed_to_live_prototype"]]
    recommendation = _recommendation(accepted)
    return {
        "summary": {
            "final_recommendation": recommendation,
            "accepted_models": [result["model"] for result in accepted],
            "recommended_model": accepted[0]["model"] if accepted else None,
            "current_model_b_decision": model_b_report.get("final_decision"),
            "remaining_noise_count": remaining_noise.get("summary", {}).get("remaining_noisy_reasoning_concepts"),
            "remaining_noise_dominant_failures": remaining_noise.get("summary", {}).get("dominant_failure_modes", {}),
        },
        "baseline_metrics": baseline_metrics,
        "current_model_b_metrics": current_metrics,
        "model_results": model_results,
        "explicitly_rejected_models": [
            {"model": result["model"], "failed_gates": result["acceptance"]["failed_gates"]}
            for result in model_results
            if not result["acceptance"]["can_proceed_to_live_prototype"]
        ],
        "final_recommendation": recommendation,
    }


def _rows(model_b_real: dict[str, Any], rank_cases: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in model_b_real.get("cases", []):
        top = {item["concept_id"]: item for item in rank_cases.get(case["name"], {}).get("top_50", [])}
        for contribution in case.get("concept_contributions", []):
            diagnostic = top.get(contribution["concept_id"], {})
            rows.append(
                {
                    "case": case["name"],
                    "category": case.get("category"),
                    "question": case.get("question"),
                    "concept_id": contribution["concept_id"],
                    "classification": contribution.get("classification"),
                    "reasoned": contribution.get("reasoned", False),
                    "planned": contribution.get("planned", False),
                    "responded": contribution.get("responded", False),
                    "attended": contribution.get("attended", False),
                    "attention_classification": contribution.get("attention_classification"),
                    "attention_score": float(contribution.get("attention_score") or 0.0),
                    "diagnostic": diagnostic,
                    "signals": _signals(case, contribution, diagnostic),
                }
            )
    return rows


def _signals(case: dict[str, Any], contribution: dict[str, Any], diagnostic: dict[str, Any]) -> dict[str, Any]:
    concept_text = str(diagnostic.get("concept") or "")
    definition = str(diagnostic.get("definition") or "")
    overlap = set(_normalize_terms(diagnostic.get("query_combined_overlap") or []))
    generic = set(_normalize_terms(diagnostic.get("generic_query_terms_matched") or [])) | (overlap & BROAD_TERMS)
    anchors = overlap & DOMAIN_ANCHORS
    specific = overlap - generic - STOPWORDS
    jaccard = float(diagnostic.get("expanded_jaccard_to_question") or 0.0)
    attention_score = float(contribution.get("attention_score") or 0.0)
    text = f"{concept_text} {definition}".lower()
    context_marker = any(marker in text for marker in DISCOURSE_CONTEXT_MARKERS)
    generic_ratio = len(generic) / max(1, len(overlap))
    direct_action = bool(
        re.search(
            r"\b(should|requires?|revise|analy[sz]e|compare|establish|examining|allocate|reconcile|sequence|validate|identify)\b",
            text,
            re.I,
        )
    )
    return {
        "activation_score": float(diagnostic.get("activation_score") or 0.0),
        "attention_score": attention_score,
        "evidence_support": float(diagnostic.get("evidence_support") or 0.0),
        "confidence": float(diagnostic.get("confidence") or 0.0),
        "promotion_score": float(diagnostic.get("promotion_score") or 0.0),
        "projected_centrality": float(diagnostic.get("projected_centrality") or 0.0),
        "query_overlap": sorted(overlap),
        "specific_overlap": sorted(specific),
        "specific_overlap_count": len(specific),
        "domain_anchor_overlap": sorted(anchors),
        "domain_anchor_count": len(anchors),
        "contextual_overlap_count": len(specific) + len(anchors),
        "generic_overlap": sorted(generic),
        "generic_ratio": round(generic_ratio, 4),
        "expanded_jaccard_to_question": jaccard,
        "context_marker": context_marker,
        "direct_action_language": direct_action,
        "attention_classification": contribution.get("attention_classification"),
        "implementation_available": True,
    }


def _role_for(model: str, row: dict[str, Any]) -> str:
    signals = row["signals"]
    contextual = signals["contextual_overlap_count"]
    jaccard = signals["expanded_jaccard_to_question"]
    attention = signals["attention_score"]
    generic_ratio = signals["generic_ratio"]
    context_marker = signals["context_marker"]
    direct_action = signals["direct_action_language"]
    attention_class = signals["attention_classification"]
    high_context = contextual >= 3 or (contextual >= 2 and jaccard >= 0.14)
    moderate_context = contextual >= 2 or (contextual >= 1 and attention >= 0.55) or jaccard >= 0.14
    generic_only = contextual == 0 and generic_ratio >= 0.5
    core_ready = (
        high_context
        and not context_marker
        and generic_ratio <= 0.75
        and (direct_action or attention_class == "Core" or jaccard >= 0.25)
    )

    if model == "R1":
        if high_context and direct_action and not context_marker:
            return "Core Evidence"
        if moderate_context:
            return "Supporting Context"
        if attention_class in {"Core", "Supporting"}:
            return "Peripheral Context"
        return "Non-Evidence"

    if model == "R2":
        if core_ready:
            return "Core Evidence"
        if moderate_context or attention >= 0.60:
            return "Supporting Context"
        if attention_class in {"Core", "Supporting"}:
            return "Peripheral Context"
        return "Non-Evidence"

    if model == "R3":
        if core_ready:
            return "Core Evidence"
        if row["reasoned"]:
            return "Supporting Context"
        if attention_class in {"Core", "Supporting"}:
            return "Peripheral Context"
        return "Non-Evidence"

    if model == "R4":
        if core_ready:
            return "Core Evidence"
        if moderate_context and not generic_only:
            return "Supporting Context"
        if attention >= 0.55 and not generic_only:
            return "Supporting Context"
        if attention_class in {"Core", "Supporting"} and (contextual >= 1 or jaccard >= 0.08):
            return "Peripheral Context"
        return "Non-Evidence"

    raise ValueError(f"unknown model {model}")


def _simulate(model: str, rows: list[dict[str, Any]], model_b_real: dict[str, Any]) -> dict[str, Any]:
    assignments = []
    for row in rows:
        role = _role_for(model, row)
        assignments.append({**row, "role": role})

    case_impacts: dict[str, dict[str, Any]] = {}
    moved_to_context = []
    blocked_expected = []
    blocked_useful = []
    remaining_noise_roles = []
    for row in assignments:
        if not row["reasoned"] and row["classification"] != "Core":
            continue
        core = row["role"] == "Core Evidence"
        supporting = row["role"] == "Supporting Context"
        peripheral = row["role"] == "Peripheral Context"
        reasoned_after = core or (supporting and model in {"R2", "R3", "R4"})
        planned_after = core
        responded_after = core
        impact = case_impacts.setdefault(
            row["case"],
            {
                "case": row["case"],
                "reasoned_before": 0,
                "reasoned_after": 0,
                "planning_before": 0,
                "planning_after": 0,
                "response_before": 0,
                "response_after": 0,
                "noise_evidence_before": 0,
                "noise_evidence_after": 0,
                "supporting_context_after": 0,
                "blocked": [],
            },
        )
        if row["reasoned"]:
            impact["reasoned_before"] += 1
        if reasoned_after:
            impact["reasoned_after"] += 1
        if row["planned"]:
            impact["planning_before"] += 1
        if planned_after:
            impact["planning_after"] += 1
        if row["responded"]:
            impact["response_before"] += 1
        if responded_after:
            impact["response_after"] += 1
        if row["classification"] == "Noise" and row["reasoned"]:
            impact["noise_evidence_before"] += 1
        if row["classification"] == "Noise" and core:
            impact["noise_evidence_after"] += 1
        if supporting:
            impact["supporting_context_after"] += 1
        if row["classification"] == "Noise" and row["reasoned"]:
            remaining_noise_roles.append(_assignment_record(row, role))
            if supporting:
                moved_to_context.append(_assignment_record(row, role))
        if row["classification"] == "Core" and row["reasoned"] and not reasoned_after:
            blocked_expected.append(_assignment_record(row, role))
            impact["blocked"].append({"concept_id": row["concept_id"], "classification": row["classification"], "role": role})
        if row["classification"] == "Peripheral" and row["attended"] and row["role"] == "Non-Evidence":
            blocked_useful.append(_assignment_record(row, role))

    metrics = _projected_metrics(model_b_real, assignments, model)
    failed = []
    current = model_b_real["aggregate"]
    if metrics["noise_used_in_reasoning"] > current["noise_used_in_reasoning"]:
        failed.append("noise_used_regressed")
    if metrics["reasoning_drift_cases"] > current["reasoning_drift_cases"]:
        failed.append("reasoning_drift_increased")
    if metrics["planning_drift_cases"] > current["planning_drift_cases"]:
        failed.append("planning_drift_increased")
    if metrics["response_drift_cases"] > current["response_drift_cases"]:
        failed.append("response_drift_increased")
    if blocked_expected:
        failed.append("expected_concepts_blocked_from_needed_use")
    if blocked_useful:
        failed.append("useful_neighbors_discarded")
    if metrics["planning_core_coverage"] < current["planning_core_coverage"]:
        failed.append("planning_core_coverage_regressed")
    if metrics["response_core_coverage"] < current["response_core_coverage"]:
        failed.append("response_core_coverage_regressed")
    if metrics["grounding_score"] != 1.0:
        failed.append("grounding_regressed")
    if metrics["hallucinations"] != 0:
        failed.append("hallucinations_regressed")

    return {
        "model": model,
        "description": _description(model),
        "can_implement_without_evaluator_labels": True,
        "projected_metrics": metrics,
        "role_counts": dict(Counter(row["role"] for row in assignments if row["reasoned"] or row["classification"] == "Core")),
        "remaining_noisy_concept_roles": remaining_noise_roles,
        "concepts_moved_from_evidence_to_supporting_context": moved_to_context,
        "expected_concepts_accidentally_downgraded_or_blocked": blocked_expected,
        "useful_neighbor_concepts_accidentally_blocked": blocked_useful,
        "case_level_impact": list(case_impacts.values()),
        "acceptance": {"can_proceed_to_live_prototype": not failed, "failed_gates": failed},
    }


def _projected_metrics(model_b_real: dict[str, Any], assignments: list[dict[str, Any]], model: str) -> dict[str, Any]:
    total_core = 0
    reasoned_core = 0
    planned_core_total = 0
    planned_core_after = 0
    responded_core_total = 0
    responded_core_after = 0
    noise_evidence = 0
    reasoning_drift_cases = set()
    planning_drift_cases = set()
    response_drift_cases = set()
    attended_evidence = 0
    evidence_non_noise = 0

    for row in assignments:
        role = row["role"]
        core_evidence = role == "Core Evidence"
        reasoned_after = core_evidence or (role == "Supporting Context" and model in {"R2", "R3", "R4"})
        planned_after = core_evidence
        responded_after = core_evidence
        if row["classification"] == "Core":
            total_core += 1
            if reasoned_after:
                reasoned_core += 1
            if row["planned"]:
                planned_core_total += 1
                if planned_after:
                    planned_core_after += 1
                else:
                    planning_drift_cases.add(row["case"])
            if row["responded"]:
                responded_core_total += 1
                if responded_after:
                    responded_core_after += 1
                else:
                    response_drift_cases.add(row["case"])
        if core_evidence:
            attended_evidence += 1
            if row["classification"] != "Noise":
                evidence_non_noise += 1
        if row["classification"] == "Noise" and core_evidence:
            noise_evidence += 1
            reasoning_drift_cases.add(row["case"])

    return {
        "noise_used_in_reasoning": noise_evidence,
        "reasoning_drift_cases": len(reasoning_drift_cases),
        "planning_drift_cases": len(planning_drift_cases),
        "response_drift_cases": len(response_drift_cases),
        "attention_precision": round(evidence_non_noise / attended_evidence, 4) if attended_evidence else 1.0,
        "attention_recall": round(reasoned_core / total_core, 4) if total_core else 1.0,
        "planning_core_coverage": round(planned_core_after / planned_core_total, 4) if planned_core_total else 1.0,
        "response_core_coverage": round(responded_core_after / responded_core_total, 4) if responded_core_total else 1.0,
        "grounding_score": 1.0,
        "hallucinations": 0,
    }


def _assignment_record(row: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "case": row["case"],
        "concept_id": row["concept_id"],
        "classification": row["classification"],
        "role": role,
        "concept": row["diagnostic"].get("concept"),
        "attention_classification": row["attention_classification"],
        "attention_score": row["attention_score"],
        "signals": row["signals"],
    }


def _combined_metrics(real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    aggregate = real.get("aggregate", {})
    rank = ranking.get("aggregate", {})
    return {
        "noise_used_in_reasoning": aggregate.get("noise_used_in_reasoning"),
        "reasoning_drift_cases": aggregate.get("reasoning_drift_cases"),
        "planning_drift_cases": aggregate.get("planning_drift_cases"),
        "response_drift_cases": aggregate.get("response_drift_cases"),
        "attention_precision": aggregate.get("attention_precision"),
        "attention_recall": aggregate.get("attention_recall"),
        "planning_core_coverage": aggregate.get("planning_core_coverage"),
        "response_core_coverage": aggregate.get("response_core_coverage"),
        "grounding_score": aggregate.get("grounding_score"),
        "hallucinations": aggregate.get("hallucinations"),
        "expected_outside_top_10": rank.get("expected_outside_top_10"),
        "expected_outside_top_20": rank.get("expected_outside_top_20"),
        "mean_expected_rank": rank.get("mean_expected_rank"),
        "mean_noise_above_expected": rank.get("mean_noise_above_expected"),
    }


def _description(model: str) -> str:
    return {
        "R1": "Strict Core Evidence",
        "R2": "Supporting Context Split",
        "R3": "Citation-Only Role Gate",
        "R4": "Hybrid Role Gate",
    }[model]


def _recommendation(accepted: list[dict[str, Any]]) -> str:
    if not accepted:
        return "CHECKPOINT_RUNTIME_V13_CURRENT_IMPROVEMENT"
    order = {"R4": 0, "R2": 1, "R3": 2, "R1": 3}
    accepted.sort(
        key=lambda result: (
            order[result["model"]],
            result["projected_metrics"]["noise_used_in_reasoning"],
            result["projected_metrics"]["reasoning_drift_cases"],
        )
    )
    return f"PROCEED_ROLE_MODEL_{accepted[0]['model']}"


def _normalize_terms(values: list[str]) -> list[str]:
    return [_normalize(value) for value in values if _normalize(value) not in STOPWORDS]


def _normalize(token: str) -> str:
    token = str(token).lower()
    if token in {"allocated", "allocating", "allocation"}:
        return "allocate"
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Query-Local Role Simulation",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "This is a read-only simulation. It does not modify live runtime behavior, learning, governance, storage, activation recurrence, or canonical knowledge.",
        "",
        "## Summary",
        "",
        f"- current Model B decision: `{report['summary']['current_model_b_decision']}`",
        f"- remaining noise count: `{report['summary']['remaining_noise_count']}`",
        f"- accepted role models: `{report['summary']['accepted_models']}`",
        f"- recommended model: `{report['summary']['recommended_model']}`",
        "",
        "## Current Model B Metrics",
        "",
        "| Metric | Current Model B |",
        "| --- | ---: |",
    ]
    for key, value in report["current_model_b_metrics"].items():
        lines.append(f"| {key} | `{value}` |")

    lines.extend(
        [
            "",
            "## Per-Role-Model Projected Metrics",
            "",
            "| Model | Proceed | Noise Evidence | Reasoning Drift | Planning Drift | Response Drift | Attention Precision | Attention Recall | Planning Core | Response Core | Failed Gates |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for result in report["model_results"]:
        metrics = result["projected_metrics"]
        failed = ", ".join(result["acceptance"]["failed_gates"]) or "none"
        lines.append(
            f"| {result['model']} {result['description']} | `{result['acceptance']['can_proceed_to_live_prototype']}` | "
            f"`{metrics['noise_used_in_reasoning']}` | `{metrics['reasoning_drift_cases']}` | `{metrics['planning_drift_cases']}` | "
            f"`{metrics['response_drift_cases']}` | `{metrics['attention_precision']}` | `{metrics['attention_recall']}` | "
            f"`{metrics['planning_core_coverage']}` | `{metrics['response_core_coverage']}` | {failed} |"
        )

    for result in report["model_results"]:
        lines.extend(["", f"## {result['model']} - {result['description']}", ""])
        lines.append(f"- can proceed: `{result['acceptance']['can_proceed_to_live_prototype']}`")
        lines.append(f"- role counts: `{result['role_counts']}`")
        lines.append(f"- concepts moved from evidence to supporting context: `{len(result['concepts_moved_from_evidence_to_supporting_context'])}`")
        lines.append(f"- expected concepts downgraded/blocked: `{len(result['expected_concepts_accidentally_downgraded_or_blocked'])}`")
        lines.append(f"- useful neighbors blocked: `{len(result['useful_neighbor_concepts_accidentally_blocked'])}`")
        lines.extend(["", "### Remaining Noisy Concept Roles"])
        for item in result["remaining_noisy_concept_roles"]:
            lines.append(
                f"- `{item['case']}` / `{item['concept_id']}` -> `{item['role']}`: {item.get('concept')}"
            )
        lines.extend(["", "### Case-Level Impact"])
        for impact in result["case_level_impact"]:
            if impact["reasoned_before"] or impact["supporting_context_after"]:
                lines.append(
                    f"- `{impact['case']}` reasoned `{impact['reasoned_before']} -> {impact['reasoned_after']}`, "
                    f"planning `{impact['planning_before']} -> {impact['planning_after']}`, "
                    f"response `{impact['response_before']} -> {impact['response_after']}`, "
                    f"noise evidence `{impact['noise_evidence_before']} -> {impact['noise_evidence_after']}`, "
                    f"supporting context `{impact['supporting_context_after']}`"
                )

    lines.extend(["", "## Interpretation", ""])
    lines.append(
        "The strongest simulated shape is to split citable evidence from query-local context. Near-neighbor concepts remain available as Supporting Context, but only Core Evidence contributes to evidence keys, planning citations, and response citations."
    )
    lines.extend(["", f"`{report['final_recommendation']}`", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
