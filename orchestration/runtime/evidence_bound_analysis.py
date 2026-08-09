"""Deterministic, source-bound analysis records built from semantic problem frames.

This module deliberately has no persistence, graph, review, model, provider,
tool, authority, scheduling, or background-work dependency.  It only turns an
already-recorded semantic frame into a bounded, provisional analysis record.
The conversational runtime owns storage, turns, rendering coordination, and
exact-once behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id


SCHEMA_VERSION = "evidence_bound_analysis_v1"
QUESTION_LOOP_SCHEMA_VERSION = "evidence_bound_operator_question_v1"
INTERNAL_WORK_SCHEMA_VERSION = "evidence_bound_internal_work_v1"
EVIDENCE_PERMISSION_SCHEMA_VERSION = "evidence_bound_evidence_permission_v1"
EVIDENCE_NEXT_OPERATION_SCHEMA_VERSION = "evidence_bound_next_operation_proposal_v1"
EVIDENCE_EXECUTION_AUTHORITY_SCHEMA_VERSION = "evidence_bound_execution_authority_v1"
EVIDENCE_FIXTURE_EXECUTION_PLAN_SCHEMA_VERSION = "evidence_bound_fixture_execution_plan_v1"
EVIDENCE_FIXTURE_DRY_RUN_SCHEMA_VERSION = "evidence_bound_fixture_dry_run_result_v1"
EVIDENCE_RESULT_INGESTION_CANDIDATE_SCHEMA_VERSION = "evidence_bound_result_ingestion_candidate_v1"
EVIDENCE_ANALYSIS_REVISION_CANDIDATE_SCHEMA_VERSION = "evidence_bound_analysis_revision_candidate_v1"
EVIDENCE_MINIMAL_FIXTURE_RESULT_SCHEMA_VERSION = "evidence_bound_minimal_fixture_result_v1"
LONG_HORIZON_SELF_CORRECTION_SCHEMA_VERSION = "objective_local_self_correction_v1"
ADAPTIVE_ROUTE_ARBITRATION_SCHEMA_VERSION = "adaptive_route_arbitration_v1"
LONG_HORIZON_CORRECTION_EFFECT_SCHEMA_VERSION = "objective_local_correction_effect_v1"
LONG_HORIZON_CORRECTION_EFFECT_CONSOLIDATION_SCHEMA_VERSION = "objective_local_correction_effect_consolidation_v1"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    kind: str
    text: str
    source_span: Mapping[str, Any]
    role: str
    confidence_label: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    description: str
    expected_property: str
    result: str
    limitation: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SafeNextAction:
    action_id: str
    action: str
    required_authority: str
    tool_required: bool
    external_action: bool
    reversible: bool
    risk: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBoundAnalysisRecord:
    analysis_id: str
    source_frame_id: str
    source_problem_model_id: str
    source_equation_frame_id: str
    source_turn_id: str
    source_text: str
    domain: str
    analysis_type: str
    evidence_items: tuple[EvidenceItem, ...]
    extracted_facts: tuple[str, ...]
    assumptions: tuple[str, ...]
    constraints: tuple[str, ...]
    unknowns: tuple[str, ...]
    selected_method: str
    method_rationale: str
    validation_checks: tuple[ValidationCheck, ...]
    result_summary: str
    limitations: tuple[str, ...]
    uncertainty: tuple[str, ...]
    safe_next_actions: tuple[SafeNextAction, ...]
    prohibited_actions: tuple[str, ...]
    risk_class: str
    status: str
    created_event_id: str
    restart_summary: str
    semantic_signature: Mapping[str, Any]
    matched_roles: tuple[str, ...]
    missing_roles: tuple[str, ...]
    source_spans: tuple[Mapping[str, Any], ...]
    confidence_label: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["record_kind"] = "evidence_bound_analysis_record"
        return record


def compile_evidence_bound_analysis(
    semantic_frame_record: Mapping[str, Any],
) -> EvidenceBoundAnalysisRecord | None:
    """Build one bounded analysis from a supported persisted semantic frame.

    The input is intentionally a record, not a free-form operator message.  That
    keeps analysis tied to an existing source frame and prevents this helper from
    becoming another input classifier or a general reasoning path.
    """

    frame = _frame(semantic_frame_record)
    frame_id = str(semantic_frame_record.get("frame_id") or frame.get("frame_id") or "")
    source_text = str(frame.get("source_text") or "")
    domain = str(frame.get("domain_guess") or "")
    if not frame_id or not source_text:
        return None

    builders = {
        "operations_logistics_receivables": _operations_analysis,
        "physics_mechanics": _incline_analysis,
        "defensive_cybersecurity": _defensive_sql_analysis,
        "finance_portfolio_risk": _portfolio_risk_analysis,
        "physics_equation_model": _newtons_second_law_analysis,
    }
    builder = builders.get(domain)
    if builder is None:
        return None
    return builder(semantic_frame_record, frame)


def render_evidence_bound_analysis(record: Mapping[str, Any]) -> str:
    """Render a compact provisional analysis without claiming reviewed truth."""

    evidence = tuple(item for item in record.get("evidence_items", ()) if isinstance(item, Mapping))
    checks = tuple(item for item in record.get("validation_checks", ()) if isinstance(item, Mapping))
    actions = tuple(item for item in record.get("safe_next_actions", ()) if isinstance(item, Mapping))
    lines = (
        "I created a bounded, source-bound analysis from the existing semantic frame.",
        f"Analysis: {str(record.get('analysis_id') or '')}",
        f"Domain: {str(record.get('domain') or '').replace('_', ' ')}",
        "",
        "Evidence:",
        *_bullet_lines(str(item.get("text") or "") for item in evidence),
        "",
        f"Method: {str(record.get('selected_method') or '')}",
        f"Why this method: {str(record.get('method_rationale') or '')}",
        "",
        f"Result: {str(record.get('result_summary') or '')}",
        "",
        "Validation checks:",
        *_bullet_lines(
            f"{str(item.get('description') or '')}: {str(item.get('result') or '')}"
            for item in checks
        ),
        "",
        "Limits and uncertainty:",
        *_bullet_lines(
            tuple(str(item) for item in record.get("limitations", ()) if str(item))
            + tuple(str(item) for item in record.get("uncertainty", ()) if str(item))
        ),
        "",
        "Safe next actions:",
        *_bullet_lines(str(item.get("action") or "") for item in actions),
        "",
        "Status: source-bound and provisional analysis. It is not reviewed or admitted knowledge, and it has not created a graph claim, review, admission, model request, provider call, tool execution, or external action.",
    )
    return "\n".join(line for line in lines if line is not None)


def render_evidence_bound_analysis_recall(record: Mapping[str, Any], *, focus: str) -> str:
    """Answer one explicit analysis question without changing the analysis record."""

    analysis_id = str(record.get("analysis_id") or "")
    facts = tuple(str(item) for item in record.get("extracted_facts", ()) if str(item))
    checks = tuple(item for item in record.get("validation_checks", ()) if isinstance(item, Mapping))
    summary = str(record.get("result_summary") or "")
    if focus == "bottleneck":
        detail = next((item for item in facts if "bottleneck" in item.lower() or "blocks" in item.lower()), summary)
        prefix = "The recorded operational bottleneck is"
    elif focus == "method":
        detail = str(record.get("selected_method") or "")
        prefix = "The recorded method is"
    elif focus == "defensive":
        detail = str(record.get("method_rationale") or summary)
        prefix = "The SQL case is defensive because"
    elif focus == "finance_risk":
        detail = summary
        prefix = "The recorded finance-risk analysis is"
    elif focus == "validation":
        detail = next(
            (
                str(item.get("description") or "")
                for item in checks
                if "net force" in str(item.get("description") or "").lower()
                or "dimensional" in str(item.get("description") or "").lower()
            ),
            str(checks[0].get("description") or "") if checks else "No validation check was recorded.",
        )
        prefix = "A recorded validation check is"
    else:
        detail = summary
        prefix = "The recorded analysis says"
    return (
        f"{prefix}: {detail}\n\n"
        f"Analysis: {analysis_id}\n"
        "This is a read-only source-bound analysis recall; it did not create or change an analysis record."
    )


@dataclass(frozen=True)
class OperatorQuestionCandidate:
    """One deterministic question that could reduce a recorded analysis uncertainty.

    This remains task-local and provisional.  The conversational runtime owns
    candidate selection, request rendering, answer binding, persistence, and
    exact-once behavior.
    """

    question_id: str
    question_binding_key: str
    source_frame_id: str
    source_analysis_id: str
    domain: str
    unknown_slot_id: str
    question_intent: str
    unknown_label: str
    question_text: str
    why_it_matters: str
    expected_answer_type: str
    priority: int
    priority_reason: str
    safety_boundary: str
    status: str
    created_event_id: str
    restart_summary: str
    source_role_refs: tuple[str, ...] = ()
    schema_version: str = QUESTION_LOOP_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["record_kind"] = "operator_question_candidate"
        return record


@dataclass(frozen=True)
class OperatorQuestionAnswer:
    """A compatible operator response bound to one selected analysis question."""

    answer_id: str
    question_id: str
    question_binding_key: str
    source_frame_id: str
    source_analysis_id: str
    answer_text: str
    interpreted_value: str
    confidence_label: str
    changes_unknowns: tuple[str, ...]
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = QUESTION_LOOP_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["record_kind"] = "operator_question_answer"
        return record


@dataclass(frozen=True)
class AnalysisRefinement:
    """An append-only, source-bound continuation of a prior analysis."""

    refinement_id: str
    source_analysis_id: str
    source_frame_id: str
    source_question_id: str
    source_answer_id: str
    question_binding_key: str
    changed_unknown_slots: tuple[str, ...]
    before_summary: str
    after_summary: str
    changed_fields: tuple[str, ...]
    remaining_uncertainty: tuple[str, ...]
    safe_next_actions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = QUESTION_LOOP_SCHEMA_VERSION
    source_evidence_minimal_fixture_result_id: str = ""
    source_evidence_analysis_revision_candidate_id: str = ""

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["record_kind"] = "evidence_bound_analysis_refinement"
        return record


@dataclass(frozen=True)
class InternalWorkCandidate:
    """One safe, deterministic continuation proposed from unresolved analysis state.

    This is deliberately a task-local proposal rather than a worker task.  The
    conversational runtime owns persistence, selection, request rendering,
    operator disposition, and exact-once behavior.  Nothing in this record
    authorizes a model call, provider call, tool, graph mutation, or external
    action.
    """

    internal_work_candidate_id: str
    active_objective_id: str
    source_frame_id: str
    source_analysis_id: str
    source_refinement_id: str
    source_question_candidate_id: str
    domain: str
    unresolved_slot_id: str
    candidate_intent: str
    semantic_binding_key: str
    latest_state_id: str
    unresolved_label: str
    why_it_matters: str
    safe_deterministic_next_step: str
    continuation_prompt: str
    expected_answer_type: str
    priority: int
    authority_boundary: str
    prohibited_actions: tuple[str, ...]
    risk_class: str
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = INTERNAL_WORK_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["prohibited_actions"] = list(self.prohibited_actions)
        record["record_kind"] = "internal_work_candidate"
        return record


@dataclass(frozen=True)
class EvidencePermissionRequest:
    """One source-bound request for later evidence authority, never execution.

    The record is intentionally narrower than an evidence-acquisition plan. It
    records why supplied evidence cannot close a particular analytic gap and
    what a later, separately-authorized action could inspect. The
    conversational runtime owns persistence, ChatAddressableRequest rendering,
    operator binding, and exact-once behavior.
    """

    evidence_permission_request_id: str
    active_objective_id: str
    source_frame_id: str
    source_analysis_id: str
    source_refinement_id: str
    source_question_candidate_id: str
    source_question_answer_id: str
    source_validation_check_id: str
    domain: str
    evidence_gap_slot_id: str
    evidence_kind: str
    semantic_binding_key: str
    latest_state_id: str
    exact_information_needed: str
    why_existing_evidence_is_insufficient: str
    proposed_source_scope: tuple[str, ...]
    context_answer_type: str
    permitted_next_stage: str
    authority_boundary: str
    prohibited_actions: tuple[str, ...]
    risk_class: str
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = EVIDENCE_PERMISSION_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["proposed_source_scope"] = list(self.proposed_source_scope)
        record["prohibited_actions"] = list(self.prohibited_actions)
        record["record_kind"] = "evidence_permission_request"
        return record


@dataclass(frozen=True)
class EvidenceNextOperationProposal:
    """One bounded proposal derived from a granted evidence authorization.

    This is still not evidence gathering.  It names a safe next operation that
    would require another explicit operator decision in a later gate.  The
    conversational runtime owns persistence, request rendering, answer binding,
    and exact-once behavior.
    """

    evidence_next_operation_proposal_id: str
    active_objective_id: str
    source_evidence_request_id: str
    source_evidence_authorization_id: str
    source_frame_id: str
    source_analysis_id: str
    source_refinement_id: str
    domain: str
    evidence_gap_slot_id: str
    proposed_operation_type: str
    proposed_scope: str
    permitted_inputs: tuple[str, ...]
    expected_evidence: str
    prohibited_actions: tuple[str, ...]
    authority_required_next: str
    may_execute_now: bool
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = EVIDENCE_NEXT_OPERATION_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["permitted_inputs"] = list(self.permitted_inputs)
        record["prohibited_actions"] = list(self.prohibited_actions)
        record["record_kind"] = "evidence_next_operation_proposal"
        return record


@dataclass(frozen=True)
class EvidenceExecutionAuthorityRecord:
    """One inert authority posture for a proposed future evidence operation.

    The record deliberately does not grant immediate execution.  It preserves an
    operator decision for a later separate gate, so the action boundary remains
    explicit and restartable.
    """

    evidence_execution_authority_id: str
    active_objective_id: str
    source_evidence_request_id: str
    source_evidence_authorization_id: str
    source_evidence_next_operation_proposal_id: str
    source_evidence_next_operation_disposition_id: str
    proposed_operation_type: str
    proposed_scope: str
    operator_decision: str
    operator_response_text: str
    operator_context_text: str
    may_execute_now: bool
    execution_requires_future_gate: bool
    prohibited_actions: tuple[str, ...]
    authority_boundary: str
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = EVIDENCE_EXECUTION_AUTHORITY_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["prohibited_actions"] = list(self.prohibited_actions)
        record["record_kind"] = "evidence_execution_authority_record"
        return record


@dataclass(frozen=True)
class EvidenceFixtureExecutionPlan:
    """One inert plan for a future bounded evidence operation.

    This record names the exact evidence target and proof boundary for a later
    execution gate.  It is not an executor and never grants immediate action.
    """

    evidence_fixture_execution_plan_id: str
    active_objective_id: str
    source_evidence_request_id: str
    source_evidence_authorization_id: str
    source_evidence_next_operation_proposal_id: str
    source_evidence_next_operation_disposition_id: str
    source_evidence_execution_authority_id: str
    proposed_operation_type: str
    proposed_scope: str
    evidence_source_class: str
    allowed_inputs: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    expected_result_shape: str
    abort_conditions: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    proof_requirements: tuple[str, ...]
    authority_required_next: str
    may_execute_now: bool
    execution_requires_future_gate: bool
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = EVIDENCE_FIXTURE_EXECUTION_PLAN_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["allowed_inputs"] = list(self.allowed_inputs)
        record["forbidden_actions"] = list(self.forbidden_actions)
        record["abort_conditions"] = list(self.abort_conditions)
        record["validation_requirements"] = list(self.validation_requirements)
        record["proof_requirements"] = list(self.proof_requirements)
        record["record_kind"] = "evidence_fixture_execution_plan"
        return record


@dataclass(frozen=True)
class EvidenceFixtureDryRunResult:
    """One deterministic inert dry-run result for an accepted fixture plan.

    The dry-run evaluates only the already-recorded plan boundary.  It does not
    read files, inspect repositories, call models/providers/tools, execute
    commands, update graph truth, or ingest evidence into analysis.
    """

    evidence_fixture_dry_run_result_id: str
    source_plan_id: str
    source_execution_authority_id: str
    source_proposal_id: str
    source_evidence_request_id: str
    source_evidence_authorization_id: str
    objective_id: str
    fixture_kind: str
    proposed_operation_type: str
    evidence_source_class: str
    input_digest: str
    deterministic_result: str
    limitations: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    proof_summary: str
    may_update_analysis: bool
    may_update_graph: bool
    requires_result_ingestion_gate: bool
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = EVIDENCE_FIXTURE_DRY_RUN_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["limitations"] = list(self.limitations)
        record["blocked_actions"] = list(self.blocked_actions)
        record["record_kind"] = "evidence_fixture_dry_run_result"
        return record


@dataclass(frozen=True)
class EvidenceMinimalFixtureResult:
    """One bounded in-memory fixture result under an accepted execution plan.

    This is the first intentionally small execution boundary. It can use only
    static fixture values and already-recorded objective context; it cannot
    inspect a repository, local files, network, model, provider, tool, or
    sandbox. The result is still provisional and requires the existing
    analysis-refinement owner before it can affect objective-local posture.
    """

    evidence_minimal_fixture_result_id: str
    source_plan_id: str
    source_execution_authority_id: str
    source_proposal_id: str
    source_evidence_request_id: str
    source_evidence_authorization_id: str
    source_analysis_id: str
    source_evidence_analysis_revision_candidate_id: str
    source_internal_work_candidate_id: str
    objective_id: str
    fixture_kind: str
    deterministic_input_digest: str
    deterministic_input_summary: str
    deterministic_output: str
    limitations: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    proof_summary: str
    may_update_analysis: bool
    may_update_problem_state: bool
    may_update_graph: bool
    requires_analysis_refinement_gate: bool
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = EVIDENCE_MINIMAL_FIXTURE_RESULT_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["limitations"] = list(self.limitations)
        record["blocked_actions"] = list(self.blocked_actions)
        record["record_kind"] = "evidence_minimal_fixture_result"
        return record


@dataclass(frozen=True)
class EvidenceResultIngestionCandidate:
    """One inert candidate saying a dry-run result could inform later revision."""

    evidence_result_ingestion_candidate_id: str
    source_dry_run_result_id: str
    source_plan_id: str
    source_execution_authority_id: str
    source_proposal_id: str
    source_evidence_request_id: str
    source_evidence_authorization_id: str
    source_analysis_id: str
    objective_id: str
    candidate_effect_type: str
    supported_update_scope: tuple[str, ...]
    blocked_update_scope: tuple[str, ...]
    confidence_basis: str
    limitations: tuple[str, ...]
    required_operator_authority_next: str
    may_update_analysis: bool
    may_update_problem_state: bool
    may_update_graph: bool
    requires_analysis_revision_gate: bool
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = EVIDENCE_RESULT_INGESTION_CANDIDATE_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["supported_update_scope"] = list(self.supported_update_scope)
        record["blocked_update_scope"] = list(self.blocked_update_scope)
        record["limitations"] = list(self.limitations)
        record["record_kind"] = "evidence_result_ingestion_candidate"
        return record


@dataclass(frozen=True)
class EvidenceAnalysisRevisionCandidate:
    """One inert candidate saying an ingestion candidate may justify revision."""

    evidence_analysis_revision_candidate_id: str
    source_ingestion_candidate_id: str
    source_dry_run_result_id: str
    source_plan_id: str
    source_execution_authority_id: str
    source_proposal_id: str
    source_evidence_request_id: str
    source_evidence_authorization_id: str
    source_analysis_id: str
    objective_id: str
    proposed_revision_type: str
    proposed_revision_scope: str
    candidate_basis: str
    supported_change: tuple[str, ...]
    blocked_change: tuple[str, ...]
    limitation_summary: tuple[str, ...]
    required_operator_authority_next: str
    may_append_refinement: bool
    may_update_analysis: bool
    may_update_problem_state: bool
    may_change_answer: bool
    may_update_graph: bool
    requires_analysis_revision_gate: bool
    status: str
    created_event_id: str
    restart_summary: str
    schema_version: str = EVIDENCE_ANALYSIS_REVISION_CANDIDATE_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["supported_change"] = list(self.supported_change)
        record["blocked_change"] = list(self.blocked_change)
        record["limitation_summary"] = list(self.limitation_summary)
        record["record_kind"] = "evidence_analysis_revision_candidate"
        return record


@dataclass(frozen=True)
class LongHorizonSelfCorrectionCandidate:
    """One deterministic correction posture over existing objective-local history."""

    correction_candidate_id: str
    objective_id: str
    correction_type: str
    source_frame_ids: tuple[str, ...]
    source_route_ids: tuple[str, ...]
    source_result_ids: tuple[str, ...]
    source_plan_ids: tuple[str, ...]
    reason: str
    prior_state: str
    corrected_or_current_state: str
    recommended_nonexecuting_posture: str
    forbidden_actions: tuple[str, ...]
    may_route_next: bool
    may_execute_now: bool
    status: str
    schema_version: str = LONG_HORIZON_SELF_CORRECTION_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["source_frame_ids"] = list(self.source_frame_ids)
        record["source_route_ids"] = list(self.source_route_ids)
        record["source_result_ids"] = list(self.source_result_ids)
        record["source_plan_ids"] = list(self.source_plan_ids)
        record["forbidden_actions"] = list(self.forbidden_actions)
        record["record_kind"] = "objective_local_self_correction_candidate"
        return record


@dataclass(frozen=True)
class AdaptiveRouteArbitration:
    """One objective-local, non-executing priority projection over persisted routes."""

    arbitration_id: str
    objective_id: str
    decision: str
    selected_route_id: str
    selected_correction_id: str
    selected_correction_effect_id: str
    considered_route_ids: tuple[str, ...]
    considered_correction_ids: tuple[str, ...]
    priority_reason: str
    forbidden_actions: tuple[str, ...]
    requires_existing_authority: bool
    may_execute_now: bool
    status: str
    schema_version: str = ADAPTIVE_ROUTE_ARBITRATION_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["considered_route_ids"] = list(self.considered_route_ids)
        record["considered_correction_ids"] = list(self.considered_correction_ids)
        record["forbidden_actions"] = list(self.forbidden_actions)
        record["record_kind"] = "objective_local_adaptive_route_arbitration"
        return record


@dataclass(frozen=True)
class AdaptivePreconditionSelection:
    """A read-only current posture over one route and its existing prerequisites."""

    precondition_selection_id: str
    objective_id: str
    selected_route_id: str
    selected_correction_effect_id: str
    considered_route_ids: tuple[str, ...]
    considered_authority_ids: tuple[str, ...]
    considered_proposal_ids: tuple[str, ...]
    considered_plan_ids: tuple[str, ...]
    considered_result_ids: tuple[str, ...]
    precondition_state: str
    missing_precondition: str
    selected_nonexecuting_posture: str
    priority_reason: str
    forbidden_actions: tuple[str, ...]
    may_execute_now: bool
    status: str
    schema_version: str = ADAPTIVE_ROUTE_ARBITRATION_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        for field_name in (
            "considered_route_ids",
            "considered_authority_ids",
            "considered_proposal_ids",
            "considered_plan_ids",
            "considered_result_ids",
            "forbidden_actions",
        ):
            record[field_name] = list(record[field_name])
        record["record_kind"] = "objective_local_adaptive_precondition_selection"
        return record


@dataclass(frozen=True)
class LongHorizonCorrectionEffect:
    """A non-executing effect of a correction on prior objective-local lineage."""

    effect_id: str
    objective_id: str
    correction_id: str
    affected_frame_ids: tuple[str, ...]
    affected_route_ids: tuple[str, ...]
    affected_result_ids: tuple[str, ...]
    affected_refinement_ids: tuple[str, ...]
    effect_type: str
    selected_nonexecuting_posture: str
    forbidden_actions: tuple[str, ...]
    may_execute_now: bool
    status: str
    schema_version: str = LONG_HORIZON_CORRECTION_EFFECT_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        for field_name in (
            "affected_frame_ids",
            "affected_route_ids",
            "affected_result_ids",
            "affected_refinement_ids",
            "forbidden_actions",
        ):
            record[field_name] = list(record[field_name])
        record["record_kind"] = "objective_local_long_horizon_correction_effect"
        return record


@dataclass(frozen=True)
class LongHorizonCorrectionEffectConsolidation:
    """One current, non-executing posture over objective-local correction effects."""

    consolidation_id: str
    objective_id: str
    active_correction_effect_ids: tuple[str, ...]
    obsolete_correction_effect_ids: tuple[str, ...]
    affected_frame_ids: tuple[str, ...]
    affected_route_ids: tuple[str, ...]
    affected_result_ids: tuple[str, ...]
    affected_refinement_ids: tuple[str, ...]
    consolidation_type: str
    selected_nonexecuting_posture: str
    forbidden_actions: tuple[str, ...]
    may_execute_now: bool
    status: str
    schema_version: str = LONG_HORIZON_CORRECTION_EFFECT_CONSOLIDATION_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        for field_name in (
            "active_correction_effect_ids",
            "obsolete_correction_effect_ids",
            "affected_frame_ids",
            "affected_route_ids",
            "affected_result_ids",
            "affected_refinement_ids",
            "forbidden_actions",
        ):
            record[field_name] = list(record[field_name])
        record["record_kind"] = "objective_local_long_horizon_correction_effect_consolidation"
        return record


def compile_operator_question_candidates(
    analysis: Mapping[str, Any],
    *,
    objective_id: str,
) -> tuple[OperatorQuestionCandidate, ...]:
    """Derive inspectable question candidates from one persisted analysis record.

    Candidate identity is determined by the source analysis and semantic unknown
    slot.  It never depends on the operator's later answer wording, so replay or
    restart cannot create another candidate for the same analytic uncertainty.
    """

    source_frame_id = str(analysis.get("source_frame_id") or "")
    source_analysis_id = str(analysis.get("analysis_id") or "")
    domain = str(analysis.get("domain") or "")
    if not objective_id or not source_frame_id or not source_analysis_id or not domain:
        return ()
    candidates = []
    for specification in _question_specifications(analysis):
        unknown_slot_id = str(specification["unknown_slot_id"])
        question_intent = "resolve_unknown"
        binding_key = "|".join(
            (
                objective_id,
                source_frame_id,
                source_analysis_id,
                domain,
                unknown_slot_id,
                question_intent,
            )
        )
        question_id = stable_id("analysis-operator-question", binding_key)
        candidates.append(
            OperatorQuestionCandidate(
                question_id=question_id,
                question_binding_key=binding_key,
                source_frame_id=source_frame_id,
                source_analysis_id=source_analysis_id,
                domain=domain,
                unknown_slot_id=unknown_slot_id,
                question_intent=question_intent,
                unknown_label=str(specification["unknown_label"]),
                question_text=str(specification["question_text"]),
                why_it_matters=str(specification["why_it_matters"]),
                expected_answer_type=str(specification["expected_answer_type"]),
                priority=int(specification["priority"]),
                priority_reason=str(specification["priority_reason"]),
                safety_boundary=str(specification["safety_boundary"]),
                status="candidate",
                created_event_id=stable_id("analysis-question-candidate-event", question_id),
                restart_summary=(
                    "Deterministic task-local candidate derived from one evidence-bound analysis; "
                    "it has not created a request, graph claim, review, model call, provider call, tool execution, or external action."
                ),
                source_role_refs=tuple(str(item) for item in specification.get("source_role_refs", ()) if str(item)),
            )
        )
    return tuple(candidates)


def select_operator_question_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    initiative_allowed: bool,
    existing_pending_request: bool,
) -> tuple[dict[str, Any], ...]:
    """Choose at most one candidate while recording why every other candidate waits.

    The caller persists these records under the active objective provenance.  This
    helper has no runtime state and never creates a ChatAddressableRequest.
    """

    ordered = sorted(
        (dict(item) for item in candidates if isinstance(item, Mapping)),
        key=lambda item: (-int(item.get("priority") or 0), str(item.get("question_id") or "")),
    )
    selections: list[dict[str, Any]] = []
    for ordinal, candidate in enumerate(ordered):
        question_id = str(candidate.get("question_id") or "")
        if not question_id:
            continue
        if not initiative_allowed:
            status = "deferred_not_authorized"
            candidate_status = "deferred_not_authorized"
            reason = "The active objective did not authorize DELTA to interrupt with an analysis question."
        elif existing_pending_request:
            status = "suppressed_existing_request"
            candidate_status = "suppressed_existing_request"
            reason = "A different unresolved ChatAddressableRequest already owns the next operator reply."
        elif ordinal == 0:
            status = "selected"
            candidate_status = "selected"
            reason = str(candidate.get("priority_reason") or "This uncertainty blocks the clearest safe refinement.")
        else:
            status = "suppressed_low_priority"
            candidate_status = "suppressed_low_priority"
            reason = "A higher-priority uncertainty blocks refinement first; this candidate remains recorded without surfacing another question."
        selection_id = stable_id("analysis-question-selection", question_id, status)
        selections.append(
            {
                "selection_id": selection_id,
                "candidate_id": question_id,
                "question_binding_key": str(candidate.get("question_binding_key") or ""),
                "source_frame_id": str(candidate.get("source_frame_id") or ""),
                "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
                "domain": str(candidate.get("domain") or ""),
                "status": status,
                "candidate_status": candidate_status,
                "selection_reason": reason,
                "created_event_id": stable_id("analysis-question-selection-event", selection_id),
                "restart_summary": "Deterministic one-question selection recorded without creating a second queue or background worker.",
                "schema_version": QUESTION_LOOP_SCHEMA_VERSION,
            }
        )
    return tuple(selections)


def compile_internal_work_candidates(
    analysis: Mapping[str, Any],
    *,
    objective_id: str,
    source_question_candidates: Sequence[Mapping[str, Any]],
    source_refinement: Mapping[str, Any] | None = None,
) -> tuple[InternalWorkCandidate, ...]:
    """Derive safe continuation candidates from the latest unresolved slots.

    A refinement supersedes the base analysis only for candidate identity and
    selection context.  It never overwrites the original analysis.  Candidate
    derivation therefore uses the latest refinement when present, filters out
    already-resolved slots, and preserves earlier candidates as history.
    """

    source_frame_id = str(analysis.get("source_frame_id") or "")
    source_analysis_id = str(analysis.get("analysis_id") or "")
    domain = str(analysis.get("domain") or "")
    refinement_id = str((source_refinement or {}).get("refinement_id") or "")
    latest_state_id = refinement_id or source_analysis_id
    if not objective_id or not source_frame_id or not source_analysis_id or not domain or not latest_state_id:
        return ()

    resolved_statuses = {
        "resolved",
        "answered_unknown",
        "operator_dismissed",
        "suppressed_resolved",
    }
    candidates: list[InternalWorkCandidate] = []
    seen_slots: set[str] = set()
    for source in sorted(
        (dict(item) for item in source_question_candidates if isinstance(item, Mapping)),
        key=lambda item: (-int(item.get("priority") or 0), str(item.get("question_id") or "")),
    ):
        if str(source.get("source_analysis_id") or "") != source_analysis_id:
            continue
        slot_id = str(source.get("unknown_slot_id") or "")
        source_id = str(source.get("question_id") or "")
        if not slot_id or not source_id or slot_id in seen_slots:
            continue
        if str(source.get("status") or "") in resolved_statuses:
            continue
        seen_slots.add(slot_id)
        candidate_intent = "propose_deterministic_continuation"
        binding_key = "|".join(
            (
                objective_id,
                source_frame_id,
                source_analysis_id,
                latest_state_id,
                domain,
                slot_id,
                candidate_intent,
            )
        )
        candidate_id = stable_id("analysis-internal-work-candidate", binding_key)
        label = str(source.get("unknown_label") or slot_id.replace("_", " "))
        why = str(source.get("why_it_matters") or "This source-bound uncertainty still limits a safe refinement.")
        prompt = str(source.get("question_text") or "")
        candidates.append(
            InternalWorkCandidate(
                internal_work_candidate_id=candidate_id,
                active_objective_id=objective_id,
                source_frame_id=source_frame_id,
                source_analysis_id=source_analysis_id,
                source_refinement_id=refinement_id,
                source_question_candidate_id=source_id,
                domain=domain,
                unresolved_slot_id=slot_id,
                candidate_intent=candidate_intent,
                semantic_binding_key=binding_key,
                latest_state_id=latest_state_id,
                unresolved_label=label,
                why_it_matters=why,
                safe_deterministic_next_step=(
                    f"Keep {label} explicitly unresolved and, only if the operator chooses, record source-bound context for it."
                ),
                continuation_prompt=prompt,
                expected_answer_type=str(source.get("expected_answer_type") or ""),
                priority=int(source.get("priority") or 0),
                authority_boundary=(
                    "This is a proposal and a possible operator-answer boundary only; it does not authorize execution."
                ),
                prohibited_actions=tuple(
                    dict.fromkeys(
                        (
                            *(str(item) for item in analysis.get("prohibited_actions", ()) if str(item)),
                            "Do not call a model, provider, tool, or external action.",
                            "Do not create graph truth, review, admission, a worker, or a scheduler.",
                        )
                    )
                ),
                risk_class=str(analysis.get("risk_class") or "safe_internal"),
                status="candidate",
                created_event_id=stable_id("analysis-internal-work-candidate-event", candidate_id),
                restart_summary=(
                    "Deterministic source-bound internal continuation candidate retained under active-objective provenance; "
                    "it has not executed work or created model, provider, tool, graph, review, admission, or external side effects."
                ),
            )
        )
    return tuple(candidates)


def compile_evidence_permission_requests(
    analysis: Mapping[str, Any],
    *,
    objective_id: str,
    source_question_candidates: Sequence[Mapping[str, Any]],
    source_question_answers: Sequence[Mapping[str, Any]],
    source_refinement: Mapping[str, Any] | None = None,
) -> tuple[EvidencePermissionRequest, ...]:
    """Derive one later-evidence permission candidate from typed analytic state.

    This helper deliberately consumes persisted analysis/check/refinement
    metadata rather than free-form prompt wording. It cannot inspect a path,
    call a provider, create a packet, or start any work. A returned record is
    only a request for a later authority decision through the existing chat
    request surface.
    """

    source_frame_id = str(analysis.get("source_frame_id") or "")
    source_analysis_id = str(analysis.get("analysis_id") or "")
    domain = str(analysis.get("domain") or "")
    refinement_id = str((source_refinement or {}).get("refinement_id") or "")
    latest_state_id = refinement_id or source_analysis_id
    if not objective_id or not source_frame_id or not source_analysis_id or not domain or not refinement_id:
        return ()

    question_id = str((source_refinement or {}).get("source_question_id") or "")
    answer_id = str((source_refinement or {}).get("source_answer_id") or "")
    candidate_by_id = {
        str(item.get("question_id") or ""): dict(item)
        for item in source_question_candidates
        if isinstance(item, Mapping) and str(item.get("question_id") or "")
    }
    answer_by_id = {
        str(item.get("answer_id") or ""): dict(item)
        for item in source_question_answers
        if isinstance(item, Mapping) and str(item.get("answer_id") or "")
    }
    source_question = candidate_by_id.get(question_id, {})
    source_answer = answer_by_id.get(answer_id, {})
    check_text = " ".join(
        " ".join(
            str(item.get(field) or "")
            for field in ("check_id", "description", "expected_property", "result", "limitation")
        ).lower()
        for item in analysis.get("validation_checks", ())
        if isinstance(item, Mapping)
    )
    source_slot_id = str(source_question.get("unknown_slot_id") or "")
    context_answer_type = str(source_question.get("expected_answer_type") or "")
    answer_status = str(source_answer.get("status") or "")
    request_specs: list[dict[str, Any]] = []

    if domain == "finance_portfolio_risk" and "live" in check_text and "correlation" in check_text:
        request_specs.append(
            {
                "evidence_gap_slot_id": "finance.live_market_data_or_correlation_gap",
                "evidence_kind": "approved_market_data_context",
                "source_validation_check_id": "live_data_unavailable",
                "exact_information_needed": "Current price and correlation context needed to evaluate the recorded concentration scenario without fabricating live market facts.",
                "why_existing_evidence_is_insufficient": "The analysis records allocations and a correction scenario, but its validation check explicitly marks live prices and correlations unavailable.",
                "proposed_source_scope": (
                    "A later bounded read-only market-data lookup limited to current price and correlation context relevant to the recorded scenario.",
                    "No trade, recommendation, account access, provider call, or data retrieval is authorized by this request.",
                ),
                "context_answer_type": "",
            }
        )
    elif (
        domain == "physics_mechanics"
        and source_slot_id == "physics.requested_output_form"
        and answer_status == "bound_operator_answer"
    ):
        request_specs.append(
            {
                "evidence_gap_slot_id": "physics.frictionless_incline_deterministic_calculation",
                "evidence_kind": "deterministic_frictionless_incline_calculation",
                "source_validation_check_id": "thirty_degree_sine",
                "exact_information_needed": "The deterministic acceleration for the recorded frictionless 30-degree incline using the fixed local gravity constant g=9.8 m/s^2.",
                "why_existing_evidence_is_insufficient": "The source analysis identifies the frictionless-incline model and the requested output form, but a bounded deterministic calculation has not yet been recorded through the governed fixture path.",
                "proposed_source_scope": (
                    "A later deterministic in-memory calculation from the recorded incline angle, frictionless constraint, and fixed local constant g=9.8 m/s^2.",
                    "No file read, network access, provider/model/tool call, sandbox, graph mutation, review, admission, worker, scheduler, or external action is authorized by this request.",
                ),
                "context_answer_type": context_answer_type,
            }
        )
    elif (
        domain == "defensive_cybersecurity"
        and "unsafe" in check_text
        and "construction" in check_text
        and context_answer_type == "ownership_context"
        and answer_status == "bound_operator_answer"
    ):
        request_specs.append(
            {
                "evidence_gap_slot_id": "cyber.local_owned_fixture_verification_gap",
                "evidence_kind": "read_only_owned_fixture_inspection",
                "source_validation_check_id": "unsafe_construction_exists",
                "exact_information_needed": "Whether the recorded owned local fixture uses parameter binding at the identified SQL construction boundary.",
                "why_existing_evidence_is_insufficient": "The source establishes a defensive source-to-sink concern, but the analysis records that prepared-statement use still needs verification in code.",
                "proposed_source_scope": (
                    "A later read-only inspection of the operator-described owned local defensive fixture, limited to the named SQL construction path.",
                    "No file read, execution, mutation, scanning, payload generation, target interaction, provider call, or network access is authorized by this request.",
                ),
                "context_answer_type": "",
            }
        )
    elif (
        domain == "operations_logistics_receivables"
        and "external" in check_text
        and "status" in check_text
        and source_slot_id
        and answer_status == "bound_unknown"
    ):
        request_specs.append(
            {
                "evidence_gap_slot_id": f"operations.{source_slot_id.rsplit('.', 1)[-1]}_status_gap",
                "evidence_kind": "bounded_operational_status_lookup",
                "source_validation_check_id": "external_status_not_verified",
                "exact_information_needed": (
                    f"The current recorded {str(source_question.get('unknown_label') or 'operational status')} needed to resolve the source-bound schedule or receivable uncertainty."
                ),
                "why_existing_evidence_is_insufficient": "The analysis has an explicit unverified external-status check and the operator reported that the selected source-bound value is still unknown.",
                "proposed_source_scope": (
                    "A later bounded status lookup limited to the recorded delivery or payment uncertainty.",
                    "No contact, commitment, schedule change, purchase, file access, provider call, or network action is authorized by this request.",
                ),
                "context_answer_type": context_answer_type,
            }
        )

    records: list[EvidencePermissionRequest] = []
    for spec in request_specs:
        gap_slot_id = str(spec["evidence_gap_slot_id"])
        binding_key = "|".join(
            (
                objective_id,
                source_frame_id,
                source_analysis_id,
                refinement_id,
                domain,
                gap_slot_id,
                "request_later_bounded_evidence_permission",
            )
        )
        evidence_permission_request_id = stable_id("analysis-evidence-permission-request", binding_key)
        records.append(
            EvidencePermissionRequest(
                evidence_permission_request_id=evidence_permission_request_id,
                active_objective_id=objective_id,
                source_frame_id=source_frame_id,
                source_analysis_id=source_analysis_id,
                source_refinement_id=refinement_id,
                source_question_candidate_id=question_id,
                source_question_answer_id=answer_id,
                source_validation_check_id=str(spec["source_validation_check_id"]),
                domain=domain,
                evidence_gap_slot_id=gap_slot_id,
                evidence_kind=str(spec["evidence_kind"]),
                semantic_binding_key=binding_key,
                latest_state_id=latest_state_id,
                exact_information_needed=str(spec["exact_information_needed"]),
                why_existing_evidence_is_insufficient=str(spec["why_existing_evidence_is_insufficient"]),
                proposed_source_scope=tuple(str(item) for item in spec["proposed_source_scope"] if str(item)),
                context_answer_type=str(spec["context_answer_type"]),
                permitted_next_stage="separate_explicit_evidence_execution_review",
                authority_boundary=(
                    "This asks only whether DELTA may retain a narrow later evidence scope. It does not authorize evidence gathering, a file read, network access, a provider or model call, tool use, sandbox work, packet creation, graph mutation, review, admission, a worker, or a scheduler."
                ),
                prohibited_actions=tuple(
                    dict.fromkeys(
                        (
                            *(str(item) for item in analysis.get("prohibited_actions", ()) if str(item)),
                            "Do not gather evidence or inspect files now.",
                            "Do not access a network, provider, model, tool, sandbox, or external system.",
                            "Do not create graph truth, review, admission, a packet, worker, or scheduler.",
                        )
                    )
                ),
                risk_class=str(analysis.get("risk_class") or "safe_internal"),
                status="candidate",
                created_event_id=stable_id("analysis-evidence-permission-request-event", evidence_permission_request_id),
                restart_summary=(
                    "Deterministic source-bound evidence-permission candidate retained under active-objective provenance; "
                    "it has not gathered evidence or created model, provider, tool, file, network, graph, review, admission, worker, scheduler, or external-action side effects."
                ),
            )
        )
    return tuple(records)


def compile_evidence_next_operation_proposals(
    evidence_request: Mapping[str, Any],
    evidence_authorization: Mapping[str, Any],
    *,
    objective_id: str,
) -> tuple[EvidenceNextOperationProposal, ...]:
    """Derive one non-executing next-operation proposal from a granted request.

    The helper deliberately requires both sides of the exact permission lineage.
    A returned proposal is only a surfaceable plan for a future approval step;
    it cannot execute, inspect, fetch, call, mutate, review, or admit anything.
    """

    request_id = str(
        evidence_request.get("evidence_permission_request_id")
        or evidence_request.get("evidence_request_id")
        or ""
    )
    authorization_id = str(evidence_authorization.get("evidence_authorization_id") or "")
    if not objective_id or not request_id or not authorization_id:
        return ()
    if str(evidence_authorization.get("status") or "") != "granted_pending_separate_execution":
        return ()
    if bool(evidence_authorization.get("may_execute_now")):
        return ()
    if str(evidence_authorization.get("evidence_request_id") or "") != request_id:
        return ()

    domain = str(evidence_request.get("domain") or evidence_authorization.get("domain") or "")
    evidence_kind = str(evidence_request.get("evidence_kind") or "")
    interpreted_scope = str(evidence_authorization.get("interpreted_scope") or "")
    operation = _next_operation_specification(domain, evidence_kind, interpreted_scope)
    if not operation:
        return ()

    proposal_id = stable_id(
        "analysis-evidence-next-operation-proposal",
        objective_id,
        request_id,
        authorization_id,
        str(operation["proposed_operation_type"]),
    )
    prohibited = tuple(
        dict.fromkeys(
            (
                *(str(item) for item in evidence_authorization.get("preserved_limits", ()) if str(item)),
                "Do not execute this proposal in the current phase.",
                "Do not read files, access networks, contact providers, call models, use tools, run sandboxes, mutate source, create graph truth, review, admit, trade, scan, or take external action.",
            )
        )
    )
    return (
        EvidenceNextOperationProposal(
            evidence_next_operation_proposal_id=proposal_id,
            active_objective_id=objective_id,
            source_evidence_request_id=request_id,
            source_evidence_authorization_id=authorization_id,
            source_frame_id=str(evidence_request.get("source_frame_id") or ""),
            source_analysis_id=str(evidence_request.get("source_analysis_id") or ""),
            source_refinement_id=str(evidence_request.get("source_refinement_id") or ""),
            domain=domain,
            evidence_gap_slot_id=str(evidence_request.get("evidence_gap_slot_id") or ""),
            proposed_operation_type=str(operation["proposed_operation_type"]),
            proposed_scope=str(operation["proposed_scope"]),
            permitted_inputs=tuple(str(item) for item in operation["permitted_inputs"] if str(item)),
            expected_evidence=str(operation["expected_evidence"]),
            prohibited_actions=prohibited,
            authority_required_next=(
                "A separate operator approval is required before any evidence gathering or fixture execution. "
                "Accepting this proposal only records that the next operation is worth considering."
            ),
            may_execute_now=False,
            status="proposed",
            created_event_id=stable_id("analysis-evidence-next-operation-proposal-event", proposal_id),
            restart_summary=(
                "Evidence next-operation proposal persists exactly once under active-objective provenance; "
                "it has not started file, network, model, provider, tool, sandbox, graph, review, admission, worker, scheduler, or external-action side effects."
            ),
        ),
    )


def _next_operation_specification(
    domain: str,
    evidence_kind: str,
    interpreted_scope: str,
) -> Mapping[str, Any]:
    scope_text = f"{domain} {evidence_kind} {interpreted_scope}".lower()
    if domain == "finance_portfolio_risk" or (not domain and "market" in scope_text):
        return {
            "proposed_operation_type": "finance_market_context_proposal_only",
            "proposed_scope": (
                "Propose a bounded evidence step that would later inspect approved market-data or correlation context for the recorded allocation scenario."
            ),
            "permitted_inputs": (
                "recorded portfolio allocation",
                "recorded six-month correction concern",
                "operator-approved market-data source if later separately authorized",
            ),
            "expected_evidence": "Current price and correlation context, if a later gate separately authorizes retrieval.",
        }
    if domain == "physics_mechanics" or (not domain and "incline" in scope_text):
        return {
            "proposed_operation_type": "physics_frictionless_incline_calculation_proposal_only",
            "proposed_scope": (
                "Propose a bounded deterministic calculation for the recorded frictionless 30-degree incline using fixed local g=9.8 m/s^2."
            ),
            "permitted_inputs": (
                "recorded frictionless incline constraint",
                "recorded 30-degree angle",
                "fixed local gravity constant g=9.8 m/s^2",
            ),
            "expected_evidence": "The deterministic acceleration a = g * sin(30 degrees) for the recorded idealized incline.",
        }
    if domain == "defensive_cybersecurity" or (not domain and ("fixture" in scope_text or "inspection" in scope_text)):
        return {
            "proposed_operation_type": "defensive_owned_fixture_read_only_proposal",
            "proposed_scope": (
                "Propose a later read-only inspection of the operator-owned defensive fixture boundary named in the analysis."
            ),
            "permitted_inputs": (
                "recorded local owned fixture description",
                "recorded SQL construction boundary",
                "operator-provided path only if a later gate separately authorizes reading it",
            ),
            "expected_evidence": "Whether the owned fixture uses parameter binding at the recorded SQL boundary.",
        }
    if domain == "operations_logistics_receivables" or (not domain and "status" in scope_text):
        return {
            "proposed_operation_type": "bounded_operational_status_lookup_proposal",
            "proposed_scope": (
                "Propose a later bounded status lookup limited to the recorded delivery or payment uncertainty."
            ),
            "permitted_inputs": (
                "recorded invoice or delivery identifier",
                "recorded operational dependency",
                "operator-approved status source if later separately authorized",
            ),
            "expected_evidence": "The specific delivery, invoice, or payment status needed by the recorded analysis.",
        }
    return {}


def compile_evidence_execution_authority_records(
    proposal: Mapping[str, Any],
    disposition: Mapping[str, Any],
    *,
    objective_id: str,
    operator_decision: str,
    operator_response_text: str,
) -> tuple[EvidenceExecutionAuthorityRecord, ...]:
    """Derive one inert execution-authority posture from a proposal decision."""

    proposal_id = str(proposal.get("evidence_next_operation_proposal_id") or "")
    disposition_id = str(disposition.get("evidence_next_operation_disposition_id") or "")
    if not objective_id or not proposal_id or not disposition_id:
        return ()
    if str(disposition.get("status") or "") != "accepted_pending_separate_execution":
        return ()
    if str(disposition.get("evidence_next_operation_proposal_id") or "") != proposal_id:
        return ()
    decision = str(operator_decision or "")
    if decision not in {"approved_for_future_gate", "declined", "deferred", "context_provided"}:
        return ()
    normalized = " ".join(str(operator_response_text or "").split())
    authority_id = stable_id(
        "analysis-evidence-execution-authority",
        objective_id,
        proposal_id,
        disposition_id,
        decision,
        normalized,
    )
    prohibited = tuple(
        dict.fromkeys(
            (
                *(str(item) for item in proposal.get("prohibited_actions", ()) if str(item)),
                "Do not execute this authority record in the current phase.",
                "Do not gather evidence, read files, access networks, call providers or models, use tools, run sandboxes, mutate graph truth, perform review or admission, start a worker, start a scheduler, or take external action.",
            )
        )
    )
    return (
        EvidenceExecutionAuthorityRecord(
            evidence_execution_authority_id=authority_id,
            active_objective_id=objective_id,
            source_evidence_request_id=str(proposal.get("source_evidence_request_id") or ""),
            source_evidence_authorization_id=str(proposal.get("source_evidence_authorization_id") or ""),
            source_evidence_next_operation_proposal_id=proposal_id,
            source_evidence_next_operation_disposition_id=disposition_id,
            proposed_operation_type=str(proposal.get("proposed_operation_type") or ""),
            proposed_scope=str(proposal.get("proposed_scope") or ""),
            operator_decision=decision,
            operator_response_text=normalized,
            operator_context_text=normalized if decision == "context_provided" else "",
            may_execute_now=False,
            execution_requires_future_gate=True,
            prohibited_actions=prohibited,
            authority_boundary=(
                "This records only the operator's posture for a future bounded execution gate. "
                "It does not authorize immediate evidence gathering or any action in this phase."
            ),
            status=decision,
            created_event_id=stable_id("analysis-evidence-execution-authority-event", authority_id),
            restart_summary=(
                "Evidence execution authority posture persists exactly once and remains inert; "
                "future execution still requires a separate explicit gate."
            ),
        ),
    )


def classify_evidence_execution_authority_operator_response(request: Mapping[str, Any], message: str) -> str | None:
    """Classify a reply to an inert future-execution authority prompt."""

    text = " ".join(str(message or "").split())
    lower = text.lower()
    if not text or text.endswith("?"):
        return None
    if re.match(r"^(?:what|why|how|who|where|when|can|could|would|should|is|are|do|does|did)\b", lower):
        return None
    if re.search(r"\b(?:later|not\s+now|defer|hold|wait|park|postpone|leave\s+(?:it|that)\s+open|keep\s+(?:it|that)\s+open)\b", lower):
        return "deferred"
    if re.search(r"\b(?:no|nope|deny|decline|reject|do\s+not|don't|not\s+authorized|not\s+approved|stop)\b", lower):
        return "declined"
    if re.search(r"\b(?:yes|approve|approved|accept|accepted|authorize|authorized|allow|allowed|go\s+ahead|you\s+may|permission\s+granted|record\s+(?:the\s+)?approval)\b", lower):
        return "approved_for_future_gate"
    if re.search(r"\b(?:maybe|not\s+sure|unclear|depends)\b", lower):
        return "unclear_pending"
    if len(text.split()) >= 4:
        return "context_provided"
    return None


def render_evidence_execution_authority_request(proposal: Mapping[str, Any], disposition: Mapping[str, Any]) -> str:
    """Ask to record future execution authority without implying execution now."""

    prohibited = tuple(str(item) for item in proposal.get("prohibited_actions", ()) if str(item))
    return "\n".join(
        (
            "The bounded evidence operation proposal is accepted as worth considering.",
            f"Proposed operation: {str(proposal.get('proposed_operation_type') or '').replace('_', ' ')}",
            f"Scope: {str(proposal.get('proposed_scope') or '')}",
            "Question: Should I record approval for a future bounded execution gate, decline it, defer it, or add context?",
            "Important: I will not run the lookup, inspect files, call a model/provider/tool, use a network, run a sandbox, mutate graph truth, review/admit anything, start a worker, or take external action in this gate.",
            "Prohibited now: " + ("; ".join(prohibited) if prohibited else "No execution or external action."),
            f"Proposal disposition: {str(disposition.get('status') or '').replace('_', ' ')}",
            "Status: execution authority request only. Future execution would require a separate gate.",
        )
    )


def render_evidence_execution_authority_record(
    proposal: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> str:
    """Acknowledge one inert future-execution authority posture."""

    decision = str(authority.get("operator_decision") or authority.get("status") or "")
    if decision == "approved_for_future_gate":
        detail = "I recorded approval for a future bounded execution gate. Nothing executed now."
    elif decision == "declined":
        detail = "I recorded that this future execution authority is declined."
    elif decision == "deferred":
        detail = "I left this future execution authority deferred."
    elif decision == "context_provided":
        detail = "I recorded your context with the authority request without authorizing execution."
    else:
        detail = "I recorded the response without authorizing execution."
    return "\n".join(
        (
            f"Evidence execution authority update: {detail}",
            f"Authority record: {str(authority.get('evidence_execution_authority_id') or '')}",
            f"Proposal: {str(proposal.get('evidence_next_operation_proposal_id') or '')}",
            f"Decision: {decision.replace('_', ' ')}",
            f"Context supplied: {str(authority.get('operator_context_text') or 'None')}",
            "Execution state: no evidence gathering, file read, network access, model/provider/tool call, sandbox execution, graph mutation, review, admission, worker, scheduler, or external action started.",
        )
    )


def select_internal_work_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    initiative_allowed: bool,
    existing_pending_request: bool,
) -> tuple[dict[str, Any], ...]:
    """Select at most one safe continuation without executing it."""

    ordered = sorted(
        (dict(item) for item in candidates if isinstance(item, Mapping)),
        key=lambda item: (-int(item.get("priority") or 0), str(item.get("internal_work_candidate_id") or "")),
    )
    selections: list[dict[str, Any]] = []
    for ordinal, candidate in enumerate(ordered):
        candidate_id = str(candidate.get("internal_work_candidate_id") or "")
        if not candidate_id:
            continue
        if not initiative_allowed:
            status = "deferred_not_authorized"
            reason = "The active objective did not authorize DELTA to surface an internal continuation proposal."
        elif existing_pending_request:
            status = "suppressed_existing_request"
            reason = "An unresolved ChatAddressableRequest already owns the next operator reply."
        elif ordinal == 0:
            status = "selected"
            reason = str(candidate.get("why_it_matters") or "This is the highest-value unresolved source-bound issue.")
        else:
            status = "suppressed_low_priority"
            reason = "A higher-priority unresolved issue was selected first; this candidate remains recorded without another proposal."
        selection_id = stable_id("analysis-internal-work-selection", candidate_id, status)
        selections.append(
            {
                "internal_work_selection_id": selection_id,
                "candidate_id": candidate_id,
                "semantic_binding_key": str(candidate.get("semantic_binding_key") or ""),
                "source_frame_id": str(candidate.get("source_frame_id") or ""),
                "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
                "source_refinement_id": str(candidate.get("source_refinement_id") or ""),
                "unresolved_slot_id": str(candidate.get("unresolved_slot_id") or ""),
                "selection_status": status,
                "status": status,
                "selection_reason": reason,
                "created_event_id": stable_id("analysis-internal-work-selection-event", selection_id),
                "restart_summary": "One deterministic continuation selection was recorded without creating a second queue, worker, or scheduler.",
                "schema_version": INTERNAL_WORK_SCHEMA_VERSION,
            }
        )
    return tuple(selections)


def classify_internal_work_operator_response(candidate: Mapping[str, Any], message: str) -> str | None:
    """Classify a bounded disposition or semantically compatible direct answer.

    The returned state is only a conversational disposition.  It never grants
    execution authority, and a bare refusal defaults to deferral rather than
    destructive suppression.
    """

    text = " ".join(str(message or "").split())
    lower = text.lower()
    if not text or text.endswith("?") or re.match(r"^(?:(?:what|why|how|who|where|when|can|could|would|should|is|are)\b|(?:do|does|did)\s+(?!not\b))", lower):
        return None
    if operator_question_answer_is_compatible(candidate, text):
        return "answered_unknown" if _operator_declares_unknown(lower) else "resolved_by_answer"
    if re.search(
        r"\b(?:ignore|dismiss|suppress|do\s+not\s+(?:surface|raise|ask|bring(?:\s+up)?|mention|show)|don't\s+(?:surface|raise|ask|bring(?:\s+up)?|mention|show))\b",
        lower,
    ):
        return "operator_dismissed"
    if re.search(r"\b(?:keep|retain|leave|preserve)\b.{0,64}\b(?:ready|available|open)\b", lower):
        return "accepted"
    if re.search(r"\b(?:later|not\s+now|defer|hold|wait|park|postpone|set\s+aside|revisit\s+later|not\s+a\s+priority)\b", lower) or lower in {"no", "nope"}:
        return "operator_deferred"
    if re.search(r"\b(?:yes|okay|ok|go\s+ahead|continue|proceed|keep\s+(?:it|that)|refine)\b", lower):
        return "accepted"
    return None


def classify_evidence_permission_operator_response(request: Mapping[str, Any], message: str) -> str | None:
    """Classify an operator response to a later-evidence permission request.

    The classification is about authority posture only. A grant is retained as
    permission for a separately reviewed later step; it never means evidence
    collection should begin in this turn.
    """

    text = " ".join(str(message or "").split())
    lower = text.lower()
    if not text or text.endswith("?"):
        return None
    if re.match(r"^(?:what|why|how|who|where|when|can|could|would|should|is|are|do|does|did)\b", lower):
        return None
    if re.search(r"\b(?:later|not\s+now|defer|hold|wait|park|postpone|leave\s+(?:it|that)\s+open|keep\s+(?:it|that)\s+open)\b", lower):
        return "deferred"
    context_answer_type = str(request.get("context_answer_type") or "")
    if context_answer_type and operator_question_answer_is_compatible({"expected_answer_type": context_answer_type}, text):
        return "operator_provided_context"
    if re.search(r"\b(?:no|nope|deny|decline|do\s+not\s+authorize|don't\s+authorize|do\s+not\s+approve|don't\s+approve|not\s+authorized|keep\s+it\s+hypothetical)\b", lower):
        return "denied"
    if re.search(r"\b(?:yes|approve|approved|authorize|authorized|allow|allowed|go\s+ahead|you\s+may|permission\s+granted|use\s+an?\s+approved|local\s+fixture)\b", lower):
        return "granted_pending_separate_execution"
    if re.search(r"\b(?:maybe|not\s+sure|unclear|depends)\b", lower):
        return "unclear"
    if len(text.split()) >= 3 and context_answer_type:
        return "operator_provided_context"
    return None


def render_internal_work_proposal(candidate: Mapping[str, Any]) -> str:
    """Render one inspectable proposal without implying that work has started."""

    return "\n".join(
        (
            "One safe internal continuation is available.",
            f"Unresolved issue: {str(candidate.get('unresolved_label') or '')}",
            f"Why it matters: {str(candidate.get('why_it_matters') or '')}",
            f"Proposed next step: {str(candidate.get('safe_deterministic_next_step') or '')}",
            "You can keep it ready, defer it, dismiss it for this analysis, or provide the missing context now.",
            "Status: proposal only. No model, provider, tool, external action, graph claim, review, admission, worker, or scheduler has started.",
        )
    )


def render_evidence_permission_request(request: Mapping[str, Any]) -> str:
    """Render one exact evidence permission request without starting evidence work."""

    scope = tuple(str(item) for item in request.get("proposed_source_scope", ()) if str(item))
    prohibited = tuple(str(item) for item in request.get("prohibited_actions", ()) if str(item))
    return "\n".join(
        (
            "A bounded evidence gap remains in the source-bound analysis.",
            f"Missing evidence: {str(request.get('exact_information_needed') or '')}",
            f"Why the current evidence is insufficient: {str(request.get('why_existing_evidence_is_insufficient') or '')}",
            "Possible later scope: " + (" ".join(scope) if scope else str(request.get("evidence_kind") or "")),
            f"Question: May I retain this narrow evidence scope for a separately reviewed later step, or would you rather deny, defer, or provide the missing context now?",
            f"Safety boundary: {str(request.get('authority_boundary') or '')}",
            "Prohibited now: " + ("; ".join(prohibited) if prohibited else "No evidence gathering, tool, provider, model, file, network, graph, review, admission, worker, scheduler, or external action."),
            "Status: permission request only. No evidence gathering has started.",
        )
    )


def render_evidence_authorization(
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
) -> str:
    """Acknowledge one bound authorization without executing evidence gathering."""

    status = str(authorization.get("status") or authorization.get("authorization_decision") or "")
    if status == "granted_pending_separate_execution":
        detail = "I recorded your grant as permission to consider this narrow source in a later separately reviewed step. I did not gather evidence."
    elif status == "denied":
        detail = "I recorded that this evidence source is denied for the current analysis and will keep the analysis hypothetical or provisional."
    elif status == "deferred":
        detail = "I left this evidence request deferred and will not resurface it automatically as a new request."
    elif status == "operator_provided_context":
        detail = "I bound your supplied context to this evidence gap instead of using any external lookup."
    else:
        detail = "I recorded that the response was unclear and did not authorize evidence gathering."
    return "\n".join(
        (
            f"Evidence permission update: {detail}",
            f"Evidence gap: {str(request.get('evidence_gap_slot_id') or '')}",
            f"Decision: {status.replace('_', ' ')}",
            f"Context supplied: {str(authorization.get('operator_provided_context_text') or 'None')}",
            "Execution state: no evidence gathering, model call, provider call, tool use, file read, network access, graph mutation, review, admission, worker, scheduler, or external action started.",
        )
    )


def render_evidence_permission_recall(
    request: Mapping[str, Any],
    authorization: Mapping[str, Any] | None = None,
) -> str:
    """Read one evidence permission posture without changing it."""

    decision = str((authorization or {}).get("status") or request.get("status") or "pending")
    return "\n".join(
        (
            "The recorded evidence request is:",
            f"Gap: {str(request.get('evidence_gap_slot_id') or '')}",
            f"Needed: {str(request.get('exact_information_needed') or '')}",
            f"Decision: {decision.replace('_', ' ')}",
            f"Provided context: {str((authorization or {}).get('operator_provided_context_text') or 'None')}",
            "This is read-only recall; it did not gather evidence or create a new authorization.",
        )
    )


def compile_evidence_fixture_execution_plans(
    proposal: Mapping[str, Any],
    disposition: Mapping[str, Any],
    authority: Mapping[str, Any],
    *,
    objective_id: str,
) -> tuple[EvidenceFixtureExecutionPlan, ...]:
    """Derive one inert fixture/evidence execution plan from approved authority."""

    proposal_id = str(proposal.get("evidence_next_operation_proposal_id") or "")
    disposition_id = str(disposition.get("evidence_next_operation_disposition_id") or "")
    authority_id = str(authority.get("evidence_execution_authority_id") or "")
    if not objective_id or not proposal_id or not disposition_id or not authority_id:
        return ()
    if str(authority.get("operator_decision") or authority.get("status") or "") != "approved_for_future_gate":
        return ()
    if bool(authority.get("may_execute_now")) or not bool(authority.get("execution_requires_future_gate")):
        return ()
    if str(authority.get("source_evidence_next_operation_proposal_id") or "") != proposal_id:
        return ()
    if str(authority.get("source_evidence_next_operation_disposition_id") or "") != disposition_id:
        return ()

    specification = _fixture_execution_plan_specification(str(proposal.get("proposed_operation_type") or ""))
    if not specification:
        return ()
    plan_id = stable_id("analysis-evidence-fixture-execution-plan", objective_id, proposal_id, disposition_id, authority_id)
    forbidden = tuple(
        dict.fromkeys(
            (
                *(str(item) for item in authority.get("prohibited_actions", ()) if str(item)),
                *(str(item) for item in proposal.get("prohibited_actions", ()) if str(item)),
                "Do not execute this plan in the current phase.",
                "Do not gather evidence, read files, access networks, call models or providers, use tools, run sandboxes, mutate graph truth, review, admit, start a worker, start a scheduler, or take external action.",
            )
        )
    )
    return (
        EvidenceFixtureExecutionPlan(
            evidence_fixture_execution_plan_id=plan_id,
            active_objective_id=objective_id,
            source_evidence_request_id=str(proposal.get("source_evidence_request_id") or authority.get("source_evidence_request_id") or ""),
            source_evidence_authorization_id=str(proposal.get("source_evidence_authorization_id") or authority.get("source_evidence_authorization_id") or ""),
            source_evidence_next_operation_proposal_id=proposal_id,
            source_evidence_next_operation_disposition_id=disposition_id,
            source_evidence_execution_authority_id=authority_id,
            proposed_operation_type=str(proposal.get("proposed_operation_type") or ""),
            proposed_scope=str(proposal.get("proposed_scope") or ""),
            evidence_source_class=str(specification["evidence_source_class"]),
            allowed_inputs=tuple(str(item) for item in specification["allowed_inputs"] if str(item)),
            forbidden_actions=forbidden,
            expected_result_shape=str(specification["expected_result_shape"]),
            abort_conditions=tuple(str(item) for item in specification["abort_conditions"] if str(item)),
            validation_requirements=tuple(str(item) for item in specification["validation_requirements"] if str(item)),
            proof_requirements=tuple(str(item) for item in specification["proof_requirements"] if str(item)),
            authority_required_next=(
                "A later explicit execution gate must approve running this plan. Recording or accepting this plan does not execute it."
            ),
            may_execute_now=False,
            execution_requires_future_gate=True,
            status="planned",
            created_event_id=stable_id("analysis-evidence-fixture-execution-plan-event", plan_id),
            restart_summary=(
                "Evidence fixture execution plan persists exactly once and remains inert; "
                "actual execution, result ingestion, graph mutation, review, and replanning are deferred to later gates."
            ),
        ),
    )


def _fixture_execution_plan_specification(proposed_operation_type: str) -> Mapping[str, Any]:
    operation = str(proposed_operation_type or "")
    if operation == "finance_market_context_proposal_only":
        return {
            "evidence_source_class": "market_source_context_plan_only",
            "allowed_inputs": (
                "recorded portfolio allocation",
                "recorded risk threshold",
                "hypothetical or later-approved market context source identifier",
            ),
            "expected_result_shape": "A bounded table or summary identifying market/context fields needed, with source, timestamp, limitation, and no recommendation or trade.",
            "abort_conditions": (
                "Abort if live data retrieval would be required in this gate.",
                "Abort if account access, trading, provider calls, model calls, or network access would be needed.",
            ),
            "validation_requirements": (
                "Plan must name exact fields before execution.",
                "Plan must preserve the hypothetical/provisional analysis boundary.",
            ),
            "proof_requirements": (
                "Future execution proof must show no trade, no account access, and no unapproved provider/model/network use.",
            ),
        }
    if operation == "physics_frictionless_incline_calculation_proposal_only":
        return {
            "evidence_source_class": "deterministic_physics_incline_plan_only",
            "allowed_inputs": (
                "recorded frictionless incline constraint",
                "recorded 30-degree angle",
                "fixed local gravity constant g=9.8 m/s^2",
            ),
            "expected_result_shape": "A deterministic calculation stating a = g * sin(30 degrees) = 4.9 m/s^2, with idealized-model limits and no experimental claim.",
            "abort_conditions": (
                "Abort if the angle is absent, nonnumeric, or not 30 degrees in this first bounded evaluator.",
                "Abort if a friction term or non-frictionless condition is present.",
                "Abort if a file read, network access, provider/model/tool call, sandbox, or external action would be needed.",
            ),
            "validation_requirements": (
                "Plan must remain bound to a recorded physics_mechanics analysis.",
                "Plan must use only the frictionless 30-degree constraint and fixed local g=9.8 m/s^2.",
            ),
            "proof_requirements": (
                "Execution proof must show source-bound deterministic inputs, no external observation, and no graph/review/admission mutation.",
            ),
        }
    if operation == "defensive_owned_fixture_read_only_proposal":
        return {
            "evidence_source_class": "owned_fixture_read_only_plan",
            "allowed_inputs": (
                "operator-provided owned fixture identifier",
                "recorded defensive SQL construction boundary",
                "later-approved read-only path or snippet",
            ),
            "expected_result_shape": "A bounded observation of whether the owned fixture uses parameter binding at the recorded boundary.",
            "abort_conditions": (
                "Abort if file reading is not separately approved in a later gate.",
                "Abort if scanning, payload generation, execution, mutation, or network access would be required.",
            ),
            "validation_requirements": (
                "Plan must identify the exact owned fixture boundary.",
                "Plan must remain defensive and read-only.",
            ),
            "proof_requirements": (
                "Future execution proof must show read-only scope, no payloads, no mutation, no scan, and no external target.",
            ),
        }
    if operation == "bounded_operational_status_lookup_proposal":
        return {
            "evidence_source_class": "bounded_operational_status_plan",
            "allowed_inputs": (
                "recorded invoice or delivery identifier",
                "recorded operational dependency",
                "later-approved status source",
            ),
            "expected_result_shape": "A bounded status fact with source label, timestamp if available, uncertainty, and no contact or commitment.",
            "abort_conditions": (
                "Abort if contacting a person/system or network access would be required in this gate.",
                "Abort if schedule, purchase, payment, or operational commitments would be created.",
            ),
            "validation_requirements": (
                "Plan must name the exact status field and source class before execution.",
                "Plan must separate status observation from operational decision.",
            ),
            "proof_requirements": (
                "Future execution proof must show no contact, no commitment, no provider/tool/network use without a separate gate.",
            ),
        }
    return {}


def classify_evidence_fixture_execution_plan_operator_response(plan: Mapping[str, Any], message: str) -> str | None:
    """Classify a reply to an inert fixture/evidence execution plan."""

    text = " ".join(str(message or "").split())
    lower = text.lower()
    if not text or text.endswith("?"):
        return None
    if re.match(r"^(?:what|why|how|who|where|when|can|could|would|should|is|are|do|does|did)\b", lower):
        return None
    if re.search(r"\b(?:later|not\s+now|defer|hold|wait|park|postpone|leave\s+(?:it|that)\s+open|keep\s+(?:it|that)\s+open)\b", lower):
        return "deferred"
    if re.search(r"\b(?:no|nope|deny|decline|reject|do\s+not|don't|not\s+approved|not\s+accepted|stop)\b", lower):
        return "declined"
    if re.search(r"\b(?:yes|approve|approved|accept|accepted|record|keep\s+(?:the\s+)?plan|looks\s+good|sounds\s+good)\b", lower):
        return "accepted_pending_execution_gate"
    if re.search(r"\b(?:maybe|not\s+sure|unclear|depends)\b", lower):
        return "unclear_pending"
    if len(text.split()) >= 4:
        return "context_provided"
    return None


def render_evidence_fixture_execution_plan(plan: Mapping[str, Any]) -> str:
    """Render one inert fixture/evidence execution plan."""

    allowed = tuple(str(item) for item in plan.get("allowed_inputs", ()) if str(item))
    forbidden = tuple(str(item) for item in plan.get("forbidden_actions", ()) if str(item))
    abort = tuple(str(item) for item in plan.get("abort_conditions", ()) if str(item))
    proof = tuple(str(item) for item in plan.get("proof_requirements", ()) if str(item))
    return "\n".join(
        (
            "I prepared a bounded evidence execution plan for a later separate gate.",
            f"Plan: {str(plan.get('evidence_fixture_execution_plan_id') or '')}",
            f"Operation: {str(plan.get('proposed_operation_type') or '').replace('_', ' ')}",
            f"Evidence source class: {str(plan.get('evidence_source_class') or '')}",
            f"Scope: {str(plan.get('proposed_scope') or '')}",
            "Allowed inputs: " + ("; ".join(allowed) if allowed else "Only already-recorded source-bound context."),
            f"Expected result shape: {str(plan.get('expected_result_shape') or '')}",
            "Abort conditions: " + ("; ".join(abort) if abort else "Abort if any unapproved execution is required."),
            "Proof requirements: " + ("; ".join(proof) if proof else "Future execution must prove the authorized boundary was respected."),
            f"Next authority required: {str(plan.get('authority_required_next') or '')}",
            "Forbidden now: " + ("; ".join(forbidden) if forbidden else "No execution, file read, network, tool, provider, model, sandbox, graph, review, admission, worker, scheduler, or external action."),
            "Question: Record this bounded execution plan for a later separate execution gate, decline it, defer it, or add context?",
            "Status: plan only. It cannot execute in this phase.",
        )
    )


def render_evidence_fixture_execution_plan_update(plan: Mapping[str, Any]) -> str:
    """Acknowledge one operator disposition on an inert plan."""

    status = str(plan.get("status") or "")
    if status == "accepted_pending_execution_gate":
        detail = "I recorded this bounded plan as accepted for a later separate execution gate. It has not run."
    elif status == "declined":
        detail = "I recorded that this plan is declined."
    elif status == "deferred":
        detail = "I left this plan deferred."
    elif status == "context_provided":
        detail = "I recorded your added context with the plan without executing it."
    else:
        detail = "I left the plan pending because the response was unclear."
    return "\n".join(
        (
            f"Evidence execution plan update: {detail}",
            f"Plan: {str(plan.get('evidence_fixture_execution_plan_id') or '')}",
            f"Decision: {status.replace('_', ' ')}",
            f"Context supplied: {str(plan.get('operator_plan_context_text') or 'None')}",
            "Execution state: no evidence gathering, file read, network access, model/provider/tool call, sandbox execution, graph mutation, review, admission, worker, scheduler, or external action started.",
        )
    )


def compile_evidence_fixture_dry_run_results(
    plan: Mapping[str, Any],
    *,
    objective_id: str,
) -> tuple[EvidenceFixtureDryRunResult, ...]:
    """Compile one deterministic non-executing dry-run result from an accepted plan."""

    plan_id = str(plan.get("evidence_fixture_execution_plan_id") or "")
    authority_id = str(plan.get("source_evidence_execution_authority_id") or "")
    proposal_id = str(plan.get("source_evidence_next_operation_proposal_id") or "")
    evidence_request_id = str(plan.get("source_evidence_request_id") or "")
    evidence_authorization_id = str(plan.get("source_evidence_authorization_id") or "")
    if not objective_id or not plan_id or not authority_id or not proposal_id or not evidence_request_id or not evidence_authorization_id:
        return ()
    if str(plan.get("status") or "") not in {"accepted_pending_execution_gate", "accepted", "approved"}:
        return ()
    if bool(plan.get("may_execute_now")) or not bool(plan.get("execution_requires_future_gate")):
        return ()

    source_class = str(plan.get("evidence_source_class") or "")
    operation = str(plan.get("proposed_operation_type") or "")
    specification = _fixture_dry_run_specification(source_class, operation)
    if not specification:
        return ()

    input_payload = {
        "plan_id": plan_id,
        "objective_id": objective_id,
        "operation": operation,
        "source_class": source_class,
        "allowed_inputs": list(plan.get("allowed_inputs", ())),
        "expected_result_shape": str(plan.get("expected_result_shape") or ""),
    }
    input_digest = _canonical_digest(input_payload)
    result_id = stable_id("analysis-evidence-fixture-dry-run-result", objective_id, plan_id, input_digest)
    blocked_actions = tuple(
        dict.fromkeys(
            (
                *(str(item) for item in plan.get("forbidden_actions", ()) if str(item)),
                "No repository file read.",
                "No local filesystem read.",
                "No network or external source lookup.",
                "No model, provider, or tool call.",
                "No sandbox command execution.",
                "No source mutation.",
                "No graph truth mutation, review, admission, analysis update, result ingestion, replanning, worker, scheduler, or external action.",
            )
        )
    )
    return (
        EvidenceFixtureDryRunResult(
            evidence_fixture_dry_run_result_id=result_id,
            source_plan_id=plan_id,
            source_execution_authority_id=authority_id,
            source_proposal_id=proposal_id,
            source_evidence_request_id=evidence_request_id,
            source_evidence_authorization_id=evidence_authorization_id,
            objective_id=objective_id,
            fixture_kind=str(specification["fixture_kind"]),
            proposed_operation_type=operation,
            evidence_source_class=source_class,
            input_digest=input_digest,
            deterministic_result=str(specification["deterministic_result"]),
            limitations=tuple(str(item) for item in specification["limitations"] if str(item)),
            blocked_actions=blocked_actions,
            proof_summary=str(specification["proof_summary"]),
            may_update_analysis=False,
            may_update_graph=False,
            requires_result_ingestion_gate=True,
            status="dry_run_completed",
            created_event_id=stable_id("analysis-evidence-fixture-dry-run-result-event", result_id),
            restart_summary=(
                "Evidence fixture dry-run result persists exactly once from plan fields only; "
                "analysis revision, graph mutation, review, admission, and real execution remain deferred."
            ),
        ),
    )


def _fixture_dry_run_specification(source_class: str, operation: str) -> Mapping[str, Any]:
    if source_class == "market_source_context_plan_only" or operation == "finance_market_context_proposal_only":
        return {
            "fixture_kind": "synthetic_market_context_blocked",
            "deterministic_result": (
                "Dry-run confirms only a synthetic market-context result shape can be produced from the accepted plan. "
                "It did not fetch prices, correlations, market data, account data, recommendations, or trades."
            ),
            "limitations": (
                "No live market data was read.",
                "No portfolio advice was updated.",
                "A later result-ingestion gate is required before analysis can use any result.",
            ),
            "proof_summary": "Market dry-run used plan metadata only and blocked lookup, provider/model/tool use, network access, account access, and trading.",
        }
    if source_class == "deterministic_physics_incline_plan_only" or operation == "physics_frictionless_incline_calculation_proposal_only":
        return {
            "fixture_kind": "synthetic_physics_incline_calculation_ready",
            "deterministic_result": (
                "Dry-run confirms that the recorded frictionless 30-degree incline can be evaluated from source-bound values and fixed local g=9.8 m/s^2. "
                "It did not read files, access a network, call a model/provider/tool, or make an experimental claim."
            ),
            "limitations": (
                "The calculation applies only to the stated frictionless 30-degree idealization.",
                "No experimental measurement, friction estimate, or external source was used.",
                "A later controlled fixture transition is required before a deterministic result can refine the analysis.",
            ),
            "proof_summary": "Physics dry-run used only recorded source constraints and fixed in-memory g=9.8 m/s^2; external actions and graph/review/admission mutation remain blocked.",
        }
    if source_class == "owned_fixture_read_only_plan" or operation == "defensive_owned_fixture_read_only_proposal":
        return {
            "fixture_kind": "synthetic_owned_fixture_inspection_blocked",
            "deterministic_result": (
                "Dry-run confirms the owned-fixture inspection boundary without reading a repository file, local file, snippet, or fixture. "
                "It did not scan, execute payloads, mutate files, or inspect code."
            ),
            "limitations": (
                "No file or repository content was read.",
                "No security conclusion was produced.",
                "A later explicitly bounded fixture gate is required before any inspection result can exist.",
            ),
            "proof_summary": "Owned-fixture dry-run used plan metadata only and blocked file reads, repo reads, scanning, payloads, commands, mutation, and network access.",
        }
    if source_class == "bounded_operational_status_plan" or operation == "bounded_operational_status_lookup_proposal":
        return {
            "fixture_kind": "synthetic_operational_status_blocked",
            "deterministic_result": (
                "Dry-run confirms only a synthetic operational-status result shape can be represented. "
                "It did not contact people or systems, fetch a status, schedule work, pay invoices, or create commitments."
            ),
            "limitations": (
                "No live status source was contacted.",
                "No operational decision was changed.",
                "A later result-ingestion gate is required before analysis can use any result.",
            ),
            "proof_summary": "Operations dry-run used plan metadata only and blocked contact, network/tool/provider/model use, commitments, payments, scheduling, and external action.",
        }
    return {}


def render_evidence_fixture_dry_run_result(result: Mapping[str, Any]) -> str:
    """Render one deterministic non-executing dry-run result."""

    limitations = tuple(str(item) for item in result.get("limitations", ()) if str(item))
    blocked = tuple(str(item) for item in result.get("blocked_actions", ()) if str(item))
    return "\n".join(
        (
            "Evidence fixture dry-run result recorded.",
            f"Dry-run result: {str(result.get('evidence_fixture_dry_run_result_id') or '')}",
            f"Source plan: {str(result.get('source_plan_id') or '')}",
            f"Fixture kind: {str(result.get('fixture_kind') or '').replace('_', ' ')}",
            f"Deterministic result: {str(result.get('deterministic_result') or '')}",
            "Limitations: " + ("; ".join(limitations) if limitations else "No live evidence was gathered."),
            f"Proof summary: {str(result.get('proof_summary') or '')}",
            "Blocked actions: " + ("; ".join(blocked) if blocked else "No execution, file read, network, model, provider, tool, sandbox, graph, review, admission, analysis update, or external action."),
            "Result boundary: may_update_analysis=false; may_update_graph=false; requires_result_ingestion_gate=true.",
        )
    )


def compile_evidence_minimal_fixture_results(
    plan: Mapping[str, Any],
    *,
    objective_id: str,
    source_analysis: Mapping[str, Any],
    source_revision_candidate: Mapping[str, Any] | None = None,
    source_internal_work_candidate: Mapping[str, Any] | None = None,
) -> tuple[EvidenceMinimalFixtureResult, ...]:
    """Compile the first bounded fixture result from recorded objective data.

    The only supported fixture deliberately stays narrow: a predeclared
    hypothetical portfolio stress table. Its weights come from the already
    recorded source analysis; its stress values are static fixture constants.
    No lookup, file read, model, tool, provider, sandbox, or external action is
    available from this helper.
    """

    plan_id = str(plan.get("evidence_fixture_execution_plan_id") or "")
    authority_id = str(plan.get("source_evidence_execution_authority_id") or "")
    proposal_id = str(plan.get("source_evidence_next_operation_proposal_id") or "")
    evidence_request_id = str(plan.get("source_evidence_request_id") or "")
    evidence_authorization_id = str(plan.get("source_evidence_authorization_id") or "")
    source_analysis_id = str(source_analysis.get("analysis_id") or "")
    if not all((objective_id, plan_id, authority_id, proposal_id, evidence_request_id, evidence_authorization_id, source_analysis_id)):
        return ()
    if str(plan.get("status") or "") not in {"accepted_pending_execution_gate", "accepted", "approved"}:
        return ()
    if bool(plan.get("may_execute_now")) or not bool(plan.get("execution_requires_future_gate")):
        return ()
    if (
        str(plan.get("evidence_source_class") or "") == "deterministic_physics_incline_plan_only"
        or str(plan.get("proposed_operation_type") or "") == "physics_frictionless_incline_calculation_proposal_only"
    ):
        return _compile_frictionless_incline_fixture_result(
            plan,
            objective_id=objective_id,
            source_analysis=source_analysis,
            source_revision_candidate=source_revision_candidate,
            source_internal_work_candidate=source_internal_work_candidate,
        )
    if str(plan.get("evidence_source_class") or "") != "market_source_context_plan_only":
        return ()
    if str(plan.get("proposed_operation_type") or "") != "finance_market_context_proposal_only":
        return ()
    if str(source_analysis.get("domain") or "") != "finance_portfolio_risk":
        return ()

    revision_candidate = dict(source_revision_candidate or {})
    revision_id = str(revision_candidate.get("evidence_analysis_revision_candidate_id") or "")
    if revision_candidate and str(revision_candidate.get("source_analysis_id") or "") != source_analysis_id:
        return ()
    internal_candidate = dict(source_internal_work_candidate or {})
    internal_id = str(internal_candidate.get("internal_work_candidate_id") or "")
    if internal_candidate and revision_id and str(internal_candidate.get("source_evidence_analysis_revision_candidate_id") or "") != revision_id:
        return ()

    fixture = _minimal_portfolio_fixture(source_analysis)
    if fixture is None:
        return ()
    input_payload = {
        "plan_id": plan_id,
        "objective_id": objective_id,
        "source_analysis_id": source_analysis_id,
        "source_revision_candidate_id": revision_id,
        "source_internal_work_candidate_id": internal_id,
        "weights": fixture["weights"],
        "stress_values": fixture["stress_values"],
    }
    input_digest = _canonical_digest(input_payload)
    result_id = stable_id(
        "analysis-evidence-minimal-fixture-result",
        objective_id,
        plan_id,
        source_analysis_id,
        revision_id,
        internal_id,
        input_digest,
    )
    weighted_drawdown = sum(
        float(weight) * float(stress)
        for weight, stress in zip(fixture["weights"], fixture["stress_values"])
    )
    percent = f"{weighted_drawdown * 100:.1f}%"
    weight_summary = ", ".join(f"{weight * 100:.0f}%" for weight in fixture["weights"])
    stress_summary = ", ".join(f"{stress * 100:.0f}%" for stress in fixture["stress_values"])
    blocked_actions = _controlled_fixture_blocked_actions()
    return (
        EvidenceMinimalFixtureResult(
            evidence_minimal_fixture_result_id=result_id,
            source_plan_id=plan_id,
            source_execution_authority_id=authority_id,
            source_proposal_id=proposal_id,
            source_evidence_request_id=evidence_request_id,
            source_evidence_authorization_id=evidence_authorization_id,
            source_analysis_id=source_analysis_id,
            source_evidence_analysis_revision_candidate_id=revision_id,
            source_internal_work_candidate_id=internal_id,
            objective_id=objective_id,
            fixture_kind="in_memory_hypothetical_portfolio_drawdown_table",
            deterministic_input_digest=input_digest,
            deterministic_input_summary=(
                f"Recorded portfolio weights: {weight_summary}. "
                f"Predeclared fixture stress values: {stress_summary}."
            ),
            deterministic_output=(
                f"The in-memory hypothetical table computes a weighted drawdown of {percent} "
                "under the predeclared fixture stresses. This is a local scenario calculation, not a forecast or live-market observation."
            ),
            limitations=(
                "The stress values are static fixture inputs rather than observed market data.",
                "No current prices, correlations, account constraints, taxes, or holdings detail were read.",
                "The result is not investment advice or a trading instruction.",
                "A separate controlled analysis-refinement transition is required before this result can affect objective-local posture.",
            ),
            blocked_actions=blocked_actions,
            proof_summary=(
                "Computed only from already-recorded allocation weights and predeclared in-memory fixture stresses; "
                "no external source, filesystem, model, provider, tool, sandbox, graph, review, admission, or worker was used."
            ),
            may_update_analysis=False,
            may_update_problem_state=False,
            may_update_graph=False,
            requires_analysis_refinement_gate=True,
            status="minimal_fixture_completed",
            created_event_id=stable_id("analysis-evidence-minimal-fixture-result-event", result_id),
            restart_summary=(
                "The bounded in-memory fixture result persists exactly once from an accepted plan and recorded source analysis; "
                "it remains provisional until the controlled existing-refinement transition records its local effect."
            ),
        ),
    )


def compile_long_horizon_self_correction_candidates(
    *,
    objective_id: str,
    semantic_frames: Sequence[Mapping[str, Any]],
    analyses: Sequence[Mapping[str, Any]] = (),
    fixture_results: Sequence[Mapping[str, Any]] = (),
    rejected_fixture_inputs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]] = (),
) -> tuple[LongHorizonSelfCorrectionCandidate, ...]:
    """Derive non-executing correction posture from existing objective history.

    Inputs are already-persisted semantic frames and controlled-loop records.
    The helper cannot inspect new evidence, create authority, mutate graph truth,
    or execute a route. The runtime remains the only persistence owner.
    """

    if not objective_id:
        return ()
    frames = [dict(item) for item in semantic_frames if isinstance(item, Mapping)]
    frame_by_id = {
        str(item.get("frame_id") or ""): item
        for item in frames
        if str(item.get("frame_id") or "")
    }
    values: list[LongHorizonSelfCorrectionCandidate] = []
    for frame in frames:
        candidate = _capability_route_candidate_from_frame(frame)
        frame_id = str(frame.get("frame_id") or "")
        route_id = str(candidate.get("capability_route_candidate_id") or "")
        decision = str(candidate.get("decision") or "")
        if not frame_id or not route_id:
            continue
        if decision == "blocked":
            values.append(
                _self_correction_candidate(
                    objective_id=objective_id,
                    correction_type="blocked_external_boundary",
                    source_frame_ids=(frame_id,),
                    source_route_ids=(route_id,),
                    reason=str(candidate.get("rationale") or "The route remains blocked by its safety boundary."),
                    prior_state="blocked route selected",
                    current_state="blocked boundary remains unresolved",
                    posture="Retain the blocked boundary and wait for explicitly authorized, source-bound evidence; do not execute or infer the missing result.",
                    forbidden_actions=tuple(str(item) for item in candidate.get("forbidden_actions", ()) if str(item)),
                    may_route_next=False,
                )
            )
        elif decision == "clarify":
            values.append(
                _self_correction_candidate(
                    objective_id=objective_id,
                    correction_type="unsupported_to_clarify",
                    source_frame_ids=(frame_id,),
                    source_route_ids=(route_id,),
                    reason=str(candidate.get("rationale") or "The source remains under-specified for a safe route."),
                    prior_state="clarification or unsupported boundary",
                    current_state="clarification remains required",
                    posture="Preserve uncertainty and request only source-grounded clarification through an existing operator-facing path if one is later selected.",
                    forbidden_actions=tuple(str(item) for item in candidate.get("forbidden_actions", ()) if str(item)),
                    may_route_next=True,
                )
            )

    for index, earlier in enumerate(frames):
        earlier_frame = _semantic_input_frame(earlier)
        earlier_domain = str(earlier_frame.get("domain_guess") or "")
        earlier_route = _capability_route_candidate_from_frame(earlier)
        earlier_requires_clarification = str(earlier_route.get("decision") or "") == "clarify"
        earlier_id = str(earlier.get("frame_id") or "")
        earlier_route_id = str(earlier_route.get("capability_route_candidate_id") or "")
        if not earlier_id or not earlier_route_id:
            continue
        for later in frames[index + 1 :]:
            later_frame = _semantic_input_frame(later)
            later_id = str(later.get("frame_id") or "")
            if not later_id or str(later_frame.get("domain_guess") or "") != earlier_domain:
                continue
            later_route = _capability_route_candidate_from_frame(later)
            later_route_id = str(later_route.get("capability_route_candidate_id") or "")
            later_text = str(later_frame.get("source_text") or "")
            if earlier_requires_clarification and _has_material_context_resolution(later_text):
                values.append(
                    _self_correction_candidate(
                        objective_id=objective_id,
                        correction_type="resolved_missing_context",
                        source_frame_ids=(earlier_id, later_id),
                        source_route_ids=(earlier_route_id, later_route_id),
                        reason="A later source-bound frame supplies an explicit context-resolution marker for an earlier clarification posture.",
                        prior_state="clarification required because context was missing",
                        current_state="later source provides material context; prior uncertainty is narrowed but not promoted as truth",
                        posture="Use the later source as bounded context for an existing route only after its normal authority boundary; do not execute automatically.",
                        forbidden_actions=tuple(str(item) for item in later_route.get("forbidden_actions", ()) if str(item)),
                        may_route_next=True,
                    )
                )
            if earlier_domain == "physics_mechanics":
                earlier_angle = _frictionless_incline_angle(earlier_frame)
                later_angle = _frictionless_incline_angle(later_frame)
                if earlier_angle is not None and later_angle is not None and not math.isclose(earlier_angle, later_angle):
                    values.append(
                        _self_correction_candidate(
                            objective_id=objective_id,
                            correction_type="contradiction_or_supersession",
                            source_frame_ids=(earlier_id, later_id),
                            source_route_ids=(earlier_route_id, later_route_id),
                            reason=f"The later source-bound physics frame records {later_angle:g} degrees, which conflicts with the earlier {earlier_angle:g}-degree assumption.",
                            prior_state=f"frictionless incline assumption: {earlier_angle:g} degrees",
                            current_state=f"later source-bound correction: {later_angle:g} degrees; earlier assumption is superseded for future framing only",
                            posture="Retain both frames and require the existing authority path before any new deterministic calculation; do not recompute automatically.",
                            forbidden_actions=tuple(str(item) for item in later_route.get("forbidden_actions", ()) if str(item)),
                            may_route_next=True,
                        )
                    )
            if earlier_domain == "finance_portfolio_risk":
                earlier_allocation = _portfolio_allocation_signature(earlier_frame)
                later_allocation = _portfolio_allocation_signature(later_frame)
                if (
                    earlier_allocation is not None
                    and later_allocation is not None
                    and earlier_allocation != later_allocation
                ):
                    values.append(
                        _self_correction_candidate(
                            objective_id=objective_id,
                            correction_type="contradiction_or_supersession",
                            source_frame_ids=(earlier_id, later_id),
                            source_route_ids=(earlier_route_id, later_route_id),
                            reason=(
                                "The later source-bound allocation conflicts with the earlier portfolio allocation, "
                                "so the earlier controlled result is no longer current."
                            ),
                            prior_state=(
                                "portfolio allocation assumption: "
                                f"{earlier_allocation[0]:g}/{earlier_allocation[1]:g}/{earlier_allocation[2]:g}"
                            ),
                            current_state=(
                                "later source-bound correction: "
                                f"{later_allocation[0]:g}/{later_allocation[1]:g}/{later_allocation[2]:g}; "
                                "earlier assumption is superseded for future framing only"
                            ),
                            posture=(
                                "Retain both source records and require the existing authority path before any new "
                                "deterministic table; do not infer replacement weights or recompute automatically."
                            ),
                            forbidden_actions=tuple(
                                str(item) for item in later_route.get("forbidden_actions", ()) if str(item)
                            ),
                            may_route_next=True,
                        )
                    )

    analysis_by_id = {
        str(item.get("analysis_id") or ""): dict(item)
        for item in analyses
        if isinstance(item, Mapping) and str(item.get("analysis_id") or "")
    }
    for result in fixture_results:
        if not isinstance(result, Mapping):
            continue
        result_id = str(result.get("evidence_minimal_fixture_result_id") or "")
        analysis = analysis_by_id.get(str(result.get("source_analysis_id") or ""))
        frame_id = str((analysis or {}).get("source_frame_id") or "")
        frame = frame_by_id.get(frame_id, {})
        route = _capability_route_candidate_from_frame(frame)
        route_id = str(route.get("capability_route_candidate_id") or "")
        if not result_id or not frame_id or not route_id:
            continue
        values.append(
            _self_correction_candidate(
                objective_id=objective_id,
                correction_type="completed_positive_loop",
                source_frame_ids=(frame_id,),
                source_route_ids=(route_id,),
                source_result_ids=(result_id,),
                source_plan_ids=(str(result.get("source_plan_id") or ""),),
                reason="An existing controlled fixture result already completed this bounded source-to-refinement path.",
                prior_state="eligible controlled route awaiting its existing authority chain",
                current_state="completed bounded positive loop remains stable and provisional",
                posture="Do not repeat the fixture, refinement, or selection. Retain the completed record and wait for a genuinely new source-bound correction.",
                forbidden_actions=tuple(str(item) for item in result.get("blocked_actions", ()) if str(item)),
                may_route_next=False,
            )
        )

    for plan, source_analysis in rejected_fixture_inputs:
        if not isinstance(plan, Mapping) or not isinstance(source_analysis, Mapping):
            continue
        correction = _malformed_fixture_rejection_correction(
            objective_id=objective_id,
            plan=plan,
            source_analysis=source_analysis,
        )
        if correction is not None:
            values.append(correction)

    unique: dict[str, LongHorizonSelfCorrectionCandidate] = {}
    for item in values:
        unique.setdefault(item.correction_candidate_id, item)
    return tuple(unique[key] for key in sorted(unique))


def compile_long_horizon_correction_effects(
    *,
    objective_id: str,
    semantic_frames: Sequence[Mapping[str, Any]],
    correction_candidates: Sequence[Mapping[str, Any]],
    analyses: Sequence[Mapping[str, Any]] = (),
    fixture_results: Sequence[Mapping[str, Any]] = (),
    refinements: Sequence[Mapping[str, Any]] = (),
) -> tuple[LongHorizonCorrectionEffect, ...]:
    """Project correction consequences over existing local lineage without mutation.

    A correction effect can suppress a stale route/result from later selection,
    but it cannot recompute, revise, execute, or change graph truth.
    """

    if not objective_id:
        return ()
    analyses_by_frame: dict[str, list[Mapping[str, Any]]] = {}
    for analysis in analyses:
        if not isinstance(analysis, Mapping):
            continue
        frame_id = str(analysis.get("source_frame_id") or "")
        if frame_id:
            analyses_by_frame.setdefault(frame_id, []).append(analysis)
    result_by_analysis: dict[str, list[Mapping[str, Any]]] = {}
    for result in fixture_results:
        if not isinstance(result, Mapping):
            continue
        analysis_id = str(result.get("source_analysis_id") or "")
        if analysis_id:
            result_by_analysis.setdefault(analysis_id, []).append(result)
    refinements_by_result: dict[str, list[Mapping[str, Any]]] = {}
    for refinement in refinements:
        if not isinstance(refinement, Mapping):
            continue
        result_id = str(refinement.get("source_evidence_minimal_fixture_result_id") or "")
        if result_id:
            refinements_by_result.setdefault(result_id, []).append(refinement)

    candidates = [dict(item) for item in correction_candidates if isinstance(item, Mapping)]
    superseded_route_ids = {
        str(route_id)
        for item in candidates
        if str(item.get("correction_type") or "") == "contradiction_or_supersession"
        for route_id in item.get("source_route_ids", ())
        if str(route_id)
    }
    effects: list[LongHorizonCorrectionEffect] = []
    for correction in candidates:
        correction_id = str(correction.get("correction_candidate_id") or "")
        correction_type = str(correction.get("correction_type") or "")
        frame_ids = tuple(str(item) for item in correction.get("source_frame_ids", ()) if str(item))
        route_ids = tuple(str(item) for item in correction.get("source_route_ids", ()) if str(item))
        if not correction_id:
            continue
        effect_type = ""
        selected_posture = ""
        affected_frame_ids = frame_ids
        affected_route_ids = route_ids
        if correction_type == "contradiction_or_supersession":
            affected_frame_ids = frame_ids[:-1] or frame_ids
            affected_route_ids = route_ids[:-1] or route_ids
            effect_type = "stale_suppression"
            selected_posture = (
                "Treat the earlier route and its controlled result as stale. Preserve both sources and wait for the existing "
                "authority path before any new source-bound calculation or scenario table; do not infer replacement weights or inputs."
            )
        elif correction_type == "resolved_missing_context":
            effect_type = "resolved_context"
            selected_posture = (
                "Use the later operator-supplied context only to narrow the existing clarification posture; do not execute evidence work."
            )
        elif correction_type == "blocked_external_boundary":
            effect_type = "blocked_persists"
            selected_posture = "Retain the blocked safety boundary until its exact authority and source constraints are resolved."
        elif correction_type == "completed_positive_loop":
            if any(route_id in superseded_route_ids for route_id in route_ids):
                continue
            effect_type = "stable_completed"
            selected_posture = "Retain the completed provisional result without repeating its fixture, refinement, or selection."
        else:
            continue

        result_ids: list[str] = []
        for frame_id in affected_frame_ids:
            for analysis in analyses_by_frame.get(frame_id, ()):
                analysis_id = str(analysis.get("analysis_id") or "")
                for result in result_by_analysis.get(analysis_id, ()):
                    result_id = str(result.get("evidence_minimal_fixture_result_id") or "")
                    if result_id:
                        result_ids.append(result_id)
        if correction_type == "completed_positive_loop":
            result_ids.extend(str(item) for item in correction.get("source_result_ids", ()) if str(item))
        result_ids = list(dict.fromkeys(result_ids))
        refinement_ids = list(
            dict.fromkeys(
                str(refinement.get("refinement_id") or "")
                for result_id in result_ids
                for refinement in refinements_by_result.get(result_id, ())
                if str(refinement.get("refinement_id") or "")
            )
        )
        effects.append(
            _correction_effect(
                objective_id=objective_id,
                correction_id=correction_id,
                affected_frame_ids=affected_frame_ids,
                affected_route_ids=affected_route_ids,
                affected_result_ids=tuple(result_ids),
                affected_refinement_ids=tuple(refinement_ids),
                effect_type=effect_type,
                posture=selected_posture,
                forbidden_actions=tuple(str(item) for item in correction.get("forbidden_actions", ()) if str(item)),
            )
        )
    unique: dict[str, LongHorizonCorrectionEffect] = {}
    for effect in effects:
        unique.setdefault(effect.effect_id, effect)
    return tuple(unique[key] for key in sorted(unique))


def _correction_effect(
    *,
    objective_id: str,
    correction_id: str,
    affected_frame_ids: tuple[str, ...],
    affected_route_ids: tuple[str, ...],
    affected_result_ids: tuple[str, ...],
    affected_refinement_ids: tuple[str, ...],
    effect_type: str,
    posture: str,
    forbidden_actions: tuple[str, ...],
) -> LongHorizonCorrectionEffect:
    return LongHorizonCorrectionEffect(
        effect_id=stable_id(
            "long-horizon-correction-effect",
            objective_id,
            correction_id,
            effect_type,
            *affected_frame_ids,
            *affected_route_ids,
            *affected_result_ids,
            *affected_refinement_ids,
        ),
        objective_id=objective_id,
        correction_id=correction_id,
        affected_frame_ids=affected_frame_ids,
        affected_route_ids=affected_route_ids,
        affected_result_ids=affected_result_ids,
        affected_refinement_ids=affected_refinement_ids,
        effect_type=effect_type,
        selected_nonexecuting_posture=posture,
        forbidden_actions=tuple(dict.fromkeys(forbidden_actions)),
        may_execute_now=False,
        status="deterministic_correction_effect_only",
    )


def compile_long_horizon_correction_effect_consolidation(
    *,
    objective_id: str,
    semantic_frames: Sequence[Mapping[str, Any]],
    correction_candidates: Sequence[Mapping[str, Any]],
    correction_effects: Sequence[Mapping[str, Any]],
) -> LongHorizonCorrectionEffectConsolidation | None:
    """Consolidate existing correction effects into one current safe posture.

    The projection is deliberately read-only: it only classifies persisted
    source lineage and never recomputes a result, changes a claim, or grants
    authority.  Temporal precedence comes from source-frame order, never from
    record insertion order or a model judgment.
    """

    if not objective_id:
        return None
    frames = [dict(item) for item in semantic_frames if isinstance(item, Mapping)]
    frame_order = {str(item.get("frame_id") or ""): index for index, item in enumerate(frames)}
    frame_by_id = {str(item.get("frame_id") or ""): item for item in frames if str(item.get("frame_id") or "")}
    candidates = {
        str(item.get("correction_candidate_id") or ""): dict(item)
        for item in correction_candidates
        if isinstance(item, Mapping) and str(item.get("correction_candidate_id") or "")
    }
    effects = [dict(item) for item in correction_effects if isinstance(item, Mapping) and str(item.get("effect_id") or "")]
    if not effects:
        return None

    def unique(values: Sequence[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if value))

    def domain_for(candidate: Mapping[str, Any]) -> str:
        frame_ids = tuple(str(item) for item in candidate.get("source_frame_ids", ()) if str(item))
        frame = _semantic_input_frame(frame_by_id.get(frame_ids[-1], {})) if frame_ids else {}
        return str(frame.get("domain_guess") or "")

    def latest_index(candidate: Mapping[str, Any]) -> int:
        return max((frame_order.get(str(frame_id), -1) for frame_id in candidate.get("source_frame_ids", ())), default=-1)

    def explicit_retraction(frame: Mapping[str, Any]) -> bool:
        source = str(_semantic_input_frame(frame).get("source_text") or "").lower()
        return bool(re.search(r"\b(?:ignore|retract|withdraw|restore)\b.*\b(?:correction|original|earlier)\b|\boriginal\b.*\b(?:correct|restore)\b", source))

    def same_signature(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        left_frame = _semantic_input_frame(left)
        right_frame = _semantic_input_frame(right)
        domain = str(left_frame.get("domain_guess") or "")
        if domain != str(right_frame.get("domain_guess") or ""):
            return False
        if domain == "physics_mechanics":
            left_angle = _frictionless_incline_angle(left_frame)
            right_angle = _frictionless_incline_angle(right_frame)
            return left_angle is not None and right_angle is not None and math.isclose(left_angle, right_angle)
        if domain == "finance_portfolio_risk":
            left_allocation = _portfolio_allocation_signature(left_frame)
            right_allocation = _portfolio_allocation_signature(right_frame)
            return left_allocation is not None and left_allocation == right_allocation
        return False

    metadata: list[dict[str, Any]] = []
    for effect in effects:
        candidate = candidates.get(str(effect.get("correction_id") or ""), {})
        metadata.append(
            {
                "effect": effect,
                "candidate": candidate,
                "domain": domain_for(candidate),
                "latest_index": latest_index(candidate),
                "prior_index": max(
                    (frame_order.get(str(item), -1) for item in tuple(candidate.get("source_frame_ids", ()))[:-1]),
                    default=-1,
                ),
            }
        )
    dynamic = [item for item in metadata if str(item["effect"].get("effect_type") or "") in {"stale_suppression", "resolved_context"}]
    blocked = [item for item in metadata if str(item["effect"].get("effect_type") or "") == "blocked_persists"]
    stable = [item for item in metadata if str(item["effect"].get("effect_type") or "") == "stable_completed"]

    active: list[dict[str, Any]] = []
    obsolete: list[dict[str, Any]] = []
    consolidation_type = "stable_unaffected"
    posture = "Retain the existing source-bound posture without recomputation or execution."
    retraction = None
    for item in sorted(dynamic, key=lambda value: (int(value["latest_index"]), str(value["effect"].get("effect_id") or "")), reverse=True):
        candidate = item["candidate"]
        frame_ids = tuple(str(value) for value in candidate.get("source_frame_ids", ()) if str(value))
        latest_frame = frame_by_id.get(frame_ids[-1], {}) if frame_ids else {}
        if explicit_retraction(latest_frame) and frame_ids:
            restored = next(
                (
                    frame_by_id.get(frame_id, {})
                    for frame_id in frame_order
                    if frame_order[frame_id] < int(item["latest_index"])
                    and same_signature(frame_by_id.get(frame_id, {}), latest_frame)
                ),
                {},
            )
            if restored:
                retraction = (item, restored)
                break
    if retraction is not None:
        active = [retraction[0]]
        restored_frame_id = str(retraction[1].get("frame_id") or "")
        restored_route_id = str(_capability_route_candidate_from_frame(retraction[1]).get("capability_route_candidate_id") or "")
        obsolete = [
            item for item in dynamic
            if item is not retraction[0] and restored_route_id in tuple(str(value) for value in item["effect"].get("affected_route_ids", ()))
        ]
        consolidation_type = "retraction_restores_stable"
        posture = (
            "An explicit later source restores the exact earlier recorded assumption. Retain the historical controlled result as stable "
            "without recomputation; preserve every correction record and do not infer replacement inputs."
        )
    elif dynamic:
        current_by_domain: dict[str, dict[str, Any]] = {}
        for item in dynamic:
            domain = str(item["domain"] or "unknown")
            current = current_by_domain.get(domain)
            if current is None or (
                int(item["latest_index"]),
                int(item["prior_index"]),
                str(item["effect"].get("effect_id") or ""),
            ) > (
                int(current["latest_index"]),
                int(current["prior_index"]),
                str(current["effect"].get("effect_id") or ""),
            ):
                current_by_domain[domain] = item
        active = [current_by_domain[key] for key in sorted(current_by_domain)]
        obsolete = [item for item in dynamic if item not in active]
        active_types = {str(item["effect"].get("effect_type") or "") for item in active}
        if len(active) > 1:
            consolidation_type = "compound_separate_effects"
            posture = "Retain separate current correction effects by source domain; do not merge their uncertainty, authority, or safety boundaries."
        elif "resolved_context" in active_types:
            consolidation_type = "partial_resolution"
            posture = "Later context narrows one recorded uncertainty, but unresolved safety or evidence limits remain clarify-only and non-executing."
        else:
            consolidation_type = "latest_supersedes_prior"
            posture = "The newest source-bound correction supersedes prior correction effects for this route; preserve historical results without recomputation."
    elif blocked:
        active = blocked
        consolidation_type = "blocked_persists"
        posture = "Retain the blocked safety boundary despite later descriptive or unsupported authority language; no contact, read, scan, status claim, or execution occurs."
    elif stable:
        active = stable
        consolidation_type = "stable_unaffected"
        posture = "The completed provisional lineage remains stable because no source-bound correction affects it; do not repeat the result, refinement, or selection."

    active_effects = [item["effect"] for item in active]
    obsolete_effects = [item["effect"] for item in obsolete]
    affected_frames = unique(
        [str(value) for effect in active_effects for value in effect.get("affected_frame_ids", ())]
    )
    if retraction is not None:
        affected_frames = unique((*affected_frames, str(retraction[1].get("frame_id") or "")))
    affected_routes = unique(
        [str(value) for effect in active_effects for value in effect.get("affected_route_ids", ())]
    )
    affected_results = unique(
        [str(value) for effect in (*active_effects, *obsolete_effects) for value in effect.get("affected_result_ids", ())]
    )
    affected_refinements = unique(
        [str(value) for effect in (*active_effects, *obsolete_effects) for value in effect.get("affected_refinement_ids", ())]
    )
    forbidden_actions = unique(
        [str(value) for effect in active_effects for value in effect.get("forbidden_actions", ())]
        + ["No automatic authority, execution, graph mutation, review, admission, scheduler, planner, or worker."]
    )
    active_ids = unique([str(effect.get("effect_id") or "") for effect in active_effects])
    obsolete_ids = unique([str(effect.get("effect_id") or "") for effect in obsolete_effects])
    return LongHorizonCorrectionEffectConsolidation(
        consolidation_id=stable_id(
            "long-horizon-correction-effect-consolidation",
            objective_id,
            consolidation_type,
            *active_ids,
            *obsolete_ids,
        ),
        objective_id=objective_id,
        active_correction_effect_ids=active_ids,
        obsolete_correction_effect_ids=obsolete_ids,
        affected_frame_ids=affected_frames,
        affected_route_ids=affected_routes,
        affected_result_ids=affected_results,
        affected_refinement_ids=affected_refinements,
        consolidation_type=consolidation_type,
        selected_nonexecuting_posture=posture,
        forbidden_actions=forbidden_actions,
        may_execute_now=False,
        status="deterministic_correction_effect_consolidation_only",
    )


def compile_adaptive_precondition_selection(
    *,
    objective_id: str,
    semantic_frames: Sequence[Mapping[str, Any]],
    arbitration: Mapping[str, Any] | None = None,
    correction_effect_consolidation: Mapping[str, Any] | None = None,
    evidence_requests: Sequence[Mapping[str, Any]] = (),
    evidence_authorizations: Sequence[Mapping[str, Any]] = (),
    evidence_next_operation_proposals: Sequence[Mapping[str, Any]] = (),
    evidence_execution_authorities: Sequence[Mapping[str, Any]] = (),
    evidence_fixture_execution_plans: Sequence[Mapping[str, Any]] = (),
    evidence_minimal_fixture_results: Sequence[Mapping[str, Any]] = (),
    analyses: Sequence[Mapping[str, Any]] = (),
) -> AdaptivePreconditionSelection | None:
    """Classify one objective-local route's existing prerequisite posture.

    This consumes only persisted records.  It cannot manufacture a request,
    authority, proposal, plan, result, or execution transition.
    """

    if not objective_id:
        return None

    def records(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [dict(item) for item in values if isinstance(item, Mapping)]

    def ids(values: Sequence[Mapping[str, Any]], field: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(str(item.get(field) or "") for item in values if str(item.get(field) or "")))

    frames = records(semantic_frames)
    routes = [
        _capability_route_candidate_from_frame(frame)
        for frame in frames
        if str(_capability_route_candidate_from_frame(frame).get("capability_route_candidate_id") or "")
    ]
    if not routes:
        return None
    requests = records(evidence_requests)
    authorizations = records(evidence_authorizations)
    proposals = records(evidence_next_operation_proposals)
    authorities = records(evidence_execution_authorities)
    plans = records(evidence_fixture_execution_plans)
    results = records(evidence_minimal_fixture_results)
    analysis_records = records(analyses)
    considered_route_ids = ids(routes, "capability_route_candidate_id")
    considered_authority_ids = ids(authorities, "evidence_execution_authority_id")
    considered_proposal_ids = ids(proposals, "evidence_next_operation_proposal_id")
    considered_plan_ids = ids(plans, "evidence_fixture_execution_plan_id")
    considered_result_ids = ids(results, "evidence_minimal_fixture_result_id")
    consolidation = dict(correction_effect_consolidation or {})
    consolidation_type = str(consolidation.get("consolidation_type") or "")
    active_effect_ids = tuple(str(item) for item in consolidation.get("active_correction_effect_ids", ()) if str(item))
    generic_forbidden = ("No automatic authority, execution, graph mutation, review, admission, scheduler, planner, or worker.",)

    def build(
        *,
        state: str,
        route: Mapping[str, Any] | None = None,
        effect_id: str = "",
        missing: str,
        posture: str,
        reason: str,
        extra_forbidden: Sequence[str] = (),
    ) -> AdaptivePreconditionSelection:
        route_forbidden = tuple(str(item) for item in (route or {}).get("forbidden_actions", ()) if str(item))
        forbidden = tuple(dict.fromkeys((*route_forbidden, *extra_forbidden, *generic_forbidden)))
        route_id = str((route or {}).get("capability_route_candidate_id") or "")
        selection_id = stable_id(
            "adaptive-precondition-selection",
            objective_id,
            state,
            route_id,
            effect_id,
            *considered_authority_ids,
            *considered_proposal_ids,
            *considered_plan_ids,
            *considered_result_ids,
        )
        return AdaptivePreconditionSelection(
            precondition_selection_id=selection_id,
            objective_id=objective_id,
            selected_route_id=route_id,
            selected_correction_effect_id=effect_id,
            considered_route_ids=considered_route_ids,
            considered_authority_ids=considered_authority_ids,
            considered_proposal_ids=considered_proposal_ids,
            considered_plan_ids=considered_plan_ids,
            considered_result_ids=considered_result_ids,
            precondition_state=state,
            missing_precondition=missing,
            selected_nonexecuting_posture=posture,
            priority_reason=reason,
            forbidden_actions=forbidden,
            may_execute_now=False,
            status="deterministic_precondition_selection_only",
        )

    blocked_route = next((route for route in routes if str(route.get("decision") or "") == "blocked"), None)
    if blocked_route is not None:
        return build(
            state="blocked_safety_boundary",
            route=blocked_route,
            missing="explicit accepted authority and a later bounded execution gate",
            posture="Retain the blocked safety boundary; do not contact, read, scan, inspect, pay, schedule, or execute.",
            reason="A blocked safety route outranks every correction, clarification, and eligible route.",
        )
    if consolidation_type == "latest_supersedes_prior" and consolidation.get("affected_result_ids"):
        return build(
            state="completed_stale_needs_new_authorized_cycle",
            effect_id=active_effect_ids[0] if active_effect_ids else "",
            missing="a new source-bound authority and accepted plan for any later controlled cycle",
            posture="The prior completed result is historical and stale. Preserve it without recomputation or duplicate selection.",
            reason="A current supersession effect affects an existing controlled result.",
            extra_forbidden=tuple(str(item) for item in consolidation.get("forbidden_actions", ()) if str(item)),
        )
    clarify_route = next((route for route in routes if str(route.get("decision") or "") == "clarify"), None)
    if clarify_route is not None:
        return build(
            state="clarify_needed",
            route=clarify_route,
            effect_id=active_effect_ids[0] if consolidation_type in {"partial_resolution", "compound_separate_effects"} and active_effect_ids else "",
            missing="source-bound clarification or unresolved safety context",
            posture="Keep the route clarify-only; do not diagnose, provide legal certainty, or execute evidence work.",
            reason="An unresolved clarification safety boundary outranks eligible and stable completed routes.",
        )

    analyses_by_frame: dict[str, list[dict[str, Any]]] = {}
    for analysis in analysis_records:
        frame_id = str(analysis.get("source_frame_id") or "")
        if frame_id:
            analyses_by_frame.setdefault(frame_id, []).append(analysis)
    results_by_analysis: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        analysis_id = str(result.get("source_analysis_id") or "")
        if analysis_id:
            results_by_analysis.setdefault(analysis_id, []).append(result)
    requests_by_frame: dict[str, list[dict[str, Any]]] = {}
    for request in requests:
        frame_id = str(request.get("source_frame_id") or "")
        if frame_id:
            requests_by_frame.setdefault(frame_id, []).append(request)
    authorizations_by_request: dict[str, list[dict[str, Any]]] = {}
    for authorization in authorizations:
        request_id = str(authorization.get("evidence_request_id") or authorization.get("source_evidence_request_id") or "")
        if request_id:
            authorizations_by_request.setdefault(request_id, []).append(authorization)
    proposals_by_frame: dict[str, list[dict[str, Any]]] = {}
    for proposal in proposals:
        frame_id = str(proposal.get("source_frame_id") or "")
        if frame_id:
            proposals_by_frame.setdefault(frame_id, []).append(proposal)
    authorities_by_proposal: dict[str, list[dict[str, Any]]] = {}
    for authority in authorities:
        proposal_id = str(authority.get("source_evidence_next_operation_proposal_id") or "")
        if proposal_id:
            authorities_by_proposal.setdefault(proposal_id, []).append(authority)
    plans_by_authority: dict[str, list[dict[str, Any]]] = {}
    for plan in plans:
        authority_id = str(plan.get("source_evidence_execution_authority_id") or "")
        if authority_id:
            plans_by_authority.setdefault(authority_id, []).append(plan)

    eligible_route = next((route for route in routes if str(route.get("decision") or "") == "eligible"), None)
    if eligible_route is None:
        return build(
            state="ordinary_no_selectable_route",
            missing="a source-bound eligible route",
            posture="No route has an actionable non-executing posture beyond the persisted safety records.",
            reason=str((arbitration or {}).get("priority_reason") or "No eligible source-bound route is present."),
        )
    source_frame_id = str(eligible_route.get("source_frame_id") or "")
    route_analyses = analyses_by_frame.get(source_frame_id, [])
    route_results = [result for analysis in route_analyses for result in results_by_analysis.get(str(analysis.get("analysis_id") or ""), [])]
    if route_results:
        return build(
            state="completed_stable",
            route=eligible_route,
            missing="",
            posture="The existing controlled result is stable and provisional; do not duplicate its result, refinement, or selection.",
            reason="A matching existing controlled result is present with no current stale correction effect.",
        )
    route_requests = requests_by_frame.get(source_frame_id, [])
    route_request_ids = {str(item.get("evidence_permission_request_id") or "") for item in route_requests}
    route_authorizations = [
        authorization
        for request_id in route_request_ids
        for authorization in authorizations_by_request.get(request_id, [])
    ]
    route_proposals = proposals_by_frame.get(source_frame_id, [])
    route_authorities = [
        authority
        for proposal in route_proposals
        for authority in authorities_by_proposal.get(str(proposal.get("evidence_next_operation_proposal_id") or ""), [])
    ]
    route_plans = [
        plan
        for authority in route_authorities
        for plan in plans_by_authority.get(str(authority.get("evidence_execution_authority_id") or ""), [])
    ]
    if route_plans:
        accepted = any(str(plan.get("status") or "") in {"accepted", "approved", "accepted_pending_execution_gate"} for plan in route_plans)
        if accepted:
            return build(
                state="accepted_plan_ready_nonexecuting",
                route=eligible_route,
                missing="a separate existing gated execution transition",
                posture="An accepted plan is present, but this selector remains record-only and does not invoke an evaluator.",
                reason="The route has an existing accepted plan and is ready only for its separately-governed path.",
            )
        return build(
            state="authority_exists_needs_plan_acceptance",
            route=eligible_route,
            missing="accepted_execution_plan",
            posture="Authority exists, but the plan remains unaccepted; do not execute or infer acceptance.",
            reason="An inert authority lineage exists without an accepted plan.",
        )
    if route_authorities:
        return build(
            state="authority_exists_needs_plan_acceptance",
            route=eligible_route,
            missing="accepted_execution_plan",
            posture="Authority exists but no accepted plan is recorded; do not create one automatically.",
            reason="The authority boundary is present but the next plan boundary is unresolved.",
        )
    if route_authorizations:
        return build(
            state="permission_granted_needs_proposal_or_authority",
            route=eligible_route,
            missing="bounded proposal and inert execution authority",
            posture="Permission is recorded, but no proposal or authority may be created by this selector.",
            reason="The permission lineage exists without the next explicit governance records.",
        )
    return build(
        state="eligible_needs_permission",
        route=eligible_route,
        missing="evidence permission and a later explicit authority chain",
        posture="The route is eligible only in principle; request creation and execution remain outside this selector.",
        reason="No matching evidence permission or authorization record exists for the eligible route.",
    )


def compile_adaptive_route_arbitration(
    *,
    objective_id: str,
    semantic_frames: Sequence[Mapping[str, Any]],
    correction_candidates: Sequence[Mapping[str, Any]] = (),
    correction_effects: Sequence[Mapping[str, Any]] = (),
    correction_effect_consolidation: Mapping[str, Any] | None = None,
) -> AdaptiveRouteArbitration | None:
    """Select one safe, non-executing posture from existing objective-local routes.

    This is intentionally a projection only. It does not create an authority,
    request, queue, task, or execution path. The caller owns persistence.
    """

    if not objective_id:
        return None
    routes: list[tuple[int, Mapping[str, Any]]] = []
    for index, frame in enumerate(semantic_frames):
        if not isinstance(frame, Mapping):
            continue
        candidate = _capability_route_candidate_from_frame(frame)
        route_id = str(candidate.get("capability_route_candidate_id") or "")
        if route_id:
            routes.append((index, candidate))
    if not routes:
        return None
    corrections = [dict(item) for item in correction_candidates if isinstance(item, Mapping)]
    effects = [dict(item) for item in correction_effects if isinstance(item, Mapping)]
    considered_route_ids = tuple(str(route.get("capability_route_candidate_id") or "") for _, route in routes)
    considered_correction_ids = tuple(
        str(item.get("correction_candidate_id") or "")
        for item in corrections
        if str(item.get("correction_candidate_id") or "")
    )
    completed_route_ids = {
        route_id
        for item in corrections
        if str(item.get("correction_type") or "") == "completed_positive_loop"
        for route_id in item.get("source_route_ids", ())
        if str(route_id)
    }
    stale_route_ids = {
        str(route_id)
        for effect in effects
        if str(effect.get("effect_type") or "") == "stale_suppression"
        for route_id in effect.get("affected_route_ids", ())
        if str(route_id)
    }

    def build(
        decision: str,
        *,
        route: Mapping[str, Any] | None = None,
        correction: Mapping[str, Any] | None = None,
        reason: str,
    ) -> AdaptiveRouteArbitration:
        selected_route_id = str((route or {}).get("capability_route_candidate_id") or "")
        selected_correction_id = str(
            (correction or {}).get("correction_candidate_id")
            or (correction or {}).get("consolidation_id")
            or ""
        )
        selected_correction_effect_id = str((correction or {}).get("effect_id") or "")
        if not selected_correction_effect_id and isinstance(correction, Mapping):
            selected_correction_effect_id = str(
                next(iter(correction.get("active_correction_effect_ids", ())), "")
            )
        forbidden = tuple(
            dict.fromkeys(
                str(item)
                for item in (
                    *(route or {}).get("forbidden_actions", ()),
                    *(correction or {}).get("forbidden_actions", ()),
                    "No automatic authority, execution, graph mutation, review, admission, scheduler, planner, or worker.",
                )
                if str(item)
            )
        )
        arbitration_id = stable_id(
            "adaptive-route-arbitration",
            objective_id,
            decision,
            selected_route_id,
            selected_correction_id,
            selected_correction_effect_id,
            *considered_route_ids,
            *considered_correction_ids,
        )
        return AdaptiveRouteArbitration(
            arbitration_id=arbitration_id,
            objective_id=objective_id,
            decision=decision,
            selected_route_id=selected_route_id,
            selected_correction_id=selected_correction_id,
            selected_correction_effect_id=selected_correction_effect_id,
            considered_route_ids=considered_route_ids,
            considered_correction_ids=considered_correction_ids,
            priority_reason=reason,
            forbidden_actions=forbidden,
            requires_existing_authority=bool((route or {}).get("required_authority_if_any")) and decision == "eligible",
            may_execute_now=False,
            status="deterministic_route_arbitration_only",
        )

    for _, route in routes:
        if str(route.get("decision") or "") == "blocked":
            return build(
                "blocked",
                route=route,
                reason="A source-bound blocked safety boundary outranks every clarify, eligible, and completed route.",
            )
    malformed = next(
        (item for item in corrections if str(item.get("correction_type") or "") == "malformed_to_fail_closed"),
        None,
    )
    if malformed is not None:
        return build(
            "blocked",
            correction=malformed,
            reason="A malformed controlled input remains fail-closed and outranks clarify, eligible, and completed routes.",
        )
    consolidation = dict(correction_effect_consolidation or {})
    consolidation_type = str(consolidation.get("consolidation_type") or "")
    active_effect_ids = tuple(
        str(item) for item in consolidation.get("active_correction_effect_ids", ()) if str(item)
    )
    if consolidation_type == "retraction_restores_stable":
        return build(
            "completed",
            correction=consolidation,
            reason="The consolidated correction posture preserves the current completed lineage without rerunning it.",
        )
    if consolidation_type in {"compound_separate_effects", "partial_resolution"}:
        clarify_route = next(
            (route for _, route in routes if str(route.get("decision") or "") == "clarify"),
            None,
        )
        if clarify_route is not None:
            return build(
                "clarify",
                route=clarify_route,
                correction=consolidation,
                reason="A consolidated multi-effect posture retains the source-bound clarification safety boundary.",
            )
    if active_effect_ids and consolidation_type != "stable_unaffected":
        return build(
            "clarify",
            correction=consolidation,
            reason="The consolidated current correction effect changes the posture without authorizing recomputation or execution.",
        )
    correction_effect = next(
        (
            item
            for item in effects
            if str(item.get("effect_type") or "") in {"stale_suppression", "resolved_context"}
        ),
        None,
    )
    if correction_effect is not None:
        return build(
            "clarify",
            correction=correction_effect,
            reason=(
                "A later source-bound correction changes the current posture; stale completed lineage is suppressed "
                "until the existing authority path is explicitly revisited."
            ),
        )
    for _, route in routes:
        if str(route.get("decision") or "") == "clarify":
            return build(
                "clarify",
                route=route,
                reason="An unresolved source-bound safety or context clarification outranks any eligible controlled route.",
            )
    for _, route in routes:
        route_id = str(route.get("capability_route_candidate_id") or "")
        if (
            str(route.get("decision") or "") == "eligible"
            and route_id not in completed_route_ids
            and route_id not in stale_route_ids
        ):
            return build(
                "eligible",
                route=route,
                reason="No blocked or clarify posture remains; the first persisted eligible route is the stable non-executing next posture.",
            )
    completed = next(
        (item for item in corrections if str(item.get("correction_type") or "") == "completed_positive_loop"),
        None,
    )
    if completed is not None:
        return build(
            "completed",
            correction=completed,
            reason="All remaining eligible routes already have stable completed-loop evidence, so no new controlled work is selected.",
        )
    return build(
        "ordinary_none",
        reason="No route requires a new posture beyond the existing source-bound records.",
    )


def _semantic_input_frame(record: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = record.get("semantic_input_frame")
    return candidate if isinstance(candidate, Mapping) else record


def _capability_route_candidate_from_frame(record: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = record.get("capability_route_candidate")
    return candidate if isinstance(candidate, Mapping) else {}


def _has_material_context_resolution(source_text: str) -> bool:
    return bool(re.search(
        r"\b(?:now\s+(?:know|known)|confirmed|identified|error\s+is|owner\s+is|no\s+fever|not\s+spreading)\b",
        source_text,
        flags=re.IGNORECASE,
    ))


def _frictionless_incline_angle(frame: Mapping[str, Any]) -> float | None:
    if str(frame.get("domain_guess") or "") != "physics_mechanics":
        return None
    source_text = str(frame.get("source_text") or "")
    if "frictionless" not in source_text.lower() and "without friction" not in source_text.lower():
        return None
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*[-\s]*(?:degrees?|degree)\b", source_text, flags=re.IGNORECASE)
    if match is None:
        return None
    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return None


def _portfolio_allocation_signature(frame: Mapping[str, Any]) -> tuple[float, float, float] | None:
    if str(frame.get("domain_guess") or "") != "finance_portfolio_risk":
        return None
    source_text = str(frame.get("source_text") or "")
    lowered = source_text.lower()
    if not all(marker in lowered for marker in ("tech", "cash", "small")):
        return None
    values = re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*%", source_text)
    if len(values) < 3:
        return None
    try:
        allocation = tuple(float(value) for value in values[:3])
    except ValueError:
        return None
    if not math.isclose(sum(allocation), 100.0):
        return None
    return allocation


def _self_correction_candidate(
    *,
    objective_id: str,
    correction_type: str,
    source_frame_ids: tuple[str, ...],
    source_route_ids: tuple[str, ...],
    reason: str,
    prior_state: str,
    current_state: str,
    posture: str,
    forbidden_actions: tuple[str, ...],
    may_route_next: bool,
    source_result_ids: tuple[str, ...] = (),
    source_plan_ids: tuple[str, ...] = (),
) -> LongHorizonSelfCorrectionCandidate:
    correction_id = stable_id(
        "objective-local-self-correction",
        objective_id,
        correction_type,
        *source_frame_ids,
        *source_route_ids,
        *source_result_ids,
        *source_plan_ids,
    )
    return LongHorizonSelfCorrectionCandidate(
        correction_candidate_id=correction_id,
        objective_id=objective_id,
        correction_type=correction_type,
        source_frame_ids=source_frame_ids,
        source_route_ids=source_route_ids,
        source_result_ids=source_result_ids,
        source_plan_ids=source_plan_ids,
        reason=reason,
        prior_state=prior_state,
        corrected_or_current_state=current_state,
        recommended_nonexecuting_posture=posture,
        forbidden_actions=tuple(dict.fromkeys(forbidden_actions)),
        may_route_next=may_route_next,
        may_execute_now=False,
        status="deterministic_correction_candidate_only",
    )


def _malformed_fixture_rejection_correction(
    *,
    objective_id: str,
    plan: Mapping[str, Any],
    source_analysis: Mapping[str, Any],
) -> LongHorizonSelfCorrectionCandidate | None:
    domain = str(source_analysis.get("domain") or "")
    accepted = str(plan.get("status") or "") in {"accepted_pending_execution_gate", "accepted", "approved"}
    if not accepted or domain not in {"finance_portfolio_risk", "physics_mechanics"}:
        return None
    source_text = str(source_analysis.get("source_text") or "")
    malformed = (
        domain == "finance_portfolio_risk" and _minimal_portfolio_fixture(source_analysis) is None
    ) or (
        domain == "physics_mechanics" and _minimal_frictionless_thirty_degree_incline_fixture(source_analysis) is None
    )
    if not malformed:
        return None
    frame_id = str(source_analysis.get("source_frame_id") or "")
    plan_id = str(plan.get("evidence_fixture_execution_plan_id") or "")
    if not frame_id or not plan_id or not source_text:
        return None
    return _self_correction_candidate(
        objective_id=objective_id,
        correction_type="malformed_to_fail_closed",
        source_frame_ids=(frame_id,),
        source_route_ids=(),
        source_plan_ids=(plan_id,),
        reason="An accepted-looking controlled plan has malformed or internally inconsistent source-bound inputs, so the evaluator must reject it without fallback data.",
        prior_state="accepted-looking plan with incomplete or inconsistent source inputs",
        current_state="fail-closed evaluator rejection; no fixture result, refinement, posture update, or selection",
        posture="Preserve the rejection reason and request corrected source-bound input through an existing clarification path; do not infer replacement values or execute.",
        forbidden_actions=(
            "No fallback data, inferred weights, calculation, fixture result, refinement, posture update, or selection.",
            "No graph truth mutation, review, admission, external action, model, provider, tool, network, filesystem, sandbox, worker, scheduler, or planner.",
        ),
        may_route_next=True,
    )


def _minimal_portfolio_fixture(source_analysis: Mapping[str, Any]) -> Mapping[str, tuple[float, ...]] | None:
    """Return static fixture inputs only for a complete three-sleeve source record."""

    source_text = str(source_analysis.get("source_text") or "")
    weights = tuple(float(item) / 100.0 for item in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*%", source_text))
    if len(weights) < 3:
        return None
    selected_weights = weights[:3]
    if not math.isclose(sum(selected_weights), 1.0, rel_tol=0.0, abs_tol=0.001):
        return None
    return {
        "weights": selected_weights,
        "stress_values": (-0.15, 0.0, -0.08),
    }


def _compile_frictionless_incline_fixture_result(
    plan: Mapping[str, Any],
    *,
    objective_id: str,
    source_analysis: Mapping[str, Any],
    source_revision_candidate: Mapping[str, Any] | None,
    source_internal_work_candidate: Mapping[str, Any] | None,
) -> tuple[EvidenceMinimalFixtureResult, ...]:
    """Compile the one source-bound frictionless 30-degree incline result."""

    if str(plan.get("evidence_source_class") or "") != "deterministic_physics_incline_plan_only":
        return ()
    if str(plan.get("proposed_operation_type") or "") != "physics_frictionless_incline_calculation_proposal_only":
        return ()
    if str(source_analysis.get("domain") or "") != "physics_mechanics":
        return ()
    fixture = _minimal_frictionless_thirty_degree_incline_fixture(source_analysis)
    if fixture is None:
        return ()

    revision_candidate = dict(source_revision_candidate or {})
    revision_id = str(revision_candidate.get("evidence_analysis_revision_candidate_id") or "")
    source_analysis_id = str(source_analysis.get("analysis_id") or "")
    if revision_candidate and str(revision_candidate.get("source_analysis_id") or "") != source_analysis_id:
        return ()
    internal_candidate = dict(source_internal_work_candidate or {})
    internal_id = str(internal_candidate.get("internal_work_candidate_id") or "")
    if internal_candidate and revision_id and str(internal_candidate.get("source_evidence_analysis_revision_candidate_id") or "") != revision_id:
        return ()

    plan_id = str(plan.get("evidence_fixture_execution_plan_id") or "")
    authority_id = str(plan.get("source_evidence_execution_authority_id") or "")
    proposal_id = str(plan.get("source_evidence_next_operation_proposal_id") or "")
    evidence_request_id = str(plan.get("source_evidence_request_id") or "")
    evidence_authorization_id = str(plan.get("source_evidence_authorization_id") or "")
    if not all((objective_id, plan_id, authority_id, proposal_id, evidence_request_id, evidence_authorization_id, source_analysis_id)):
        return ()

    input_payload = {
        "plan_id": plan_id,
        "objective_id": objective_id,
        "source_analysis_id": source_analysis_id,
        "source_revision_candidate_id": revision_id,
        "source_internal_work_candidate_id": internal_id,
        "angle_degrees": fixture["angle_degrees"],
        "gravity_m_per_s2": fixture["gravity_m_per_s2"],
        "frictionless": True,
    }
    input_digest = _canonical_digest(input_payload)
    result_id = stable_id(
        "analysis-evidence-minimal-fixture-result",
        objective_id,
        plan_id,
        source_analysis_id,
        revision_id,
        internal_id,
        input_digest,
    )
    return (
        EvidenceMinimalFixtureResult(
            evidence_minimal_fixture_result_id=result_id,
            source_plan_id=plan_id,
            source_execution_authority_id=authority_id,
            source_proposal_id=proposal_id,
            source_evidence_request_id=evidence_request_id,
            source_evidence_authorization_id=evidence_authorization_id,
            source_analysis_id=source_analysis_id,
            source_evidence_analysis_revision_candidate_id=revision_id,
            source_internal_work_candidate_id=internal_id,
            objective_id=objective_id,
            fixture_kind="in_memory_frictionless_thirty_degree_incline_calculation",
            deterministic_input_digest=input_digest,
            deterministic_input_summary="Recorded frictionless incline angle: 30 degrees. Fixed local gravity constant: g=9.8 m/s^2.",
            deterministic_output="Using a = g * sin(30 degrees), the deterministic frictionless-incline acceleration is 4.9 m/s^2 down the plane. This is an idealized calculation, not an experimental measurement.",
            limitations=(
                "The calculation applies only to the recorded frictionless 30-degree incline.",
                "The fixed g=9.8 m/s^2 constant is a local deterministic convention rather than an observed measurement.",
                "No friction, air resistance, experimental uncertainty, or external source is represented.",
                "A separate controlled analysis-refinement transition is required before this result can affect objective-local posture.",
            ),
            blocked_actions=_controlled_fixture_blocked_actions(),
            proof_summary="Computed only from the recorded frictionless 30-degree constraint and fixed in-memory g=9.8 m/s^2; no external source, filesystem, model, provider, tool, sandbox, graph, review, admission, or worker was used.",
            may_update_analysis=False,
            may_update_problem_state=False,
            may_update_graph=False,
            requires_analysis_refinement_gate=True,
            status="minimal_fixture_completed",
            created_event_id=stable_id("analysis-evidence-minimal-fixture-result-event", result_id),
            restart_summary="The bounded physics fixture result persists exactly once from an accepted plan and recorded source analysis; it remains provisional until the controlled existing-refinement transition records its local effect.",
        ),
    )


def _minimal_frictionless_thirty_degree_incline_fixture(source_analysis: Mapping[str, Any]) -> Mapping[str, float] | None:
    source_text = str(source_analysis.get("source_text") or "")
    lower = source_text.lower()
    if "frictionless" not in lower:
        return None
    if re.search(r"\bfriction\b", lower.replace("frictionless", "")):
        return None
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:[-\s]*(?:degrees?|degree)|°)\b", lower)
    if match is None:
        return None
    try:
        angle_degrees = float(match.group(1))
    except (TypeError, ValueError):
        return None
    if not math.isclose(angle_degrees, 30.0, rel_tol=0.0, abs_tol=0.001):
        return None
    return {"angle_degrees": angle_degrees, "gravity_m_per_s2": 9.8}


def _controlled_fixture_blocked_actions() -> tuple[str, ...]:
    return (
        "No repository file read.",
        "No local filesystem read.",
        "No network or external source lookup.",
        "No model, provider, or tool call.",
        "No sandbox command execution.",
        "No source mutation.",
        "No graph truth mutation, review, admission, answer finalization, worker, scheduler, or external action.",
    )


def render_evidence_minimal_fixture_result(result: Mapping[str, Any]) -> str:
    """Render the bounded fixture result without overstating its authority."""

    limitations = tuple(str(item) for item in result.get("limitations", ()) if str(item))
    return "\n".join(
        (
            "Controlled in-memory fixture result recorded.",
            f"Fixture result: {str(result.get('evidence_minimal_fixture_result_id') or '')}",
            f"Source plan: {str(result.get('source_plan_id') or '')}",
            f"Fixture: {str(result.get('fixture_kind') or '').replace('_', ' ')}",
            f"Inputs: {str(result.get('deterministic_input_summary') or '')}",
            f"Result: {str(result.get('deterministic_output') or '')}",
            "Limits: " + ("; ".join(limitations) if limitations else "Fixture-only result."),
            f"Proof: {str(result.get('proof_summary') or '')}",
            "Status: provisional fixture result only. It has not changed graph truth, review, admission, an answer, or any external system.",
        )
    )


def compile_controlled_fixture_analysis_refinement(
    analysis: Mapping[str, Any],
    fixture_result: Mapping[str, Any],
    *,
    source_evidence_request: Mapping[str, Any],
) -> AnalysisRefinement | None:
    """Reuse the canonical append-only refinement record for one fixture result."""

    source_analysis_id = str(analysis.get("analysis_id") or "")
    fixture_result_id = str(fixture_result.get("evidence_minimal_fixture_result_id") or "")
    evidence_request_id = str(source_evidence_request.get("evidence_permission_request_id") or source_evidence_request.get("evidence_request_id") or "")
    if not source_analysis_id or not fixture_result_id or not evidence_request_id:
        return None
    if str(fixture_result.get("source_analysis_id") or "") != source_analysis_id:
        return None
    if str(fixture_result.get("status") or "") != "minimal_fixture_completed":
        return None
    if bool(fixture_result.get("may_update_analysis")) or bool(fixture_result.get("may_update_problem_state")) or bool(fixture_result.get("may_update_graph")):
        return None
    if not bool(fixture_result.get("requires_analysis_refinement_gate")):
        return None
    if str(source_evidence_request.get("source_analysis_id") or "") != source_analysis_id:
        return None

    source_question_id = str(source_evidence_request.get("source_question_candidate_id") or evidence_request_id)
    source_answer_id = str(source_evidence_request.get("source_question_answer_id") or "")
    binding_key = "|".join(("controlled_fixture", evidence_request_id, fixture_result_id))
    before_summary = str(analysis.get("result_summary") or "The source-bound analysis remains available.")
    fixture_output = str(fixture_result.get("deterministic_output") or "")
    fixture_kind = str(fixture_result.get("fixture_kind") or "")
    is_physics_fixture = fixture_kind == "in_memory_frictionless_thirty_degree_incline_calculation"
    after_summary = (
        f"{before_summary} Controlled fixture addition: {fixture_output} "
        + (
            "The result remains limited to the recorded frictionless 30-degree idealization."
            if is_physics_fixture
            else "The live-data and correlation gap remains unresolved, so this only sharpens the stated hypothetical scenario."
        )
    )
    remaining_uncertainty = tuple(
        dict.fromkeys(
            (
                *(str(item) for item in analysis.get("uncertainty", ()) if str(item)),
                *(str(item) for item in fixture_result.get("limitations", ()) if str(item)),
            )
        )
    )
    safe_next_actions = tuple(
        dict.fromkeys(
            (
                *(str(item.get("action") or "") for item in analysis.get("safe_next_actions", ()) if isinstance(item, Mapping) and str(item.get("action") or "")),
                (
                    "Keep the frictionless 30-degree idealization explicit; do not treat the calculation as an experimental measurement."
                    if is_physics_fixture
                    else "Keep the live-data and correlation uncertainty open; use the fixture only as a bounded hypothetical comparison."
                ),
            )
        )
    )
    prohibited_actions = tuple(
        dict.fromkeys(
            (
                *(str(item) for item in analysis.get("prohibited_actions", ()) if str(item)),
                *(str(item) for item in fixture_result.get("blocked_actions", ()) if str(item)),
                (
                    "Do not treat this fixture output as an experimental measurement or apply it to frictional motion."
                    if is_physics_fixture
                    else "Do not treat this fixture output as current market evidence, a forecast, investment advice, or a trade instruction."
                ),
            )
        )
    )
    refinement_id = stable_id("evidence-bound-analysis-refinement", source_analysis_id, fixture_result_id)
    return AnalysisRefinement(
        refinement_id=refinement_id,
        source_analysis_id=source_analysis_id,
        source_frame_id=str(analysis.get("source_frame_id") or ""),
        source_question_id=source_question_id,
        source_answer_id=source_answer_id,
        question_binding_key=binding_key,
        changed_unknown_slots=(
            "physics.frictionless_thirty_degree_calculation"
            if is_physics_fixture
            else "finance.hypothetical_fixture_scenario",
        ),
        before_summary=before_summary,
        after_summary=after_summary,
        changed_fields=(
            ("controlled_fixture_result", "frictionless_incline_calculation")
            if is_physics_fixture
            else ("controlled_fixture_result", "hypothetical_drawdown_check")
        ),
        remaining_uncertainty=remaining_uncertainty,
        safe_next_actions=safe_next_actions,
        prohibited_actions=prohibited_actions,
        status="controlled_fixture_refinement",
        created_event_id=stable_id("evidence-bound-analysis-refinement-event", refinement_id),
        restart_summary=(
            "Append-only source-bound refinement created from one bounded in-memory fixture result; "
            "the original analysis remains intact and graph truth, review, admission, answer finalization, and external action remain unchanged."
        ),
        source_evidence_minimal_fixture_result_id=fixture_result_id,
        source_evidence_analysis_revision_candidate_id=str(
            fixture_result.get("source_evidence_analysis_revision_candidate_id") or ""
        ),
    )


def render_controlled_fixture_analysis_refinement(refinement: Mapping[str, Any]) -> str:
    """Render the result-driven refinement distinctly from an operator answer."""

    uncertainty = tuple(str(item) for item in refinement.get("remaining_uncertainty", ()) if str(item))
    return "\n".join(
        (
            "I appended the controlled fixture result to the existing source-bound analysis.",
            f"What changed: {str(refinement.get('after_summary') or '')}",
            "Still uncertain: " + ("; ".join(uncertainty) if uncertainty else "No additional uncertainty was recorded."),
            "Status: provisional, append-only refinement. The original analysis remains preserved; this did not create graph truth, review, admission, a final answer, or external action.",
        )
    )


def compile_evidence_result_ingestion_candidates(
    dry_run_result: Mapping[str, Any],
    *,
    objective_id: str,
    source_evidence_request: Mapping[str, Any] | None = None,
) -> tuple[EvidenceResultIngestionCandidate, ...]:
    """Compile one non-mutating ingestion candidate from a dry-run boundary result."""

    dry_run_id = str(dry_run_result.get("evidence_fixture_dry_run_result_id") or "")
    plan_id = str(dry_run_result.get("source_plan_id") or "")
    authority_id = str(dry_run_result.get("source_execution_authority_id") or "")
    proposal_id = str(dry_run_result.get("source_proposal_id") or "")
    evidence_request_id = str(dry_run_result.get("source_evidence_request_id") or "")
    evidence_authorization_id = str(dry_run_result.get("source_evidence_authorization_id") or "")
    if not objective_id or not dry_run_id or not plan_id or not authority_id or not proposal_id or not evidence_request_id or not evidence_authorization_id:
        return ()
    if str(dry_run_result.get("status") or "") not in {"recorded", "completed", "dry_run_completed", "blocked_boundary_result", "synthetic_boundary_result"}:
        return ()
    if bool(dry_run_result.get("may_update_analysis")) or bool(dry_run_result.get("may_update_graph")):
        return ()
    if not bool(dry_run_result.get("requires_result_ingestion_gate")):
        return ()

    source_request = dict(source_evidence_request or {})
    if source_request and str(source_request.get("evidence_permission_request_id") or source_request.get("evidence_request_id") or "") != evidence_request_id:
        return ()
    source_analysis_id = str(source_request.get("source_analysis_id") or "")
    fixture_kind = str(dry_run_result.get("fixture_kind") or "")
    effect_type = _ingestion_candidate_effect_type(fixture_kind)
    candidate_id = stable_id("analysis-evidence-result-ingestion-candidate", objective_id, dry_run_id, effect_type, source_analysis_id)
    status = "candidate" if source_analysis_id else "analysis_binding_required"
    blocked_scope = tuple(
        dict.fromkeys(
            (
                "analysis_update",
                "analysis_refinement",
                "problem_state_update",
                "graph_update",
                "review_admission",
                "replanning",
                "objective_completion_claim",
                "evidence_truth_claim",
                "file_read",
                "repo_read",
                "network",
                "tool",
                "model",
                "provider",
                "sandbox",
                "source_mutation",
            )
        )
    )
    return (
        EvidenceResultIngestionCandidate(
            evidence_result_ingestion_candidate_id=candidate_id,
            source_dry_run_result_id=dry_run_id,
            source_plan_id=plan_id,
            source_execution_authority_id=authority_id,
            source_proposal_id=proposal_id,
            source_evidence_request_id=evidence_request_id,
            source_evidence_authorization_id=evidence_authorization_id,
            source_analysis_id=source_analysis_id,
            objective_id=objective_id,
            candidate_effect_type=effect_type,
            supported_update_scope=(
                "later_analysis_revision_candidate",
                "operator_reviewable_evidence_posture",
            ),
            blocked_update_scope=blocked_scope,
            confidence_basis=(
                "Deterministic classifier over the dry-run result boundary only; "
                "the dry-run is synthetic and records blocked evidence activity, not external evidence."
            ),
            limitations=tuple(
                dict.fromkeys(
                    (
                        *(str(item) for item in dry_run_result.get("limitations", ()) if str(item)),
                        "This candidate does not revise analysis.",
                        "This candidate does not update graph truth.",
                        "This candidate does not prove evidence was gathered.",
                    )
                )
            ),
            required_operator_authority_next=(
                "A later explicit analysis-revision gate is required before this candidate can affect any analysis, problem state, graph, review, admission, or plan."
            ),
            may_update_analysis=False,
            may_update_problem_state=False,
            may_update_graph=False,
            requires_analysis_revision_gate=True,
            status=status,
            created_event_id=stable_id("analysis-evidence-result-ingestion-candidate-event", candidate_id),
            restart_summary=(
                "Evidence result ingestion candidate persists exactly once from a dry-run boundary result; "
                "analysis mutation, graph mutation, review, admission, and replanning remain deferred."
            ),
        ),
    )


def _ingestion_candidate_effect_type(fixture_kind: str) -> str:
    if fixture_kind == "synthetic_market_context_blocked":
        return "evidence_gap_remains_lookup_blocked"
    if fixture_kind == "synthetic_owned_fixture_inspection_blocked":
        return "evidence_gap_remains_file_read_blocked"
    if fixture_kind == "synthetic_operational_status_blocked":
        return "evidence_gap_remains_external_contact_blocked"
    return "dry_run_boundary_observed"


def render_evidence_result_ingestion_candidate(candidate: Mapping[str, Any]) -> str:
    """Render one inert result-ingestion candidate."""

    supported = tuple(str(item) for item in candidate.get("supported_update_scope", ()) if str(item))
    blocked = tuple(str(item) for item in candidate.get("blocked_update_scope", ()) if str(item))
    limitations = tuple(str(item) for item in candidate.get("limitations", ()) if str(item))
    return "\n".join(
        (
            "Evidence result ingestion candidate recorded.",
            f"Candidate: {str(candidate.get('evidence_result_ingestion_candidate_id') or '')}",
            f"Source dry-run result: {str(candidate.get('source_dry_run_result_id') or '')}",
            f"Effect type: {str(candidate.get('candidate_effect_type') or '').replace('_', ' ')}",
            "Supported later scope: " + ("; ".join(supported) if supported else "Later operator-reviewable analysis revision only."),
            "Blocked now: " + ("; ".join(blocked) if blocked else "No analysis, problem, graph, review, admission, or replan mutation."),
            "Limitations: " + ("; ".join(limitations) if limitations else "Dry-run is synthetic boundary material only."),
            f"Next authority required: {str(candidate.get('required_operator_authority_next') or '')}",
            "Candidate boundary: may_update_analysis=false; may_update_problem_state=false; may_update_graph=false; requires_analysis_revision_gate=true.",
        )
    )


def compile_evidence_analysis_revision_candidates(
    ingestion_candidate: Mapping[str, Any],
    *,
    objective_id: str,
) -> tuple[EvidenceAnalysisRevisionCandidate, ...]:
    """Compile one non-mutating analysis-revision candidate from ingestion state."""

    ingestion_id = str(ingestion_candidate.get("evidence_result_ingestion_candidate_id") or "")
    dry_run_id = str(ingestion_candidate.get("source_dry_run_result_id") or "")
    plan_id = str(ingestion_candidate.get("source_plan_id") or "")
    authority_id = str(ingestion_candidate.get("source_execution_authority_id") or "")
    proposal_id = str(ingestion_candidate.get("source_proposal_id") or "")
    evidence_request_id = str(ingestion_candidate.get("source_evidence_request_id") or "")
    evidence_authorization_id = str(ingestion_candidate.get("source_evidence_authorization_id") or "")
    if not objective_id or not ingestion_id or not dry_run_id or not plan_id or not authority_id or not proposal_id or not evidence_request_id or not evidence_authorization_id:
        return ()
    if bool(ingestion_candidate.get("may_update_analysis")):
        return ()
    if bool(ingestion_candidate.get("may_append_refinement")):
        return ()
    if bool(ingestion_candidate.get("may_update_problem_state")):
        return ()
    if bool(ingestion_candidate.get("may_change_answer")):
        return ()
    if bool(ingestion_candidate.get("may_update_graph")):
        return ()
    if not bool(ingestion_candidate.get("requires_analysis_revision_gate")):
        return ()

    source_analysis_id = str(ingestion_candidate.get("source_analysis_id") or "")
    effect_type = str(ingestion_candidate.get("candidate_effect_type") or "")
    proposed_revision_type = _analysis_revision_candidate_type(effect_type)
    candidate_id = stable_id("analysis-evidence-analysis-revision-candidate", objective_id, ingestion_id, proposed_revision_type, source_analysis_id)
    status = "candidate" if source_analysis_id else "analysis_binding_required"
    blocked_change = tuple(
        dict.fromkeys(
            (
                "analysis_update",
                "analysis_refinement_append",
                "problem_state_update",
                "answer_change",
                "graph_update",
                "review_admission",
                "replanning",
                "objective_completion_claim",
                "evidence_truth_claim",
                "file_read",
                "repo_read",
                "network",
                "tool",
                "model",
                "provider",
                "sandbox",
                "source_mutation",
            )
        )
    )
    return (
        EvidenceAnalysisRevisionCandidate(
            evidence_analysis_revision_candidate_id=candidate_id,
            source_ingestion_candidate_id=ingestion_id,
            source_dry_run_result_id=dry_run_id,
            source_plan_id=plan_id,
            source_execution_authority_id=authority_id,
            source_proposal_id=proposal_id,
            source_evidence_request_id=evidence_request_id,
            source_evidence_authorization_id=evidence_authorization_id,
            source_analysis_id=source_analysis_id,
            objective_id=objective_id,
            proposed_revision_type=proposed_revision_type,
            proposed_revision_scope=_analysis_revision_scope(proposed_revision_type),
            candidate_basis=(
                "Deterministic classifier over an inert evidence-result ingestion candidate. "
                "The source candidate records a dry-run boundary only, not external evidence or an operator answer."
            ),
            supported_change=(
                "later_operator_reviewable_analysis_revision_candidate",
                "later_note_about_unresolved_evidence_boundary",
            ),
            blocked_change=blocked_change,
            limitation_summary=tuple(
                dict.fromkeys(
                    (
                        *(str(item) for item in ingestion_candidate.get("limitations", ()) if str(item)),
                        "Synthetic or blocked dry-run material cannot revise analysis in this gate.",
                        "This candidate does not append an AnalysisRefinement.",
                        "This candidate does not change answers, problem state, graph truth, review, admission, or replanning.",
                    )
                )
            ),
            required_operator_authority_next=(
                "A later explicit analysis-revision approval gate is required before appending a refinement or changing analysis-facing state."
            ),
            may_append_refinement=False,
            may_update_analysis=False,
            may_update_problem_state=False,
            may_change_answer=False,
            may_update_graph=False,
            requires_analysis_revision_gate=True,
            status=status,
            created_event_id=stable_id("analysis-evidence-analysis-revision-candidate-event", candidate_id),
            restart_summary=(
                "Evidence analysis revision candidate persists exactly once from an ingestion candidate; "
                "refinement append, analysis mutation, answer change, graph mutation, review, admission, and replanning remain deferred."
            ),
        ),
    )


def _analysis_revision_candidate_type(effect_type: str) -> str:
    if effect_type == "evidence_gap_remains_lookup_blocked":
        return "note_lookup_still_blocked"
    if effect_type == "evidence_gap_remains_file_read_blocked":
        return "note_file_read_still_blocked"
    if effect_type == "evidence_gap_remains_external_contact_blocked":
        return "note_external_contact_still_blocked"
    return "note_dry_run_boundary_only"


def _analysis_revision_scope(revision_type: str) -> str:
    if revision_type == "note_lookup_still_blocked":
        return "A later revision may note that live lookup/correlation evidence remains unavailable and analysis should remain hypothetical."
    if revision_type == "note_file_read_still_blocked":
        return "A later revision may note that file or fixture inspection was not performed and security analysis remains unverified."
    if revision_type == "note_external_contact_still_blocked":
        return "A later revision may note that external contact or status verification was not performed and operational status remains unresolved."
    return "A later revision may note that the dry-run was boundary-only and does not change analysis content."


def render_evidence_analysis_revision_candidate(candidate: Mapping[str, Any]) -> str:
    """Render one inert analysis-revision candidate."""

    supported = tuple(str(item) for item in candidate.get("supported_change", ()) if str(item))
    blocked = tuple(str(item) for item in candidate.get("blocked_change", ()) if str(item))
    limitations = tuple(str(item) for item in candidate.get("limitation_summary", ()) if str(item))
    return "\n".join(
        (
            "Evidence analysis revision candidate recorded.",
            f"Candidate: {str(candidate.get('evidence_analysis_revision_candidate_id') or '')}",
            f"Source ingestion candidate: {str(candidate.get('source_ingestion_candidate_id') or '')}",
            f"Proposed revision type: {str(candidate.get('proposed_revision_type') or '').replace('_', ' ')}",
            f"Proposed revision scope: {str(candidate.get('proposed_revision_scope') or '')}",
            "Supported later change: " + ("; ".join(supported) if supported else "Later operator-reviewable analysis revision candidate only."),
            "Blocked now: " + ("; ".join(blocked) if blocked else "No refinement, analysis, answer, problem, graph, review, admission, or replan mutation."),
            "Limitations: " + ("; ".join(limitations) if limitations else "Candidate is inert boundary material only."),
            f"Next authority required: {str(candidate.get('required_operator_authority_next') or '')}",
            "Candidate boundary: may_append_refinement=false; may_update_analysis=false; may_update_problem_state=false; may_change_answer=false; may_update_graph=false; requires_analysis_revision_gate=true.",
        )
    )


def compile_analysis_revision_internal_work_candidates(
    revision_candidate: Mapping[str, Any],
    *,
    objective_id: str,
    source_evidence_request: Mapping[str, Any] | None = None,
) -> tuple[InternalWorkCandidate, ...]:
    """Adapt an inert revision candidate into the existing internal-work shape."""

    revision_id = str(revision_candidate.get("evidence_analysis_revision_candidate_id") or "")
    source_analysis_id = str(revision_candidate.get("source_analysis_id") or "")
    source_request = dict(source_evidence_request or {})
    source_frame_id = str(source_request.get("source_frame_id") or "")
    domain = str(source_request.get("domain") or "")
    proposed_revision_type = str(revision_candidate.get("proposed_revision_type") or "")
    if not objective_id or not revision_id or not source_analysis_id or not proposed_revision_type:
        return ()
    if bool(revision_candidate.get("may_append_refinement")):
        return ()
    if bool(revision_candidate.get("may_update_analysis")):
        return ()
    if bool(revision_candidate.get("may_update_problem_state")):
        return ()
    if bool(revision_candidate.get("may_change_answer")):
        return ()
    if bool(revision_candidate.get("may_update_graph")):
        return ()
    if not bool(revision_candidate.get("requires_analysis_revision_gate")):
        return ()

    candidate_intent = "route_analysis_revision_candidate_to_existing_internal_work"
    binding_key = "|".join(
        (
            objective_id,
            source_frame_id,
            source_analysis_id,
            revision_id,
            proposed_revision_type,
            candidate_intent,
        )
    )
    internal_id = stable_id("analysis-internal-work-candidate", binding_key)
    label = proposed_revision_type.replace("_", " ")
    return (
        InternalWorkCandidate(
            internal_work_candidate_id=internal_id,
            active_objective_id=objective_id,
            source_frame_id=source_frame_id,
            source_analysis_id=source_analysis_id,
            source_refinement_id=str(source_request.get("source_refinement_id") or ""),
            source_question_candidate_id=str(source_request.get("source_question_candidate_id") or ""),
            domain=domain or "source_bound_analysis",
            unresolved_slot_id=proposed_revision_type,
            candidate_intent=candidate_intent,
            semantic_binding_key=binding_key,
            latest_state_id=revision_id,
            unresolved_label=label,
            why_it_matters=str(
                revision_candidate.get("proposed_revision_scope")
                or "A dry-run boundary indicates this analysis may need later revision when real evidence is available."
            ),
            safe_deterministic_next_step=(
                "Keep this evidence boundary unresolved in the existing continuation path. "
                "Do not append an analysis refinement unless a later explicit source and revision gate authorize it."
            ),
            continuation_prompt=(
                "This remains pending internal work: revisit the analysis only after real evidence or operator context is available."
            ),
            expected_answer_type="",
            priority=1,
            authority_boundary=(
                "This routes a revision candidate into the existing internal-work path only; it does not approve or append a refinement."
            ),
            prohibited_actions=tuple(
                dict.fromkeys(
                    (
                        *(str(item) for item in revision_candidate.get("blocked_change", ()) if str(item)),
                        "Do not append AnalysisRefinement.",
                        "Do not mutate analysis, problem state, answer state, graph truth, review, admission, or replanning.",
                        "Do not read files, access networks, call models/providers/tools, execute sandboxes, mutate source, start workers, or start schedulers.",
                    )
                )
            ),
            risk_class="safe_internal",
            status="candidate",
            created_event_id=stable_id("analysis-internal-work-candidate-event", internal_id),
            restart_summary=(
                "Existing internal-work candidate created from an evidence analysis revision candidate; "
                "no new approval ladder, refinement append, analysis update, graph mutation, review, admission, execution, worker, scheduler, or external action occurred."
            ),
        ),
    )


def _canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def classify_evidence_next_operation_operator_response(proposal: Mapping[str, Any], message: str) -> str | None:
    """Classify a reply to a non-executing next-operation proposal."""

    text = " ".join(str(message or "").split())
    lower = text.lower()
    if not text or text.endswith("?"):
        return None
    if re.match(r"^(?:what|why|how|who|where|when|can|could|would|should|is|are|do|does|did)\b", lower):
        return None
    if re.search(r"\b(?:later|not\s+now|defer|hold|wait|park|postpone|leave\s+(?:it|that)\s+open|keep\s+(?:it|that)\s+open)\b", lower):
        return "deferred"
    if re.search(r"\b(?:no|nope|deny|decline|do\s+not|don't|not\s+authorized|not\s+approved|stop)\b", lower):
        return "declined"
    if re.search(r"\b(?:yes|approve|approved|accept|accepted|authorize|authorized|allow|allowed|go\s+ahead|you\s+may|permission\s+granted|keep\s+(?:it|that)|sounds\s+good)\b", lower):
        return "accepted_pending_separate_execution"
    if re.search(r"\b(?:maybe|not\s+sure|unclear|depends)\b", lower):
        return "unclear_pending"
    if len(text.split()) >= 4:
        return "context_provided"
    return None


def render_evidence_next_operation_proposal(proposal: Mapping[str, Any]) -> str:
    """Render one proposed next operation without starting it."""

    permitted = tuple(str(item) for item in proposal.get("permitted_inputs", ()) if str(item))
    prohibited = tuple(str(item) for item in proposal.get("prohibited_actions", ()) if str(item))
    return "\n".join(
        (
            "A bounded next evidence operation can be proposed from your authorization.",
            f"Evidence gap: {str(proposal.get('evidence_gap_slot_id') or '')}",
            f"Proposed operation: {str(proposal.get('proposed_operation_type') or '').replace('_', ' ')}",
            f"Scope: {str(proposal.get('proposed_scope') or '')}",
            "Permitted inputs: " + ("; ".join(permitted) if permitted else "Only the already-recorded source-bound analysis and authorization."),
            f"Expected evidence: {str(proposal.get('expected_evidence') or '')}",
            f"Next authority required: {str(proposal.get('authority_required_next') or '')}",
            "Prohibited now: " + ("; ".join(prohibited) if prohibited else "No execution, file read, network, provider, model, tool, sandbox, graph, review, admission, or external action."),
            "Question: Should I keep this proposal ready for a later separate execution gate, decline it, defer it, or add context?",
            "Status: proposal only. It cannot execute in this phase.",
        )
    )


def render_evidence_next_operation_disposition(
    proposal: Mapping[str, Any],
    disposition: Mapping[str, Any],
) -> str:
    """Acknowledge one proposal disposition without executing it."""

    status = str(disposition.get("status") or "")
    if status == "accepted_pending_separate_execution":
        detail = "I kept this bounded next operation ready for a later separate execution gate. It has not started."
    elif status == "declined":
        detail = "I recorded that this next operation is declined for the current analysis."
    elif status == "deferred":
        detail = "I left this next operation deferred and will not execute or resurface it as a new proposal automatically."
    elif status == "context_provided":
        detail = "I recorded your added context with the proposal without executing the operation."
    else:
        detail = "I recorded the response as unclear and did not authorize execution."
    return "\n".join(
        (
            f"Evidence next-operation update: {detail}",
            f"Proposal: {str(proposal.get('evidence_next_operation_proposal_id') or '')}",
            f"Decision: {status.replace('_', ' ')}",
            f"Context supplied: {str(disposition.get('operator_context_text') or 'None')}",
            "Execution state: no evidence gathering, model call, provider call, tool use, file read, network access, sandbox execution, graph mutation, review, admission, worker, scheduler, or external action started.",
        )
    )


def render_evidence_next_operation_recall(
    proposal: Mapping[str, Any],
    disposition: Mapping[str, Any] | None = None,
) -> str:
    """Read one next-operation proposal posture without changing it."""

    status = str((disposition or {}).get("status") or proposal.get("status") or "proposed")
    return "\n".join(
        (
            "The recorded evidence next-operation proposal is:",
            f"Proposal: {str(proposal.get('evidence_next_operation_proposal_id') or '')}",
            f"Evidence gap: {str(proposal.get('evidence_gap_slot_id') or '')}",
            f"Proposed operation: {str(proposal.get('proposed_operation_type') or '').replace('_', ' ')}",
            f"Status: {status.replace('_', ' ')}",
            "This is read-only recall; it did not execute evidence gathering or create a new proposal disposition.",
        )
    )


def render_internal_work_disposition(
    candidate: Mapping[str, Any],
    disposition: Mapping[str, Any],
) -> str:
    """Acknowledge one operator disposition without executing the proposal."""

    status = str(disposition.get("status") or "")
    label = str(candidate.get("unresolved_label") or "the unresolved issue")
    if status == "accepted":
        detail = "I recorded the continuation as ready for a later explicit, bounded step. It has not started work."
    elif status == "operator_deferred":
        detail = "I kept the continuation deferred and will not resurface it automatically for this analysis."
    elif status == "operator_dismissed":
        detail = "I suppressed this continuation for the current analysis while preserving the original evidence and analysis history."
    elif status == "answered_unknown":
        detail = "I recorded that the context remains unknown and left the source-bound issue unresolved without starting work."
    else:
        detail = "I recorded the supplied context against this continuation proposal without executing it or changing the original analysis."
    return (
        f"Internal continuation update for {label}: {detail}\n\n"
        "This is a provenance-only disposition; it did not create graph truth, review, admission, a model request, provider call, tool execution, or external action."
    )


def render_internal_work_recall(
    candidate: Mapping[str, Any],
    selection: Mapping[str, Any] | None = None,
    disposition: Mapping[str, Any] | None = None,
) -> str:
    """Read a recorded continuation posture without changing it."""

    status = str((disposition or {}).get("status") or (selection or {}).get("status") or candidate.get("status") or "candidate")
    return "\n".join(
        (
            "The recorded internal continuation is:",
            f"Unresolved issue: {str(candidate.get('unresolved_label') or '')}",
            f"Why it matters: {str(candidate.get('why_it_matters') or '')}",
            f"Status: {status.replace('_', ' ')}",
            f"Next safe step: {str(candidate.get('safe_deterministic_next_step') or '')}",
            "This is a read-only provenance recall; it did not create a candidate, request, disposition, model call, provider call, tool execution, or external action.",
        )
    )


def operator_question_answer_is_compatible(candidate: Mapping[str, Any], message: str) -> bool:
    """Check an answer's semantic shape before binding it to a selected question.

    This is intentionally a conservative answer-shape check, not a truth check.
    It prevents a fresh foreground question or unrelated declarative statement
    from being silently consumed by a pending analysis question.
    """

    text = " ".join(str(message or "").split())
    lower = text.lower()
    if not text or text.endswith("?"):
        return False
    if re.match(r"^(?:what|why|how|who|where|when|can|could|would|should|is|are|do|does|did)\b", lower):
        return False
    if re.match(r"^(?:your\s+new\s+goal|please\s+|help\s+me\s+|do\s+not\s+|don't\s+)", lower):
        return False
    if _operator_declares_unknown(lower):
        return True
    expected = str(candidate.get("expected_answer_type") or "")
    matchers = {
        "temporal_commitment": _looks_like_temporal_commitment,
        "payment_status": _looks_like_payment_status,
        "availability_status": _looks_like_availability_status,
        "urgency_classification": _looks_like_urgency_classification,
        "explanation_preference": _looks_like_explanation_preference,
        "ownership_context": _looks_like_ownership_context,
        "risk_threshold": _looks_like_risk_threshold,
        "account_context": _looks_like_account_context,
        "target_variable": _looks_like_target_variable,
    }
    matcher = matchers.get(expected)
    return bool(matcher and matcher(lower))


def compile_operator_question_answer(
    candidate: Mapping[str, Any],
    answer_text: str,
) -> OperatorQuestionAnswer | None:
    """Compile one operator-provided, non-authoritative answer record."""

    if not operator_question_answer_is_compatible(candidate, answer_text):
        return None
    normalized = " ".join(str(answer_text or "").split())
    question_id = str(candidate.get("question_id") or "")
    binding_key = str(candidate.get("question_binding_key") or "")
    if not question_id or not binding_key:
        return None
    declared_unknown = _operator_declares_unknown(normalized.lower())
    answer_id = stable_id("analysis-question-answer", question_id, normalized)
    return OperatorQuestionAnswer(
        answer_id=answer_id,
        question_id=question_id,
        question_binding_key=binding_key,
        source_frame_id=str(candidate.get("source_frame_id") or ""),
        source_analysis_id=str(candidate.get("source_analysis_id") or ""),
        answer_text=normalized,
        interpreted_value=("operator reports this value is not currently known" if declared_unknown else normalized),
        confidence_label=("operator_declared_unknown" if declared_unknown else "operator_stated_compatible_shape"),
        changes_unknowns=(str(candidate.get("unknown_slot_id") or ""),),
        status=("bound_unknown" if declared_unknown else "bound_operator_answer"),
        created_event_id=stable_id("analysis-question-answer-event", answer_id),
        restart_summary="Operator answer is bound only to the selected source-bound analysis question; it is not graph truth or external verification.",
    )


def compile_analysis_refinement(
    analysis: Mapping[str, Any],
    candidate: Mapping[str, Any],
    answer: Mapping[str, Any],
) -> AnalysisRefinement:
    """Append a limited refinement without modifying the original analysis."""

    source_analysis_id = str(analysis.get("analysis_id") or "")
    source_frame_id = str(analysis.get("source_frame_id") or "")
    question_id = str(candidate.get("question_id") or "")
    answer_id = str(answer.get("answer_id") or "")
    unknown_slot_id = str(candidate.get("unknown_slot_id") or "")
    before_summary = str(analysis.get("result_summary") or "")
    answer_value = str(answer.get("interpreted_value") or answer.get("answer_text") or "")
    after_summary = _refined_summary(analysis, candidate, answer_value)
    remaining = _remaining_uncertainty(analysis, candidate, answer)
    safe_next_actions = tuple(
        str(item.get("action") or "")
        for item in analysis.get("safe_next_actions", ())
        if isinstance(item, Mapping) and str(item.get("action") or "")
    )
    refinement_id = stable_id("evidence-bound-analysis-refinement", source_analysis_id, question_id, answer_id)
    return AnalysisRefinement(
        refinement_id=refinement_id,
        source_analysis_id=source_analysis_id,
        source_frame_id=source_frame_id,
        source_question_id=question_id,
        source_answer_id=answer_id,
        question_binding_key=str(candidate.get("question_binding_key") or ""),
        changed_unknown_slots=(unknown_slot_id,) if unknown_slot_id else (),
        before_summary=before_summary,
        after_summary=after_summary,
        changed_fields=(unknown_slot_id, "operator_provided_context") if unknown_slot_id else ("operator_provided_context",),
        remaining_uncertainty=remaining,
        safe_next_actions=safe_next_actions,
        prohibited_actions=tuple(str(item) for item in analysis.get("prohibited_actions", ()) if str(item)),
        status="provisional_refinement",
        created_event_id=stable_id("evidence-bound-analysis-refinement-event", refinement_id),
        restart_summary="Append-only source-bound refinement retained beside the original analysis; no graph truth, review, admission, model, provider, tool, or external action occurred.",
    )


def render_evidence_bound_analysis_question(
    analysis: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> str:
    """Render one concise, inspectable question on the normal conversation path."""

    return "\n".join(
        (
            "I created a bounded, source-bound analysis from the supplied scenario.",
            f"Summary: {str(analysis.get('result_summary') or '')}",
            f"Why one clarification matters: {str(candidate.get('why_it_matters') or '')}",
            f"Question: {str(candidate.get('question_text') or '')}",
            f"Safety boundary: {str(candidate.get('safety_boundary') or '')}",
            "Status: provisional analysis only. Your answer will refine this one analysis record; it will not create graph truth, review, admission, a model request, provider call, tool execution, or external action.",
        )
    )


def render_evidence_bound_analysis_refinement(refinement: Mapping[str, Any]) -> str:
    """Show the operator exactly how one answer changed a provisional analysis."""

    uncertainty = tuple(str(item) for item in refinement.get("remaining_uncertainty", ()) if str(item))
    return "\n".join(
        (
            "I appended your answer as a source-bound refinement of the existing analysis.",
            f"What changed: {str(refinement.get('after_summary') or '')}",
            "Still uncertain: " + ("; ".join(uncertainty) if uncertainty else "No additional uncertainty was recorded for this bounded refinement."),
            "Status: provisional refinement only. The original analysis is preserved, and this did not create graph truth, review, admission, a model request, provider call, tool execution, or external action.",
        )
    )


def render_evidence_bound_analysis_refinement_recall(
    refinement: Mapping[str, Any],
    *,
    focus: str,
    analysis: Mapping[str, Any] | None = None,
    candidate: Mapping[str, Any] | None = None,
    answer: Mapping[str, Any] | None = None,
) -> str:
    """Read one existing refinement without creating a new candidate or request."""

    if focus == "uncertainty":
        detail = "; ".join(str(item) for item in refinement.get("remaining_uncertainty", ()) if str(item))
        prefix = "The remaining uncertainty is"
    elif focus == "chain":
        source_summary = str(refinement.get("before_summary") or (analysis or {}).get("result_summary") or "")
        question_text = str((candidate or {}).get("question_text") or refinement.get("source_question_id") or "")
        answer_text = str((answer or {}).get("answer_text") or refinement.get("source_answer_id") or "")
        detail = "\n".join(
            (
                f"Analysis: {source_summary}",
                f"Question asked: {question_text}",
                f"Operator answer: {answer_text}",
                f"What changed: {str(refinement.get('after_summary') or '')}",
                "Still uncertain: "
                + (
                    "; ".join(str(item) for item in refinement.get("remaining_uncertainty", ()) if str(item))
                    or "No additional uncertainty was recorded."
                ),
            )
        )
        prefix = "The recorded chain is"
    else:
        detail = str(refinement.get("after_summary") or "")
        prefix = "The recorded change is"
    return (
        f"{prefix}: {detail}\n\n"
        f"Refinement: {str(refinement.get('refinement_id') or '')}\n"
        "This is a read-only source-bound refinement recall; it did not create a question, answer, or refinement."
    )


def _question_specifications(analysis: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    domain = str(analysis.get("domain") or "")
    role_values = _analysis_role_values(analysis)
    if domain == "operations_logistics_receivables":
        resource = str(role_values.get("delivery_or_resource_condition") or "the delivery dependency")
        job = str(role_values.get("work_item_or_job") or "the blocked job")
        invoice = str(role_values.get("receivable_or_invoice_state") or "the overdue invoice")
        return (
            _question_spec(
                "logistics.pump_delivery_eta", "delivery ETA", f"When is {resource} expected to arrive?",
                f"The delivery timing determines whether {job} is blocked now or can be scheduled around a known date.",
                "temporal_commitment", 100, "The delivery dependency directly blocks the named work.",
                "Record only operator-provided timing; do not contact a vendor or change the schedule.",
                ("delivery_or_resource_condition", "work_item_or_job"),
            ),
            _question_spec(
                "logistics.invoice_payment_status", "invoice payment status", f"Is {invoice} disputed, paid, or simply still unpaid?",
                "Payment status determines whether the receivable is an active cashflow risk or an already-resolved record.",
                "payment_status", 80, "The receivable remains material but does not unblock the job before delivery timing is known.",
                "Record only operator-provided status; do not contact the customer or represent payment as verified.",
                ("receivable_or_invoice_state",),
            ),
            _question_spec(
                "logistics.alternate_resource_available", "alternate resource availability", f"Is another {resource} available for {job}?",
                "An alternate could reduce the schedule dependency if delivery timing is unfavorable.",
                "availability_status", 70, "This matters after the expected delivery timing is known.",
                "Do not reserve, borrow, buy, or deploy equipment.",
                ("delivery_or_resource_condition", "work_item_or_job"),
            ),
            _question_spec(
                "logistics.job_priority", "job priority", f"How urgent is {job} relative to the other work?",
                "Priority affects the safe scheduling interpretation once delivery and payment context are known.",
                "urgency_classification", 60, "Priority helps rank follow-up but does not resolve the immediate delivery blocker.",
                "Do not reschedule work or make commitments.",
                ("work_item_or_job",),
            ),
        )
    if domain == "physics_mechanics":
        return (
            _question_spec(
                "physics.requested_output_form", "requested explanation form", "Would a numeric result, a derivation, or both be most useful?",
                "The same frictionless-incline model can be presented at different useful levels without changing the underlying assumptions.",
                "explanation_preference", 80, "The mathematical result is available, but the requested explanation depth is not explicit.",
                "Keep the idealized model provisional; do not present it as an experimental measurement.",
                ("inclined_surface", "friction_condition"),
            ),
        )
    if domain == "defensive_cybersecurity":
        return (
            _question_spec(
                "cyber.authorization_context", "defensive ownership context", "Is this code or a fixture you own and are reviewing defensively?",
                "Ownership and defensive scope determine which safe review or mitigation discussion is appropriate.",
                "ownership_context", 100, "Defensive authorization must be clear before discussing a code-path-specific follow-up.",
                "Do not generate payloads, scan targets, bypass controls, or run code.",
                ("untrusted_input", "sql_command_sink", "execution_boundary"),
            ),
        )
    if domain == "finance_portfolio_risk":
        return (
            _question_spec(
                "finance.drawdown_tolerance", "six-month drawdown tolerance", "What six-month decline would be unacceptable for this account?",
                "A risk threshold is needed to interpret the concentration scenario without issuing a trade instruction.",
                "risk_threshold", 100, "Tolerance is the most decision-relevant missing constraint in the stated scenario.",
                "Do not recommend or execute a trade, and do not fabricate market data.",
                ("stress_scenario",),
            ),
            _question_spec(
                "finance.risk_tolerance", "risk tolerance", "How would you describe the account's risk tolerance: cautious, balanced, or aggressive?",
                "Risk tolerance helps qualify the scenario discussion after the unacceptable drawdown is known.",
                "risk_threshold", 90, "It is material but less specific than a stated loss threshold.",
                "Do not recommend or execute a trade, and do not fabricate market data.",
                ("stress_scenario",),
            ),
            _question_spec(
                "finance.account_constraints", "account constraints", "Are there tax, retirement, liquidity, or other account constraints that matter here?",
                "Account constraints can change how a hypothetical risk discussion should be qualified.",
                "account_context", 70, "This refines the context but does not outrank the stated risk threshold.",
                "Do not recommend or execute a trade, and do not fabricate market data.",
                ("stress_scenario",),
            ),
        )
    if domain == "physics_equation_model":
        return (
            _question_spec(
                "equation.target_unknown", "target variable", "Which quantity do you want to solve for: net force, mass, or acceleration?",
                "The model can solve for different variables, and the required known values depend on the intended target.",
                "target_variable", 100, "The requested output is the key missing modeling choice.",
                "Keep the explanation within the classical net-force model; do not infer unstated forces.",
                ("equation",),
            ),
        )
    return ()


def _question_spec(
    unknown_slot_id: str,
    unknown_label: str,
    question_text: str,
    why_it_matters: str,
    expected_answer_type: str,
    priority: int,
    priority_reason: str,
    safety_boundary: str,
    source_role_refs: Sequence[str],
) -> dict[str, Any]:
    return {
        "unknown_slot_id": unknown_slot_id,
        "unknown_label": unknown_label,
        "question_text": question_text,
        "why_it_matters": why_it_matters,
        "expected_answer_type": expected_answer_type,
        "priority": priority,
        "priority_reason": priority_reason,
        "safety_boundary": safety_boundary,
        "source_role_refs": tuple(source_role_refs),
    }


def _analysis_role_values(analysis: Mapping[str, Any]) -> Mapping[str, Any]:
    signature = analysis.get("semantic_signature")
    if not isinstance(signature, Mapping):
        return {}
    values = signature.get("role_values")
    return values if isinstance(values, Mapping) else {}


def _operator_declares_unknown(lower: str) -> bool:
    return bool(re.search(r"\b(?:i\s+(?:do\s+not|don't)\s+know|not\s+sure|unknown|no\s+idea|cannot\s+say)\b", lower))


def _looks_like_temporal_commitment(lower: str) -> bool:
    return bool(re.search(
        r"\b(?:today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|next\s+(?:week|month)|this\s+(?:week|month)|end\s+of\s+(?:the\s+)?(?:week|month)|within\s+\d+\s*(?:day|week|month)s?|in\s+\d+\s*(?:day|week|month)s?|on\s+\w+\s+\d{1,2}|eta|arriv(?:e|es|ing)|deliver(?:y|ed|ing))\b",
        lower,
    ))


def _looks_like_payment_status(lower: str) -> bool:
    return bool(
        re.search(
            r"\b(?:paid|unpaid|overdue|disputed|settled|pending|payment|invoice|remittance|commit(?:ted|ment)|bill(?:ing)?|charge|receivable|cash|funds?|collection|customer\s+(?:contests?|challenges?))\b",
            lower,
        )
    )


def _looks_like_availability_status(lower: str) -> bool:
    return bool(re.search(r"\b(?:available|unavailable|not\s+available|spare|replacement|alternate|backup|borrow(?:ed|able)?|none\s+available)\b", lower))


def _looks_like_urgency_classification(lower: str) -> bool:
    return bool(re.search(r"\b(?:urgent|urgency|critical|high|medium|low|priority|asap|can\s+wait|time[-\s]?sensitive)\b", lower))


def _looks_like_explanation_preference(lower: str) -> bool:
    return bool(re.search(r"\b(?:numeric|number|derivation|derive|both|diagram|free[-\s]?body|step[-\s]?by[-\s]?step|brief|detailed|explain)\b", lower))


def _looks_like_ownership_context(lower: str) -> bool:
    return bool(re.search(r"\b(?:i\s+own|we\s+own|our\s+code|my\s+code|internal|fixture|test|authorized|defensive\s+review|codebase)\b", lower))


def _looks_like_risk_threshold(lower: str) -> bool:
    has_threshold = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:%|percent\b)", lower))
    has_context = bool(re.search(r"\b(?:drawdown|decline|loss|drop|tolerat(?:e|ion)|unacceptable|risk|cautious|balanced|aggressive)\b", lower))
    return has_threshold and has_context or bool(re.search(r"\b(?:cautious|balanced|aggressive)\b", lower))


def _looks_like_account_context(lower: str) -> bool:
    return bool(re.search(r"\b(?:taxable|retirement|ira|401\(k\)|brokerage|liquidity|margin|trust|education|cash\s+need)\b", lower))


def _looks_like_target_variable(lower: str) -> bool:
    return bool(re.search(r"\b(?:force|net\s+force|mass|acceleration|solve\s+for\s+[fma])\b", lower))


def _remaining_uncertainty(
    analysis: Mapping[str, Any],
    candidate: Mapping[str, Any],
    answer: Mapping[str, Any],
) -> tuple[str, ...]:
    if str(answer.get("status") or "") == "bound_unknown":
        return tuple(str(item) for item in analysis.get("uncertainty", ()) if str(item))
    expected = str(candidate.get("expected_answer_type") or "")
    exclusions = {
        "temporal_commitment": ("eta", "delivery", "arriv"),
        "payment_status": ("payment", "dispute", "committed payment"),
        "availability_status": ("alternate", "available"),
        "urgency_classification": ("urgent", "priority"),
        "risk_threshold": ("risk tolerance", "drawdown", "risk"),
        "account_context": ("tax", "account"),
        "target_variable": ("unknown", "solve"),
        "explanation_preference": ("numerical", "precision", "diagram"),
    }.get(expected, ())
    return tuple(
        str(item)
        for item in analysis.get("uncertainty", ())
        if str(item) and not any(token in str(item).lower() for token in exclusions)
    )


def _refined_summary(
    analysis: Mapping[str, Any],
    candidate: Mapping[str, Any],
    answer_value: str,
) -> str:
    before = str(analysis.get("result_summary") or "The original source-bound analysis remains available.")
    slot = str(candidate.get("unknown_slot_id") or "")
    label = str(candidate.get("unknown_label") or "the selected uncertainty")
    answer_sentence = str(answer_value or "").rstrip(".?! ") or str(answer_value or "")
    if slot == "logistics.pump_delivery_eta":
        return (
            f"{before} The operator-stated delivery timing is {answer_sentence}. "
            "The schedule blocker is now time-bounded by that stated timing; payment status, alternate availability, and work priority remain provisional unless separately clarified."
        )
    if slot == "finance.drawdown_tolerance":
        return (
            f"{before} The operator-stated unacceptable six-month decline is {answer_sentence}. "
            "That threshold now qualifies the scenario discussion without becoming a trade instruction or live-market conclusion."
        )
    if slot == "cyber.authorization_context":
        return (
            f"{before} The operator supplied this defensive ownership context: {answer_sentence}. "
            "Any later follow-up remains limited to defensive review and does not authorize testing, scanning, payloads, or code execution."
        )
    return (
        f"{before} The operator supplied {label}: {answer_sentence}. "
        "This narrows one source-bound uncertainty while the remaining assumptions and limits stay provisional."
    )


def _operations_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "operational_dependency_risk_triage"
    analysis_id = _analysis_id(record, analysis_type)
    invoice = _entity_label(frame, "receivable", "the overdue invoice")
    crew = _entity_label(frame, "execution_actor", "the crew")
    job = _entity_label(frame, "blocked_work", "the job")
    resource = _entity_label(frame, "dependency_resource", "the pump")
    overdue = _quantity_text(frame, "overdue duration", "overdue")
    evidence = (
        _evidence(analysis_id, "receivable_status", f"{invoice} is an overdue invoice ({overdue}).", frame, invoice, overdue),
        _evidence(analysis_id, "blocked_start", f"{crew} cannot start {job} until the dependency is resolved.", frame, crew, job),
        _evidence(analysis_id, "delivery_dependency", f"{resource} delivery is stated as a prerequisite for {job}.", frame, resource, "delivered"),
    )
    checks = (
        _check(analysis_id, "source_names_overdue_invoice", "The source contains an overdue invoice.", "overdue receivable is explicit", "observed_in_source", "Payment status is not externally verified."),
        _check(analysis_id, "source_names_blocked_start", "The source contains a crew/job blocked start.", "blocked start is explicit", "observed_in_source", "No schedule outcome is verified."),
        _check(analysis_id, "source_names_delivery_dependency", "The source contains a delivery dependency.", "resource prerequisite is explicit", "observed_in_source", "Pump ETA and alternate availability are unknown."),
        _check(analysis_id, "external_status_not_verified", "No external payment or delivery status was checked.", "no external verification", "not_performed_by_design", "The analysis is limited to the supplied source."),
    )
    actions = (
        _action(analysis_id, "Ask for the pump ETA.", "operator-provided information", risk="low"),
        _action(analysis_id, "Check the invoice payment status or dispute status with operator approval.", "operator approval before external communication", risk="moderate"),
        _action(analysis_id, "Identify whether an alternate pump is available.", "operator-provided information or approval", risk="low"),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            f"Cashflow or receivable risk: {invoice} is {overdue}.",
            f"Schedule dependency risk: {crew} cannot start {job} before {resource} is delivered.",
            f"Operational bottleneck: {resource} delivery blocks {crew} from starting {job}.",
        ),
        selected_method="dependency and risk triage",
        method_rationale="The source names one receivable exposure and one delivery dependency that blocks job execution, so they should be separated and clarified before any external action.",
        validation_checks=checks,
        result_summary=(
            f"The source supports two operational risks: a cashflow or receivable risk from {invoice} being {overdue}, "
            f"and a schedule risk because {resource} delivery blocks {crew} from starting {job}."
        ),
        safe_next_actions=actions,
        prohibited_actions=(
            "Do not contact the client or vendor automatically.",
            "Do not alter the schedule or represent payment status without confirming it.",
        ),
        risk_class="operational_decision_support_no_external_action",
    )


def _incline_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "frictionless_incline_solution_sketch"
    analysis_id = _analysis_id(record, analysis_type)
    angle = _quantity_value(frame, "incline angle")
    mass = _quantity_value(frame, "mass")
    acceleration = _incline_acceleration(angle)
    result = (
        f"Using a = g sin(theta), a {angle}-degree frictionless incline gives approximately {acceleration:.1f} m/s^2 down the plane when g is approximately 9.8 m/s^2. The stated mass ({mass} kg) cancels from the acceleration."
        if acceleration is not None and angle
        else "Use a = g sin(theta) for acceleration down a frictionless incline; a numeric result needs a usable angle and gravity convention."
    )
    angle_check_result = "observed_in_source" if angle else "missing_from_source"
    half_check_result = "passes" if _is_thirty_degrees(angle) else "not_applicable_to_stated_angle"
    evidence = (
        _evidence(analysis_id, "system_body", f"The source identifies a {mass or 'stated'} kg block on an incline.", frame, "block", mass),
        _evidence(analysis_id, "incline_angle", f"The source gives an incline angle of {angle or 'an unspecified'} degrees.", frame, angle, "incline"),
        _evidence(analysis_id, "constraint", "The source states that the incline is frictionless.", frame, "frictionless"),
    )
    checks = (
        _check(analysis_id, "acceleration_units", "Acceleration is expressed in m/s^2.", "dimension of acceleration", "passes" if acceleration is not None else "symbolic_only", "A numeric result requires a gravity convention."),
        _check(analysis_id, "incline_angle_present", "The source gives an incline angle.", "usable angle", angle_check_result, "No numeric acceleration follows if the angle is missing."),
        _check(analysis_id, "thirty_degree_sine", "For 30 degrees, sin(theta) equals 0.5.", "half gravitational acceleration", half_check_result, "This check applies only to the stated 30-degree case."),
        _check(analysis_id, "bounded_by_gravity", "The acceleration should be less than g for an incline below 90 degrees.", "0 <= a < g", "passes" if acceleration is not None else "symbolic_check_pending", "The angle must be in the physical incline range."),
        _check(analysis_id, "mass_cancels", "Mass cancels from frictionless-incline acceleration.", "same acceleration for any stated mass", "passes", "This relies on the frictionless idealization."),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            "The problem specifies a frictionless incline.",
            f"The stated target is acceleration down the incline at {angle or 'the supplied'} degrees.",
            "The mass cancels from the acceleration in the frictionless model.",
        ),
        selected_method="Newtonian force decomposition using a = g sin(theta)",
        method_rationale="On a frictionless incline, the component of gravity parallel to the plane determines acceleration while the normal force cancels the perpendicular component.",
        validation_checks=checks,
        result_summary=result,
        safe_next_actions=(
            _action(analysis_id, "Ask whether numeric precision or a free-body diagram is needed.", "none", risk="low"),
        ),
        prohibited_actions=("Do not treat the idealized result as an experimental measurement.",),
        risk_class="safe_physics_modeling",
    )


def _defensive_sql_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "defensive_sql_source_to_sink_analysis"
    analysis_id = _analysis_id(record, analysis_type)
    evidence = (
        _evidence(analysis_id, "untrusted_source", "User-controlled input is identified as the source.", frame, "User input", "input"),
        _evidence(analysis_id, "database_sink", "SQL query execution is identified as the command sink.", frame, "SQL query", "execution"),
        _evidence(analysis_id, "unsafe_construction", "The source states that input is concatenated into the query before execution.", frame, "concatenated"),
    )
    checks = (
        _check(analysis_id, "source_exists", "An external or user-controlled source exists.", "untrusted source", "observed_in_source", "The exact validation layer is unknown."),
        _check(analysis_id, "sink_exists", "A SQL execution sink exists.", "database command sink", "observed_in_source", "The driver and query path are not supplied."),
        _check(analysis_id, "unsafe_construction_exists", "String concatenation is present before the sink.", "unsafe query construction", "observed_in_source", "Prepared-statement use must still be verified in code."),
        _check(analysis_id, "payload_not_needed", "No exploit payload is required for this defensive classification.", "defensive review without exploitation", "passes_by_design", "This does not establish exploitability against a target."),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            "Trust boundary: user-controlled input flows toward a database command sink.",
            "Risk: concatenated input creates a SQL injection candidate.",
            "The analysis is defensive because it focuses on containment and validation, not exploitation.",
        ),
        selected_method="defensive source-to-sink review",
        method_rationale="The source identifies an untrusted input crossing into executable SQL construction, which calls for defensive containment checks rather than payload generation or target interaction.",
        validation_checks=checks,
        result_summary="This is a defensive SQL injection candidate: untrusted input reaches SQL query construction through concatenation before execution. The safe response is to verify parameter binding and boundary controls.",
        safe_next_actions=(
            _action(analysis_id, "Use a parameterized query or prepared statement.", "code-change approval", risk="moderate"),
            _action(analysis_id, "Validate input at the boundary and use a least-privilege database account.", "code-change approval", risk="moderate"),
            _action(analysis_id, "Add a regression test that verifies parameter binding.", "code-change approval", risk="low"),
        ),
        prohibited_actions=(
            "Do not generate exploit payloads.",
            "Do not scan a target, bypass controls, evade detection, or build an offensive chain.",
        ),
        risk_class="defensive_cybersecurity_review_only",
    )


def _portfolio_risk_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "portfolio_concentration_scenario_analysis"
    analysis_id = _analysis_id(record, analysis_type)
    allocations = _portfolio_allocations(frame)
    allocation_total = sum(weight for weight, _asset in allocations)
    allocation_text = ", ".join(f"{weight:g}% {asset}" for weight, asset in allocations) or "the stated allocations"
    evidence = tuple(
        _evidence(analysis_id, "portfolio_allocation", f"The source assigns {weight:g}% to {asset}.", frame, asset, f"{weight:g}%")
        for weight, asset in allocations
    ) + (
        _evidence(analysis_id, "scenario", "The source names an AI/tech correction scenario over the stated horizon.", frame, "AI", "tech", "six-month"),
    )
    allocation_result = "passes" if allocations and abs(allocation_total - 100.0) < 0.001 else "needs_source_clarification"
    checks = (
        _check(analysis_id, "allocations_sum", "The supplied allocations sum to 100%.", "allocation total equals 100%", allocation_result, f"Recorded total is {allocation_total:g}% from the supplied entries."),
        _check(analysis_id, "live_data_unavailable", "Live prices and correlations are unavailable.", "no fabricated market data", "not_available_by_design", "This is not a live valuation or forecast."),
        _check(analysis_id, "operator_constraints_unknown", "Tax, account, and risk-tolerance constraints are unknown.", "decision constraints supplied", "missing_from_source", "No personalized recommendation should follow."),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            f"Stated allocation: {allocation_text}.",
            "Primary risks: sector concentration, drawdown sensitivity, volatility, cash drag, and horizon mismatch.",
            "The supplied scenario is a bounded six-month AI/tech correction discussion, not a market forecast.",
        ),
        selected_method="concentration and scenario risk analysis",
        method_rationale="The source provides a concentrated allocation, a cash buffer, and a correction scenario, so the appropriate bounded method is exposure and scenario framing rather than a trade decision.",
        validation_checks=checks,
        result_summary=(
            f"The stated portfolio ({allocation_text}) has material concentration and drawdown sensitivity to an AI/tech correction. "
            "Cash provides a buffer but can create opportunity-cost or cash-drag tradeoffs; live pricing, correlations, tax constraints, and risk tolerance remain unknown."
        ),
        safe_next_actions=(
            _action(analysis_id, "Build a descriptive scenario table from the stated allocations.", "none for a local hypothetical table", risk="low"),
            _action(analysis_id, "Ask for holdings, account type, risk tolerance, and drawdown tolerance.", "operator-provided information", risk="low"),
        ),
        prohibited_actions=(
            "Do not issue an autonomous buy or sell instruction.",
            "Do not execute a trade or fabricate market prices, correlations, or returns.",
        ),
        risk_class="financial_decision_support_no_trade_execution",
    )


def _newtons_second_law_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "newtons_second_law_model_analysis"
    analysis_id = _analysis_id(record, analysis_type)
    evidence = (
        _evidence(analysis_id, "equation", "The source states the equation F = ma.", frame, "F", "m", "a"),
        _evidence(analysis_id, "modeled_quantity", "The frame identifies force, mass, and acceleration as the modeled variables.", frame, "F", "m", "a"),
    )
    checks = (
        _check(analysis_id, "dimensional_consistency", "Check N = kg*m/s^2.", "force dimensions match mass times acceleration", "passes_as_model_check", "Known values are still needed for a numeric result."),
        _check(analysis_id, "net_force", "Use net force rather than one arbitrary individual force.", "relevant forces are summed", "required_before_numeric_use", "A free-body model may be needed for a concrete scenario."),
        _check(analysis_id, "classical_domain", "Apply the model in an inertial frame at classical scales.", "model assumptions are stated", "recorded_as_assumption", "The equation is not a complete description of every system."),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            "F = ma means net force equals mass times acceleration.",
            "Given the other two quantities, the model can solve for net force, mass, or acceleration.",
            "A validation check is to use net force and confirm N = kg*m/s^2.",
        ),
        selected_method="dimensional and model interpretation of Newton's second law",
        method_rationale="The equation is a classical mechanics model relating net force, mass, and acceleration; the bounded analysis identifies the solvable unknowns and the checks needed before substitution.",
        validation_checks=checks,
        result_summary="F = ma states that net force equals mass times acceleration. It can solve for F, m, or a when the other required quantities are known, provided the force is the net force in an applicable classical inertial-frame model.",
        safe_next_actions=(
            _action(analysis_id, "Ask for the known variables or a concrete physical scenario.", "operator-provided information", risk="low"),
        ),
        prohibited_actions=("Do not substitute an arbitrary individual force for net force.",),
        risk_class="safe_physics_modeling",
    )


def _record(
    source_record: Mapping[str, Any],
    frame: Mapping[str, Any],
    *,
    analysis_id: str,
    analysis_type: str,
    evidence_items: Sequence[EvidenceItem],
    extracted_facts: Sequence[str],
    selected_method: str,
    method_rationale: str,
    validation_checks: Sequence[ValidationCheck],
    result_summary: str,
    safe_next_actions: Sequence[SafeNextAction],
    prohibited_actions: Sequence[str],
    risk_class: str,
) -> EvidenceBoundAnalysisRecord:
    model = _mapping(source_record.get("problem_model"))
    equation = _mapping(source_record.get("equation_understanding_frame"))
    source_frame_id = str(source_record.get("frame_id") or frame.get("frame_id") or "")
    return EvidenceBoundAnalysisRecord(
        analysis_id=analysis_id,
        source_frame_id=source_frame_id,
        source_problem_model_id=str(model.get("problem_model_id") or ""),
        source_equation_frame_id=str(equation.get("equation_frame_id") or ""),
        source_turn_id=str(frame.get("source_turn_id") or ""),
        source_text=str(frame.get("source_text") or ""),
        domain=str(frame.get("domain_guess") or ""),
        analysis_type=analysis_type,
        evidence_items=tuple(evidence_items),
        extracted_facts=tuple(str(item) for item in extracted_facts if str(item)),
        assumptions=tuple(str(item) for item in model.get("assumptions", ()) if str(item)),
        constraints=tuple(str(item) for item in frame.get("constraints", ()) if str(item)),
        unknowns=tuple(str(item) for item in frame.get("uncertainty", ()) if str(item)),
        selected_method=selected_method,
        method_rationale=method_rationale,
        validation_checks=tuple(validation_checks),
        result_summary=result_summary,
        limitations=tuple(str(item) for item in frame.get("limitations", ()) if str(item)),
        uncertainty=tuple(str(item) for item in frame.get("uncertainty", ()) if str(item)),
        safe_next_actions=tuple(safe_next_actions),
        prohibited_actions=tuple(str(item) for item in prohibited_actions if str(item)),
        risk_class=risk_class,
        status="provisional_analysis",
        created_event_id=stable_id("evidence-bound-analysis-event", analysis_id, SCHEMA_VERSION),
        restart_summary="Deterministic source-frame analysis persisted by the conversational runtime with no graph, review, model, provider, tool, or external-action side effect.",
        semantic_signature=_mapping(frame.get("semantic_signature")),
        matched_roles=tuple(str(item) for item in frame.get("matched_roles", ()) if str(item)),
        missing_roles=tuple(str(item) for item in frame.get("missing_roles", ()) if str(item)),
        source_spans=tuple(
            dict(item)
            for item in frame.get("source_spans", ())
            if isinstance(item, Mapping)
        ),
        confidence_label=str(frame.get("confidence_label") or "deterministic_pattern_match"),
    )


def _analysis_id(record: Mapping[str, Any], analysis_type: str) -> str:
    frame = _frame(record)
    return stable_id(
        "evidence-bound-analysis",
        str(record.get("frame_id") or frame.get("frame_id") or ""),
        analysis_type,
        SCHEMA_VERSION,
    )


def _frame(record: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = record.get("semantic_input_frame")
    return candidate if isinstance(candidate, Mapping) else record


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _entity_label(frame: Mapping[str, Any], role: str, fallback: str) -> str:
    for item in frame.get("entities", ()):
        if isinstance(item, Mapping) and str(item.get("role") or "") == role:
            label = str(item.get("label") or item.get("entity") or "")
            if label:
                return label
    return fallback


def _quantity_value(frame: Mapping[str, Any], label: str) -> str:
    for item in frame.get("quantities", ()):
        if isinstance(item, Mapping) and str(item.get("label") or "") == label:
            return str(item.get("value") or "")
    return ""


def _quantity_text(frame: Mapping[str, Any], label: str, fallback: str) -> str:
    value = _quantity_value(frame, label)
    if not value:
        return fallback
    for item in frame.get("quantities", ()):
        if isinstance(item, Mapping) and str(item.get("label") or "") == label:
            unit = str(item.get("unit") or "").strip()
            return f"{value} {unit}".strip()
    return value


def _span(frame: Mapping[str, Any], *terms: str) -> Mapping[str, Any]:
    spans = tuple(item for item in frame.get("source_spans", ()) if isinstance(item, Mapping))
    normalized_terms = tuple(term.lower() for term in terms if term)
    for term in normalized_terms:
        for span in spans:
            if term in str(span.get("text") or "").lower():
                return dict(span)
    for item in frame.get("entities", ()):
        if isinstance(item, Mapping):
            span = item.get("source_span")
            if isinstance(span, Mapping) and any(term in str(span.get("text") or "").lower() for term in normalized_terms):
                return dict(span)
    for item in frame.get("quantities", ()):
        if isinstance(item, Mapping):
            span = item.get("source_span")
            if isinstance(span, Mapping) and any(term in str(span.get("text") or "").lower() for term in normalized_terms):
                return dict(span)
    source_text = str(frame.get("source_text") or "")
    lowered_source = source_text.lower()
    for term in normalized_terms:
        start = lowered_source.find(term)
        if start >= 0:
            end = start + len(term)
            return {
                "kind": "source_text",
                "text": source_text[start:end],
                "start": start,
                "end": end,
            }
    return {}


def _evidence(
    analysis_id: str,
    kind: str,
    text: str,
    frame: Mapping[str, Any],
    *terms: str,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=stable_id("evidence-bound-analysis-evidence", analysis_id, kind, text),
        kind=kind,
        text=text,
        source_span=_span(frame, *terms),
        role=kind,
        confidence_label="source_stated",
    )


def _check(
    analysis_id: str,
    check_id: str,
    description: str,
    expected_property: str,
    result: str,
    limitation: str,
) -> ValidationCheck:
    return ValidationCheck(
        check_id=stable_id("evidence-bound-analysis-check", analysis_id, check_id),
        description=description,
        expected_property=expected_property,
        result=result,
        limitation=limitation,
    )


def _action(
    analysis_id: str,
    action: str,
    required_authority: str,
    *,
    risk: str,
) -> SafeNextAction:
    return SafeNextAction(
        action_id=stable_id("evidence-bound-analysis-action", analysis_id, action),
        action=action,
        required_authority=required_authority,
        tool_required=False,
        external_action=False,
        reversible=True,
        risk=risk,
    )


def _incline_acceleration(angle: str) -> float | None:
    try:
        value = float(angle)
    except (TypeError, ValueError):
        return None
    if not 0 <= value <= 90:
        return None
    return 9.8 * math.sin(math.radians(value))


def _is_thirty_degrees(angle: str) -> bool:
    try:
        return abs(float(angle) - 30.0) < 0.001
    except (TypeError, ValueError):
        return False


def _portfolio_allocations(frame: Mapping[str, Any]) -> tuple[tuple[float, str], ...]:
    values: list[tuple[float, str]] = []
    for relation in frame.get("relationships", ()):
        if not isinstance(relation, Mapping) or relation.get("predicate") != "has_portfolio_weight":
            continue
        weight_match = re.search(r"\d+(?:\.\d+)?", str(relation.get("object") or ""))
        if weight_match is None:
            continue
        values.append((float(weight_match.group(0)), str(relation.get("subject") or "portfolio exposure")))
    return tuple(values)


def _bullet_lines(values: Sequence[str]) -> tuple[str, ...]:
    material = tuple(value for value in values if value)
    return tuple(f"- {value}" for value in material) or ("- No source-bound detail was recorded.",)


__all__ = [
    "EvidenceBoundAnalysisRecord",
    "AdaptiveRouteArbitration",
    "AdaptivePreconditionSelection",
    "EvidenceAnalysisRevisionCandidate",
    "EvidenceExecutionAuthorityRecord",
    "EvidenceFixtureDryRunResult",
    "EvidenceFixtureExecutionPlan",
    "EvidenceMinimalFixtureResult",
    "EvidenceNextOperationProposal",
    "EvidencePermissionRequest",
    "EvidenceResultIngestionCandidate",
    "EvidenceItem",
    "LongHorizonSelfCorrectionCandidate",
    "LongHorizonCorrectionEffect",
    "LongHorizonCorrectionEffectConsolidation",
    "EVIDENCE_EXECUTION_AUTHORITY_SCHEMA_VERSION",
    "EVIDENCE_ANALYSIS_REVISION_CANDIDATE_SCHEMA_VERSION",
    "EVIDENCE_FIXTURE_DRY_RUN_SCHEMA_VERSION",
    "EVIDENCE_FIXTURE_EXECUTION_PLAN_SCHEMA_VERSION",
    "EVIDENCE_MINIMAL_FIXTURE_RESULT_SCHEMA_VERSION",
    "EVIDENCE_NEXT_OPERATION_SCHEMA_VERSION",
    "EVIDENCE_PERMISSION_SCHEMA_VERSION",
    "EVIDENCE_RESULT_INGESTION_CANDIDATE_SCHEMA_VERSION",
    "INTERNAL_WORK_SCHEMA_VERSION",
    "InternalWorkCandidate",
    "SafeNextAction",
    "SCHEMA_VERSION",
    "ValidationCheck",
    "classify_evidence_execution_authority_operator_response",
    "classify_evidence_fixture_execution_plan_operator_response",
    "classify_evidence_next_operation_operator_response",
    "classify_evidence_permission_operator_response",
    "compile_analysis_revision_internal_work_candidates",
    "compile_controlled_fixture_analysis_refinement",
    "compile_evidence_analysis_revision_candidates",
    "compile_evidence_bound_analysis",
    "compile_evidence_execution_authority_records",
    "compile_evidence_fixture_dry_run_results",
    "compile_evidence_fixture_execution_plans",
    "compile_evidence_minimal_fixture_results",
    "compile_evidence_next_operation_proposals",
    "compile_evidence_permission_requests",
    "compile_adaptive_route_arbitration",
    "compile_adaptive_precondition_selection",
    "compile_evidence_result_ingestion_candidates",
    "compile_internal_work_candidates",
    "compile_long_horizon_self_correction_candidates",
    "compile_long_horizon_correction_effects",
    "compile_long_horizon_correction_effect_consolidation",
    "classify_internal_work_operator_response",
    "render_evidence_analysis_revision_candidate",
    "render_evidence_authorization",
    "render_evidence_bound_analysis",
    "render_evidence_bound_analysis_recall",
    "render_evidence_execution_authority_record",
    "render_evidence_execution_authority_request",
    "render_evidence_fixture_dry_run_result",
    "render_evidence_fixture_execution_plan",
    "render_evidence_fixture_execution_plan_update",
    "render_evidence_minimal_fixture_result",
    "render_evidence_next_operation_disposition",
    "render_evidence_next_operation_proposal",
    "render_evidence_next_operation_recall",
    "render_evidence_result_ingestion_candidate",
    "render_evidence_permission_recall",
    "render_evidence_permission_request",
    "render_controlled_fixture_analysis_refinement",
    "render_internal_work_disposition",
    "render_internal_work_proposal",
    "render_internal_work_recall",
    "select_internal_work_candidates",
]
