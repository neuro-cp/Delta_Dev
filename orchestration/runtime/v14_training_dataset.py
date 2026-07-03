from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14R_INVARIANT_FLAGS: dict[str, bool] = {
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "training_dataset_export_enabled": False,
    "dataset_write_enabled": False,
    "active_dataset_enabled": False,
    "automatic_training_allowed": False,
    "user_message_auto_training_enabled": False,
    "autonomous_learning_enabled": False,
    "background_learning_enabled": False,
    "canonical_write_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "provider_calls_enabled": False,
    "specialist_routing_enabled": False,
    "action_execution_enabled": False,
    "tool_calls_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class TrainingCandidateSourceType(str, Enum):
    RUNTIME_CONSOLE_PREVIEW = "runtime_console_preview"
    MANUAL_E2E_CASE = "manual_e2e_case"
    ANSWER_TRACE = "answer_trace"
    EVIDENCE_TRACE = "evidence_trace"
    FEEDBACK_RECORD = "feedback_record"
    CORRECTION_RECORD = "correction_record"
    REPLAY_REVIEW_RESULT = "replay_review_result"
    CONSOLIDATION_CANDIDATE = "consolidation_candidate"
    LEARNING_CANDIDATE = "learning_candidate"
    HYPOTHESIS_ARBITRATION_REPORT = "hypothesis_arbitration_report"
    SPECIALIST_MERGE_REPORT = "specialist_merge_report"
    UNKNOWN = "unknown"


class TrainingSafetyStatus(str, Enum):
    SAFE_FOR_FUTURE_REVIEW = "safe_for_future_review"
    INSUFFICIENT_PROVENANCE = "insufficient_provenance"
    PRIVACY_REVIEW_REQUIRED = "privacy_review_required"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    REJECT = "reject"


class TrainingDataApprovalType(str, Enum):
    HUMAN_REQUIRED = "human_required"
    ADMIN_REQUIRED = "admin_required"
    PRIVACY_REVIEW_REQUIRED = "privacy_review_required"
    SAFETY_REVIEW_REQUIRED = "safety_review_required"
    BLOCKED_NO_APPROVAL_POSSIBLE = "blocked_no_approval_possible"


class TrainingExportOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    DRAFT_ONLY = "draft_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REQUIRES_PRIVACY_REVIEW = "requires_privacy_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_OFFLINE_EVAL = "eligible_for_future_offline_eval"
    ELIGIBLE_FOR_FUTURE_EXPORT_REVIEW = "eligible_for_future_export_review"


class TrainingExportFormat(str, Enum):
    JSONL_PREVIEW = "jsonl_preview"
    CSV_PREVIEW = "csv_preview"
    EVAL_CASE_PREVIEW = "eval_case_preview"
    INSTRUCTION_TUNING_PREVIEW = "instruction_tuning_preview"
    PREFERENCE_PAIR_PREVIEW = "preference_pair_preview"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TrainingCandidateSource:
    source_id: str
    source_type: TrainingCandidateSourceType
    source_reference_id: str
    source_summary: str
    provenance_reference_ids: tuple[str, ...] = ()
    user_visible: bool = True
    contains_user_message: bool = False
    human_approval_required: bool = True
    active: bool = False
    training_enabled: bool = False
    automatic_training_allowed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "source_reference_id": self.source_reference_id,
            "source_summary": self.source_summary,
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "user_visible": self.user_visible,
            "contains_user_message": self.contains_user_message,
            "human_approval_required": self.human_approval_required,
            "active": self.active,
            "training_enabled": self.training_enabled,
            "automatic_training_allowed": self.automatic_training_allowed,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TrainingExampleDraft:
    draft_id: str
    source_id: str
    input_preview: str
    target_preview: str = ""
    instruction_preview: str = ""
    rationale: str = ""
    provenance_reference_ids: tuple[str, ...] = ()
    safety_notes: tuple[str, ...] = ()
    privacy_notes: tuple[str, ...] = ()
    lane_scope: tuple[str, ...] = ()
    active: bool = False
    approved: bool = False
    training_ready: bool = False
    exported: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "draft_id": self.draft_id,
            "source_id": self.source_id,
            "input_preview": self.input_preview,
            "target_preview": self.target_preview,
            "instruction_preview": self.instruction_preview,
            "rationale": self.rationale,
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "safety_notes": list(self.safety_notes),
            "privacy_notes": list(self.privacy_notes),
            "lane_scope": list(self.lane_scope),
            "active": self.active,
            "approved": self.approved,
            "training_ready": self.training_ready,
            "exported": self.exported,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TrainingDatasetCandidate:
    dataset_candidate_id: str
    draft_ids: tuple[str, ...] = ()
    dataset_purpose: str = ""
    dataset_scope: str = ""
    evidence_summary: str = ""
    exclusion_notes: tuple[str, ...] = ()
    required_reviews: tuple[str, ...] = ()
    active: bool = False
    approved: bool = False
    export_ready: bool = False
    exported: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_candidate_id": self.dataset_candidate_id,
            "draft_ids": list(self.draft_ids),
            "dataset_purpose": self.dataset_purpose,
            "dataset_scope": self.dataset_scope,
            "evidence_summary": self.evidence_summary,
            "exclusion_notes": list(self.exclusion_notes),
            "required_reviews": list(self.required_reviews),
            "active": self.active,
            "approved": self.approved,
            "export_ready": self.export_ready,
            "exported": self.exported,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TrainingDataSafetyReview:
    review_id: str
    target_reference_id: str
    safety_status: TrainingSafetyStatus
    privacy_status: TrainingSafetyStatus
    provenance_status: TrainingSafetyStatus
    risk_notes: tuple[str, ...] = ()
    required_before_export: bool = True
    blocked_by_invariant: bool = False
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "target_reference_id": self.target_reference_id,
            "safety_status": self.safety_status.value,
            "privacy_status": self.privacy_status.value,
            "provenance_status": self.provenance_status.value,
            "risk_notes": list(self.risk_notes),
            "required_before_export": self.required_before_export,
            "blocked_by_invariant": self.blocked_by_invariant,
            "approved": self.approved,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TrainingDataApprovalRequirement:
    requirement_id: str
    target_reference_id: str
    approval_type: TrainingDataApprovalType
    required_actor: str
    approval_reason: str
    satisfied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "target_reference_id": self.target_reference_id,
            "approval_type": self.approval_type.value,
            "required_actor": self.required_actor,
            "approval_reason": self.approval_reason,
            "satisfied": self.satisfied,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TrainingExportDecision:
    decision_id: str
    outcome: TrainingExportOutcome
    rationale: str
    dataset_candidate_id: str = ""
    draft_id: str = ""
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14R_INVARIANT_FLAGS))
    applied: bool = False
    approved: bool = False
    exported: bool = False
    training_triggered: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "dataset_candidate_id": self.dataset_candidate_id,
            "draft_id": self.draft_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "approved": self.approved,
            "exported": self.exported,
            "training_triggered": self.training_triggered,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TrainingExportPlan:
    export_plan_id: str
    dataset_candidate_id: str
    output_format: TrainingExportFormat
    output_location_preview: str = ""
    required_approval_ids: tuple[str, ...] = ()
    required_review_ids: tuple[str, ...] = ()
    export_steps: tuple[str, ...] = ()
    export_enabled: bool = False
    dataset_write_enabled: bool = False
    training_enabled: bool = False
    fine_tuning_enabled: bool = False
    weight_update_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "export_plan_id": self.export_plan_id,
            "dataset_candidate_id": self.dataset_candidate_id,
            "output_format": self.output_format.value,
            "output_location_preview": self.output_location_preview,
            "required_approval_ids": list(self.required_approval_ids),
            "required_review_ids": list(self.required_review_ids),
            "export_steps": list(self.export_steps),
            "export_enabled": self.export_enabled,
            "dataset_write_enabled": self.dataset_write_enabled,
            "training_enabled": self.training_enabled,
            "fine_tuning_enabled": self.fine_tuning_enabled,
            "weight_update_enabled": self.weight_update_enabled,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TrainingDatasetAuditRecord:
    audit_id: str
    draft_ids: tuple[str, ...] = ()
    dataset_candidate_id: str = ""
    decision_id: str = ""
    source_reference_ids: tuple[str, ...] = ()
    review_reference_ids: tuple[str, ...] = ()
    approval_requirement_ids: tuple[str, ...] = ()
    audit_summary: str = ""
    generated_for_review_only: bool = True
    persisted_to_active_dataset: bool = False
    exported: bool = False
    training_triggered: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "audit_id": self.audit_id,
            "dataset_candidate_id": self.dataset_candidate_id,
            "draft_ids": list(self.draft_ids),
            "decision_id": self.decision_id,
            "source_reference_ids": list(self.source_reference_ids),
            "review_reference_ids": list(self.review_reference_ids),
            "approval_requirement_ids": list(self.approval_requirement_ids),
            "audit_summary": self.audit_summary,
            "generated_for_review_only": self.generated_for_review_only,
            "persisted_to_active_dataset": self.persisted_to_active_dataset,
            "exported": self.exported,
            "training_triggered": self.training_triggered,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TrainingDatasetReportEntry:
    report_entry_id: str
    draft_summary: str
    review_summary: str
    approval_summary: str
    export_decision_summary: str
    audit_summary: str
    dataset_candidate_id: str = ""
    unresolved_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = "design offline evaluation harness"
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "report_entry_id": self.report_entry_id,
            "dataset_candidate_id": self.dataset_candidate_id,
            "draft_summary": self.draft_summary,
            "review_summary": self.review_summary,
            "approval_summary": self.approval_summary,
            "export_decision_summary": self.export_decision_summary,
            "audit_summary": self.audit_summary,
            "unresolved_gaps": list(self.unresolved_gaps),
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
        }


def create_training_candidate_source(
    *,
    source_type: TrainingCandidateSourceType,
    source_reference_id: str,
    source_summary: str,
    provenance_reference_ids: tuple[str, ...] = (),
    user_visible: bool = True,
    contains_user_message: bool = False,
    human_approval_required: bool = True,
) -> TrainingCandidateSource:
    source_id = _stable_id(
        "training-candidate-source",
        source_type.value,
        source_reference_id,
        source_summary,
        provenance_reference_ids,
        contains_user_message,
    )
    return TrainingCandidateSource(
        source_id=source_id,
        source_type=source_type,
        source_reference_id=source_reference_id,
        source_summary=source_summary.strip(),
        provenance_reference_ids=tuple(provenance_reference_ids),
        user_visible=user_visible,
        contains_user_message=contains_user_message,
        human_approval_required=human_approval_required,
    )


def create_training_example_draft(
    *,
    source: TrainingCandidateSource,
    input_preview: str,
    target_preview: str = "",
    instruction_preview: str = "",
    rationale: str = "",
    safety_notes: tuple[str, ...] = (),
    privacy_notes: tuple[str, ...] = (),
    lane_scope: tuple[str, ...] = (),
) -> TrainingExampleDraft:
    draft_id = _stable_id(
        "training-example-draft",
        source.source_id,
        input_preview,
        target_preview,
        instruction_preview,
        rationale,
    )
    return TrainingExampleDraft(
        draft_id=draft_id,
        source_id=source.source_id,
        input_preview=input_preview.strip(),
        target_preview=target_preview.strip(),
        instruction_preview=instruction_preview.strip(),
        rationale=rationale.strip(),
        provenance_reference_ids=source.provenance_reference_ids,
        safety_notes=tuple(safety_notes),
        privacy_notes=tuple(privacy_notes),
        lane_scope=tuple(lane_scope),
    )


def create_training_dataset_candidate(
    *,
    drafts: tuple[TrainingExampleDraft, ...],
    dataset_purpose: str,
    dataset_scope: str,
    evidence_summary: str = "",
    exclusion_notes: tuple[str, ...] = (),
    required_reviews: tuple[str, ...] = ("human_review", "privacy_review", "safety_review"),
) -> TrainingDatasetCandidate:
    draft_ids = tuple(sorted(draft.draft_id for draft in drafts))
    dataset_candidate_id = _stable_id("training-dataset-candidate", draft_ids, dataset_purpose, dataset_scope)
    return TrainingDatasetCandidate(
        dataset_candidate_id=dataset_candidate_id,
        draft_ids=draft_ids,
        dataset_purpose=dataset_purpose.strip(),
        dataset_scope=dataset_scope.strip(),
        evidence_summary=evidence_summary.strip(),
        exclusion_notes=tuple(exclusion_notes),
        required_reviews=tuple(required_reviews),
    )


def review_training_data_safety(
    target_reference_id: str,
    *,
    contains_user_message: bool = False,
    provenance_reference_ids: tuple[str, ...] = (),
    force_blocked: bool = False,
) -> TrainingDataSafetyReview:
    blocked = force_blocked or any(value is True for value in RUNTIME_V14R_INVARIANT_FLAGS.values())
    if blocked:
        safety = privacy = provenance = TrainingSafetyStatus.BLOCKED_BY_INVARIANT
        notes = ("training dataset invariant block",)
    elif not provenance_reference_ids:
        safety = TrainingSafetyStatus.HUMAN_REVIEW_REQUIRED
        privacy = TrainingSafetyStatus.PRIVACY_REVIEW_REQUIRED if contains_user_message else TrainingSafetyStatus.SAFE_FOR_FUTURE_REVIEW
        provenance = TrainingSafetyStatus.INSUFFICIENT_PROVENANCE
        notes = ("insufficient provenance for export",)
    elif contains_user_message:
        safety = TrainingSafetyStatus.HUMAN_REVIEW_REQUIRED
        privacy = TrainingSafetyStatus.PRIVACY_REVIEW_REQUIRED
        provenance = TrainingSafetyStatus.SAFE_FOR_FUTURE_REVIEW
        notes = ("user-visible message requires privacy and human review",)
    else:
        safety = privacy = provenance = TrainingSafetyStatus.SAFE_FOR_FUTURE_REVIEW
        notes = ("future review only; not approval",)
    review_id = _stable_id("training-data-safety-review", target_reference_id, safety.value, privacy.value, provenance.value, notes)
    return TrainingDataSafetyReview(
        review_id=review_id,
        target_reference_id=target_reference_id,
        safety_status=safety,
        privacy_status=privacy,
        provenance_status=provenance,
        risk_notes=notes,
        blocked_by_invariant=blocked,
    )


def create_training_data_approval_requirement(
    *,
    target_reference_id: str,
    approval_type: TrainingDataApprovalType,
    required_actor: str,
    approval_reason: str,
) -> TrainingDataApprovalRequirement:
    requirement_id = _stable_id("training-data-approval", target_reference_id, approval_type.value, required_actor, approval_reason)
    return TrainingDataApprovalRequirement(
        requirement_id=requirement_id,
        target_reference_id=target_reference_id,
        approval_type=approval_type,
        required_actor=required_actor,
        approval_reason=approval_reason.strip(),
    )


def decide_training_export(
    *,
    dataset_candidate: TrainingDatasetCandidate | None = None,
    draft: TrainingExampleDraft | None = None,
    safety_review: TrainingDataSafetyReview | None = None,
    approval_requirement: TrainingDataApprovalRequirement | None = None,
) -> TrainingExportDecision:
    dataset_candidate_id = dataset_candidate.dataset_candidate_id if dataset_candidate else ""
    draft_id = draft.draft_id if draft else ""
    if any(value is True for value in RUNTIME_V14R_INVARIANT_FLAGS.values()):
        outcome = TrainingExportOutcome.BLOCKED_BY_INVARIANT
        rationale = "training dataset invariants are not in the design-only baseline"
    elif safety_review and safety_review.blocked_by_invariant:
        outcome = TrainingExportOutcome.BLOCKED_BY_INVARIANT
        rationale = "safety review blocked by invariant"
    elif safety_review and safety_review.privacy_status == TrainingSafetyStatus.PRIVACY_REVIEW_REQUIRED:
        outcome = TrainingExportOutcome.REQUIRES_PRIVACY_REVIEW
        rationale = "privacy review is required before any future export review"
    elif approval_requirement and not approval_requirement.satisfied:
        outcome = TrainingExportOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "approval requirement is unsatisfied"
    elif dataset_candidate:
        outcome = TrainingExportOutcome.ELIGIBLE_FOR_FUTURE_OFFLINE_EVAL
        rationale = "candidate may be used for future offline evaluation review only"
    elif draft:
        outcome = TrainingExportOutcome.DRAFT_ONLY
        rationale = "draft exists for review only and is not training data"
    else:
        outcome = TrainingExportOutcome.DEFER
        rationale = "no draft or dataset candidate was supplied"
    decision_id = _stable_id("training-export-decision", dataset_candidate_id, draft_id, outcome.value, rationale)
    return TrainingExportDecision(
        decision_id=decision_id,
        dataset_candidate_id=dataset_candidate_id,
        draft_id=draft_id,
        outcome=outcome,
        rationale=rationale,
    )


def create_training_export_plan(
    *,
    dataset_candidate: TrainingDatasetCandidate,
    output_format: TrainingExportFormat = TrainingExportFormat.JSONL_PREVIEW,
    output_location_preview: str = "",
    required_approval_ids: tuple[str, ...] = (),
    required_review_ids: tuple[str, ...] = (),
    export_steps: tuple[str, ...] = (),
) -> TrainingExportPlan:
    export_plan_id = _stable_id(
        "training-export-plan",
        dataset_candidate.dataset_candidate_id,
        output_format.value,
        output_location_preview,
        required_approval_ids,
        required_review_ids,
        export_steps,
    )
    return TrainingExportPlan(
        export_plan_id=export_plan_id,
        dataset_candidate_id=dataset_candidate.dataset_candidate_id,
        output_format=output_format,
        output_location_preview=output_location_preview.strip(),
        required_approval_ids=tuple(required_approval_ids),
        required_review_ids=tuple(required_review_ids),
        export_steps=tuple(export_steps),
    )


def create_training_dataset_audit_record(
    *,
    drafts: tuple[TrainingExampleDraft, ...],
    dataset_candidate: TrainingDatasetCandidate | None = None,
    decision: TrainingExportDecision | None = None,
    source_reference_ids: tuple[str, ...] = (),
    review_reference_ids: tuple[str, ...] = (),
    approval_requirement_ids: tuple[str, ...] = (),
    audit_summary: str = "",
) -> TrainingDatasetAuditRecord:
    draft_ids = tuple(sorted(draft.draft_id for draft in drafts))
    dataset_candidate_id = dataset_candidate.dataset_candidate_id if dataset_candidate else ""
    decision_id = decision.decision_id if decision else ""
    audit_id = _stable_id("training-dataset-audit", dataset_candidate_id, draft_ids, decision_id, source_reference_ids, review_reference_ids, approval_requirement_ids)
    return TrainingDatasetAuditRecord(
        audit_id=audit_id,
        dataset_candidate_id=dataset_candidate_id,
        draft_ids=draft_ids,
        decision_id=decision_id,
        source_reference_ids=tuple(source_reference_ids),
        review_reference_ids=tuple(review_reference_ids),
        approval_requirement_ids=tuple(approval_requirement_ids),
        audit_summary=audit_summary.strip(),
    )


def create_training_dataset_report_entry(
    *,
    dataset_candidate: TrainingDatasetCandidate,
    drafts: tuple[TrainingExampleDraft, ...],
    safety_review: TrainingDataSafetyReview,
    approval_requirement: TrainingDataApprovalRequirement,
    decision: TrainingExportDecision,
    audit_record: TrainingDatasetAuditRecord,
    unresolved_gaps: tuple[str, ...] = (),
) -> TrainingDatasetReportEntry:
    report_entry_id = _stable_id(
        "training-dataset-report-entry",
        dataset_candidate.dataset_candidate_id,
        tuple(draft.draft_id for draft in drafts),
        decision.decision_id,
        audit_record.audit_id,
    )
    return TrainingDatasetReportEntry(
        report_entry_id=report_entry_id,
        dataset_candidate_id=dataset_candidate.dataset_candidate_id,
        draft_summary=f"{len(drafts)} draft(s), none approved/training-ready/exported",
        review_summary=f"{safety_review.safety_status.value}/{safety_review.privacy_status.value}/{safety_review.provenance_status.value}",
        approval_summary=f"{approval_requirement.approval_type.value}: satisfied={approval_requirement.satisfied}",
        export_decision_summary=f"{decision.outcome.value}: {decision.rationale}",
        audit_summary=audit_record.audit_summary,
        unresolved_gaps=tuple(unresolved_gaps),
    )


def validate_training_candidate_source_inert(source: TrainingCandidateSource) -> bool:
    return not any((source.active, source.training_enabled, source.automatic_training_allowed))


def validate_training_example_draft_inert(draft: TrainingExampleDraft) -> bool:
    return not any((draft.active, draft.approved, draft.training_ready, draft.exported))


def validate_training_dataset_candidate_inert(candidate: TrainingDatasetCandidate) -> bool:
    return not any((candidate.active, candidate.approved, candidate.export_ready, candidate.exported))


def validate_training_data_safety_review_not_approval(review: TrainingDataSafetyReview) -> bool:
    return review.required_before_export and review.approved is False


def validate_training_data_approval_requirement_unsatisfied(requirement: TrainingDataApprovalRequirement) -> bool:
    return requirement.satisfied is False


def validate_training_export_decision_inert(decision: TrainingExportDecision) -> bool:
    return (
        not any((decision.applied, decision.approved, decision.exported, decision.training_triggered))
        and all(value is False for value in decision.invariant_flags.values())
    )


def validate_training_export_plan_inert(plan: TrainingExportPlan) -> bool:
    return not any(
        (
            plan.export_enabled,
            plan.dataset_write_enabled,
            plan.training_enabled,
            plan.fine_tuning_enabled,
            plan.weight_update_enabled,
        )
    )


def validate_training_dataset_audit_record_review_only(record: TrainingDatasetAuditRecord) -> bool:
    return record.generated_for_review_only and not any(
        (record.persisted_to_active_dataset, record.exported, record.training_triggered)
    )


def validate_training_dataset_report_entry_review_only(entry: TrainingDatasetReportEntry) -> bool:
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
