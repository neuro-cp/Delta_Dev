from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


HIGH_RISK_CASES = {
    "risk_uncertainty_planning",
    "planning_failed_assumption",
    "policy_audit_conflict",
    "logistics_proxy_planning",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Design a read-only Runtime V1.3 attention-side recurrence/usage gating prototype."
    )
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--prototype-report", type=Path, required=True)
    parser.add_argument("--isolated", type=Path, required=True)
    parser.add_argument("--baseline-real", type=Path, required=True)
    parser.add_argument("--baseline-ranking", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    audit = _load_json(args.audit)
    prototype_report = _load_json(args.prototype_report)
    isolated = _load_json(args.isolated)
    baseline_real = _load_json(args.baseline_real)
    baseline_ranking = _load_json(args.baseline_ranking)

    design = build_design(
        audit=audit,
        prototype_report=prototype_report,
        isolated=isolated,
        baseline_real=baseline_real,
        baseline_ranking=baseline_ranking,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_attention_gating_design.json").write_text(
        json.dumps(design, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_attention_gating_design.md").write_text(
        render_markdown(design),
        encoding="utf-8",
    )
    return 0


def build_design(
    *,
    audit: dict[str, Any],
    prototype_report: dict[str, Any],
    isolated: dict[str, Any],
    baseline_real: dict[str, Any],
    baseline_ranking: dict[str, Any],
) -> dict[str, Any]:
    recurring_prior = isolated.get("recurring_noise_prior", {})
    baseline_summary = _baseline_failure_summary(audit, prototype_report, baseline_real, baseline_ranking)
    per_case = []
    all_new_noise: list[dict[str, Any]] = []
    attention_classes: Counter[str] = Counter()
    query_overlap_counter: Counter[str] = Counter()
    high_risk_hits: Counter[str] = Counter()

    for case in audit.get("per_case", []):
        case_noise = []
        for detail in case.get("newly_used_details", []):
            if detail.get("classification") != "Noise":
                continue
            concept_id = detail["concept_id"]
            overlap = detail.get("query_overlap", [])
            attention_class = detail.get("attention_classification", "Unknown")
            attention_classes[attention_class] += 1
            query_overlap_counter.update(overlap)
            if case["case"] in HIGH_RISK_CASES:
                high_risk_hits[case["case"]] += 1
            record = {
                "case": case["case"],
                "category": case.get("category"),
                "concept_id": concept_id,
                "attention_classification": attention_class,
                "attention_score": detail.get("attention_score"),
                "activation_rank": detail.get("activation_rank"),
                "activation_score": detail.get("activation_score"),
                "query_overlap": overlap,
                "specific_overlap_count": len(overlap),
                "generic_terms": detail.get("generic_terms", []),
                "reasoned": bool(detail.get("reasoned")),
                "planned": bool(detail.get("planned")),
                "responded": bool(detail.get("responded")),
                "entered_activation_top10": concept_id in set(case.get("entered_activation_top10", [])),
                "recurrence_prior": recurring_prior.get(concept_id, {}),
                "recurrence_risk": concept_id in recurring_prior,
                "weak_specificity": _is_weak_specificity(overlap),
                "high_risk_case": case["case"] in HIGH_RISK_CASES,
            }
            case_noise.append(record)
            all_new_noise.append(record)
        per_case.append(
            {
                "case": case["case"],
                "category": case.get("category"),
                "high_risk_case": case["case"] in HIGH_RISK_CASES,
                "noise_used_delta": case.get("noise_used_delta", 0),
                "attention_precision_delta": case.get("attention_precision_delta", 0),
                "reasoning_drift_before": case.get("reasoning_drift_before"),
                "reasoning_drift_after": case.get("reasoning_drift_after"),
                "newly_used_noisy_concepts": case_noise,
            }
        )

    strategy_evaluations = _evaluate_strategies(all_new_noise, audit)
    recommendation = _recommend_strategy(strategy_evaluations, audit)
    return {
        "final_recommendation": recommendation,
        "baseline_failure_summary": baseline_summary,
        "newly_used_noisy_concepts_by_case": per_case,
        "attention_classifications_that_admitted_noise": dict(attention_classes),
        "query_overlap_signals_that_admitted_noise": query_overlap_counter.most_common(),
        "high_risk_cases": {
            case: {
                "newly_used_noise_count": high_risk_hits.get(case, 0),
                "risk_reason": _high_risk_reason(case, per_case),
            }
            for case in sorted(HIGH_RISK_CASES)
        },
        "proposed_gating_strategies": strategy_evaluations,
        "predicted_effects": {
            strategy["name"]: strategy["predicted_effect"]
            for strategy in strategy_evaluations
        },
        "regression_risks": _regression_risks(),
        "recommended_next_simulation": _next_simulation(recommendation),
        "explicitly_rejected_strategies": [
            "global attention threshold loosening",
            "stronger activation recurrence penalty",
            "hard concept blacklist",
            "learning/governance/promotion changes",
            "provider prompt changes",
        ],
        "read_only": True,
        "inputs": {
            "audit_final_decision": audit.get("final_decision"),
            "prototype_final_decision": prototype_report.get("final_decision"),
            "isolated_final_recommendation": isolated.get("final_recommendation"),
        },
    }


def _baseline_failure_summary(
    audit: dict[str, Any],
    prototype_report: dict[str, Any],
    baseline_real: dict[str, Any],
    baseline_ranking: dict[str, Any],
) -> dict[str, Any]:
    summary = audit.get("summary", {})
    if not summary:
        summary = {}
        metrics = prototype_report.get("metrics", {})
        for key, values in metrics.items():
            if isinstance(values, list) and len(values) == 2:
                summary[key] = {"baseline": values[0], "prototype": values[1]}
    return {
        "audit_decision": audit.get("final_decision"),
        "prototype_decision": prototype_report.get("final_decision"),
        "case_count": len(baseline_real.get("cases", [])),
        "baseline_ranking_case_count": len(baseline_ranking.get("cases", [])),
        "metrics": summary,
        "acceptance_criteria_failures": audit.get("acceptance_criteria_failures", {}),
        "interpretation": (
            "The rejected prototype improved activation rank metrics but admitted replacement noise "
            "through attention, increasing reasoning consumption of noisy concepts."
        ),
    }


def _evaluate_strategies(new_noise: list[dict[str, Any]], audit: dict[str, Any]) -> list[dict[str, Any]]:
    total_new_noise = len(new_noise)
    weak_noise = [item for item in new_noise if item["weak_specificity"]]
    supporting_noise = [item for item in new_noise if item["attention_classification"] == "Supporting"]
    core_noise = [item for item in new_noise if item["attention_classification"] == "Core"]
    recurrence_noise = [item for item in new_noise if item["recurrence_risk"]]
    entered_top10_noise = [item for item in new_noise if item["entered_activation_top10"]]
    case_with_noise_increase = len(audit.get("replacement_noise_analysis", {}).get("cases_with_noise_increase", []))

    return [
        {
            "name": "A. Recurrence-risk metadata only",
            "mechanism": "Expose recurrence-risk and weak-specificity flags in attention traces without changing selection.",
            "would_block_new_noise": 0,
            "coverage_of_new_noise": _ratio(0, total_new_noise),
            "predicted_effect": {
                "attention_precision": "unchanged",
                "attention_recall": "unchanged",
                "noise_used_in_reasoning": "unchanged",
                "planning_core_coverage": "unchanged",
                "response_core_coverage": "unchanged",
                "grounding_score": "unchanged",
                "hallucinations": "unchanged",
            },
            "regression_risk": "lowest",
            "assessment": "Useful instrumentation, but insufficient as the next prototype because it cannot reduce noise consumption.",
        },
        {
            "name": "B. Negative attention feature",
            "mechanism": (
                "Subtract a bounded attention penalty when recurrence-risk or replacement-risk combines with weak "
                "specific query overlap."
            ),
            "would_block_new_noise": len(weak_noise),
            "coverage_of_new_noise": _ratio(len(weak_noise), total_new_noise),
            "predicted_effect": {
                "attention_precision": "likely improves",
                "attention_recall": "possible mild regression if expected concepts have sparse overlap",
                "noise_used_in_reasoning": "likely decreases",
                "planning_core_coverage": "watch for under-attending",
                "response_core_coverage": "watch for under-attending",
                "grounding_score": "should remain stable",
                "hallucinations": "should remain 0 if response remains evidence bounded",
            },
            "regression_risk": "medium",
            "assessment": "Good candidate, but it changes selection and could repeat the activation-prototype mistake at the attention layer.",
        },
        {
            "name": "C. Usage gate before reasoning",
            "mechanism": (
                "Allow weak replacement-risk candidates into working memory for observability, but prevent reasoning "
                "from consuming them unless they have stronger support than shallow query overlap."
            ),
            "would_block_new_noise": len(weak_noise),
            "coverage_of_new_noise": _ratio(len(weak_noise), total_new_noise),
            "predicted_effect": {
                "attention_precision": "selection metric may remain similar",
                "attention_recall": "selection recall should remain stable",
                "noise_used_in_reasoning": "likely decreases sharply",
                "planning_core_coverage": "lower risk than selection penalty because core concepts remain visible",
                "response_core_coverage": "lower risk than selection penalty because core concepts remain visible",
                "grounding_score": "should remain stable",
                "hallucinations": "should remain 0 if response still cites used evidence only",
            },
            "regression_risk": "low-medium",
            "assessment": "Best next simulation because the observed failure is not retrieval presence; it is noisy concepts entering reasoning.",
        },
        {
            "name": "D. Supporting-only downgrade",
            "mechanism": "Downgrade weak replacement-risk Core/Supporting concepts to Peripheral before reasoning.",
            "would_block_new_noise": len(supporting_noise) + len(core_noise),
            "coverage_of_new_noise": _ratio(len(supporting_noise) + len(core_noise), total_new_noise),
            "predicted_effect": {
                "attention_precision": "likely improves if Peripheral is not counted as attended",
                "attention_recall": "possible regression on sparse expected concepts",
                "noise_used_in_reasoning": "likely decreases",
                "planning_core_coverage": "watch expected Supporting concepts",
                "response_core_coverage": "watch expected Supporting concepts",
                "grounding_score": "should remain stable",
                "hallucinations": "should remain 0",
            },
            "regression_risk": "medium",
            "assessment": "Potentially equivalent to a hard attention penalty unless carefully limited to usage, not visibility.",
        },
        {
            "name": "E. Case-local replacement-noise guard",
            "mechanism": (
                "For concepts that newly entered activation top-10 after recurring concepts were suppressed, require "
                "stronger query specificity before attention selection."
            ),
            "would_block_new_noise": len(entered_top10_noise),
            "coverage_of_new_noise": _ratio(len(entered_top10_noise), total_new_noise),
            "predicted_effect": {
                "attention_precision": "likely improves in affected cases",
                "attention_recall": "unknown until expected concepts newly entering top-10 are checked",
                "noise_used_in_reasoning": f"likely decreases in up to {case_with_noise_increase} noisy cases",
                "planning_core_coverage": "requires simulation",
                "response_core_coverage": "requires simulation",
                "grounding_score": "should remain stable",
                "hallucinations": "should remain 0",
            },
            "regression_risk": "medium-high",
            "assessment": "Explains the failure but is too coupled to the rejected activation mutation to be the first live design.",
        },
    ]


def _recommend_strategy(strategies: list[dict[str, Any]], audit: dict[str, Any]) -> str:
    noise_delta = audit.get("replacement_noise_analysis", {}).get("total_noise_delta")
    if noise_delta is None:
        baseline = audit.get("summary", {}).get("noise_used_in_reasoning", {}).get("baseline")
        prototype = audit.get("summary", {}).get("noise_used_in_reasoning", {}).get("prototype")
        noise_delta = (prototype - baseline) if isinstance(baseline, (int, float)) and isinstance(prototype, (int, float)) else 0
    if noise_delta > 0:
        return "SIMULATE_REASONING_USAGE_GATE"
    return "RUN_MORE_DIAGNOSTICS"


def _high_risk_reason(case_name: str, per_case: list[dict[str, Any]]) -> str:
    matching = [case for case in per_case if case["case"] == case_name]
    if not matching:
        return "No matching case found in audit output."
    case = matching[0]
    if case["newly_used_noisy_concepts"]:
        return "Rejected prototype admitted newly used noisy concepts in this high-risk runtime case."
    if case["attention_precision_delta"] < 0:
        return "Attention precision regressed even without newly used noise details."
    return "High-risk case named by continuation prompt; no direct newly used noise was observed."


def _is_weak_specificity(overlap: list[str]) -> bool:
    return len(set(overlap)) <= 2


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _regression_risks() -> list[str]:
    return [
        "Over-gating could suppress sparse but valid expected concepts before they influence reasoning.",
        "A negative attention feature could recreate the live-prototype failure if it changes selection without checking downstream use.",
        "Usage gating could preserve attention recall but make planning appear to ignore visible supporting evidence if reports do not distinguish visible from usable.",
        "Hard discard would hide diagnostic evidence and make future activation failures harder to explain.",
        "Query-overlap rules are brittle because broad terms such as risk, evidence, plan, resource, and failure can be legitimate anchors.",
    ]


def _next_simulation(recommendation: str) -> str:
    if recommendation == "SIMULATE_REASONING_USAGE_GATE":
        return (
            "Replay the V1.2/V1.3 contribution traces with a read-only usage gate: recurrence-risk or "
            "replacement-risk plus weak specificity remains visible in working memory but cannot contribute "
            "to reasoning, planning, or response unless stronger evidence support is present."
        )
    if recommendation == "SIMULATE_ATTENTION_NEGATIVE_FEATURE":
        return "Replay a bounded attention-score penalty without changing activation ranking."
    return "Collect more per-concept attention traces before changing any runtime stage."


def render_markdown(design: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Attention-Gating Design",
        "",
        f"Final recommendation: `{design['final_recommendation']}`",
        "",
        "## Baseline Failure Summary",
        "",
        design["baseline_failure_summary"]["interpretation"],
        "",
        "| Metric | Baseline | Rejected Prototype |",
        "| --- | ---: | ---: |",
    ]
    for key, value in design["baseline_failure_summary"]["metrics"].items():
        if isinstance(value, dict) and "baseline" in value and "prototype" in value:
            lines.append(f"| {key} | `{value['baseline']}` | `{value['prototype']}` |")
        elif isinstance(value, list) and len(value) == 2:
            lines.append(f"| {key} | `{value[0]}` | `{value[1]}` |")
    lines.extend(
        [
            "",
            "## Newly Used Noisy Concepts By Case",
            "",
            "| Case | High Risk | Noise Delta | Concept | Attention Class | Attention Score | Query Overlap | Reasoned | Planned | Responded |",
            "| --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for case in design["newly_used_noisy_concepts_by_case"]:
        if not case["newly_used_noisy_concepts"]:
            lines.append(
                f"| {case['case']} | `{case['high_risk_case']}` | `{case['noise_used_delta']}` | none | - | - | - | - | - | - |"
            )
            continue
        for item in case["newly_used_noisy_concepts"]:
            overlap = ", ".join(item["query_overlap"]) or "none"
            lines.append(
                f"| {case['case']} | `{case['high_risk_case']}` | `{case['noise_used_delta']}` | "
                f"`{item['concept_id']}` | `{item['attention_classification']}` | "
                f"`{item['attention_score']}` | {overlap} | `{item['reasoned']}` | "
                f"`{item['planned']}` | `{item['responded']}` |"
            )

    lines.extend(["", "## Attention Classifications That Admitted Noise", ""])
    for classification, count in sorted(design["attention_classifications_that_admitted_noise"].items()):
        lines.append(f"- `{classification}`: `{count}`")
    lines.extend(["", "## Query-Overlap Signals That Admitted Noise", ""])
    if not design["query_overlap_signals_that_admitted_noise"]:
        lines.append("- none")
    for term, count in design["query_overlap_signals_that_admitted_noise"][:20]:
        lines.append(f"- `{term}`: `{count}`")

    lines.extend(["", "## Proposed Gating Strategies", ""])
    for strategy in design["proposed_gating_strategies"]:
        lines.extend(
            [
                f"### {strategy['name']}",
                "",
                strategy["mechanism"],
                "",
                f"- would block newly used noise: `{strategy['would_block_new_noise']}`",
                f"- coverage of newly used noise: `{strategy['coverage_of_new_noise']}`",
                f"- regression risk: `{strategy['regression_risk']}`",
                f"- assessment: {strategy['assessment']}",
                "",
            ]
        )

    lines.extend(["## Predicted Effects", ""])
    for name, effects in design["predicted_effects"].items():
        lines.append(f"### {name}")
        for key, value in effects.items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")

    lines.extend(["## Regression Risks", ""])
    lines.extend(f"- {risk}" for risk in design["regression_risks"])
    lines.extend(
        [
            "",
            "## Recommended Next Simulation",
            "",
            design["recommended_next_simulation"],
            "",
            "## Explicitly Rejected Strategies",
            "",
        ]
    )
    lines.extend(f"- {strategy}" for strategy in design["explicitly_rejected_strategies"])
    lines.extend(["", f"`{design['final_recommendation']}`", ""])
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input report: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
