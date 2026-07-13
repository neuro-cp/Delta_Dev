"""GSR-A inert governed self-regulation state model.

This module defines serializable contracts for governed self-regulating
cognition. It does not observe live runtime state, edit source, run sandboxes,
call providers, execute local models, write memory, schedule background work,
or authorize itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping, get_args, get_origin

from orchestration.runtime.delta_1_0_common import safety_metadata as base_safety_metadata
from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime import rc4_governed_action_runtime as rc4


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

SANDBOX_PLAN_REVIEW_DISPOSITIONS = (
    "approve_for_future_sandbox_execution",
    "reject",
    "revise",
    "defer",
    "deeper_design_required",
    "suspend",
    "expire",
)

SANDBOX_PLAN_BLOCKING_DISPOSITIONS = {
    "reject",
    "revise",
    "defer",
    "deeper_design_required",
    "suspend",
    "expire",
}

GSR_E1_LIFECYCLE_STATES = (
    "objective_pending",
    "objective_authorized",
    "cycle_active",
    "observation_requested",
    "observation_review_pending",
    "diagnosis_authorization_pending",
    "diagnosis_review_pending",
    "proposal_review_pending",
    "sandbox_planning_authorization_pending",
    "sandbox_plan_review_pending",
    "future_sandbox_execution_eligible",
    "paused",
    "suspended",
    "rejected",
    "deeper_design_required",
    "completed",
    "rollback_review_required",
    "interrupted",
)

GSR_E1_UNREACHABLE_EXECUTION_STATES = (
    "sandbox_executing",
    "applying",
    "module_attaching",
    "command_running",
    "patching",
)

GSR_E1_FORBIDDEN_TRANSITION_SCOPES = (
    "sandbox_execution",
    "workspace_creation",
    "command_execution",
    "tool_invocation",
    "patch_generation",
    "source_mutation",
    "module_loading",
    "registry_mutation",
    "application_authorization",
    "application",
    "provider_call",
    "model_inference",
    "memory_write",
    "persistence",
    "scheduler",
    "thread",
    "background_task",
)

GSR_E2_FORBIDDEN_EXECUTION_SCOPES = (
    "live_source_mutation",
    "source_mutation",
    "patch_application",
    "git_stage",
    "git_commit",
    "git_push",
    "merge",
    "deployment",
    "publication",
    "production_application",
    "module_activation",
    "registry_mutation",
    "canonical_memory_write",
    "provider_call",
    "model_inference",
    "scheduler",
    "thread",
    "background_loop",
    "autonomous_retry",
    "recursive_objective_continuation",
    "additional_execution_attempt",
    "unrestricted_filesystem",
    "unrestricted_network",
    "credential_access",
    "DELTA-75",
)

GSR_E2_UNRESTRICTED_POLICY_MARKERS = ("*", "unrestricted", "ambient", "wildcard")

GSR_E2_REQUIRED_BUDGET_FIELDS = (
    "max_commands",
    "max_tool_calls",
    "max_elapsed_units",
    "max_output_bytes",
    "max_artifact_count",
    "max_workspace_writes",
    "max_processes",
    "max_retries",
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


@dataclass(frozen=True)
class SandboxPlanReviewDecision:
    decision_id: str
    plan_id: str
    operator_authority: str
    disposition: str
    rationale: str
    allowed_execution_scope: tuple[str, ...]
    forbidden_execution_scope: tuple[str, ...]
    allowed_tool_classes: tuple[str, ...]
    forbidden_tool_classes: tuple[str, ...]
    allowed_command_categories: tuple[str, ...]
    forbidden_command_categories: tuple[str, ...]
    conditions: tuple[str, ...]
    one_shot: bool
    decision_sequence: int
    expires_after_sequence: int | None
    consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxPlanReviewResult:
    accepted: bool
    reason: str
    state: SandboxPlanningState
    plan: SandboxEvaluationPlan | None = None
    decision: SandboxPlanReviewDecision | None = None
    future_sandbox_execution_eligible: bool = False
    disposition: str = ""
    sandbox_authorization_created: bool = False
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


@dataclass(frozen=True)
class GovernedObjectiveCycle:
    cycle_id: str
    objective_id: str
    objective_snapshot: dict[str, Any]
    current_stage: str
    current_substage: str
    sequence: int
    cycle_status: str
    active_artifact_type: str
    active_artifact_id: str
    observation_ledger_reference: str | None = None
    diagnosis_state_reference: str | None = None
    sandbox_planning_state_reference: str | None = None
    completed_stage_markers: tuple[str, ...] = ()
    pending_transition_request_ids: tuple[str, ...] = ()
    consumed_transition_authorization_ids: tuple[str, ...] = ()
    blocked_transition_ids: tuple[str, ...] = ()
    pause_reason: str = ""
    suspension_reason: str = ""
    rejection_reason: str = ""
    deeper_design_reason: str = ""
    rollback_required: bool = False
    interruption_marker: str = ""
    last_successful_transition: str = ""
    last_failed_transition: str = ""
    operator_attention_required: bool = True
    autonomous_continuation_prohibited: bool = True
    background_execution_prohibited: bool = True
    persistence_prohibited: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObjectiveCycleTransitionRequest:
    request_id: str
    cycle_id: str
    from_stage: str
    requested_stage: str
    requested_substage: str
    artifact_type: str
    artifact_id: str
    eligibility_claims: tuple[str, ...]
    required_evidence_refs: tuple[str, ...]
    required_authorization_scope: tuple[str, ...]
    forbidden_scope: tuple[str, ...]
    requested_sequence: int
    request_rationale: str
    creates_execution: bool = False
    creates_background_work: bool = False
    creates_persistence: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObjectiveCycleTransitionAuthorization:
    authorization_id: str
    cycle_id: str
    request_id: str
    operator_authority: str
    allowed_from_stage: str
    allowed_to_stage: str
    allowed_substage: str
    allowed_artifact_type: str
    allowed_artifact_id: str
    allowed_scope: tuple[str, ...]
    forbidden_scope: tuple[str, ...]
    conditions: tuple[str, ...]
    one_shot: bool
    decision_sequence: int
    expires_after_sequence: int | None
    consumed: bool = False
    rationale: str = "operator authorized inert objective-cycle transition"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObjectiveCycleTransitionRecord:
    transition_id: str
    cycle_id: str
    from_stage: str
    to_stage: str
    from_substage: str
    to_substage: str
    artifact_type: str
    artifact_id: str
    request_id: str
    authorization_id: str
    sequence: int
    result: str
    reason: str
    operator_controlled: bool = True
    execution_performed: bool = False
    automatic_continuation: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObjectiveCycleTransitionResult:
    accepted: bool
    reason: str
    previous_cycle: GovernedObjectiveCycle
    next_cycle: GovernedObjectiveCycle
    request: ObjectiveCycleTransitionRequest | None = None
    authorization: ObjectiveCycleTransitionAuthorization | None = None
    consumed_authorization: ObjectiveCycleTransitionAuthorization | None = None
    transition_record: ObjectiveCycleTransitionRecord | None = None
    eligibility_result: "ObjectiveCycleTransitionEligibilityResult | None" = None
    operator_attention_required: bool = True
    transition_applied: bool = False
    authorization_consumed: bool = False
    record_created: bool = False
    cycle_mutated: bool = False
    replacement_cycle_produced: bool = False
    automatic_continuation: bool = False
    execution_performed: bool = False
    sandbox_started: bool = False
    command_executed: bool = False
    tool_invoked: bool = False
    patch_created: bool = False
    source_mutated: bool = False
    module_loaded: bool = False
    application_authorized: bool = False
    application_performed: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    memory_written: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False


@dataclass(frozen=True)
class ObjectiveCycleTransitionEligibilityResult:
    accepted: bool
    reason: str
    cycle: GovernedObjectiveCycle
    request: ObjectiveCycleTransitionRequest | None = None
    authorization: ObjectiveCycleTransitionAuthorization | None = None
    eligible_for_operator_review: bool = False
    transition_applied: bool = False
    cycle_mutated: bool = False
    execution_performed: bool = False
    sandbox_started: bool = False
    command_executed: bool = False
    tool_invoked: bool = False
    patch_created: bool = False
    source_mutated: bool = False
    module_loaded: bool = False
    application_authorized: bool = False
    application_performed: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    memory_written: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxExecutionRequest:
    request_id: str
    cycle_id: str
    sandbox_plan_id: str
    sandbox_plan_version: str
    sandbox_plan_digest: str
    requested_execution_sequence: int
    requested_scope: tuple[str, ...]
    requested_workspace_policy: tuple[str, ...]
    requested_tool_allowlist: tuple[str, ...]
    requested_command_allowlist: tuple[str, ...]
    requested_network_policy: tuple[str, ...]
    requested_execution_budget: dict[str, int]
    requested_artifact_output_policy: tuple[str, ...]
    operator_review_required: bool = True
    execution_requested: bool = True
    execution_started: bool = False
    request_consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxExecutionAuthorization:
    authorization_id: str
    request_id: str
    cycle_id: str
    sandbox_plan_id: str
    sandbox_plan_version: str
    sandbox_plan_digest: str
    authorized_source_lifecycle_stage: str
    authorized_target_lifecycle_stage: str
    authorized_scope: tuple[str, ...]
    authorized_workspace_policy: tuple[str, ...]
    authorized_tool_allowlist: tuple[str, ...]
    authorized_command_allowlist: tuple[str, ...]
    authorized_network_policy: tuple[str, ...]
    authorized_execution_budget: dict[str, int]
    authorized_artifact_output_policy: tuple[str, ...]
    issued_sequence: int
    expires_after_sequence: int | None
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY
    one_shot: bool = True
    consumed: bool = False
    execution_authorized: bool = True
    execution_started: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxExecutionEligibilityResult:
    accepted: bool
    reason: str
    cycle: GovernedObjectiveCycle
    sandbox_plan: SandboxEvaluationPlan | None = None
    request: SandboxExecutionRequest | None = None
    authorization: SandboxExecutionAuthorization | None = None
    eligible_for_future_sandbox_execution: bool = False
    authorization_consumed: bool = False
    cycle_mutated: bool = False
    plan_mutated: bool = False
    execution_performed: bool = False
    execution_started: bool = False
    workspace_created: bool = False
    sandbox_started: bool = False
    command_executed: bool = False
    tool_invoked: bool = False
    network_accessed: bool = False
    patch_created: bool = False
    patch_applied: bool = False
    source_mutated: bool = False
    module_loaded: bool = False
    module_activated: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    memory_written: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False
    application_authorized: bool = False
    application_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxExecutionAttempt:
    attempt_id: str
    cycle_id: str
    sandbox_plan_id: str
    request_id: str
    authorization_id: str
    execution_sequence: int
    workspace_policy: tuple[str, ...]
    command_name: str
    normalized_arguments: tuple[str, ...]
    execution_budget: dict[str, int]
    workspace_root: str
    attempt_started: bool = False
    attempt_completed: bool = False
    authorization_consumed: bool = False
    cleanup_required: bool = True
    cleanup_verified: bool = False
    live_source_unchanged: bool = False
    operator_review_required: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxExecutionEvidence:
    attempt_id: str
    command_name: str
    normalized_arguments: tuple[str, ...]
    start_sequence: int
    end_sequence: int
    return_code: int
    stdout_summary: str
    stderr_summary: str
    output_truncated: bool
    artifact_manifest: tuple[str, ...]
    filesystem_write_manifest: tuple[str, ...]
    budget_observed: dict[str, int]
    cleanup_result: str
    live_source_integrity_status: str
    execution_performed: bool
    evaluation_performed: bool = False
    application_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxExecutionResult:
    accepted: bool
    reason: str
    cycle: GovernedObjectiveCycle
    sandbox_plan: SandboxEvaluationPlan | None = None
    request: SandboxExecutionRequest | None = None
    original_authorization: SandboxExecutionAuthorization | None = None
    consumed_authorization: SandboxExecutionAuthorization | None = None
    attempt: SandboxExecutionAttempt | None = None
    evidence: SandboxExecutionEvidence | None = None
    eligible_for_operator_review: bool = False
    execution_performed: bool = False
    execution_succeeded: bool = False
    cleanup_verified: bool = False
    live_source_unchanged: bool = False
    authorization_consumed: bool = False
    second_attempt_created: bool = False
    next_request_created: bool = False
    automatic_continuation: bool = False
    patch_applied: bool = False
    source_mutated: bool = False
    module_activated: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    memory_written: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False
    application_authorized: bool = False
    application_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxEvidenceFinding:
    code: str
    severity: str
    message: str
    source_field: str
    expected_value: str
    observed_value: str
    blocks_operator_acceptance: bool
    requires_deeper_design: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxEvidenceEvaluation:
    evaluation_id: str
    cycle_id: str
    plan_id: str
    attempt_id: str
    request_id: str
    authorization_id: str
    evidence_digest: str
    accepted_for_operator_review: bool
    classification: str
    reason: str
    findings: tuple[SandboxEvidenceFinding, ...]
    execution_started: bool
    execution_succeeded: bool
    command_failed: bool
    budget_compliant: bool
    output_within_policy: bool
    artifacts_within_policy: bool
    writes_within_policy: bool
    cleanup_verified: bool
    live_source_unchanged: bool
    evidence_complete: bool
    evidence_consistent: bool
    operator_review_required: bool = True
    application_authorized: bool = False
    application_performed: bool = False
    next_attempt_authorized: bool = False
    automatic_continuation: bool = False
    execution_authorization_created: bool = False
    lifecycle_transition_applied: bool = False
    next_request_created: bool = False
    authorization_consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxEvaluationDispositionRequest:
    disposition_request_id: str
    evaluation_id: str
    cycle_id: str
    plan_id: str
    attempt_id: str
    proposed_disposition: str
    request_id: str = ""
    authorization_id: str = ""
    evidence_digest: str = ""
    operator_review_required: bool = True
    application_requested: bool = False
    next_execution_requested: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxEvaluationDisposition:
    disposition_id: str
    disposition_request_id: str
    evaluation_id: str
    operator_authority: str
    accepted: bool
    decision: str
    reason: str
    issued_sequence: int
    one_shot: bool
    cycle_id: str = ""
    plan_id: str = ""
    attempt_id: str = ""
    request_id: str = ""
    authorization_id: str = ""
    evidence_digest: str = ""
    consumed: bool = False
    application_authorized: bool = False
    execution_authorized: bool = False
    automatic_continuation: bool = False
    lifecycle_transition_applied: bool = False
    source_mutation_authorized: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxEvaluationDispositionRecord:
    record_id: str
    evaluation_id: str
    disposition_request_id: str
    disposition_id: str
    cycle_id: str
    plan_id: str
    attempt_id: str
    request_id: str
    authorization_id: str
    evidence_digest: str
    operator_disposition: str
    operator_issued: bool
    issued_sequence: int
    disposition_applied: bool = True
    disposition_authority_consumed: bool = True
    accepted_evidence: bool = False
    rejected_evidence: bool = False
    revision_requested: bool = False
    more_evidence_requested: bool = False
    deeper_design_required: bool = False
    another_execution_requested_metadata_only: bool = False
    lifecycle_closure_requested_metadata_only: bool = False
    cleanup_failure_marked: bool = False
    live_source_integrity_failure_marked: bool = False
    application_authorized: bool = False
    execution_authorized: bool = False
    lifecycle_transition_applied: bool = False
    patch_created: bool = False
    patch_applied: bool = False
    source_mutated: bool = False
    module_activated: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    memory_written: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False
    automatic_continuation: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxEvaluationDispositionResult:
    accepted: bool
    reason: str
    evaluation: SandboxEvidenceEvaluation
    request: SandboxEvaluationDispositionRequest | None = None
    disposition: SandboxEvaluationDisposition | None = None
    original_disposition: SandboxEvaluationDisposition | None = None
    consumed_disposition: SandboxEvaluationDisposition | None = None
    disposition_record: SandboxEvaluationDispositionRecord | None = None
    disposition_applied: bool = False
    disposition_authority_consumed: bool = False
    record_created: bool = False
    evaluation_mutated: bool = False
    execution_started: bool = False
    sandbox_started: bool = False
    next_execution_authorized: bool = False
    application_authorized: bool = False
    application_performed: bool = False
    execution_authorized: bool = False
    lifecycle_transition_applied: bool = False
    patch_created: bool = False
    patch_applied: bool = False
    source_mutated: bool = False
    module_activated: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    memory_written: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False
    automatic_continuation: bool = False
    next_request_created: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ApplicationArtifact:
    artifact_id: str
    artifact_digest: str
    evaluation_id: str
    disposition_record_id: str
    cycle_id: str
    plan_id: str
    attempt_id: str
    request_id: str
    authorization_id: str
    evidence_digest: str
    target_file_set: tuple[str, ...]
    operation_set: tuple[str, ...]
    expected_pre_application_hashes: dict[str, str]
    target_scope: tuple[str, ...]
    artifact_present: bool = True
    binary_or_unsupported_content: bool = False
    module_activation_implied: bool = False
    scheduler_or_background_implied: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ApplicationRequest:
    application_request_id: str
    cycle_id: str
    plan_id: str
    attempt_id: str
    request_id: str
    authorization_id: str
    evaluation_id: str
    evidence_digest: str
    disposition_record_id: str
    proposed_application_artifact_id: str
    proposed_application_artifact_digest: str
    target_scope: tuple[str, ...]
    target_file_set: tuple[str, ...]
    expected_pre_application_hashes: dict[str, str]
    requested_operation_set: tuple[str, ...]
    requested_sequence: int
    application_requested: bool = True
    application_started: bool = False
    request_consumed: bool = False
    operator_review_required: bool = True
    immediate_application_authority: bool = False
    git_stage_authorized: bool = False
    git_commit_authorized: bool = False
    git_push_authorized: bool = False
    merge_authorized: bool = False
    deployment_authorized: bool = False
    publication_authorized: bool = False
    module_activation_authorized: bool = False
    provider_model_authorized: bool = False
    memory_write_authorized: bool = False
    persistence_authorized: bool = False
    scheduler_authorized: bool = False
    thread_authorized: bool = False
    background_task_authorized: bool = False
    lifecycle_transition_authorized: bool = False
    another_execution_authorized: bool = False
    automatic_continuation: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ApplicationAuthorization:
    application_authorization_id: str
    application_request_id: str
    cycle_id: str
    plan_id: str
    attempt_id: str
    evaluation_id: str
    evidence_digest: str
    disposition_record_id: str
    proposed_application_artifact_id: str
    proposed_application_artifact_digest: str
    authorized_target_scope: tuple[str, ...]
    authorized_target_file_set: tuple[str, ...]
    authorized_operation_set: tuple[str, ...]
    expected_pre_application_hashes: dict[str, str]
    issued_sequence: int
    expiration_sequence: int
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY
    one_shot: bool = True
    consumed: bool = False
    application_authorized_metadata: bool = True
    application_started: bool = False
    source_mutated: bool = False
    git_stage_authorized: bool = False
    git_commit_authorized: bool = False
    git_push_authorized: bool = False
    merge_authorized: bool = False
    deployment_authorized: bool = False
    publication_authorized: bool = False
    module_activation_authorized: bool = False
    provider_model_authorized: bool = False
    memory_write_authorized: bool = False
    persistence_authorized: bool = False
    scheduler_authorized: bool = False
    thread_authorized: bool = False
    background_task_authorized: bool = False
    lifecycle_transition_authorized: bool = False
    another_execution_authorized: bool = False
    automatic_continuation: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ApplicationEligibilityResult:
    accepted: bool
    reason: str
    evaluation: SandboxEvidenceEvaluation
    disposition_record: SandboxEvaluationDispositionRecord
    artifact: ApplicationArtifact | None = None
    request: ApplicationRequest | None = None
    authorization: ApplicationAuthorization | None = None
    eligible_for_future_application: bool = False
    application_performed: bool = False
    application_started: bool = False
    authorization_consumed: bool = False
    patch_created: bool = False
    patch_applied: bool = False
    source_mutated: bool = False
    files_written: bool = False
    git_diff_created: bool = False
    git_staged: bool = False
    git_committed: bool = False
    git_pushed: bool = False
    git_merged: bool = False
    deployed: bool = False
    published: bool = False
    module_loaded: bool = False
    module_activated: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    memory_written: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False
    lifecycle_transition_applied: bool = False
    next_request_created: bool = False
    automatic_continuation: bool = False
    execution_started: bool = False
    execution_authorized: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ApplicationPlanOperation:
    sequence: int
    operation: str
    target_path: str
    expected_current_hash: str | None = None
    expected_post_application_hash: str | None = None
    expected_absent_before: bool = False
    rollback_operation: str = ""
    rollback_artifact_id: str = ""
    rollback_target_path: str = ""
    rollback_expected_hash: str | None = None


@dataclass(frozen=True)
class ApplicationPlan:
    application_plan_id: str
    application_request_id: str
    application_authorization_id: str
    cycle_id: str
    plan_id: str
    attempt_id: str
    evaluation_id: str
    evidence_digest: str
    disposition_record_id: str
    artifact_id: str
    artifact_digest: str
    ordered_target_operations: tuple[ApplicationPlanOperation, ...]
    target_file_set: tuple[str, ...]
    expected_current_hashes: dict[str, str]
    expected_post_application_hashes: dict[str, str]
    rollback_metadata: tuple[dict[str, Any], ...]
    required_validation_commands: tuple[str, ...] = ()
    application_sequence: int = 0
    cleanup_requirements: tuple[str, ...] = ("verify_target_hashes",)
    operator_review_required: bool = True
    application_started: bool = False
    authorization_consumed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ApplicationTargetInspection:
    inspected_target_paths: tuple[str, ...]
    current_target_hashes: dict[str, str]
    target_existence_map: dict[str, bool]
    target_type_map: dict[str, str]
    unreadable_targets: tuple[str, ...] = ()
    oversized_targets: tuple[str, ...] = ()
    symlink_targets: tuple[str, ...] = ()
    live_source_read_only: bool = True
    source_mutated: bool = False
    files_written: bool = False
    process_started: bool = False
    thread_started: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ApplicationWorktreeStatus:
    modified_paths: tuple[str, ...] = ()
    staged_paths: tuple[str, ...] = ()
    untracked_paths: tuple[str, ...] = ()
    conflicted_paths: tuple[str, ...] = ()
    known_dirty_paths: tuple[str, ...] = ()
    expected_dirty_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplicationPreflightResult:
    accepted: bool
    reason: str
    eligibility_result: ApplicationEligibilityResult
    application_plan: ApplicationPlan
    artifact: ApplicationArtifact
    request: ApplicationRequest
    authorization: ApplicationAuthorization
    inspected_target_paths: tuple[str, ...] = ()
    current_target_hashes: dict[str, str] = field(default_factory=dict)
    target_existence_map: dict[str, bool] = field(default_factory=dict)
    target_type_map: dict[str, str] = field(default_factory=dict)
    worktree_classification: dict[str, tuple[str, ...]] = field(default_factory=dict)
    preconditions_match: bool = False
    rollback_ready: bool = False
    artifact_consistent: bool = False
    operation_order_valid: bool = False
    target_scope_valid: bool = False
    live_source_read_only: bool = True
    ready_for_future_application: bool = False
    authorization_consumed: bool = False
    application_started: bool = False
    patch_created: bool = False
    patch_applied: bool = False
    source_mutated: bool = False
    files_written: bool = False
    git_diff_created: bool = False
    git_staged: bool = False
    git_committed: bool = False
    git_pushed: bool = False
    git_merged: bool = False
    deployed: bool = False
    published: bool = False
    module_activated: bool = False
    provider_called: bool = False
    model_invoked: bool = False
    memory_written: bool = False
    persistence_performed: bool = False
    scheduler_started: bool = False
    thread_started: bool = False
    background_task_started: bool = False
    lifecycle_transition_applied: bool = False
    next_request_created: bool = False
    automatic_continuation: bool = False
    execution_started: bool = False
    execution_authorized: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObjectiveCycleStateBundle:
    cycle: GovernedObjectiveCycle
    observation_ledger_state: dict[str, Any] | None = None
    diagnosis_proposal_state: dict[str, Any] | None = None
    sandbox_planning_state: dict[str, Any] | None = None
    transition_requests: tuple[dict[str, Any], ...] = ()
    transition_authorizations: tuple[dict[str, Any], ...] = ()
    transition_records: tuple[dict[str, Any], ...] = ()
    consumed_request_ids: tuple[str, ...] = ()
    persistence_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


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


def make_sandbox_plan_review_decision(
    plan_id: str,
    *,
    disposition: str,
    rationale: str,
    allowed_execution_scope: tuple[str, ...],
    forbidden_execution_scope: tuple[str, ...] = (),
    allowed_tool_classes: tuple[str, ...] = (),
    forbidden_tool_classes: tuple[str, ...] = (),
    allowed_command_categories: tuple[str, ...] = (),
    forbidden_command_categories: tuple[str, ...] = (),
    conditions: tuple[str, ...] = (),
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    one_shot: bool = True,
    decision_sequence: int = 0,
    expires_after_sequence: int | None = None,
    consumed: bool = False,
) -> SandboxPlanReviewDecision:
    return SandboxPlanReviewDecision(
        decision_id=stable_id("gsr-d-sandbox-plan-review", plan_id, disposition, decision_sequence),
        plan_id=plan_id,
        operator_authority=operator_authority,
        disposition=disposition,
        rationale=rationale,
        allowed_execution_scope=allowed_execution_scope,
        forbidden_execution_scope=forbidden_execution_scope,
        allowed_tool_classes=allowed_tool_classes,
        forbidden_tool_classes=forbidden_tool_classes,
        allowed_command_categories=allowed_command_categories,
        forbidden_command_categories=forbidden_command_categories,
        conditions=conditions,
        one_shot=one_shot,
        decision_sequence=decision_sequence,
        expires_after_sequence=expires_after_sequence,
        consumed=consumed,
    )


def review_sandbox_plan(
    state: SandboxPlanningState,
    decision: SandboxPlanReviewDecision,
    *,
    sequence: int,
) -> SandboxPlanReviewResult:
    allowed, reason, plan = _sandbox_plan_review_decision_allows(state, decision, sequence=sequence)
    if not allowed:
        return SandboxPlanReviewResult(False, reason, state, plan, decision, disposition=decision.disposition)
    assert plan is not None
    next_state = _replace_sandbox_plan_for_review(state, plan, decision)
    eligible = decision.disposition == "approve_for_future_sandbox_execution"
    return SandboxPlanReviewResult(
        True,
        "sandbox_plan_review_decision_accepted",
        next_state,
        plan,
        decision,
        future_sandbox_execution_eligible=eligible,
        disposition=decision.disposition,
    )


def sandbox_plan_can_review_itself(plan: SandboxEvaluationPlan) -> bool:
    _ = plan
    return False


def sandbox_plan_is_future_execution_eligible(state: SandboxPlanningState, plan_id: str) -> bool:
    return plan_id in state.future_sandbox_execution_eligible_plans


def sandbox_plan_disposition_blocks_execution(disposition: str) -> bool:
    return disposition in SANDBOX_PLAN_BLOCKING_DISPOSITIONS


def make_governed_objective_cycle(
    objective: DevelopmentObjective,
    *,
    current_stage: str = "objective_authorized",
    current_substage: str = "awaiting_transition_request",
    sequence: int | None = None,
) -> GovernedObjectiveCycle:
    return GovernedObjectiveCycle(
        cycle_id=stable_id("gsr-e-cycle", objective.objective_id, sequence if sequence is not None else objective.sequence),
        objective_id=objective.objective_id,
        objective_snapshot=serialize(objective),
        current_stage=current_stage,
        current_substage=current_substage,
        sequence=objective.sequence if sequence is None else sequence,
        cycle_status="operator_attention_required",
        active_artifact_type="development_objective",
        active_artifact_id=objective.objective_id,
    )


def make_objective_cycle_state_bundle(
    cycle: GovernedObjectiveCycle,
    *,
    observation_ledger_state: ObservationLedgerState | None = None,
    diagnosis_proposal_state: DiagnosisProposalState | None = None,
    sandbox_planning_state: SandboxPlanningState | None = None,
    transition_requests: tuple[ObjectiveCycleTransitionRequest, ...] = (),
    transition_authorizations: tuple[ObjectiveCycleTransitionAuthorization, ...] = (),
    transition_records: tuple[ObjectiveCycleTransitionRecord, ...] = (),
) -> ObjectiveCycleStateBundle:
    return ObjectiveCycleStateBundle(
        cycle=cycle,
        observation_ledger_state=serialize(observation_ledger_state) if observation_ledger_state is not None else None,
        diagnosis_proposal_state=serialize(diagnosis_proposal_state) if diagnosis_proposal_state is not None else None,
        sandbox_planning_state=serialize(sandbox_planning_state) if sandbox_planning_state is not None else None,
        transition_requests=tuple(serialize(item) for item in transition_requests),
        transition_authorizations=tuple(serialize(item) for item in transition_authorizations),
        transition_records=tuple(serialize(item) for item in transition_records),
    )


def make_cycle_transition_request(
    cycle: GovernedObjectiveCycle,
    *,
    requested_stage: str,
    requested_substage: str,
    artifact_type: str = "",
    artifact_id: str = "",
    eligibility_claims: tuple[str, ...] = (),
    required_evidence_refs: tuple[str, ...] = (),
    required_authorization_scope: tuple[str, ...] = (),
    forbidden_scope: tuple[str, ...] = (),
    requested_sequence: int | None = None,
    request_rationale: str = "operator requested next inert cycle transition",
) -> ObjectiveCycleTransitionRequest:
    sequence = cycle.sequence + 1 if requested_sequence is None else requested_sequence
    return ObjectiveCycleTransitionRequest(
        request_id=stable_id("gsr-e-transition-request", cycle.cycle_id, cycle.current_stage, requested_stage, sequence),
        cycle_id=cycle.cycle_id,
        from_stage=cycle.current_stage,
        requested_stage=requested_stage,
        requested_substage=requested_substage,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        eligibility_claims=eligibility_claims,
        required_evidence_refs=required_evidence_refs,
        required_authorization_scope=required_authorization_scope,
        forbidden_scope=forbidden_scope,
        requested_sequence=sequence,
        request_rationale=request_rationale,
    )


def make_cycle_transition_authorization(
    request: ObjectiveCycleTransitionRequest,
    *,
    allowed_scope: tuple[str, ...],
    forbidden_scope: tuple[str, ...] = (),
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    conditions: tuple[str, ...] = (),
    one_shot: bool = True,
    decision_sequence: int | None = None,
    expires_after_sequence: int | None = None,
    consumed: bool = False,
    rationale: str = "operator authorized inert objective-cycle transition",
) -> ObjectiveCycleTransitionAuthorization:
    sequence = request.requested_sequence if decision_sequence is None else decision_sequence
    return ObjectiveCycleTransitionAuthorization(
        authorization_id=stable_id("gsr-e-transition-authorization", request.request_id, request.requested_stage, sequence),
        cycle_id=request.cycle_id,
        request_id=request.request_id,
        operator_authority=operator_authority,
        allowed_from_stage=request.from_stage,
        allowed_to_stage=request.requested_stage,
        allowed_substage=request.requested_substage,
        allowed_artifact_type=request.artifact_type,
        allowed_artifact_id=request.artifact_id,
        allowed_scope=allowed_scope,
        forbidden_scope=forbidden_scope,
        conditions=conditions,
        one_shot=one_shot,
        decision_sequence=sequence,
        expires_after_sequence=expires_after_sequence,
        consumed=consumed,
        rationale=rationale,
    )


def make_objective_cycle_transition_record(
    request: ObjectiveCycleTransitionRequest,
    authorization: ObjectiveCycleTransitionAuthorization,
    *,
    result: str = "pending",
    reason: str = "inert transition record only",
) -> ObjectiveCycleTransitionRecord:
    return ObjectiveCycleTransitionRecord(
        transition_id=stable_id("gsr-e-transition-record", request.request_id, authorization.authorization_id, result),
        cycle_id=request.cycle_id,
        from_stage=request.from_stage,
        to_stage=request.requested_stage,
        from_substage="",
        to_substage=request.requested_substage,
        artifact_type=request.artifact_type,
        artifact_id=request.artifact_id,
        request_id=request.request_id,
        authorization_id=authorization.authorization_id,
        sequence=authorization.decision_sequence,
        result=result,
        reason=reason,
    )


def cycle_requires_operator_attention(cycle: GovernedObjectiveCycle) -> bool:
    return cycle.operator_attention_required is True


def cycle_can_continue_automatically(cycle: GovernedObjectiveCycle) -> bool:
    _ = cycle
    return False


def cycle_transition_executes_stage(record: ObjectiveCycleTransitionRecord | ObjectiveCycleTransitionRequest | ObjectiveCycleTransitionResult) -> bool:
    _ = record
    return False


def transition_request_targets_known_lifecycle_state(request: ObjectiveCycleTransitionRequest) -> bool:
    return request.requested_stage in GSR_E1_LIFECYCLE_STATES


def transition_request_targets_forbidden_execution_state(request: ObjectiveCycleTransitionRequest) -> bool:
    return request.requested_stage in GSR_E1_UNREACHABLE_EXECUTION_STATES


def transition_authorization_matches_request(
    cycle: GovernedObjectiveCycle,
    request: ObjectiveCycleTransitionRequest,
    authorization: ObjectiveCycleTransitionAuthorization,
) -> bool:
    return (
        request.cycle_id == cycle.cycle_id
        and authorization.cycle_id == cycle.cycle_id
        and authorization.request_id == request.request_id
        and request.from_stage == cycle.current_stage
        and authorization.allowed_from_stage == cycle.current_stage
        and authorization.allowed_to_stage == request.requested_stage
        and authorization.allowed_substage == request.requested_substage
        and authorization.allowed_artifact_type == request.artifact_type
        and authorization.allowed_artifact_id == request.artifact_id
    )


def transition_authorization_is_available(
    authorization: ObjectiveCycleTransitionAuthorization,
    *,
    sequence: int,
) -> bool:
    if authorization.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False
    if not authorization.one_shot:
        return False
    if authorization.consumed:
        return False
    if authorization.expires_after_sequence is not None and sequence > authorization.expires_after_sequence:
        return False
    return True


def transition_scope_is_within_authorization(
    request: ObjectiveCycleTransitionRequest,
    authorization: ObjectiveCycleTransitionAuthorization,
) -> bool:
    required = set(request.required_authorization_scope)
    allowed = set(authorization.allowed_scope)
    if required and not required.issubset(allowed):
        return False
    if required.intersection(GSR_E1_FORBIDDEN_TRANSITION_SCOPES):
        return False
    if allowed.intersection(GSR_E1_FORBIDDEN_TRANSITION_SCOPES):
        return False
    if set(request.forbidden_scope).intersection(allowed):
        return False
    if set(authorization.forbidden_scope).intersection(required):
        return False
    return True


def evaluate_objective_cycle_transition_eligibility(
    cycle: GovernedObjectiveCycle,
    request: ObjectiveCycleTransitionRequest,
    authorization: ObjectiveCycleTransitionAuthorization,
    *,
    sequence: int,
) -> ObjectiveCycleTransitionEligibilityResult:
    if request.creates_execution or request.creates_background_work or request.creates_persistence:
        return ObjectiveCycleTransitionEligibilityResult(False, "request_attempts_execution", cycle, request, authorization)
    if transition_request_targets_forbidden_execution_state(request):
        return ObjectiveCycleTransitionEligibilityResult(False, "forbidden_execution_state", cycle, request, authorization)
    if not transition_request_targets_known_lifecycle_state(request):
        return ObjectiveCycleTransitionEligibilityResult(False, "unknown_lifecycle_state", cycle, request, authorization)
    if request.cycle_id != cycle.cycle_id or authorization.cycle_id != cycle.cycle_id:
        return ObjectiveCycleTransitionEligibilityResult(False, "wrong_cycle", cycle, request, authorization)
    if request.from_stage != cycle.current_stage or authorization.allowed_from_stage != cycle.current_stage:
        return ObjectiveCycleTransitionEligibilityResult(False, "wrong_stage", cycle, request, authorization)
    if authorization.request_id != request.request_id:
        return ObjectiveCycleTransitionEligibilityResult(False, "wrong_request", cycle, request, authorization)
    if authorization.consumed:
        return ObjectiveCycleTransitionEligibilityResult(False, "authorization_consumed", cycle, request, authorization)
    if authorization.expires_after_sequence is not None and sequence > authorization.expires_after_sequence:
        return ObjectiveCycleTransitionEligibilityResult(False, "authorization_expired", cycle, request, authorization)
    if not transition_authorization_is_available(authorization, sequence=sequence):
        return ObjectiveCycleTransitionEligibilityResult(False, "authorization_unavailable", cycle, request, authorization)
    if not transition_authorization_matches_request(cycle, request, authorization):
        return ObjectiveCycleTransitionEligibilityResult(False, "authorization_mismatch", cycle, request, authorization)
    if not transition_scope_is_within_authorization(request, authorization):
        return ObjectiveCycleTransitionEligibilityResult(False, "scope_mismatch_or_forbidden", cycle, request, authorization)
    return ObjectiveCycleTransitionEligibilityResult(
        True,
        "eligible_for_operator_review",
        cycle,
        request,
        authorization,
        eligible_for_operator_review=True,
    )


def apply_objective_cycle_transition(
    cycle: GovernedObjectiveCycle,
    request: ObjectiveCycleTransitionRequest,
    authorization: ObjectiveCycleTransitionAuthorization,
    *,
    sequence: int,
) -> ObjectiveCycleTransitionResult:
    eligibility = evaluate_objective_cycle_transition_eligibility(
        cycle,
        request,
        authorization,
        sequence=sequence,
    )
    if not eligibility.accepted:
        return ObjectiveCycleTransitionResult(
            False,
            eligibility.reason,
            cycle,
            cycle,
            request=request,
            authorization=authorization,
            eligibility_result=eligibility,
        )

    consumed_authorization = replace(authorization, consumed=True)
    completed_markers = tuple(dict.fromkeys((*cycle.completed_stage_markers, request.from_stage)))
    consumed_authorization_ids = tuple(dict.fromkeys((*cycle.consumed_transition_authorization_ids, authorization.authorization_id)))
    pending_request_ids = tuple(item for item in cycle.pending_transition_request_ids if item != request.request_id)
    transition_id = stable_id("gsr-e-transition-record", request.request_id, authorization.authorization_id, "applied")
    next_cycle = replace(
        cycle,
        current_stage=request.requested_stage,
        current_substage=request.requested_substage,
        sequence=sequence,
        cycle_status="operator_attention_required",
        active_artifact_type=request.artifact_type or cycle.active_artifact_type,
        active_artifact_id=request.artifact_id or cycle.active_artifact_id,
        completed_stage_markers=completed_markers,
        pending_transition_request_ids=pending_request_ids,
        consumed_transition_authorization_ids=consumed_authorization_ids,
        last_successful_transition=transition_id,
        operator_attention_required=True,
        autonomous_continuation_prohibited=True,
        background_execution_prohibited=True,
        persistence_prohibited=True,
    )
    record = ObjectiveCycleTransitionRecord(
        transition_id=transition_id,
        cycle_id=cycle.cycle_id,
        from_stage=cycle.current_stage,
        to_stage=request.requested_stage,
        from_substage=cycle.current_substage,
        to_substage=request.requested_substage,
        artifact_type=request.artifact_type,
        artifact_id=request.artifact_id,
        request_id=request.request_id,
        authorization_id=authorization.authorization_id,
        sequence=sequence,
        result="metadata_transition_applied",
        reason="one inert lifecycle metadata transition applied",
    )
    return ObjectiveCycleTransitionResult(
        True,
        "metadata_transition_applied",
        cycle,
        next_cycle,
        request=request,
        authorization=authorization,
        consumed_authorization=consumed_authorization,
        transition_record=record,
        eligibility_result=eligibility,
        operator_attention_required=True,
        transition_applied=True,
        authorization_consumed=True,
        record_created=True,
        cycle_mutated=False,
        replacement_cycle_produced=True,
        automatic_continuation=False,
    )


def sandbox_plan_version(plan: SandboxEvaluationPlan) -> str:
    return str(plan.creation_sequence)


def sandbox_plan_digest(plan: SandboxEvaluationPlan) -> str:
    return stable_id("gsr-e2-sandbox-plan-digest", serialize(plan))


def make_sandbox_execution_request(
    cycle: GovernedObjectiveCycle,
    sandbox_plan: SandboxEvaluationPlan,
    *,
    requested_scope: tuple[str, ...],
    requested_workspace_policy: tuple[str, ...],
    requested_tool_allowlist: tuple[str, ...],
    requested_command_allowlist: tuple[str, ...],
    requested_network_policy: tuple[str, ...],
    requested_execution_budget: Mapping[str, int],
    requested_artifact_output_policy: tuple[str, ...],
    requested_execution_sequence: int,
) -> SandboxExecutionRequest:
    version = sandbox_plan_version(sandbox_plan)
    digest = sandbox_plan_digest(sandbox_plan)
    return SandboxExecutionRequest(
        request_id=stable_id("gsr-e2-sandbox-execution-request", cycle.cycle_id, sandbox_plan.plan_id, version, digest, requested_execution_sequence),
        cycle_id=cycle.cycle_id,
        sandbox_plan_id=sandbox_plan.plan_id,
        sandbox_plan_version=version,
        sandbox_plan_digest=digest,
        requested_execution_sequence=requested_execution_sequence,
        requested_scope=requested_scope,
        requested_workspace_policy=requested_workspace_policy,
        requested_tool_allowlist=requested_tool_allowlist,
        requested_command_allowlist=requested_command_allowlist,
        requested_network_policy=requested_network_policy,
        requested_execution_budget=dict(requested_execution_budget),
        requested_artifact_output_policy=requested_artifact_output_policy,
    )


def make_sandbox_execution_authorization(
    request: SandboxExecutionRequest,
    *,
    authorized_scope: tuple[str, ...],
    authorized_workspace_policy: tuple[str, ...],
    authorized_tool_allowlist: tuple[str, ...],
    authorized_command_allowlist: tuple[str, ...],
    authorized_network_policy: tuple[str, ...],
    authorized_execution_budget: Mapping[str, int],
    authorized_artifact_output_policy: tuple[str, ...],
    authorized_source_lifecycle_stage: str = "future_sandbox_execution_eligible",
    authorized_target_lifecycle_stage: str = "future_sandbox_execution_eligible",
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    one_shot: bool = True,
    consumed: bool = False,
    issued_sequence: int | None = None,
    expires_after_sequence: int | None = None,
) -> SandboxExecutionAuthorization:
    sequence = request.requested_execution_sequence if issued_sequence is None else issued_sequence
    return SandboxExecutionAuthorization(
        authorization_id=stable_id("gsr-e2-sandbox-execution-authorization", request.request_id, request.sandbox_plan_id, sequence),
        request_id=request.request_id,
        cycle_id=request.cycle_id,
        sandbox_plan_id=request.sandbox_plan_id,
        sandbox_plan_version=request.sandbox_plan_version,
        sandbox_plan_digest=request.sandbox_plan_digest,
        authorized_source_lifecycle_stage=authorized_source_lifecycle_stage,
        authorized_target_lifecycle_stage=authorized_target_lifecycle_stage,
        authorized_scope=authorized_scope,
        authorized_workspace_policy=authorized_workspace_policy,
        authorized_tool_allowlist=authorized_tool_allowlist,
        authorized_command_allowlist=authorized_command_allowlist,
        authorized_network_policy=authorized_network_policy,
        authorized_execution_budget=dict(authorized_execution_budget),
        authorized_artifact_output_policy=authorized_artifact_output_policy,
        issued_sequence=sequence,
        expires_after_sequence=expires_after_sequence,
        operator_authority=operator_authority,
        one_shot=one_shot,
        consumed=consumed,
    )


def sandbox_execution_request_matches_cycle(cycle: GovernedObjectiveCycle, request: SandboxExecutionRequest) -> bool:
    return request.cycle_id == cycle.cycle_id


def sandbox_execution_request_matches_plan(request: SandboxExecutionRequest, plan: SandboxEvaluationPlan) -> bool:
    return (
        request.sandbox_plan_id == plan.plan_id
        and request.sandbox_plan_version == sandbox_plan_version(plan)
        and request.sandbox_plan_digest == sandbox_plan_digest(plan)
    )


def sandbox_execution_authorization_matches_request(
    request: SandboxExecutionRequest,
    authorization: SandboxExecutionAuthorization,
) -> bool:
    return (
        authorization.request_id == request.request_id
        and authorization.cycle_id == request.cycle_id
        and authorization.sandbox_plan_id == request.sandbox_plan_id
        and authorization.sandbox_plan_version == request.sandbox_plan_version
        and authorization.sandbox_plan_digest == request.sandbox_plan_digest
    )


def sandbox_execution_authorization_is_available(
    authorization: SandboxExecutionAuthorization,
    *,
    sequence: int,
) -> bool:
    if authorization.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False
    if not authorization.one_shot:
        return False
    if authorization.consumed:
        return False
    if authorization.expires_after_sequence is not None and sequence > authorization.expires_after_sequence:
        return False
    return True


def _policy_has_unrestricted_marker(policy: tuple[str, ...]) -> bool:
    normalized = {str(item).strip().lower() for item in policy}
    return bool(normalized.intersection(GSR_E2_UNRESTRICTED_POLICY_MARKERS))


def _scope_contains_forbidden_execution(scope: tuple[str, ...]) -> bool:
    return bool(set(scope).intersection(GSR_E2_FORBIDDEN_EXECUTION_SCOPES))


def sandbox_execution_scope_is_within_authorization(
    request: SandboxExecutionRequest,
    authorization: SandboxExecutionAuthorization,
) -> bool:
    requested = set(request.requested_scope)
    authorized = set(authorization.authorized_scope)
    if not requested or not requested.issubset(authorized):
        return False
    if _scope_contains_forbidden_execution(request.requested_scope):
        return False
    if _scope_contains_forbidden_execution(authorization.authorized_scope):
        return False
    return True


def sandbox_execution_budget_is_within_authorization(
    request: SandboxExecutionRequest,
    authorization: SandboxExecutionAuthorization,
) -> bool:
    requested = request.requested_execution_budget
    authorized = authorization.authorized_execution_budget
    if set(requested) != set(GSR_E2_REQUIRED_BUDGET_FIELDS):
        return False
    if set(authorized) != set(GSR_E2_REQUIRED_BUDGET_FIELDS):
        return False
    for key in GSR_E2_REQUIRED_BUDGET_FIELDS:
        requested_value = requested.get(key)
        authorized_value = authorized.get(key)
        if not isinstance(requested_value, int) or not isinstance(authorized_value, int):
            return False
        if requested_value <= 0 or authorized_value <= 0:
            return False
        if requested_value > authorized_value:
            return False
    return True


def sandbox_execution_policy_is_safe(
    request: SandboxExecutionRequest,
    authorization: SandboxExecutionAuthorization,
) -> tuple[bool, str]:
    required_workspace = {
        "disposable_workspace_required",
        "cleanup_required",
        "cleanup_verification_required",
        "no_production_path_access",
        "no_credential_access",
        "no_home_directory_access",
        "no_external_drive_access",
        "no_environment_secret_inheritance",
    }
    if not required_workspace.issubset(set(request.requested_workspace_policy)):
        return False, "workspace_policy_mismatch"
    if not set(request.requested_workspace_policy).issubset(set(authorization.authorized_workspace_policy)):
        return False, "workspace_policy_mismatch"
    if _policy_has_unrestricted_marker(request.requested_workspace_policy) or _policy_has_unrestricted_marker(authorization.authorized_workspace_policy):
        return False, "unrestricted_policy"
    if not request.requested_tool_allowlist or not set(request.requested_tool_allowlist).issubset(set(authorization.authorized_tool_allowlist)):
        return False, "tool_policy_mismatch"
    if not request.requested_command_allowlist or not set(request.requested_command_allowlist).issubset(set(authorization.authorized_command_allowlist)):
        return False, "command_policy_mismatch"
    if _policy_has_unrestricted_marker(request.requested_tool_allowlist) or _policy_has_unrestricted_marker(authorization.authorized_tool_allowlist):
        return False, "unrestricted_policy"
    if _policy_has_unrestricted_marker(request.requested_command_allowlist) or _policy_has_unrestricted_marker(authorization.authorized_command_allowlist):
        return False, "unrestricted_policy"
    if not set(request.requested_network_policy).issubset(set(authorization.authorized_network_policy)):
        return False, "network_policy_mismatch"
    if _policy_has_unrestricted_marker(request.requested_network_policy) or _policy_has_unrestricted_marker(authorization.authorized_network_policy):
        return False, "unrestricted_policy"
    if not set(request.requested_artifact_output_policy).issubset(set(authorization.authorized_artifact_output_policy)):
        return False, "artifact_policy_mismatch"
    return True, "policy_valid"


def evaluate_sandbox_execution_eligibility(
    cycle: GovernedObjectiveCycle,
    planning_state: SandboxPlanningState,
    sandbox_plan: SandboxEvaluationPlan,
    request: SandboxExecutionRequest,
    authorization: SandboxExecutionAuthorization,
    *,
    sequence: int,
) -> SandboxExecutionEligibilityResult:
    if not sandbox_execution_request_matches_cycle(cycle, request) or authorization.cycle_id != cycle.cycle_id:
        return SandboxExecutionEligibilityResult(False, "wrong_cycle", cycle, sandbox_plan, request, authorization)
    if cycle.current_stage != "future_sandbox_execution_eligible" or authorization.authorized_source_lifecycle_stage != cycle.current_stage:
        return SandboxExecutionEligibilityResult(False, "wrong_stage", cycle, sandbox_plan, request, authorization)
    if cycle.current_stage in {"completed", "rejected", "suspended", "interrupted", "deeper_design_required"}:
        return SandboxExecutionEligibilityResult(False, "cycle_terminal_or_blocked", cycle, sandbox_plan, request, authorization)
    if not cycle.autonomous_continuation_prohibited or not cycle.background_execution_prohibited:
        return SandboxExecutionEligibilityResult(False, "cycle_automatic_continuation_detected", cycle, sandbox_plan, request, authorization)
    if not sandbox_execution_request_matches_plan(request, sandbox_plan):
        return SandboxExecutionEligibilityResult(False, "wrong_plan", cycle, sandbox_plan, request, authorization)
    if authorization.sandbox_plan_id != sandbox_plan.plan_id:
        return SandboxExecutionEligibilityResult(False, "wrong_plan", cycle, sandbox_plan, request, authorization)
    if authorization.sandbox_plan_version != sandbox_plan_version(sandbox_plan):
        return SandboxExecutionEligibilityResult(False, "wrong_plan_version", cycle, sandbox_plan, request, authorization)
    if authorization.sandbox_plan_digest != sandbox_plan_digest(sandbox_plan):
        return SandboxExecutionEligibilityResult(False, "wrong_plan_digest", cycle, sandbox_plan, request, authorization)
    if _sandbox_plan_payload(planning_state, sandbox_plan.plan_id) is None:
        return SandboxExecutionEligibilityResult(False, "wrong_plan", cycle, sandbox_plan, request, authorization)
    if sandbox_plan.plan_id not in planning_state.future_sandbox_execution_eligible_plans:
        return SandboxExecutionEligibilityResult(False, "plan_not_future_execution_eligible", cycle, sandbox_plan, request, authorization)
    if sandbox_plan.plan_id in planning_state.rejected_plans or sandbox_plan.plan_id in planning_state.deeper_design_plans:
        return SandboxExecutionEligibilityResult(False, "plan_not_accepted", cycle, sandbox_plan, request, authorization)
    if not sandbox_plan.disposable_workspace or not sandbox_plan.cleanup_proof_requirements:
        return SandboxExecutionEligibilityResult(False, "workspace_policy_mismatch", cycle, sandbox_plan, request, authorization)
    if not (
        sandbox_plan.workspace_creation_prohibited
        and sandbox_plan.sandbox_execution_prohibited
        and sandbox_plan.command_execution_prohibited
        and sandbox_plan.source_mutation_prohibited
        and sandbox_plan.module_loading_prohibited
        and sandbox_plan.application_prohibited
        and sandbox_plan.persistence_prohibited
    ):
        return SandboxExecutionEligibilityResult(False, "plan_authorizes_operation", cycle, sandbox_plan, request, authorization)
    if not sandbox_execution_authorization_matches_request(request, authorization):
        return SandboxExecutionEligibilityResult(False, "wrong_request", cycle, sandbox_plan, request, authorization)
    if authorization.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return SandboxExecutionEligibilityResult(False, "non_operator_authorization", cycle, sandbox_plan, request, authorization)
    if authorization.consumed:
        return SandboxExecutionEligibilityResult(False, "consumed", cycle, sandbox_plan, request, authorization)
    if authorization.expires_after_sequence is not None and sequence > authorization.expires_after_sequence:
        return SandboxExecutionEligibilityResult(False, "expired", cycle, sandbox_plan, request, authorization)
    if not sandbox_execution_authorization_is_available(authorization, sequence=sequence):
        return SandboxExecutionEligibilityResult(False, "authorization_unavailable", cycle, sandbox_plan, request, authorization)
    if not sandbox_execution_scope_is_within_authorization(request, authorization):
        return SandboxExecutionEligibilityResult(False, "scope_mismatch", cycle, sandbox_plan, request, authorization)
    if not sandbox_execution_budget_is_within_authorization(request, authorization):
        return SandboxExecutionEligibilityResult(False, "budget_mismatch", cycle, sandbox_plan, request, authorization)
    policy_ok, policy_reason = sandbox_execution_policy_is_safe(request, authorization)
    if not policy_ok:
        return SandboxExecutionEligibilityResult(False, policy_reason, cycle, sandbox_plan, request, authorization)
    return SandboxExecutionEligibilityResult(
        True,
        "eligible_for_future_sandbox_execution",
        cycle,
        sandbox_plan,
        request,
        authorization,
        eligible_for_future_sandbox_execution=True,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_status_short() -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=_repo_root(),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return tuple(line for line in completed.stdout.splitlines() if line.strip())


def _safe_relative_workspace_path(relative_path: str) -> bool:
    path = Path(relative_path)
    if path.is_absolute():
        return False
    if any(part in {"..", ""} for part in path.parts):
        return False
    blocked = {".git", ".env", "secrets", "credentials", "DELTA-75"}
    return not any(part in blocked for part in path.parts)


def _bounded_text(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[-limit:], True


def _workspace_write_manifest(workspace: Path) -> tuple[str, ...]:
    if not workspace.exists():
        return ()
    paths: list[str] = []
    for path in sorted(item for item in workspace.rglob("*") if item.is_file()):
        paths.append(path.relative_to(workspace).as_posix())
    return tuple(paths)


def execute_disposable_sandbox_attempt(
    cycle: GovernedObjectiveCycle,
    planning_state: SandboxPlanningState,
    sandbox_plan: SandboxEvaluationPlan,
    request: SandboxExecutionRequest,
    authorization: SandboxExecutionAuthorization,
    *,
    command_name: str,
    command_arguments: tuple[str, ...],
    fixture_files: Mapping[str, str],
    sequence: int,
) -> SandboxExecutionResult:
    eligibility = evaluate_sandbox_execution_eligibility(
        cycle,
        planning_state,
        sandbox_plan,
        request,
        authorization,
        sequence=sequence,
    )
    if not eligibility.accepted:
        return SandboxExecutionResult(False, eligibility.reason, cycle, sandbox_plan, request, authorization)
    if command_name not in request.requested_command_allowlist or command_name not in authorization.authorized_command_allowlist:
        return SandboxExecutionResult(False, "command_not_authorized", cycle, sandbox_plan, request, authorization)
    if command_name not in rc4.SAFE_COMMAND_ALLOWLIST or command_name in rc4.PROHIBITED_COMMANDS:
        return SandboxExecutionResult(False, "command_not_allowlisted", cycle, sandbox_plan, request, authorization)
    if request.requested_execution_budget.get("max_commands", 0) < 1:
        return SandboxExecutionResult(False, "budget_mismatch", cycle, sandbox_plan, request, authorization)
    if len(fixture_files) > request.requested_execution_budget.get("max_workspace_writes", 0):
        return SandboxExecutionResult(False, "workspace_write_budget_exceeded", cycle, sandbox_plan, request, authorization)
    if not fixture_files:
        return SandboxExecutionResult(False, "fixture_required", cycle, sandbox_plan, request, authorization)
    if any(not _safe_relative_workspace_path(path) for path in fixture_files):
        return SandboxExecutionResult(False, "path_traversal_or_forbidden_fixture", cycle, sandbox_plan, request, authorization)
    if any(not _safe_relative_workspace_path(arg) for arg in command_arguments):
        return SandboxExecutionResult(False, "path_traversal_or_forbidden_argument", cycle, sandbox_plan, request, authorization)

    live_status_before = _git_status_short()
    temp_root = Path(tempfile.mkdtemp(prefix="gsr_e2b_"))
    workspace = temp_root / "workspace"
    workspace.mkdir()
    attempt_id = stable_id("gsr-e2b-sandbox-attempt", authorization.authorization_id, sequence)
    consumed_authorization = replace(authorization, consumed=True)
    cleanup_verified = False
    cleanup_result = "not_started"
    evidence: SandboxExecutionEvidence | None = None
    attempt = SandboxExecutionAttempt(
        attempt_id=attempt_id,
        cycle_id=cycle.cycle_id,
        sandbox_plan_id=sandbox_plan.plan_id,
        request_id=request.request_id,
        authorization_id=authorization.authorization_id,
        execution_sequence=sequence,
        workspace_policy=request.requested_workspace_policy,
        command_name=command_name,
        normalized_arguments=command_arguments,
        execution_budget=request.requested_execution_budget,
        workspace_root=str(workspace),
        attempt_started=True,
        authorization_consumed=True,
    )
    try:
        for relative_path, content in fixture_files.items():
            target = workspace / relative_path
            resolved_target = target.resolve()
            if not resolved_target.is_relative_to(workspace.resolve()):
                return SandboxExecutionResult(
                    False,
                    "workspace_escape_detected",
                    cycle,
                    sandbox_plan,
                    request,
                    authorization,
                    consumed_authorization,
                    attempt,
                    authorization_consumed=True,
                    execution_performed=False,
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        scope = rc4.make_scope(
            target_repository="disposable_fixture",
            allowed_paths=tuple(fixture_files),
            allowed_commands=(command_name,),
            allowed_tools=("compiler", "filesystem_read"),
            max_duration_seconds=max(1, min(request.requested_execution_budget["max_elapsed_units"], 20)),
            max_changed_files=request.requested_execution_budget["max_workspace_writes"],
            max_diff_lines=0,
        )
        command = rc4.authorize_command(command_name, command_arguments, scope)
        command_result = rc4.run_authorized_command(workspace, command)
        stdout_summary, stdout_truncated = _bounded_text(command_result.stdout, request.requested_execution_budget["max_output_bytes"])
        stderr_summary, stderr_truncated = _bounded_text(command_result.stderr, request.requested_execution_budget["max_output_bytes"])
        manifest = _workspace_write_manifest(workspace)
        artifact_manifest = manifest[: request.requested_execution_budget["max_artifact_count"]]
        output_truncated = stdout_truncated or stderr_truncated or len(manifest) > len(artifact_manifest)
        live_status_after_execution = _git_status_short()
        live_source_unchanged = live_status_after_execution == live_status_before
        evidence = SandboxExecutionEvidence(
            attempt_id=attempt_id,
            command_name=command_name,
            normalized_arguments=command_arguments,
            start_sequence=sequence,
            end_sequence=sequence,
            return_code=command_result.returncode,
            stdout_summary=stdout_summary,
            stderr_summary=stderr_summary,
            output_truncated=output_truncated,
            artifact_manifest=artifact_manifest,
            filesystem_write_manifest=manifest,
            budget_observed={
                "command_count": 1,
                "tool_call_count": 0,
                "process_count": 1,
                "artifact_count": len(artifact_manifest),
                "workspace_write_count": len(manifest),
                "retry_count": 0,
                "duration_ms": command_result.duration_ms,
            },
            cleanup_result="pending",
            live_source_integrity_status="unchanged" if live_source_unchanged else "changed",
            execution_performed=True,
        )
        if not live_source_unchanged:
            return SandboxExecutionResult(
                False,
                "live_source_integrity_failed",
                cycle,
                sandbox_plan,
                request,
                authorization,
                consumed_authorization,
                attempt,
                evidence,
                execution_performed=True,
                authorization_consumed=True,
                live_source_unchanged=False,
            )
    finally:
        try:
            shutil.rmtree(temp_root)
            cleanup_verified = not temp_root.exists()
            cleanup_result = "verified" if cleanup_verified else "workspace_still_exists"
        except Exception as exc:  # pragma: no cover - exercised by monkeypatch in tests
            cleanup_verified = False
            cleanup_result = f"cleanup_failed:{type(exc).__name__}"

    final_live_unchanged = _git_status_short() == live_status_before
    completed_attempt = replace(
        attempt,
        attempt_completed=evidence is not None,
        cleanup_verified=cleanup_verified,
        live_source_unchanged=final_live_unchanged,
    )
    completed_evidence = replace(
        evidence,
        cleanup_result=cleanup_result,
        live_source_integrity_status="unchanged" if final_live_unchanged else "changed",
    ) if evidence is not None else None
    accepted = bool(
        completed_evidence is not None
        and completed_evidence.return_code == 0
        and cleanup_verified
        and final_live_unchanged
    )
    reason = "sandbox_attempt_succeeded" if accepted else (
        "cleanup_failed" if not cleanup_verified else "command_failed"
    )
    return SandboxExecutionResult(
        accepted,
        reason,
        cycle,
        sandbox_plan,
        request,
        authorization,
        consumed_authorization,
        completed_attempt,
        completed_evidence,
        eligible_for_operator_review=True,
        execution_performed=completed_evidence is not None,
        execution_succeeded=accepted,
        cleanup_verified=cleanup_verified,
        live_source_unchanged=final_live_unchanged,
        authorization_consumed=True,
    )


def make_sandbox_evidence_digest(evidence: SandboxExecutionEvidence) -> str:
    return stable_id("gsr-e3-sandbox-evidence-digest", serialize(evidence))


def _sandbox_finding(
    code: str,
    source_field: str,
    expected: object,
    observed: object,
    *,
    blocks: bool = True,
    severity: str = "error",
    deeper: bool = False,
) -> SandboxEvidenceFinding:
    return SandboxEvidenceFinding(
        code=code,
        severity=severity,
        message=code,
        source_field=source_field,
        expected_value=str(expected),
        observed_value=str(observed),
        blocks_operator_acceptance=blocks,
        requires_deeper_design=deeper,
    )


def evaluate_sandbox_execution_evidence(
    result: SandboxExecutionResult,
    *,
    expected_evidence_digest: str | None = None,
) -> SandboxEvidenceEvaluation:
    cycle = result.cycle
    plan = result.sandbox_plan
    request = result.request
    authorization = result.consumed_authorization or result.original_authorization
    attempt = result.attempt
    evidence = result.evidence
    findings: list[SandboxEvidenceFinding] = []

    if plan is None:
        findings.append(_sandbox_finding("evidence_incomplete", "sandbox_plan", "present", "missing"))
    if request is None:
        findings.append(_sandbox_finding("evidence_incomplete", "request", "present", "missing"))
    if authorization is None:
        findings.append(_sandbox_finding("authorization_invalid", "authorization", "present", "missing"))
    if result.reason in {"command_not_authorized", "command_not_allowlisted", "budget_mismatch", "workspace_write_budget_exceeded", "fixture_required", "path_traversal_or_forbidden_fixture", "path_traversal_or_forbidden_argument"}:
        findings.append(_sandbox_finding("preflight_denied", "reason", "post_start_or_success", result.reason, blocks=False, severity="info"))
    if attempt is None:
        findings.append(_sandbox_finding("evidence_incomplete", "attempt", "present", "missing", blocks=result.execution_performed))
    if evidence is None:
        findings.append(_sandbox_finding("evidence_incomplete", "evidence", "present", "missing", blocks=result.execution_performed))

    evidence_digest = make_sandbox_evidence_digest(evidence) if evidence is not None else stable_id("gsr-e3-missing-evidence", result.reason)
    if expected_evidence_digest is not None and evidence_digest != expected_evidence_digest:
        findings.append(_sandbox_finding("evidence_digest_mismatch", "evidence_digest", expected_evidence_digest, evidence_digest))

    if attempt is not None:
        if attempt.cycle_id != cycle.cycle_id:
            findings.append(_sandbox_finding("wrong_cycle", "attempt.cycle_id", cycle.cycle_id, attempt.cycle_id))
        if plan is not None and attempt.sandbox_plan_id != plan.plan_id:
            findings.append(_sandbox_finding("wrong_plan", "attempt.sandbox_plan_id", plan.plan_id, attempt.sandbox_plan_id))
        if request is not None and attempt.request_id != request.request_id:
            findings.append(_sandbox_finding("wrong_request", "attempt.request_id", request.request_id, attempt.request_id))
        if authorization is not None and attempt.authorization_id != authorization.authorization_id:
            findings.append(_sandbox_finding("wrong_authorization", "attempt.authorization_id", authorization.authorization_id, attempt.authorization_id))
        if attempt.attempt_started != result.execution_performed:
            findings.append(_sandbox_finding("evidence_inconsistent", "attempt_started", result.execution_performed, attempt.attempt_started))
        if attempt.authorization_consumed != result.authorization_consumed:
            findings.append(_sandbox_finding("evidence_inconsistent", "authorization_consumed", result.authorization_consumed, attempt.authorization_consumed))
        if attempt.cleanup_verified != result.cleanup_verified:
            findings.append(_sandbox_finding("evidence_inconsistent", "cleanup_verified", result.cleanup_verified, attempt.cleanup_verified))
        if not attempt.cleanup_verified and result.execution_performed:
            findings.append(_sandbox_finding("cleanup_failed", "attempt.cleanup_verified", True, False))
        if not attempt.live_source_unchanged and result.execution_performed:
            findings.append(_sandbox_finding("live_source_integrity_failed", "attempt.live_source_unchanged", True, False, deeper=True))

    budget_compliant = True
    output_within_policy = True
    artifacts_within_policy = True
    writes_within_policy = True
    if evidence is not None:
        if attempt is not None and evidence.attempt_id != attempt.attempt_id:
            findings.append(_sandbox_finding("wrong_attempt", "evidence.attempt_id", attempt.attempt_id, evidence.attempt_id))
        if evidence.execution_performed != result.execution_performed:
            findings.append(_sandbox_finding("evidence_inconsistent", "evidence.execution_performed", result.execution_performed, evidence.execution_performed))
        if result.execution_succeeded != (evidence.return_code == 0 and result.accepted):
            findings.append(_sandbox_finding("evidence_inconsistent", "return_code_success", result.execution_succeeded, evidence.return_code))
        if not evidence.cleanup_result:
            findings.append(_sandbox_finding("evidence_incomplete", "cleanup_result", "present", "missing"))
        if evidence.cleanup_result != "verified" and result.execution_performed:
            findings.append(_sandbox_finding("cleanup_failed", "cleanup_result", "verified", evidence.cleanup_result))
        if not evidence.live_source_integrity_status:
            findings.append(_sandbox_finding("evidence_incomplete", "live_source_integrity_status", "present", "missing"))
        if evidence.live_source_integrity_status != "unchanged" and result.execution_performed:
            findings.append(_sandbox_finding("live_source_integrity_failed", "live_source_integrity_status", "unchanged", evidence.live_source_integrity_status, deeper=True))
        required_budget = {"command_count", "tool_call_count", "process_count", "artifact_count", "workspace_write_count", "retry_count", "duration_ms"}
        if not required_budget.issubset(evidence.budget_observed):
            findings.append(_sandbox_finding("evidence_incomplete", "budget_observed", required_budget, set(evidence.budget_observed)))
            budget_compliant = False
        else:
            if request is not None:
                budget_limits = request.requested_execution_budget
                budget_pairs = {
                    "command_count": "max_commands",
                    "tool_call_count": "max_tool_calls",
                    "process_count": "max_processes",
                    "artifact_count": "max_artifact_count",
                    "workspace_write_count": "max_workspace_writes",
                    "retry_count": "max_retries",
                }
                for observed_key, limit_key in budget_pairs.items():
                    if evidence.budget_observed[observed_key] > budget_limits.get(limit_key, 0):
                        findings.append(_sandbox_finding("budget_exceeded", observed_key, budget_limits.get(limit_key, 0), evidence.budget_observed[observed_key]))
                        budget_compliant = False
        if evidence.output_truncated:
            findings.append(_sandbox_finding("output_truncated", "output_truncated", False, True, blocks=False, severity="warning"))
            output_within_policy = False
        if evidence.artifact_manifest is None:
            findings.append(_sandbox_finding("evidence_incomplete", "artifact_manifest", "present", "missing"))
            artifacts_within_policy = False
        if evidence.filesystem_write_manifest is None:
            findings.append(_sandbox_finding("evidence_incomplete", "filesystem_write_manifest", "present", "missing"))
            writes_within_policy = False
        for path in evidence.artifact_manifest:
            if not _safe_relative_workspace_path(path):
                findings.append(_sandbox_finding("unsupported_artifact", "artifact_manifest", "safe_relative_path", path))
                artifacts_within_policy = False
        for path in evidence.filesystem_write_manifest:
            if not _safe_relative_workspace_path(path):
                findings.append(_sandbox_finding("external_write_detected", "filesystem_write_manifest", "workspace_relative_path", path))
                writes_within_policy = False
        if evidence.application_performed:
            findings.append(_sandbox_finding("application_authority_detected", "evidence.application_performed", False, True))

    action_flags = {
        "second_attempt_created": result.second_attempt_created,
        "automatic_continuation": result.automatic_continuation,
        "patch_applied": result.patch_applied,
        "source_mutated": result.source_mutated,
        "module_activated": result.module_activated,
        "provider_called": result.provider_called,
        "model_invoked": result.model_invoked,
        "memory_written": result.memory_written,
        "persistence_performed": result.persistence_performed,
        "application_authorized": result.application_authorized,
        "application_performed": result.application_performed,
    }
    for field_name, observed in action_flags.items():
        if observed:
            code = "application_authority_detected" if field_name.startswith("application") else field_name
            findings.append(_sandbox_finding(code, field_name, False, True, deeper=field_name in {"source_mutated"}))

    blocking = [finding for finding in findings if finding.blocks_operator_acceptance]
    complete = (not result.execution_performed) or (evidence is not None and attempt is not None)
    consistent = not any(finding.code == "evidence_inconsistent" for finding in findings)
    if not result.execution_performed:
        classification = "preflight_denied"
    elif result.execution_performed and evidence is not None and evidence.return_code != 0:
        classification = "execution_failed"
    elif any(finding.code == "budget_exceeded" for finding in findings):
        classification = "budget_exceeded"
    elif any(finding.code == "cleanup_failed" for finding in findings):
        classification = "cleanup_failed"
    elif any(finding.code == "live_source_integrity_failed" for finding in findings):
        classification = "live_source_integrity_failed"
    elif any(finding.code == "evidence_incomplete" for finding in findings):
        classification = "evidence_incomplete"
    elif any(finding.code == "evidence_inconsistent" for finding in findings):
        classification = "evidence_inconsistent"
    elif result.execution_succeeded:
        classification = "execution_succeeded"
    else:
        classification = "evidence_valid_for_operator_review"
    accepted = complete and consistent and not blocking and classification in {"execution_succeeded", "execution_failed", "preflight_denied", "evidence_valid_for_operator_review"}
    reason = "evidence_valid_for_operator_review" if accepted else classification
    return SandboxEvidenceEvaluation(
        evaluation_id=stable_id("gsr-e3-evidence-evaluation", cycle.cycle_id, plan.plan_id if plan else "", evidence_digest, classification),
        cycle_id=cycle.cycle_id,
        plan_id=plan.plan_id if plan else "",
        attempt_id=attempt.attempt_id if attempt else "",
        request_id=request.request_id if request else "",
        authorization_id=authorization.authorization_id if authorization else "",
        evidence_digest=evidence_digest,
        accepted_for_operator_review=accepted,
        classification=classification,
        reason=reason,
        findings=tuple(findings),
        execution_started=bool(attempt and attempt.attempt_started),
        execution_succeeded=result.execution_succeeded,
        command_failed=bool(result.execution_performed and evidence is not None and evidence.return_code != 0),
        budget_compliant=budget_compliant,
        output_within_policy=output_within_policy,
        artifacts_within_policy=artifacts_within_policy,
        writes_within_policy=writes_within_policy,
        cleanup_verified=result.cleanup_verified,
        live_source_unchanged=result.live_source_unchanged,
        evidence_complete=complete,
        evidence_consistent=consistent,
    )


def make_sandbox_evaluation_disposition_request(
    evaluation: SandboxEvidenceEvaluation,
    *,
    proposed_disposition: str,
) -> SandboxEvaluationDispositionRequest:
    return SandboxEvaluationDispositionRequest(
        disposition_request_id=stable_id("gsr-e3-disposition-request", evaluation.evaluation_id, proposed_disposition),
        evaluation_id=evaluation.evaluation_id,
        cycle_id=evaluation.cycle_id,
        plan_id=evaluation.plan_id,
        attempt_id=evaluation.attempt_id,
        proposed_disposition=proposed_disposition,
        request_id=evaluation.request_id,
        authorization_id=evaluation.authorization_id,
        evidence_digest=evaluation.evidence_digest,
    )


def make_sandbox_evaluation_disposition(
    request: SandboxEvaluationDispositionRequest,
    *,
    decision: str,
    reason: str,
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    issued_sequence: int = 0,
    one_shot: bool = True,
    consumed: bool = False,
) -> SandboxEvaluationDisposition:
    return SandboxEvaluationDisposition(
        disposition_id=stable_id("gsr-e3-disposition", request.disposition_request_id, decision, issued_sequence),
        disposition_request_id=request.disposition_request_id,
        evaluation_id=request.evaluation_id,
        operator_authority=operator_authority,
        accepted=operator_authority == OPERATOR_CONTROLLED_AUTHORITY and one_shot,
        decision=decision,
        reason=reason,
        issued_sequence=issued_sequence,
        one_shot=one_shot,
        cycle_id=request.cycle_id,
        plan_id=request.plan_id,
        attempt_id=request.attempt_id,
        request_id=request.request_id,
        authorization_id=request.authorization_id,
        evidence_digest=request.evidence_digest,
        consumed=consumed,
    )


def review_sandbox_evaluation_disposition(
    evaluation: SandboxEvidenceEvaluation,
    request: SandboxEvaluationDispositionRequest,
    disposition: SandboxEvaluationDisposition,
) -> SandboxEvaluationDispositionResult:
    if request.evaluation_id != evaluation.evaluation_id or disposition.evaluation_id != evaluation.evaluation_id:
        return SandboxEvaluationDispositionResult(False, "wrong_evaluation", evaluation, request, disposition)
    if disposition.disposition_request_id != request.disposition_request_id:
        return SandboxEvaluationDispositionResult(False, "wrong_disposition_request", evaluation, request, disposition)
    if disposition.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return SandboxEvaluationDispositionResult(False, "operator_authority_required", evaluation, request, disposition)
    if not disposition.one_shot:
        return SandboxEvaluationDispositionResult(False, "one_shot_disposition_required", evaluation, request, disposition)
    if disposition.consumed:
        return SandboxEvaluationDispositionResult(False, "disposition_consumed", evaluation, request, disposition)
    if disposition.application_authorized or disposition.execution_authorized or disposition.automatic_continuation or disposition.lifecycle_transition_applied:
        return SandboxEvaluationDispositionResult(False, "disposition_attempts_action", evaluation, request, disposition)
    return SandboxEvaluationDispositionResult(True, "operator_disposition_recorded", evaluation, request, disposition)


SANDBOX_EVALUATION_DISPOSITIONS = (
    "accept_evidence_for_future_consideration",
    "accept_evidence_for_future_application_consideration",
    "reject_evidence",
    "request_revised_sandbox_plan",
    "request_another_sandbox_attempt",
    "require_more_evidence",
    "require_deeper_design",
    "defer",
    "suspend",
    "close_objective_cycle_as_rejected",
    "close_objective_cycle_as_completed_without_application",
    "mark_cleanup_failure",
    "mark_live_source_integrity_failure",
)


def sandbox_disposition_matches_evaluation(
    evaluation: SandboxEvidenceEvaluation,
    disposition: SandboxEvaluationDisposition,
) -> tuple[bool, str]:
    if disposition.evaluation_id != evaluation.evaluation_id:
        return False, "wrong_evaluation"
    if disposition.cycle_id != evaluation.cycle_id:
        return False, "wrong_cycle"
    if disposition.plan_id != evaluation.plan_id:
        return False, "wrong_plan"
    if disposition.attempt_id != evaluation.attempt_id:
        return False, "wrong_attempt"
    if disposition.request_id != evaluation.request_id:
        return False, "wrong_request"
    if disposition.authorization_id != evaluation.authorization_id:
        return False, "wrong_authorization"
    if disposition.evidence_digest != evaluation.evidence_digest:
        return False, "wrong_evidence_digest"
    return True, "valid"


def sandbox_disposition_matches_request(
    evaluation: SandboxEvidenceEvaluation,
    request: SandboxEvaluationDispositionRequest,
    disposition: SandboxEvaluationDisposition,
) -> tuple[bool, str]:
    if request.evaluation_id != evaluation.evaluation_id:
        return False, "wrong_evaluation"
    if request.cycle_id != evaluation.cycle_id:
        return False, "wrong_cycle"
    if request.plan_id != evaluation.plan_id:
        return False, "wrong_plan"
    if request.attempt_id != evaluation.attempt_id:
        return False, "wrong_attempt"
    if request.request_id != evaluation.request_id:
        return False, "wrong_request"
    if request.authorization_id != evaluation.authorization_id:
        return False, "wrong_authorization"
    if request.evidence_digest != evaluation.evidence_digest:
        return False, "wrong_evidence_digest"
    if disposition.disposition_request_id != request.disposition_request_id:
        return False, "wrong_disposition_request"
    if disposition.decision != request.proposed_disposition:
        return False, "wrong_disposition"
    return True, "valid"


def sandbox_disposition_is_available(
    disposition: SandboxEvaluationDisposition,
    *,
    sequence: int,
) -> tuple[bool, str]:
    if disposition.operator_authority != OPERATOR_CONTROLLED_AUTHORITY or not disposition.accepted:
        return False, "non_operator_disposition"
    if not disposition.one_shot:
        return False, "wrong_disposition"
    if disposition.consumed:
        return False, "consumed"
    if disposition.issued_sequence > sequence:
        return False, "expired"
    if disposition.application_authorized:
        return False, "application_authority_forbidden"
    if disposition.execution_authorized:
        return False, "execution_authority_forbidden"
    if disposition.lifecycle_transition_applied:
        return False, "lifecycle_authority_forbidden"
    if disposition.source_mutation_authorized:
        return False, "source_mutation_forbidden"
    if disposition.automatic_continuation:
        return False, "automatic_continuation_forbidden"
    return True, "valid"


def sandbox_disposition_decision_is_allowed(decision: str) -> tuple[bool, str]:
    if decision not in SANDBOX_EVALUATION_DISPOSITIONS:
        return False, "unsupported_decision"
    return True, "valid"


def sandbox_disposition_is_compatible_with_evaluation(
    evaluation: SandboxEvidenceEvaluation,
    decision: str,
) -> tuple[bool, str]:
    clean_acceptance = {
        "accept_evidence_for_future_consideration",
        "accept_evidence_for_future_application_consideration",
        "close_objective_cycle_as_completed_without_application",
    }
    if decision in clean_acceptance:
        if not evaluation.accepted_for_operator_review or not evaluation.evidence_complete or not evaluation.evidence_consistent:
            return False, "decision_incompatible_with_evaluation"
        if not evaluation.cleanup_verified:
            return False, "decision_incompatible_with_evaluation"
        if not evaluation.live_source_unchanged:
            return False, "decision_incompatible_with_evaluation"
        if evaluation.classification in {"cleanup_failed", "live_source_integrity_failed", "evidence_incomplete", "evidence_inconsistent", "budget_exceeded"}:
            return False, "decision_incompatible_with_evaluation"
    if decision == "mark_cleanup_failure" and evaluation.classification != "cleanup_failed" and evaluation.cleanup_verified:
        return False, "decision_incompatible_with_evaluation"
    if decision == "mark_live_source_integrity_failure" and evaluation.classification != "live_source_integrity_failed" and evaluation.live_source_unchanged:
        return False, "decision_incompatible_with_evaluation"
    if decision == "request_another_sandbox_attempt" and evaluation.application_authorized:
        return False, "application_authority_forbidden"
    return True, "valid"


def evaluate_sandbox_disposition_application(
    evaluation: SandboxEvidenceEvaluation,
    request: SandboxEvaluationDispositionRequest,
    disposition: SandboxEvaluationDisposition,
    *,
    sequence: int,
) -> tuple[bool, str]:
    for check in (
        sandbox_disposition_matches_evaluation(evaluation, disposition),
        sandbox_disposition_matches_request(evaluation, request, disposition),
        sandbox_disposition_is_available(disposition, sequence=sequence),
        sandbox_disposition_decision_is_allowed(disposition.decision),
        sandbox_disposition_is_compatible_with_evaluation(evaluation, disposition.decision),
    ):
        accepted, reason = check
        if not accepted:
            return accepted, reason
    return True, "valid"


def _sandbox_disposition_record(
    evaluation: SandboxEvidenceEvaluation,
    request: SandboxEvaluationDispositionRequest,
    disposition: SandboxEvaluationDisposition,
) -> SandboxEvaluationDispositionRecord:
    decision = disposition.decision
    return SandboxEvaluationDispositionRecord(
        record_id=stable_id(
            "gsr-e3-disposition-record",
            evaluation.evaluation_id,
            request.disposition_request_id,
            disposition.disposition_id,
            decision,
        ),
        evaluation_id=evaluation.evaluation_id,
        disposition_request_id=request.disposition_request_id,
        disposition_id=disposition.disposition_id,
        cycle_id=evaluation.cycle_id,
        plan_id=evaluation.plan_id,
        attempt_id=evaluation.attempt_id,
        request_id=evaluation.request_id,
        authorization_id=evaluation.authorization_id,
        evidence_digest=evaluation.evidence_digest,
        operator_disposition=decision,
        operator_issued=disposition.operator_authority == OPERATOR_CONTROLLED_AUTHORITY,
        issued_sequence=disposition.issued_sequence,
        accepted_evidence=decision in {"accept_evidence_for_future_consideration", "accept_evidence_for_future_application_consideration"},
        rejected_evidence=decision in {"reject_evidence", "close_objective_cycle_as_rejected"},
        revision_requested=decision == "request_revised_sandbox_plan",
        more_evidence_requested=decision == "require_more_evidence",
        deeper_design_required=decision == "require_deeper_design",
        another_execution_requested_metadata_only=decision == "request_another_sandbox_attempt",
        lifecycle_closure_requested_metadata_only=decision in {
            "close_objective_cycle_as_rejected",
            "close_objective_cycle_as_completed_without_application",
        },
        cleanup_failure_marked=decision == "mark_cleanup_failure",
        live_source_integrity_failure_marked=decision == "mark_live_source_integrity_failure",
    )


def apply_sandbox_evaluation_disposition(
    evaluation: SandboxEvidenceEvaluation,
    request: SandboxEvaluationDispositionRequest,
    disposition: SandboxEvaluationDisposition,
    *,
    sequence: int,
) -> SandboxEvaluationDispositionResult:
    accepted, reason = evaluate_sandbox_disposition_application(
        evaluation,
        request,
        disposition,
        sequence=sequence,
    )
    if not accepted:
        return SandboxEvaluationDispositionResult(
            False,
            reason,
            evaluation,
            request,
            disposition,
            original_disposition=disposition,
        )
    consumed_disposition = replace(disposition, consumed=True)
    record = _sandbox_disposition_record(evaluation, request, disposition)
    return SandboxEvaluationDispositionResult(
        True,
        "operator_evidence_disposition_recorded",
        evaluation,
        request,
        disposition,
        original_disposition=disposition,
        consumed_disposition=consumed_disposition,
        disposition_record=record,
        disposition_applied=True,
        disposition_authority_consumed=True,
        record_created=True,
    )


APPLICATION_ALLOWED_OPERATIONS = (
    "replace_exact_file",
    "add_exact_reviewed_file",
    "delete_exact_reviewed_generated_file",
    "apply_exact_reviewed_text_change",
)


def make_application_artifact(
    evaluation: SandboxEvidenceEvaluation,
    disposition_record: SandboxEvaluationDispositionRecord,
    *,
    proposed_application_artifact_id: str,
    proposed_application_artifact_digest: str,
    target_file_set: tuple[str, ...],
    operation_set: tuple[str, ...],
    expected_pre_application_hashes: dict[str, str],
    target_scope: tuple[str, ...],
    artifact_present: bool = True,
    binary_or_unsupported_content: bool = False,
    module_activation_implied: bool = False,
    scheduler_or_background_implied: bool = False,
) -> ApplicationArtifact:
    return ApplicationArtifact(
        artifact_id=proposed_application_artifact_id,
        artifact_digest=proposed_application_artifact_digest,
        evaluation_id=evaluation.evaluation_id,
        disposition_record_id=disposition_record.record_id,
        cycle_id=evaluation.cycle_id,
        plan_id=evaluation.plan_id,
        attempt_id=evaluation.attempt_id,
        request_id=evaluation.request_id,
        authorization_id=evaluation.authorization_id,
        evidence_digest=evaluation.evidence_digest,
        target_file_set=target_file_set,
        operation_set=operation_set,
        expected_pre_application_hashes=dict(expected_pre_application_hashes),
        target_scope=target_scope,
        artifact_present=artifact_present,
        binary_or_unsupported_content=binary_or_unsupported_content,
        module_activation_implied=module_activation_implied,
        scheduler_or_background_implied=scheduler_or_background_implied,
    )


def make_application_request(
    evaluation: SandboxEvidenceEvaluation,
    disposition_record: SandboxEvaluationDispositionRecord,
    artifact: ApplicationArtifact,
    *,
    requested_sequence: int,
) -> ApplicationRequest:
    return ApplicationRequest(
        application_request_id=stable_id("gsr-e4-application-request", evaluation.evaluation_id, disposition_record.record_id, artifact.artifact_id, requested_sequence),
        cycle_id=evaluation.cycle_id,
        plan_id=evaluation.plan_id,
        attempt_id=evaluation.attempt_id,
        request_id=evaluation.request_id,
        authorization_id=evaluation.authorization_id,
        evaluation_id=evaluation.evaluation_id,
        evidence_digest=evaluation.evidence_digest,
        disposition_record_id=disposition_record.record_id,
        proposed_application_artifact_id=artifact.artifact_id,
        proposed_application_artifact_digest=artifact.artifact_digest,
        target_scope=artifact.target_scope,
        target_file_set=artifact.target_file_set,
        expected_pre_application_hashes=dict(artifact.expected_pre_application_hashes),
        requested_operation_set=artifact.operation_set,
        requested_sequence=requested_sequence,
    )


def make_application_authorization(
    request: ApplicationRequest,
    *,
    issued_sequence: int,
    expiration_sequence: int,
    operator_authority: str = OPERATOR_CONTROLLED_AUTHORITY,
    one_shot: bool = True,
    consumed: bool = False,
) -> ApplicationAuthorization:
    return ApplicationAuthorization(
        application_authorization_id=stable_id("gsr-e4-application-authorization", request.application_request_id, issued_sequence),
        application_request_id=request.application_request_id,
        cycle_id=request.cycle_id,
        plan_id=request.plan_id,
        attempt_id=request.attempt_id,
        evaluation_id=request.evaluation_id,
        evidence_digest=request.evidence_digest,
        disposition_record_id=request.disposition_record_id,
        proposed_application_artifact_id=request.proposed_application_artifact_id,
        proposed_application_artifact_digest=request.proposed_application_artifact_digest,
        authorized_target_scope=request.target_scope,
        authorized_target_file_set=request.target_file_set,
        authorized_operation_set=request.requested_operation_set,
        expected_pre_application_hashes=dict(request.expected_pre_application_hashes),
        issued_sequence=issued_sequence,
        expiration_sequence=expiration_sequence,
        operator_authority=operator_authority,
        one_shot=one_shot,
        consumed=consumed,
    )


def _normalized_application_path(path_text: str) -> str | None:
    text = str(path_text).strip().replace("\\", "/")
    if not text or "*" in text:
        return None
    path = Path(text)
    if path.is_absolute():
        return None
    parts = tuple(part for part in text.split("/") if part)
    if not parts or any(part in {"..", "."} for part in parts):
        return None
    normalized = "/".join(parts)
    lowered_parts = tuple(part.lower() for part in parts)
    lowered = normalized.lower()
    blocked_parts = {".git", ".env", "secrets", "credentials", "keys", "key_material", "delta-75"}
    if any(part in blocked_parts for part in lowered_parts):
        return None
    if lowered.startswith("reports/rc4_"):
        return None
    if lowered.startswith((".github/", "deployment/", "deploy/", "dist/", "build/")):
        return None
    if lowered.endswith((".env", ".pem", ".key", ".pfx", ".p12")):
        return None
    if any(marker in lowered for marker in ("credential", "secret", "token", "password")):
        return None
    if lowered.startswith(("data/rc2_developmental_memory/", "data/canonical_memory/", "memory/", "stores/")):
        return None
    if lowered.endswith((".db", ".sqlite", ".sqlite3")):
        return None
    return normalized


def application_target_scope_is_safe(target_file_set: tuple[str, ...], target_scope: tuple[str, ...]) -> tuple[bool, str, tuple[str, ...]]:
    normalized_files: list[str] = []
    for path in target_file_set:
        normalized = _normalized_application_path(path)
        if normalized is None:
            return False, "unsafe_target", ()
        normalized_files.append(normalized)
    if len(set(normalized_files)) != len(normalized_files):
        return False, "precondition_mismatch", ()
    if not normalized_files:
        return False, "target_file_mismatch", ()
    normalized_scope: list[str] = []
    for scope in target_scope:
        normalized = _normalized_application_path(scope)
        if normalized is None:
            return False, "forbidden_scope", ()
        normalized_scope.append(normalized)
    if set(normalized_files) != set(normalized_scope):
        return False, "target_scope_mismatch", tuple(normalized_files)
    return True, "valid", tuple(normalized_files)


def application_preconditions_match(
    target_file_set: tuple[str, ...],
    request_hashes: dict[str, str],
    authorization_hashes: dict[str, str],
) -> tuple[bool, str]:
    normalized = tuple(_normalized_application_path(path) or "" for path in target_file_set)
    if any(not path for path in normalized):
        return False, "unsafe_target"
    if set(request_hashes) != set(normalized) or set(authorization_hashes) != set(normalized):
        return False, "precondition_mismatch"
    if request_hashes != authorization_hashes:
        return False, "precondition_mismatch"
    for digest in request_hashes.values():
        if not isinstance(digest, str) or len(digest) < 16 or not all(char in "0123456789abcdefABCDEF" for char in digest):
            return False, "precondition_mismatch"
    return True, "valid"


def application_request_matches_evaluation(evaluation: SandboxEvidenceEvaluation, request: ApplicationRequest) -> tuple[bool, str]:
    if request.evaluation_id != evaluation.evaluation_id:
        return False, "wrong_evaluation"
    if request.cycle_id != evaluation.cycle_id:
        return False, "wrong_cycle"
    if request.plan_id != evaluation.plan_id:
        return False, "wrong_plan"
    if request.attempt_id != evaluation.attempt_id:
        return False, "wrong_attempt"
    if request.request_id != evaluation.request_id:
        return False, "wrong_execution_request"
    if request.authorization_id != evaluation.authorization_id:
        return False, "wrong_execution_authorization"
    if request.evidence_digest != evaluation.evidence_digest:
        return False, "wrong_evidence_digest"
    return True, "valid"


def application_request_matches_disposition(record: SandboxEvaluationDispositionRecord, request: ApplicationRequest) -> tuple[bool, str]:
    if request.disposition_record_id != record.record_id:
        return False, "wrong_disposition_record"
    if request.evaluation_id != record.evaluation_id:
        return False, "wrong_evaluation"
    if request.cycle_id != record.cycle_id:
        return False, "wrong_cycle"
    if request.plan_id != record.plan_id:
        return False, "wrong_plan"
    if request.attempt_id != record.attempt_id:
        return False, "wrong_attempt"
    if request.request_id != record.request_id:
        return False, "wrong_execution_request"
    if request.authorization_id != record.authorization_id:
        return False, "wrong_execution_authorization"
    if request.evidence_digest != record.evidence_digest:
        return False, "wrong_evidence_digest"
    if record.operator_disposition != "accept_evidence_for_future_application_consideration" or not record.accepted_evidence:
        return False, "incompatible_disposition"
    if record.deeper_design_required or record.more_evidence_requested or record.revision_requested or record.another_execution_requested_metadata_only:
        return False, "deeper_design_required"
    if record.rejected_evidence or record.lifecycle_closure_requested_metadata_only or record.cleanup_failure_marked or record.live_source_integrity_failure_marked:
        return False, "incompatible_disposition"
    if record.application_authorized or record.execution_authorized or record.lifecycle_transition_applied or record.automatic_continuation:
        return False, "incompatible_disposition"
    return True, "valid"


def application_request_matches_artifact(request: ApplicationRequest, artifact: ApplicationArtifact) -> tuple[bool, str]:
    if not artifact.artifact_present:
        return False, "wrong_artifact"
    if request.proposed_application_artifact_id != artifact.artifact_id:
        return False, "wrong_artifact"
    if request.proposed_application_artifact_digest != artifact.artifact_digest:
        return False, "wrong_artifact_digest"
    if request.evaluation_id != artifact.evaluation_id:
        return False, "wrong_evaluation"
    if request.disposition_record_id != artifact.disposition_record_id:
        return False, "wrong_disposition_record"
    if request.cycle_id != artifact.cycle_id:
        return False, "wrong_cycle"
    if request.plan_id != artifact.plan_id:
        return False, "wrong_plan"
    if request.attempt_id != artifact.attempt_id:
        return False, "wrong_attempt"
    if request.request_id != artifact.request_id:
        return False, "wrong_execution_request"
    if request.authorization_id != artifact.authorization_id:
        return False, "wrong_execution_authorization"
    if request.evidence_digest != artifact.evidence_digest:
        return False, "wrong_evidence_digest"
    if request.target_file_set != artifact.target_file_set:
        return False, "target_file_mismatch"
    if request.requested_operation_set != artifact.operation_set:
        return False, "operation_mismatch"
    if request.expected_pre_application_hashes != artifact.expected_pre_application_hashes:
        return False, "precondition_mismatch"
    if request.target_scope != artifact.target_scope:
        return False, "target_scope_mismatch"
    if artifact.binary_or_unsupported_content or artifact.module_activation_implied or artifact.scheduler_or_background_implied:
        return False, "unsupported_operation"
    return True, "valid"


def application_authorization_matches_request(request: ApplicationRequest, authorization: ApplicationAuthorization) -> tuple[bool, str]:
    if authorization.application_request_id != request.application_request_id:
        return False, "wrong_application_authorization"
    if authorization.cycle_id != request.cycle_id:
        return False, "wrong_cycle"
    if authorization.plan_id != request.plan_id:
        return False, "wrong_plan"
    if authorization.attempt_id != request.attempt_id:
        return False, "wrong_attempt"
    if authorization.evaluation_id != request.evaluation_id:
        return False, "wrong_evaluation"
    if authorization.evidence_digest != request.evidence_digest:
        return False, "wrong_evidence_digest"
    if authorization.disposition_record_id != request.disposition_record_id:
        return False, "wrong_disposition_record"
    if authorization.proposed_application_artifact_id != request.proposed_application_artifact_id:
        return False, "wrong_artifact"
    if authorization.proposed_application_artifact_digest != request.proposed_application_artifact_digest:
        return False, "wrong_artifact_digest"
    if authorization.authorized_target_file_set != request.target_file_set:
        return False, "target_file_mismatch"
    if authorization.authorized_operation_set != request.requested_operation_set:
        return False, "operation_mismatch"
    if authorization.authorized_target_scope != request.target_scope:
        return False, "target_scope_mismatch"
    if authorization.expected_pre_application_hashes != request.expected_pre_application_hashes:
        return False, "precondition_mismatch"
    return True, "valid"


def application_authorization_is_available(authorization: ApplicationAuthorization, *, sequence: int) -> tuple[bool, str]:
    if authorization.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False, "non_operator_authorization"
    if not authorization.one_shot:
        return False, "wrong_application_authorization"
    if authorization.consumed:
        return False, "consumed"
    if sequence > authorization.expiration_sequence or authorization.issued_sequence > sequence:
        return False, "expired"
    if authorization.application_started or authorization.source_mutated:
        return False, "immediate_application_authority"
    forbidden_flags = {
        "git_authority": authorization.git_stage_authorized or authorization.git_commit_authorized or authorization.git_push_authorized or authorization.merge_authorized or authorization.deployment_authorized or authorization.publication_authorized,
        "module_activation": authorization.module_activation_authorized,
        "provider_model": authorization.provider_model_authorized,
        "memory_persistence": authorization.memory_write_authorized or authorization.persistence_authorized,
        "scheduler_background": authorization.scheduler_authorized or authorization.thread_authorized or authorization.background_task_authorized,
        "lifecycle": authorization.lifecycle_transition_authorized,
        "another_execution": authorization.another_execution_authorized,
        "automatic_continuation": authorization.automatic_continuation,
    }
    for reason, observed in forbidden_flags.items():
        if observed:
            return False, {
                "git_authority": "forbidden_scope",
                "module_activation": "forbidden_scope",
                "provider_model": "forbidden_scope",
                "memory_persistence": "forbidden_scope",
                "scheduler_background": "forbidden_scope",
                "lifecycle": "forbidden_scope",
                "another_execution": "forbidden_scope",
                "automatic_continuation": "forbidden_scope",
            }[reason]
    return True, "valid"


def application_scope_is_within_authorization(request: ApplicationRequest, authorization: ApplicationAuthorization) -> tuple[bool, str]:
    return (
        (True, "valid")
        if set(request.target_file_set).issubset(set(authorization.authorized_target_file_set))
        and set(request.requested_operation_set).issubset(set(authorization.authorized_operation_set))
        and set(request.target_scope).issubset(set(authorization.authorized_target_scope))
        else (False, "target_scope_mismatch")
    )


def _application_action_authority_forbidden(request: ApplicationRequest) -> tuple[bool, str]:
    if request.immediate_application_authority or request.application_started:
        return False, "immediate_application_authority"
    if request.git_stage_authorized or request.git_commit_authorized or request.git_push_authorized or request.merge_authorized or request.deployment_authorized or request.publication_authorized:
        return False, "forbidden_scope"
    if request.module_activation_authorized or request.provider_model_authorized or request.memory_write_authorized or request.persistence_authorized:
        return False, "forbidden_scope"
    if request.scheduler_authorized or request.thread_authorized or request.background_task_authorized or request.lifecycle_transition_authorized or request.another_execution_authorized or request.automatic_continuation:
        return False, "forbidden_scope"
    return True, "valid"


def _application_evaluation_is_eligible(evaluation: SandboxEvidenceEvaluation) -> tuple[bool, str]:
    if not evaluation.cleanup_verified:
        return False, "cleanup_not_verified"
    if not evaluation.live_source_unchanged:
        return False, "live_source_integrity_failed"
    if not evaluation.evidence_complete:
        return False, "evidence_incomplete"
    if not evaluation.evidence_consistent:
        return False, "evidence_inconsistent"
    if not evaluation.accepted_for_operator_review:
        return False, "evidence_incomplete"
    if not evaluation.budget_compliant or not evaluation.artifacts_within_policy or not evaluation.writes_within_policy:
        return False, "forbidden_scope"
    if evaluation.application_authorized or evaluation.application_performed or evaluation.next_attempt_authorized or evaluation.automatic_continuation or evaluation.execution_authorization_created or evaluation.lifecycle_transition_applied or evaluation.next_request_created:
        return False, "forbidden_scope"
    return True, "valid"


def evaluate_application_eligibility(
    evaluation: SandboxEvidenceEvaluation,
    disposition_record: SandboxEvaluationDispositionRecord,
    artifact: ApplicationArtifact,
    request: ApplicationRequest,
    authorization: ApplicationAuthorization,
    *,
    sequence: int,
) -> ApplicationEligibilityResult:
    checks = (
        _application_evaluation_is_eligible(evaluation),
        application_request_matches_evaluation(evaluation, request),
        application_request_matches_disposition(disposition_record, request),
        application_request_matches_artifact(request, artifact),
        application_authorization_matches_request(request, authorization),
        application_authorization_is_available(authorization, sequence=sequence),
        _application_action_authority_forbidden(request),
        application_target_scope_is_safe(request.target_file_set, request.target_scope)[:2],
        (False, "unsupported_operation") if not set(request.requested_operation_set).issubset(set(APPLICATION_ALLOWED_OPERATIONS)) else (True, "valid"),
        application_preconditions_match(request.target_file_set, request.expected_pre_application_hashes, authorization.expected_pre_application_hashes),
        application_scope_is_within_authorization(request, authorization),
    )
    for accepted, reason in checks:
        if not accepted:
            return ApplicationEligibilityResult(False, reason, evaluation, disposition_record, artifact, request, authorization)
    return ApplicationEligibilityResult(
        True,
        "valid",
        evaluation,
        disposition_record,
        artifact,
        request,
        authorization,
        eligible_for_future_application=True,
    )


MAX_APPLICATION_PREFLIGHT_TARGET_BYTES = 1_000_000
APPLICATION_ADD_OPERATIONS = {"add_exact_reviewed_file"}
APPLICATION_REPLACE_OPERATIONS = {"replace_exact_file", "apply_exact_reviewed_text_change"}
APPLICATION_DELETE_OPERATIONS = {"delete_exact_reviewed_generated_file"}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file_read_only(path: Path) -> tuple[bool, str, str]:
    try:
        if path.is_symlink():
            return False, "symlink", ""
        if not path.exists():
            return False, "missing", ""
        if not path.is_file():
            return False, "not_file", ""
        if path.stat().st_size > MAX_APPLICATION_PREFLIGHT_TARGET_BYTES:
            return False, "too_large", ""
        return True, "valid", _sha256_bytes(path.read_bytes())
    except OSError:
        return False, "unreadable", ""


def make_application_plan(
    eligibility_result: ApplicationEligibilityResult,
    *,
    ordered_target_operations: tuple[ApplicationPlanOperation, ...],
    expected_post_application_hashes: dict[str, str] | None = None,
    rollback_metadata: tuple[dict[str, Any], ...] = (),
    required_validation_commands: tuple[str, ...] = (),
    application_sequence: int = 0,
) -> ApplicationPlan:
    request = eligibility_result.request
    authorization = eligibility_result.authorization
    artifact = eligibility_result.artifact
    return ApplicationPlan(
        application_plan_id=stable_id("gsr-e4-application-plan", request.application_request_id, authorization.application_authorization_id, artifact.artifact_id, application_sequence),
        application_request_id=request.application_request_id,
        application_authorization_id=authorization.application_authorization_id,
        cycle_id=request.cycle_id,
        plan_id=request.plan_id,
        attempt_id=request.attempt_id,
        evaluation_id=request.evaluation_id,
        evidence_digest=request.evidence_digest,
        disposition_record_id=request.disposition_record_id,
        artifact_id=artifact.artifact_id,
        artifact_digest=artifact.artifact_digest,
        ordered_target_operations=ordered_target_operations,
        target_file_set=request.target_file_set,
        expected_current_hashes=dict(request.expected_pre_application_hashes),
        expected_post_application_hashes=dict(expected_post_application_hashes or {}),
        rollback_metadata=rollback_metadata,
        required_validation_commands=required_validation_commands,
        application_sequence=application_sequence,
    )


def inspect_application_targets_read_only(root: Path, target_file_set: tuple[str, ...]) -> ApplicationTargetInspection:
    root = root.resolve()
    inspected: list[str] = []
    hashes: dict[str, str] = {}
    exists: dict[str, bool] = {}
    types: dict[str, str] = {}
    unreadable: list[str] = []
    oversized: list[str] = []
    symlinks: list[str] = []
    for target in target_file_set:
        normalized = _normalized_application_path(target)
        if normalized is None:
            inspected.append(str(target))
            exists[str(target)] = False
            types[str(target)] = "unsafe"
            unreadable.append(str(target))
            continue
        path = (root / normalized).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            inspected.append(normalized)
            exists[normalized] = False
            types[normalized] = "escape"
            unreadable.append(normalized)
            continue
        inspected.append(normalized)
        exists[normalized] = path.exists()
        if path.is_symlink():
            types[normalized] = "symlink"
            symlinks.append(normalized)
            continue
        if path.exists() and path.is_file():
            ok, reason, digest = _hash_file_read_only(path)
            types[normalized] = "file" if ok else reason
            if ok:
                hashes[normalized] = digest
            elif reason == "too_large":
                oversized.append(normalized)
            else:
                unreadable.append(normalized)
        elif path.exists():
            types[normalized] = "directory"
        else:
            types[normalized] = "missing"
    return ApplicationTargetInspection(
        inspected_target_paths=tuple(inspected),
        current_target_hashes=hashes,
        target_existence_map=exists,
        target_type_map=types,
        unreadable_targets=tuple(unreadable),
        oversized_targets=tuple(oversized),
        symlink_targets=tuple(symlinks),
    )


def application_plan_matches_eligibility(
    eligibility_result: ApplicationEligibilityResult,
    plan: ApplicationPlan,
) -> tuple[bool, str]:
    if not eligibility_result.accepted or not eligibility_result.eligible_for_future_application:
        return False, "eligibility_not_accepted"
    request = eligibility_result.request
    authorization = eligibility_result.authorization
    if plan.application_request_id != request.application_request_id:
        return False, "wrong_application_request"
    if plan.application_authorization_id != authorization.application_authorization_id:
        return False, "wrong_application_authorization"
    if plan.cycle_id != request.cycle_id:
        return False, "wrong_application_plan"
    if plan.plan_id != request.plan_id:
        return False, "wrong_application_plan"
    if plan.attempt_id != request.attempt_id:
        return False, "wrong_application_plan"
    if plan.evaluation_id != request.evaluation_id:
        return False, "wrong_evaluation"
    if plan.disposition_record_id != request.disposition_record_id:
        return False, "wrong_disposition_record"
    if plan.evidence_digest != request.evidence_digest:
        return False, "wrong_evidence_digest"
    return True, "valid"


def application_plan_matches_artifact(plan: ApplicationPlan, artifact: ApplicationArtifact) -> tuple[bool, str]:
    if plan.artifact_id != artifact.artifact_id:
        return False, "wrong_artifact"
    if plan.artifact_digest != artifact.artifact_digest:
        return False, "wrong_artifact_digest"
    if plan.target_file_set != artifact.target_file_set:
        return False, "target_file_mismatch"
    if tuple(operation.operation for operation in plan.ordered_target_operations) != artifact.operation_set:
        return False, "operation_mismatch"
    if plan.expected_current_hashes != artifact.expected_pre_application_hashes:
        return False, "precondition_mismatch"
    return True, "valid"


def application_plan_matches_authorization(plan: ApplicationPlan, authorization: ApplicationAuthorization) -> tuple[bool, str]:
    if plan.application_authorization_id != authorization.application_authorization_id:
        return False, "wrong_application_authorization"
    if plan.target_file_set != authorization.authorized_target_file_set:
        return False, "target_file_mismatch"
    if tuple(operation.operation for operation in plan.ordered_target_operations) != authorization.authorized_operation_set:
        return False, "operation_mismatch"
    if plan.expected_current_hashes != authorization.expected_pre_application_hashes:
        return False, "precondition_mismatch"
    return True, "valid"


def application_plan_operation_order_is_valid(plan: ApplicationPlan) -> tuple[bool, str]:
    operations = plan.ordered_target_operations
    if not operations:
        return False, "operation_order_invalid"
    sequence_numbers = [operation.sequence for operation in operations]
    if sequence_numbers != list(range(1, len(operations) + 1)):
        return False, "operation_order_invalid"
    targets = [operation.target_path for operation in operations]
    if len(set(targets)) != len(targets):
        return False, "duplicate_target"
    if tuple(targets) != plan.target_file_set:
        return False, "target_file_mismatch"
    for operation in operations:
        if operation.operation not in APPLICATION_ALLOWED_OPERATIONS:
            return False, "operation_mismatch"
        if operation.rollback_operation not in {"restore_exact_content", "delete_added_file", "restore_deleted_file"}:
            return False, "rollback_metadata_missing"
        if operation.operation in APPLICATION_ADD_OPERATIONS and operation.rollback_operation != "delete_added_file":
            return False, "rollback_not_exact"
        if operation.operation in APPLICATION_REPLACE_OPERATIONS and operation.rollback_operation != "restore_exact_content":
            return False, "rollback_not_exact"
        if operation.operation in APPLICATION_DELETE_OPERATIONS and operation.rollback_operation != "restore_deleted_file":
            return False, "rollback_not_exact"
    return True, "valid"


def application_rollback_metadata_is_complete(plan: ApplicationPlan) -> tuple[bool, str]:
    metadata_by_target = {str(item.get("target_path")): item for item in plan.rollback_metadata}
    if len(metadata_by_target) != len(plan.rollback_metadata):
        return False, "rollback_metadata_missing"
    for operation in plan.ordered_target_operations:
        item = metadata_by_target.get(operation.target_path)
        if item is None:
            return False, "rollback_metadata_missing"
        if item.get("rollback_operation") != operation.rollback_operation:
            return False, "rollback_not_exact"
        if item.get("rollback_target_path") != operation.target_path:
            return False, "rollback_scope_mismatch"
        if not item.get("rollback_artifact_id") or item.get("rollback_artifact_id") != operation.rollback_artifact_id:
            return False, "rollback_artifact_mismatch"
        if operation.operation in APPLICATION_REPLACE_OPERATIONS | APPLICATION_DELETE_OPERATIONS:
            if item.get("rollback_expected_hash") != operation.rollback_expected_hash or not operation.rollback_expected_hash:
                return False, "rollback_not_exact"
        if str(item.get("requires", "")).lower() in {"network", "provider", "model", "git_reset", "repository_reset"}:
            return False, "rollback_not_exact"
    if set(metadata_by_target) != set(plan.target_file_set):
        return False, "rollback_scope_mismatch"
    return True, "valid"


def application_current_hashes_match(plan: ApplicationPlan, inspection: ApplicationTargetInspection) -> tuple[bool, str]:
    if inspection.symlink_targets:
        return False, "unsafe_target"
    if inspection.oversized_targets:
        return False, "target_too_large"
    if inspection.unreadable_targets:
        return False, "target_unreadable"
    for operation in plan.ordered_target_operations:
        target = operation.target_path
        exists = inspection.target_existence_map.get(target, False)
        target_type = inspection.target_type_map.get(target)
        if operation.operation in APPLICATION_ADD_OPERATIONS:
            if exists:
                return False, "target_unexpectedly_exists"
            continue
        if not exists:
            return False, "target_missing"
        if target_type != "file":
            return False, "target_type_mismatch"
        expected = plan.expected_current_hashes.get(target)
        if not expected:
            return False, "precondition_missing"
        current = inspection.current_target_hashes.get(target)
        if current != expected:
            return False, "stale_precondition"
    return True, "valid"


def application_worktree_boundary_is_safe(
    plan: ApplicationPlan,
    worktree: ApplicationWorktreeStatus,
) -> tuple[bool, str, dict[str, tuple[str, ...]]]:
    target_set = set(plan.target_file_set)
    staged = tuple(path for path in worktree.staged_paths if path in target_set)
    conflicted = tuple(path for path in worktree.conflicted_paths if path in target_set)
    modified = tuple(path for path in worktree.modified_paths if path in target_set)
    untracked = tuple(path for path in worktree.untracked_paths if path in target_set)
    known = tuple(path for path in worktree.known_dirty_paths if path not in target_set)
    expected = tuple(path for path in worktree.expected_dirty_paths if path not in target_set)
    classification = {
        "staged_targets": staged,
        "conflicted_targets": conflicted,
        "unexpected_dirty_targets": modified,
        "untracked_target_collisions": untracked,
        "known_unrelated_dirty": known,
        "expected_unrelated_dirty": expected,
    }
    if staged:
        return False, "staged_target", classification
    if conflicted:
        return False, "conflicted_target", classification
    if modified:
        return False, "unexpected_dirty_target", classification
    if untracked:
        return False, "untracked_target_collision", classification
    return True, "valid", classification


def evaluate_application_preflight(
    eligibility_result: ApplicationEligibilityResult,
    application_plan: ApplicationPlan,
    *,
    root: Path,
    worktree: ApplicationWorktreeStatus | None = None,
    sequence: int,
) -> ApplicationPreflightResult:
    artifact = eligibility_result.artifact
    request = eligibility_result.request
    authorization = eligibility_result.authorization
    inspection = inspect_application_targets_read_only(root, application_plan.target_file_set)
    worktree_status = worktree or ApplicationWorktreeStatus()
    worktree_ok, worktree_reason, worktree_classification = application_worktree_boundary_is_safe(application_plan, worktree_status)
    checks = (
        application_plan_matches_eligibility(eligibility_result, application_plan),
        application_plan_matches_artifact(application_plan, artifact),
        application_plan_matches_authorization(application_plan, authorization),
        application_authorization_is_available(authorization, sequence=sequence),
        application_plan_operation_order_is_valid(application_plan),
        application_rollback_metadata_is_complete(application_plan),
        application_target_scope_is_safe(application_plan.target_file_set, application_plan.target_file_set)[:2],
        application_current_hashes_match(application_plan, inspection),
        (worktree_ok, worktree_reason),
    )
    for accepted, reason in checks:
        if not accepted:
            return ApplicationPreflightResult(
                False,
                reason,
                eligibility_result,
                application_plan,
                artifact,
                request,
                authorization,
                inspected_target_paths=inspection.inspected_target_paths,
                current_target_hashes=inspection.current_target_hashes,
                target_existence_map=inspection.target_existence_map,
                target_type_map=inspection.target_type_map,
                worktree_classification=worktree_classification,
                live_source_read_only=inspection.live_source_read_only,
            )
    return ApplicationPreflightResult(
        True,
        "valid",
        eligibility_result,
        application_plan,
        artifact,
        request,
        authorization,
        inspected_target_paths=inspection.inspected_target_paths,
        current_target_hashes=inspection.current_target_hashes,
        target_existence_map=inspection.target_existence_map,
        target_type_map=inspection.target_type_map,
        worktree_classification=worktree_classification,
        preconditions_match=True,
        rollback_ready=True,
        artifact_consistent=True,
        operation_order_valid=True,
        target_scope_valid=True,
        live_source_read_only=inspection.live_source_read_only,
        ready_for_future_application=True,
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


def _sandbox_plan_payload(state: SandboxPlanningState, plan_id: str) -> dict[str, Any] | None:
    for payload in state.sandbox_plans:
        if payload.get("plan_id") == plan_id:
            return payload
    return None


def _sandbox_plan_review_decision_allows(
    state: SandboxPlanningState,
    decision: SandboxPlanReviewDecision,
    *,
    sequence: int,
) -> tuple[bool, str, SandboxEvaluationPlan | None]:
    if decision.decision_id in state.consumed_plan_review_decision_ids:
        return False, "sandbox_plan_review_decision_already_consumed", None
    payload = _sandbox_plan_payload(state, decision.plan_id)
    plan = deserialize(SandboxEvaluationPlan, payload) if payload is not None else None
    if decision.operator_authority == decision.plan_id:
        return False, "sandbox_plan_cannot_self_review", plan
    if plan is not None and plan.module_attachment_plan_id and decision.operator_authority == plan.module_attachment_plan_id:
        return False, "module_attachment_plan_cannot_self_review", plan
    if decision.operator_authority != OPERATOR_CONTROLLED_AUTHORITY:
        return False, "operator_authority_required", None
    if decision.consumed:
        return False, "sandbox_plan_review_decision_consumed", None
    if decision.one_shot is not True:
        return False, "one_shot_review_required", None
    if decision.expires_after_sequence is not None and sequence > decision.expires_after_sequence:
        return False, "sandbox_plan_review_decision_expired", None
    if decision.disposition not in SANDBOX_PLAN_REVIEW_DISPOSITIONS:
        return False, "unknown_sandbox_plan_disposition", None
    if set(decision.allowed_execution_scope).intersection(decision.forbidden_execution_scope):
        return False, "execution_scope_overlaps_forbidden_scope", None
    if set(decision.allowed_tool_classes).intersection(decision.forbidden_tool_classes):
        return False, "tool_class_overlaps_forbidden_tool_class", None
    if set(decision.allowed_command_categories).intersection(decision.forbidden_command_categories):
        return False, "command_category_overlaps_forbidden_category", None
    if payload is None:
        return False, "sandbox_plan_not_found", None
    assert plan is not None
    if plan.plan_only_status != "PLAN_ONLY":
        return False, "sandbox_plan_not_plan_only", plan
    if plan.plan_id not in state.pending_plan_review_queue:
        return False, "sandbox_plan_not_pending_review", plan
    return True, "sandbox_plan_review_decision_valid", plan


def _replace_sandbox_plan_for_review(
    state: SandboxPlanningState,
    plan: SandboxEvaluationPlan,
    decision: SandboxPlanReviewDecision,
) -> SandboxPlanningState:
    future = state.future_sandbox_execution_eligible_plans
    rejected = state.rejected_plans
    revision = state.revision_required_plans
    deferred = state.deferred_plans
    suspended = state.suspended_plans
    expired = state.expired_plans
    deeper = state.deeper_design_plans
    if decision.disposition == "approve_for_future_sandbox_execution":
        future = tuple(dict.fromkeys(future + (plan.plan_id,)))
    elif decision.disposition == "reject":
        rejected = tuple(dict.fromkeys(rejected + (plan.plan_id,)))
    elif decision.disposition == "revise":
        revision = tuple(dict.fromkeys(revision + (plan.plan_id,)))
    elif decision.disposition == "defer":
        deferred = tuple(dict.fromkeys(deferred + (plan.plan_id,)))
    elif decision.disposition == "suspend":
        suspended = tuple(dict.fromkeys(suspended + (plan.plan_id,)))
    elif decision.disposition == "expire":
        expired = tuple(dict.fromkeys(expired + (plan.plan_id,)))
    elif decision.disposition == "deeper_design_required":
        deeper = tuple(dict.fromkeys(deeper + (plan.plan_id,)))
    return SandboxPlanningState(
        **{
            **serialize(state),
            "plan_review_decisions": state.plan_review_decisions + (serialize(decision),),
            "consumed_plan_review_decision_ids": tuple(dict.fromkeys(state.consumed_plan_review_decision_ids + (decision.decision_id,))),
            "pending_plan_review_queue": tuple(item for item in state.pending_plan_review_queue if item != plan.plan_id),
            "future_sandbox_execution_eligible_plans": future,
            "rejected_plans": rejected,
            "revision_required_plans": revision,
            "deferred_plans": deferred,
            "suspended_plans": suspended,
            "expired_plans": expired,
            "deeper_design_plans": deeper,
        }
    )


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
