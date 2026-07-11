"""Governed learning loop for DELTA 1.0.

The loop turns operator-approved objectives into assessment, practice,
evaluation, adaptation proposals, and reviewed lesson candidates. It does not
write canonical memory, run providers, execute code, or self-approve lessons.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now
from orchestration.runtime.delta_1_0_objective_engine import DevelopmentObjective


LOOP_STATES = (
    "OBJECTIVE_PENDING",
    "OBJECTIVE_APPROVED",
    "ASSESSING",
    "GAP_IDENTIFIED",
    "PLANNING_RESOURCES",
    "AWAITING_RESOURCE_APPROVAL",
    "PREPARING_PRACTICE",
    "EVALUATING",
    "ANALYZING_ERROR",
    "PROPOSING_ADAPTATION",
    "AWAITING_OPERATOR_DISPOSITION",
    "RETEST_PENDING",
    "COMPLETED",
    "PAUSED",
    "CANCELLED",
    "FAILED",
)

LESSON_STATUSES = ("PROPOSED", "APPROVED_NONCANONICAL", "REJECTED", "DEFERRED", "SUPERSEDED", "REVOKED")


@dataclass(frozen=True)
class CapabilityAssessment:
    assessment_id: str
    capability: str
    baseline_score: float
    gaps: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class PracticeArtifact:
    artifact_id: str
    artifact_type: str
    prompt_or_task: str
    expected_behavior: str
    produced_output_summary: str
    executable: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class LearningEvaluation:
    evaluation_id: str
    score: float
    passed: bool
    evidence_refs: tuple[str, ...]
    regressions: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ErrorAnalysis:
    analysis_id: str
    error_classes: tuple[str, ...]
    root_cause_hypothesis: str
    evidence_needed: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class AdaptationProposal:
    proposal_id: str
    adaptation_type: str
    summary: str
    expected_benefit: str
    required_review: tuple[str, ...]
    authority: str = "proposal_only"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class LessonCandidate:
    lesson_id: str
    summary: str
    status: str
    source_evidence: tuple[str, ...]
    operator_disposition_required: bool = True
    canonical: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class GovernedLearningLoop:
    loop_id: str
    objective_id: str
    state: str
    capability: str
    assessment: CapabilityAssessment | None = None
    practice_artifacts: tuple[PracticeArtifact, ...] = ()
    evaluations: tuple[LearningEvaluation, ...] = ()
    error_analysis: ErrorAnalysis | None = None
    adaptation_proposal: AdaptationProposal | None = None
    lesson_candidate: LessonCandidate | None = None
    created_at: str = field(default_factory=utc_now)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def create_learning_loop(objective: DevelopmentObjective, capability: str) -> GovernedLearningLoop:
    state = "OBJECTIVE_APPROVED" if objective.operator_approved else "OBJECTIVE_PENDING"
    return GovernedLearningLoop(
        loop_id=stable_id("delta10-learning-loop", objective.objective_id, capability),
        objective_id=objective.objective_id,
        state=state,
        capability=capability,
    )


def assess_capability(loop: GovernedLearningLoop, *, baseline_score: float, gaps: tuple[str, ...], evidence_refs: tuple[str, ...]) -> GovernedLearningLoop:
    assessment = CapabilityAssessment(
        assessment_id=stable_id("delta10-assessment", loop.loop_id, baseline_score, gaps),
        capability=loop.capability,
        baseline_score=baseline_score,
        gaps=gaps,
        evidence_refs=evidence_refs,
    )
    state = "GAP_IDENTIFIED" if gaps else "EVALUATING"
    return replace(loop, state=state, assessment=assessment)


def prepare_practice(loop: GovernedLearningLoop, task: str, expected_behavior: str) -> GovernedLearningLoop:
    artifact = PracticeArtifact(
        artifact_id=stable_id("delta10-practice", loop.loop_id, task, expected_behavior),
        artifact_type="python_module_practice",
        prompt_or_task=task,
        expected_behavior=expected_behavior,
        produced_output_summary="practice artifact prepared for operator review",
    )
    return replace(loop, state="PREPARING_PRACTICE", practice_artifacts=loop.practice_artifacts + (artifact,))


def evaluate_practice(loop: GovernedLearningLoop, *, score: float, evidence_refs: tuple[str, ...], regressions: tuple[str, ...] = ()) -> GovernedLearningLoop:
    evaluation = LearningEvaluation(
        evaluation_id=stable_id("delta10-learning-eval", loop.loop_id, score, evidence_refs, regressions),
        score=score,
        passed=score >= 0.8 and not regressions,
        evidence_refs=evidence_refs,
        regressions=regressions,
    )
    state = "ANALYZING_ERROR" if not evaluation.passed else "AWAITING_OPERATOR_DISPOSITION"
    return replace(loop, state=state, evaluations=loop.evaluations + (evaluation,))


def analyze_error(loop: GovernedLearningLoop, error_classes: tuple[str, ...]) -> GovernedLearningLoop:
    analysis = ErrorAnalysis(
        analysis_id=stable_id("delta10-error", loop.loop_id, error_classes),
        error_classes=error_classes,
        root_cause_hypothesis="bounded capability calibration needed",
        evidence_needed=("focused_regression", "operator_review", "before_after_comparison"),
    )
    proposal = AdaptationProposal(
        proposal_id=stable_id("delta10-adaptation", loop.loop_id, error_classes),
        adaptation_type="rule_or_benchmark_update",
        summary="Prepare a small calibration proposal; do not apply automatically.",
        expected_benefit="better behavior on observed gap without expanding authority",
        required_review=("operator_review", "focused_tests", "regression_checks"),
    )
    return replace(loop, state="PROPOSING_ADAPTATION", error_analysis=analysis, adaptation_proposal=proposal)


def propose_lesson(loop: GovernedLearningLoop, summary: str, evidence_refs: tuple[str, ...]) -> GovernedLearningLoop:
    lesson = LessonCandidate(
        lesson_id=stable_id("delta10-lesson", loop.loop_id, summary, evidence_refs),
        summary=summary,
        status="PROPOSED",
        source_evidence=evidence_refs,
    )
    return replace(loop, state="AWAITING_OPERATOR_DISPOSITION", lesson_candidate=lesson)


def dispose_lesson(loop: GovernedLearningLoop, status: str, *, operator_approved: bool) -> GovernedLearningLoop:
    if status not in LESSON_STATUSES:
        raise ValueError(f"unknown lesson status: {status}")
    if loop.lesson_candidate is None:
        return loop
    if status == "APPROVED_NONCANONICAL" and not operator_approved:
        return loop
    lesson = replace(loop.lesson_candidate, status=status)
    final_state = "COMPLETED" if status in ("APPROVED_NONCANONICAL", "REJECTED", "DEFERRED") else loop.state
    return replace(loop, state=final_state, lesson_candidate=lesson)


def governed_learning_report() -> dict[str, Any]:
    from orchestration.runtime.delta_1_0_objective_engine import propose_objective, transition_objective

    objective = propose_objective(
        "Improve Python module failure interpretation.",
        objective_type="CAPABILITY_IMPROVEMENT",
        origin="OPERATOR_CREATED",
        evidence_refs=("pilot-evidence-python-failure",),
    )
    objective, _ = transition_objective(objective, "AWAITING_OPERATOR_APPROVAL")
    objective, _ = transition_objective(objective, "APPROVED", operator_approved=True)
    loop = create_learning_loop(objective, "PYTHON_CODING_MODULE_V1")
    loop = assess_capability(loop, baseline_score=0.72, gaps=("import_failure_classification",), evidence_refs=("focused-test",))
    loop = prepare_practice(loop, "Classify ModuleNotFoundError fixture", "return import_failure without executing commands")
    loop = evaluate_practice(loop, score=0.76, evidence_refs=("practice-fixture",))
    loop = analyze_error(loop, ("classification_gap",))
    loop = propose_lesson(loop, "ModuleNotFoundError fixtures need import-path evidence before repair proposals.", ("practice-fixture",))
    return {
        "status": "GOVERNED_LEARNING_LOOP_READY_OPERATOR_REVIEW_REQUIRED",
        "sample_loop": loop,
        "lesson_statuses": LESSON_STATUSES,
        "safety": safety_metadata(),
    }
