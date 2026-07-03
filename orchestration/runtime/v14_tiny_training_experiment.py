from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14T_INVARIANT_FLAGS: dict[str, bool] = {
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "training_job_execution_enabled": False,
    "dataset_export_enabled": False,
    "active_dataset_write_enabled": False,
    "artifact_creation_enabled": False,
    "artifact_promotion_enabled": False,
    "model_default_change_enabled": False,
    "model_b_default_changed": False,
    "active_runtime_variant_enabled": False,
    "offline_evaluation_run_enabled": False,
    "provider_calls_enabled": False,
    "specialist_routing_enabled": False,
    "action_execution_enabled": False,
    "tool_calls_enabled": False,
    "canonical_write_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "autonomous_learning_enabled": False,
    "background_learning_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class TinyTrainingMethod(str, Enum):
    NO_TRAINING_REVIEW_ONLY = "no_training_review_only"
    LORA_PREVIEW = "lora_preview"
    SUPERVISED_FINETUNE_PREVIEW = "supervised_finetune_preview"
    PREFERENCE_TUNING_PREVIEW = "preference_tuning_preview"
    PROMPT_VARIANT_COMPARISON_PREVIEW = "prompt_variant_comparison_preview"
    UNKNOWN = "unknown"


class TinyTrainingArtifactType(str, Enum):
    MODEL_ADAPTER_PREVIEW = "model_adapter_preview"
    PROMPT_VARIANT_PREVIEW = "prompt_variant_preview"
    EVALUATION_REPORT_PREVIEW = "evaluation_report_preview"
    CONFIG_DELTA_PREVIEW = "config_delta_preview"
    UNKNOWN = "unknown"


class TinyTrainingExperimentOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    DESIGN_ONLY = "design_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REQUIRES_DATASET_EXPORT_REVIEW = "requires_dataset_export_review"
    REQUIRES_OFFLINE_EVAL_REVIEW = "requires_offline_eval_review"
    REQUIRES_ROLLBACK_PLAN = "requires_rollback_plan"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_ARTIFACT_COMPARISON_REVIEW = "eligible_for_future_artifact_comparison_review"


@dataclass(frozen=True)
class TinyTrainingExperimentCandidate:
    experiment_candidate_id: str
    experiment_summary: str
    purpose: str
    source_dataset_candidate_id: str = ""
    source_training_candidate_ids: tuple[str, ...] = field(default_factory=tuple)
    source_evaluation_case_set_ids: tuple[str, ...] = field(default_factory=tuple)
    provenance_reference_ids: tuple[str, ...] = field(default_factory=tuple)
    human_approval_required: bool = True
    safety_review_required: bool = True
    baseline_comparison_required: bool = True
    rollback_required: bool = True
    active: bool = False
    training_enabled: bool = False
    training_ready: bool = False
    approved: bool = False
    executed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingExperimentScope:
    scope_id: str
    experiment_candidate_id: str
    allowed_dataset_scope: str
    allowed_model_scope: str
    allowed_runtime_scope: str
    max_example_count: int | None = None
    max_training_steps: int | None = None
    offline_only: bool = True
    live_runtime_allowed: bool = False
    model_default_change_allowed: bool = False
    provider_calls_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingExperimentApprovalGate:
    gate_id: str
    experiment_candidate_id: str
    required_approval_ids: tuple[str, ...] = field(default_factory=tuple)
    required_safety_review_ids: tuple[str, ...] = field(default_factory=tuple)
    required_dataset_decision_ids: tuple[str, ...] = field(default_factory=tuple)
    required_evaluation_plan_ids: tuple[str, ...] = field(default_factory=tuple)
    human_approval_present: bool = False
    dataset_export_approved: bool = False
    safety_approved: bool = False
    evaluation_approved: bool = False
    gate_satisfied: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingRunPlan:
    training_run_plan_id: str
    experiment_candidate_id: str
    scope_id: str
    approval_gate_id: str
    training_method: TinyTrainingMethod
    dataset_reference_preview: str
    output_artifact_preview: str
    required_pre_eval_plan_ids: tuple[str, ...] = field(default_factory=tuple)
    required_post_eval_plan_ids: tuple[str, ...] = field(default_factory=tuple)
    training_enabled: bool = False
    fine_tuning_enabled: bool = False
    weight_update_enabled: bool = False
    job_execution_enabled: bool = False
    dataset_export_enabled: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingArtifactPlan:
    artifact_plan_id: str
    training_run_plan_id: str
    artifact_type: TinyTrainingArtifactType
    artifact_reference_preview: str
    baseline_reference: str
    comparison_required: bool = True
    rollback_required: bool = True
    artifact_created: bool = False
    promoted: bool = False
    active_runtime_artifact: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingEvaluationGate:
    evaluation_gate_id: str
    experiment_candidate_id: str
    required_metric_ids: tuple[str, ...]
    minimum_safety_status: str
    regression_blockers: tuple[str, ...] = field(default_factory=tuple)
    pre_training_case_set_id: str = ""
    post_training_case_set_id: str = ""
    baseline_target_id: str = ""
    pre_eval_passed: bool = False
    post_eval_passed: bool = False
    promotion_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingRollbackRequirement:
    rollback_requirement_id: str
    experiment_candidate_id: str
    rollback_strategy: str
    required_artifact_versioning: str
    required_baseline_reference: str
    rollback_test_required: bool = True
    rollback_ready: bool = False
    rollback_executed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingExperimentDecision:
    decision_id: str
    experiment_candidate_id: str
    outcome: TinyTrainingExperimentOutcome
    rationale: str
    invariant_status: str
    applied: bool = False
    training_triggered: bool = False
    artifact_created: bool = False
    promoted: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingExperimentAuditRecord:
    audit_id: str
    experiment_candidate_id: str
    source_reference_ids: tuple[str, ...]
    audit_summary: str
    run_plan_id: str = ""
    approval_gate_id: str = ""
    evaluation_gate_id: str = ""
    rollback_requirement_id: str = ""
    decision_id: str = ""
    generated_for_review_only: bool = True
    persisted_to_active_training_registry: bool = False
    training_triggered: bool = False
    artifact_created: bool = False
    promoted: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class TinyTrainingExperimentReportEntry:
    report_entry_id: str
    experiment_candidate_id: str
    scope_summary: str
    approval_summary: str
    run_plan_summary: str
    artifact_summary: str
    evaluation_summary: str
    rollback_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...]
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_tiny_training_experiment_candidate(
    *,
    experiment_summary: str,
    purpose: str,
    source_dataset_candidate_id: str = "",
    source_training_candidate_ids: tuple[str, ...] = (),
    source_evaluation_case_set_ids: tuple[str, ...] = (),
    provenance_reference_ids: tuple[str, ...] = (),
) -> TinyTrainingExperimentCandidate:
    return TinyTrainingExperimentCandidate(
        experiment_candidate_id=_stable_id(
            "tiny-training-experiment-candidate",
            experiment_summary,
            purpose,
            source_dataset_candidate_id,
            source_training_candidate_ids,
            source_evaluation_case_set_ids,
            provenance_reference_ids,
        ),
        experiment_summary=experiment_summary,
        purpose=purpose,
        source_dataset_candidate_id=source_dataset_candidate_id,
        source_training_candidate_ids=tuple(source_training_candidate_ids),
        source_evaluation_case_set_ids=tuple(source_evaluation_case_set_ids),
        provenance_reference_ids=tuple(provenance_reference_ids),
    )


def create_tiny_training_experiment_scope(
    *,
    candidate: TinyTrainingExperimentCandidate,
    allowed_dataset_scope: str,
    allowed_model_scope: str,
    allowed_runtime_scope: str,
    max_example_count: int | None = None,
    max_training_steps: int | None = None,
) -> TinyTrainingExperimentScope:
    return TinyTrainingExperimentScope(
        scope_id=_stable_id(
            "tiny-training-scope",
            candidate.experiment_candidate_id,
            allowed_dataset_scope,
            allowed_model_scope,
            allowed_runtime_scope,
            max_example_count,
            max_training_steps,
        ),
        experiment_candidate_id=candidate.experiment_candidate_id,
        allowed_dataset_scope=allowed_dataset_scope,
        allowed_model_scope=allowed_model_scope,
        allowed_runtime_scope=allowed_runtime_scope,
        max_example_count=max_example_count,
        max_training_steps=max_training_steps,
    )


def create_tiny_training_approval_gate(
    *,
    candidate: TinyTrainingExperimentCandidate,
    required_approval_ids: tuple[str, ...] = (),
    required_safety_review_ids: tuple[str, ...] = (),
    required_dataset_decision_ids: tuple[str, ...] = (),
    required_evaluation_plan_ids: tuple[str, ...] = (),
) -> TinyTrainingExperimentApprovalGate:
    return TinyTrainingExperimentApprovalGate(
        gate_id=_stable_id(
            "tiny-training-approval-gate",
            candidate.experiment_candidate_id,
            required_approval_ids,
            required_safety_review_ids,
            required_dataset_decision_ids,
            required_evaluation_plan_ids,
        ),
        experiment_candidate_id=candidate.experiment_candidate_id,
        required_approval_ids=tuple(required_approval_ids),
        required_safety_review_ids=tuple(required_safety_review_ids),
        required_dataset_decision_ids=tuple(required_dataset_decision_ids),
        required_evaluation_plan_ids=tuple(required_evaluation_plan_ids),
    )


def create_tiny_training_run_plan(
    *,
    candidate: TinyTrainingExperimentCandidate,
    scope: TinyTrainingExperimentScope,
    approval_gate: TinyTrainingExperimentApprovalGate,
    training_method: TinyTrainingMethod,
    dataset_reference_preview: str,
    output_artifact_preview: str,
    required_pre_eval_plan_ids: tuple[str, ...] = (),
    required_post_eval_plan_ids: tuple[str, ...] = (),
) -> TinyTrainingRunPlan:
    return TinyTrainingRunPlan(
        training_run_plan_id=_stable_id(
            "tiny-training-run-plan",
            candidate.experiment_candidate_id,
            scope.scope_id,
            approval_gate.gate_id,
            training_method.value,
            dataset_reference_preview,
            output_artifact_preview,
            required_pre_eval_plan_ids,
            required_post_eval_plan_ids,
        ),
        experiment_candidate_id=candidate.experiment_candidate_id,
        scope_id=scope.scope_id,
        approval_gate_id=approval_gate.gate_id,
        training_method=training_method,
        dataset_reference_preview=dataset_reference_preview,
        output_artifact_preview=output_artifact_preview,
        required_pre_eval_plan_ids=tuple(required_pre_eval_plan_ids),
        required_post_eval_plan_ids=tuple(required_post_eval_plan_ids),
    )


def create_tiny_training_artifact_plan(
    *,
    run_plan: TinyTrainingRunPlan,
    artifact_type: TinyTrainingArtifactType,
    artifact_reference_preview: str,
    baseline_reference: str,
) -> TinyTrainingArtifactPlan:
    return TinyTrainingArtifactPlan(
        artifact_plan_id=_stable_id(
            "tiny-training-artifact-plan",
            run_plan.training_run_plan_id,
            artifact_type.value,
            artifact_reference_preview,
            baseline_reference,
        ),
        training_run_plan_id=run_plan.training_run_plan_id,
        artifact_type=artifact_type,
        artifact_reference_preview=artifact_reference_preview,
        baseline_reference=baseline_reference,
    )


def create_tiny_training_evaluation_gate(
    *,
    candidate: TinyTrainingExperimentCandidate,
    required_metric_ids: tuple[str, ...],
    minimum_safety_status: str,
    regression_blockers: tuple[str, ...] = (),
    pre_training_case_set_id: str = "",
    post_training_case_set_id: str = "",
    baseline_target_id: str = "",
) -> TinyTrainingEvaluationGate:
    return TinyTrainingEvaluationGate(
        evaluation_gate_id=_stable_id(
            "tiny-training-evaluation-gate",
            candidate.experiment_candidate_id,
            required_metric_ids,
            minimum_safety_status,
            regression_blockers,
            pre_training_case_set_id,
            post_training_case_set_id,
            baseline_target_id,
        ),
        experiment_candidate_id=candidate.experiment_candidate_id,
        required_metric_ids=tuple(required_metric_ids),
        minimum_safety_status=minimum_safety_status,
        regression_blockers=tuple(regression_blockers),
        pre_training_case_set_id=pre_training_case_set_id,
        post_training_case_set_id=post_training_case_set_id,
        baseline_target_id=baseline_target_id,
    )


def create_tiny_training_rollback_requirement(
    *,
    candidate: TinyTrainingExperimentCandidate,
    rollback_strategy: str,
    required_artifact_versioning: str,
    required_baseline_reference: str,
) -> TinyTrainingRollbackRequirement:
    return TinyTrainingRollbackRequirement(
        rollback_requirement_id=_stable_id(
            "tiny-training-rollback-requirement",
            candidate.experiment_candidate_id,
            rollback_strategy,
            required_artifact_versioning,
            required_baseline_reference,
        ),
        experiment_candidate_id=candidate.experiment_candidate_id,
        rollback_strategy=rollback_strategy,
        required_artifact_versioning=required_artifact_versioning,
        required_baseline_reference=required_baseline_reference,
    )


def create_tiny_training_experiment_decision(
    *,
    candidate: TinyTrainingExperimentCandidate,
    outcome: TinyTrainingExperimentOutcome,
    rationale: str,
    invariant_status: str,
) -> TinyTrainingExperimentDecision:
    return TinyTrainingExperimentDecision(
        decision_id=_stable_id(
            "tiny-training-experiment-decision",
            candidate.experiment_candidate_id,
            outcome.value,
            rationale,
            invariant_status,
        ),
        experiment_candidate_id=candidate.experiment_candidate_id,
        outcome=outcome,
        rationale=rationale,
        invariant_status=invariant_status,
    )


def create_tiny_training_audit_record(
    *,
    candidate: TinyTrainingExperimentCandidate,
    source_reference_ids: tuple[str, ...],
    audit_summary: str,
    run_plan: TinyTrainingRunPlan | None = None,
    approval_gate: TinyTrainingExperimentApprovalGate | None = None,
    evaluation_gate: TinyTrainingEvaluationGate | None = None,
    rollback_requirement: TinyTrainingRollbackRequirement | None = None,
    decision: TinyTrainingExperimentDecision | None = None,
) -> TinyTrainingExperimentAuditRecord:
    return TinyTrainingExperimentAuditRecord(
        audit_id=_stable_id(
            "tiny-training-audit",
            candidate.experiment_candidate_id,
            source_reference_ids,
            audit_summary,
            run_plan.training_run_plan_id if run_plan else "",
            approval_gate.gate_id if approval_gate else "",
            evaluation_gate.evaluation_gate_id if evaluation_gate else "",
            rollback_requirement.rollback_requirement_id if rollback_requirement else "",
            decision.decision_id if decision else "",
        ),
        experiment_candidate_id=candidate.experiment_candidate_id,
        source_reference_ids=tuple(source_reference_ids),
        audit_summary=audit_summary,
        run_plan_id=run_plan.training_run_plan_id if run_plan else "",
        approval_gate_id=approval_gate.gate_id if approval_gate else "",
        evaluation_gate_id=evaluation_gate.evaluation_gate_id if evaluation_gate else "",
        rollback_requirement_id=rollback_requirement.rollback_requirement_id if rollback_requirement else "",
        decision_id=decision.decision_id if decision else "",
    )


def create_tiny_training_report_entry(
    *,
    candidate: TinyTrainingExperimentCandidate,
    scope_summary: str,
    approval_summary: str,
    run_plan_summary: str,
    artifact_summary: str,
    evaluation_summary: str,
    rollback_summary: str,
    decision_summary: str,
    unresolved_gaps: tuple[str, ...],
    recommended_next_review_step: str,
) -> TinyTrainingExperimentReportEntry:
    return TinyTrainingExperimentReportEntry(
        report_entry_id=_stable_id(
            "tiny-training-report-entry",
            candidate.experiment_candidate_id,
            scope_summary,
            approval_summary,
            run_plan_summary,
            artifact_summary,
            evaluation_summary,
            rollback_summary,
            decision_summary,
            unresolved_gaps,
            recommended_next_review_step,
        ),
        experiment_candidate_id=candidate.experiment_candidate_id,
        scope_summary=scope_summary,
        approval_summary=approval_summary,
        run_plan_summary=run_plan_summary,
        artifact_summary=artifact_summary,
        evaluation_summary=evaluation_summary,
        rollback_summary=rollback_summary,
        decision_summary=decision_summary,
        unresolved_gaps=tuple(unresolved_gaps),
        recommended_next_review_step=recommended_next_review_step,
    )


def validate_tiny_training_candidate_inert(candidate: TinyTrainingExperimentCandidate) -> bool:
    return not any((candidate.active, candidate.training_enabled, candidate.training_ready, candidate.approved, candidate.executed))


def validate_tiny_training_scope_offline_only(scope: TinyTrainingExperimentScope) -> bool:
    return scope.offline_only and not any((scope.live_runtime_allowed, scope.model_default_change_allowed, scope.provider_calls_allowed))


def validate_tiny_training_approval_gate_unsatisfied(gate: TinyTrainingExperimentApprovalGate) -> bool:
    return not any((gate.human_approval_present, gate.dataset_export_approved, gate.safety_approved, gate.evaluation_approved, gate.gate_satisfied))


def validate_tiny_training_run_plan_inert(plan: TinyTrainingRunPlan) -> bool:
    return not any((plan.training_enabled, plan.fine_tuning_enabled, plan.weight_update_enabled, plan.job_execution_enabled, plan.dataset_export_enabled))


def validate_tiny_training_artifact_plan_inert(plan: TinyTrainingArtifactPlan) -> bool:
    return not any((plan.artifact_created, plan.promoted, plan.active_runtime_artifact))


def validate_tiny_training_evaluation_gate_inert(gate: TinyTrainingEvaluationGate) -> bool:
    return not any((gate.pre_eval_passed, gate.post_eval_passed, gate.promotion_allowed))


def validate_tiny_training_rollback_requirement_inert(requirement: TinyTrainingRollbackRequirement) -> bool:
    return not any((requirement.rollback_ready, requirement.rollback_executed))


def validate_tiny_training_decision_inert(decision: TinyTrainingExperimentDecision) -> bool:
    return not any((decision.applied, decision.training_triggered, decision.artifact_created, decision.promoted))


def validate_tiny_training_audit_record_review_only(audit: TinyTrainingExperimentAuditRecord) -> bool:
    return audit.generated_for_review_only and not any(
        (audit.persisted_to_active_training_registry, audit.training_triggered, audit.artifact_created, audit.promoted)
    )


def validate_tiny_training_report_entry_review_only(entry: TinyTrainingExperimentReportEntry) -> bool:
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
