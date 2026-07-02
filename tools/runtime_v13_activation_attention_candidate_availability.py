"""Runtime V1.3 activation/attention candidate-availability diagnostic.

This is a report-only diagnostic over the accepted Model B default. It does not
patch runtime behavior or run inference. It quantifies whether expected concepts
are unavailable because activation ranked them too low, attention pruned them,
or they are absent from the diagnostic window.
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
CONSOLIDATION = REPORTS / "runtime_v13_failure_bottleneck_consolidation_audit.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
V12_REAL = REPORTS / "runtime_v12_baseline_before_v13" / "runtime_v12_real_knowledge.json"
V12_RANKING = REPORTS / "runtime_v12_baseline_before_v13" / "runtime_v12_activation_ranking_diagnostic.json"

GENERIC_ANCHORS = {
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
    "cause",
    "contradiction",
    "decision",
    "decrease",
    "evidence",
    "exception",
    "failure rate",
    "if",
    "increase",
    "prediction",
    "reallocate",
    "revise",
    "root cause",
    "tradeoff",
    "validate",
    "would",
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


def concept_lookup(ranking_case: dict[str, Any], concept_id: str) -> dict[str, Any]:
    for rank, item in enumerate(ranking_case.get("top_50", []), start=1):
        if item.get("concept_id") == concept_id:
            return {**item, "rank": rank, "present_in_top_50": True}
    for item in ranking_case.get("expected_concepts", []):
        if item.get("concept_id") == concept_id:
            diagnostic = item.get("diagnostic") or {}
            return {
                **diagnostic,
                "rank": item.get("rank"),
                "selected_by_attention": item.get("selected_by_attention"),
                "pruned_by_attention": item.get("pruned_by_attention"),
                "present_in_top_50": item.get("rank") is not None,
            }
    return {"concept_id": concept_id, "rank": None, "present_in_top_50": False}


def availability_bucket(rank: int | None, selected_by_attention: bool | None) -> str:
    if rank is None:
        return "absent_from_diagnostic_top_50"
    if rank <= 10 and selected_by_attention:
        return "inside_top10_selected_by_attention"
    if rank <= 10:
        return "inside_top10_pruned_by_attention"
    if rank <= 20:
        return "outside_top10_inside_top20"
    if rank <= 50:
        return "outside_top20_inside_top50"
    return "absent_from_diagnostic_top_50"


def feature_summary(item: dict[str, Any]) -> dict[str, Any]:
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    query_terms = {term.lower() for term in item.get("query_combined_overlap", [])}
    generic = sorted(query_terms & GENERIC_ANCHORS)
    relation = sorted(term for term in RELATION_TERMS if term in text.lower())
    specific = sorted(query_terms - GENERIC_ANCHORS)
    return {
        "query_specific_overlap": specific,
        "query_specific_overlap_count": len(specific),
        "generic_anchor_overlap": generic,
        "generic_anchor_ratio": round(len(generic) / max(1, len(query_terms)), 4),
        "relation_terms": relation,
        "relation_specificity_count": len(relation),
        "evidence_support": item.get("evidence_support"),
        "confidence": item.get("confidence"),
        "promotion_score": item.get("promotion_score"),
        "projected_centrality": item.get("projected_centrality"),
        "concept_definition_alignment": round(
            len(tokens(item.get("concept", "")) & tokens(item.get("definition", "")))
            / max(1, len(tokens(item.get("concept", "")) | tokens(item.get("definition", "")))),
            4,
        )
        if item.get("concept") or item.get("definition")
        else None,
    }


def expected_records(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, Any]]:
    contributions = contribution_map(case)
    records = []
    for item in metadata.get("expected_concept_text", []):
        concept_id = item.get("concept_id")
        if not concept_id:
            continue
        lookup = concept_lookup(ranking_case, concept_id)
        contribution = contributions.get(concept_id, {})
        selected = lookup.get("selected_by_attention")
        if selected is None:
            selected = contribution.get("attended")
        bucket = availability_bucket(lookup.get("rank"), bool(selected) if selected is not None else False)
        records.append(
            {
                "concept_id": concept_id,
                "concept": item.get("definition") or item.get("concept") or lookup.get("concept") or "",
                "rank": lookup.get("rank"),
                "selected_by_attention": bool(selected),
                "reached_working_memory": bool(contribution.get("attended")),
                "reached_reasoning": bool(contribution.get("reasoned")),
                "reached_planning": bool(contribution.get("planned")),
                "bucket": bucket,
                "features": feature_summary(lookup),
            }
        )
    return records


def top_range_risk(ranking_case: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    contributions = contribution_map(case)
    ranges = {
        "top10": ranking_case.get("top_50", [])[:10],
        "rank11_20": ranking_case.get("top_50", [])[10:20],
        "rank21_50": ranking_case.get("top_50", [])[20:50],
    }
    risk: dict[str, Any] = {}
    for name, items in ranges.items():
        noise = [item for item in items if item.get("role") == "noise"]
        expected = [item for item in items if item.get("role") == "expected"]
        attended_noise = [
            item
            for item in noise
            if contributions.get(item.get("concept_id", ""), {}).get("attended")
        ]
        pruned_noise = [
            item
            for item in noise
            if not contributions.get(item.get("concept_id", ""), {}).get("attended")
        ]
        risk[name] = {
            "candidate_count": len(items),
            "expected_count": len(expected),
            "noise_count": len(noise),
            "attended_noise_count": len(attended_noise),
            "pruned_noise_count": len(pruned_noise),
            "noise_to_expected_ratio": round(len(noise) / max(1, len(expected)), 4),
        }
    return risk


def audit_case(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    expected = expected_records(case, ranking_case, metadata)
    buckets = Counter(record["bucket"] for record in expected)
    return {
        "case": case["name"],
        "category": case.get("category"),
        "question": case.get("question"),
        "runtime_decision": case.get("runtime_decision"),
        "planning_core_coverage": case.get("planning_core_coverage"),
        "noise_used_in_reasoning": case.get("noise_used_in_reasoning"),
        "bucket_counts": dict(buckets),
        "expected_concepts": expected,
        "range_noise_risk": top_range_risk(ranking_case, case),
    }


def choose_recommendation(case_audits: list[dict[str, Any]]) -> str:
    bucket_counts = Counter(
        record["bucket"]
        for case in case_audits
        for record in case["expected_concepts"]
    )
    attention_pruned = bucket_counts["inside_top10_pruned_by_attention"]
    rank_11_20 = bucket_counts["outside_top10_inside_top20"]
    deep = bucket_counts["outside_top20_inside_top50"] + bucket_counts["absent_from_diagnostic_top_50"]
    top20_noise = sum(case["range_noise_risk"]["rank11_20"]["noise_count"] for case in case_audits)
    top20_expected = sum(case["range_noise_risk"]["rank11_20"]["expected_count"] for case in case_audits)
    if attention_pruned >= max(rank_11_20, deep / 2):
        return "PROCEED_BOUNDED_ATTENTION_RESCUE_SIMULATION"
    if rank_11_20 > 0 and top20_noise <= 6 * max(1, top20_expected):
        return "PROCEED_BOUNDED_ACTIVATION_WINDOW_SIMULATION"
    if deep > 0:
        return "PROCEED_ACTIVATION_RERANKING_SIMULATION"
    if not bucket_counts:
        return "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13"
    return "RUN_MORE_DIAGNOSTICS"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    consolidation = load_json(args.consolidation)
    model_b = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    cases = case_map(model_b)
    rankings = ranking_case_map(ranking)
    metadata = model_b.get("case_metadata", {})
    failed_names = [case["case"] for case in consolidation.get("case_audits", [])]
    audits = [
        audit_case(cases[name], rankings.get(name, {}), metadata.get(name, {}))
        for name in failed_names
        if name in cases
    ]
    bucket_counts = Counter(
        record["bucket"]
        for case in audits
        for record in case["expected_concepts"]
    )
    aggregate_risk = {
        "top10_pruned_noise": sum(case["range_noise_risk"]["top10"]["pruned_noise_count"] for case in audits),
        "top10_expected": sum(case["range_noise_risk"]["top10"]["expected_count"] for case in audits),
        "rank11_20_expected": sum(case["range_noise_risk"]["rank11_20"]["expected_count"] for case in audits),
        "rank11_20_noise": sum(case["range_noise_risk"]["rank11_20"]["noise_count"] for case in audits),
        "rank21_50_expected": sum(case["range_noise_risk"]["rank21_50"]["expected_count"] for case in audits),
        "rank21_50_noise": sum(case["range_noise_risk"]["rank21_50"]["noise_count"] for case in audits),
    }
    recommendation = choose_recommendation(audits)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "live_runtime_changed": False,
        "source_reports": {
            "consolidation": str(args.consolidation),
            "model_b_real": str(args.model_b_real),
            "model_b_ranking": str(args.model_b_ranking),
            "v12_real": str(args.v12_real) if args.v12_real.exists() else None,
            "v12_ranking": str(args.v12_ranking) if args.v12_ranking.exists() else None,
        },
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "bucket_distribution": dict(bucket_counts),
        "noise_risk_estimate": aggregate_risk,
        "case_audits": audits,
        "rejected_paths": [
            "more Planning Support/QRM variants",
            "hard concept blacklist",
            "evaluator-label logic",
            "benchmark case IDs or concept IDs in live logic",
            "global threshold loosening",
            "activation recurrence by default",
        ],
        "smallest_safe_next_simulation": simulation_label(recommendation),
        "interpretation": interpretation(bucket_counts, aggregate_risk, recommendation),
        "final_recommendation": recommendation,
    }


def simulation_label(recommendation: str) -> str:
    return {
        "PROCEED_BOUNDED_ATTENTION_RESCUE_SIMULATION": "bounded attention rescue simulation",
        "PROCEED_BOUNDED_ACTIVATION_WINDOW_SIMULATION": "bounded activation-window expansion simulation",
        "PROCEED_ACTIVATION_RERANKING_SIMULATION": "activation reranking simulation",
        "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13": "checkpoint Model B and stop Runtime V1.3",
        "RUN_MORE_DIAGNOSTICS": "additional diagnostics",
    }[recommendation]


def interpretation(bucket_counts: Counter[str], risk: dict[str, Any], recommendation: str) -> str:
    if recommendation == "PROCEED_BOUNDED_ATTENTION_RESCUE_SIMULATION":
        return (
            "The largest immediately actionable availability failure is expected concepts already inside the top-10 activation "
            "window but pruned before working memory. This suggests testing a bounded attention rescue before broadening activation."
        )
    if recommendation == "PROCEED_BOUNDED_ACTIVATION_WINDOW_SIMULATION":
        return (
            "Several expected concepts are near misses in ranks 11-20 and the estimated noise risk is bounded enough to simulate "
            "a narrow activation-window expansion."
        )
    if recommendation == "PROCEED_ACTIVATION_RERANKING_SIMULATION":
        return (
            "Many expected concepts are deep misses or absent from the diagnostic top-50, so window expansion would mostly admit noise. "
            "The safer next diagnostic is activation reranking."
        )
    return "Model B should be checkpointed unless a new runtime failure justifies further V1.3 work."


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Activation/Attention Candidate Availability",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Diagnostic only. No runtime behavior, learning, governance, storage, provider, activation, attention, candidate-store, or canonical systems were modified.",
        "",
        "## Summary",
        "",
        f"- Current accepted default: {report['current_accepted_default']}",
        f"- Bucket distribution: `{report['bucket_distribution']}`",
        f"- Noise risk estimate: `{report['noise_risk_estimate']}`",
        f"- Smallest safe next simulation: `{report['smallest_safe_next_simulation']}`",
        "",
        "## Case Bottleneck Table",
        "",
        "| Case | Decision | Top10 Selected | Top10 Pruned | Rank 11-20 | Rank 21-50 | Absent | Top20 Noise/Expected |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in report["case_audits"]:
        buckets = case["bucket_counts"]
        risk = case["range_noise_risk"]["rank11_20"]
        lines.append(
            f"| {case['case']} | `{case['runtime_decision']}` | "
            f"`{buckets.get('inside_top10_selected_by_attention', 0)}` | "
            f"`{buckets.get('inside_top10_pruned_by_attention', 0)}` | "
            f"`{buckets.get('outside_top10_inside_top20', 0)}` | "
            f"`{buckets.get('outside_top20_inside_top50', 0)}` | "
            f"`{buckets.get('absent_from_diagnostic_top_50', 0)}` | "
            f"`{risk['noise_count']}/{risk['expected_count']}` |"
        )
    lines.extend(["", "## Expected Concept Availability", ""])
    lines.append("| Case | Concept ID | Bucket | Rank | Attention | Reasoning | Planning | Specific Overlap | Relation Terms | Text |")
    lines.append("| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- | --- |")
    for case in report["case_audits"]:
        for record in case["expected_concepts"]:
            text = record["concept"].replace("|", "\\|")
            if len(text) > 110:
                text = text[:107] + "..."
            lines.append(
                f"| {case['case']} | {record['concept_id']} | `{record['bucket']}` | `{record['rank']}` | "
                f"`{record['selected_by_attention']}` | `{record['reached_reasoning']}` | `{record['reached_planning']}` | "
                f"`{', '.join(record['features']['query_specific_overlap'])}` | "
                f"`{', '.join(record['features']['relation_terms'])}` | {text} |"
            )
    lines.extend(["", "## Attention-Pruned Expected Concepts", ""])
    pruned = [
        (case, record)
        for case in report["case_audits"]
        for record in case["expected_concepts"]
        if record["bucket"] == "inside_top10_pruned_by_attention"
    ]
    if not pruned:
        lines.append("No expected concepts were pruned inside the top-10 activation window.")
    else:
        lines.append("| Case | Concept ID | Rank | Features |")
        lines.append("| --- | --- | ---: | --- |")
        for case, record in pruned:
            lines.append(
                f"| {case['case']} | {record['concept_id']} | `{record['rank']}` | "
                f"specific=`{record['features']['query_specific_overlap_count']}`, "
                f"relation=`{record['features']['relation_specificity_count']}`, "
                f"generic_ratio=`{record['features']['generic_anchor_ratio']}` |"
            )
    lines.extend(["", "## Top-10/Top-20/Top-50 Miss Table", ""])
    lines.append("| Bucket | Count |")
    lines.append("| --- | ---: |")
    for bucket, count in sorted(report["bucket_distribution"].items()):
        lines.append(f"| {bucket} | `{count}` |")
    lines.extend(
        [
            "",
            "## Noise Risk Estimate",
            "",
            f"- Top-10 pruned noise candidates: `{report['noise_risk_estimate']['top10_pruned_noise']}`",
            f"- Rank 11-20 expected/noise: `{report['noise_risk_estimate']['rank11_20_expected']}` / `{report['noise_risk_estimate']['rank11_20_noise']}`",
            f"- Rank 21-50 expected/noise: `{report['noise_risk_estimate']['rank21_50_expected']}` / `{report['noise_risk_estimate']['rank21_50_noise']}`",
            "",
            "## Rejected Paths",
            "",
        ]
    )
    for item in report["rejected_paths"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            report["final_recommendation"],
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    json_path = args.reports_dir / "runtime_v13_activation_attention_candidate_availability.json"
    md_path = args.reports_dir / "runtime_v13_activation_attention_candidate_availability.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
