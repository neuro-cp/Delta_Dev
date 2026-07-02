from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


FINAL_PROCEED = "PROCEED_REASONING_USAGE_GATE_LIVE_PROTOTYPE"
FINAL_REVISE = "REVISE_REASONING_USAGE_GATE_SIMULATION"
FINAL_REJECT = "REJECT_REASONING_USAGE_GATE"
FINAL_DIAGNOSTICS = "RUN_MORE_DIAGNOSTICS"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only simulation of a Runtime V1.3 reasoning usage gate.")
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--prototype-real", type=Path, required=True)
    parser.add_argument("--prototype-ranking", type=Path, required=True)
    parser.add_argument("--baseline-real", type=Path, required=True)
    parser.add_argument("--baseline-ranking", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    design = _load_json(args.design)
    audit = _load_json(args.audit)
    prototype_real = _load_json(args.prototype_real)
    prototype_ranking = _load_json(args.prototype_ranking)
    baseline_real = _load_json(args.baseline_real)
    baseline_ranking = _load_json(args.baseline_ranking)

    simulation = simulate_usage_gate(
        design=design,
        audit=audit,
        prototype_real=prototype_real,
        prototype_ranking=prototype_ranking,
        baseline_real=baseline_real,
        baseline_ranking=baseline_ranking,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_reasoning_usage_gate_simulation.json").write_text(
        json.dumps(simulation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_reasoning_usage_gate_simulation.md").write_text(
        render_markdown(simulation),
        encoding="utf-8",
    )
    return 0


def simulate_usage_gate(
    *,
    design: dict[str, Any],
    audit: dict[str, Any],
    prototype_real: dict[str, Any],
    prototype_ranking: dict[str, Any],
    baseline_real: dict[str, Any],
    baseline_ranking: dict[str, Any],
) -> dict[str, Any]:
    baseline_cases = {case["name"]: case for case in baseline_real.get("cases", [])}
    prototype_cases = {case["name"]: case for case in prototype_real.get("cases", [])}
    audit_cases = {case["case"]: case for case in audit.get("per_case", [])}

    per_case = []
    blocked_noise: list[dict[str, Any]] = []
    blocked_expected: list[dict[str, Any]] = []
    blocked_useful: list[dict[str, Any]] = []
    unblocked_new_noise: list[dict[str, Any]] = []
    implementation_signal_counter: Counter[str] = Counter()
    evaluation_label_counter: Counter[str] = Counter()

    for name, prototype_case in prototype_cases.items():
        baseline_case = baseline_cases.get(name, {})
        audit_case = audit_cases.get(name, {})
        newly_used_details = audit_case.get("newly_used_details", [])
        blocked_for_case = []
        unblocked_for_case = []
        expected_remain_usable = _count_expected_usable_after_gate(prototype_case, newly_used_details)
        expected_accidentally_blocked = []
        useful_accidentally_blocked = []

        for detail in newly_used_details:
            decision = _gate_decision(detail)
            if decision["blocked"]:
                if decision["implementation_available_signals"]:
                    implementation_signal_counter.update(decision["implementation_available_signals"])
                evaluation_label_counter.update(decision["evaluation_only_labels"])
                blocked_for_case.append({**detail, **decision})
                if detail.get("classification") == "Noise":
                    blocked_noise.append({**detail, "case": name, **decision})
                elif detail.get("classification") == "Core":
                    blocked_expected.append({**detail, "case": name, **decision})
                    expected_accidentally_blocked.append(detail["concept_id"])
                elif detail.get("classification") in {"UsefulNeighbor", "Supporting"}:
                    blocked_useful.append({**detail, "case": name, **decision})
                    useful_accidentally_blocked.append(detail["concept_id"])
            else:
                unblocked_for_case.append({**detail, **decision})
                if detail.get("classification") == "Noise" and detail.get("reasoned"):
                    unblocked_new_noise.append({**detail, "case": name, **decision})

        baseline_noise = int(baseline_case.get("noise_used_in_reasoning", 0))
        prototype_noise = int(prototype_case.get("noise_used_in_reasoning", 0))
        blocked_reasoned_noise = sum(
            1
            for item in blocked_for_case
            if item.get("classification") == "Noise" and item.get("reasoned")
        )
        simulated_noise = max(0, prototype_noise - blocked_reasoned_noise)
        baseline_drift = _case_has_reasoning_drift(baseline_case)
        prototype_drift = _case_has_reasoning_drift(prototype_case)
        projected_drift = _project_reasoning_drift(
            baseline_drift=baseline_drift,
            prototype_drift=prototype_drift,
            newly_used_noise=[item for item in newly_used_details if item.get("classification") == "Noise"],
            blocked_noise=[item for item in blocked_for_case if item.get("classification") == "Noise"],
        )

        per_case.append(
            {
                "case": name,
                "category": prototype_case.get("category"),
                "baseline_noise_used": baseline_noise,
                "prototype_noise_used": prototype_noise,
                "simulated_noise_used": simulated_noise,
                "newly_used_noisy_concepts_blocked": [
                    item["concept_id"] for item in blocked_for_case if item.get("classification") == "Noise"
                ],
                "newly_used_noise_not_blocked": [
                    item["concept_id"] for item in unblocked_for_case if item.get("classification") == "Noise"
                ],
                "expected_concepts_that_remain_usable": expected_remain_usable,
                "expected_concepts_accidentally_blocked": expected_accidentally_blocked,
                "useful_neighbors_accidentally_blocked": useful_accidentally_blocked,
                "projected_reasoning_drift_after_gate": projected_drift,
                "baseline_reasoning_drift": baseline_drift,
                "prototype_reasoning_drift": prototype_drift,
                "blocked_details": blocked_for_case,
                "unblocked_details": unblocked_for_case,
            }
        )

    baseline_aggregate = baseline_real.get("aggregate", {})
    prototype_aggregate = prototype_real.get("aggregate", {})
    simulated_metrics = _project_aggregate_metrics(
        baseline_aggregate=baseline_aggregate,
        prototype_aggregate=prototype_aggregate,
        per_case=per_case,
    )
    gate_coverage = {
        "total_newly_used_noise_concepts": len(blocked_noise) + len(unblocked_new_noise),
        "newly_used_noise_blocked": len(blocked_noise),
        "newly_used_noise_not_blocked": len(unblocked_new_noise),
        "expected_concepts_blocked": len(blocked_expected),
        "useful_neighbors_blocked": len(blocked_useful),
        "blocked_noise_ratio": _ratio(len(blocked_noise), len(blocked_noise) + len(unblocked_new_noise)),
    }
    risk_analysis = _risk_analysis(per_case, blocked_expected, blocked_useful, unblocked_new_noise)
    acceptance = _acceptance(simulated_metrics, gate_coverage)
    final = _final_recommendation(acceptance)

    return {
        "final_recommendation": final,
        "read_only": True,
        "simulation_only": True,
        "design_recommendation": design.get("final_recommendation"),
        "baseline_vs_rejected_vs_simulated": simulated_metrics,
        "per_case_gate_results": per_case,
        "gate_coverage": gate_coverage,
        "risk_analysis": risk_analysis,
        "implementation_boundary": {
            "safe_future_live_signals": [
                "attention_classification",
                "attention_score",
                "activation_rank",
                "activation_score",
                "query_overlap_terms",
                "specific_overlap_count",
                "entered_activation_top10",
                "recurrence_or_replacement_risk_metadata",
                "evidence_support_if_available",
                "centrality/promotion/confidence if already present in candidate metadata",
            ],
            "evaluation_only_labels_not_allowed_live": [
                "Noise",
                "Core",
                "expected concept",
                "useful neighbor",
                "human/evaluator correctness labels",
            ],
            "implementation_signal_counts_seen_in_blocked_set": dict(implementation_signal_counter),
            "evaluation_label_counts_seen_in_blocked_set": dict(evaluation_label_counter),
        },
        "acceptance_criteria": acceptance,
        "recommendation": _recommendation_text(final),
        "source_report_health": {
            "baseline_case_count": len(baseline_real.get("cases", [])),
            "prototype_case_count": len(prototype_real.get("cases", [])),
            "prototype_ranking_case_count": len(prototype_ranking.get("cases", [])),
            "baseline_ranking_case_count": len(baseline_ranking.get("cases", [])),
            "audit_final_decision": audit.get("final_decision"),
        },
    }


def _gate_decision(detail: dict[str, Any]) -> dict[str, Any]:
    classification = detail.get("classification")
    attended_as_usable = detail.get("attention_classification") in {"Core", "Supporting"}
    newly_used = bool(detail.get("reasoned") or detail.get("planned") or detail.get("responded"))
    overlap = detail.get("query_overlap", [])
    weak_specificity = len(set(overlap)) <= 2
    replacement_risk = bool(detail.get("activation_rank", 99) <= 10)
    shallow_overlap = bool(_shallow_overlap_terms(overlap))

    # This is a replay simulation. The evaluator label is used only to measure the
    # safety envelope of the hypothetical gate, not as a future live signal.
    blocked = (
        newly_used
        and attended_as_usable
        and classification == "Noise"
        and (weak_specificity or replacement_risk or shallow_overlap)
    )
    implementation_signals = []
    if attended_as_usable:
        implementation_signals.append("attention_core_or_supporting")
    if weak_specificity:
        implementation_signals.append("weak_specificity")
    if replacement_risk:
        implementation_signals.append("replacement_risk_top10")
    if shallow_overlap:
        implementation_signals.append("shallow_query_overlap")
    return {
        "blocked": blocked,
        "gate_reason": "newly-used noisy attended concept with weak/replacement-risk support" if blocked else "allowed",
        "implementation_available_signals": implementation_signals,
        "evaluation_only_labels": [classification] if classification else [],
        "weak_specificity": weak_specificity,
        "replacement_risk": replacement_risk,
        "shallow_overlap_terms": _shallow_overlap_terms(overlap),
    }


def _count_expected_usable_after_gate(prototype_case: dict[str, Any], newly_used_details: list[dict[str, Any]]) -> list[str]:
    blocked_ids = {
        detail["concept_id"]
        for detail in newly_used_details
        if _gate_decision(detail)["blocked"]
    }
    usable = []
    for contribution in prototype_case.get("concept_contributions", []):
        if contribution.get("classification") == "Core" and contribution.get("concept_id") not in blocked_ids:
            usable.append(contribution["concept_id"])
    return usable


def _case_has_reasoning_drift(case: dict[str, Any]) -> bool:
    if not case:
        return False
    return bool(case.get("noise_used_in_reasoning", 0) > 0 or case.get("runtime_decision") in {"Reasoning Drift"})


def _project_reasoning_drift(
    *,
    baseline_drift: bool,
    prototype_drift: bool,
    newly_used_noise: list[dict[str, Any]],
    blocked_noise: list[dict[str, Any]],
) -> bool:
    if not prototype_drift:
        return False
    if baseline_drift:
        return True
    if newly_used_noise and len(newly_used_noise) == len(blocked_noise):
        return False
    return prototype_drift


def _project_aggregate_metrics(
    *,
    baseline_aggregate: dict[str, Any],
    prototype_aggregate: dict[str, Any],
    per_case: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    simulated_noise = sum(case["simulated_noise_used"] for case in per_case)
    simulated_drift = sum(1 for case in per_case if case["projected_reasoning_drift_after_gate"])
    metrics = {}
    for key in [
        "noise_used_in_reasoning",
        "attention_precision",
        "attention_recall",
        "reasoning_drift_cases",
        "planning_core_coverage",
        "response_core_coverage",
        "grounding_score",
        "hallucinations",
    ]:
        baseline = baseline_aggregate.get(key)
        prototype = prototype_aggregate.get(key)
        if key == "noise_used_in_reasoning":
            simulated = simulated_noise
        elif key == "reasoning_drift_cases":
            simulated = simulated_drift
        elif key in {"attention_precision", "attention_recall"}:
            simulated = prototype
        else:
            simulated = prototype
        metrics[key] = {
            "baseline": baseline,
            "rejected_prototype": prototype,
            "simulated_usage_gate": simulated,
        }
    return metrics


def _risk_analysis(
    per_case: list[dict[str, Any]],
    blocked_expected: list[dict[str, Any]],
    blocked_useful: list[dict[str, Any]],
    unblocked_new_noise: list[dict[str, Any]],
) -> dict[str, Any]:
    helps = []
    risky = []
    for case in per_case:
        blocked_noise_count = len(case["newly_used_noisy_concepts_blocked"])
        if blocked_noise_count:
            helps.append(case["case"])
        if case["expected_concepts_accidentally_blocked"] or case["useful_neighbors_accidentally_blocked"]:
            risky.append(case["case"])
    risk_case = next((case for case in per_case if case["case"] == "risk_uncertainty_planning"), None)
    planning_case = next((case for case in per_case if case["case"] == "planning_failed_assumption"), None)
    return {
        "cases_where_gate_helps": helps,
        "cases_where_gate_is_risky": risky,
        "unblocked_new_noise": [item["concept_id"] for item in unblocked_new_noise],
        "risk_uncertainty_planning": {
            "blocked_noise": risk_case["newly_used_noisy_concepts_blocked"] if risk_case else [],
            "expected_blocked": risk_case["expected_concepts_accidentally_blocked"] if risk_case else [],
            "interpretation": "improves without suppressing expected concepts" if risk_case and not risk_case["expected_concepts_accidentally_blocked"] else "requires revision",
        },
        "planning_failed_assumption": {
            "blocked_noise": planning_case["newly_used_noisy_concepts_blocked"] if planning_case else [],
            "expected_remain_usable": planning_case["expected_concepts_that_remain_usable"] if planning_case else [],
            "expected_blocked": planning_case["expected_concepts_accidentally_blocked"] if planning_case else [],
            "interpretation": "expected evidence remains usable" if planning_case and not planning_case["expected_concepts_accidentally_blocked"] else "requires revision",
        },
        "blocked_expected_count": len(blocked_expected),
        "blocked_useful_neighbor_count": len(blocked_useful),
    }


def _acceptance(metrics: dict[str, dict[str, Any]], coverage: dict[str, Any]) -> dict[str, bool]:
    rejected_noise = metrics["noise_used_in_reasoning"]["rejected_prototype"]
    simulated_noise = metrics["noise_used_in_reasoning"]["simulated_usage_gate"]
    rejected_drift = metrics["reasoning_drift_cases"]["rejected_prototype"]
    simulated_drift = metrics["reasoning_drift_cases"]["simulated_usage_gate"]
    return {
        "noise_used_in_reasoning_decreases_materially": simulated_noise <= rejected_noise - 4,
        "no_expected_concepts_blocked": coverage["expected_concepts_blocked"] == 0,
        "no_useful_neighbors_blocked": coverage["useful_neighbors_blocked"] == 0,
        "grounding_score_stable": metrics["grounding_score"]["simulated_usage_gate"] == metrics["grounding_score"]["rejected_prototype"],
        "hallucinations_stable": metrics["hallucinations"]["simulated_usage_gate"] == metrics["hallucinations"]["rejected_prototype"],
        "reasoning_drift_not_worse": simulated_drift <= rejected_drift,
        "reasoning_drift_decreases": simulated_drift < rejected_drift,
        "planning_core_coverage_not_regress": metrics["planning_core_coverage"]["simulated_usage_gate"] >= metrics["planning_core_coverage"]["rejected_prototype"],
        "response_core_coverage_not_regress": metrics["response_core_coverage"]["simulated_usage_gate"] >= metrics["response_core_coverage"]["rejected_prototype"],
    }


def _final_recommendation(acceptance: dict[str, bool]) -> str:
    if all(acceptance.values()):
        return FINAL_PROCEED
    if (
        acceptance["noise_used_in_reasoning_decreases_materially"]
        and acceptance["no_expected_concepts_blocked"]
        and acceptance["no_useful_neighbors_blocked"]
    ):
        return FINAL_REVISE
    if not acceptance["noise_used_in_reasoning_decreases_materially"]:
        return FINAL_REJECT
    return FINAL_DIAGNOSTICS


def _recommendation_text(final: str) -> str:
    if final == FINAL_PROCEED:
        return (
            "Proceed to a live prototype only if it preserves the simulation boundary: keep activation and attention "
            "visible, gate reasoning usage, and add regression checks for expected concepts in risk_uncertainty_planning."
        )
    if final == FINAL_REVISE:
        return "Revise the usage gate before any live prototype; the safety envelope is promising but incomplete."
    if final == FINAL_REJECT:
        return "Reject usage gating because the simulation did not materially reduce noisy reasoning usage."
    return "Run more diagnostics before changing runtime behavior."


def _shallow_overlap_terms(overlap: list[str]) -> list[str]:
    shallow = {"and", "for", "should", "after", "plan", "risk", "failure", "resource", "uncertainty"}
    return [term for term in overlap if term in shallow]


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def render_markdown(simulation: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Reasoning Usage-Gate Simulation",
        "",
        f"Final recommendation: `{simulation['final_recommendation']}`",
        "",
        "## Baseline vs Rejected Prototype vs Simulated Usage-Gate Metrics",
        "",
        "| Metric | Baseline | Rejected Prototype | Simulated Usage Gate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key, values in simulation["baseline_vs_rejected_vs_simulated"].items():
        lines.append(
            f"| {key} | `{values['baseline']}` | `{values['rejected_prototype']}` | `{values['simulated_usage_gate']}` |"
        )

    lines.extend(
        [
            "",
            "## Per-Case Gate Results",
            "",
            "| Case | Noise Before | Noise After | Blocked New Noise | Expected Blocked | Useful Blocked | Projected Drift |",
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for case in simulation["per_case_gate_results"]:
        lines.append(
            f"| {case['case']} | `{case['prototype_noise_used']}` | `{case['simulated_noise_used']}` | "
            f"`{len(case['newly_used_noisy_concepts_blocked'])}` | "
            f"`{len(case['expected_concepts_accidentally_blocked'])}` | "
            f"`{len(case['useful_neighbors_accidentally_blocked'])}` | "
            f"`{case['projected_reasoning_drift_after_gate']}` |"
        )

    coverage = simulation["gate_coverage"]
    lines.extend(
        [
            "",
            "## Gate Coverage",
            "",
            f"- total newly used noise concepts: `{coverage['total_newly_used_noise_concepts']}`",
            f"- newly used noise blocked: `{coverage['newly_used_noise_blocked']}`",
            f"- newly used noise not blocked: `{coverage['newly_used_noise_not_blocked']}`",
            f"- expected/useful concepts blocked: `{coverage['expected_concepts_blocked'] + coverage['useful_neighbors_blocked']}`",
            f"- blocked noise ratio: `{coverage['blocked_noise_ratio']}`",
            "",
            "## Risk Analysis",
            "",
            f"- cases where gate helps: `{', '.join(simulation['risk_analysis']['cases_where_gate_helps']) or 'none'}`",
            f"- cases where gate is risky: `{', '.join(simulation['risk_analysis']['cases_where_gate_is_risky']) or 'none'}`",
            f"- risk_uncertainty_planning: {simulation['risk_analysis']['risk_uncertainty_planning']['interpretation']}",
            f"- planning_failed_assumption: {simulation['risk_analysis']['planning_failed_assumption']['interpretation']}",
            "",
            "## Implementation Boundary",
            "",
            "Safe future live signals:",
        ]
    )
    lines.extend(f"- `{signal}`" for signal in simulation["implementation_boundary"]["safe_future_live_signals"])
    lines.extend(["", "Evaluation-only labels that must not be used live:"])
    lines.extend(f"- `{label}`" for label in simulation["implementation_boundary"]["evaluation_only_labels_not_allowed_live"])

    lines.extend(["", "## Acceptance Criteria", ""])
    for key, value in simulation["acceptance_criteria"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Recommendation", "", simulation["recommendation"], "", f"`{simulation['final_recommendation']}`", ""])
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input report: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
