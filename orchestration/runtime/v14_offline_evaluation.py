from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14S_INVARIANT_FLAGS: dict[str, bool] = {
    "offline_evaluation_enabled": False,
    "evaluation_run_enabled": False,
    "provider_calls_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "training_dataset_export_enabled": False,
    "dataset_write_enabled": False,
    "promotion_enabled": False,
    "model_default_change_enabled": False,
    "model_b_default_changed": False,
    "active_runtime_variant_enabled": False,
    "canonical_write_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "specialist_routing_enabled": False,
    "action_execution_enabled": False,
    "tool_calls_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class EvaluationCaseType(str, Enum):
    RUNTIME_CONSOLE_CASE = "runtime_console_case"
    MANUAL_E2E_CASE = "manual_e2e_case"
    CORRECTION_CASE = "correction_case"
    UNCERTAINTY_CASE = "uncertainty_case"
    MEMORY_SENSITIVE_CASE = "memory_sensitive_case"
    TRAINING_SENSITIVE_CASE = "training_sensitive_case"
    ACTION_SENSITIVE_CASE = "action_sensitive_case"
    SPECIALIST_GAP_CASE = "specialist_gap_case"
    SAFETY_CASE = "safety_case"
    UNKNOWN = "unknown"


class EvaluationTargetType(str, Enum):
    MODEL_B_BASELINE_REFERENCE = "model_b_baseline_reference"
    RUNTIME_VARIANT_CANDIDATE = "runtime_variant_candidate"
    TRAINING_CANDIDATE = "training_candidate"
    DATASET_CANDIDATE = "dataset_candidate"
    PROMPT_VARIANT_CANDIDATE = "prompt_variant_candidate"
    CONTROLLED_LEARNING_CANDIDATE = "controlled_learning_candidate"
    UNKNOWN = "unknown"


class EvaluationMode(str, Enum):
    REVIEW_ONLY = "review_only"
    DETERMINISTIC_LOCAL_PREVIEW = "deterministic_local_preview"
    BASELINE_COMPARISON_PLAN = "baseline_comparison_plan"
    FUTURE_OFFLINE_RUN = "future_offline_run"
    REJECT = "reject"


class EvaluationMetricType(str, Enum):
    CORRECTNESS_PROXY = "correctness_proxy"
    UNCERTAINTY_HANDLING = "uncertainty_handling"
    EVIDENCE_USE = "evidence_use"
    CITATION_OR_PROVENANCE = "citation_or_provenance"
    SAFETY_INVARIANT = "safety_invariant"
    NO_MUTATION = "no_mutation"
    NO_SIDE_EFFECT = "no_side_effect"
    REGRESSION_GUARD = "regression_guard"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class EvaluationSafetyStatus(str, Enum):
    SAFE_FOR_FUTURE_REVIEW = "safe_for_future_review"
    INSUFFICIENT_CASES = "insufficient_cases"
    REGRESSION_DETECTED = "regression_detected"
    INVARIANT_FAILURE = "invariant_failure"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    REJECT = "reject"


class EvaluationBlockerType(str, Enum):
    INSUFFICIENT_CASES = "insufficient_cases"
    SAFETY_FAILURE = "safety_failure"
    REGRESSION_DETECTED = "regression_detected"
    MISSING_HUMAN_REVIEW = "missing_human_review"
    MISSING_ROLLBACK_PLAN = "missing_rollback_plan"
    MISSING_BASELINE_COMPARISON = "missing_baseline_comparison"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    case_type: EvaluationCaseType
    input_preview: str
    expected_behavior_summary: str
    safety_expectations: tuple[str, ...] = ()
    source_reference_ids: tuple[str, ...] = ()
    provenance_reference_ids: tuple[str, ...] = ()
    active: bool = False
    training_example: bool = False
    dataset_exported: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "case_type": self.case_type.value,
            "input_preview": self.input_preview,
            "expected_behavior_summary": self.expected_behavior_summary,
            "safety_expectations": list(self.safety_expectations),
            "source_reference_ids": list(self.source_reference_ids),
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "active": self.active,
            "training_example": self.training_example,
            "dataset_exported": self.dataset_exported,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationCaseSet:
    case_set_id: str
    case_ids: tuple[str, ...]
    purpose: str
    scope: str
    baseline_required: bool = True
    minimum_case_count: int = 1
    active: bool = False
    used_for_training: bool = False
    exported: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "case_set_id": self.case_set_id,
            "case_ids": list(self.case_ids),
            "purpose": self.purpose,
            "scope": self.scope,
            "baseline_required": self.baseline_required,
            "minimum_case_count": self.minimum_case_count,
            "active": self.active,
            "used_for_training": self.used_for_training,
            "exported": self.exported,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationTarget:
    target_id: str
    target_type: EvaluationTargetType
    target_reference_id: str
    target_summary: str
    baseline: bool = False
    candidate: bool = False
    active_runtime_target: bool = False
    promoted: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type.value,
            "target_reference_id": self.target_reference_id,
            "target_summary": self.target_summary,
            "baseline": self.baseline,
            "candidate": self.candidate,
            "active_runtime_target": self.active_runtime_target,
            "promoted": self.promoted,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationRunPlan:
    run_plan_id: str
    case_set_id: str
    target_ids: tuple[str, ...] = ()
    metric_spec_ids: tuple[str, ...] = ()
    evaluation_mode: EvaluationMode = EvaluationMode.REVIEW_ONLY
    required_before_training: bool = True
    required_before_promotion: bool = True
    run_enabled: bool = False
    provider_calls_enabled: bool = False
    training_enabled: bool = False
    promotion_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "run_plan_id": self.run_plan_id,
            "case_set_id": self.case_set_id,
            "target_ids": list(self.target_ids),
            "metric_spec_ids": list(self.metric_spec_ids),
            "evaluation_mode": self.evaluation_mode.value,
            "required_before_training": self.required_before_training,
            "required_before_promotion": self.required_before_promotion,
            "run_enabled": self.run_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "training_enabled": self.training_enabled,
            "promotion_enabled": self.promotion_enabled,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationMetricSpec:
    metric_id: str
    metric_name: str
    metric_type: EvaluationMetricType
    description: str
    higher_is_better: bool = True
    safety_critical: bool = False
    authoritative: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "metric_id": self.metric_id,
            "metric_name": self.metric_name,
            "metric_type": self.metric_type.value,
            "description": self.description,
            "higher_is_better": self.higher_is_better,
            "safety_critical": self.safety_critical,
            "authoritative": self.authoritative,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationResultDraft:
    result_id: str
    run_plan_id: str
    target_id: str
    case_id: str
    metric_id: str
    observed_summary: str
    score: float | None = None
    pass_fail: bool | None = None
    rationale: str = ""
    generated_for_review_only: bool = True
    authoritative: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "result_id": self.result_id,
            "run_plan_id": self.run_plan_id,
            "target_id": self.target_id,
            "case_id": self.case_id,
            "metric_id": self.metric_id,
            "observed_summary": self.observed_summary,
            "score": self.score,
            "pass_fail": self.pass_fail,
            "rationale": self.rationale,
            "generated_for_review_only": self.generated_for_review_only,
            "authoritative": self.authoritative,
            "applied": self.applied,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationScorecard:
    scorecard_id: str
    run_plan_id: str
    target_id: str
    result_ids: tuple[str, ...] = ()
    aggregate_summary: str = ""
    safety_failures: tuple[str, ...] = ()
    regression_notes: tuple[str, ...] = ()
    human_review_notes: tuple[str, ...] = ()
    score_is_authoritative: bool = False
    promotion_recommended: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "scorecard_id": self.scorecard_id,
            "run_plan_id": self.run_plan_id,
            "target_id": self.target_id,
            "result_ids": list(self.result_ids),
            "aggregate_summary": self.aggregate_summary,
            "safety_failures": list(self.safety_failures),
            "regression_notes": list(self.regression_notes),
            "human_review_notes": list(self.human_review_notes),
            "score_is_authoritative": self.score_is_authoritative,
            "promotion_recommended": self.promotion_recommended,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationSafetyReview:
    review_id: str
    run_plan_id: str
    target_id: str
    safety_status: EvaluationSafetyStatus
    invariant_failures: tuple[str, ...] = ()
    required_before_training: bool = True
    required_before_promotion: bool = True
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "run_plan_id": self.run_plan_id,
            "target_id": self.target_id,
            "safety_status": self.safety_status.value,
            "invariant_failures": list(self.invariant_failures),
            "required_before_training": self.required_before_training,
            "required_before_promotion": self.required_before_promotion,
            "approved": self.approved,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationComparisonReport:
    comparison_id: str
    baseline_target_id: str
    candidate_target_ids: tuple[str, ...] = ()
    scorecard_ids: tuple[str, ...] = ()
    comparison_summary: str = ""
    preferred_candidate_id: str = ""
    preferred_is_authoritative: bool = False
    default_change_recommended: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "comparison_id": self.comparison_id,
            "baseline_target_id": self.baseline_target_id,
            "candidate_target_ids": list(self.candidate_target_ids),
            "scorecard_ids": list(self.scorecard_ids),
            "comparison_summary": self.comparison_summary,
            "preferred_candidate_id": self.preferred_candidate_id,
            "preferred_is_authoritative": self.preferred_is_authoritative,
            "default_change_recommended": self.default_change_recommended,
            "applied": self.applied,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationPromotionBlocker:
    blocker_id: str
    target_id: str
    blocker_type: EvaluationBlockerType
    rationale: str
    required_resolution: str
    resolved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "blocker_id": self.blocker_id,
            "target_id": self.target_id,
            "blocker_type": self.blocker_type.value,
            "rationale": self.rationale,
            "required_resolution": self.required_resolution,
            "resolved": self.resolved,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvaluationHarnessReportEntry:
    report_entry_id: str
    run_plan_id: str
    case_set_summary: str
    target_summary: str
    metric_summary: str
    result_summary: str
    safety_summary: str
    comparison_summary: str
    blocker_summary: str
    recommended_next_review_step: str = "design tiny controlled training experiment"
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "report_entry_id": self.report_entry_id,
            "run_plan_id": self.run_plan_id,
            "case_set_summary": self.case_set_summary,
            "target_summary": self.target_summary,
            "metric_summary": self.metric_summary,
            "result_summary": self.result_summary,
            "safety_summary": self.safety_summary,
            "comparison_summary": self.comparison_summary,
            "blocker_summary": self.blocker_summary,
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
        }


def create_evaluation_case(
    *,
    case_type: EvaluationCaseType,
    input_preview: str,
    expected_behavior_summary: str,
    safety_expectations: tuple[str, ...] = (),
    source_reference_ids: tuple[str, ...] = (),
    provenance_reference_ids: tuple[str, ...] = (),
) -> EvaluationCase:
    case_id = _stable_id("evaluation-case", case_type.value, input_preview, expected_behavior_summary, safety_expectations)
    return EvaluationCase(
        case_id=case_id,
        case_type=case_type,
        input_preview=input_preview.strip(),
        expected_behavior_summary=expected_behavior_summary.strip(),
        safety_expectations=tuple(safety_expectations),
        source_reference_ids=tuple(source_reference_ids),
        provenance_reference_ids=tuple(provenance_reference_ids),
    )


def create_evaluation_case_set(
    *,
    cases: tuple[EvaluationCase, ...],
    purpose: str,
    scope: str,
    minimum_case_count: int = 1,
) -> EvaluationCaseSet:
    case_ids = tuple(sorted(case.case_id for case in cases))
    case_set_id = _stable_id("evaluation-case-set", case_ids, purpose, scope, minimum_case_count)
    return EvaluationCaseSet(
        case_set_id=case_set_id,
        case_ids=case_ids,
        purpose=purpose.strip(),
        scope=scope.strip(),
        minimum_case_count=minimum_case_count,
    )


def create_evaluation_target(
    *,
    target_type: EvaluationTargetType,
    target_reference_id: str,
    target_summary: str,
    baseline: bool = False,
    candidate: bool = False,
) -> EvaluationTarget:
    target_id = _stable_id("evaluation-target", target_type.value, target_reference_id, target_summary, baseline, candidate)
    return EvaluationTarget(
        target_id=target_id,
        target_type=target_type,
        target_reference_id=target_reference_id,
        target_summary=target_summary.strip(),
        baseline=baseline,
        candidate=candidate,
    )


def create_evaluation_metric_spec(
    *,
    metric_name: str,
    metric_type: EvaluationMetricType,
    description: str,
    higher_is_better: bool = True,
    safety_critical: bool = False,
) -> EvaluationMetricSpec:
    metric_id = _stable_id("evaluation-metric", metric_name, metric_type.value, description, higher_is_better, safety_critical)
    return EvaluationMetricSpec(
        metric_id=metric_id,
        metric_name=metric_name.strip(),
        metric_type=metric_type,
        description=description.strip(),
        higher_is_better=higher_is_better,
        safety_critical=safety_critical,
    )


def create_evaluation_run_plan(
    *,
    case_set: EvaluationCaseSet,
    targets: tuple[EvaluationTarget, ...],
    metric_specs: tuple[EvaluationMetricSpec, ...],
    evaluation_mode: EvaluationMode = EvaluationMode.REVIEW_ONLY,
) -> EvaluationRunPlan:
    target_ids = tuple(sorted(target.target_id for target in targets))
    metric_ids = tuple(sorted(metric.metric_id for metric in metric_specs))
    run_plan_id = _stable_id("evaluation-run-plan", case_set.case_set_id, target_ids, metric_ids, evaluation_mode.value)
    return EvaluationRunPlan(
        run_plan_id=run_plan_id,
        case_set_id=case_set.case_set_id,
        target_ids=target_ids,
        metric_spec_ids=metric_ids,
        evaluation_mode=evaluation_mode,
    )


def create_evaluation_result_draft(
    *,
    run_plan: EvaluationRunPlan,
    target: EvaluationTarget,
    case: EvaluationCase,
    metric: EvaluationMetricSpec,
    observed_summary: str,
    score: float | None = None,
    pass_fail: bool | None = None,
    rationale: str = "",
) -> EvaluationResultDraft:
    result_id = _stable_id("evaluation-result", run_plan.run_plan_id, target.target_id, case.case_id, metric.metric_id, observed_summary, score, pass_fail)
    return EvaluationResultDraft(
        result_id=result_id,
        run_plan_id=run_plan.run_plan_id,
        target_id=target.target_id,
        case_id=case.case_id,
        metric_id=metric.metric_id,
        observed_summary=observed_summary.strip(),
        score=score,
        pass_fail=pass_fail,
        rationale=rationale.strip(),
    )


def create_evaluation_scorecard(
    *,
    run_plan: EvaluationRunPlan,
    target: EvaluationTarget,
    results: tuple[EvaluationResultDraft, ...],
    aggregate_summary: str = "",
    safety_failures: tuple[str, ...] = (),
    regression_notes: tuple[str, ...] = (),
    human_review_notes: tuple[str, ...] = (),
) -> EvaluationScorecard:
    result_ids = tuple(sorted(result.result_id for result in results))
    scorecard_id = _stable_id("evaluation-scorecard", run_plan.run_plan_id, target.target_id, result_ids, aggregate_summary)
    return EvaluationScorecard(
        scorecard_id=scorecard_id,
        run_plan_id=run_plan.run_plan_id,
        target_id=target.target_id,
        result_ids=result_ids,
        aggregate_summary=aggregate_summary.strip(),
        safety_failures=tuple(safety_failures),
        regression_notes=tuple(regression_notes),
        human_review_notes=tuple(human_review_notes),
    )


def review_evaluation_safety(
    *,
    run_plan: EvaluationRunPlan,
    target: EvaluationTarget,
    case_set: EvaluationCaseSet,
    invariant_failures: tuple[str, ...] = (),
) -> EvaluationSafetyReview:
    if any(value is True for value in RUNTIME_V14S_INVARIANT_FLAGS.values()):
        status = EvaluationSafetyStatus.BLOCKED_BY_INVARIANT
        failures = tuple(invariant_failures) or ("invariant drift",)
    elif invariant_failures:
        status = EvaluationSafetyStatus.INVARIANT_FAILURE
        failures = tuple(invariant_failures)
    elif len(case_set.case_ids) < case_set.minimum_case_count:
        status = EvaluationSafetyStatus.INSUFFICIENT_CASES
        failures = ("insufficient cases",)
    else:
        status = EvaluationSafetyStatus.HUMAN_REVIEW_REQUIRED
        failures = ()
    review_id = _stable_id("evaluation-safety-review", run_plan.run_plan_id, target.target_id, status.value, failures)
    return EvaluationSafetyReview(
        review_id=review_id,
        run_plan_id=run_plan.run_plan_id,
        target_id=target.target_id,
        safety_status=status,
        invariant_failures=failures,
    )


def create_evaluation_comparison_report(
    *,
    baseline_target: EvaluationTarget,
    candidate_targets: tuple[EvaluationTarget, ...],
    scorecards: tuple[EvaluationScorecard, ...],
    comparison_summary: str,
    preferred_candidate_id: str = "",
) -> EvaluationComparisonReport:
    candidate_ids = tuple(sorted(target.target_id for target in candidate_targets))
    scorecard_ids = tuple(sorted(scorecard.scorecard_id for scorecard in scorecards))
    comparison_id = _stable_id("evaluation-comparison", baseline_target.target_id, candidate_ids, scorecard_ids, comparison_summary, preferred_candidate_id)
    return EvaluationComparisonReport(
        comparison_id=comparison_id,
        baseline_target_id=baseline_target.target_id,
        candidate_target_ids=candidate_ids,
        scorecard_ids=scorecard_ids,
        comparison_summary=comparison_summary.strip(),
        preferred_candidate_id=preferred_candidate_id,
    )


def create_evaluation_promotion_blocker(
    *,
    target_id: str,
    blocker_type: EvaluationBlockerType,
    rationale: str,
    required_resolution: str,
) -> EvaluationPromotionBlocker:
    blocker_id = _stable_id("evaluation-blocker", target_id, blocker_type.value, rationale, required_resolution)
    return EvaluationPromotionBlocker(
        blocker_id=blocker_id,
        target_id=target_id,
        blocker_type=blocker_type,
        rationale=rationale.strip(),
        required_resolution=required_resolution.strip(),
    )


def create_evaluation_harness_report_entry(
    *,
    run_plan: EvaluationRunPlan,
    case_set: EvaluationCaseSet,
    targets: tuple[EvaluationTarget, ...],
    metrics: tuple[EvaluationMetricSpec, ...],
    results: tuple[EvaluationResultDraft, ...],
    safety_review: EvaluationSafetyReview,
    comparison: EvaluationComparisonReport,
    blockers: tuple[EvaluationPromotionBlocker, ...],
) -> EvaluationHarnessReportEntry:
    report_entry_id = _stable_id(
        "evaluation-harness-report-entry",
        run_plan.run_plan_id,
        case_set.case_set_id,
        tuple(target.target_id for target in targets),
        tuple(metric.metric_id for metric in metrics),
        tuple(result.result_id for result in results),
        safety_review.review_id,
        comparison.comparison_id,
    )
    return EvaluationHarnessReportEntry(
        report_entry_id=report_entry_id,
        run_plan_id=run_plan.run_plan_id,
        case_set_summary=f"{len(case_set.case_ids)} case(s), not training/exported",
        target_summary=f"{len(targets)} target(s), none promoted/default-changing",
        metric_summary=f"{len(metrics)} metric(s), report-only",
        result_summary=f"{len(results)} draft result(s), none applied",
        safety_summary=f"{safety_review.safety_status.value}: approved={safety_review.approved}",
        comparison_summary=f"default_change_recommended={comparison.default_change_recommended}",
        blocker_summary=f"{len(blockers)} unresolved blocker(s)",
    )


def validate_evaluation_case_inert(case: EvaluationCase) -> bool:
    return not any((case.active, case.training_example, case.dataset_exported))


def validate_evaluation_case_set_inert(case_set: EvaluationCaseSet) -> bool:
    return not any((case_set.active, case_set.used_for_training, case_set.exported))


def validate_evaluation_target_inert(target: EvaluationTarget) -> bool:
    return not any((target.active_runtime_target, target.promoted))


def validate_evaluation_run_plan_inert(plan: EvaluationRunPlan) -> bool:
    return not any((plan.run_enabled, plan.provider_calls_enabled, plan.training_enabled, plan.promotion_enabled))


def validate_evaluation_metric_spec_report_only(metric: EvaluationMetricSpec) -> bool:
    return metric.authoritative is False


def validate_evaluation_result_draft_review_only(result: EvaluationResultDraft) -> bool:
    return result.generated_for_review_only and not any((result.authoritative, result.applied))


def validate_evaluation_scorecard_report_only(scorecard: EvaluationScorecard) -> bool:
    return not any((scorecard.score_is_authoritative, scorecard.promotion_recommended))


def validate_evaluation_safety_review_not_approval(review: EvaluationSafetyReview) -> bool:
    return review.required_before_training and review.required_before_promotion and review.approved is False


def validate_evaluation_comparison_report_inert(comparison: EvaluationComparisonReport) -> bool:
    return not any((comparison.preferred_is_authoritative, comparison.default_change_recommended, comparison.applied))


def validate_evaluation_promotion_blocker_unresolved(blocker: EvaluationPromotionBlocker) -> bool:
    return blocker.resolved is False


def validate_evaluation_harness_report_entry_review_only(entry: EvaluationHarnessReportEntry) -> bool:
    return entry.generated_for_review_only


def _stable_id(prefix: str, *parts: object) -> str:
    normalized = "|".join(_normalize_part(part) for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)
