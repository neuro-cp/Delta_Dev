from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14U_INVARIANT_FLAGS: dict[str, bool] = {
    "artifact_comparison_enabled": False,
    "comparison_run_enabled": False,
    "provider_calls_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "training_job_execution_enabled": False,
    "dataset_export_enabled": False,
    "active_dataset_write_enabled": False,
    "artifact_creation_enabled": False,
    "artifact_promotion_enabled": False,
    "promotion_enabled": False,
    "model_default_change_enabled": False,
    "model_b_default_changed": False,
    "upgraded_variant_active": False,
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


class ArtifactComparisonTargetType(str, Enum):
    MODEL_B_BASELINE_REFERENCE = "model_b_baseline_reference"
    UPGRADED_VARIANT_CANDIDATE = "upgraded_variant_candidate"
    TRAINED_ARTIFACT_CANDIDATE = "trained_artifact_candidate"
    RUNTIME_VARIANT_CANDIDATE = "runtime_variant_candidate"
    PROMPT_VARIANT_CANDIDATE = "prompt_variant_candidate"
    CONFIG_DELTA_CANDIDATE = "config_delta_candidate"
    UNKNOWN = "unknown"


class ArtifactComparisonCaseType(str, Enum):
    SIMPLE_QUESTION = "simple_question"
    CORRECTION_HANDLING = "correction_handling"
    UNCERTAINTY_HANDLING = "uncertainty_handling"
    EVIDENCE_USE = "evidence_use"
    MEMORY_SENSITIVE = "memory_sensitive"
    TRAINING_SENSITIVE = "training_sensitive"
    ACTION_SENSITIVE = "action_sensitive"
    SPECIALIST_GAP = "specialist_gap"
    UNSAFE_EXECUTION = "unsafe_execution"
    REGRESSION_GUARD = "regression_guard"
    UNKNOWN = "unknown"


class ArtifactComparisonMode(str, Enum):
    REVIEW_ONLY = "review_only"
    DETERMINISTIC_LOCAL_PREVIEW = "deterministic_local_preview"
    FIXED_CASE_SCORECARD_PLAN = "fixed_case_scorecard_plan"
    FUTURE_OFFLINE_COMPARISON = "future_offline_comparison"
    REJECT = "reject"


class ArtifactComparisonMetricType(str, Enum):
    CORRECTNESS_PROXY = "correctness_proxy"
    UNCERTAINTY_HANDLING = "uncertainty_handling"
    EVIDENCE_USE = "evidence_use"
    CORRECTION_HANDLING = "correction_handling"
    NO_MEMORY_MUTATION = "no_memory_mutation"
    NO_TRAINING_LEAKAGE = "no_training_leakage"
    NO_ACTION_EXECUTION = "no_action_execution"
    SAFETY_INVARIANT = "safety_invariant"
    REGRESSION_GUARD = "regression_guard"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class ArtifactRegressionType(str, Enum):
    CORRECTNESS_REGRESSION = "correctness_regression"
    UNCERTAINTY_REGRESSION = "uncertainty_regression"
    EVIDENCE_USE_REGRESSION = "evidence_use_regression"
    SAFETY_REGRESSION = "safety_regression"
    MUTATION_BOUNDARY_REGRESSION = "mutation_boundary_regression"
    ACTION_BOUNDARY_REGRESSION = "action_boundary_regression"
    TRAINING_BOUNDARY_REGRESSION = "training_boundary_regression"
    UNKNOWN = "unknown"


class ArtifactSafetyStatus(str, Enum):
    SAFE_FOR_FUTURE_REVIEW = "safe_for_future_review"
    INSUFFICIENT_CASES = "insufficient_cases"
    REGRESSION_DETECTED = "regression_detected"
    INVARIANT_FAILURE = "invariant_failure"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    REJECT = "reject"


class ArtifactComparisonDecisionOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    COMPARISON_ONLY = "comparison_only"
    REQUIRES_MORE_EVAL = "requires_more_eval"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_REGRESSION = "blocked_by_regression"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_PROMOTION_ROLLBACK_REVIEW = "eligible_for_future_promotion_rollback_review"


@dataclass(frozen=True)
class ArtifactComparisonTarget:
    comparison_target_id: str
    target_name: str
    target_type: ArtifactComparisonTargetType
    target_summary: str
    target_reference_id: str = ""
    baseline: bool = False
    candidate: bool = False
    model_b_reference: bool = False
    upgraded_variant_reference: bool = False
    active_runtime_target: bool = False
    promoted: bool = False
    default_change_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactComparisonCase:
    comparison_case_id: str
    case_type: ArtifactComparisonCaseType
    input_preview: str
    expected_behavior_summary: str
    safety_expectations: tuple[str, ...]
    metric_focus: tuple[str, ...]
    source_reference_ids: tuple[str, ...]
    training_example: bool = False
    exported: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactComparisonRunPlan:
    comparison_run_plan_id: str
    baseline_target_id: str
    candidate_target_ids: tuple[str, ...]
    comparison_case_ids: tuple[str, ...]
    metric_ids: tuple[str, ...]
    comparison_mode: ArtifactComparisonMode
    baseline_required: bool = True
    model_b_default_preserved: bool = True
    run_enabled: bool = False
    provider_calls_enabled: bool = False
    training_enabled: bool = False
    promotion_enabled: bool = False
    default_change_enabled: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactComparisonMetric:
    metric_id: str
    metric_name: str
    metric_type: ArtifactComparisonMetricType
    description: str
    higher_is_better: bool = True
    safety_critical: bool = False
    regression_sensitive: bool = True
    authoritative: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactComparisonResultDraft:
    result_id: str
    comparison_run_plan_id: str
    target_id: str
    comparison_case_id: str
    metric_id: str
    observed_summary: str
    rationale: str
    score: float | None = None
    pass_fail: bool | None = None
    generated_for_review_only: bool = True
    authoritative: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactComparisonScorecard:
    scorecard_id: str
    comparison_run_plan_id: str
    baseline_target_id: str
    candidate_target_id: str
    result_ids: tuple[str, ...]
    baseline_summary: str
    candidate_summary: str
    aggregate_comparison_summary: str
    candidate_appears_better: bool = False
    candidate_has_regressions: bool = True
    score_is_authoritative: bool = False
    promotion_recommended: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactRegressionFinding:
    regression_id: str
    candidate_target_id: str
    baseline_target_id: str
    regression_type: ArtifactRegressionType
    severity: str
    rationale: str
    comparison_case_id: str = ""
    metric_id: str = ""
    blocks_promotion: bool = True
    resolved: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactSafetyComparisonReview:
    safety_review_id: str
    comparison_run_plan_id: str
    baseline_target_id: str
    candidate_target_id: str
    safety_status: ArtifactSafetyStatus
    invariant_failures: tuple[str, ...]
    regression_ids: tuple[str, ...]
    required_before_promotion: bool = True
    approved: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactPromotionEligibilityReview:
    eligibility_review_id: str
    candidate_target_id: str
    baseline_target_id: str
    comparison_scorecard_id: str = ""
    safety_review_id: str = ""
    required_human_review: bool = True
    required_rollback_plan: bool = True
    required_additional_eval: bool = True
    eligible_for_future_promotion_review: bool = False
    promotion_approved: bool = False
    default_change_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactComparisonDecision:
    decision_id: str
    comparison_run_plan_id: str
    candidate_target_id: str
    outcome: ArtifactComparisonDecisionOutcome
    rationale: str
    invariant_status: str
    applied: bool = False
    promoted: bool = False
    default_changed: bool = False
    training_triggered: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ArtifactComparisonReportEntry:
    report_entry_id: str
    comparison_run_plan_id: str
    baseline_target_id: str
    candidate_target_id: str
    case_summary: str
    metric_summary: str
    scorecard_summary: str
    regression_summary: str
    safety_summary: str
    eligibility_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...]
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_artifact_comparison_target(
    *,
    target_name: str,
    target_type: ArtifactComparisonTargetType,
    target_summary: str,
    target_reference_id: str = "",
    baseline: bool = False,
    candidate: bool = False,
    model_b_reference: bool = False,
    upgraded_variant_reference: bool = False,
    active_runtime_target: bool = False,
) -> ArtifactComparisonTarget:
    return ArtifactComparisonTarget(
        comparison_target_id=_stable_id(
            "artifact-comparison-target",
            target_name,
            target_type.value,
            target_summary,
            target_reference_id,
            baseline,
            candidate,
            model_b_reference,
            upgraded_variant_reference,
            active_runtime_target,
        ),
        target_name=target_name,
        target_type=target_type,
        target_summary=target_summary,
        target_reference_id=target_reference_id,
        baseline=baseline,
        candidate=candidate,
        model_b_reference=model_b_reference,
        upgraded_variant_reference=upgraded_variant_reference,
        active_runtime_target=active_runtime_target,
    )


def create_artifact_comparison_case(
    *,
    case_type: ArtifactComparisonCaseType,
    input_preview: str,
    expected_behavior_summary: str,
    safety_expectations: tuple[str, ...],
    metric_focus: tuple[str, ...],
    source_reference_ids: tuple[str, ...],
) -> ArtifactComparisonCase:
    return ArtifactComparisonCase(
        comparison_case_id=_stable_id(
            "artifact-comparison-case",
            case_type.value,
            input_preview,
            expected_behavior_summary,
            safety_expectations,
            metric_focus,
            source_reference_ids,
        ),
        case_type=case_type,
        input_preview=input_preview,
        expected_behavior_summary=expected_behavior_summary,
        safety_expectations=tuple(safety_expectations),
        metric_focus=tuple(metric_focus),
        source_reference_ids=tuple(source_reference_ids),
    )


def create_artifact_comparison_metric(
    *,
    metric_name: str,
    metric_type: ArtifactComparisonMetricType,
    description: str,
    higher_is_better: bool = True,
    safety_critical: bool = False,
    regression_sensitive: bool = True,
) -> ArtifactComparisonMetric:
    return ArtifactComparisonMetric(
        metric_id=_stable_id(
            "artifact-comparison-metric",
            metric_name,
            metric_type.value,
            description,
            higher_is_better,
            safety_critical,
            regression_sensitive,
        ),
        metric_name=metric_name,
        metric_type=metric_type,
        description=description,
        higher_is_better=higher_is_better,
        safety_critical=safety_critical,
        regression_sensitive=regression_sensitive,
    )


def create_artifact_comparison_run_plan(
    *,
    baseline_target: ArtifactComparisonTarget,
    candidate_targets: tuple[ArtifactComparisonTarget, ...],
    cases: tuple[ArtifactComparisonCase, ...],
    metrics: tuple[ArtifactComparisonMetric, ...],
    comparison_mode: ArtifactComparisonMode,
) -> ArtifactComparisonRunPlan:
    return ArtifactComparisonRunPlan(
        comparison_run_plan_id=_stable_id(
            "artifact-comparison-run-plan",
            baseline_target.comparison_target_id,
            tuple(target.comparison_target_id for target in candidate_targets),
            tuple(case.comparison_case_id for case in cases),
            tuple(metric.metric_id for metric in metrics),
            comparison_mode.value,
        ),
        baseline_target_id=baseline_target.comparison_target_id,
        candidate_target_ids=tuple(target.comparison_target_id for target in candidate_targets),
        comparison_case_ids=tuple(case.comparison_case_id for case in cases),
        metric_ids=tuple(metric.metric_id for metric in metrics),
        comparison_mode=comparison_mode,
    )


def create_artifact_comparison_result_draft(
    *,
    run_plan: ArtifactComparisonRunPlan,
    target: ArtifactComparisonTarget,
    case: ArtifactComparisonCase,
    metric: ArtifactComparisonMetric,
    observed_summary: str,
    rationale: str,
    score: float | None = None,
    pass_fail: bool | None = None,
) -> ArtifactComparisonResultDraft:
    return ArtifactComparisonResultDraft(
        result_id=_stable_id(
            "artifact-comparison-result",
            run_plan.comparison_run_plan_id,
            target.comparison_target_id,
            case.comparison_case_id,
            metric.metric_id,
            observed_summary,
            rationale,
            score,
            pass_fail,
        ),
        comparison_run_plan_id=run_plan.comparison_run_plan_id,
        target_id=target.comparison_target_id,
        comparison_case_id=case.comparison_case_id,
        metric_id=metric.metric_id,
        observed_summary=observed_summary,
        rationale=rationale,
        score=score,
        pass_fail=pass_fail,
    )


def create_artifact_comparison_scorecard(
    *,
    run_plan: ArtifactComparisonRunPlan,
    baseline_target: ArtifactComparisonTarget,
    candidate_target: ArtifactComparisonTarget,
    result_ids: tuple[str, ...],
    baseline_summary: str,
    candidate_summary: str,
    aggregate_comparison_summary: str,
    candidate_appears_better: bool = False,
    candidate_has_regressions: bool = True,
) -> ArtifactComparisonScorecard:
    return ArtifactComparisonScorecard(
        scorecard_id=_stable_id(
            "artifact-comparison-scorecard",
            run_plan.comparison_run_plan_id,
            baseline_target.comparison_target_id,
            candidate_target.comparison_target_id,
            result_ids,
            baseline_summary,
            candidate_summary,
            aggregate_comparison_summary,
            candidate_appears_better,
            candidate_has_regressions,
        ),
        comparison_run_plan_id=run_plan.comparison_run_plan_id,
        baseline_target_id=baseline_target.comparison_target_id,
        candidate_target_id=candidate_target.comparison_target_id,
        result_ids=tuple(result_ids),
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
        aggregate_comparison_summary=aggregate_comparison_summary,
        candidate_appears_better=candidate_appears_better,
        candidate_has_regressions=candidate_has_regressions,
    )


def create_artifact_regression_finding(
    *,
    candidate_target: ArtifactComparisonTarget,
    baseline_target: ArtifactComparisonTarget,
    regression_type: ArtifactRegressionType,
    severity: str,
    rationale: str,
    comparison_case_id: str = "",
    metric_id: str = "",
    blocks_promotion: bool = True,
) -> ArtifactRegressionFinding:
    return ArtifactRegressionFinding(
        regression_id=_stable_id(
            "artifact-regression",
            candidate_target.comparison_target_id,
            baseline_target.comparison_target_id,
            regression_type.value,
            severity,
            rationale,
            comparison_case_id,
            metric_id,
            blocks_promotion,
        ),
        candidate_target_id=candidate_target.comparison_target_id,
        baseline_target_id=baseline_target.comparison_target_id,
        regression_type=regression_type,
        severity=severity,
        rationale=rationale,
        comparison_case_id=comparison_case_id,
        metric_id=metric_id,
        blocks_promotion=blocks_promotion,
    )


def create_artifact_safety_comparison_review(
    *,
    run_plan: ArtifactComparisonRunPlan,
    baseline_target: ArtifactComparisonTarget,
    candidate_target: ArtifactComparisonTarget,
    safety_status: ArtifactSafetyStatus,
    invariant_failures: tuple[str, ...] = (),
    regression_ids: tuple[str, ...] = (),
) -> ArtifactSafetyComparisonReview:
    return ArtifactSafetyComparisonReview(
        safety_review_id=_stable_id(
            "artifact-safety-review",
            run_plan.comparison_run_plan_id,
            baseline_target.comparison_target_id,
            candidate_target.comparison_target_id,
            safety_status.value,
            invariant_failures,
            regression_ids,
        ),
        comparison_run_plan_id=run_plan.comparison_run_plan_id,
        baseline_target_id=baseline_target.comparison_target_id,
        candidate_target_id=candidate_target.comparison_target_id,
        safety_status=safety_status,
        invariant_failures=tuple(invariant_failures),
        regression_ids=tuple(regression_ids),
    )


def create_artifact_promotion_eligibility_review(
    *,
    candidate_target: ArtifactComparisonTarget,
    baseline_target: ArtifactComparisonTarget,
    comparison_scorecard_id: str = "",
    safety_review_id: str = "",
    required_additional_eval: bool = True,
) -> ArtifactPromotionEligibilityReview:
    return ArtifactPromotionEligibilityReview(
        eligibility_review_id=_stable_id(
            "artifact-promotion-eligibility",
            candidate_target.comparison_target_id,
            baseline_target.comparison_target_id,
            comparison_scorecard_id,
            safety_review_id,
            required_additional_eval,
        ),
        candidate_target_id=candidate_target.comparison_target_id,
        baseline_target_id=baseline_target.comparison_target_id,
        comparison_scorecard_id=comparison_scorecard_id,
        safety_review_id=safety_review_id,
        required_additional_eval=required_additional_eval,
    )


def create_artifact_comparison_decision(
    *,
    run_plan: ArtifactComparisonRunPlan,
    candidate_target: ArtifactComparisonTarget,
    outcome: ArtifactComparisonDecisionOutcome,
    rationale: str,
    invariant_status: str,
) -> ArtifactComparisonDecision:
    return ArtifactComparisonDecision(
        decision_id=_stable_id(
            "artifact-comparison-decision",
            run_plan.comparison_run_plan_id,
            candidate_target.comparison_target_id,
            outcome.value,
            rationale,
            invariant_status,
        ),
        comparison_run_plan_id=run_plan.comparison_run_plan_id,
        candidate_target_id=candidate_target.comparison_target_id,
        outcome=outcome,
        rationale=rationale,
        invariant_status=invariant_status,
    )


def create_artifact_comparison_report_entry(
    *,
    run_plan: ArtifactComparisonRunPlan,
    baseline_target: ArtifactComparisonTarget,
    candidate_target: ArtifactComparisonTarget,
    case_summary: str,
    metric_summary: str,
    scorecard_summary: str,
    regression_summary: str,
    safety_summary: str,
    eligibility_summary: str,
    decision_summary: str,
    unresolved_gaps: tuple[str, ...],
    recommended_next_review_step: str,
) -> ArtifactComparisonReportEntry:
    return ArtifactComparisonReportEntry(
        report_entry_id=_stable_id(
            "artifact-comparison-report-entry",
            run_plan.comparison_run_plan_id,
            baseline_target.comparison_target_id,
            candidate_target.comparison_target_id,
            case_summary,
            metric_summary,
            scorecard_summary,
            regression_summary,
            safety_summary,
            eligibility_summary,
            decision_summary,
            unresolved_gaps,
            recommended_next_review_step,
        ),
        comparison_run_plan_id=run_plan.comparison_run_plan_id,
        baseline_target_id=baseline_target.comparison_target_id,
        candidate_target_id=candidate_target.comparison_target_id,
        case_summary=case_summary,
        metric_summary=metric_summary,
        scorecard_summary=scorecard_summary,
        regression_summary=regression_summary,
        safety_summary=safety_summary,
        eligibility_summary=eligibility_summary,
        decision_summary=decision_summary,
        unresolved_gaps=tuple(unresolved_gaps),
        recommended_next_review_step=recommended_next_review_step,
    )


def validate_model_b_target_is_baseline_reference(target: ArtifactComparisonTarget) -> bool:
    return (
        target.target_type == ArtifactComparisonTargetType.MODEL_B_BASELINE_REFERENCE
        and target.baseline
        and not target.candidate
        and target.model_b_reference
        and not target.promoted
        and not target.default_change_allowed
    )


def validate_upgraded_target_is_inactive_candidate(target: ArtifactComparisonTarget) -> bool:
    return (
        target.candidate
        and not target.baseline
        and target.upgraded_variant_reference
        and not target.active_runtime_target
        and not target.promoted
        and not target.default_change_allowed
    )


def validate_artifact_comparison_case_inert(case: ArtifactComparisonCase) -> bool:
    return not any((case.training_example, case.exported))


def validate_artifact_comparison_run_plan_inert(plan: ArtifactComparisonRunPlan) -> bool:
    return plan.baseline_required and plan.model_b_default_preserved and not any(
        (plan.run_enabled, plan.provider_calls_enabled, plan.training_enabled, plan.promotion_enabled, plan.default_change_enabled)
    )


def validate_artifact_comparison_metric_report_only(metric: ArtifactComparisonMetric) -> bool:
    return metric.authoritative is False


def validate_artifact_comparison_result_review_only(result: ArtifactComparisonResultDraft) -> bool:
    return result.generated_for_review_only and not any((result.authoritative, result.applied))


def validate_artifact_comparison_scorecard_report_only(scorecard: ArtifactComparisonScorecard) -> bool:
    return not any((scorecard.score_is_authoritative, scorecard.promotion_recommended))


def validate_artifact_regression_blocks_until_resolved(regression: ArtifactRegressionFinding) -> bool:
    return regression.blocks_promotion and regression.resolved is False


def validate_artifact_safety_review_not_approved(review: ArtifactSafetyComparisonReview) -> bool:
    return review.required_before_promotion and review.approved is False


def validate_artifact_promotion_review_not_approval(review: ArtifactPromotionEligibilityReview) -> bool:
    return not any((review.promotion_approved, review.default_change_allowed))


def validate_artifact_comparison_decision_inert(decision: ArtifactComparisonDecision) -> bool:
    return not any((decision.applied, decision.promoted, decision.default_changed, decision.training_triggered))


def validate_artifact_comparison_report_entry_review_only(entry: ArtifactComparisonReportEntry) -> bool:
    return entry.generated_for_review_only


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        elif isinstance(value, tuple):
            values[key] = [item.value if isinstance(item, Enum) else item for item in value]
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    normalized = "|".join(_normalize_part(part) for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, Enum):
        return part.value
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
