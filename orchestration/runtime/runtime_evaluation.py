from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from orchestration.runtime.runtime_v1_pipeline import RuntimeV1Pipeline, RuntimeV1Result


@dataclass(frozen=True)
class RuntimeEvaluationCase:
    name: str
    category: str
    question: str
    expected_concepts: list[str] = field(default_factory=list)
    useful_neighbor_concepts: list[str] = field(default_factory=list)
    forbidden_concepts: list[str] = field(default_factory=list)
    expected_conflict: bool = False
    sparse_expected: bool = False
    expected_plan: str | None = None


@dataclass(frozen=True)
class RuntimeConceptContribution:
    concept_id: str
    activated: bool
    attended: bool
    reasoned: bool
    planned: bool
    responded: bool
    classification: str
    rationale: str
    attention_score: float = 0.0
    attention_classification: str = "Unknown"


@dataclass(frozen=True)
class RuntimeCaseScorecard:
    name: str
    category: str
    question: str
    activated_concepts: list[str]
    retrieval_precision: float
    retrieval_recall: float
    missed_concepts: list[str]
    irrelevant_concepts: list[str]
    activation_confidence: float
    grounding_score: float
    unsupported_claims: int
    conflict_score: float
    confidence_calibration: float
    planning_score: float
    hallucination_count: int
    response_confidence: float
    used_concepts: list[str]
    unused_concepts: list[str]
    reasoning_referenced_concepts: list[str]
    planning_referenced_concepts: list[str]
    response_referenced_concepts: list[str]
    working_memory_efficiency: float
    planning_utilization_ratio: float
    response_utilization_ratio: float
    overall_utilization_ratio: float
    activation_waste: dict[str, str]
    neighbor_utility: dict[str, str]
    useful_neighbor_count: int
    noise_count: int
    ignored_count: int
    attention_recall: float
    attention_precision: float
    used_noise_count: int
    ignored_noise_count: int
    suppressed_core_count: int
    concept_contributions: list[RuntimeConceptContribution]
    reasoning_contribution_ratio: float
    supporting_ratio: float
    peripheral_ratio: float
    noise_used_in_reasoning: int
    planning_core_coverage: float
    response_core_coverage: float
    runtime_decision: str
    passed: bool
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RuntimeEvaluationReport:
    suite_name: str
    cases: list[RuntimeCaseScorecard]
    category_scores: dict[str, dict[str, float]]
    aggregate: dict[str, float]


class RuntimeEvaluationSuite:
    """
    Unit-test style cognition evaluator for Runtime V1.

    This measures the read-only runtime loop. It does not learn, validate,
    promote, write canonical knowledge, or modify candidate stores.
    """

    def __init__(
        self,
        *,
        suite_name: str = "runtime_v1_evaluation",
        cases: Iterable[RuntimeEvaluationCase] = (),
        activation_limit: int = 8,
    ) -> None:
        self.suite_name = suite_name
        self.cases = list(cases)
        self.activation_limit = activation_limit

    def run(
        self,
        *,
        store_root: str | Path,
        reports_dirs: tuple[str | Path, ...] = (),
    ) -> RuntimeEvaluationReport:
        pipeline = RuntimeV1Pipeline(
            store_root=store_root,
            reports_dirs=reports_dirs,
            activation_limit=self.activation_limit,
        )
        scores = [
            evaluate_runtime_case(case, pipeline.answer(case.question, cycle_id=f"eval:{case.name}"))
            for case in self.cases
        ]
        return RuntimeEvaluationReport(
            suite_name=self.suite_name,
            cases=scores,
            category_scores=_category_scores(scores),
            aggregate=_aggregate_scores(scores),
        )


def evaluate_runtime_case(case: RuntimeEvaluationCase, result: RuntimeV1Result) -> RuntimeCaseScorecard:
    activated = [item.concept_id for item in result.activation.items]
    expected = set(case.expected_concepts)
    activated_set = set(activated)
    forbidden = set(case.forbidden_concepts)
    relevant = activated_set & expected
    irrelevant = sorted((activated_set - expected) | (activated_set & forbidden))
    missed = sorted(expected - activated_set)

    if expected:
        precision = len(relevant) / max(1, len(activated_set))
        recall = len(relevant) / len(expected)
    else:
        precision = 1.0 if not activated else 0.0
        recall = 1.0 if not activated else 0.0

    activation_confidence = _mean([item.score for item in result.activation.items])
    unsupported_claims, hallucinations = _unsupported_claims(case, result)
    grounding = 1.0 if unsupported_claims == 0 else 0.0
    conflict_score = _conflict_score(case, result)
    calibration = _confidence_calibration(case, result)
    planning = 1.0 if not case.expected_plan or result.plan.recommended_option == case.expected_plan else 0.0
    efficiency = _efficiency_metrics(case, result)
    contribution = _contribution_metrics(case, result, efficiency)

    notes: list[str] = []
    if missed:
        notes.append(f"missed expected concepts: {', '.join(missed)}")
    if irrelevant:
        notes.append(f"irrelevant concepts activated: {', '.join(irrelevant)}")
    if unsupported_claims:
        notes.append(f"unsupported claims detected: {unsupported_claims}")
    if case.expected_conflict and conflict_score < 1.0:
        notes.append("expected conflict was not detected")
    if case.sparse_expected and result.activation.items:
        notes.append("sparse-knowledge case activated candidate knowledge")
    if efficiency["noise_count"]:
        notes.append(f"activation noise detected: {efficiency['noise_count']}")
    if efficiency["ignored_count"]:
        notes.append(f"ignored activations: {efficiency['ignored_count']}")

    passed = (
        precision >= 0.75
        and recall >= 0.75
        and grounding >= 1.0
        and conflict_score >= 1.0
        and calibration >= 0.75
        and planning >= 1.0
        and hallucinations == 0
    )

    return RuntimeCaseScorecard(
        name=case.name,
        category=case.category,
        question=case.question,
        activated_concepts=activated,
        retrieval_precision=round(precision, 4),
        retrieval_recall=round(recall, 4),
        missed_concepts=missed,
        irrelevant_concepts=irrelevant,
        activation_confidence=round(activation_confidence, 4),
        grounding_score=round(grounding, 4),
        unsupported_claims=unsupported_claims,
        conflict_score=round(conflict_score, 4),
        confidence_calibration=round(calibration, 4),
        planning_score=round(planning, 4),
        hallucination_count=hallucinations,
        response_confidence=round(result.response.confidence, 4),
        used_concepts=efficiency["used_concepts"],
        unused_concepts=efficiency["unused_concepts"],
        reasoning_referenced_concepts=efficiency["reasoning_referenced_concepts"],
        planning_referenced_concepts=efficiency["planning_referenced_concepts"],
        response_referenced_concepts=efficiency["response_referenced_concepts"],
        working_memory_efficiency=efficiency["working_memory_efficiency"],
        planning_utilization_ratio=efficiency["planning_utilization_ratio"],
        response_utilization_ratio=efficiency["response_utilization_ratio"],
        overall_utilization_ratio=efficiency["overall_utilization_ratio"],
        activation_waste=efficiency["activation_waste"],
        neighbor_utility=efficiency["neighbor_utility"],
        useful_neighbor_count=efficiency["useful_neighbor_count"],
        noise_count=efficiency["noise_count"],
        ignored_count=efficiency["ignored_count"],
        attention_recall=efficiency["attention_recall"],
        attention_precision=efficiency["attention_precision"],
        used_noise_count=efficiency["used_noise_count"],
        ignored_noise_count=efficiency["ignored_noise_count"],
        suppressed_core_count=efficiency["suppressed_core_count"],
        concept_contributions=contribution["concept_contributions"],
        reasoning_contribution_ratio=contribution["reasoning_contribution_ratio"],
        supporting_ratio=contribution["supporting_ratio"],
        peripheral_ratio=contribution["peripheral_ratio"],
        noise_used_in_reasoning=contribution["noise_used_in_reasoning"],
        planning_core_coverage=contribution["planning_core_coverage"],
        response_core_coverage=contribution["response_core_coverage"],
        runtime_decision=contribution["runtime_decision"],
        passed=passed,
        notes=notes,
    )


def runtime_report_to_json(report: RuntimeEvaluationReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True) + "\n"


def runtime_report_to_markdown(report: RuntimeEvaluationReport) -> str:
    lines = [
        f"# {report.suite_name}",
        "",
        "## Aggregate",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report.aggregate.items():
        lines.append(f"| {key} | `{value}` |")
    lines.extend(
        [
            "",
            "## Categories",
            "",
            "| Category | Pass Rate | Retrieval Precision | Retrieval Recall | Attention Precision | Attention Recall | Used Noise | Suppressed Core |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for category, values in sorted(report.category_scores.items()):
        lines.append(
            "| "
            + " | ".join(
                [
                    category,
                    f"`{values['pass_rate']}`",
                    f"`{values['retrieval_precision']}`",
                    f"`{values['retrieval_recall']}`",
                    f"`{values['attention_precision']}`",
                    f"`{values['attention_recall']}`",
                    f"`{values['average_used_noise']}`",
                    f"`{values['average_suppressed_core']}`",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Case Scorecards", ""])
    for case in report.cases:
        lines.extend(
            [
                f"### {case.name}",
                "",
                f"- category: `{case.category}`",
                f"- passed: `{case.passed}`",
                f"- activated: `{', '.join(case.activated_concepts) if case.activated_concepts else 'none'}`",
                f"- retrieval precision: `{case.retrieval_precision}`",
                f"- retrieval recall: `{case.retrieval_recall}`",
                f"- grounding: `{case.grounding_score}`",
                f"- conflict score: `{case.conflict_score}`",
                f"- confidence calibration: `{case.confidence_calibration}`",
                f"- planning score: `{case.planning_score}`",
                f"- working memory efficiency: `{case.working_memory_efficiency}`",
                f"- response utilization: `{case.response_utilization_ratio}`",
                f"- overall utilization: `{case.overall_utilization_ratio}`",
                f"- useful neighbors: `{case.useful_neighbor_count}`",
                f"- noise concepts: `{case.noise_count}`",
                f"- ignored concepts: `{case.ignored_count}`",
                f"- attention recall: `{case.attention_recall}`",
                f"- attention precision: `{case.attention_precision}`",
                f"- used noise: `{case.used_noise_count}`",
                f"- suppressed core: `{case.suppressed_core_count}`",
                f"- reasoning contribution ratio: `{case.reasoning_contribution_ratio}`",
                f"- supporting ratio: `{case.supporting_ratio}`",
                f"- peripheral ratio: `{case.peripheral_ratio}`",
                f"- noise used in reasoning: `{case.noise_used_in_reasoning}`",
                f"- runtime decision: `{case.runtime_decision}`",
                f"- hallucinations: `{case.hallucination_count}`",
            ]
        )
        if case.notes:
            lines.append(f"- notes: {'; '.join(case.notes)}")
        lines.append("")
    return "\n".join(lines)


def _efficiency_metrics(case: RuntimeEvaluationCase, result: RuntimeV1Result) -> dict[str, Any]:
    activated = [item.concept_id for item in result.activation.items]
    activated_set = set(activated)
    reasoning = set(result.reasoning.evidence_keys)
    planning = {
        key
        for option in result.plan.options
        for key in option.supporting_evidence
    }
    response = set(result.response.evidence_used)
    used = activated_set & (reasoning | planning | response)
    unused = activated_set - used
    expected = set(case.expected_concepts)
    useful_neighbors = set(case.useful_neighbor_concepts)
    forbidden = set(case.forbidden_concepts)

    waste: dict[str, str] = {}
    utility: dict[str, str] = {}
    for concept_id in activated:
        if concept_id in unused:
            waste[concept_id] = "IGNORED"
        elif concept_id in expected:
            waste[concept_id] = "USED"
        elif concept_id in useful_neighbors:
            waste[concept_id] = "SUPPORTED"
        else:
            waste[concept_id] = "USED"

        if concept_id in expected:
            utility[concept_id] = "Core Evidence"
        elif concept_id in useful_neighbors:
            utility[concept_id] = "Useful Neighbor"
        elif concept_id in forbidden:
            utility[concept_id] = "Noise"
        elif concept_id in unused:
            utility[concept_id] = "Noise"
        else:
            utility[concept_id] = "Noise"

    used_core = used & expected
    used_noise = {
        concept_id
        for concept_id, value in utility.items()
        if value == "Noise" and concept_id in used
    }
    ignored_noise = {
        concept_id
        for concept_id, value in utility.items()
        if value == "Noise" and concept_id in unused
    }
    suppressed_core = expected & unused
    return {
        "used_concepts": sorted(used),
        "unused_concepts": sorted(unused),
        "reasoning_referenced_concepts": sorted(reasoning & activated_set),
        "planning_referenced_concepts": sorted(planning & activated_set),
        "response_referenced_concepts": sorted(response & activated_set),
        "working_memory_efficiency": _ratio(len(used), len(activated)),
        "planning_utilization_ratio": _ratio(len(planning & activated_set), len(activated)),
        "response_utilization_ratio": _ratio(len(response & activated_set), len(activated)),
        "overall_utilization_ratio": _ratio(len(used), len(activated)),
        "activation_waste": waste,
        "neighbor_utility": utility,
        "useful_neighbor_count": sum(1 for value in utility.values() if value == "Useful Neighbor"),
        "noise_count": sum(1 for value in utility.values() if value == "Noise"),
        "ignored_count": len(unused),
        "attention_recall": _ratio(len(used_core), len(expected)) if expected else 1.0,
        "attention_precision": _ratio(len(used - used_noise), len(used)),
        "used_noise_count": len(used_noise),
        "ignored_noise_count": len(ignored_noise),
        "suppressed_core_count": len(suppressed_core),
    }


def _contribution_metrics(
    case: RuntimeEvaluationCase,
    result: RuntimeV1Result,
    efficiency: dict[str, Any],
) -> dict[str, Any]:
    activated = set(efficiency["activation_waste"].keys())
    attended = {item.key for item in result.working_memory.items}
    reasoned = set(result.reasoning.evidence_keys)
    planned = {
        key
        for option in result.plan.options
        for key in option.supporting_evidence
    }
    responded = set(result.response.evidence_used)
    attention_decisions = {
        decision.concept_id: decision
        for decision in result.attention.decisions
    }
    expected = set(case.expected_concepts)
    useful_neighbors = set(case.useful_neighbor_concepts)
    noise = {
        concept_id
        for concept_id, value in efficiency["neighbor_utility"].items()
        if value == "Noise"
    }

    contributions: list[RuntimeConceptContribution] = []
    for concept_id in sorted(activated):
        any_downstream = concept_id in reasoned or concept_id in planned or concept_id in responded
        if concept_id in noise:
            classification = "Noise"
            rationale = "concept is unrelated or forbidden for this evaluation case"
        elif concept_id in expected and any_downstream:
            classification = "Core"
            rationale = "expected concept influenced reasoning, planning, or response evidence"
        elif concept_id in useful_neighbors and any_downstream:
            classification = "Supporting"
            rationale = "useful neighboring concept contributed context or support"
        elif concept_id in attended:
            classification = "Peripheral"
            rationale = "concept reached working memory but did not materially influence downstream output"
        elif concept_id in expected:
            classification = "Peripheral"
            rationale = "expected concept was activated but suppressed before reasoning"
        elif concept_id in useful_neighbors:
            classification = "Peripheral"
            rationale = "useful neighbor was activated but not used"
        else:
            classification = "Peripheral"
            rationale = "concept remained outside downstream contribution"
        contributions.append(
            RuntimeConceptContribution(
                concept_id=concept_id,
                activated=True,
                attended=concept_id in attended,
                reasoned=concept_id in reasoned,
                planned=concept_id in planned,
                responded=concept_id in responded,
                classification=classification,
                rationale=rationale,
                attention_score=float(attention_decisions.get(concept_id).attention_score)
                if concept_id in attention_decisions
                else 0.0,
                attention_classification=attention_decisions.get(concept_id).classification
                if concept_id in attention_decisions
                else "Unknown",
            )
        )

    attended_count = max(1, len(attended))
    core_attended = [
        item
        for item in contributions
        if item.attended and item.classification == "Core"
    ]
    supporting_attended = [
        item
        for item in contributions
        if item.attended and item.classification == "Supporting"
    ]
    peripheral_attended = [
        item
        for item in contributions
        if item.attended and item.classification == "Peripheral"
    ]
    noise_reasoned = [
        item
        for item in contributions
        if item.reasoned and item.classification == "Noise"
    ]
    core_expected = expected or {item.concept_id for item in core_attended}
    planned_core = {item.concept_id for item in contributions if item.planned and item.concept_id in core_expected}
    responded_core = {item.concept_id for item in contributions if item.responded and item.concept_id in core_expected}
    decision = _runtime_decision(
        contributions=contributions,
        attended_count=len(attended),
        noise_reasoned=len(noise_reasoned),
        expected=expected,
        planned_core=planned_core,
        responded_core=responded_core,
    )
    return {
        "concept_contributions": contributions,
        "reasoning_contribution_ratio": _ratio(len(core_attended), attended_count),
        "supporting_ratio": _ratio(len(supporting_attended), attended_count),
        "peripheral_ratio": _ratio(len(peripheral_attended), attended_count),
        "noise_used_in_reasoning": len(noise_reasoned),
        "planning_core_coverage": _ratio(len(planned_core), len(core_expected)) if core_expected else 1.0,
        "response_core_coverage": _ratio(len(responded_core), len(core_expected)) if core_expected else 1.0,
        "runtime_decision": decision,
    }


def _runtime_decision(
    *,
    contributions: list[RuntimeConceptContribution],
    attended_count: int,
    noise_reasoned: int,
    expected: set[str],
    planned_core: set[str],
    responded_core: set[str],
) -> str:
    if noise_reasoned:
        return "Reasoning Drift"
    suppressed_expected = [
        item
        for item in contributions
        if item.concept_id in expected and not item.attended
    ]
    if suppressed_expected:
        return "Under-Attending"
    peripheral_attended = [
        item
        for item in contributions
        if item.attended and item.classification == "Peripheral"
    ]
    if attended_count and len(peripheral_attended) / attended_count > 0.35:
        return "Over-Attending"
    if expected and planned_core and len(planned_core) < len(expected):
        return "Planning Drift"
    if expected and responded_core and len(responded_core) < len(expected):
        return "Response Drift"
    return "Healthy"


def _unsupported_claims(case: RuntimeEvaluationCase, result: RuntimeV1Result) -> tuple[int, int]:
    if result.activation.items:
        return 0, 0
    if "not have enough activated candidate knowledge" in result.response.answer:
        return 0, 0
    if case.sparse_expected:
        return 1, 1
    return 1, 0


def _conflict_score(case: RuntimeEvaluationCase, result: RuntimeV1Result) -> float:
    if not case.expected_conflict:
        return 1.0
    if result.reasoning.conflicts:
        return 1.0
    answer = result.response.answer.lower()
    if "risk" in answer or "tradeoff" in answer or "competing" in answer:
        return 1.0
    return 0.0


def _confidence_calibration(case: RuntimeEvaluationCase, result: RuntimeV1Result) -> float:
    confidence = result.response.confidence
    if case.sparse_expected:
        return 1.0 if confidence <= 0.3 else 0.0
    if case.expected_concepts and result.activation.items:
        return 1.0 if 0.25 <= confidence <= 0.9 else 0.0
    return 0.75


def _category_scores(cases: list[RuntimeCaseScorecard]) -> dict[str, dict[str, float]]:
    categories = sorted({case.category for case in cases})
    scores: dict[str, dict[str, float]] = {}
    for category in categories:
        subset = [case for case in cases if case.category == category]
        scores[category] = {
            "pass_rate": round(sum(1 for case in subset if case.passed) / max(1, len(subset)), 4),
            "retrieval_precision": round(_mean([case.retrieval_precision for case in subset]), 4),
            "retrieval_recall": round(_mean([case.retrieval_recall for case in subset]), 4),
            "grounding_score": round(_mean([case.grounding_score for case in subset]), 4),
            "confidence_calibration": round(_mean([case.confidence_calibration for case in subset]), 4),
            "working_memory_efficiency": round(_mean([case.working_memory_efficiency for case in subset]), 4),
            "evidence_utilization": round(_mean([case.overall_utilization_ratio for case in subset]), 4),
            "average_activated_concepts": round(_mean([float(len(case.activated_concepts)) for case in subset]), 4),
            "average_used_concepts": round(_mean([float(len(case.used_concepts)) for case in subset]), 4),
            "average_ignored_concepts": round(_mean([float(case.ignored_count) for case in subset]), 4),
            "average_noise_concepts": round(_mean([float(case.noise_count) for case in subset]), 4),
            "average_useful_neighbors": round(_mean([float(case.useful_neighbor_count) for case in subset]), 4),
            "attention_recall": round(_mean([case.attention_recall for case in subset]), 4),
            "attention_precision": round(_mean([case.attention_precision for case in subset]), 4),
            "average_used_noise": round(_mean([float(case.used_noise_count) for case in subset]), 4),
            "average_suppressed_core": round(_mean([float(case.suppressed_core_count) for case in subset]), 4),
            "reasoning_contribution_ratio": round(_mean([case.reasoning_contribution_ratio for case in subset]), 4),
            "supporting_ratio": round(_mean([case.supporting_ratio for case in subset]), 4),
            "peripheral_ratio": round(_mean([case.peripheral_ratio for case in subset]), 4),
            "noise_used_in_reasoning": round(_mean([float(case.noise_used_in_reasoning) for case in subset]), 4),
            "planning_core_coverage": round(_mean([case.planning_core_coverage for case in subset]), 4),
            "response_core_coverage": round(_mean([case.response_core_coverage for case in subset]), 4),
        }
    return scores


def _aggregate_scores(cases: list[RuntimeCaseScorecard]) -> dict[str, float]:
    return {
        "case_count": float(len(cases)),
        "pass_rate": round(sum(1 for case in cases if case.passed) / max(1, len(cases)), 4),
        "retrieval_precision": round(_mean([case.retrieval_precision for case in cases]), 4),
        "retrieval_recall": round(_mean([case.retrieval_recall for case in cases]), 4),
        "grounding_score": round(_mean([case.grounding_score for case in cases]), 4),
        "conflict_score": round(_mean([case.conflict_score for case in cases]), 4),
        "confidence_calibration": round(_mean([case.confidence_calibration for case in cases]), 4),
        "planning_score": round(_mean([case.planning_score for case in cases]), 4),
        "hallucinations": float(sum(case.hallucination_count for case in cases)),
        "working_memory_efficiency": round(_mean([case.working_memory_efficiency for case in cases]), 4),
        "planning_utilization_ratio": round(_mean([case.planning_utilization_ratio for case in cases]), 4),
        "response_utilization_ratio": round(_mean([case.response_utilization_ratio for case in cases]), 4),
        "overall_utilization_ratio": round(_mean([case.overall_utilization_ratio for case in cases]), 4),
        "average_activated_concepts": round(_mean([float(len(case.activated_concepts)) for case in cases]), 4),
        "average_used_concepts": round(_mean([float(len(case.used_concepts)) for case in cases]), 4),
        "average_ignored_concepts": round(_mean([float(case.ignored_count) for case in cases]), 4),
        "average_noise_concepts": round(_mean([float(case.noise_count) for case in cases]), 4),
        "average_useful_neighbors": round(_mean([float(case.useful_neighbor_count) for case in cases]), 4),
        "attention_recall": round(_mean([case.attention_recall for case in cases]), 4),
        "attention_precision": round(_mean([case.attention_precision for case in cases]), 4),
        "average_used_noise": round(_mean([float(case.used_noise_count) for case in cases]), 4),
        "average_ignored_noise": round(_mean([float(case.ignored_noise_count) for case in cases]), 4),
        "average_suppressed_core": round(_mean([float(case.suppressed_core_count) for case in cases]), 4),
        "reasoning_contribution_ratio": round(_mean([case.reasoning_contribution_ratio for case in cases]), 4),
        "supporting_ratio": round(_mean([case.supporting_ratio for case in cases]), 4),
        "peripheral_ratio": round(_mean([case.peripheral_ratio for case in cases]), 4),
        "noise_used_in_reasoning": float(sum(case.noise_used_in_reasoning for case in cases)),
        "planning_core_coverage": round(_mean([case.planning_core_coverage for case in cases]), 4),
        "response_core_coverage": round(_mean([case.response_core_coverage for case in cases]), 4),
        "healthy_cases": float(sum(1 for case in cases if case.runtime_decision == "Healthy")),
        "under_attending_cases": float(sum(1 for case in cases if case.runtime_decision == "Under-Attending")),
        "reasoning_drift_cases": float(sum(1 for case in cases if case.runtime_decision == "Reasoning Drift")),
        "planning_drift_cases": float(sum(1 for case in cases if case.runtime_decision == "Planning Drift")),
        "response_drift_cases": float(sum(1 for case in cases if case.runtime_decision == "Response Drift")),
        "over_attending_cases": float(sum(1 for case in cases if case.runtime_decision == "Over-Attending")),
    }


def _mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0 if numerator == 0 else 0.0
    return round(numerator / denominator, 4)
