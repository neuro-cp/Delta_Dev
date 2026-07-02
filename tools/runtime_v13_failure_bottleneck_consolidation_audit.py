"""Consolidate Runtime V1.3 failures by bottleneck layer.

This is a diagnostic-only audit over the accepted Model B baseline. It asks
whether failed cases were missing evidence upstream (activation/attention) or
whether downstream role/planning gates could plausibly have fixed them.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"

BOTTLENECKS = (
    "activation_rank_unavailable",
    "attention_pruned_expected",
    "reasoning_gate_misclassified",
    "planning_support_misclassified",
    "evaluator_priority_artifact",
    "benchmark_expected_concept_outside_live_window",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["name"]: case for case in data.get("cases", [])}


def ranking_case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def expected_diagnostic(ranking_case: dict[str, Any], concept_id: str) -> dict[str, Any]:
    for item in ranking_case.get("expected_concepts", []):
        if item.get("concept_id") == concept_id:
            diagnostic = item.get("diagnostic") or {}
            return {
                "rank": item.get("rank"),
                "inside_top_10": item.get("inside_top_10"),
                "inside_top_20": item.get("inside_top_20"),
                "selected_by_attention": item.get("selected_by_attention"),
                "pruned_by_attention": item.get("pruned_by_attention"),
                "activation_score": diagnostic.get("activation_score"),
                "query_overlap": diagnostic.get("query_combined_overlap", []),
                "concept": diagnostic.get("concept") or diagnostic.get("definition") or "",
            }
    for rank, item in enumerate(ranking_case.get("top_50", []), start=1):
        if item.get("concept_id") == concept_id:
            return {
                "rank": rank,
                "inside_top_10": rank <= 10,
                "inside_top_20": rank <= 20,
                "selected_by_attention": None,
                "pruned_by_attention": None,
                "activation_score": item.get("activation_score"),
                "query_overlap": item.get("query_combined_overlap", []),
                "concept": item.get("concept") or item.get("definition") or "",
            }
    return {
        "rank": None,
        "inside_top_10": False,
        "inside_top_20": False,
        "selected_by_attention": False,
        "pruned_by_attention": None,
        "activation_score": None,
        "query_overlap": [],
        "concept": "",
    }


def classify_expected(
    *,
    contribution: dict[str, Any] | None,
    diagnostic: dict[str, Any],
    case_decision: str,
) -> str:
    rank = diagnostic.get("rank")
    if rank is None:
        return "benchmark_expected_concept_outside_live_window"
    if rank > 20:
        return "benchmark_expected_concept_outside_live_window"
    if rank > 10:
        return "activation_rank_unavailable"
    selected = diagnostic.get("selected_by_attention")
    if selected is False:
        return "attention_pruned_expected"
    if contribution and contribution.get("attended") and not contribution.get("reasoned"):
        return "reasoning_gate_misclassified"
    if contribution and contribution.get("reasoned") and not contribution.get("planned"):
        return "planning_support_misclassified"
    if case_decision == "Reasoning Drift" and contribution and contribution.get("planned"):
        return "evaluator_priority_artifact"
    return "reasoning_gate_misclassified"


def case_primary_bottleneck(records: list[dict[str, Any]], case: dict[str, Any]) -> str:
    counts = Counter(record["bottleneck"] for record in records)
    decision = case.get("runtime_decision")
    if decision == "Reasoning Drift" and case.get("noise_used_in_reasoning", 0) > 0:
        missing_upstream = counts["activation_rank_unavailable"] + counts["attention_pruned_expected"] + counts["benchmark_expected_concept_outside_live_window"]
        if missing_upstream == 0:
            return "evaluator_priority_artifact"
    for bottleneck in (
        "benchmark_expected_concept_outside_live_window",
        "activation_rank_unavailable",
        "attention_pruned_expected",
        "evaluator_priority_artifact",
        "reasoning_gate_misclassified",
        "planning_support_misclassified",
    ):
        if counts[bottleneck]:
            return bottleneck
    return "reasoning_gate_misclassified"


def audit_case(
    *,
    case: dict[str, Any],
    ranking_case: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    contributions = contribution_map(case)
    expected_records = []
    for item in metadata.get("expected_concept_text", []):
        concept_id = item.get("concept_id")
        if not concept_id:
            continue
        diagnostic = expected_diagnostic(ranking_case, concept_id)
        contribution = contributions.get(concept_id)
        bottleneck = classify_expected(
            contribution=contribution,
            diagnostic=diagnostic,
            case_decision=case.get("runtime_decision", ""),
        )
        reached_working_memory = bool(contribution and contribution.get("attended"))
        reached_reasoning = bool(contribution and contribution.get("reasoned"))
        reached_planning = bool(contribution and contribution.get("planned"))
        downstream_fix_possible = reached_working_memory and diagnostic.get("rank") is not None and diagnostic.get("rank") <= 10
        expected_records.append(
            {
                "concept_id": concept_id,
                "concept": item.get("definition") or item.get("concept") or diagnostic.get("concept") or "",
                "activation_rank": diagnostic.get("rank"),
                "activation_score": diagnostic.get("activation_score"),
                "selected_by_attention": diagnostic.get("selected_by_attention"),
                "pruned_by_attention": diagnostic.get("pruned_by_attention"),
                "reached_working_memory": reached_working_memory,
                "reached_reasoning": reached_reasoning,
                "reached_planning": reached_planning,
                "query_overlap": diagnostic.get("query_overlap", []),
                "bottleneck": bottleneck,
                "downstream_gates_could_fix_without_activation_attention": downstream_fix_possible,
            }
        )
    primary = case_primary_bottleneck(expected_records, case)
    downstream_possible = any(
        record["downstream_gates_could_fix_without_activation_attention"]
        for record in expected_records
    )
    return {
        "case": case["name"],
        "category": case.get("category"),
        "question": case.get("question"),
        "runtime_decision": case.get("runtime_decision"),
        "planning_score": case.get("planning_score"),
        "planning_core_coverage": case.get("planning_core_coverage"),
        "response_core_coverage": case.get("response_core_coverage"),
        "noise_used_in_reasoning": case.get("noise_used_in_reasoning"),
        "expected_concepts": expected_records,
        "primary_bottleneck": primary,
        "downstream_gates_could_fix_case_without_activation_attention": downstream_possible
        and primary not in {"activation_rank_unavailable", "attention_pruned_expected", "benchmark_expected_concept_outside_live_window"},
        "smallest_appropriate_intervention_layer": intervention_for(primary),
    }


def intervention_for(bottleneck: str) -> str:
    if bottleneck in {
        "activation_rank_unavailable",
        "benchmark_expected_concept_outside_live_window",
    }:
        return "activation/ranking diagnostics"
    if bottleneck == "attention_pruned_expected":
        return "attention selection diagnostics"
    if bottleneck == "evaluator_priority_artifact":
        return "evaluation taxonomy audit"
    if bottleneck == "reasoning_gate_misclassified":
        return "reasoning usage gate audit"
    if bottleneck == "planning_support_misclassified":
        return "planning support audit"
    return "diagnostics"


def final_recommendation(summary: Counter[str]) -> str:
    upstream = (
        summary["activation_rank_unavailable"]
        + summary["attention_pruned_expected"]
        + summary["benchmark_expected_concept_outside_live_window"]
    )
    downstream = summary["reasoning_gate_misclassified"] + summary["planning_support_misclassified"]
    if upstream >= downstream and upstream > 0:
        return "RETURN_TO_ACTIVATION_ATTENTION_DIAGNOSTICS"
    if downstream > upstream:
        return "CONTINUE_DOWNSTREAM_ROLE_WORK"
    return "CHECKPOINT_MODEL_B_AND_STOP_V13"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    model_b = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    rankings = ranking_case_map(ranking)
    metadata = model_b.get("case_metadata", {})
    failed_cases = [
        case
        for case in model_b.get("cases", [])
        if case.get("runtime_decision") != "Healthy"
    ]
    audits = [
        audit_case(
            case=case,
            ranking_case=rankings.get(case["name"], {}),
            metadata=metadata.get(case["name"], {}),
        )
        for case in failed_cases
    ]
    case_summary = Counter(audit["primary_bottleneck"] for audit in audits)
    concept_summary = Counter(
        record["bottleneck"]
        for audit in audits
        for record in audit["expected_concepts"]
    )
    final = final_recommendation(case_summary)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "live_runtime_changed": False,
        "source_reports": {
            "model_b_real": str(args.model_b_real),
            "model_b_ranking": str(args.model_b_ranking),
        },
        "model_b_aggregate": model_b.get("aggregate", {}),
        "failed_case_count": len(audits),
        "case_bottleneck_distribution": dict(case_summary),
        "concept_bottleneck_distribution": dict(concept_summary),
        "case_audits": audits,
        "interpretation": interpretation(case_summary, concept_summary, final),
        "final_recommendation": final,
    }


def interpretation(case_summary: Counter[str], concept_summary: Counter[str], final: str) -> str:
    if final == "RETURN_TO_ACTIVATION_ATTENTION_DIAGNOSTICS":
        return (
            "Most failed cases are limited before downstream role/planning gates can act: expected concepts are outside "
            "the effective activation window, outside the benchmark live window, or pruned before reasoning/planning. "
            "Downstream Planning Support variants are therefore compensating for upstream candidate availability."
        )
    if final == "CONTINUE_DOWNSTREAM_ROLE_WORK":
        return (
            "Most failures have expected evidence available in working memory/reasoning, so downstream role/planning work remains justified."
        )
    return (
        "Model B is stable enough to checkpoint and stop V1.3 role work until a new observed runtime failure justifies reopening it."
    )


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Failure Bottleneck Consolidation Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Diagnostic only. No runtime behavior, learning, governance, storage, provider, activation, attention, candidate-store, or canonical systems were modified.",
        "",
        "## Summary",
        "",
        f"- Failed cases audited: `{report['failed_case_count']}`",
        f"- Case bottleneck distribution: `{report['case_bottleneck_distribution']}`",
        f"- Concept bottleneck distribution: `{report['concept_bottleneck_distribution']}`",
        f"- Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Case Table",
        "",
        "| Case | Decision | Primary Bottleneck | Intervention Layer | Downstream Fix Possible | Noise Used | Planning Coverage |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for audit in report["case_audits"]:
        lines.append(
            f"| {audit['case']} | `{audit['runtime_decision']}` | `{audit['primary_bottleneck']}` | "
            f"{audit['smallest_appropriate_intervention_layer']} | "
            f"`{audit['downstream_gates_could_fix_case_without_activation_attention']}` | "
            f"`{audit['noise_used_in_reasoning']}` | `{audit['planning_core_coverage']}` |"
        )
    lines.extend(["", "## Expected Concept Traces", ""])
    for audit in report["case_audits"]:
        lines.append(f"### {audit['case']}")
        lines.append("")
        lines.append("| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |")
        lines.append("| --- | ---: | --- | ---: | ---: | ---: | --- | --- |")
        for record in audit["expected_concepts"]:
            text = record["concept"].replace("|", "\\|")
            if len(text) > 120:
                text = text[:117] + "..."
            lines.append(
                f"| {record['concept_id']} | `{record['activation_rank']}` | `{record['selected_by_attention']}` | "
                f"`{record['reached_working_memory']}` | `{record['reached_reasoning']}` | "
                f"`{record['reached_planning']}` | `{record['bottleneck']}` | {text} |"
            )
        lines.append("")
    lines.extend(
        [
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
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_failure_bottleneck_consolidation_audit.json"
    md_path = args.reports_dir / "runtime_v13_failure_bottleneck_consolidation_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
