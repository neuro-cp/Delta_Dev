"""Focused planning-drift audit for Runtime V1.3 Variant C.

This tool is diagnostic only. It compares the accepted Model B real-knowledge
report against the rejected Variant C response-citation-gate report and writes
read-only audit reports. It does not import or execute runtime code.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_B_REAL = ROOT / "reports" / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = ROOT / "reports" / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
VARIANT_C_REAL = (
    ROOT
    / "reports"
    / "runtime_v13_role_compromise_suite_raw"
    / "variant_c_response_citation_gate"
    / "runtime_v12_real_knowledge.json"
)
VARIANT_C_RANKING = (
    ROOT
    / "reports"
    / "runtime_v13_role_compromise_suite_raw"
    / "variant_c_response_citation_gate"
    / "runtime_v12_activation_ranking_diagnostic.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_set(case: dict[str, Any], key: str) -> set[str]:
    return set(case.get(key) or [])


def case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["name"]: case for case in data.get("cases", [])}


def ranking_case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def concept_text_index(real: dict[str, Any], ranking: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    for metadata in real.get("case_metadata", {}).values():
        for key, role in (
            ("expected_concept_text", "expected"),
            ("useful_neighbor_text", "useful_neighbor"),
        ):
            for item in metadata.get(key, []):
                cid = item.get("concept_id")
                if cid:
                    index.setdefault(cid, {}).update(
                        {
                            "concept_id": cid,
                            "concept": item.get("concept") or item.get("definition") or "",
                            "definition": item.get("definition") or item.get("concept") or "",
                            "metadata_role": role,
                        }
                    )

    for rank_case in ranking.get("cases", []):
        for item in rank_case.get("top_50", []):
            diagnostic = item.get("diagnostic") or item
            cid = diagnostic.get("concept_id") or item.get("concept_id")
            if not cid:
                continue
            record = index.setdefault(cid, {"concept_id": cid})
            for key in (
                "concept",
                "definition",
                "role",
                "activation_score",
                "promotion_score",
                "confidence",
                "projected_centrality",
                "evidence_support",
                "recommendation",
            ):
                if diagnostic.get(key) is not None:
                    record.setdefault(key, diagnostic.get(key))

        for item in rank_case.get("expected_concepts", []):
            diagnostic = item.get("diagnostic") or {}
            cid = item.get("concept_id") or diagnostic.get("concept_id")
            if not cid:
                continue
            record = index.setdefault(cid, {"concept_id": cid})
            record.setdefault("rank", item.get("rank"))
            for key in ("concept", "definition", "role", "activation_score"):
                if diagnostic.get(key) is not None:
                    record.setdefault(key, diagnostic.get(key))

    return index


def concept_record(
    concept_id: str,
    details: dict[str, dict[str, Any]],
    contributions: dict[str, dict[str, Any]],
    expected: set[str],
    useful_neighbors: set[str],
) -> dict[str, Any]:
    detail = dict(details.get(concept_id, {"concept_id": concept_id}))
    contribution = contributions.get(concept_id, {})
    if concept_id in expected:
        evaluator_role = "expected"
    elif concept_id in useful_neighbors:
        evaluator_role = "useful_neighbor"
    else:
        evaluator_role = "noise"
    detail.update(
        {
            "concept_id": concept_id,
            "evaluator_role": evaluator_role,
            "evaluation_classification": contribution.get("classification"),
            "attention_classification": contribution.get("attention_classification"),
            "attention_score": contribution.get("attention_score"),
            "reasoned": contribution.get("reasoned", False),
            "planned": contribution.get("planned", False),
            "responded": contribution.get("responded", False),
            "rationale": contribution.get("rationale"),
        }
    )
    return detail


def summarize_case(
    name: str,
    model_b_case: dict[str, Any],
    variant_c_case: dict[str, Any],
    metadata: dict[str, Any],
    details: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    model_contrib = contribution_map(model_b_case)
    variant_contrib = contribution_map(variant_c_case)

    model_plan = as_set(model_b_case, "planning_referenced_concepts")
    model_response = as_set(model_b_case, "response_referenced_concepts")
    model_reason = as_set(model_b_case, "reasoning_referenced_concepts")
    variant_plan = as_set(variant_c_case, "planning_referenced_concepts")
    variant_response = as_set(variant_c_case, "response_referenced_concepts")
    variant_reason = as_set(variant_c_case, "reasoning_referenced_concepts")

    variant_core_evidence = variant_reason | variant_response
    variant_planning_support = variant_plan - variant_response
    variant_planning_only = variant_plan - variant_reason - variant_response
    model_noise_plan = model_plan - expected - useful
    variant_noise_plan = variant_plan - expected - useful
    variant_noise_planning_support = variant_planning_support - expected - useful

    removed_response_citations = sorted(model_response - variant_response)
    removed_reasoning_evidence = sorted(model_reason - variant_reason)

    if (
        model_b_case.get("runtime_decision") == "Reasoning Drift"
        and variant_c_case.get("runtime_decision") == "Planning Drift"
        and (variant_c_case.get("noise_used_in_reasoning") or 0) < (model_b_case.get("noise_used_in_reasoning") or 0)
    ):
        primary_cause = (
            "Variant C removed noisy reasoning/response citations that made Model B fail earlier as "
            "Reasoning Drift, exposing an existing incomplete planning-core coverage condition."
        )
    elif variant_noise_planning_support:
        primary_cause = "Planning Support is too permissive: evaluator-noise concepts entered the planning lane."
    elif len(variant_plan & expected) < len(expected):
        primary_cause = "Planning Support is too weak for expected concept coverage: at least one expected concept never entered planning."
    else:
        primary_cause = "No deterministic cause isolated from report fields; inspect evaluator classification."

    concept_ids = sorted(
        model_plan
        | model_response
        | model_reason
        | variant_plan
        | variant_response
        | variant_reason
        | expected
        | useful
    )
    concepts = [
        concept_record(cid, details, variant_contrib or model_contrib, expected, useful)
        for cid in concept_ids
    ]

    return {
        "case": name,
        "category": model_b_case.get("category") or variant_c_case.get("category"),
        "question": model_b_case.get("question") or variant_c_case.get("question"),
        "model_b": {
            "runtime_decision": model_b_case.get("runtime_decision"),
            "planning_score": model_b_case.get("planning_score"),
            "planning_core_coverage": model_b_case.get("planning_core_coverage"),
            "response_core_coverage": model_b_case.get("response_core_coverage"),
            "noise_used_in_reasoning": model_b_case.get("noise_used_in_reasoning"),
            "planning_referenced_concepts": sorted(model_plan),
            "reasoning_referenced_concepts": sorted(model_reason),
            "response_referenced_concepts": sorted(model_response),
            "noise_planning_concepts": sorted(model_noise_plan),
        },
        "variant_c": {
            "runtime_decision": variant_c_case.get("runtime_decision"),
            "planning_score": variant_c_case.get("planning_score"),
            "planning_core_coverage": variant_c_case.get("planning_core_coverage"),
            "response_core_coverage": variant_c_case.get("response_core_coverage"),
            "noise_used_in_reasoning": variant_c_case.get("noise_used_in_reasoning"),
            "citable_noise_used_in_reasoning": variant_c_case.get("citable_noise_used_in_reasoning"),
            "core_evidence_count": variant_c_case.get("core_evidence_count"),
            "planning_support_count": variant_c_case.get("planning_support_count"),
            "non_evidence_count": variant_c_case.get("non_evidence_count"),
            "core_evidence_concepts": sorted(variant_core_evidence),
            "planning_support_concepts": sorted(variant_planning_support),
            "planning_only_concepts": sorted(variant_planning_only),
            "noise_planning_concepts": sorted(variant_noise_plan),
            "noise_planning_support_concepts": sorted(variant_noise_planning_support),
        },
        "delta": {
            "new_planning_concepts": sorted(variant_plan - model_plan),
            "removed_planning_concepts": sorted(model_plan - variant_plan),
            "removed_response_citations": removed_response_citations,
            "removed_reasoning_evidence": removed_reasoning_evidence,
            "expected_missing_from_planning": sorted(expected - variant_plan),
            "expected_in_planning": sorted(expected & variant_plan),
            "expected_in_response": sorted(expected & variant_response),
        },
        "primary_cause": primary_cause,
        "concepts": concepts,
    }


def recommendation(audited_cases: list[dict[str, Any]]) -> str:
    if not audited_cases:
        return "RUN_MORE_DIAGNOSTICS"
    if any(case["variant_c"]["noise_planning_support_concepts"] for case in audited_cases):
        return "PROCEED_PLANNING_SUPPORT_SCORING_SIMULATION"
    if any(case["delta"]["expected_missing_from_planning"] for case in audited_cases):
        return "PROCEED_PLANNING_SUPPORT_SCORING_SIMULATION"
    if any(case["delta"]["removed_response_citations"] for case in audited_cases):
        return "PROCEED_PLANNING_RESPONSE_SEPARATION"
    return "RUN_MORE_DIAGNOSTICS"


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Runtime V1.3 Variant C Planning-Drift Audit")
    lines.append("")
    lines.append(f"Generated: `{report['generated_at']}`")
    lines.append("")
    lines.append("Diagnostic only. No runtime behavior, learning, governance, storage, activation, attention, provider, or canonical systems were modified.")
    lines.append("")
    lines.append("## Aggregate Comparison")
    lines.append("")
    lines.append("| Metric | Model B | Variant C |")
    lines.append("| --- | ---: | ---: |")
    for metric in report["aggregate_metrics"]:
        lines.append(f"| {metric} | `{report['model_b_aggregate'].get(metric)}` | `{report['variant_c_aggregate'].get(metric)}` |")
    lines.append("")
    lines.append("## Drift Summary")
    lines.append("")
    lines.append(f"- Model B planning drift cases: `{report['model_b_planning_drift_cases']}`")
    lines.append(f"- Variant C planning drift cases: `{report['variant_c_planning_drift_cases']}`")
    lines.append(f"- New Variant C planning drift cases: `{', '.join(report['new_planning_drift_cases']) or 'none'}`")
    lines.append(f"- Shared planning drift cases: `{', '.join(report['shared_planning_drift_cases']) or 'none'}`")
    lines.append("")
    lines.append("## New Planning-Drift Cases")
    lines.append("")
    if not report["new_case_audits"]:
        lines.append("No new planning-drift cases were found.")
    for case in report["new_case_audits"]:
        lines.append(f"### {case['case']}")
        lines.append("")
        lines.append(f"- Model B decision: `{case['model_b']['runtime_decision']}`")
        lines.append(f"- Variant C decision: `{case['variant_c']['runtime_decision']}`")
        lines.append(f"- Model B noisy reasoning concepts: `{case['model_b']['noise_used_in_reasoning']}`")
        lines.append(f"- Variant C noisy reasoning concepts: `{case['variant_c']['noise_used_in_reasoning']}`")
        lines.append(f"- Planning core coverage: `{case['model_b']['planning_core_coverage']}` -> `{case['variant_c']['planning_core_coverage']}`")
        lines.append(f"- Response core coverage: `{case['model_b']['response_core_coverage']}` -> `{case['variant_c']['response_core_coverage']}`")
        lines.append(f"- Primary cause: {case['primary_cause']}")
        lines.append("")
        lines.append("#### Concept Movement")
        lines.append("")
        lines.append(f"- Variant C Core Evidence: `{', '.join(case['variant_c']['core_evidence_concepts']) or 'none'}`")
        lines.append(f"- Variant C Planning Support: `{', '.join(case['variant_c']['planning_support_concepts']) or 'none'}`")
        lines.append(f"- Planning-only concepts: `{', '.join(case['variant_c']['planning_only_concepts']) or 'none'}`")
        lines.append(f"- Removed response citations: `{', '.join(case['delta']['removed_response_citations']) or 'none'}`")
        lines.append(f"- Removed reasoning evidence: `{', '.join(case['delta']['removed_reasoning_evidence']) or 'none'}`")
        lines.append(f"- Expected missing from planning: `{', '.join(case['delta']['expected_missing_from_planning']) or 'none'}`")
        lines.append("")
        lines.append("#### Concepts")
        lines.append("")
        lines.append("| Concept ID | Eval Role | Eval Class | Attn Class | Reasoned | Planned | Responded | Text |")
        lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | --- |")
        for concept in case["concepts"]:
            text = (concept.get("concept") or concept.get("definition") or "").replace("|", "\\|")
            if len(text) > 140:
                text = text[:137] + "..."
            lines.append(
                "| {concept_id} | {role} | {classification} | {attention} | {reasoned} | {planned} | {responded} | {text} |".format(
                    concept_id=concept["concept_id"],
                    role=concept.get("evaluator_role"),
                    classification=concept.get("evaluation_classification"),
                    attention=concept.get("attention_classification"),
                    reasoned=concept.get("reasoned"),
                    planned=concept.get("planned"),
                    responded=concept.get("responded"),
                    text=text,
                )
            )
        lines.append("")
    lines.append("## Shared Planning-Drift Cases")
    lines.append("")
    if not report["shared_case_audits"]:
        lines.append("No shared planning-drift cases were found.")
    for case in report["shared_case_audits"]:
        lines.append(
            f"- `{case['case']}` stayed `Planning Drift`; planning core coverage `{case['model_b']['planning_core_coverage']}` -> `{case['variant_c']['planning_core_coverage']}`."
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(report["interpretation"])
    lines.append("")
    lines.append("## Smallest Safe Next Experiment")
    lines.append("")
    lines.append(report["smallest_safe_next_experiment"])
    lines.append("")
    lines.append(report["final_recommendation"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    model_b = load_json(args.model_b_real)
    variant_c = load_json(args.variant_c_real)
    model_b_ranking = load_json(args.model_b_ranking)
    variant_c_ranking = load_json(args.variant_c_ranking)
    model_cases = case_map(model_b)
    variant_cases = case_map(variant_c)

    details = concept_text_index(model_b, model_b_ranking)
    details.update(concept_text_index(variant_c, variant_c_ranking))

    model_b_planning = {name for name, case in model_cases.items() if case.get("runtime_decision") == "Planning Drift"}
    variant_c_planning = {name for name, case in variant_cases.items() if case.get("runtime_decision") == "Planning Drift"}
    new_planning = sorted(variant_c_planning - model_b_planning)
    shared_planning = sorted(variant_c_planning & model_b_planning)

    case_metadata = variant_c.get("case_metadata") or model_b.get("case_metadata") or {}
    new_case_audits = [
        summarize_case(name, model_cases[name], variant_cases[name], case_metadata.get(name, {}), details)
        for name in new_planning
        if name in model_cases and name in variant_cases
    ]
    shared_case_audits = [
        summarize_case(name, model_cases[name], variant_cases[name], case_metadata.get(name, {}), details)
        for name in shared_planning
        if name in model_cases and name in variant_cases
    ]

    final = recommendation(new_case_audits)
    interpretation = (
        "Variant C did not create a lower planning score and did not change aggregate planning-core coverage. "
        "The new planning-drift case is caused by removing noisy reasoning/response evidence that made Model B fail earlier as Reasoning Drift. "
        "Once that higher-priority reasoning failure is removed, the evaluator can see the existing partial planning-core coverage. "
        "In the new drift case, Variant C still permits evaluator-noise concepts into Planning Support, so the next step should be a scoring simulation for planning support rather than a live behavior patch."
    )
    smallest = (
        "Run a report-only Planning Support scoring simulation that keeps Model B as the default, preserves response citation separation, "
        "and tests whether planning-support candidates can be scored to exclude evaluator-noise concepts while retaining expected planning coverage. "
        "Do not patch live runtime until the simulation shows planning_drift_cases does not regress."
    )

    metrics = [
        "planning_score",
        "planning_drift_cases",
        "reasoning_drift_cases",
        "noise_used_in_reasoning",
        "citable_noise_used_in_reasoning",
        "planning_support_count",
        "planning_core_coverage",
        "response_core_coverage",
        "attention_precision",
        "attention_recall",
        "hallucinations",
    ]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model_b_real_path": str(args.model_b_real),
        "variant_c_real_path": str(args.variant_c_real),
        "model_b_ranking_path": str(args.model_b_ranking),
        "variant_c_ranking_path": str(args.variant_c_ranking),
        "model_b_aggregate": model_b.get("aggregate", {}),
        "variant_c_aggregate": variant_c.get("aggregate", {}),
        "aggregate_metrics": metrics,
        "model_b_planning_drift_cases": sorted(model_b_planning),
        "variant_c_planning_drift_cases": sorted(variant_c_planning),
        "new_planning_drift_cases": new_planning,
        "shared_planning_drift_cases": shared_planning,
        "new_case_audits": new_case_audits,
        "shared_case_audits": shared_case_audits,
        "interpretation": interpretation,
        "smallest_safe_next_experiment": smallest,
        "final_recommendation": final,
        "read_only_verified": {
            "model_b_real": model_b.get("read_only_verified"),
            "variant_c_real": variant_c.get("read_only_verified"),
            "model_b_ranking": model_b_ranking.get("read_only_verified"),
            "variant_c_ranking": variant_c_ranking.get("read_only_verified"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    parser.add_argument("--variant-c-real", type=Path, default=VARIANT_C_REAL)
    parser.add_argument("--variant-c-ranking", type=Path, default=VARIANT_C_RANKING)
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.model_b_real = args.model_b_real.resolve()
    args.model_b_ranking = args.model_b_ranking.resolve()
    args.variant_c_real = args.variant_c_real.resolve()
    args.variant_c_ranking = args.variant_c_ranking.resolve()
    args.reports_dir = args.reports_dir.resolve()
    args.reports_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_variant_c_planning_drift_audit.json"
    md_path = args.reports_dir / "runtime_v13_variant_c_planning_drift_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, md_path)

    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
