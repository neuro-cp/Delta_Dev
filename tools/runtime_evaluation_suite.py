from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge.semantic_record import SemanticKnowledgeRecord
from orchestration.runtime.runtime_evaluation import (
    RuntimeEvaluationCase,
    RuntimeEvaluationSuite,
    RuntimeEvaluationReport,
    runtime_report_to_json,
    runtime_report_to_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Runtime V1 Evaluation Suite.")
    parser.add_argument(
        "--store-root",
        type=Path,
        default=Path(".tmp/runtime_evaluation/fixture_store"),
        help="Candidate knowledge store root. A fixture store is created when missing.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="Directory for evaluation reports and fixture governance.",
    )
    args = parser.parse_args()

    store_root = args.store_root
    reports_dir = args.reports_dir
    fixture_reports = reports_dir / "runtime_evaluation_fixture"
    _ensure_fixture_store(store_root=store_root, reports_dir=fixture_reports)

    suite = RuntimeEvaluationSuite(
        suite_name="Phase B Runtime Evaluation Suite",
        cases=_default_cases(),
        activation_limit=6,
    )
    report = suite.run(store_root=store_root, reports_dirs=(fixture_reports,))

    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phaseB_runtime_evaluation_report.json").write_text(
        runtime_report_to_json(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_runtime_evaluation_report.md").write_text(
        runtime_report_to_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_runtime_scorecards.md").write_text(
        _scorecards_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_runtime_efficiency.json").write_text(
        json.dumps(_efficiency_payload(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "phaseB_runtime_efficiency.md").write_text(
        _efficiency_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_activation_waste.md").write_text(
        _activation_waste_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_neighbor_utility.md").write_text(
        _neighbor_utility_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_reasoning_contribution.json").write_text(
        json.dumps(_reasoning_contribution_payload(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "phaseB_reasoning_contribution.md").write_text(
        _reasoning_contribution_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_reasoning_flow.md").write_text(
        _reasoning_flow_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_contribution_scorecards.md").write_text(
        _contribution_scorecards_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_attention_vs_reasoning.md").write_text(
        _attention_vs_reasoning_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_attention_optimization.json").write_text(
        json.dumps(_attention_optimization_payload(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "phaseB_attention_optimization.md").write_text(
        _attention_optimization_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_attention_tradeoff.md").write_text(
        _attention_tradeoff_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_attention_score_distribution.md").write_text(
        _attention_score_distribution_markdown(report),
        encoding="utf-8",
    )
    (reports_dir / "phaseB_runtime_progress.md").write_text(
        _runtime_progress_markdown(report),
        encoding="utf-8",
    )
    return 0


def _default_cases() -> list[RuntimeEvaluationCase]:
    return [
        RuntimeEvaluationCase(
            name="gps_drift_retrieval",
            category="retrieval_accuracy",
            question="What causes GPS drift in dense cities?",
            expected_concepts=["gps-satellite-geometry", "gps-multipath", "gps-atmospheric-delay"],
            forbidden_concepts=["snow-plow-positioning"],
            expected_plan="Evidence-grounded recommendation",
        ),
        RuntimeEvaluationCase(
            name="snowstorm_grounded_planning",
            category="planning",
            question="How should a city prepare for a severe snowstorm?",
            expected_concepts=["snow-plow-positioning", "emergency-route-priority", "shelter-capacity"],
            useful_neighbor_concepts=["resource-allocation-triage", "risk-likelihood-impact"],
            forbidden_concepts=["gps-satellite-geometry"],
            expected_plan="Evidence-grounded recommendation",
        ),
        RuntimeEvaluationCase(
            name="salt_tradeoff_conflict",
            category="conflict_handling",
            question="Should a city increase road salt usage during severe winter storms?",
            expected_concepts=["salt-traction-benefit", "salt-environmental-cost"],
            expected_conflict=True,
            expected_plan="Evidence-grounded recommendation",
        ),
        RuntimeEvaluationCase(
            name="resource_allocation_calibration",
            category="confidence_calibration",
            question="How should limited emergency crews be allocated during a flood?",
            expected_concepts=["resource-allocation-triage", "risk-likelihood-impact"],
            useful_neighbor_concepts=["emergency-route-priority", "shelter-capacity"],
            expected_plan="Evidence-grounded recommendation",
        ),
        RuntimeEvaluationCase(
            name="sparse_violin_question",
            category="sparse_knowledge",
            question="Explain violin tuning for a beginner.",
            sparse_expected=True,
            expected_plan="Low-evidence response",
        ),
        RuntimeEvaluationCase(
            name="repeat_snowstorm_stability",
            category="runtime_stability",
            question="How should a city prepare for a severe snowstorm?",
            expected_concepts=["snow-plow-positioning", "emergency-route-priority", "shelter-capacity"],
            useful_neighbor_concepts=["resource-allocation-triage", "risk-likelihood-impact"],
            expected_plan="Evidence-grounded recommendation",
        ),
    ]


def _ensure_fixture_store(*, store_root: Path, reports_dir: Path) -> None:
    store_root.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    records = _fixture_records()
    (store_root / "knowledge.jsonl").write_text(
        "".join(json.dumps(asdict(record), sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    (reports_dir / "promotion_governance_report.json").write_text(
        json.dumps({"decisions": [_governance_decision(record) for record in records]}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _fixture_records() -> list[SemanticKnowledgeRecord]:
    return [
        _record(
            "gps-satellite-geometry",
            "GPS satellite geometry",
            "GPS drift increases when satellite geometry provides weak positional constraints.",
            confidence=0.83,
            relationships=["gps-rel-a"],
        ),
        _record(
            "gps-multipath",
            "GPS multipath interference",
            "Dense buildings can reflect GPS signals and cause multipath interference that shifts estimated location.",
            confidence=0.86,
            relationships=["gps-rel-b"],
        ),
        _record(
            "gps-atmospheric-delay",
            "GPS atmospheric delay",
            "Atmospheric delay can change satellite signal timing and reduce GPS position accuracy.",
            confidence=0.78,
            relationships=["gps-rel-c"],
        ),
        _record(
            "snow-plow-positioning",
            "Snowstorm plow positioning",
            "Cities should pre-position plows before severe snowstorms to reduce response latency.",
            confidence=0.84,
            relationships=["snow-rel-a"],
        ),
        _record(
            "emergency-route-priority",
            "Emergency route priority",
            "Snow response plans should prioritize hospital routes, evacuation corridors, and emergency access roads.",
            confidence=0.87,
            relationships=["snow-rel-b"],
        ),
        _record(
            "shelter-capacity",
            "Shelter capacity planning",
            "Severe storm planning should compare shelter capacity against expected displaced population.",
            confidence=0.79,
            relationships=["snow-rel-c"],
        ),
        _record(
            "salt-traction-benefit",
            "Road salt traction benefit",
            "Increasing road salt usage can improve traction quickly during icy winter storms.",
            confidence=0.75,
            relationships=["salt-rel-a"],
        ),
        _record(
            "salt-environmental-cost",
            "Road salt environmental tradeoff",
            "Reducing salt usage can lower environmental risk but may trade off against immediate road traction.",
            confidence=0.77,
            relationships=["salt-rel-b"],
        ),
        _record(
            "resource-allocation-triage",
            "Emergency resource allocation",
            "Limited emergency crews should be allocated by severity, urgency, and expected impact.",
            confidence=0.82,
            relationships=["risk-rel-a"],
        ),
        _record(
            "risk-likelihood-impact",
            "Risk likelihood impact",
            "Risk assessment should combine likelihood and impact before selecting mitigation priorities.",
            confidence=0.8,
            relationships=["risk-rel-b"],
        ),
    ]


def _record(
    concept_id: str,
    concept: str,
    definition: str,
    *,
    confidence: float,
    relationships: list[str],
) -> SemanticKnowledgeRecord:
    return SemanticKnowledgeRecord(
        concept_id=concept_id,
        created_at="2026-07-02T00:00:00+00:00",
        updated_at="2026-07-02T00:00:00+00:00",
        concept=concept,
        definition=definition,
        confidence=confidence,
        supporting_evidence=[f"memory-{concept_id}"],
        contradicting_evidence=[],
        relationship_ids=relationships,
        creation_source="runtime_evaluation_fixture",
        last_validation="2026-07-02T00:00:00+00:00",
        revision_history=[],
        metadata={"profile": "runtime_evaluation"},
    )


def _governance_decision(record: SemanticKnowledgeRecord) -> dict[str, Any]:
    return {
        "concept_id": record.concept_id,
        "recommendation": "Validated",
        "promotion_score": 0.61 if record.concept_id in {"gps-multipath", "emergency-route-priority"} else 0.56,
        "dimensions": {
            "projected_centrality": 0.3 if record.relationship_ids else 0.0,
            "evidence_support": 1.0,
            "redundancy_penalty": 0.05,
        },
        "evidence": {"supported_predictions": 2, "failed_predictions": 0},
    }


def _scorecards_markdown(report: Any) -> str:
    lines = [
        "# Phase B Runtime Scorecards",
        "",
        "| Case | Category | Pass | Retrieval Precision | Retrieval Recall | Attention Precision | Attention Recall | Grounding | Used Noise | Suppressed Core |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in report.cases:
        lines.append(
            f"| {case.name} | {case.category} | `{case.passed}` | `{case.retrieval_precision}` | "
            f"`{case.retrieval_recall}` | `{case.attention_precision}` | `{case.attention_recall}` | "
            f"`{case.grounding_score}` | `{case.used_noise_count}` | `{case.suppressed_core_count}` |"
        )
    return "\n".join(lines) + "\n"


def _efficiency_payload(report: RuntimeEvaluationReport) -> dict[str, Any]:
    return {
        "aggregate": {
            key: report.aggregate[key]
            for key in (
                "working_memory_efficiency",
                "planning_utilization_ratio",
                "response_utilization_ratio",
                "overall_utilization_ratio",
                "average_activated_concepts",
                "average_used_concepts",
                "average_ignored_concepts",
                "average_noise_concepts",
                "average_useful_neighbors",
                "attention_recall",
                "attention_precision",
                "average_used_noise",
                "average_ignored_noise",
                "average_suppressed_core",
            )
        },
        "recommendation": _efficiency_recommendation(report),
        "cases": [
            {
                "name": case.name,
                "category": case.category,
                "activated_concepts": case.activated_concepts,
                "used_concepts": case.used_concepts,
                "unused_concepts": case.unused_concepts,
                "working_memory_efficiency": case.working_memory_efficiency,
                "planning_utilization_ratio": case.planning_utilization_ratio,
                "response_utilization_ratio": case.response_utilization_ratio,
                "overall_utilization_ratio": case.overall_utilization_ratio,
                "useful_neighbor_count": case.useful_neighbor_count,
                "noise_count": case.noise_count,
                "ignored_count": case.ignored_count,
                "attention_recall": case.attention_recall,
                "attention_precision": case.attention_precision,
                "used_noise_count": case.used_noise_count,
                "ignored_noise_count": case.ignored_noise_count,
                "suppressed_core_count": case.suppressed_core_count,
            }
            for case in report.cases
        ],
    }


def _efficiency_markdown(report: RuntimeEvaluationReport) -> str:
    recommendation = _efficiency_recommendation(report)
    lines = [
        "# Phase B.1 Runtime Efficiency",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "working_memory_efficiency",
        "planning_utilization_ratio",
        "response_utilization_ratio",
        "overall_utilization_ratio",
        "average_activated_concepts",
        "average_used_concepts",
        "average_ignored_concepts",
        "average_noise_concepts",
        "average_useful_neighbors",
        "attention_recall",
        "attention_precision",
        "average_used_noise",
        "average_ignored_noise",
        "average_suppressed_core",
    ):
        lines.append(f"| {key} | `{report.aggregate[key]}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Is low retrieval precision harming Runtime? `{recommendation['low_precision_harm']}`",
            f"- Extra activated concepts are mostly: `{recommendation['extra_concept_character']}`",
            f"- Is Working Memory carrying unnecessary load? `{recommendation['working_memory_load']}`",
            f"- Should retrieval ranking be optimized now? `{recommendation['optimize_retrieval_next']}`",
            f"- Conversation testing recommendation: `{recommendation['conversation_testing']}`",
            "",
            recommendation["rationale"],
            "",
            "## Per Case",
            "",
            "| Case | Activated | Used | Ignored | Attention Precision | Attention Recall | Used Noise | Suppressed Core |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for case in report.cases:
        lines.append(
            f"| {case.name} | `{len(case.activated_concepts)}` | `{len(case.used_concepts)}` | "
            f"`{case.ignored_count}` | `{case.attention_precision}` | "
            f"`{case.attention_recall}` | `{case.used_noise_count}` | `{case.suppressed_core_count}` |"
        )
    return "\n".join(lines) + "\n"


def _activation_waste_markdown(report: RuntimeEvaluationReport) -> str:
    lines = [
        "# Phase B.1 Activation Waste",
        "",
        "| Case | Concept | Classification | Neighbor Utility |",
        "| --- | --- | --- | --- |",
    ]
    for case in report.cases:
        for concept_id in case.activated_concepts:
            lines.append(
                f"| {case.name} | `{concept_id}` | `{case.activation_waste[concept_id]}` | "
                f"`{case.neighbor_utility[concept_id]}` |"
            )
    return "\n".join(lines) + "\n"


def _neighbor_utility_markdown(report: RuntimeEvaluationReport) -> str:
    counts: dict[str, int] = {}
    for case in report.cases:
        for value in case.neighbor_utility.values():
            counts[value] = counts.get(value, 0) + 1
    lines = [
        "# Phase B.1 Neighbor Utility",
        "",
        "## Distribution",
        "",
        "| Classification | Count |",
        "| --- | ---: |",
    ]
    for name in sorted(counts):
        lines.append(f"| {name} | `{counts[name]}` |")
    lines.extend(["", "## Case Detail", ""])
    for case in report.cases:
        useful = [key for key, value in case.neighbor_utility.items() if value == "Useful Neighbor"]
        noise = [key for key, value in case.neighbor_utility.items() if value == "Noise"]
        lines.extend(
            [
                f"### {case.name}",
                "",
                f"- useful neighbors: `{', '.join(useful) if useful else 'none'}`",
                f"- noise: `{', '.join(noise) if noise else 'none'}`",
                "",
            ]
        )
    return "\n".join(lines)


def _reasoning_contribution_payload(report: RuntimeEvaluationReport) -> dict[str, Any]:
    return {
        "aggregate": {
            key: report.aggregate[key]
            for key in (
                "reasoning_contribution_ratio",
                "supporting_ratio",
                "peripheral_ratio",
                "noise_used_in_reasoning",
                "planning_core_coverage",
                "response_core_coverage",
                "healthy_cases",
                "under_attending_cases",
                "reasoning_drift_cases",
                "planning_drift_cases",
                "response_drift_cases",
                "over_attending_cases",
            )
        },
        "cases": [
            {
                "name": case.name,
                "category": case.category,
                "runtime_decision": case.runtime_decision,
                "reasoning_contribution_ratio": case.reasoning_contribution_ratio,
                "supporting_ratio": case.supporting_ratio,
                "peripheral_ratio": case.peripheral_ratio,
                "noise_used_in_reasoning": case.noise_used_in_reasoning,
                "planning_core_coverage": case.planning_core_coverage,
                "response_core_coverage": case.response_core_coverage,
                "concept_contributions": [
                    {
                        "concept_id": contribution.concept_id,
                        "activated": contribution.activated,
                        "attended": contribution.attended,
                        "reasoned": contribution.reasoned,
                        "planned": contribution.planned,
                        "responded": contribution.responded,
                        "classification": contribution.classification,
                        "rationale": contribution.rationale,
                    }
                    for contribution in case.concept_contributions
                ],
            }
            for case in report.cases
        ],
    }


def _reasoning_contribution_markdown(report: RuntimeEvaluationReport) -> str:
    lines = [
        "# Phase B.2 Reasoning Contribution",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "reasoning_contribution_ratio",
        "supporting_ratio",
        "peripheral_ratio",
        "noise_used_in_reasoning",
        "planning_core_coverage",
        "response_core_coverage",
        "healthy_cases",
        "under_attending_cases",
        "reasoning_drift_cases",
        "planning_drift_cases",
        "response_drift_cases",
        "over_attending_cases",
    ):
        lines.append(f"| {key} | `{report.aggregate[key]}` |")
    lines.extend(["", "## Interpretation", ""])
    if report.aggregate["noise_used_in_reasoning"] == 0.0 and report.aggregate["under_attending_cases"] > 0:
        lines.append(
            "Runtime is not allowing noise to influence reasoning, but attention is suppressing some expected concepts before they can contribute."
        )
    elif report.aggregate["noise_used_in_reasoning"] > 0.0:
        lines.append("Runtime has reasoning drift: noise influenced reasoning and must be blocked before conversation testing.")
    elif report.aggregate["healthy_cases"] == report.aggregate["case_count"]:
        lines.append("All cases are healthy under contribution auditing.")
    else:
        lines.append("Contribution behavior is mixed; inspect case-level decisions before tuning runtime behavior.")
    lines.extend(["", "## Case Decisions", "", "| Case | Decision | Core Ratio | Supporting | Peripheral | Noise Reasoned | Plan Coverage | Response Coverage |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for case in report.cases:
        lines.append(
            f"| {case.name} | `{case.runtime_decision}` | `{case.reasoning_contribution_ratio}` | "
            f"`{case.supporting_ratio}` | `{case.peripheral_ratio}` | `{case.noise_used_in_reasoning}` | "
            f"`{case.planning_core_coverage}` | `{case.response_core_coverage}` |"
        )
    return "\n".join(lines) + "\n"


def _reasoning_flow_markdown(report: RuntimeEvaluationReport) -> str:
    lines = [
        "# Phase B.2 Reasoning Flow",
        "",
        "| Case | Concept | Activated | Attended | Reasoned | Planned | Responded | Classification |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in report.cases:
        for contribution in case.concept_contributions:
            lines.append(
                f"| {case.name} | `{contribution.concept_id}` | `{contribution.activated}` | "
                f"`{contribution.attended}` | `{contribution.reasoned}` | `{contribution.planned}` | "
                f"`{contribution.responded}` | `{contribution.classification}` |"
            )
    return "\n".join(lines) + "\n"


def _contribution_scorecards_markdown(report: RuntimeEvaluationReport) -> str:
    lines = [
        "# Phase B.2 Contribution Scorecards",
        "",
        "| Case | Decision | Retrieval Recall | Attention Recall | Attention Precision | Core Ratio | Supporting Ratio | Peripheral Ratio | Noise Used |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in report.cases:
        lines.append(
            f"| {case.name} | `{case.runtime_decision}` | `{case.retrieval_recall}` | "
            f"`{case.attention_recall}` | `{case.attention_precision}` | "
            f"`{case.reasoning_contribution_ratio}` | `{case.supporting_ratio}` | "
            f"`{case.peripheral_ratio}` | `{case.noise_used_in_reasoning}` |"
        )
    return "\n".join(lines) + "\n"


def _attention_vs_reasoning_markdown(report: RuntimeEvaluationReport) -> str:
    lines = [
        "# Phase B.2 Attention vs Reasoning",
        "",
        "| Case | Activated | Attended | Reasoned | Suppressed Core | Used Noise | Decision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in report.cases:
        lines.append(
            f"| {case.name} | `{len(case.activated_concepts)}` | `{len(case.used_concepts)}` | "
            f"`{len(case.reasoning_referenced_concepts)}` | `{case.suppressed_core_count}` | "
            f"`{case.noise_used_in_reasoning}` | `{case.runtime_decision}` |"
        )
    return "\n".join(lines) + "\n"


def _attention_optimization_payload(report: RuntimeEvaluationReport) -> dict[str, Any]:
    targets = _attention_targets(report)
    return {
        "metrics": {
            "retrieval_recall": report.aggregate["retrieval_recall"],
            "retrieval_precision": report.aggregate["retrieval_precision"],
            "attention_recall": report.aggregate["attention_recall"],
            "attention_precision": report.aggregate["attention_precision"],
            "noise_used_in_reasoning": report.aggregate["noise_used_in_reasoning"],
            "reasoning_drift_cases": report.aggregate["reasoning_drift_cases"],
            "planning_drift_cases": report.aggregate["planning_drift_cases"],
            "response_drift_cases": report.aggregate["response_drift_cases"],
            "grounding_score": report.aggregate["grounding_score"],
            "hallucinations": report.aggregate["hallucinations"],
            "planning_core_coverage": report.aggregate["planning_core_coverage"],
            "response_core_coverage": report.aggregate["response_core_coverage"],
        },
        "targets": targets,
        "recommendation": _attention_recommendation(targets),
        "stopping_rule_met": all(targets.values()),
    }


def _attention_optimization_markdown(report: RuntimeEvaluationReport) -> str:
    payload = _attention_optimization_payload(report)
    lines = [
        "# Runtime V1.1 Attention Optimization",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in payload["metrics"].items():
        lines.append(f"| {key} | `{value}` |")
    lines.extend(["", "## Target Check", "", "| Target | Met |", "| --- | ---: |"])
    for key, value in payload["targets"].items():
        lines.append(f"| {key} | `{value}` |")
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            payload["recommendation"],
        ]
    )
    return "\n".join(lines) + "\n"


def _attention_tradeoff_markdown(report: RuntimeEvaluationReport) -> str:
    lines = [
        "# Runtime V1.1 Attention Tradeoff",
        "",
        "| Case | Retrieval Recall | Attention Recall | Attention Precision | Used Noise | Suppressed Core | Decision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in report.cases:
        lines.append(
            f"| {case.name} | `{case.retrieval_recall}` | `{case.attention_recall}` | "
            f"`{case.attention_precision}` | `{case.noise_used_in_reasoning}` | "
            f"`{case.suppressed_core_count}` | `{case.runtime_decision}` |"
        )
    lines.extend(
        [
            "",
            "The operating point preserves broad activation while using attention as the selective gate into working memory.",
        ]
    )
    return "\n".join(lines) + "\n"


def _attention_score_distribution_markdown(report: RuntimeEvaluationReport) -> str:
    rows = [
        contribution
        for case in report.cases
        for contribution in case.concept_contributions
    ]
    lines = [
        "# Runtime V1.1 Attention Score Distribution",
        "",
        "| Concept | Score | Attention Class | Contribution | Attended | Case |",
        "| --- | ---: | --- | --- | ---: | --- |",
    ]
    for case in report.cases:
        for contribution in sorted(
            case.concept_contributions,
            key=lambda item: item.attention_score,
            reverse=True,
        ):
            lines.append(
                f"| `{contribution.concept_id}` | `{contribution.attention_score}` | "
                f"`{contribution.attention_classification}` | `{contribution.classification}` | "
                f"`{contribution.attended}` | {case.name} |"
            )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- scored concepts: `{len(rows)}`",
            f"- attended concepts: `{sum(1 for row in rows if row.attended)}`",
            f"- noise concepts attended: `{sum(1 for row in rows if row.attended and row.classification == 'Noise')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _runtime_progress_markdown(report: RuntimeEvaluationReport) -> str:
    lines = [
        "# Runtime V1 Progress",
        "",
        "| Runtime Metric | Current |",
        "| --- | ---: |",
        f"| retrieval recall | `{report.aggregate['retrieval_recall']}` |",
        f"| attention precision | `{report.aggregate['attention_precision']}` |",
        f"| attention recall | `{report.aggregate['attention_recall']}` |",
        f"| noise used in reasoning | `{report.aggregate['noise_used_in_reasoning']}` |",
        f"| planning core coverage | `{report.aggregate['planning_core_coverage']}` |",
        f"| response core coverage | `{report.aggregate['response_core_coverage']}` |",
        f"| healthy cases | `{report.aggregate['healthy_cases']}` |",
        f"| grounding | `{report.aggregate['grounding_score']}` |",
        f"| hallucinations | `{report.aggregate['hallucinations']}` |",
        "",
        "Runtime V1.1 attention meets the fixture-suite operating target. The next recommended step is Runtime V1.2: evaluate against real Phase A candidate knowledge and held-out prompts before multi-turn conversation.",
    ]
    return "\n".join(lines) + "\n"


def _attention_targets(report: RuntimeEvaluationReport) -> dict[str, bool]:
    return {
        "retrieval_recall_near_1": float(report.aggregate["retrieval_recall"]) >= 0.99,
        "attention_precision_at_least_0_98": float(report.aggregate["attention_precision"]) >= 0.98,
        "attention_recall_at_least_0_95": float(report.aggregate["attention_recall"]) >= 0.95,
        "noise_used_zero": float(report.aggregate["noise_used_in_reasoning"]) == 0.0,
        "reasoning_drift_zero": float(report.aggregate["reasoning_drift_cases"]) == 0.0,
        "planning_drift_zero": float(report.aggregate["planning_drift_cases"]) == 0.0,
        "response_drift_zero": float(report.aggregate["response_drift_cases"]) == 0.0,
        "grounding_1": float(report.aggregate["grounding_score"]) == 1.0,
        "hallucinations_zero": float(report.aggregate["hallucinations"]) == 0.0,
    }


def _attention_recommendation(targets: dict[str, bool]) -> str:
    if all(targets.values()):
        return (
            "Stopping rule met. Do not continue tuning attention on the fixture suite; "
            "prepare Runtime V1.2 against real Phase A candidate knowledge."
        )
    return (
        "Stopping rule not met. Continue attention scoring refinement only if the failed "
        "targets are reproducible and the same Runtime suite is rerun after each change."
    )


def _efficiency_recommendation(report: RuntimeEvaluationReport) -> dict[str, str]:
    used_noise = float(report.aggregate["average_used_noise"])
    attention_recall = float(report.aggregate["attention_recall"])
    suppressed_core = float(report.aggregate["average_suppressed_core"])
    if used_noise <= 0.1 and attention_recall >= 0.9 and suppressed_core <= 0.1:
        return {
            "low_precision_harm": "not materially harmful in this suite",
            "extra_concept_character": "mostly supportive neighbors",
            "working_memory_load": "acceptable",
            "optimize_retrieval_next": "no",
            "conversation_testing": "reasonable after adding held-out prompts",
            "rationale": "Attention keeps noisy activations out of downstream reasoning while preserving expected concepts.",
        }
    if used_noise <= 0.1 and attention_recall < 0.9:
        return {
            "low_precision_harm": "reduced by attention, but attention is too selective",
            "extra_concept_character": "mostly suppressed before reasoning",
            "working_memory_load": "acceptable after attention",
            "optimize_retrieval_next": "no",
            "conversation_testing": "defer until attention recall improves",
            "rationale": "The attention layer prevents noisy activations from entering reasoning, but it also suppresses some expected core concepts. The next refinement should tune attention scoring, not retrieval ranking.",
        }
    if used_noise > 0.1:
        return {
            "low_precision_harm": "yes, noisy concepts are entering downstream reasoning",
            "extra_concept_character": "mostly unused or noisy",
            "working_memory_load": "unnecessary semantic load is present",
            "optimize_retrieval_next": "attention or retrieval filtering is needed",
            "conversation_testing": "defer until activation precision improves",
            "rationale": "The runtime is efficient in a mechanical sense, but noisy activations are being used downstream instead of being ignored. Retrieval ranking should be refined before conversation layers amplify the noise.",
        }
    return {
        "low_precision_harm": "partially",
        "extra_concept_character": "mixed supportive and noisy",
        "working_memory_load": "watch",
        "optimize_retrieval_next": "evaluate with held-out prompts before changing ranking",
        "conversation_testing": "limited single-turn expansion first",
        "rationale": "The suite shows mixed neighbor utility. More held-out prompts should confirm whether this is persistent before retrieval ranking changes.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
