from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BROAD_TERMS = {
    "account",
    "analyze",
    "change",
    "changes",
    "concept",
    "evidence",
    "failure",
    "finding",
    "handle",
    "identify",
    "plan",
    "policy",
    "question",
    "report",
    "reports",
    "resource",
    "resources",
    "risk",
    "should",
    "team",
    "uncertainty",
}

TECHNICAL_ANCHORS = {
    "atmospheric",
    "contradictory",
    "emergency",
    "gps",
    "industrial",
    "maintenance",
    "multipath",
    "permit",
    "shelter",
    "shelters",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit remaining Runtime V1.3 noisy reasoning cases.")
    parser.add_argument("--baseline-real", type=Path, required=True)
    parser.add_argument("--baseline-ranking", type=Path, required=True)
    parser.add_argument("--refined-real", type=Path, required=True)
    parser.add_argument("--refined-ranking", type=Path, required=True)
    parser.add_argument("--resolution-suite", type=Path, required=True)
    parser.add_argument("--evidence-audit", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--output-stem", default="runtime_v13_remaining_noise_audit")
    args = parser.parse_args()

    baseline_real = _load(args.baseline_real)
    baseline_ranking = _load(args.baseline_ranking)
    refined_real = _load(args.refined_real)
    refined_ranking = _load(args.refined_ranking)
    resolution_suite = _load(args.resolution_suite)
    evidence_audit = _load(args.evidence_audit)

    audit = build_audit(
        baseline_real=baseline_real,
        baseline_ranking=baseline_ranking,
        refined_real=refined_real,
        refined_ranking=refined_ranking,
        resolution_suite=resolution_suite,
        evidence_audit=evidence_audit,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / f"{args.output_stem}.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / f"{args.output_stem}.md").write_text(
        _markdown(audit),
        encoding="utf-8",
    )
    return 0


def build_audit(
    *,
    baseline_real: dict[str, Any],
    baseline_ranking: dict[str, Any],
    refined_real: dict[str, Any],
    refined_ranking: dict[str, Any],
    resolution_suite: dict[str, Any],
    evidence_audit: dict[str, Any],
) -> dict[str, Any]:
    baseline_cases = {case["name"]: case for case in baseline_real.get("cases", [])}
    refined_cases = {case["name"]: case for case in refined_real.get("cases", [])}
    baseline_rank_cases = {case["case"]: case for case in baseline_ranking.get("cases", [])}
    refined_rank_cases = {case["case"]: case for case in refined_ranking.get("cases", [])}

    remaining_records: list[dict[str, Any]] = []
    successful_removals: list[dict[str, Any]] = []
    unchanged_noise: list[dict[str, Any]] = []
    at_risk_expected: list[dict[str, Any]] = []
    per_case: list[dict[str, Any]] = []

    for case_name, refined_case in refined_cases.items():
        baseline_case = baseline_cases.get(case_name, {})
        baseline_noise = _noise_reasoned(baseline_case)
        refined_noise = _noise_reasoned(refined_case)
        baseline_noise_ids = {item["concept_id"] for item in baseline_noise}
        refined_noise_ids = {item["concept_id"] for item in refined_noise}
        removed_ids = sorted(baseline_noise_ids - refined_noise_ids)
        unchanged_ids = sorted(baseline_noise_ids & refined_noise_ids)

        refined_rank = refined_rank_cases.get(case_name, {})
        baseline_rank = baseline_rank_cases.get(case_name, {})
        refined_top = _top_index(refined_rank)
        baseline_top = _top_index(baseline_rank)
        expected = _expected_records(refined_rank)

        for noise in refined_noise:
            record = _remaining_record(
                case=refined_case,
                contribution=noise,
                diagnostic=refined_top.get(noise["concept_id"], {}),
                expected=expected,
            )
            remaining_records.append(record)

        for concept_id in removed_ids:
            successful_removals.append(
                _removal_record(
                    case=refined_case,
                    concept_id=concept_id,
                    baseline_contribution=_contribution_by_id(baseline_case, concept_id),
                    baseline_diagnostic=baseline_top.get(concept_id, {}),
                    refined_contribution=_contribution_by_id(refined_case, concept_id),
                    refined_diagnostic=refined_top.get(concept_id, {}),
                )
            )

        for concept_id in unchanged_ids:
            unchanged_noise.append(
                {
                    "case": case_name,
                    "concept_id": concept_id,
                    "concept": refined_top.get(concept_id, {}).get("concept"),
                    "attention_classification": _contribution_by_id(refined_case, concept_id).get(
                        "attention_classification"
                    ),
                    "attention_score": _contribution_by_id(refined_case, concept_id).get("attention_score"),
                    "rank": _rank(refined_rank, concept_id),
                    "activation_score": refined_top.get(concept_id, {}).get("activation_score"),
                }
            )

        for item in expected:
            contribution = _contribution_by_id(refined_case, item["concept_id"])
            if not contribution.get("attended", False) or not contribution.get("reasoned", False):
                at_risk_expected.append(
                    {
                        "case": case_name,
                        "concept_id": item["concept_id"],
                        "concept": item.get("concept"),
                        "rank": _rank(refined_rank, item["concept_id"]),
                        "activation_score": item.get("activation_score"),
                        "attention_classification": contribution.get("attention_classification"),
                        "attention_score": contribution.get("attention_score"),
                        "attended": contribution.get("attended", False),
                        "reasoned": contribution.get("reasoned", False),
                        "reason": "expected concept did not fully pass attention/reasoning",
                    }
                )

        per_case.append(
            {
                "case": case_name,
                "category": refined_case.get("category"),
                "question": refined_case.get("question"),
                "baseline_noise_used": len(baseline_noise),
                "refined_noise_used": len(refined_noise),
                "removed_noise": len(removed_ids),
                "unchanged_noise": len(unchanged_ids),
                "expected_concepts": len(expected),
                "expected_at_risk": sum(1 for item in at_risk_expected if item["case"] == case_name),
                "dominant_remaining_causes": _dominant_causes(
                    [record for record in remaining_records if record["case"] == case_name]
                ),
            }
        )

    cause_counts = Counter()
    for record in remaining_records:
        cause_counts.update(record["taxonomy"])
    pass_reason_counts = Counter(record["pass_reason"] for record in remaining_records)
    case_counts = Counter(record["case"] for record in remaining_records)

    recommendation = _recommendation(cause_counts, remaining_records, at_risk_expected)

    baseline_metrics = _metrics(baseline_real, baseline_ranking, evidence_audit, "baseline_reference")
    refined_metrics = _metrics(refined_real, refined_ranking, evidence_audit, "citation_context_usage_gate")
    if "variants" in resolution_suite:
        selected = next(
            (variant for variant in resolution_suite["variants"] if variant.get("name") == "citation_context_usage_gate"),
            None,
        )
        if selected:
            for key, value in selected.get("metrics", {}).items():
                refined_metrics.setdefault(key, value)

    return {
        "summary": {
            "remaining_noisy_reasoning_concepts": len(remaining_records),
            "cases_with_remaining_noise": len(case_counts),
            "successful_noise_removals": len(successful_removals),
            "unchanged_noise": len(unchanged_noise),
            "expected_or_useful_at_risk": len(at_risk_expected),
            "dominant_failure_modes": dict(cause_counts.most_common()),
            "pass_reason_counts": dict(pass_reason_counts.most_common()),
            "final_recommendation": recommendation,
        },
        "baseline_metrics": baseline_metrics,
        "refined_metrics": refined_metrics,
        "per_case": per_case,
        "remaining_noisy_reasoning_concepts": remaining_records,
        "successful_noise_removals": successful_removals,
        "unchanged_noise": unchanged_noise,
        "expected_or_useful_concepts_at_risk": at_risk_expected,
        "explicitly_rejected_experiments": [
            "stronger_activation_recurrence_by_default",
            "hard_concept_blacklist",
            "global_attention_threshold_loosening",
            "learning_governance_or_promotion_changes",
            "provider_prompt_changes",
        ],
        "recommended_next_experiment": recommendation,
    }


def _remaining_record(
    *,
    case: dict[str, Any],
    contribution: dict[str, Any],
    diagnostic: dict[str, Any],
    expected: list[dict[str, Any]],
) -> dict[str, Any]:
    overlap = sorted(set(diagnostic.get("query_combined_overlap", [])))
    generic = sorted(set(diagnostic.get("generic_query_terms_matched", [])))
    anchors = sorted(set(overlap) & TECHNICAL_ANCHORS)
    specific = sorted(set(overlap) - set(generic) - BROAD_TERMS - STOPWORDS)
    expected_comparison = _compare_to_expected(diagnostic, expected)
    taxonomy = _taxonomy(contribution, diagnostic, overlap, generic, anchors, specific, expected_comparison)
    return {
        "case": case.get("name"),
        "category": case.get("category"),
        "question": case.get("question"),
        "concept_id": contribution.get("concept_id"),
        "concept": diagnostic.get("concept"),
        "definition": diagnostic.get("definition"),
        "activation_rank": diagnostic.get("_rank"),
        "activation_score": diagnostic.get("activation_score"),
        "attention_classification": contribution.get("attention_classification"),
        "attention_score": contribution.get("attention_score"),
        "reasoned": contribution.get("reasoned"),
        "planned": contribution.get("planned"),
        "responded": contribution.get("responded"),
        "query_overlap": overlap,
        "specific_overlap": specific,
        "generic_overlap": generic,
        "domain_anchor_overlap": anchors,
        "expanded_jaccard_to_question": diagnostic.get("expanded_jaccard_to_question"),
        "evidence_support": diagnostic.get("evidence_support"),
        "confidence": diagnostic.get("confidence"),
        "promotion_score": diagnostic.get("promotion_score"),
        "projected_centrality": diagnostic.get("projected_centrality"),
        "why_refined_gate_allowed_it": _pass_reason(contribution, diagnostic, specific, anchors, generic),
        "pass_reason": _pass_reason(contribution, diagnostic, specific, anchors, generic)["summary"],
        "comparison_to_expected": expected_comparison,
        "taxonomy": taxonomy,
    }


def _removal_record(
    *,
    case: dict[str, Any],
    concept_id: str,
    baseline_contribution: dict[str, Any],
    baseline_diagnostic: dict[str, Any],
    refined_contribution: dict[str, Any],
    refined_diagnostic: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case": case.get("name"),
        "concept_id": concept_id,
        "concept": refined_diagnostic.get("concept") or baseline_diagnostic.get("concept"),
        "baseline_attention_classification": baseline_contribution.get("attention_classification"),
        "baseline_attention_score": baseline_contribution.get("attention_score"),
        "baseline_rank": baseline_diagnostic.get("_rank"),
        "baseline_activation_score": baseline_diagnostic.get("activation_score"),
        "refined_attention_classification": refined_contribution.get("attention_classification"),
        "refined_attention_score": refined_contribution.get("attention_score"),
        "refined_reasoned": refined_contribution.get("reasoned", False),
        "refined_rank": refined_diagnostic.get("_rank"),
        "refined_activation_score": refined_diagnostic.get("activation_score"),
    }


def _taxonomy(
    contribution: dict[str, Any],
    diagnostic: dict[str, Any],
    overlap: list[str],
    generic: list[str],
    anchors: list[str],
    specific: list[str],
    expected_comparison: dict[str, Any],
) -> list[str]:
    causes: list[str] = []
    attention_score = float(contribution.get("attention_score") or 0.0)
    evidence_support = float(diagnostic.get("evidence_support") or 0.0)
    concept = str(diagnostic.get("concept") or "")
    concept_tokens = set(_tokens(concept))

    if evidence_support >= 0.9 and len(specific) <= 2:
        causes.append("insufficient_query_specific_evidence_modeling")
    if contribution.get("attention_classification") in {"Core", "Supporting"}:
        causes.append("attention_misclassification")
    if len(overlap) <= 2 and evidence_support >= 0.9:
        causes.append("reasoning_gate_override_too_permissive")
    if len(generic) >= 2 or len(concept_tokens & BROAD_TERMS) >= 2:
        causes.append("overly_broad_concept")
    if anchors or expected_comparison.get("nearest_expected_shared_terms", 0) >= 2:
        causes.append("role_ambiguity_between_useful_neighbor_and_noise")
    if expected_comparison.get("nearest_expected_shared_terms", 0) >= 3 and attention_score >= 0.6:
        causes.append("evaluator_or_benchmark_label_issue")
    if len(specific) == 0 and not anchors:
        causes.append("missing_concept_role_metadata")
    return causes or ["run_more_diagnostics"]


def _pass_reason(
    contribution: dict[str, Any],
    diagnostic: dict[str, Any],
    specific: list[str],
    anchors: list[str],
    generic: list[str],
) -> dict[str, Any]:
    attention = contribution.get("attention_classification")
    attention_score = float(contribution.get("attention_score") or 0.0)
    evidence_support = float(diagnostic.get("evidence_support") or 0.0)
    if evidence_support >= 0.9 and (specific or anchors) and attention_score >= 0.4:
        summary = "high_corpus_support_plus_context_overlap"
    elif attention == "Core":
        summary = "core_attention_classification"
    elif attention == "Supporting" and generic:
        summary = "supporting_attention_plus_generic_overlap"
    elif evidence_support >= 0.9:
        summary = "corpus_support_override"
    else:
        summary = "attention_allowed_without_clear_query_support"
    return {
        "summary": summary,
        "attention_classification": attention,
        "attention_score": attention_score,
        "evidence_support": evidence_support,
        "specific_overlap": specific,
        "domain_anchor_overlap": anchors,
        "generic_overlap": generic,
        "note": "Inferred from archived diagnostics; the audit does not execute or mutate runtime code.",
    }


def _compare_to_expected(diagnostic: dict[str, Any], expected: list[dict[str, Any]]) -> dict[str, Any]:
    concept_tokens = set(_tokens(diagnostic.get("concept") or ""))
    comparisons = []
    for item in expected:
        expected_tokens = set(_tokens(item.get("concept") or item.get("definition") or ""))
        shared = sorted((concept_tokens & expected_tokens) - STOPWORDS)
        union = concept_tokens | expected_tokens
        comparisons.append(
            {
                "concept_id": item.get("concept_id"),
                "shared_terms": shared[:20],
                "shared_term_count": len(shared),
                "jaccard": round(len(concept_tokens & expected_tokens) / len(union), 4) if union else 0.0,
            }
        )
    comparisons.sort(key=lambda item: (item["shared_term_count"], item["jaccard"]), reverse=True)
    nearest = comparisons[0] if comparisons else {}
    return {
        "nearest_expected_concept_id": nearest.get("concept_id"),
        "nearest_expected_shared_terms": nearest.get("shared_term_count", 0),
        "nearest_expected_jaccard": nearest.get("jaccard", 0.0),
        "nearest_expected_shared_term_sample": nearest.get("shared_terms", []),
    }


def _recommendation(cause_counts: Counter[str], remaining: list[dict[str, Any]], at_risk_expected: list[dict[str, Any]]) -> str:
    if not remaining:
        return "RUN_MORE_DIAGNOSTICS"
    if cause_counts["insufficient_query_specific_evidence_modeling"] >= max(3, len(remaining) // 2):
        return "PROCEED_QUERY_SPECIFIC_EVIDENCE_MODELING"
    if cause_counts["role_ambiguity_between_useful_neighbor_and_noise"] >= max(3, len(remaining) // 2):
        return "PROCEED_ROLE_AWARE_CONCEPT_CLASSIFICATION"
    if cause_counts["attention_misclassification"] >= max(4, len(remaining) // 2) and not at_risk_expected:
        return "PROCEED_ATTENTION_CLASSIFICATION_REFINEMENT"
    if sum(1 for record in remaining if record.get("planned") or record.get("responded")) >= max(4, len(remaining) // 2):
        return "PROCEED_PLANNING_RESPONSE_CITATION_REFINEMENT"
    return "RUN_MORE_DIAGNOSTICS"


def _metrics(real: dict[str, Any], ranking: dict[str, Any], evidence_audit: dict[str, Any], variant_name: str) -> dict[str, Any]:
    aggregate = dict(real.get("aggregate", {}))
    ranking_aggregate = ranking.get("aggregate", {})
    return {
        "noise_used_in_reasoning": aggregate.get("noise_used_in_reasoning"),
        "attention_precision": aggregate.get("attention_precision"),
        "attention_recall": aggregate.get("attention_recall"),
        "retrieval_recall": aggregate.get("retrieval_recall"),
        "retrieval_precision": aggregate.get("retrieval_precision"),
        "grounding_score": aggregate.get("grounding_score"),
        "hallucinations": aggregate.get("hallucinations"),
        "confidence_calibration": aggregate.get("confidence_calibration"),
        "planning_score": aggregate.get("planning_score"),
        "mean_expected_rank": ranking_aggregate.get("mean_expected_rank"),
        "mean_noise_above_expected": ranking_aggregate.get("mean_noise_above_expected"),
        "evidence_audit_noise_used": evidence_audit.get("noise_used_by_variant", {}).get(variant_name),
    }


def _dominant_causes(records: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.get("taxonomy", []))
    return dict(counter.most_common())


def _noise_reasoned(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in case.get("concept_contributions", [])
        if item.get("classification") == "Noise" and item.get("reasoned")
    ]


def _contribution_by_id(case: dict[str, Any], concept_id: str) -> dict[str, Any]:
    return next((item for item in case.get("concept_contributions", []) if item.get("concept_id") == concept_id), {})


def _expected_records(rank_case: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for expected in rank_case.get("expected_concepts", []):
        diagnostic = dict(expected.get("diagnostic") or {})
        diagnostic["_rank"] = expected.get("rank")
        diagnostic.setdefault("concept_id", expected.get("concept_id"))
        items.append(diagnostic)
    return items


def _top_index(rank_case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(rank_case.get("top_50", []), start=1):
        copy = dict(item)
        copy["_rank"] = index
        indexed[item["concept_id"]] = copy
    return indexed


def _rank(rank_case: dict[str, Any], concept_id: str) -> int | None:
    for index, item in enumerate(rank_case.get("top_50", []), start=1):
        if item.get("concept_id") == concept_id:
            return index
    return None


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    lines = [
        "# Runtime V1.3 Remaining Noise Audit",
        "",
        f"Final recommendation: `{summary['final_recommendation']}`",
        "",
        "This is a read-only diagnostic report. It does not patch runtime behavior, learning, governance, storage, activation recurrence, or canonical knowledge.",
        "",
        "## Summary",
        "",
        f"- remaining noisy reasoning concepts: `{summary['remaining_noisy_reasoning_concepts']}`",
        f"- cases with remaining noise: `{summary['cases_with_remaining_noise']}`",
        f"- successful noise removals: `{summary['successful_noise_removals']}`",
        f"- unchanged noisy concepts: `{summary['unchanged_noise']}`",
        f"- expected/useful concepts at risk: `{summary['expected_or_useful_at_risk']}`",
        "",
        "## Baseline vs Refined Gate Metrics",
        "",
        "| Metric | V1.2 Baseline | Refined V1.3 |",
        "| --- | ---: | ---: |",
    ]
    for key in [
        "noise_used_in_reasoning",
        "attention_precision",
        "attention_recall",
        "retrieval_recall",
        "retrieval_precision",
        "grounding_score",
        "hallucinations",
        "confidence_calibration",
        "planning_score",
        "mean_expected_rank",
        "mean_noise_above_expected",
    ]:
        lines.append(f"| {key} | `{audit['baseline_metrics'].get(key)}` | `{audit['refined_metrics'].get(key)}` |")

    lines.extend(
        [
            "",
            "## Per-Case Noise Taxonomy",
            "",
            "| Case | Baseline Noise | Refined Noise | Removed | Unchanged | Dominant Causes |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for case in audit["per_case"]:
        causes = ", ".join(f"{key}: {value}" for key, value in case["dominant_remaining_causes"].items()) or "none"
        lines.append(
            f"| {case['case']} | `{case['baseline_noise_used']}` | `{case['refined_noise_used']}` | "
            f"`{case['removed_noise']}` | `{case['unchanged_noise']}` | {causes} |"
        )

    lines.extend(["", "## Remaining Noisy Reasoning Concepts", ""])
    for record in audit["remaining_noisy_reasoning_concepts"]:
        lines.extend(
            [
                f"### {record['case']} / `{record['concept_id']}`",
                "",
                f"- concept: {record.get('concept')}",
                f"- activation: rank `{record.get('activation_rank')}`, score `{record.get('activation_score')}`",
                f"- attention: `{record.get('attention_classification')}` score `{record.get('attention_score')}`",
                f"- usage: reasoned=`{record.get('reasoned')}`, planned=`{record.get('planned')}`, responded=`{record.get('responded')}`",
                f"- overlaps: specific `{record.get('specific_overlap')}`, domain anchors `{record.get('domain_anchor_overlap')}`, generic `{record.get('generic_overlap')}`",
                f"- support: evidence_support `{record.get('evidence_support')}`, confidence `{record.get('confidence')}`, promotion_score `{record.get('promotion_score')}`, projected_centrality `{record.get('projected_centrality')}`",
                f"- inferred pass reason: `{record['pass_reason']}`",
                f"- taxonomy: {', '.join(record['taxonomy'])}",
                f"- nearest expected: `{record['comparison_to_expected'].get('nearest_expected_concept_id')}` with `{record['comparison_to_expected'].get('nearest_expected_shared_terms')}` shared terms",
                "",
            ]
        )

    lines.extend(["## Why Each Noisy Concept Passed The Refined Gate", ""])
    lines.append("| Case | Concept | Inferred Pass Reason | Specific Overlap | Domain Anchors | Generic Overlap |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for record in audit["remaining_noisy_reasoning_concepts"]:
        lines.append(
            f"| {record['case']} | `{record['concept_id']}` | `{record['pass_reason']}` | "
            f"`{record.get('specific_overlap')}` | `{record.get('domain_anchor_overlap')}` | `{record.get('generic_overlap')}` |"
        )

    lines.extend(["", "## Comparison To Expected Concepts", ""])
    lines.append("| Case | Noisy Concept | Nearest Expected | Shared Terms | Jaccard |")
    lines.append("| --- | --- | --- | ---: | ---: |")
    for record in audit["remaining_noisy_reasoning_concepts"]:
        comparison = record["comparison_to_expected"]
        lines.append(
            f"| {record['case']} | `{record['concept_id']}` | `{comparison.get('nearest_expected_concept_id')}` | "
            f"`{comparison.get('nearest_expected_shared_terms')}` | `{comparison.get('nearest_expected_jaccard')}` |"
        )

    lines.extend(["## Successful Noise Removals", ""])
    if audit["successful_noise_removals"]:
        for item in audit["successful_noise_removals"]:
            lines.append(
                f"- `{item['case']}` removed `{item['concept_id']}`: {item.get('concept')} "
                f"(baseline attention `{item.get('baseline_attention_classification')}` -> refined reasoned `{item.get('refined_reasoned')}`)"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Noise Remaining Unchanged", ""])
    if audit["unchanged_noise"]:
        for item in audit["unchanged_noise"]:
            lines.append(
                f"- `{item['case']}` kept noisy `{item['concept_id']}` at rank `{item.get('rank')}` "
                f"with attention `{item.get('attention_classification')}` score `{item.get('attention_score')}`: {item.get('concept')}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Expected Or Useful Concepts At Risk", ""])
    if audit["expected_or_useful_concepts_at_risk"]:
        for item in audit["expected_or_useful_concepts_at_risk"]:
            lines.append(
                f"- `{item['case']}` expected `{item['concept_id']}` was rank `{item.get('rank')}`, "
                f"attended=`{item.get('attended')}`, reasoned=`{item.get('reasoned')}`: {item.get('concept')}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Remaining Failure Modes", ""])
    for cause, count in summary["dominant_failure_modes"].items():
        lines.append(f"- `{cause}`: `{count}`")

    lines.extend(
        [
            "",
            "## Recommended Next Experiment",
            "",
            f"`{summary['final_recommendation']}`",
            "",
            "The strongest signal is that remaining noise is still generally high-support corpus knowledge with weak or ambiguous query-specific fit. The next safe experiment should model whether a concept supports this exact question before it is allowed to influence reasoning as evidence.",
            "",
            "## Explicitly Rejected Experiments",
            "",
        ]
    )
    for item in audit["explicitly_rejected_experiments"]:
        lines.append(f"- `{item}`")
    lines.extend(["", f"`{summary['final_recommendation']}`", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
