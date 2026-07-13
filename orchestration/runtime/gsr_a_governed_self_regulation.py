"""GSR-A inert governed self-regulation state model.

This module defines serializable contracts for governed self-regulating
cognition. It does not observe live runtime state, edit source, run sandboxes,
call providers, execute local models, write memory, schedule background work,
or authorize itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
import json
from pathlib import Path
from typing import Any, Mapping, get_args, get_origin

from orchestration.runtime.delta_1_0_common import safety_metadata as base_safety_metadata
from orchestration.runtime.delta_1_0_common import stable_id, utc_now


LIFECYCLE_STATES = (
    "idle",
    "objective_pending",
    "observing",
    "observation_review",
    "diagnosing",
    "diagnosis_review",
    "proposal_drafting",
    "proposal_review",
    "sandbox_authorized",
    "sandbox_evaluating",
    "evaluation_review",
    "application_authorized",
    "applying",
    "post_change_observation",
    "completed",
    "rejected",
    "suspended",
    "rolled_back",
    "deeper_design_required",
)

VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "idle": ("objective_pending", "suspended"),
    "objective_pending": ("observing", "rejected", "suspended"),
    "observing": ("observation_review", "suspended"),
    "observation_review": ("diagnosing", "rejected", "deeper_design_required", "suspended"),
    "diagnosing": ("diagnosis_review", "deeper_design_required", "suspended"),
    "diagnosis_review": ("proposal_drafting", "rejected", "deeper_design_required", "suspended"),
    "proposal_drafting": ("proposal_review", "suspended"),
    "proposal_review": ("sandbox_authorized", "rejected", "deeper_design_required", "suspended"),
    "sandbox_authorized": ("sandbox_evaluating", "suspended", "rolled_back"),
    "sandbox_evaluating": ("evaluation_review", "rolled_back", "suspended"),
    "evaluation_review": ("application_authorized", "completed", "rejected", "deeper_design_required", "suspended"),
    "application_authorized": ("applying", "suspended", "rolled_back"),
    "applying": ("post_change_observation", "rolled_back", "suspended"),
    "post_change_observation": ("completed", "deeper_design_required", "rolled_back", "suspended"),
    "completed": (),
    "rejected": (),
    "suspended": ("objective_pending", "rejected"),
    "rolled_back": (),
    "deeper_design_required": (),
}

EXECUTION_DENY_STATES = {"idle", "objective_pending", "observing", "observation_review", "diagnosing", "diagnosis_review", "proposal_drafting", "proposal_review", "evaluation_review", "completed", "rejected", "suspended", "rolled_back", "deeper_design_required"}
OPERATOR_AUTHORIZED = "OPERATOR_AUTHORIZED"
OPERATOR_CONTROLLED_AUTHORITY = "OPERATOR_CONTROLLED_AUTHORITY"

OBSERVATION_LEDGER_STATES = (
    "raw",
    "validated",
    "pending_review",
    "retained",
    "rejected",
    "duplicate",
    "corroborated",
    "superseded",
    "expired",
    "insufficient_evidence",
    "non_defect",
    "telemetry_only",
    "suspended",
    "diagnosis_review_eligible",
)

OBSERVATION_LEDGER_TERMINAL_STATES = {"rejected", "superseded", "expired", "suspended"}
OBSERVATION_DISPOSITIONS = (
    "retain",
    "reject",
    "mark_duplicate",
    "mark_corroborated",
    "supersede",
    "expire",
    "mark_insufficient_evidence",
    "mark_non_defect",
    "mark_telemetry_only",
    "suspend",
    "make_diagnosis_review_eligible",
)

OBSERVATION_RETENTION_POLICIES = (
    "retain_until_review",
    "retain_for_sequence_window",
    "retain_until_objective_closed",
    "manual_retention",
    "expire_after_sequence",
)

DIAGNOSIS_DISPOSITIONS = (
    "pending_review",
    "accepted_for_proposal_drafting",
    "rejected",
    "revise",
    "insufficient_evidence",
    "competing_hypothesis_unresolved",
    "non_defect",
    "duplicate_diagnosis",
    "suspended",
    "expired",
    "deeper_design_required",
)

DIAGNOSIS_PROPOSAL_BLOCKING_DISPOSITIONS = {
    "rejected",
    "insufficient_evidence",
    "competing_hypothesis_unresolved",
    "non_defect",
    "duplicate_diagnosis",
    "suspended",
    "expired",
    "deeper_design_required",
}

PROPOSAL_REVIEW_DISPOSITIONS = (
    "approve_for_future_sandbox_planning",
    "reject",
    "revise",
    "defer",
    "deeper_design_required",
    "suspend",
    "expire",
)


def safety_metadata() -> dict[str, bool]:
    safety = base_safety_metadata()
    safety.update({
        "local_model_inference_performed": False,
        "live_runtime_activation_performed": False,
        "scheduler_started": False,
        "self_approval_performed": False,
        "sandbox_evaluation_started": False,
        "application_performed": False,
    })
    return safety


@dataclass(frozen=True)
class DevelopmentObjective:
    objective_id: str
    operator_supplied_goal: str
    scope: tuple[str, ...]
    success_criteria: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    lifecycle_state: str
    operator_authorization_state: str
    creation_source: str
    sequence: int
    created_at: str
    parent_objective_id: str | None = None
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SelfObservation:
    observation_id: str
    objective_id: str
    source_subsystem: str
    observed_behavior: str
    expected_behavior: str
    evidence_references: tuple[str, ...]
    confidence: float
    uncertainty: str
    severity: str
    reproducibility: str
    user_visible: bool
    telemetry_only: bool
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DiagnosisCandidate:
    diagnosis_id: str
    linked_observations: tuple[str, ...]
    first_incorrect_transition: str
    suspected_mechanism: str
    competing_hypotheses: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    disconfirming_evidence: tuple[str, ...]
    confidence: float
    scope_estimate: str
    deeper_design_required: bool
    provisional: bool = True
    source_ledger_entry_id: str | None = None
    linked_evidence_references: tuple[str, ...] = ()
    unresolved_evidence: tuple[str, ...] = ()
    uncertainty: str = "unreviewed"
    severity: str = "medium"
    reproducibility: str = "unknown"
    affected_components: tuple[str, ...] = ()
    forbidden_components: tuple[str, ...] = ()
    operator_review_status: str = "pending_review"
    creation_authorization_id: str | None = None
    created_sequence: int = 0
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class RepairProposal:
    proposal_id: str
    diagnosis_id: str
    proposed_change: str
    files_or_components_in_scope: tuple[str, ...]
    forbidden_files_or_components: tuple[str, ...]
    predicted_effects: tuple[str, ...]
    risks: tuple[str, ...]
    rollback_strategy: tuple[str, ...]
    validation_plan: tuple[str, ...]
    operator_approval_requirement: str
    proposal_only_status: str = "PROPOSAL_ONLY"
    proposal_title: str = ""
    problem_statement: str = ""
    first_incorrect_transition: str = ""
    expected_user_visible_effects: tuple[str, ...] = ()
    regression_risks: tuple[str, ...] = ()
    governance_risks: tuple[str, ...] = ()
    safety_risks: tuple[str, ...] = ()
    alternatives_considered: tuple[str, ...] = ()
    reasons_alternatives_rejected: tuple[str, ...] = ()
    rollback_description: str = ""
    focused_test_requirements: tuple[str, ...] = ()
    adjacent_test_requirements: tuple[str, ...] = ()
    live_runtime_evidence_requirements: tuple[str, ...] = ()
    full_suite_policy: str = "not_required_for_proposal_only_review"
    provider_model_restrictions: tuple[str, ...] = ()
    memory_write_restrictions: tuple[str, ...] = ()
    source_mutation_prohibited: bool = True
    sandbox_execution_prohibited: bool = True
    application_prohibited: bool = True
    deeper_design_handling: str = "defer_to_design_milestone"
    operator_review_status: str = "pending_review"
    creation_sequence: int = 0
    expiration_sequence: int | None = None
    linked_evidence_references: tuple[str, ...] = ()
    linked_selected_hypothesis_id: str | None = None
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxEvaluationPlan:
    plan_id: str
    proposal_id: str
    disposable_workspace: str
    test_selection: tuple[str, ...]
    live_runtime_evidence_requirements: tuple[str, ...]
    provider_model_restrictions: tuple[str, ...]
    memory_write_restrictions: tuple[str, ...]
    success_criteria: tuple[str, ...]
    failure_criteria: tuple[str, ...]
    rollback_proof: tuple[str, ...]
    artifact_retention_policy: str
    planning_authorization_id: str = ""
    repository_snapshot_description: str = ""
    files_or_components_in_scope: tuple[str, ...] = ()
    forbidden_files_or_components: tuple[str, ...] = ()
    allowed_tool_classes: tuple[str, ...] = ()
    forbidden_tool_classes: tuple[str, ...] = ()
    allowed_command_categories: tuple[str, ...] = ()
    forbidden_command_categories: tuple[str, ...] = ()
    focused_test_requirements: tuple[str, ...] = ()
    adjacent_test_requirements: tuple[str, ...] = ()
    network_restrictions: tuple[str, ...] = ()
    source_mutation_restrictions: tuple[str, ...] = ()
    rollback_proof_requirements: tuple[str, ...] = ()
    cleanup_proof_requirements: tuple[str, ...] = ()
    execution_budget_metadata: tuple[str, ...] = ()
    module_attachment_plan_id: str | None = None
    plan_only_status: str = "PLAN_ONLY"
    operator_review_status: str = "pending_review"
    creation_sequence: int = 0
    expiration_sequence: int | None = None
    workspace_creation_prohibited: bool = True
    sandbox_execution_prohibited: bool = True
    command_execution_prohibited: bool = True
    source_mutation_prohibited: bool = True
    module_loading_prohibited: bool = True
    application_prohibited: bool = True
    persistence_prohibited: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    proposal_id: str
    operator_authority: str
    decision: str
    allowed_scope: tuple[str, ...]
    one_shot: bool
    expires_after_sequence: int | None
    attached_conditions: tuple[str, ...]
    audit_rationale: str
    consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class RegulationCycleState:
    cycle_id: str
    objective_id: str
    lifecycle_state: str
    sequence: int
    observation_ids: tuple[str, ...] = ()
    diagnosis_ids: tuple[str, ...] = ()
    proposal_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    deeper_design_required: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class TransitionResult:
    accepted: bool
    from_state: str
    to_state: str
    reason: str
    state: RegulationCycleState
    execution_allowed: bool


@dataclass(frozen=True)
class ObservationEvidence:
    evidence_id: str
    objective_id: str
    source_subsystem: str
    source_type: str
    source_reference: str
    observed_input: str
    observed_output: str
    expected_transition: str
    observed_transition: str
    first_incorrect_transition: str
    evidence_fingerprint: str
    normalized_observation_signature: str
    sequence: int
    user_visible: bool
    telemetry_only: bool
    synthetic_fixture: bool
    live_runtime: bool
    provider_involved: bool
    model_involved: bool
    canonical_write_performed: bool
    evidence_complete: bool = True
    validation_notes: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObservationLedgerEntry:
    ledger_entry_id: str
    observation: dict[str, Any]
    evidence_refs: tuple[str, ...]
    objective_id: str
    lifecycle_state: str
    source_subsystem: str
    expected_transition: str
    observed_transition: str
    first_incorrect_transition: str
    normalized_observation_signature: str
    first_seen_sequence: int
    most_recent_sequence: int
    occurrence_count: int = 1
    corroboration_count: int = 0
    duplicate_of: str | None = None
    superseded_by: str | None = None
    review_status: str = "operator_review_required"
    operator_disposition: str = "pending"
    diagnosis_eligibility_status: str = "not_eligible"
    retention_policy: str = "review_required"
    expires_after_sequence: int | None = None
    audit_rationale: str = "validated observation pending operator review"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObservationDisposition:
    disposition_id: str
    ledger_entry_id: str
    disposition: str
    operator_authority: str
    rationale: str
    sequence: int
    creates_diagnosis_candidate: bool = False
    writes_memory: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObservationReviewDecision:
    decision_id: str
    ledger_entry_id: str
    operator_authority: str
    decision: str
    rationale: str
    allowed_transition: str
    sequence: int
    one_shot: bool = True
    expires_after_sequence: int | None = None
    reclassifies_telemetry: bool = False
    consumed: bool = False
    duplicate_of: str | None = None
    supersedes: str | None = None
    retention_policy: str = "retain_until_review"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObservationLedgerState:
    ledger_id: str
    objective_id: str
    sequence: int
    entries: tuple[dict[str, Any], ...] = ()
    evidence_index: dict[str, dict[str, Any]] = field(default_factory=dict)
    duplicate_links: dict[str, str] = field(default_factory=dict)
    supersession_links: dict[str, str] = field(default_factory=dict)
    review_queue: tuple[str, ...] = ()
    diagnosis_review_queue: tuple[str, ...] = ()
    expired_entries: tuple[str, ...] = ()
    suspended_entries: tuple[str, ...] = ()
    review_decision_ids: tuple[str, ...] = ()
    retention_metadata_only: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObservationLedgerResult:
    accepted: bool
    reason: str
    state: ObservationLedgerState
    entry: ObservationLedgerEntry | None = None
    creates_diagnosis_candidate: bool = False


@dataclass(frozen=True)
class DiagnosisReviewAuthorization:
    authorization_id: str
    ledger_entry_id: str
    operator_authority: str
    allowed_diagnosis_scope: tuple[str, ...]
    linked_objective_id: str | None
    evidence_constraints: tuple[str, ...]
    one_shot: bool
    decision_sequence: int
    expires_after_sequence: int | None
    conditions: tuple[str, ...]
    audit_rationale: str
    consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DiagnosisEvidenceReference:
    evidence_reference_id: str
    ledger_entry_id: str
    observation_id: str
    evidence_id: str
    source_subsystem: str
    evidence_role: str
    classification: str
    deterministic_fingerprint: str
    live_runtime: bool
    synthetic_fixture: bool
    provider_or_model_derived: bool
    user_visible: bool
    integrity_status: str
    sequence: int
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class CompetingDiagnosisHypothesis:
    hypothesis_id: str
    diagnosis_id: str
    mechanism_description: str
    first_incorrect_transition_candidate: str
    supporting_evidence_reference_ids: tuple[str, ...]
    disconfirming_evidence_reference_ids: tuple[str, ...]
    neutral_evidence_reference_ids: tuple[str, ...]
    unresolved_evidence_reference_ids: tuple[str, ...]
    confidence: float
    uncertainty: str
    scope_estimate: str
    affected_components: tuple[str, ...]
    forbidden_components: tuple[str, ...]
    deeper_design_indicator: bool
    status: str
    created_sequence: int
    updated_sequence: int
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DiagnosisReviewDecision:
    decision_id: str
    diagnosis_id: str
    operator_authority: str
    disposition: str
    selected_hypothesis_id: str | None
    rationale: str
    allowed_next_transition: str
    conditions: tuple[str, ...]
    one_shot: bool
    decision_sequence: int
    expires_after_sequence: int | None
    consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DiagnosisProposalState:
    state_version: str
    diagnosis_review_authorization_ids: tuple[str, ...] = ()
    consumed_diagnosis_authorization_ids: tuple[str, ...] = ()
    diagnosis_candidates: tuple[dict[str, Any], ...] = ()
    competing_hypotheses: tuple[dict[str, Any], ...] = ()
    diagnosis_review_decisions: tuple[dict[str, Any], ...] = ()
    consumed_diagnosis_decision_ids: tuple[str, ...] = ()
    repair_proposals: tuple[dict[str, Any], ...] = ()
    proposal_review_decisions: tuple[dict[str, Any], ...] = ()
    consumed_proposal_decision_ids: tuple[str, ...] = ()
    pending_diagnosis_review_queue: tuple[str, ...] = ()
    proposal_drafting_eligible_diagnoses: tuple[str, ...] = ()
    pending_proposal_review_queue: tuple[str, ...] = ()
    future_sandbox_planning_eligible_proposals: tuple[str, ...] = ()
    rejected_proposals: tuple[str, ...] = ()
    revision_required_proposals: tuple[str, ...] = ()
    deferred_proposals: tuple[str, ...] = ()
    suspended_proposals: tuple[str, ...] = ()
    expired_proposals: tuple[str, ...] = ()
    deeper_design_proposals: tuple[str, ...] = ()
    rejected_diagnoses: tuple[str, ...] = ()
    unresolved_diagnoses: tuple[str, ...] = ()
    insufficient_evidence_diagnoses: tuple[str, ...] = ()
    non_defect_diagnoses: tuple[str, ...] = ()
    duplicate_diagnoses: tuple[str, ...] = ()
    suspended_diagnoses: tuple[str, ...] = ()
    expired_diagnoses: tuple[str, ...] = ()
    deeper_design_diagnoses: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DiagnosisCreationResult:
    accepted: bool
    reason: str
    state: DiagnosisProposalState
    diagnosis: DiagnosisCandidate | None = None
    evidence_references: tuple[DiagnosisEvidenceReference, ...] = ()
    creates_repair_proposal: bool = False


@dataclass(frozen=True)
class ProposalCreationResult:
    accepted: bool
    reason: str
    state: DiagnosisProposalState
    proposal: RepairProposal | None = None
    creates_patch: bool = False
    creates_sandbox_authorization: bool = False
    starts_sandbox: bool = False
    mutates_source: bool = False
    authorizes_application: bool = False
    performs_application: bool = False
    performs_persistence: bool = False
    provider_calls_performed: bool = False
    model_inference_performed: bool = False
    memory_write_performed: bool = False


@dataclass(frozen=True)
class ProposalReviewDecision:
    decision_id: str
    proposal_id: str
    operator_authority: str
    disposition: str
    rationale: str
    allowed_scope: tuple[str, ...]
    forbidden_scope: tuple[str, ...]
    conditions: tuple[str, ...]
    one_shot: bool
    decision_sequence: int
    expires_after_sequence: int | None
    consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ProposalReviewResult:
    accepted: bool
    reason: str
    state: DiagnosisProposalState
    proposal: RepairProposal | None = None
    decision: ProposalReviewDecision | None = None
    future_sandbox_planning_eligible: bool = False
    sandbox_authorization_created: bool = False
    sandbox_started: bool = False
    patch_created: bool = False
    source_mutated: bool = False
    application_authorized: bool = False
    application_performed: bool = False
    persistence_performed: bool = False


@dataclass(frozen=True)
class SandboxPlanningAuthorization:
    authorization_id: str
    proposal_id: str
    operator_authority: str
    allowed_planning_scope: tuple[str, ...]
    forbidden_planning_scope: tuple[str, ...]
    allowed_workspace_class: str
    allowed_tool_classes: tuple[str, ...]
    forbidden_tool_classes: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    one_shot: bool
    decision_sequence: int
    expires_after_sequence: int | None
    conditions: tuple[str, ...]
    rationale: str
    consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ModuleAttachmentPlan:
    attachment_plan_id: str
    proposal_id: str
    sandbox_plan_id: str
    module_identifier: str
    module_type: str
    source_package_description: str
    required_interfaces: tuple[str, ...]
    requested_permissions: tuple[str, ...]
    forbidden_permissions: tuple[str, ...]
    data_access_boundaries: tuple[str, ...]
    network_boundaries: tuple[str, ...]
    memory_boundaries: tuple[str, ...]
    tool_boundaries: tuple[str, ...]
    lifecycle_hooks_described: tuple[str, ...]
    activation_conditions: tuple[str, ...]
    deactivation_conditions: tuple[str, ...]
    rollback_or_removal_description: str
    compatibility_requirements: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    attachment_only_status: str = "ATTACHMENT_PLAN_ONLY"
    live_activation_prohibited: bool = True
    permissions_granted: bool = False
    module_loaded: bool = False
    registry_mutated: bool = False
    creation_sequence: int = 0
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxPlanningState:
    state_version: str
    planning_authorization_ids: tuple[str, ...] = ()
    consumed_planning_authorization_ids: tuple[str, ...] = ()
    sandbox_plans: tuple[dict[str, Any], ...] = ()
    module_attachment_plans: tuple[dict[str, Any], ...] = ()
    plan_review_decisions: tuple[dict[str, Any], ...] = ()
    consumed_plan_review_decision_ids: tuple[str, ...] = ()
    pending_plan_review_queue: tuple[str, ...] = ()
    plan_ids_by_proposal: dict[str, tuple[str, ...]] = field(default_factory=dict)
    attachment_plan_ids_by_sandbox_plan: dict[str, tuple[str, ...]] = field(default_factory=dict)
    future_sandbox_execution_eligible_plans: tuple[str, ...] = ()
    rejected_plans: tuple[str, ...] = ()
    revision_required_plans: tuple[str, ...] = ()
    deferred_plans: tuple[str, ...] = ()
    suspended_plans: tuple[str, ...] = ()
    expired_plans: tuple[str, ...] = ()
    deeper_design_plans: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxPlanCreationResult:
    accepted: bool
    reason: str
    state: SandboxPlanningState
    authorization: SandboxPlanningAuthorization | None = None
    sandbox_plan: SandboxEvaluationPlan | None = None
    module_attachment_plan: ModuleAttachmentPlan | None = None
    planning_authorization_consumed: bool = False
    sandbox_created: bool = False
    sandbox_started: bool = False
    workspace_created: bool = False
    repository_cloned: bool = False
    command_executed: bool = False
    tool_invoked: bool = False
    patch_created: bool = False
    source_mutated: bool = False
    module_loaded: bool = False
    registry_mutated: bool = False
    permissions_granted: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    network_accessed: bool = False
    memory_written: bool = False
    application_authorized: bool = False
    application_performed: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False


def make_development_objective(
    operator_supplied_goal: str,
    *,
    scope: tuple[str, ...] = ("diagnosis", "proposal"),
    success_criteria: tuple[str, ...] = ("operator_review_ready",),
    evidence_requirements: tuple[str, ...] = ("reproducible_observation",),
    forbidden_actions: tuple[str, ...] = ("provider_calls", "model_inference", "source_mutation", "canonical_writes", "schedulers", "self_approval"),
    creation_source: str = "operator_supplied",
    sequence: int = 0,
    parent_objective_id: str | None = None,
) -> DevelopmentObjective:
    return DevelopmentObjective(
        objective_id=stable_id("gsr-objective", operator_supplied_goal, scope, sequence),
        operator_supplied_goal=operator_supplied_goal,
        scope=scope,
        success_criteria=success_criteria,
        forbidden_actions=forbidden_actions,
        evidence_requirements=evidence_requirements,
        lifecycle_state="objective_pending",
        operator_authorization_state="NOT_AUTHORIZED",
        creation_source=creation_source,
        sequence=sequence,
        created_at=utc_now(),
        parent_objective_id=parent_objective_id,
    )


def make_observation(
    objective_id: str,
    *,
    source_subsystem: str,
    observed_behavior: str,
    expected_behavior: str,
    evidence_references: tuple[str, ...],
    confidence: float = 0.5,
    uncertainty: str = "explicit",
    severity: str = "medium",
    reproducibility: str = "unknown",
    user_visible: bool = False,
    telemetry_only: bool = False,
) -> SelfObservation:
    return SelfObservation(
        observation_id=stable_id("gsr-observation", objective_id, source_subsystem, observed_behavior, evidence_references),
        objective_id=objective_id,
        source_subsystem=source_subsystem,
        observed_behavior=observed_behavior,
        expected_behavior=expected_behavior,
        evidence_references=evidence_references,
        confidence=confidence,
        uncertainty=uncertainty,
        severity=severity,
        reproducibility=reproducibility,
        user_visible=user_visible,
        telemetry_only=telemetry_only,
    )


def make_diagnosis_candidate(
    observations: tuple[SelfObservation, ...],
    *,
    first_incorrect_transition: str,
    suspected_mechanism: str,
    competing_hypotheses: tuple[str, ...] = (),
    supporting_evidence: tuple[str, ...] = (),
    disconfirming_evidence: tuple[str, ...] = (),
    confidence: float = 0.5,
    scope_estimate: str = "bounded",
    deeper_design_required: bool = False,
) -> DiagnosisCandidate:
    observation_ids = tuple(item.observation_id for item in observations)
    return DiagnosisCandidate(
        diagnosis_id=stable_id("gsr-diagnosis", observation_ids, first_incorrect_transition, suspected_mechanism),
        linked_observations=observation_ids,
        first_incorrect_transition=first_incorrect_transition,
        suspected_mechanism=suspected_mechanism,
        competing_hypotheses=competing_hypotheses,
        supporting_evidence=supporting_evidence,
        disconfirming_evidence=disconfirming_evidence,
        confidence=confidence,
        scope_estimate=scope_estimate,
        deeper_design_required=deeper_design_required,
    )


def make_repair_proposal(
    diagnosis: DiagnosisCandidate,
    *,
    proposed_change: str,
    files_or_components_in_scope: tuple[str, ...],
    forbidden_files_or_components: tuple[str, ...],
    validation_plan: tuple[str, ...],
    predicted_effects: tuple[str, ...] = (),
    risks: tuple[str, ...] = (),
    rollback_strategy: tuple[str, ...] = ("discard_candidate_patch",),
) -> RepairProposal:
    return RepairProposal(
        proposal_id=stable_id("gsr-proposal", diagnosis.diagnosis_id, proposed_change, files_or_components_in_scope),
        diagnosis_id=diagnosis.diagnosis_id,
        proposed_change=proposed_change,
        files_or_components_in_scope=files_or_components_in_scope,
        forbidden_files_or_components=forbidden_files_or_components,
        predicted_effects=predicted_effects,
        risks=risks,
        rollback_strategy=rollback_strategy,
        validation_plan=validation_plan,
        operator_approval_requirement="EXPLICIT_OPERATOR_DECISION_REQUIRED",
    )


def make_sandbox_plan(proposal: RepairProposal) -> SandboxEvaluationPlan:
    return SandboxEvaluationPlan(
        plan_id=stable_id("gsr-sandbox-plan", proposal.proposal_id),
        proposal_id=proposal.proposal_id,
        disposable_workspace="required_disposable_workspace",
        test_selection=proposal.validation_plan,
        live_runtime_evidence_requirements=("no_live_runtime_activation",),
        provider_model_restrictions=("provider_calls_forbidden", "local_model_inference_forbidden"),
        memory_write_restrictions=("canonical_writes_forbidden", "noncanonical_writes_forbidden"),
        success_criteria=("focused_tests_pass", "rollback_proof_present"),
        failure_criteria=("scope_expansion", "provider_call", "memory_write", "live_mutation"),
        rollback_proof=proposal.rollback_strategy,
        artifact_retention_policy="retain_report_artifacts_only",
    )


def make_governance_decision(
    proposal_id: str,
    *,
    decision: str,
    allowed_scope: tuple[str, ...],
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    sequence: int = 0,
    one_shot: bool = True,
    expires_after_sequence: int | None = None,
    attached_conditions: tuple[str, ...] = (),
    audit_rationale: str = "operator controlled decision",
) -> GovernanceDecision:
    return GovernanceDecision(
        decision_id=stable_id("gsr-decision", proposal_id, decision, allowed_scope, sequence),
        proposal_id=proposal_id,
        operator_authority=operator_authority,
        decision=decision,
        allowed_scope=allowed_scope,
        one_shot=one_shot,
        expires_after_sequence=expires_after_sequence,
        attached_conditions=attached_conditions,
        audit_rationale=audit_rationale,
    )


def initial_cycle(objective: DevelopmentObjective) -> RegulationCycleState:
    return RegulationCycleState(
        cycle_id=stable_id("gsr-cycle", objective.objective_id),
        objective_id=objective.objective_id,
        lifecycle_state="objective_pending",
        sequence=objective.sequence,
    )


def can_activate_objective(objective: DevelopmentObjective, decision: GovernanceDecision | None = None) -> bool:
    return (
        objective.operator_authorization_state == OPERATOR_AUTHORIZED
        or _decision_allows(decision, proposal_id=objective.objective_id, scope="objective_activation", sequence=objective.sequence)
    )


def can_begin_sandbox(plan: SandboxEvaluationPlan, decision: GovernanceDecision | None, *, sequence: int = 0) -> bool:
    return _decision_allows(decision, proposal_id=plan.proposal_id, scope="sandbox_evaluation", sequence=sequence)


def can_apply_proposal(proposal: RepairProposal, decision: GovernanceDecision | None, *, sequence: int = 0) -> bool:
    return _decision_allows(decision, proposal_id=proposal.proposal_id, scope="application", sequence=sequence)


def proposal_can_apply_itself(proposal: RepairProposal) -> bool:
    _ = proposal
    return False


def observation_mutates_state(observation: SelfObservation) -> bool:
    return any(observation.safety.values())


def observation_auto_diagnoses(observation: SelfObservation) -> bool:
    _ = observation
    return False


def diagnosis_authorizes_proposal(diagnosis: DiagnosisCandidate) -> bool:
    _ = diagnosis
    return False


def execution_allowed_for_state(state: RegulationCycleState) -> bool:
    if state.deeper_design_required:
        return False
    return state.lifecycle_state in {"sandbox_authorized", "sandbox_evaluating", "application_authorized", "applying", "post_change_observation"}


def transition_cycle(
    state: RegulationCycleState,
    to_state: str,
    *,
    decision: GovernanceDecision | None = None,
    proposal_id: str | None = None,
) -> TransitionResult:
    if to_state not in LIFECYCLE_STATES:
        return TransitionResult(False, state.lifecycle_state, to_state, "unknown_state", state, False)
    if state.deeper_design_required and to_state != "deeper_design_required":
        return TransitionResult(False, state.lifecycle_state, to_state, "deeper_design_required_blocks_continuation", state, False)
    if to_state not in VALID_TRANSITIONS.get(state.lifecycle_state, ()):
        return TransitionResult(False, state.lifecycle_state, to_state, "invalid_transition", state, False)
    if to_state == "sandbox_authorized" and not _decision_allows(decision, proposal_id=proposal_id, scope="sandbox_evaluation", sequence=state.sequence):
        return TransitionResult(False, state.lifecycle_state, to_state, "sandbox_authorization_required", state, False)
    if to_state == "application_authorized" and not _decision_allows(decision, proposal_id=proposal_id, scope="application", sequence=state.sequence):
        return TransitionResult(False, state.lifecycle_state, to_state, "application_authorization_required", state, False)
    next_state = RegulationCycleState(
        cycle_id=state.cycle_id,
        objective_id=state.objective_id,
        lifecycle_state=to_state,
        sequence=state.sequence + 1,
        observation_ids=state.observation_ids,
        diagnosis_ids=state.diagnosis_ids,
        proposal_ids=state.proposal_ids,
        decision_ids=state.decision_ids + ((decision.decision_id,) if decision else ()),
        deeper_design_required=state.deeper_design_required or to_state == "deeper_design_required",
    )
    return TransitionResult(True, state.lifecycle_state, to_state, "transition_accepted", next_state, execution_allowed_for_state(next_state))


def make_observation_evidence(
    objective_id: str,
    *,
    source_subsystem: str,
    source_type: str,
    source_reference: str,
    observed_input: str,
    observed_output: str,
    expected_transition: str,
    observed_transition: str,
    first_incorrect_transition: str,
    sequence: int = 0,
    user_visible: bool = True,
    telemetry_only: bool = False,
    synthetic_fixture: bool = False,
    live_runtime: bool = False,
    provider_involved: bool = False,
    model_involved: bool = False,
    canonical_write_performed: bool = False,
    evidence_complete: bool = True,
    validation_notes: tuple[str, ...] = (),
    evidence_fingerprint: str | None = None,
) -> ObservationEvidence:
    signature = _normalized_observation_signature(
        source_subsystem,
        expected_transition,
        observed_transition,
        objective_id,
        first_incorrect_transition,
    )
    fingerprint = evidence_fingerprint or stable_id(
        "gsr-b-evidence-fingerprint",
        source_subsystem,
        source_type,
        source_reference,
        observed_input,
        observed_output,
        expected_transition,
        observed_transition,
        first_incorrect_transition,
    )
    return ObservationEvidence(
        evidence_id=stable_id("gsr-b-evidence", objective_id, source_subsystem, fingerprint, sequence),
        objective_id=objective_id,
        source_subsystem=source_subsystem,
        source_type=source_type,
        source_reference=source_reference,
        observed_input=observed_input,
        observed_output=observed_output,
        expected_transition=expected_transition,
        observed_transition=observed_transition,
        first_incorrect_transition=first_incorrect_transition,
        evidence_fingerprint=fingerprint,
        normalized_observation_signature=signature,
        sequence=sequence,
        user_visible=user_visible,
        telemetry_only=telemetry_only,
        synthetic_fixture=synthetic_fixture,
        live_runtime=live_runtime,
        provider_involved=provider_involved,
        model_involved=model_involved,
        canonical_write_performed=canonical_write_performed,
        evidence_complete=evidence_complete,
        validation_notes=validation_notes,
    )


def validate_observation_evidence(evidence: ObservationEvidence) -> tuple[bool, str]:
    required_text = (
        evidence.objective_id,
        evidence.source_subsystem,
        evidence.source_type,
        evidence.source_reference,
        evidence.observed_output,
        evidence.expected_transition,
        evidence.observed_transition,
        evidence.first_incorrect_transition,
        evidence.evidence_fingerprint,
        evidence.normalized_observation_signature,
    )
    if not evidence.evidence_complete:
        return False, "evidence_incomplete"
    if any(not str(item).strip() for item in required_text):
        return False, "required_evidence_field_missing"
    if evidence.provider_involved or evidence.model_involved or evidence.canonical_write_performed:
        return False, "prohibited_side_effect_in_evidence"
    if evidence.telemetry_only and evidence.user_visible:
        return False, "telemetry_only_conflicts_with_user_visible_evidence"
    return True, "evidence_validated"


def make_observation_ledger(objective_id: str, *, sequence: int = 0) -> ObservationLedgerState:
    return ObservationLedgerState(
        ledger_id=stable_id("gsr-b-ledger", objective_id),
        objective_id=objective_id,
        sequence=sequence,
    )


def record_observation(
    ledger: ObservationLedgerState,
    observation: SelfObservation,
    evidence: ObservationEvidence,
) -> ObservationLedgerResult:
    valid, reason = validate_observation_evidence(evidence)
    if not valid:
        return ObservationLedgerResult(False, reason, ledger)
    if observation.objective_id != ledger.objective_id or evidence.objective_id != ledger.objective_id:
        return ObservationLedgerResult(False, "objective_mismatch", ledger)
    if evidence.evidence_id not in observation.evidence_references:
        return ObservationLedgerResult(False, "observation_missing_evidence_reference", ledger)

    duplicate_of = find_duplicate_observation(ledger, observation, evidence)
    entry = ObservationLedgerEntry(
        ledger_entry_id=stable_id("gsr-b-ledger-entry", ledger.ledger_id, observation.observation_id, evidence.evidence_id),
        observation=serialize(observation),
        evidence_refs=(evidence.evidence_id,),
        objective_id=ledger.objective_id,
        lifecycle_state="pending_review",
        source_subsystem=evidence.source_subsystem,
        expected_transition=evidence.expected_transition,
        observed_transition=evidence.observed_transition,
        first_incorrect_transition=evidence.first_incorrect_transition,
        normalized_observation_signature=evidence.normalized_observation_signature,
        first_seen_sequence=evidence.sequence,
        most_recent_sequence=evidence.sequence,
        duplicate_of=duplicate_of,
        audit_rationale="validated evidence recorded; operator review required",
    )
    new_entries = ledger.entries + (serialize(entry),)
    new_index = dict(ledger.evidence_index)
    new_index[evidence.evidence_id] = serialize(evidence)
    new_review_queue = ledger.review_queue + (entry.ledger_entry_id,)
    new_duplicate_links = dict(ledger.duplicate_links)
    if duplicate_of is not None:
        new_duplicate_links[entry.ledger_entry_id] = duplicate_of
    next_ledger = ObservationLedgerState(
        ledger_id=ledger.ledger_id,
        objective_id=ledger.objective_id,
        sequence=max(ledger.sequence, evidence.sequence) + 1,
        entries=new_entries,
        evidence_index=new_index,
        duplicate_links=new_duplicate_links,
        supersession_links=dict(ledger.supersession_links),
        review_queue=new_review_queue,
        diagnosis_review_queue=ledger.diagnosis_review_queue,
        expired_entries=ledger.expired_entries,
        suspended_entries=ledger.suspended_entries,
    )
    return ObservationLedgerResult(True, "observation_pending_operator_review", next_ledger, entry)


def make_observation_review_decision(
    ledger_entry_id: str,
    *,
    decision: str,
    allowed_transition: str,
    rationale: str,
    sequence: int,
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    one_shot: bool = True,
    expires_after_sequence: int | None = None,
    reclassifies_telemetry: bool = False,
    duplicate_of: str | None = None,
    supersedes: str | None = None,
    retention_policy: str = "retain_until_review",
) -> ObservationReviewDecision:
    return ObservationReviewDecision(
        decision_id=stable_id("gsr-b-observation-review", ledger_entry_id, decision, allowed_transition, sequence),
        ledger_entry_id=ledger_entry_id,
        operator_authority=operator_authority,
        decision=decision,
        rationale=rationale,
        allowed_transition=allowed_transition,
        sequence=sequence,
        one_shot=one_shot,
        expires_after_sequence=expires_after_sequence,
        reclassifies_telemetry=reclassifies_telemetry,
        duplicate_of=duplicate_of,
        supersedes=supersedes,
        retention_policy=retention_policy,
    )


def review_observation_entry(
    ledger: ObservationLedgerState,
    decision: ObservationReviewDecision,
) -> ObservationLedgerResult:
    if decision.decision_id in ledger.review_decision_ids:
        return ObservationLedgerResult(False, "decision_already_used", ledger)
    entry_payload = _ledger_entry_payload(ledger, decision.ledger_entry_id)
    if entry_payload is None:
        return ObservationLedgerResult(False, "entry_not_found", ledger)
    entry = deserialize(ObservationLedgerEntry, entry_payload)
    allowed, reason = _review_decision_allows(entry, decision, ledger.sequence)
    if not allowed:
        return ObservationLedgerResult(False, reason, ledger, entry)
    evidence_payload = ledger.evidence_index.get(entry.evidence_refs[0], {})
    if entry.lifecycle_state in OBSERVATION_LEDGER_TERMINAL_STATES:
        return ObservationLedgerResult(False, "entry_state_cannot_advance", ledger, entry)
    if decision.allowed_transition == "superseded":
        if not decision.supersedes or decision.supersedes == entry.ledger_entry_id:
            return ObservationLedgerResult(False, "replacement_entry_required", ledger, entry)
        if _ledger_entry_payload(ledger, decision.supersedes) is None:
            return ObservationLedgerResult(False, "replacement_entry_not_found", ledger, entry)
    if evidence_payload.get("telemetry_only") is True and decision.allowed_transition == "diagnosis_review_eligible":
        if not decision.reclassifies_telemetry:
            return ObservationLedgerResult(False, "telemetry_reclassification_required", ledger, entry)
        if entry.lifecycle_state != "telemetry_only":
            return ObservationLedgerResult(False, "telemetry_disposition_required", ledger, entry)

    updated_entry = _entry_for_review(entry, decision)
    if updated_entry is None:
        return ObservationLedgerResult(False, "invalid_review_transition", ledger, entry)
    next_ledger = _replace_ledger_entry(ledger, updated_entry, decision)
    return ObservationLedgerResult(
        True,
        "observation_review_transition_accepted",
        next_ledger,
        updated_entry,
        creates_diagnosis_candidate=False,
    )


def make_observation_disposition(decision: ObservationReviewDecision) -> ObservationDisposition:
    return ObservationDisposition(
        disposition_id=stable_id("gsr-b-observation-disposition", decision.decision_id),
        ledger_entry_id=decision.ledger_entry_id,
        disposition=decision.allowed_transition,
        operator_authority=decision.operator_authority,
        rationale=decision.rationale,
        sequence=decision.sequence,
    )


def find_duplicate_observation(
    ledger: ObservationLedgerState,
    observation: SelfObservation,
    evidence: ObservationEvidence,
) -> str | None:
    for payload in ledger.entries:
        existing = deserialize(ObservationLedgerEntry, payload)
        if (
            existing.source_subsystem == evidence.source_subsystem
            and existing.expected_transition == evidence.expected_transition
            and existing.observed_transition == evidence.observed_transition
            and existing.objective_id == observation.objective_id
            and existing.first_incorrect_transition == evidence.first_incorrect_transition
            and existing.normalized_observation_signature == evidence.normalized_observation_signature
        ):
            existing_evidence = ledger.evidence_index.get(existing.evidence_refs[0], {})
            if existing_evidence.get("evidence_fingerprint") == evidence.evidence_fingerprint:
                return existing.ledger_entry_id
    return None


def ledger_entry_can_advance(entry: ObservationLedgerEntry) -> bool:
    return entry.lifecycle_state not in OBSERVATION_LEDGER_TERMINAL_STATES


def ledger_entry_creates_diagnosis(entry: ObservationLedgerEntry) -> bool:
    _ = entry
    return False


def ledger_entry_creates_repair_proposal(entry: ObservationLedgerEntry) -> bool:
    _ = entry
    return False


def observation_can_review_itself(observation: SelfObservation) -> bool:
    _ = observation
    return False


def expire_observation_entries(
    ledger: ObservationLedgerState,
    *,
    current_sequence: int,
    objective_closed: bool = False,
) -> ObservationLedgerState:
    updated_entries: list[dict[str, Any]] = []
    expired = set(ledger.expired_entries)
    for payload in ledger.entries:
        entry = deserialize(ObservationLedgerEntry, payload)
        should_expire = (
            entry.expires_after_sequence is not None
            and current_sequence > entry.expires_after_sequence
            and entry.retention_policy in {"retain_for_sequence_window", "expire_after_sequence"}
            and entry.lifecycle_state not in OBSERVATION_LEDGER_TERMINAL_STATES
        )
        objective_should_expire = (
            objective_closed
            and entry.retention_policy == "retain_until_objective_closed"
            and entry.lifecycle_state not in OBSERVATION_LEDGER_TERMINAL_STATES
        )
        if should_expire or objective_should_expire:
            entry = ObservationLedgerEntry(**{**serialize(entry), "lifecycle_state": "expired", "operator_disposition": "expired"})
            expired.add(entry.ledger_entry_id)
        updated_entries.append(serialize(entry))
    return ObservationLedgerState(
        ledger_id=ledger.ledger_id,
        objective_id=ledger.objective_id,
        sequence=max(ledger.sequence, current_sequence),
        entries=tuple(updated_entries),
        evidence_index=dict(ledger.evidence_index),
        duplicate_links=dict(ledger.duplicate_links),
        supersession_links=dict(ledger.supersession_links),
        review_queue=tuple(entry_id for entry_id in ledger.review_queue if entry_id not in expired),
        diagnosis_review_queue=ledger.diagnosis_review_queue,
        expired_entries=tuple(sorted(expired)),
        suspended_entries=ledger.suspended_entries,
        review_decision_ids=ledger.review_decision_ids,
    )


def build_gsr_b_ledger_report() -> dict[str, Any]:
    objective = make_development_objective("Create an inert self-observation ledger.", sequence=2)
    evidence = make_observation_evidence(
        objective.objective_id,
        source_subsystem="semantic_runtime",
        source_type="operator_supplied_transcript",
        source_reference="reports/operator_pilot/conversation_log.md",
        observed_input="what were we discussing before that",
        observed_output="pending consent repeated",
        expected_transition="discourse_history_recall",
        observed_transition="pending_local_model_consent",
        first_incorrect_transition="pending_consent_preempts_discourse_recall",
        sequence=2,
        live_runtime=True,
    )
    observation = make_observation(
        objective.objective_id,
        source_subsystem=evidence.source_subsystem,
        observed_behavior=evidence.observed_transition,
        expected_behavior=evidence.expected_transition,
        evidence_references=(evidence.evidence_id,),
        confidence=0.6,
        uncertainty="operator_transcript",
        reproducibility="single_live_sequence",
        user_visible=True,
    )
    ledger = make_observation_ledger(objective.objective_id, sequence=2)
    recorded = record_observation(ledger, observation, evidence)
    return {
        "stage": "GSR-B",
        "status": "INERT_SELF_OBSERVATION_LEDGER",
        "ledger_state": serialize(recorded.state),
        "recorded": recorded.accepted,
        "reason": recorded.reason,
        "creates_diagnosis_candidate": recorded.creates_diagnosis_candidate,
        "safety": safety_metadata(),
        "live_runtime_integration_performed": False,
    }


def make_diagnosis_proposal_state() -> DiagnosisProposalState:
    return DiagnosisProposalState(state_version="GSR-C-1")


def make_diagnosis_review_authorization(
    ledger_entry_id: str,
    *,
    allowed_diagnosis_scope: tuple[str, ...],
    linked_objective_id: str | None = None,
    evidence_constraints: tuple[str, ...] = ("traceable_ledger_evidence",),
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    decision_sequence: int = 0,
    expires_after_sequence: int | None = None,
    conditions: tuple[str, ...] = (),
    audit_rationale: str = "operator authorized provisional diagnosis review",
    one_shot: bool = True,
    consumed: bool = False,
) -> DiagnosisReviewAuthorization:
    return DiagnosisReviewAuthorization(
        authorization_id=stable_id("gsr-c-diagnosis-authorization", ledger_entry_id, allowed_diagnosis_scope, decision_sequence),
        ledger_entry_id=ledger_entry_id,
        operator_authority=operator_authority,
        allowed_diagnosis_scope=allowed_diagnosis_scope,
        linked_objective_id=linked_objective_id,
        evidence_constraints=evidence_constraints,
        one_shot=one_shot,
        decision_sequence=decision_sequence,
        expires_after_sequence=expires_after_sequence,
        conditions=conditions,
        audit_rationale=audit_rationale,
        consumed=consumed,
    )


def make_diagnosis_evidence_reference(
    ledger_entry: ObservationLedgerEntry,
    evidence: Mapping[str, Any],
    *,
    evidence_role: str = "supporting",
    classification: str = "supporting",
    sequence: int = 0,
) -> DiagnosisEvidenceReference:
    observation_payload = ledger_entry.observation
    observation_id = str(observation_payload.get("observation_id") or "")
    evidence_id = str(evidence.get("evidence_id") or ledger_entry.evidence_refs[0])
    return DiagnosisEvidenceReference(
        evidence_reference_id=stable_id("gsr-c-diagnosis-evidence", ledger_entry.ledger_entry_id, evidence_id, evidence_role, classification),
        ledger_entry_id=ledger_entry.ledger_entry_id,
        observation_id=observation_id,
        evidence_id=evidence_id,
        source_subsystem=str(evidence.get("source_subsystem") or ledger_entry.source_subsystem),
        evidence_role=evidence_role,
        classification=classification,
        deterministic_fingerprint=str(evidence.get("evidence_fingerprint") or ledger_entry.normalized_observation_signature),
        live_runtime=bool(evidence.get("live_runtime", False)),
        synthetic_fixture=bool(evidence.get("synthetic_fixture", False)),
        provider_or_model_derived=bool(evidence.get("provider_involved", False) or evidence.get("model_involved", False)),
        user_visible=bool(evidence.get("user_visible", False)),
        integrity_status="intact" if evidence_id in ledger_entry.evidence_refs else "unlinked",
        sequence=sequence,
    )


def create_provisional_diagnosis_candidate(
    ledger: ObservationLedgerState,
    state: DiagnosisProposalState,
    authorization: DiagnosisReviewAuthorization,
    *,
    suspected_mechanism: str,
    competing_hypotheses: tuple[str, ...] = (),
    confidence: float = 0.5,
    uncertainty: str = "provisional",
    severity: str = "medium",
    reproducibility: str = "unknown",
    scope_estimate: str = "bounded",
    affected_components: tuple[str, ...] = (),
    forbidden_components: tuple[str, ...] = (),
    deeper_design_required: bool = False,
    sequence: int = 0,
) -> DiagnosisCreationResult:
    allowed, reason, entry = _diagnosis_authorization_allows(ledger, state, authorization, sequence=sequence)
    if not allowed:
        return DiagnosisCreationResult(False, reason, state)
    assert entry is not None
    evidence_payload = ledger.evidence_index.get(entry.evidence_refs[0], {})
    evidence_ref = make_diagnosis_evidence_reference(entry, evidence_payload, sequence=sequence)
    diagnosis = DiagnosisCandidate(
        diagnosis_id=stable_id("gsr-c-diagnosis", entry.ledger_entry_id, authorization.authorization_id, suspected_mechanism),
        linked_observations=(str(entry.observation.get("observation_id") or ""),),
        linked_evidence_references=(evidence_ref.evidence_reference_id,),
        source_ledger_entry_id=entry.ledger_entry_id,
        first_incorrect_transition=entry.first_incorrect_transition,
        suspected_mechanism=suspected_mechanism,
        competing_hypotheses=competing_hypotheses,
        supporting_evidence=(evidence_ref.evidence_reference_id,),
        disconfirming_evidence=(),
        unresolved_evidence=(),
        confidence=confidence,
        uncertainty=uncertainty,
        severity=severity,
        reproducibility=reproducibility,
        scope_estimate=scope_estimate,
        affected_components=affected_components,
        forbidden_components=forbidden_components,
        deeper_design_required=deeper_design_required,
        provisional=True,
        operator_review_status="pending_review",
        creation_authorization_id=authorization.authorization_id,
        created_sequence=sequence,
    )
    next_state = DiagnosisProposalState(
        state_version=state.state_version,
        diagnosis_review_authorization_ids=tuple(dict.fromkeys(state.diagnosis_review_authorization_ids + (authorization.authorization_id,))),
        consumed_diagnosis_authorization_ids=tuple(dict.fromkeys(state.consumed_diagnosis_authorization_ids + (authorization.authorization_id,))),
        diagnosis_candidates=state.diagnosis_candidates + (serialize(diagnosis),),
        diagnosis_review_decisions=state.diagnosis_review_decisions,
        consumed_diagnosis_decision_ids=state.consumed_diagnosis_decision_ids,
        repair_proposals=state.repair_proposals,
        proposal_review_decisions=state.proposal_review_decisions,
        consumed_proposal_decision_ids=state.consumed_proposal_decision_ids,
        pending_diagnosis_review_queue=tuple(dict.fromkeys(state.pending_diagnosis_review_queue + (diagnosis.diagnosis_id,))),
        proposal_drafting_eligible_diagnoses=state.proposal_drafting_eligible_diagnoses,
        pending_proposal_review_queue=state.pending_proposal_review_queue,
        future_sandbox_planning_eligible_proposals=state.future_sandbox_planning_eligible_proposals,
        rejected_diagnoses=state.rejected_diagnoses,
        suspended_diagnoses=state.suspended_diagnoses,
        expired_diagnoses=state.expired_diagnoses,
        deeper_design_diagnoses=state.deeper_design_diagnoses,
    )
    return DiagnosisCreationResult(True, "provisional_diagnosis_created", next_state, diagnosis, (evidence_ref,), False)


def diagnosis_candidate_creates_proposal(diagnosis: DiagnosisCandidate) -> bool:
    _ = diagnosis
    return False


def diagnosis_authorization_is_consumed(state: DiagnosisProposalState, authorization: DiagnosisReviewAuthorization) -> bool:
    return authorization.authorization_id in state.consumed_diagnosis_authorization_ids


def make_competing_diagnosis_hypothesis(
    diagnosis: DiagnosisCandidate,
    *,
    mechanism_description: str,
    first_incorrect_transition_candidate: str | None = None,
    confidence: float = 0.5,
    uncertainty: str = "provisional",
    scope_estimate: str | None = None,
    affected_components: tuple[str, ...] | None = None,
    forbidden_components: tuple[str, ...] | None = None,
    deeper_design_indicator: bool = False,
    status: str = "pending_review",
    sequence: int = 0,
) -> CompetingDiagnosisHypothesis:
    return CompetingDiagnosisHypothesis(
        hypothesis_id=stable_id("gsr-c-hypothesis", diagnosis.diagnosis_id, mechanism_description, sequence),
        diagnosis_id=diagnosis.diagnosis_id,
        mechanism_description=mechanism_description,
        first_incorrect_transition_candidate=first_incorrect_transition_candidate or diagnosis.first_incorrect_transition,
        supporting_evidence_reference_ids=(),
        disconfirming_evidence_reference_ids=(),
        neutral_evidence_reference_ids=(),
        unresolved_evidence_reference_ids=(),
        confidence=confidence,
        uncertainty=uncertainty,
        scope_estimate=scope_estimate or diagnosis.scope_estimate,
        affected_components=affected_components if affected_components is not None else diagnosis.affected_components,
        forbidden_components=forbidden_components if forbidden_components is not None else diagnosis.forbidden_components,
        deeper_design_indicator=deeper_design_indicator,
        status=status,
        created_sequence=sequence,
        updated_sequence=sequence,
    )


def add_competing_diagnosis_hypothesis(
    state: DiagnosisProposalState,
    diagnosis: DiagnosisCandidate,
    hypothesis: CompetingDiagnosisHypothesis,
) -> DiagnosisProposalState:
    if hypothesis.diagnosis_id != diagnosis.diagnosis_id:
        return state
    return DiagnosisProposalState(
        **{
            **serialize(state),
            "competing_hypotheses": state.competing_hypotheses + (serialize(hypothesis),),
        }
    )


def attach_evidence_to_hypothesis(
    hypothesis: CompetingDiagnosisHypothesis,
    evidence_reference: DiagnosisEvidenceReference,
    *,
    role: str,
    sequence: int,
) -> CompetingDiagnosisHypothesis:
    if role not in {"supporting", "disconfirming", "neutral", "unresolved"}:
        return hypothesis
    evidence_id = evidence_reference.evidence_reference_id
    updates: dict[str, Any] = {"updated_sequence": sequence}
    field_name = f"{role}_evidence_reference_ids"
    existing = getattr(hypothesis, field_name)
    updates[field_name] = tuple(dict.fromkeys(existing + (evidence_id,)))
    return CompetingDiagnosisHypothesis(**{**serialize(hypothesis), **updates})


def hypothesis_selects_itself(hypothesis: CompetingDiagnosisHypothesis) -> bool:
    _ = hypothesis
    return False


def diagnosis_has_automatic_hypothesis_winner(state: DiagnosisProposalState, diagnosis_id: str) -> bool:
    _ = state, diagnosis_id
    return False


def make_diagnosis_review_decision(
    diagnosis_id: str,
    *,
    disposition: str,
    rationale: str,
    allowed_next_transition: str,
    selected_hypothesis_id: str | None = None,
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    conditions: tuple[str, ...] = (),
    one_shot: bool = True,
    decision_sequence: int = 0,
    expires_after_sequence: int | None = None,
    consumed: bool = False,
) -> DiagnosisReviewDecision:
    return DiagnosisReviewDecision(
        decision_id=stable_id("gsr-c-diagnosis-review", diagnosis_id, disposition, selected_hypothesis_id or "no-selection", decision_sequence),
        diagnosis_id=diagnosis_id,
        operator_authority=operator_authority,
        disposition=disposition,
        selected_hypothesis_id=selected_hypothesis_id,
        rationale=rationale,
        allowed_next_transition=allowed_next_transition,
        conditions=conditions,
        one_shot=one_shot,
        decision_sequence=decision_sequence,
        expires_after_sequence=expires_after_sequence,
        consumed=consumed,
    )


def review_diagnosis_candidate(
    state: DiagnosisProposalState,
    decision: DiagnosisReviewDecision,
    *,
    sequence: int,
) -> DiagnosisCreationResult:
    allowed, reason, diagnosis = _diagnosis_review_decision_allows(state, decision, sequence=sequence)
    if not allowed:
        return DiagnosisCreationResult(False, reason, state, diagnosis)
    assert diagnosis is not None
    reviewed = DiagnosisCandidate(**{
        **serialize(diagnosis),
        "operator_review_status": decision.disposition,
    })
    next_state = _replace_diagnosis_candidate_for_review(state, reviewed, decision)
    return DiagnosisCreationResult(True, "diagnosis_review_decision_accepted", next_state, reviewed, (), False)


def diagnosis_candidate_can_review_itself(diagnosis: DiagnosisCandidate) -> bool:
    _ = diagnosis
    return False


def diagnosis_is_eligible_for_proposal_drafting(state: DiagnosisProposalState, diagnosis_id: str) -> bool:
    return diagnosis_id in state.proposal_drafting_eligible_diagnoses


def diagnosis_disposition_blocks_proposal_drafting(disposition: str) -> bool:
    return disposition in DIAGNOSIS_PROPOSAL_BLOCKING_DISPOSITIONS


def create_proposal_only_repair_proposal(
    state: DiagnosisProposalState,
    diagnosis_id: str,
    *,
    proposal_title: str,
    proposed_mechanism_level_change: str,
    problem_statement: str,
    files_or_components_in_scope: tuple[str, ...],
    forbidden_files_or_components: tuple[str, ...],
    predicted_effects: tuple[str, ...],
    expected_user_visible_effects: tuple[str, ...],
    regression_risks: tuple[str, ...],
    governance_risks: tuple[str, ...],
    safety_risks: tuple[str, ...],
    alternatives_considered: tuple[str, ...],
    reasons_alternatives_rejected: tuple[str, ...],
    rollback_description: str,
    validation_plan: tuple[str, ...],
    focused_test_requirements: tuple[str, ...],
    adjacent_test_requirements: tuple[str, ...],
    live_runtime_evidence_requirements: tuple[str, ...],
    full_suite_policy: str,
    provider_model_restrictions: tuple[str, ...],
    memory_write_restrictions: tuple[str, ...],
    linked_selected_hypothesis_id: str | None = None,
    creation_sequence: int = 0,
    expiration_sequence: int | None = None,
) -> ProposalCreationResult:
    diagnosis_payload = _diagnosis_payload(state, diagnosis_id)
    if diagnosis_payload is None:
        return ProposalCreationResult(False, "diagnosis_not_found", state)
    diagnosis = deserialize(DiagnosisCandidate, diagnosis_payload)
    if diagnosis_id in state.rejected_diagnoses:
        return ProposalCreationResult(False, "diagnosis_rejected_blocks_proposal", state)
    if diagnosis_id in state.unresolved_diagnoses:
        return ProposalCreationResult(False, "diagnosis_unresolved_blocks_proposal", state)
    if diagnosis_id in state.non_defect_diagnoses:
        return ProposalCreationResult(False, "diagnosis_non_defect_blocks_proposal", state)
    if diagnosis_id in state.insufficient_evidence_diagnoses:
        return ProposalCreationResult(False, "diagnosis_insufficient_evidence_blocks_proposal", state)
    if diagnosis_id in state.suspended_diagnoses:
        return ProposalCreationResult(False, "diagnosis_suspended_blocks_proposal", state)
    if diagnosis_id in state.expired_diagnoses:
        return ProposalCreationResult(False, "diagnosis_expired_blocks_proposal", state)
    if diagnosis_id in state.duplicate_diagnoses:
        return ProposalCreationResult(False, "diagnosis_duplicate_blocks_proposal", state)
    if diagnosis_id in state.deeper_design_diagnoses or diagnosis.deeper_design_required:
        return ProposalCreationResult(False, "diagnosis_deeper_design_blocks_proposal", state)
    if diagnosis_id not in state.proposal_drafting_eligible_diagnoses or diagnosis.operator_review_status != "accepted_for_proposal_drafting":
        return ProposalCreationResult(False, "diagnosis_not_accepted_for_proposal_drafting", state)
    if linked_selected_hypothesis_id is not None and not _hypothesis_belongs_to_diagnosis(state, diagnosis_id, linked_selected_hypothesis_id):
        return ProposalCreationResult(False, "selected_hypothesis_not_in_diagnosis", state)
    if set(files_or_components_in_scope).intersection(forbidden_files_or_components):
        return ProposalCreationResult(False, "scope_overlaps_forbidden_components", state)
    if not rollback_description.strip():
        return ProposalCreationResult(False, "rollback_description_required", state)
    if not validation_plan:
        return ProposalCreationResult(False, "validation_plan_required", state)
    if not provider_model_restrictions:
        return ProposalCreationResult(False, "provider_model_restrictions_required", state)
    if not memory_write_restrictions:
        return ProposalCreationResult(False, "memory_write_restrictions_required", state)
    content = (proposal_title, proposed_mechanism_level_change, problem_statement, rollback_description, full_suite_policy, *predicted_effects, *validation_plan)
    if _contains_executable_proposal_content(content):
        return ProposalCreationResult(False, "executable_content_prohibited", state)
    proposal = RepairProposal(
        proposal_id=stable_id("gsr-c-proposal", diagnosis_id, proposal_title, creation_sequence),
        diagnosis_id=diagnosis_id,
        proposed_change=proposed_mechanism_level_change,
        files_or_components_in_scope=files_or_components_in_scope,
        forbidden_files_or_components=forbidden_files_or_components,
        predicted_effects=predicted_effects,
        risks=regression_risks + governance_risks + safety_risks,
        rollback_strategy=(rollback_description,),
        validation_plan=validation_plan,
        operator_approval_requirement="EXPLICIT_OPERATOR_PROPOSAL_REVIEW_REQUIRED",
        proposal_only_status="PROPOSAL_ONLY",
        proposal_title=proposal_title,
        problem_statement=problem_statement,
        first_incorrect_transition=diagnosis.first_incorrect_transition,
        expected_user_visible_effects=expected_user_visible_effects,
        regression_risks=regression_risks,
        governance_risks=governance_risks,
        safety_risks=safety_risks,
        alternatives_considered=alternatives_considered,
        reasons_alternatives_rejected=reasons_alternatives_rejected,
        rollback_description=rollback_description,
        focused_test_requirements=focused_test_requirements,
        adjacent_test_requirements=adjacent_test_requirements,
        live_runtime_evidence_requirements=live_runtime_evidence_requirements,
        full_suite_policy=full_suite_policy,
        provider_model_restrictions=provider_model_restrictions,
        memory_write_restrictions=memory_write_restrictions,
        source_mutation_prohibited=True,
        sandbox_execution_prohibited=True,
        application_prohibited=True,
        deeper_design_handling="defer_to_design_milestone",
        operator_review_status="pending_review",
        creation_sequence=creation_sequence,
        expiration_sequence=expiration_sequence,
        linked_evidence_references=diagnosis.linked_evidence_references,
        linked_selected_hypothesis_id=linked_selected_hypothesis_id,
    )
    next_state = DiagnosisProposalState(
        **{
            **serialize(state),
            "repair_proposals": state.repair_proposals + (serialize(proposal),),
            "pending_proposal_review_queue": tuple(dict.fromkeys(state.pending_proposal_review_queue + (proposal.proposal_id,))),
        }
    )
    return ProposalCreationResult(True, "proposal_only_repair_proposal_created", next_state, proposal)


def proposal_contains_patch_or_executable_content(proposal: RepairProposal) -> bool:
    return _contains_executable_proposal_content(
        (
            proposal.proposal_title,
            proposal.proposed_change,
            proposal.problem_statement,
            proposal.rollback_description,
            *proposal.predicted_effects,
            *proposal.validation_plan,
        )
    )


def proposal_mutates_source(proposal: RepairProposal) -> bool:
    _ = proposal
    return False


def proposal_starts_sandbox(proposal: RepairProposal) -> bool:
    _ = proposal
    return False


def proposal_authorizes_application(proposal: RepairProposal) -> bool:
    _ = proposal
    return False


def make_proposal_review_decision(
    proposal_id: str,
    *,
    disposition: str,
    rationale: str,
    allowed_scope: tuple[str, ...],
    forbidden_scope: tuple[str, ...] = (),
    conditions: tuple[str, ...] = (),
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    one_shot: bool = True,
    decision_sequence: int = 0,
    expires_after_sequence: int | None = None,
    consumed: bool = False,
) -> ProposalReviewDecision:
    return ProposalReviewDecision(
        decision_id=stable_id("gsr-c-proposal-review", proposal_id, disposition, decision_sequence),
        proposal_id=proposal_id,
        operator_authority=operator_authority,
        disposition=disposition,
        rationale=rationale,
        allowed_scope=allowed_scope,
        forbidden_scope=forbidden_scope,
        conditions=conditions,
        one_shot=one_shot,
        decision_sequence=decision_sequence,
        expires_after_sequence=expires_after_sequence,
        consumed=consumed,
    )


def review_repair_proposal(
    state: DiagnosisProposalState,
    decision: ProposalReviewDecision,
    *,
    sequence: int,
) -> ProposalReviewResult:
    allowed, reason, proposal = _proposal_review_decision_allows(state, decision, sequence=sequence)
    if not allowed:
        return ProposalReviewResult(False, reason, state, proposal, decision)
    assert proposal is not None
    reviewed = RepairProposal(**{**serialize(proposal), "operator_review_status": decision.disposition})
    next_state = _replace_repair_proposal_for_review(state, reviewed, decision)
    eligible = decision.disposition == "approve_for_future_sandbox_planning"
    return ProposalReviewResult(
        True,
        "proposal_review_decision_accepted",
        next_state,
        reviewed,
        decision,
        future_sandbox_planning_eligible=eligible,
    )


def proposal_can_review_itself(proposal: RepairProposal) -> bool:
    _ = proposal
    return False


def make_sandbox_planning_state() -> SandboxPlanningState:
    return SandboxPlanningState(state_version="GSR-D1-A")


def make_sandbox_planning_authorization(
    proposal_id: str,
    *,
    allowed_planning_scope: tuple[str, ...],
    forbidden_planning_scope: tuple[str, ...] = (),
    allowed_workspace_class: str = "disposable_workspace_description_only",
    allowed_tool_classes: tuple[str, ...] = ("read_only_inspection", "test_selection_metadata"),
    forbidden_tool_classes: tuple[str, ...] = ("command_execution", "patch_generation", "source_mutation", "module_loading"),
    evidence_requirements: tuple[str, ...] = ("approved_gsr_c_future_sandbox_planning_marker",),
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    one_shot: bool = True,
    decision_sequence: int = 0,
    expires_after_sequence: int | None = None,
    conditions: tuple[str, ...] = (),
    rationale: str = "operator authorized sandbox planning only",
    consumed: bool = False,
) -> SandboxPlanningAuthorization:
    return SandboxPlanningAuthorization(
        authorization_id=stable_id("gsr-d-sandbox-planning-authorization", proposal_id, allowed_planning_scope, decision_sequence),
        proposal_id=proposal_id,
        operator_authority=operator_authority,
        allowed_planning_scope=allowed_planning_scope,
        forbidden_planning_scope=forbidden_planning_scope,
        allowed_workspace_class=allowed_workspace_class,
        allowed_tool_classes=allowed_tool_classes,
        forbidden_tool_classes=forbidden_tool_classes,
        evidence_requirements=evidence_requirements,
        one_shot=one_shot,
        decision_sequence=decision_sequence,
        expires_after_sequence=expires_after_sequence,
        conditions=conditions,
        rationale=rationale,
        consumed=consumed,
    )


def authorize_sandbox_plan_creation(
    proposal_state: DiagnosisProposalState,
    planning_state: SandboxPlanningState,
    authorization: SandboxPlanningAuthorization | None,
    *,
    proposal_id: str,
    sequence: int,
) -> SandboxPlanCreationResult:
    allowed, reason = _sandbox_planning_authorization_allows(
        proposal_state,
        planning_state,
        authorization,
        proposal_id=proposal_id,
        sequence=sequence,
    )
    if not allowed:
        return SandboxPlanCreationResult(False, reason, planning_state, authorization)
    assert authorization is not None
    next_state = SandboxPlanningState(
        **{
            **serialize(planning_state),
            "planning_authorization_ids": tuple(dict.fromkeys(planning_state.planning_authorization_ids + (authorization.authorization_id,))),
            "consumed_planning_authorization_ids": tuple(dict.fromkeys(planning_state.consumed_planning_authorization_ids + (authorization.authorization_id,))),
        }
    )
    return SandboxPlanCreationResult(True, "sandbox_planning_authorization_accepted", next_state, authorization)


def create_inert_sandbox_plan(
    proposal_state: DiagnosisProposalState,
    planning_state: SandboxPlanningState,
    authorization: SandboxPlanningAuthorization,
    *,
    proposal_id: str,
    disposable_workspace_description: str,
    repository_snapshot_description: str,
    files_or_components_in_scope: tuple[str, ...],
    forbidden_files_or_components: tuple[str, ...],
    allowed_tool_classes: tuple[str, ...],
    forbidden_tool_classes: tuple[str, ...],
    allowed_command_categories: tuple[str, ...],
    forbidden_command_categories: tuple[str, ...],
    test_selection: tuple[str, ...],
    focused_test_requirements: tuple[str, ...],
    adjacent_test_requirements: tuple[str, ...],
    live_runtime_evidence_requirements: tuple[str, ...],
    provider_model_restrictions: tuple[str, ...],
    network_restrictions: tuple[str, ...],
    memory_write_restrictions: tuple[str, ...],
    source_mutation_restrictions: tuple[str, ...],
    success_criteria: tuple[str, ...],
    failure_criteria: tuple[str, ...],
    rollback_proof_requirements: tuple[str, ...],
    cleanup_proof_requirements: tuple[str, ...],
    artifact_retention_policy: str,
    execution_budget_metadata: tuple[str, ...] = (),
    module_attachment: Mapping[str, Any] | None = None,
    creation_sequence: int = 0,
    expiration_sequence: int | None = None,
) -> SandboxPlanCreationResult:
    allowed, reason = _sandbox_plan_creation_allows(
        proposal_state,
        planning_state,
        authorization,
        proposal_id=proposal_id,
        files_or_components_in_scope=files_or_components_in_scope,
        forbidden_files_or_components=forbidden_files_or_components,
        allowed_tool_classes=allowed_tool_classes,
        forbidden_tool_classes=forbidden_tool_classes,
        allowed_command_categories=allowed_command_categories,
        forbidden_command_categories=forbidden_command_categories,
        provider_model_restrictions=provider_model_restrictions,
        network_restrictions=network_restrictions,
        memory_write_restrictions=memory_write_restrictions,
        source_mutation_restrictions=source_mutation_restrictions,
        success_criteria=success_criteria,
        failure_criteria=failure_criteria,
        rollback_proof_requirements=rollback_proof_requirements,
        cleanup_proof_requirements=cleanup_proof_requirements,
        artifact_retention_policy=artifact_retention_policy,
        content_parts=(
            disposable_workspace_description,
            repository_snapshot_description,
            artifact_retention_policy,
            *files_or_components_in_scope,
            *forbidden_files_or_components,
            *allowed_tool_classes,
            *forbidden_tool_classes,
            *allowed_command_categories,
            *forbidden_command_categories,
            *test_selection,
            *focused_test_requirements,
            *adjacent_test_requirements,
            *live_runtime_evidence_requirements,
            *provider_model_restrictions,
            *network_restrictions,
            *memory_write_restrictions,
            *source_mutation_restrictions,
            *success_criteria,
            *failure_criteria,
            *rollback_proof_requirements,
            *cleanup_proof_requirements,
            *execution_budget_metadata,
        ),
    )
    if not allowed:
        return SandboxPlanCreationResult(False, reason, planning_state, authorization)
    plan_id = stable_id("gsr-d-sandbox-plan", proposal_id, authorization.authorization_id, creation_sequence)
    module_plan: ModuleAttachmentPlan | None = None
    module_plan_id: str | None = None
    if module_attachment is not None:
        module_allowed, module_reason = _module_attachment_plan_allows(module_attachment)
        if not module_allowed:
            return SandboxPlanCreationResult(False, module_reason, planning_state, authorization)
        module_plan_id = stable_id("gsr-d-module-attachment-plan", proposal_id, plan_id, module_attachment.get("module_identifier"), creation_sequence)
        module_plan = ModuleAttachmentPlan(
            attachment_plan_id=module_plan_id,
            proposal_id=proposal_id,
            sandbox_plan_id=plan_id,
            module_identifier=str(module_attachment["module_identifier"]),
            module_type=str(module_attachment["module_type"]),
            source_package_description=str(module_attachment["source_package_description"]),
            required_interfaces=tuple(module_attachment["required_interfaces"]),
            requested_permissions=tuple(module_attachment["requested_permissions"]),
            forbidden_permissions=tuple(module_attachment["forbidden_permissions"]),
            data_access_boundaries=tuple(module_attachment["data_access_boundaries"]),
            network_boundaries=tuple(module_attachment["network_boundaries"]),
            memory_boundaries=tuple(module_attachment["memory_boundaries"]),
            tool_boundaries=tuple(module_attachment["tool_boundaries"]),
            lifecycle_hooks_described=tuple(module_attachment["lifecycle_hooks_described"]),
            activation_conditions=tuple(module_attachment["activation_conditions"]),
            deactivation_conditions=tuple(module_attachment["deactivation_conditions"]),
            rollback_or_removal_description=str(module_attachment["rollback_or_removal_description"]),
            compatibility_requirements=tuple(module_attachment["compatibility_requirements"]),
            validation_requirements=tuple(module_attachment["validation_requirements"]),
            creation_sequence=creation_sequence,
        )
    plan = SandboxEvaluationPlan(
        plan_id=plan_id,
        proposal_id=proposal_id,
        disposable_workspace=disposable_workspace_description,
        test_selection=test_selection,
        live_runtime_evidence_requirements=live_runtime_evidence_requirements,
        provider_model_restrictions=provider_model_restrictions,
        memory_write_restrictions=memory_write_restrictions,
        success_criteria=success_criteria,
        failure_criteria=failure_criteria,
        rollback_proof=rollback_proof_requirements,
        artifact_retention_policy=artifact_retention_policy,
        planning_authorization_id=authorization.authorization_id,
        repository_snapshot_description=repository_snapshot_description,
        files_or_components_in_scope=files_or_components_in_scope,
        forbidden_files_or_components=forbidden_files_or_components,
        allowed_tool_classes=allowed_tool_classes,
        forbidden_tool_classes=forbidden_tool_classes,
        allowed_command_categories=allowed_command_categories,
        forbidden_command_categories=forbidden_command_categories,
        focused_test_requirements=focused_test_requirements,
        adjacent_test_requirements=adjacent_test_requirements,
        network_restrictions=network_restrictions,
        source_mutation_restrictions=source_mutation_restrictions,
        rollback_proof_requirements=rollback_proof_requirements,
        cleanup_proof_requirements=cleanup_proof_requirements,
        execution_budget_metadata=execution_budget_metadata,
        module_attachment_plan_id=module_plan_id,
        creation_sequence=creation_sequence,
        expiration_sequence=expiration_sequence,
    )
    plan_index = dict(planning_state.plan_ids_by_proposal)
    plan_index[proposal_id] = tuple(dict.fromkeys(plan_index.get(proposal_id, ()) + (plan.plan_id,)))
    attachment_index = dict(planning_state.attachment_plan_ids_by_sandbox_plan)
    if module_plan is not None:
        attachment_index[plan.plan_id] = (module_plan.attachment_plan_id,)
    next_state = SandboxPlanningState(
        **{
            **serialize(planning_state),
            "sandbox_plans": planning_state.sandbox_plans + (serialize(plan),),
            "module_attachment_plans": planning_state.module_attachment_plans + ((serialize(module_plan),) if module_plan is not None else ()),
            "pending_plan_review_queue": tuple(dict.fromkeys(planning_state.pending_plan_review_queue + (plan.plan_id,))),
            "plan_ids_by_proposal": plan_index,
            "attachment_plan_ids_by_sandbox_plan": attachment_index,
        }
    )
    return SandboxPlanCreationResult(
        True,
        "inert_sandbox_plan_created",
        next_state,
        authorization,
        plan,
        module_plan,
        planning_authorization_consumed=authorization.authorization_id in planning_state.consumed_planning_authorization_ids,
    )


def _normalized_observation_signature(
    source_subsystem: str,
    expected_transition: str,
    observed_transition: str,
    objective_id: str,
    first_incorrect_transition: str,
) -> str:
    parts = (source_subsystem, expected_transition, observed_transition, objective_id, first_incorrect_transition)
    return "|".join(" ".join(str(part).lower().strip().split()) for part in parts)


def _ledger_entry_payload(ledger: ObservationLedgerState, entry_id: str) -> dict[str, Any] | None:
    for payload in ledger.entries:
        if payload.get("ledger_entry_id") == entry_id:
            return payload
    return None


def _review_decision_allows(
    entry: ObservationLedgerEntry,
    decision: ObservationReviewDecision,
    sequence: int,
) -> tuple[bool, str]:
    if decision.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False, "operator_authority_required"
    if decision.consumed:
        return False, "decision_consumed"
    if decision.one_shot is not True:
        return False, "one_shot_review_required"
    if decision.expires_after_sequence is not None and sequence > decision.expires_after_sequence:
        return False, "decision_expired"
    if decision.ledger_entry_id != entry.ledger_entry_id:
        return False, "decision_entry_mismatch"
    if decision.decision != "approve":
        return False, "approval_required"
    if decision.allowed_transition not in OBSERVATION_LEDGER_STATES:
        return False, "unknown_ledger_state"
    if decision.retention_policy not in OBSERVATION_RETENTION_POLICIES:
        return False, "unknown_retention_policy"
    return True, "review_decision_valid"


def _entry_for_review(
    entry: ObservationLedgerEntry,
    decision: ObservationReviewDecision,
) -> ObservationLedgerEntry | None:
    transition = decision.allowed_transition
    if transition == "pending_review" or transition == "raw" or transition == "validated":
        return None
    if transition == "duplicate" and not decision.duplicate_of:
        return None
    if transition == "superseded" and not decision.supersedes:
        return None
    return ObservationLedgerEntry(
        **{
            **serialize(entry),
            "lifecycle_state": transition,
            "most_recent_sequence": decision.sequence,
            "corroboration_count": entry.corroboration_count + (1 if transition == "corroborated" else 0),
            "duplicate_of": decision.duplicate_of if transition == "duplicate" else entry.duplicate_of,
            "superseded_by": decision.supersedes if transition == "superseded" else entry.superseded_by,
            "review_status": "operator_reviewed",
            "operator_disposition": transition,
            "diagnosis_eligibility_status": "eligible_for_review" if transition == "diagnosis_review_eligible" else entry.diagnosis_eligibility_status,
            "retention_policy": decision.retention_policy,
            "expires_after_sequence": decision.expires_after_sequence if decision.retention_policy in {"retain_for_sequence_window", "expire_after_sequence"} else entry.expires_after_sequence,
            "audit_rationale": decision.rationale,
        }
    )


def _replace_ledger_entry(
    ledger: ObservationLedgerState,
    updated_entry: ObservationLedgerEntry,
    decision: ObservationReviewDecision,
) -> ObservationLedgerState:
    entries = tuple(
        serialize(updated_entry) if payload.get("ledger_entry_id") == updated_entry.ledger_entry_id else payload
        for payload in ledger.entries
    )
    duplicate_links = dict(ledger.duplicate_links)
    if updated_entry.duplicate_of:
        duplicate_links[updated_entry.ledger_entry_id] = updated_entry.duplicate_of
    supersession_links = dict(ledger.supersession_links)
    if updated_entry.superseded_by:
        supersession_links[updated_entry.ledger_entry_id] = updated_entry.superseded_by
    review_queue = tuple(entry_id for entry_id in ledger.review_queue if entry_id != updated_entry.ledger_entry_id)
    diagnosis_queue = ledger.diagnosis_review_queue
    if updated_entry.lifecycle_state == "diagnosis_review_eligible":
        diagnosis_queue = tuple(dict.fromkeys(diagnosis_queue + (updated_entry.ledger_entry_id,)))
    expired_entries = ledger.expired_entries
    if updated_entry.lifecycle_state == "expired":
        expired_entries = tuple(dict.fromkeys(expired_entries + (updated_entry.ledger_entry_id,)))
    suspended_entries = ledger.suspended_entries
    if updated_entry.lifecycle_state == "suspended":
        suspended_entries = tuple(dict.fromkeys(suspended_entries + (updated_entry.ledger_entry_id,)))
    return ObservationLedgerState(
        ledger_id=ledger.ledger_id,
        objective_id=ledger.objective_id,
        sequence=max(ledger.sequence, decision.sequence) + 1,
        entries=entries,
        evidence_index=dict(ledger.evidence_index),
        duplicate_links=duplicate_links,
        supersession_links=supersession_links,
        review_queue=review_queue,
        diagnosis_review_queue=diagnosis_queue,
        expired_entries=expired_entries,
        suspended_entries=suspended_entries,
        review_decision_ids=tuple(dict.fromkeys(ledger.review_decision_ids + (decision.decision_id,))),
    )


def _diagnosis_authorization_allows(
    ledger: ObservationLedgerState,
    state: DiagnosisProposalState,
    authorization: DiagnosisReviewAuthorization,
    *,
    sequence: int,
) -> tuple[bool, str, ObservationLedgerEntry | None]:
    if authorization.authorization_id in state.consumed_diagnosis_authorization_ids:
        return False, "diagnosis_authorization_already_consumed", None
    if authorization.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False, "operator_authority_required", None
    if authorization.consumed:
        return False, "diagnosis_authorization_consumed", None
    if authorization.one_shot is not True:
        return False, "one_shot_authorization_required", None
    if authorization.expires_after_sequence is not None and sequence > authorization.expires_after_sequence:
        return False, "diagnosis_authorization_expired", None
    entry_payload = _ledger_entry_payload(ledger, authorization.ledger_entry_id)
    if entry_payload is None:
        return False, "ledger_entry_not_found", None
    entry = deserialize(ObservationLedgerEntry, entry_payload)
    if entry.lifecycle_state != "diagnosis_review_eligible":
        return False, "ledger_entry_not_diagnosis_review_eligible", entry
    if entry.ledger_entry_id not in ledger.diagnosis_review_queue:
        return False, "ledger_entry_not_in_diagnosis_review_queue", entry
    if authorization.linked_objective_id is not None and authorization.linked_objective_id != entry.objective_id:
        return False, "authorization_objective_mismatch", entry
    if not authorization.allowed_diagnosis_scope:
        return False, "diagnosis_scope_required", entry
    if not entry.evidence_refs:
        return False, "ledger_entry_missing_evidence", entry
    missing = [evidence_id for evidence_id in entry.evidence_refs if evidence_id not in ledger.evidence_index]
    if missing:
        return False, "ledger_evidence_not_found", entry
    return True, "diagnosis_authorization_valid", entry


def _diagnosis_payload(state: DiagnosisProposalState, diagnosis_id: str) -> dict[str, Any] | None:
    for payload in state.diagnosis_candidates:
        if payload.get("diagnosis_id") == diagnosis_id:
            return payload
    return None


def _hypothesis_belongs_to_diagnosis(
    state: DiagnosisProposalState,
    diagnosis_id: str,
    hypothesis_id: str,
) -> bool:
    for payload in state.competing_hypotheses:
        if payload.get("diagnosis_id") == diagnosis_id and payload.get("hypothesis_id") == hypothesis_id:
            return True
    return False


def _diagnosis_review_decision_allows(
    state: DiagnosisProposalState,
    decision: DiagnosisReviewDecision,
    *,
    sequence: int,
) -> tuple[bool, str, DiagnosisCandidate | None]:
    if decision.decision_id in state.consumed_diagnosis_decision_ids:
        return False, "diagnosis_review_decision_already_consumed", None
    if decision.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False, "operator_authority_required", None
    if decision.consumed:
        return False, "diagnosis_review_decision_consumed", None
    if decision.one_shot is not True:
        return False, "one_shot_review_required", None
    if decision.expires_after_sequence is not None and sequence > decision.expires_after_sequence:
        return False, "diagnosis_review_decision_expired", None
    if decision.disposition not in DIAGNOSIS_DISPOSITIONS:
        return False, "unknown_diagnosis_disposition", None
    payload = _diagnosis_payload(state, decision.diagnosis_id)
    if payload is None:
        return False, "diagnosis_not_found", None
    diagnosis = deserialize(DiagnosisCandidate, payload)
    if diagnosis.provisional is not True:
        return False, "diagnosis_not_provisional", diagnosis
    if decision.operator_authority == diagnosis.diagnosis_id:
        return False, "diagnosis_cannot_self_review", diagnosis
    if decision.selected_hypothesis_id is not None and not _hypothesis_belongs_to_diagnosis(state, diagnosis.diagnosis_id, decision.selected_hypothesis_id):
        return False, "selected_hypothesis_not_in_diagnosis", diagnosis
    return True, "diagnosis_review_decision_valid", diagnosis


def _replace_diagnosis_candidate_for_review(
    state: DiagnosisProposalState,
    reviewed: DiagnosisCandidate,
    decision: DiagnosisReviewDecision,
) -> DiagnosisProposalState:
    candidates = tuple(
        serialize(reviewed) if payload.get("diagnosis_id") == reviewed.diagnosis_id else payload
        for payload in state.diagnosis_candidates
    )
    eligible = state.proposal_drafting_eligible_diagnoses
    rejected = state.rejected_diagnoses
    unresolved = state.unresolved_diagnoses
    insufficient = state.insufficient_evidence_diagnoses
    non_defect = state.non_defect_diagnoses
    duplicate = state.duplicate_diagnoses
    suspended = state.suspended_diagnoses
    expired = state.expired_diagnoses
    deeper = state.deeper_design_diagnoses
    if decision.disposition == "accepted_for_proposal_drafting":
        eligible = tuple(dict.fromkeys(eligible + (reviewed.diagnosis_id,)))
    elif decision.disposition == "rejected":
        rejected = tuple(dict.fromkeys(rejected + (reviewed.diagnosis_id,)))
    elif decision.disposition == "competing_hypothesis_unresolved":
        unresolved = tuple(dict.fromkeys(unresolved + (reviewed.diagnosis_id,)))
    elif decision.disposition == "insufficient_evidence":
        insufficient = tuple(dict.fromkeys(insufficient + (reviewed.diagnosis_id,)))
    elif decision.disposition == "non_defect":
        non_defect = tuple(dict.fromkeys(non_defect + (reviewed.diagnosis_id,)))
    elif decision.disposition == "duplicate_diagnosis":
        duplicate = tuple(dict.fromkeys(duplicate + (reviewed.diagnosis_id,)))
    elif decision.disposition == "suspended":
        suspended = tuple(dict.fromkeys(suspended + (reviewed.diagnosis_id,)))
    elif decision.disposition == "expired":
        expired = tuple(dict.fromkeys(expired + (reviewed.diagnosis_id,)))
    elif decision.disposition == "deeper_design_required":
        deeper = tuple(dict.fromkeys(deeper + (reviewed.diagnosis_id,)))
    return DiagnosisProposalState(
        **{
            **serialize(state),
            "diagnosis_candidates": candidates,
            "diagnosis_review_decisions": state.diagnosis_review_decisions + (serialize(decision),),
            "consumed_diagnosis_decision_ids": tuple(dict.fromkeys(state.consumed_diagnosis_decision_ids + (decision.decision_id,))),
            "proposal_drafting_eligible_diagnoses": eligible,
            "rejected_diagnoses": rejected,
            "unresolved_diagnoses": unresolved,
            "insufficient_evidence_diagnoses": insufficient,
            "non_defect_diagnoses": non_defect,
            "duplicate_diagnoses": duplicate,
            "suspended_diagnoses": suspended,
            "expired_diagnoses": expired,
            "deeper_design_diagnoses": deeper,
        }
    )


def _sandbox_planning_authorization_allows(
    proposal_state: DiagnosisProposalState,
    planning_state: SandboxPlanningState,
    authorization: SandboxPlanningAuthorization | None,
    *,
    proposal_id: str,
    sequence: int,
) -> tuple[bool, str]:
    if proposal_id not in proposal_state.future_sandbox_planning_eligible_proposals:
        return False, "proposal_not_future_sandbox_planning_eligible"
    if authorization is None:
        return False, "sandbox_planning_authorization_required"
    if authorization.authorization_id in planning_state.consumed_planning_authorization_ids:
        return False, "sandbox_planning_authorization_already_consumed"
    if authorization.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False, "operator_authority_required"
    if authorization.consumed:
        return False, "sandbox_planning_authorization_consumed"
    if authorization.one_shot is not True:
        return False, "one_shot_authorization_required"
    if authorization.expires_after_sequence is not None and sequence > authorization.expires_after_sequence:
        return False, "sandbox_planning_authorization_expired"
    if authorization.proposal_id != proposal_id:
        return False, "sandbox_planning_authorization_target_mismatch"
    if not authorization.allowed_planning_scope:
        return False, "planning_scope_required"
    if set(authorization.allowed_planning_scope).intersection(authorization.forbidden_planning_scope):
        return False, "planning_scope_overlaps_forbidden_scope"
    if not authorization.allowed_workspace_class.strip():
        return False, "workspace_class_required"
    if not authorization.evidence_requirements:
        return False, "evidence_requirements_required"
    return True, "sandbox_planning_authorization_valid"


def _sandbox_plan_creation_allows(
    proposal_state: DiagnosisProposalState,
    planning_state: SandboxPlanningState,
    authorization: SandboxPlanningAuthorization,
    *,
    proposal_id: str,
    files_or_components_in_scope: tuple[str, ...],
    forbidden_files_or_components: tuple[str, ...],
    allowed_tool_classes: tuple[str, ...],
    forbidden_tool_classes: tuple[str, ...],
    allowed_command_categories: tuple[str, ...],
    forbidden_command_categories: tuple[str, ...],
    provider_model_restrictions: tuple[str, ...],
    network_restrictions: tuple[str, ...],
    memory_write_restrictions: tuple[str, ...],
    source_mutation_restrictions: tuple[str, ...],
    success_criteria: tuple[str, ...],
    failure_criteria: tuple[str, ...],
    rollback_proof_requirements: tuple[str, ...],
    cleanup_proof_requirements: tuple[str, ...],
    artifact_retention_policy: str,
    content_parts: tuple[str, ...],
) -> tuple[bool, str]:
    if proposal_id not in proposal_state.future_sandbox_planning_eligible_proposals:
        return False, "proposal_not_future_sandbox_planning_eligible"
    if authorization.authorization_id not in planning_state.consumed_planning_authorization_ids:
        return False, "consumed_sandbox_planning_authorization_required"
    if authorization.proposal_id != proposal_id:
        return False, "sandbox_planning_authorization_target_mismatch"
    if set(("sandbox_plan_drafting",)).isdisjoint(authorization.allowed_planning_scope):
        return False, "sandbox_planning_scope_mismatch"
    if "sandbox_plan_drafting" in authorization.forbidden_planning_scope:
        return False, "sandbox_planning_scope_forbidden"
    if any(payload.get("planning_authorization_id") == authorization.authorization_id for payload in planning_state.sandbox_plans):
        return False, "sandbox_planning_authorization_already_used_for_plan"
    if set(files_or_components_in_scope).intersection(forbidden_files_or_components):
        return False, "file_scope_overlaps_forbidden_scope"
    if set(allowed_tool_classes).intersection(forbidden_tool_classes):
        return False, "tool_class_overlaps_forbidden_tool_class"
    if set(allowed_command_categories).intersection(forbidden_command_categories):
        return False, "command_category_overlaps_forbidden_category"
    if not set(allowed_tool_classes).issubset(set(authorization.allowed_tool_classes)):
        return False, "tool_class_outside_authorization"
    if set(allowed_tool_classes).intersection(authorization.forbidden_tool_classes):
        return False, "tool_class_forbidden_by_authorization"
    required_fields = (
        (rollback_proof_requirements, "rollback_proof_requirements_required"),
        (cleanup_proof_requirements, "cleanup_proof_requirements_required"),
        (provider_model_restrictions, "provider_model_restrictions_required"),
        (network_restrictions, "network_restrictions_required"),
        (memory_write_restrictions, "memory_write_restrictions_required"),
        (source_mutation_restrictions, "source_mutation_restrictions_required"),
        (success_criteria, "success_criteria_required"),
        (failure_criteria, "failure_criteria_required"),
    )
    for values, reason in required_fields:
        if not values:
            return False, reason
    if not artifact_retention_policy.strip():
        return False, "artifact_retention_policy_required"
    if _contains_executable_plan_content(content_parts):
        return False, "executable_plan_content_prohibited"
    return True, "sandbox_plan_creation_valid"


def _module_attachment_plan_allows(payload: Mapping[str, Any]) -> tuple[bool, str]:
    required = (
        "module_identifier",
        "module_type",
        "source_package_description",
        "required_interfaces",
        "requested_permissions",
        "forbidden_permissions",
        "data_access_boundaries",
        "network_boundaries",
        "memory_boundaries",
        "tool_boundaries",
        "lifecycle_hooks_described",
        "activation_conditions",
        "deactivation_conditions",
        "rollback_or_removal_description",
        "compatibility_requirements",
        "validation_requirements",
    )
    for key in required:
        value = payload.get(key)
        if value in (None, "", ()):
            return False, f"{key}_required"
    if payload.get("module_type") not in {"python_module", "runtime_adapter", "tool_adapter", "capability_module"}:
        return False, "module_type_not_allowed"
    if set(payload["requested_permissions"]).intersection(payload["forbidden_permissions"]):
        return False, "module_permission_overlap"
    if _contains_executable_plan_content(tuple(str(value) for value in payload.values())):
        return False, "executable_module_attachment_content_prohibited"
    return True, "module_attachment_plan_valid"


def _contains_executable_plan_content(parts: tuple[str, ...]) -> bool:
    blocked_markers = (
        "```",
        "@@",
        "--- a/",
        "+++ b/",
        "diff --git",
        "apply_patch",
        "git ",
        "git clone",
        "powershell",
        "pwsh",
        "cmd.exe",
        "bash ",
        "python -",
        "python.exe",
        "pytest ",
        "\"command\":",
        "tool_call",
        "write this file",
        "replace the code",
        "importlib",
        "__import__",
        "load_module",
        "attach_module",
        "registry_mutation",
        " deploy ",
        "\ndeploy ",
    )
    lowered = "\n".join(str(part).lower() for part in parts)
    return any(marker in lowered for marker in blocked_markers)


def _contains_executable_proposal_content(parts: tuple[str, ...]) -> bool:
    blocked_markers = (
        "```",
        "@@",
        "--- a/",
        "+++ b/",
        "diff --git",
        "apply_patch",
        "git ",
        "powershell",
        "cmd.exe",
        "python -",
        "python.exe",
        "pytest ",
        "rm ",
        "\ndel ",
        " del /",
        "copy ",
        "move ",
        "invoke-",
        "start-process",
        "tool_call",
        "\"command\":",
        "write this file",
        "replace the code",
    )
    lowered = "\n".join(str(part).lower() for part in parts)
    return any(marker in lowered for marker in blocked_markers)


def _proposal_payload(state: DiagnosisProposalState, proposal_id: str) -> dict[str, Any] | None:
    for payload in state.repair_proposals:
        if payload.get("proposal_id") == proposal_id:
            return payload
    return None


def _proposal_review_decision_allows(
    state: DiagnosisProposalState,
    decision: ProposalReviewDecision,
    *,
    sequence: int,
) -> tuple[bool, str, RepairProposal | None]:
    if decision.decision_id in state.consumed_proposal_decision_ids:
        return False, "proposal_review_decision_already_consumed", None
    if decision.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False, "operator_authority_required", None
    if decision.consumed:
        return False, "proposal_review_decision_consumed", None
    if decision.one_shot is not True:
        return False, "one_shot_review_required", None
    if decision.expires_after_sequence is not None and sequence > decision.expires_after_sequence:
        return False, "proposal_review_decision_expired", None
    if decision.disposition not in PROPOSAL_REVIEW_DISPOSITIONS:
        return False, "unknown_proposal_review_disposition", None
    payload = _proposal_payload(state, decision.proposal_id)
    if payload is None:
        return False, "proposal_not_found", None
    proposal = deserialize(RepairProposal, payload)
    if proposal.proposal_only_status != "PROPOSAL_ONLY":
        return False, "proposal_not_proposal_only", proposal
    if decision.operator_authority == proposal.proposal_id:
        return False, "proposal_cannot_self_review", proposal
    return True, "proposal_review_decision_valid", proposal


def _replace_repair_proposal_for_review(
    state: DiagnosisProposalState,
    reviewed: RepairProposal,
    decision: ProposalReviewDecision,
) -> DiagnosisProposalState:
    proposals = tuple(
        serialize(reviewed) if payload.get("proposal_id") == reviewed.proposal_id else payload
        for payload in state.repair_proposals
    )
    rejected = state.rejected_proposals
    revision = state.revision_required_proposals
    deferred = state.deferred_proposals
    suspended = state.suspended_proposals
    expired = state.expired_proposals
    deeper = state.deeper_design_proposals
    if decision.disposition == "reject":
        rejected = tuple(dict.fromkeys(rejected + (reviewed.proposal_id,)))
    elif decision.disposition == "revise":
        revision = tuple(dict.fromkeys(revision + (reviewed.proposal_id,)))
    elif decision.disposition == "defer":
        deferred = tuple(dict.fromkeys(deferred + (reviewed.proposal_id,)))
    elif decision.disposition == "suspend":
        suspended = tuple(dict.fromkeys(suspended + (reviewed.proposal_id,)))
    elif decision.disposition == "expire":
        expired = tuple(dict.fromkeys(expired + (reviewed.proposal_id,)))
    elif decision.disposition == "deeper_design_required":
        deeper = tuple(dict.fromkeys(deeper + (reviewed.proposal_id,)))
    future = state.future_sandbox_planning_eligible_proposals
    if decision.disposition == "approve_for_future_sandbox_planning":
        future = tuple(dict.fromkeys(future + (reviewed.proposal_id,)))
    return DiagnosisProposalState(
        **{
            **serialize(state),
            "repair_proposals": proposals,
            "proposal_review_decisions": state.proposal_review_decisions + (serialize(decision),),
            "consumed_proposal_decision_ids": tuple(dict.fromkeys(state.consumed_proposal_decision_ids + (decision.decision_id,))),
            "pending_proposal_review_queue": tuple(item for item in state.pending_proposal_review_queue if item != reviewed.proposal_id),
            "future_sandbox_planning_eligible_proposals": future,
            "rejected_proposals": rejected,
            "revision_required_proposals": revision,
            "deferred_proposals": deferred,
            "suspended_proposals": suspended,
            "expired_proposals": expired,
            "deeper_design_proposals": deeper,
        }
    )


def serialize(value: Any) -> dict[str, Any]:
    if not is_dataclass(value):
        raise TypeError("GSR-A serialization only accepts dataclass instances")
    return asdict(value)


def deserialize(cls: type[Any], payload: Mapping[str, Any]) -> Any:
    converted = {}
    field_types = {item.name: item.type for item in fields(cls)}
    for key, value in dict(payload).items():
        field_type = field_types.get(key)
        converted[key] = _restore_json_value(field_type, value)
    return cls(**converted)


def _restore_json_value(field_type: Any, value: Any) -> Any:
    if get_origin(field_type) is tuple or str(field_type).startswith("tuple["):
        return tuple(value or ())
    return value


def build_gsr_a_foundation_report() -> dict[str, Any]:
    objective = make_development_objective("Create an inert governed self-regulation foundation.")
    observation = make_observation(
        objective.objective_id,
        source_subsystem="semantic_runtime",
        observed_behavior="runtime behavior can be observed",
        expected_behavior="observation remains evidence only",
        evidence_references=("reports/semantic_runtime_closure.md",),
        user_visible=True,
    )
    diagnosis = make_diagnosis_candidate(
        (observation,),
        first_incorrect_transition="observation_to_authorized_repair_missing_gate",
        suspected_mechanism="distributed_authority_without_explicit_gsr_state",
        supporting_evidence=(observation.observation_id,),
    )
    proposal = make_repair_proposal(
        diagnosis,
        proposed_change="add inert GSR-A state contracts",
        files_or_components_in_scope=("orchestration/runtime/gsr_a_governed_self_regulation.py",),
        forbidden_files_or_components=("DELTA.py", "live_router", "provider_runtime"),
        validation_plan=("py_compile", "focused_gsr_a_tests"),
    )
    sandbox = make_sandbox_plan(proposal)
    return {
        "stage": "GSR-A",
        "status": "INERT_GOVERNED_SCAFFOLD",
        "contracts": {
            "objective": serialize(objective),
            "observation": serialize(observation),
            "diagnosis": serialize(diagnosis),
            "proposal": serialize(proposal),
            "sandbox": serialize(sandbox),
        },
        "lifecycle_states": LIFECYCLE_STATES,
        "safety": safety_metadata(),
        "live_runtime_integration_performed": False,
    }


def write_gsr_a_report(path: Path) -> dict[str, Any]:
    report = build_gsr_a_foundation_report()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _decision_allows(
    decision: GovernanceDecision | None,
    *,
    proposal_id: str | None,
    scope: str,
    sequence: int,
) -> bool:
    if decision is None:
        return False
    if decision.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False
    if decision.decision != "approve":
        return False
    if proposal_id and decision.proposal_id != proposal_id:
        return False
    if scope not in decision.allowed_scope:
        return False
    if decision.consumed:
        return False
    if decision.expires_after_sequence is not None and sequence > decision.expires_after_sequence:
        return False
    return True
