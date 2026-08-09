"""Deterministic, source-bound analysis records built from semantic problem frames.

This module deliberately has no persistence, graph, review, model, provider,
tool, authority, scheduling, or background-work dependency.  It only turns an
already-recorded semantic frame into a bounded, provisional analysis record.
The conversational runtime owns storage, turns, rendering coordination, and
exact-once behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id


SCHEMA_VERSION = "evidence_bound_analysis_v1"
QUESTION_LOOP_SCHEMA_VERSION = "evidence_bound_operator_question_v1"
INTERNAL_WORK_SCHEMA_VERSION = "evidence_bound_internal_work_v1"
EVIDENCE_PERMISSION_SCHEMA_VERSION = "evidence_bound_evidence_permission_v1"


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
    "EvidencePermissionRequest",
    "EvidenceItem",
    "EVIDENCE_PERMISSION_SCHEMA_VERSION",
    "INTERNAL_WORK_SCHEMA_VERSION",
    "InternalWorkCandidate",
    "SafeNextAction",
    "SCHEMA_VERSION",
    "ValidationCheck",
    "classify_evidence_permission_operator_response",
    "compile_evidence_bound_analysis",
    "compile_evidence_permission_requests",
    "compile_internal_work_candidates",
    "classify_internal_work_operator_response",
    "render_evidence_authorization",
    "render_evidence_bound_analysis",
    "render_evidence_bound_analysis_recall",
    "render_evidence_permission_recall",
    "render_evidence_permission_request",
    "render_internal_work_disposition",
    "render_internal_work_proposal",
    "render_internal_work_recall",
    "select_internal_work_candidates",
]
