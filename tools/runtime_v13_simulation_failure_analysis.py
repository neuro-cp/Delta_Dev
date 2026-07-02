from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.runtime_v13_scoring_simulation import GENERIC_TOKENS, STOPWORDS


FOCUS_CASES = {
    "causal_industrial_failure",
    "policy_audit_conflict",
    "resource_allocation_shelters",
    "risk_uncertainty_planning",
    "multi_step_failure_revision",
    "logistics_proxy_planning",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze why Runtime V1.3 scoring simulation failed.")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("reports/runtime_v12_activation_ranking_diagnostic.json"),
    )
    parser.add_argument(
        "--simulation",
        type=Path,
        default=Path("reports/runtime_v13_scoring_simulation.json"),
    )
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    baseline = _load_json(args.baseline)
    simulation = _load_json(args.simulation)
    analysis = _analyze(baseline=baseline, simulation=simulation)

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_simulation_failure_analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_simulation_failure_analysis.md").write_text(
        _markdown(analysis),
        encoding="utf-8",
    )
    return 0


def _analyze(*, baseline: dict[str, Any], simulation: dict[str, Any]) -> dict[str, Any]:
    baseline_cases = {case["case"]: case for case in baseline["cases"]}
    simulation_cases = {case["case"]: case for case in simulation["cases"]}
    worsened = _worsened_expected_concepts(baseline_cases, simulation_cases)
    recurring_noise = _recurring_noise_analysis(baseline_cases, simulation)
    comparison = _case_comparison(baseline_cases, simulation_cases)
    sparse = _sparse_analysis(baseline_cases, simulation_cases)
    next_direction = _next_direction(worsened=worsened, recurring_noise=recurring_noise, sparse=sparse, comparison=comparison)
    return {
        "source_reports": {
            "baseline": "reports/runtime_v12_activation_ranking_diagnostic.json",
            "simulation": "reports/runtime_v13_scoring_simulation.json",
        },
        "final_decision_from_simulation": simulation["final_decision"],
        "failed_metrics": simulation["aggregate"],
        "worsened_expected_concepts": worsened,
        "recurring_noise_analysis": recurring_noise,
        "improved_vs_worsened_cases": comparison,
        "sparse_behavior": sparse,
        "next_formula_assessment": next_direction,
        "conclusion": {
            "Root cause of failed formula": (
                "The formula treated generic task-domain terms as globally weak signals. "
                "In the Phase A corpus, words such as resource, risk, plan, failure, and evidence "
                "are often the actual domain anchors for valid concepts, so blunt dampening punished "
                "expected concepts while allowing other recurring noisy concepts to dominate."
            ),
            "Recommended next experiment": (
                "Do not revise live activation yet. Run a separate simulation for recurring-noise suppression "
                "and a separate sparse-abstention simulation. Keep attention rescue as a distinct experiment "
                "for attention-primary cases."
            ),
            "Experiments explicitly rejected": [
                "stronger global generic-token dampening",
                "live activation scoring changes based on the failed formula",
                "loosening attention thresholds to compensate for activation noise",
                "learning/governance/promotion changes",
            ],
            "Metrics to monitor": [
                "expected_outside_top10",
                "expected_outside_top20",
                "mean_expected_rank",
                "mean_noise_above_expected",
                "expected top-10 concepts pushed out",
                "sparse top activation score",
                "noise_used_in_reasoning",
                "grounding_score",
                "hallucinations",
            ],
            "Whether to keep, revise, or delete tools/runtime_v13_scoring_simulation.py": (
                "Keep it as a failed prototype artifact and baseline simulation harness. Revise by adding "
                "alternative named formulas rather than overwriting this result."
            ),
        },
    }


def _worsened_expected_concepts(
    baseline_cases: dict[str, dict[str, Any]],
    simulation_cases: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_name, sim_case in simulation_cases.items():
        base_case = baseline_cases[case_name]
        baseline_by_id = {item["concept_id"]: item for item in base_case["top_50"]}
        for concept in sim_case["expected_concepts"]:
            if concept["rank_delta"] is None or concept["rank_delta"] >= 0:
                continue
            base_item = baseline_by_id.get(concept["concept_id"], {})
            specific = _specific_terms(base_item)
            generic = set(base_item.get("generic_query_terms_matched", []))
            rows.append(
                {
                    "case": case_name,
                    "concept_id": concept["concept_id"],
                    "original_rank": concept["original_rank"],
                    "simulated_rank": concept["simulated_rank"],
                    "rank_delta": concept["rank_delta"],
                    "original_score": concept["original_score"],
                    "simulated_score": concept["simulated_score"],
                    "generic_terms_matched": sorted(generic),
                    "specific_terms_matched": sorted(specific),
                    "concept_overlap": base_item.get("query_concept_overlap", []),
                    "definition_overlap": base_item.get("query_definition_overlap", []),
                    "mostly_generic_overlap": _mostly_generic(base_item),
                    "domain_relevant_despite_generic_terms": _domain_relevant(base_item, specific, generic),
                    "likely_failure_reason": _expected_failure_reason(base_item, specific, generic),
                    "concept": base_item.get("concept", ""),
                }
            )
    rows.sort(key=lambda row: row["rank_delta"])
    return rows


def _recurring_noise_analysis(
    baseline_cases: dict[str, dict[str, Any]],
    simulation: dict[str, Any],
) -> list[dict[str, Any]]:
    before = dict(simulation["aggregate"]["recurring_noise_before"])
    after = dict(simulation["aggregate"]["recurring_noise_after"])
    all_noise = sorted(set(before) | set(after), key=lambda concept_id: (after.get(concept_id, 0), before.get(concept_id, 0)), reverse=True)
    rows: list[dict[str, Any]] = []
    for concept_id in all_noise:
        appearances = _noise_appearances(concept_id, baseline_cases)
        generic_terms = Counter(term for item in appearances for term in item.get("generic_query_terms_matched", []))
        specific_terms = Counter(term for item in appearances for term in _specific_terms(item))
        components = _score_component_summary(appearances)
        rows.append(
            {
                "concept_id": concept_id,
                "before_count": before.get(concept_id, 0),
                "after_count": after.get(concept_id, 0),
                "count_delta": after.get(concept_id, 0) - before.get(concept_id, 0),
                "generic_terms": generic_terms.most_common(),
                "specific_terms": specific_terms.most_common(),
                "average_activation_score": components["average_activation_score"],
                "average_confidence": components["average_confidence"],
                "average_promotion_score": components["average_promotion_score"],
                "average_centrality": components["average_centrality"],
                "average_evidence_support": components["average_evidence_support"],
                "likely_reason_it_survived_or_gained": _noise_reason(appearances, generic_terms, specific_terms, components),
                "example_concept": appearances[0].get("concept", "") if appearances else "",
            }
        )
    return rows[:15]


def _case_comparison(
    baseline_cases: dict[str, dict[str, Any]],
    simulation_cases: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_name in sorted(FOCUS_CASES):
        if case_name not in simulation_cases:
            continue
        sim_case = simulation_cases[case_name]
        base_case = baseline_cases[case_name]
        improved = len(sim_case["expected_rank_improvements"])
        worsened = len(sim_case["expected_rank_worsening"])
        rows.append(
            {
                "case": case_name,
                "baseline_diagnosis": base_case["diagnosis"],
                "expected_improved": improved,
                "expected_worsened": worsened,
                "expected_outside_top10_before": base_case["expected_outside_top_10"],
                "expected_pruned_by_attention_before": base_case["expected_pruned_by_attention"],
                "interpretation": _case_interpretation(base_case["diagnosis"], improved, worsened),
            }
        )
    return rows


def _sparse_analysis(
    baseline_cases: dict[str, dict[str, Any]],
    simulation_cases: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_name, sim_case in simulation_cases.items():
        if not sim_case["sparse_expected"]:
            continue
        base_case = baseline_cases[case_name]
        top_before = base_case["top_50"][0] if base_case["top_50"] else {}
        top_after = sim_case["top_10_after"][0] if sim_case["top_10_after"] else {}
        rows.append(
            {
                "case": case_name,
                "original_sparse_top_score": sim_case["original_sparse_top_score"],
                "simulated_sparse_top_score": sim_case["simulated_sparse_top_score"],
                "sparse_behavior_ok": sim_case["sparse_behavior_ok"],
                "top_before_overlap": top_before.get("query_combined_overlap", []),
                "top_before_generic_terms": top_before.get("generic_query_terms_matched", []),
                "top_after_concept_id": top_after.get("concept_id"),
                "why": _sparse_reason(sim_case, top_before),
                "separate_sparse_gate_recommended": True,
            }
        )
    return rows


def _next_direction(
    *,
    worsened: list[dict[str, Any]],
    recurring_noise: list[dict[str, Any]],
    sparse: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
) -> dict[str, Any]:
    attention_cases = [row["case"] for row in comparison if "attention" in row["baseline_diagnosis"]]
    high_noise = [row["concept_id"] for row in recurring_noise if row["count_delta"] > 0]
    return {
        "A_revised_generic_token_dampening": "reject_for_now",
        "B_domain_aware_generic_token_dampening": "possible_but_not_first",
        "C_query_specific_rarity_weighting": "possible_with_care",
        "D_duplicate_or_noisy_concept_suppression": "recommended_next_activation_simulation",
        "E_separate_sparse_abstention_gate": "recommended_separate_simulation",
        "F_attention_rescue_instead_of_activation_scoring": "recommended_for_attention_primary_cases",
        "rationale": [
            f"{len(worsened)} expected concepts worsened under blunt generic dampening.",
            f"{len(high_noise)} recurring noisy concepts became more dominant after simulation.",
            f"{len(sparse)} sparse cases behave structurally differently and should not be folded into normal activation scoring.",
            f"attention-primary cases remain distinct: {', '.join(attention_cases) if attention_cases else 'none'}",
        ],
    }


def _noise_appearances(concept_id: str, baseline_cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    appearances = []
    for case in baseline_cases.values():
        for item in case["top_50"]:
            if item["concept_id"] == concept_id:
                appearances.append(item)
    return appearances


def _score_component_summary(items: list[dict[str, Any]]) -> dict[str, float]:
    if not items:
        return {
            "average_activation_score": 0.0,
            "average_confidence": 0.0,
            "average_promotion_score": 0.0,
            "average_centrality": 0.0,
            "average_evidence_support": 0.0,
        }
    return {
        "average_activation_score": round(sum(float(item.get("activation_score", 0.0)) for item in items) / len(items), 4),
        "average_confidence": round(sum(float(item.get("confidence", 0.0)) for item in items) / len(items), 4),
        "average_promotion_score": round(sum(float(item.get("promotion_score", 0.0)) for item in items) / len(items), 4),
        "average_centrality": round(sum(float(item.get("projected_centrality", 0.0)) for item in items) / len(items), 4),
        "average_evidence_support": round(sum(float(item.get("evidence_support", 0.0)) for item in items) / len(items), 4),
    }


def _specific_terms(item: dict[str, Any]) -> set[str]:
    return {
        str(term).lower()
        for term in item.get("query_combined_overlap", [])
        if str(term).lower() not in GENERIC_TOKENS
        and str(term).lower() not in STOPWORDS
        and len(str(term)) >= 3
    }


def _mostly_generic(item: dict[str, Any]) -> bool:
    generic = set(item.get("generic_query_terms_matched", []))
    specific = _specific_terms(item)
    return bool(generic) and len(generic) >= len(specific)


def _domain_relevant(item: dict[str, Any], specific: set[str], generic: set[str]) -> bool:
    if item.get("role") == "expected":
        return True
    return bool(specific) and bool(generic)


def _expected_failure_reason(item: dict[str, Any], specific: set[str], generic: set[str]) -> str:
    if generic and not specific:
        return "expected concept depended mostly on domain-generic terms and was over-penalized"
    if generic and specific:
        return "expected concept combined generic domain anchors with specific terms, but the generic penalty dominated"
    if not generic and specific:
        return "expected concept was outranked by other concepts after unrelated score shifts"
    return "expected concept lacked measurable overlap in the saved diagnostic fields"


def _noise_reason(
    appearances: list[dict[str, Any]],
    generic_terms: Counter[str],
    specific_terms: Counter[str],
    components: dict[str, float],
) -> str:
    if not appearances:
        return "not present in top-50 appearances"
    if specific_terms:
        return "survived through accidental or broad non-generic overlap: " + ", ".join(term for term, _ in specific_terms.most_common(4))
    if components["average_confidence"] >= 0.8 or components["average_promotion_score"] >= 0.55:
        return "survived through high confidence or promotion score after other candidates were penalized"
    if generic_terms:
        return "survived because generic-token dampening was not selective enough across all noisy concepts"
    return "survived due to residual base activation score and relative movement of other candidates"


def _case_interpretation(diagnosis: str, improved: int, worsened: int) -> str:
    if worsened > improved:
        return "formula harmed this case; do not use this scoring direction for it"
    if improved > worsened:
        return "formula helped some concepts, but verify gains are not isolated or label-dependent"
    if "attention" in diagnosis:
        return "activation formula is not enough; attention remains the likely bottleneck"
    return "no clear rank movement"


def _sparse_reason(sim_case: dict[str, Any], top_before: dict[str, Any]) -> str:
    if sim_case["sparse_behavior_ok"]:
        return "the top candidate had only weak stopword/generic overlap and was sufficiently penalized below the abstention threshold"
    return (
        "the top candidate remained above the abstention threshold despite weak overlap; sparse behavior needs a separate "
        "abstention gate instead of being folded into normal activation scoring"
    )


def _markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Simulation Failure Analysis",
        "",
        f"- simulation decision: `{analysis['final_decision_from_simulation']}`",
        "",
        "## Failed Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in analysis["failed_metrics"].items():
        if key.startswith("recurring") or key == "expected_concepts_worsened_out_of_top10":
            continue
        lines.append(f"| {key} | `{value}` |")

    lines.extend(["", "## Worsened Expected Concepts", ""])
    if not analysis["worsened_expected_concepts"]:
        lines.append("- none")
    for item in analysis["worsened_expected_concepts"]:
        lines.extend(
            [
                f"### {item['case']} / {item['concept_id']}",
                "",
                f"- rank: `{item['original_rank']}` -> `{item['simulated_rank']}`",
                f"- score: `{item['original_score']}` -> `{item['simulated_score']}`",
                f"- generic terms: `{', '.join(item['generic_terms_matched']) or 'none'}`",
                f"- specific terms: `{', '.join(item['specific_terms_matched']) or 'none'}`",
                f"- mostly generic overlap: `{item['mostly_generic_overlap']}`",
                f"- domain relevant despite generic terms: `{item['domain_relevant_despite_generic_terms']}`",
                f"- likely reason: {item['likely_failure_reason']}",
                "",
            ]
        )

    lines.extend(["", "## Recurring Noise That Gained Or Survived", "", "| Concept | Before | After | Reason |", "| --- | ---: | ---: | --- |"])
    for item in analysis["recurring_noise_analysis"]:
        lines.append(
            f"| `{item['concept_id']}` | `{item['before_count']}` | `{item['after_count']}` | {item['likely_reason_it_survived_or_gained']} |"
        )

    lines.extend(["", "## Improved Vs Worsened Cases", "", "| Case | Diagnosis | Improved | Worsened | Interpretation |", "| --- | --- | ---: | ---: | --- |"])
    for item in analysis["improved_vs_worsened_cases"]:
        lines.append(
            f"| {item['case']} | `{item['baseline_diagnosis']}` | `{item['expected_improved']}` | `{item['expected_worsened']}` | {item['interpretation']} |"
        )

    lines.extend(["", "## Sparse Behavior", ""])
    for item in analysis["sparse_behavior"]:
        lines.extend(
            [
                f"### {item['case']}",
                "",
                f"- top score: `{item['original_sparse_top_score']}` -> `{item['simulated_sparse_top_score']}`",
                f"- sparse behavior ok: `{item['sparse_behavior_ok']}`",
                f"- explanation: {item['why']}",
                f"- separate sparse gate recommended: `{item['separate_sparse_gate_recommended']}`",
                "",
            ]
        )

    lines.extend(["", "## Next Formula Assessment", ""])
    for key, value in analysis["next_formula_assessment"].items():
        if key == "rationale":
            continue
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "Rationale:"])
    lines.extend(f"- {item}" for item in analysis["next_formula_assessment"]["rationale"])

    conclusion = analysis["conclusion"]
    for heading in [
        "Root cause of failed formula",
        "Recommended next experiment",
        "Experiments explicitly rejected",
        "Metrics to monitor",
        "Whether to keep, revise, or delete tools/runtime_v13_scoring_simulation.py",
    ]:
        lines.extend(["", f"## {heading}", ""])
        value = conclusion[heading]
        if isinstance(value, list):
            lines.extend(f"- {item}" for item in value)
        else:
            lines.append(value)
    lines.append("")
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input report: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
