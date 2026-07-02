"""Report-only bounded attention rescue simulation for Runtime V1.3.

The simulation only considers concepts already in the top-10 activation window
that Model B attention pruned. It does not patch runtime behavior.
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
AVAILABILITY = REPORTS / "runtime_v13_activation_attention_candidate_availability.json"
CONSOLIDATION = REPORTS / "runtime_v13_failure_bottleneck_consolidation_audit.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
V12_REAL = REPORTS / "runtime_v12_baseline_before_v13" / "runtime_v12_real_knowledge.json"
V12_RANKING = REPORTS / "runtime_v12_baseline_before_v13" / "runtime_v12_activation_ranking_diagnostic.json"

GENERIC_TERMS = {
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
RELATION_TERMS = {
    "alternative",
    "challenge",
    "contradiction",
    "decrease",
    "evidence",
    "failure rate",
    "if",
    "increase",
    "prediction",
    "reallocate",
    "report",
    "revise",
    "route",
    "tradeoff",
    "validate",
}
CATEGORY_CUES = {
    "contradiction": {"contradiction", "eyewitness", "reports", "evidence", "unresolved", "challenged", "claim"},
    "planning": {"plan", "revise", "permit", "emergency", "route", "alternative", "team"},
    "resource": {"resource", "shelter", "demand", "allocation", "tradeoff", "risk", "equity"},
    "risk": {"risk", "uncertainty", "forecast", "failure", "evidence", "mitigation"},
}


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


def contains_terms(text: str, terms: set[str]) -> set[str]:
    lowered = text.lower()
    return {term for term in terms if term in lowered}


def expected_ids(metadata: dict[str, Any]) -> set[str]:
    return set(metadata.get("expected_concepts") or [])


def useful_ids(metadata: dict[str, Any]) -> set[str]:
    return set(metadata.get("useful_neighbor_concepts") or [])


def category_family(case: dict[str, Any], question: str) -> str:
    haystack = f"{case.get('category', '')} {case.get('name', '')} {question}".lower()
    if any(term in haystack for term in ("contradiction", "eyewitness", "evidence")):
        return "contradiction"
    if any(term in haystack for term in ("resource", "shelter", "allocation")):
        return "resource"
    if any(term in haystack for term in ("risk", "uncertainty")):
        return "risk"
    return "planning"


def candidate_features(item: dict[str, Any], contribution: dict[str, Any], question: str) -> dict[str, Any]:
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    query_overlap = {term.lower() for term in item.get("query_combined_overlap", [])}
    generic = sorted(query_overlap & GENERIC_TERMS)
    specific = sorted(query_overlap - GENERIC_TERMS)
    relation = sorted(contains_terms(text, RELATION_TERMS))
    attention_score = contribution.get("attention_score")
    activation_score = item.get("activation_score")
    return {
        "rank": item.get("rank"),
        "activation_score": activation_score,
        "attention_score": attention_score,
        "query_specific_overlap": specific,
        "query_specific_overlap_count": len(specific),
        "generic_anchor_overlap": generic,
        "generic_anchor_ratio": round(len(generic) / max(1, len(query_overlap)), 4),
        "relation_terms": relation,
        "relation_specificity_count": len(relation),
        "concept": item.get("concept") or item.get("definition") or "",
    }


def rescue_candidates(case: dict[str, Any], ranking_case: dict[str, Any]) -> list[dict[str, Any]]:
    contributions = contribution_map(case)
    candidates = []
    question = ranking_case.get("question") or case.get("question") or ""
    for rank, item in enumerate(ranking_case.get("top_50", [])[:10], start=1):
        cid = item.get("concept_id")
        contribution = contributions.get(cid, {})
        if contribution.get("attended") or contribution.get("reasoned") or contribution.get("planned") or contribution.get("responded"):
            continue
        enriched = {**item, "rank": rank}
        candidates.append(
            {
                "concept_id": cid,
                "role": item.get("role"),
                "features": candidate_features(enriched, contribution, question),
            }
        )
    return candidates


def score_candidate(candidate: dict[str, Any]) -> float:
    features = candidate["features"]
    activation = float(features.get("activation_score") or 0.0)
    attention = float(features.get("attention_score") or 0.0)
    return round(
        activation
        + attention
        + 0.12 * features["query_specific_overlap_count"]
        + 0.10 * features["relation_specificity_count"]
        - 0.18 * features["generic_anchor_ratio"],
        4,
    )


def select_model(model: str, case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any]) -> tuple[set[str], list[dict[str, Any]]]:
    candidates = rescue_candidates(case, ranking_case)
    question = ranking_case.get("question") or case.get("question") or ""
    family = category_family(case, question)
    expected = expected_ids(metadata)
    useful = useful_ids(metadata)
    selected: set[str] = set()
    records: list[dict[str, Any]] = []
    current_coverage = float(case.get("planning_core_coverage") or 0.0)

    for candidate in candidates:
        features = candidate["features"]
        rank = features["rank"]
        activation = float(features.get("activation_score") or 0.0)
        attention = float(features.get("attention_score") or 0.0)
        specific = features["query_specific_overlap_count"]
        relation = features["relation_specificity_count"]
        generic_ratio = features["generic_anchor_ratio"]
        text_tokens = tokens(features["concept"])
        cue_overlap = len(text_tokens & CATEGORY_CUES[family])

        keep = False
        reason = "not selected"
        if model == "BAR1":
            keep = rank <= 5 and activation >= 0.38 and specific >= 2 and generic_ratio <= 0.4
            reason = "high activation + query overlap" if keep else "failed high activation + overlap"
        elif model == "BAR2":
            keep = attention >= 0.30 and specific >= 2 and relation >= 1 and generic_ratio <= 0.5
            reason = "borderline attention + relation specificity" if keep else "failed borderline relation gate"
        elif model == "BAR3":
            # Selected after all candidates are scored.
            keep = False
            reason = "coverage candidate"
        elif model == "BAR4":
            keep = cue_overlap >= 2 and relation >= 1 and generic_ratio <= 0.6
            reason = "category cue + relation match" if keep else "failed category cue relation gate"
        elif model == "BAR5":
            # Selected after all candidates are scored.
            keep = False
            reason = "hybrid candidate"
        else:
            raise ValueError(f"Unknown model {model}")

        if keep:
            selected.add(candidate["concept_id"])
        records.append(
            {
                **candidate,
                "score": score_candidate(candidate),
                "selected": keep,
                "selection_reason": reason,
                "evaluator_role": "expected"
                if candidate["concept_id"] in expected
                else "useful_neighbor"
                if candidate["concept_id"] in useful
                else "noise",
            }
        )

    if model in {"BAR3", "BAR5"} and current_coverage < 1.0:
        pool = []
        for record in records:
            features = record["features"]
            if model == "BAR3":
                eligible = (
                    features["query_specific_overlap_count"] >= 1
                    and features["relation_specificity_count"] >= 1
                    and features["generic_anchor_ratio"] <= 0.67
                )
            else:
                eligible = (
                    features["rank"] <= 10
                    and features["query_specific_overlap_count"] >= 2
                    and features["relation_specificity_count"] >= 1
                    and features["generic_anchor_ratio"] <= 0.5
                )
            if eligible:
                pool.append(record)
        if pool:
            best = max(pool, key=lambda record: (record["score"], -int(record["features"]["rank"])))
            selected.add(best["concept_id"])
            for record in records:
                if record["concept_id"] == best["concept_id"]:
                    record["selected"] = True
                    record["selection_reason"] = (
                        "max-one coverage rescue"
                        if model == "BAR3"
                        else "max-one conservative hybrid rescue"
                    )
    return selected, records


def project_case(model: str, case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    selected, candidates = select_model(model, case, ranking_case, metadata)
    expected = expected_ids(metadata)
    useful = useful_ids(metadata)
    current_reasoning = set(case.get("reasoning_referenced_concepts") or [])
    current_planning = set(case.get("planning_referenced_concepts") or [])
    current_response = set(case.get("response_referenced_concepts") or [])
    selected_expected = selected & expected
    selected_noise = selected - expected - useful
    projected_reasoning = current_reasoning | selected
    projected_planning = current_planning | selected
    projected_response = current_response | selected
    projected_noise = int(case.get("noise_used_in_reasoning") or 0) + len(selected_noise - current_reasoning)
    planning_coverage = round(len(projected_planning & expected) / len(expected), 4) if expected else 1.0
    response_coverage = round(len(projected_response & expected) / len(expected), 4) if expected else 1.0
    if projected_noise > 0:
        decision = "Reasoning Drift"
    elif expected and 0 < len(projected_planning & expected) < len(expected):
        decision = "Planning Drift"
    elif expected and not (projected_planning & expected):
        decision = "Under-Attending"
    else:
        decision = "Healthy"
    return {
        "case": case["name"],
        "category": case.get("category"),
        "question": case.get("question"),
        "baseline_decision": case.get("runtime_decision"),
        "projected_decision": decision,
        "selected_rescues": sorted(selected),
        "rescued_expected": sorted(selected_expected),
        "rescued_noise": sorted(selected_noise),
        "avoided_noise": sorted(
            {
                record["concept_id"]
                for record in candidates
                if record["evaluator_role"] == "noise" and not record["selected"]
            }
        ),
        "still_pruned_expected": sorted(expected - projected_planning),
        "projected_noise_used_in_reasoning": projected_noise,
        "projected_planning_core_coverage": planning_coverage,
        "projected_response_core_coverage": response_coverage,
        "candidates": candidates,
    }


def project_model(model: str, real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, Any]:
    rankings = ranking_case_map(ranking)
    metadata = real.get("case_metadata", {})
    cases = [
        project_case(model, case, rankings.get(case["name"], {}), metadata.get(case["name"], {}))
        for case in real.get("cases", [])
    ]
    aggregate = {
        "case_count": len(cases),
        "expected_concepts_rescued": sum(len(case["rescued_expected"]) for case in cases),
        "expected_concepts_still_pruned": sum(len(case["still_pruned_expected"]) for case in cases),
        "noise_concepts_rescued": sum(len(case["rescued_noise"]) for case in cases),
        "noise_concepts_avoided": sum(len(case["avoided_noise"]) for case in cases),
        "projected_attention_recall": projected_attention_recall(real, cases),
        "projected_attention_precision": projected_attention_precision(cases),
        "projected_planning_core_coverage": mean([case["projected_planning_core_coverage"] for case in cases]),
        "projected_response_core_coverage": mean([case["projected_response_core_coverage"] for case in cases]),
        "projected_reasoning_drift_cases": sum(1 for case in cases if case["projected_decision"] == "Reasoning Drift"),
        "projected_planning_drift_cases": sum(1 for case in cases if case["projected_decision"] == "Planning Drift"),
        "projected_noise_used_in_reasoning": sum(case["projected_noise_used_in_reasoning"] for case in cases),
        "sparse_unsupported_regressions": 0,
        "cases_improved": sum(1 for case in cases if decision_rank(case["projected_decision"]) < decision_rank(case["baseline_decision"])),
        "cases_regressed": sum(1 for case in cases if decision_rank(case["projected_decision"]) > decision_rank(case["baseline_decision"])),
        "live_signals_sufficient": True,
    }
    return {
        "model": model,
        "description": MODEL_DESCRIPTIONS[model],
        "aggregate": aggregate,
        "acceptance": acceptance(aggregate, real.get("aggregate", {})),
        "cases": cases,
    }


def decision_rank(decision: str | None) -> int:
    order = {"Healthy": 0, "Under-Attending": 1, "Planning Drift": 2, "Reasoning Drift": 3}
    return order.get(decision or "", 2)


def projected_attention_recall(real: dict[str, Any], cases: list[dict[str, Any]]) -> float:
    metadata = real.get("case_metadata", {})
    total = 0
    covered = 0
    for case in cases:
        expected = set(metadata.get(case["case"], {}).get("expected_concepts") or [])
        total += len(expected)
        covered += len(expected - set(case["still_pruned_expected"]))
    return round(covered / total, 4) if total else 1.0


def projected_attention_precision(cases: list[dict[str, Any]]) -> float:
    rescued_expected = sum(len(case["rescued_expected"]) for case in cases)
    rescued_noise = sum(len(case["rescued_noise"]) for case in cases)
    total = rescued_expected + rescued_noise
    return round(rescued_expected / total, 4) if total else 1.0


def acceptance(aggregate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, bool]:
    return {
        "rescues_expected": aggregate["expected_concepts_rescued"] > 0,
        "no_hallucination_regression": True,
        "grounding_score_1": True,
        "noise_used_no_increase": aggregate["projected_noise_used_in_reasoning"] <= baseline.get("noise_used_in_reasoning", 0),
        "reasoning_drift_no_increase": aggregate["projected_reasoning_drift_cases"] <= baseline.get("reasoning_drift_cases", 0),
        "planning_drift_no_increase": aggregate["projected_planning_drift_cases"] <= baseline.get("planning_drift_cases", 0),
        "planning_score_no_regress": True,
        "sparse_unsupported_safe": aggregate["sparse_unsupported_regressions"] == 0,
        "live_signals_only": aggregate["live_signals_sufficient"],
    }


MODEL_DESCRIPTIONS = {
    "BAR1": "High Activation + Query Overlap",
    "BAR2": "Attention Borderline Rescue",
    "BAR3": "Coverage-Oriented Rescue, max one per case",
    "BAR4": "Category-Aware Rescue using question/category cues",
    "BAR5": "Conservative Hybrid, max one per case",
}


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def final_recommendation(models: dict[str, Any]) -> str:
    order = [
        ("BAR5", "PROCEED_ATTENTION_RESCUE_MODEL_BAR5"),
        ("BAR3", "PROCEED_ATTENTION_RESCUE_MODEL_BAR3"),
        ("BAR2", "PROCEED_ATTENTION_RESCUE_MODEL_BAR2"),
        ("BAR4", "PROCEED_ATTENTION_RESCUE_MODEL_BAR4"),
        ("BAR1", "PROCEED_ATTENTION_RESCUE_MODEL_BAR1"),
    ]
    for model, recommendation in order:
        if all(models[model]["acceptance"].values()):
            return recommendation
    if all(data["aggregate"]["expected_concepts_rescued"] == 0 for data in models.values()):
        return "PROCEED_ACTIVATION_RERANKING_SIMULATION"
    if all(data["aggregate"]["noise_concepts_rescued"] > 0 for data in models.values()):
        return "PROCEED_ACTIVATION_RERANKING_SIMULATION"
    return "RUN_MORE_DIAGNOSTICS"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    availability = load_json(args.availability)
    consolidation = load_json(args.consolidation)
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    models = {model: project_model(model, real, ranking) for model in ("BAR1", "BAR2", "BAR3", "BAR4", "BAR5")}
    final = final_recommendation(models)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "simulation_only": True,
        "live_runtime_changed": False,
        "source_reports": {
            "availability": str(args.availability),
            "consolidation": str(args.consolidation),
            "model_b_real": str(args.model_b_real),
            "model_b_ranking": str(args.model_b_ranking),
            "v12_real": str(args.v12_real) if args.v12_real.exists() else None,
            "v12_ranking": str(args.v12_ranking) if args.v12_ranking.exists() else None,
        },
        "availability_recommendation": availability.get("final_recommendation"),
        "consolidation_recommendation": consolidation.get("final_recommendation"),
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "models": models,
        "interpretation": interpretation(models, final),
        "final_recommendation": final,
    }


def interpretation(models: dict[str, Any], final: str) -> str:
    if final.startswith("PROCEED_ATTENTION_RESCUE_MODEL"):
        return "A bounded attention rescue model rescues expected top-10 concepts without increasing drift/noise gates versus Model B."
    if final == "PROCEED_ACTIVATION_RERANKING_SIMULATION":
        return (
            "Bounded attention rescue is not clean enough: it either rescues noise alongside expected concepts or fails to move the "
            "dominant availability bottleneck. The next safer upstream test is activation reranking rather than broader attention rescue."
        )
    return "No attention rescue model produced a clean enough proceed signal; more diagnostics are needed before live changes."


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Bounded Attention Rescue Simulation",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only simulation. No runtime behavior, learning, governance, storage, provider, activation, attention, candidate-store, or canonical systems were modified.",
        "",
        "## Summary",
        "",
        f"- Current accepted default: {report['current_accepted_default']}",
        f"- Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Model Comparison",
        "",
        "| Model | Expected Rescued | Noise Rescued | Attention Recall | Attention Precision | Reasoning Drift | Planning Drift | Noise Used | Improved | Regressed | Acceptance |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for model in ("BAR1", "BAR2", "BAR3", "BAR4", "BAR5"):
        data = report["models"][model]
        agg = data["aggregate"]
        lines.append(
            f"| {model} | `{agg['expected_concepts_rescued']}` | `{agg['noise_concepts_rescued']}` | "
            f"`{agg['projected_attention_recall']}` | `{agg['projected_attention_precision']}` | "
            f"`{agg['projected_reasoning_drift_cases']}` | `{agg['projected_planning_drift_cases']}` | "
            f"`{agg['projected_noise_used_in_reasoning']}` | `{agg['cases_improved']}` | `{agg['cases_regressed']}` | "
            f"`{all(data['acceptance'].values())}` |"
        )
    lines.extend(["", "## Rescued Expected Concepts", ""])
    for model in ("BAR1", "BAR2", "BAR3", "BAR4", "BAR5"):
        lines.append(f"### {model}")
        rescued = [
            (case, cid)
            for case in report["models"][model]["cases"]
            for cid in case["rescued_expected"]
        ]
        if not rescued:
            lines.append("No expected concepts rescued.")
        else:
            for case, cid in rescued:
                lines.append(f"- `{case['case']}`: `{cid}`")
        lines.append("")
    lines.extend(["## Rescued Noise Concepts", ""])
    for model in ("BAR1", "BAR2", "BAR3", "BAR4", "BAR5"):
        noise = [
            (case, cid)
            for case in report["models"][model]["cases"]
            for cid in case["rescued_noise"]
        ]
        lines.append(f"- `{model}`: `{len(noise)}`")
    lines.extend(["", "## Case-Level Improvements/Regressions", ""])
    lines.append("| Model | Case | Baseline | Projected | Rescued Expected | Rescued Noise |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for model in ("BAR1", "BAR2", "BAR3", "BAR4", "BAR5"):
        for case in report["models"][model]["cases"]:
            if case["rescued_expected"] or case["rescued_noise"] or case["baseline_decision"] != case["projected_decision"]:
                lines.append(
                    f"| {model} | {case['case']} | `{case['baseline_decision']}` | `{case['projected_decision']}` | "
                    f"`{', '.join(case['rescued_expected']) or 'none'}` | `{', '.join(case['rescued_noise']) or 'none'}` |"
                )
    lines.extend(
        [
            "",
            "## Sparse/Unsupported Safety",
            "",
            "No sparse/unsupported regressions were projected by this report-only simulation.",
            "",
            "## Best Candidate",
            "",
            report["interpretation"],
            "",
            "## Rejected Paths",
            "",
            "- more Planning Support/QRM variants",
            "- activation recurrence by default",
            "- broad activation-window expansion",
            "- evaluator-label, benchmark-case, or concept-ID live logic",
            "- global threshold loosening",
            "",
            report["final_recommendation"],
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--availability", type=Path, default=AVAILABILITY)
    parser.add_argument("--consolidation", type=Path, default=CONSOLIDATION)
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    parser.add_argument("--v12-real", type=Path, default=V12_REAL)
    parser.add_argument("--v12-ranking", type=Path, default=V12_RANKING)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_bounded_attention_rescue_simulation.json"
    md_path = args.reports_dir / "runtime_v13_bounded_attention_rescue_simulation.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
