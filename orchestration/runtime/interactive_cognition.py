"""Read-only coordination primitives for DELTA's interactive cognition.

This module intentionally does not own conversation, goals, requests, model
execution, or semantic knowledge.  It presents bounded references to those
canonical owners, then makes a deterministic, advisory attention decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from orchestration.runtime.active_cognitive_loop import ActiveCognitiveEpisodeState
from orchestration.runtime.conversational_runtime_operation import ConversationalRuntimeState
from orchestration.runtime.consolidation_feedback import derive_consolidation_feedback
from orchestration.runtime.provisional_semantic_consolidation import ProvisionalSemanticGraphState


SCHEMA_VERSION = "interactive_cognition_v1"
THREAD_KINDS = (
    "foreground_conversation",
    "active_goal",
    "local_inquiry",
    "pending_operator_question",
    "pending_authority_request",
    "provisional_hypothesis",
    "consolidation_cluster",
    "contradiction_review",
    "near_association",
    "far_analogy",
    "curiosity_candidate",
    "paused_goal",
    "developmental_objective",
    "runtime_health_issue",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canonical(value).encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}-{sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class AttentionInputs:
    """Explicit inputs.  Values are bounded integers, not a learned score."""

    direct_operator_obligation: int = 0
    foreground_binding: int = 0
    authority_boundary: int = 0
    conversational_relevance: int = 0
    goal_importance: int = 0
    epistemic_instability: int = 0
    contradiction_severity: int = 0
    novelty: int = 0
    expected_information_gain: int = 0
    recency: int = 0
    starvation: int = 0
    interruption_cost: int = 0
    resource_cost: int = 0
    consolidation_urgency: int = 0
    association_strength: int = 0
    operator_interest_alignment: int = 0
    safety_priority: int = 0
    runtime_health_priority: int = 0

    def as_record(self) -> dict[str, int]:
        return {key: int(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class CognitiveThread:
    """A reference into a canonical subsystem, never a copied owner payload."""

    thread_id: str
    thread_kind: str
    canonical_owner: str
    source_record_ids: tuple[str, ...]
    status: str
    focus: str
    originating_reference: str
    created_at: str
    last_activity_at: str
    interruptibility: str
    authority_requirement: str
    resource_requirements: tuple[str, ...]
    resume_cursor_ref: str
    expiry_policy: str
    operator_visibility: str
    dependency_refs: tuple[str, ...]
    semantic_refs: tuple[str, ...]
    epistemic_status: str
    inclusion_reason: str
    attention: AttentionInputs = field(default_factory=AttentionInputs)
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class CoordinationMetadata:
    """The only durable state owned by the coordination layer."""

    thread_id: str
    defer_until_sequence: int = 0
    suppressed: bool = False
    last_surfaced_sequence: int = 0
    starvation_count: int = 0
    preemption_requested: bool = False
    preemption_operation_id: str = ""
    preemption_candidate_id: str = ""
    preemption_ledger_request_id: str = ""
    preemption_foreground_turn_id: str = ""
    preemption_reason: str = ""
    operator_pause_policy: str = ""
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class CandidateDisposition:
    """Durable scheduling state for a derived candidate, not a memory record."""

    candidate_id: str
    candidate_kind: str
    state: str
    source_record_ids: tuple[str, ...]
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION


_CANDIDATE_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "generated": frozenset({"queued", "surfaced", "deferred", "rejected", "expired", "suppressed"}),
    "queued": frozenset({"surfaced", "deferred", "rejected", "expired", "suppressed"}),
    "surfaced": frozenset({"accepted", "deferred", "rejected", "expired", "resolved", "suppressed"}),
    "accepted": frozenset({"approved_for_bounded_exploration", "approved_for_revisit", "rejected", "resolved", "expired", "suppressed"}),
    "approved_for_bounded_exploration": frozenset({"exploration_queued", "rejected", "resolved", "expired", "suppressed"}),
    "exploration_queued": frozenset({"exploration_running", "exploration_failed", "exploration_blocked"}),
    "exploration_running": frozenset({"explored_pending_consolidation", "exploration_retryable", "exploration_failed", "exploration_blocked", "exploration_interrupted_indeterminate"}),
    "exploration_retryable": frozenset({"exploration_queued", "exploration_blocked", "exploration_failed"}),
    "explored_pending_consolidation": frozenset(),
    "exploration_blocked": frozenset(),
    "exploration_failed": frozenset(),
    "exploration_interrupted_indeterminate": frozenset(),
    "approved_for_revisit": frozenset({"revisit_queued", "revisit_rejected", "revisit_suppressed", "revisit_deferred"}),
    "revisit_queued": frozenset({"revisit_running", "revisit_failed_execution", "revisit_blocked_invalid_output"}),
    "revisit_running": frozenset({"revisited_pending_consolidation", "revisit_interrupted_indeterminate", "revisit_failed_execution", "revisit_blocked_invalid_output"}),
    "revisited_pending_consolidation": frozenset(),
    "revisit_rejected": frozenset(),
    "revisit_suppressed": frozenset(),
    "revisit_deferred": frozenset(),
    "revisit_blocked_invalid_output": frozenset(),
    "revisit_interrupted_indeterminate": frozenset(),
    "revisit_failed_execution": frozenset(),
    "deferred": frozenset({"queued", "surfaced", "rejected", "expired", "suppressed"}),
    "rejected": frozenset(),
    "expired": frozenset(),
    "resolved": frozenset(),
    "suppressed": frozenset(),
}


@dataclass(frozen=True)
class CoordinationState:
    runtime_id: str
    entries: tuple[CoordinationMetadata, ...] = ()
    decision_history: tuple[Mapping[str, Any], ...] = ()
    candidate_dispositions: tuple[CandidateDisposition, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class CognitiveWorkspaceSnapshot:
    snapshot_id: str
    snapshot_digest: str
    runtime_id: str
    lifecycle_state: str
    foreground_message: str
    foreground_turn_id: str
    active_objective_id: str
    active_episode_id: str
    graph_id: str
    threads: tuple[CognitiveThread, ...]
    question_candidates: tuple["QuestionCandidate", ...]
    association_candidates: tuple["AssociationCandidate", ...]
    curiosity_candidates: tuple["CuriosityCandidate", ...]
    source_digests: Mapping[str, str]
    ui_visibility: Mapping[str, Any]
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class AttentionDecisionRecord:
    decision_id: str
    snapshot_digest: str
    selected_posture: str
    target_thread_id: str
    target_owner: str
    reason_codes: tuple[str, ...]
    rejected_competitors: tuple[Mapping[str, str], ...]
    urgency: str
    maximum_step_budget: int
    preemption_policy: str
    operator_visibility: str
    required_authority: str
    expected_completion_boundary: str
    decision_stage: str = "shadow"
    shadow_mode: bool = True
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class QuestionCandidate:
    """A typed view of an existing request, never a second prompt owner."""

    question_id: str
    question_class: str
    originating_thread_id: str
    canonical_owner: str
    source_record_ids: tuple[str, ...]
    target_operator_role: str
    purpose: str
    expected_information_gain: int
    urgency: str
    expiry_policy: str
    safe_independent_work_may_continue: bool
    dependency_refs: tuple[str, ...]
    operator_visible_wording: str
    accepted_response_types: tuple[str, ...]
    answer_binding_contract: str
    status: str
    surface_in_chat: bool
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class AssociationCandidate:
    """A read-only proposal grounded in a concrete graph path."""

    association_id: str
    association_type: str
    source_refs: tuple[str, ...]
    target_refs: tuple[str, ...]
    relation_path: tuple[str, ...]
    shared_structure: str
    strength: int
    uncertainty: str
    operator_relevance: int
    proposed_question: str
    provenance_refs: tuple[str, ...]
    surface_worthy: bool
    state: str = "generated"
    schema_version: str = SCHEMA_VERSION

    @property
    def candidate_id(self) -> str:
        """Expose the common candidate identity without changing association records."""

        return self.association_id

    def as_record(self) -> dict[str, Any]:
        record = _jsonable(asdict(self))
        record["candidate_id"] = self.candidate_id
        return record


@dataclass(frozen=True)
class CuriosityCandidate:
    """A governed revisit pressure derived from unresolved epistemic state."""

    candidate_id: str
    trigger: str
    source_record_ids: tuple[str, ...]
    canonical_owner: str
    rationale: str
    safe_next_step: str
    operator_relevance: int
    surface_worthy: bool
    expiry_policy: str
    state: str = "generated"
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


def coordination_path(runtime_root: str | Path) -> Path:
    return Path(runtime_root) / "interactive-cognition" / "coordination_state.json"


def load_coordination_state(runtime_root: str | Path, *, runtime_id: str) -> CoordinationState:
    path = coordination_path(runtime_root)
    if not path.exists():
        return CoordinationState(runtime_id=runtime_id)
    record = json.loads(path.read_text(encoding="utf-8"))
    entries = tuple(
        CoordinationMetadata(
            thread_id=str(item.get("thread_id") or ""),
            defer_until_sequence=int(item.get("defer_until_sequence") or 0),
            suppressed=bool(item.get("suppressed")),
            last_surfaced_sequence=int(item.get("last_surfaced_sequence") or 0),
            starvation_count=int(item.get("starvation_count") or 0),
            preemption_requested=bool(item.get("preemption_requested")),
            preemption_operation_id=str(item.get("preemption_operation_id") or ""),
            preemption_candidate_id=str(item.get("preemption_candidate_id") or ""),
            preemption_ledger_request_id=str(item.get("preemption_ledger_request_id") or ""),
            preemption_foreground_turn_id=str(item.get("preemption_foreground_turn_id") or ""),
            preemption_reason=str(item.get("preemption_reason") or ""),
            operator_pause_policy=str(item.get("operator_pause_policy") or ""),
            updated_at=str(item.get("updated_at") or ""),
        )
        for item in record.get("entries", ())
        if isinstance(item, Mapping) and item.get("thread_id")
    )
    decisions = tuple(
        _jsonable(dict(item))
        for item in record.get("decision_history", ())
        if isinstance(item, Mapping) and item.get("decision_id")
    )
    dispositions = tuple(
        CandidateDisposition(
            candidate_id=str(item.get("candidate_id") or ""),
            candidate_kind=str(item.get("candidate_kind") or ""),
            state=str(item.get("state") or "generated"),
            source_record_ids=tuple(str(ref) for ref in item.get("source_record_ids", ()) if str(ref)),
            updated_at=str(item.get("updated_at") or ""),
        )
        for item in record.get("candidate_dispositions", ())
        if isinstance(item, Mapping) and item.get("candidate_id")
    )
    return CoordinationState(
        runtime_id=str(record.get("runtime_id") or runtime_id),
        entries=entries,
        decision_history=decisions,
        candidate_dispositions=dispositions,
    )


def save_coordination_state(runtime_root: str | Path, state: CoordinationState) -> None:
    path = coordination_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(_canonical(state.as_record()) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def record_shadow_decision(
    state: CoordinationState,
    decision: AttentionDecisionRecord,
    *,
    limit: int = 96,
) -> CoordinationState:
    """Persist bounded audit evidence without changing any canonical owner."""

    existing = tuple(item for item in state.decision_history if item.get("decision_id") != decision.decision_id)
    return CoordinationState(
        runtime_id=state.runtime_id,
        entries=state.entries,
        decision_history=(existing + (decision.as_record(),))[-max(1, int(limit)):],
        candidate_dispositions=state.candidate_dispositions,
    )


def stage_attention_decision(
    decision: AttentionDecisionRecord,
    *,
    stage: str,
) -> AttentionDecisionRecord:
    """Create an auditable active-control record from an advisory decision."""

    normalized = str(stage or "shadow").strip() or "shadow"
    return replace(
        decision,
        decision_id=_stable_id("attention-decision-stage", decision.decision_id, normalized),
        decision_stage=normalized,
        shadow_mode=normalized == "shadow",
    )


def request_preemption(
    state: CoordinationState,
    *,
    thread_id: str,
    operation_id: str = "",
    candidate_id: str = "",
    ledger_request_id: str = "",
    foreground_turn_id: str = "",
    reason: str = "",
    updated_at: str = "",
) -> CoordinationState:
    """Record a foreground interruption for observation at an existing safe boundary."""

    if not thread_id:
        return state
    entries = {item.thread_id: item for item in state.entries}
    prior = entries.get(thread_id, CoordinationMetadata(thread_id=thread_id))
    entries[thread_id] = replace(prior, preemption_requested=True, preemption_operation_id=operation_id or prior.preemption_operation_id, preemption_candidate_id=candidate_id or prior.preemption_candidate_id, preemption_ledger_request_id=ledger_request_id or prior.preemption_ledger_request_id, preemption_foreground_turn_id=foreground_turn_id or prior.preemption_foreground_turn_id, preemption_reason=reason or prior.preemption_reason, updated_at=updated_at or prior.updated_at)
    return CoordinationState(
        runtime_id=state.runtime_id,
        entries=tuple(entries[key] for key in sorted(entries)),
        decision_history=state.decision_history,
        candidate_dispositions=state.candidate_dispositions,
    )


def clear_preemption(
    state: CoordinationState,
    *,
    thread_id: str,
    updated_at: str = "",
) -> CoordinationState:
    """Clear an observed interruption without touching the canonical owner."""

    if not thread_id:
        return state
    entries = {item.thread_id: item for item in state.entries}
    prior = entries.get(thread_id)
    if prior is None or not prior.preemption_requested:
        return state
    entries[thread_id] = replace(prior, preemption_requested=False, updated_at=updated_at or prior.updated_at)
    return CoordinationState(
        runtime_id=state.runtime_id,
        entries=tuple(entries[key] for key in sorted(entries)),
        decision_history=state.decision_history,
        candidate_dispositions=state.candidate_dispositions,
    )


def set_candidate_disposition(
    state: CoordinationState,
    *,
    candidate_id: str,
    candidate_kind: str,
    disposition: str,
    source_record_ids: Sequence[str],
    updated_at: str = "",
) -> CoordinationState:
    """Persist an operator or scheduler disposition without persisting the candidate as memory."""

    normalized = str(disposition or "").strip()
    if not candidate_id or normalized not in _CANDIDATE_TRANSITIONS:
        raise ValueError("candidate disposition must name a candidate and an allowed lifecycle state")
    dispositions = {item.candidate_id: item for item in state.candidate_dispositions}
    prior = dispositions.get(candidate_id)
    prior_state = prior.state if prior else "generated"
    if prior is not None and prior.candidate_kind != str(candidate_kind or "derived_candidate"):
        raise ValueError("candidate disposition cannot change candidate kind")
    if normalized != prior_state and normalized not in _CANDIDATE_TRANSITIONS.get(prior_state, frozenset()):
        raise ValueError(f"candidate disposition cannot transition from {prior_state} to {normalized}")
    dispositions[candidate_id] = CandidateDisposition(
        candidate_id=candidate_id,
        candidate_kind=prior.candidate_kind if prior else str(candidate_kind or "derived_candidate"),
        state=normalized,
        source_record_ids=tuple(str(item) for item in source_record_ids if str(item)),
        updated_at=updated_at,
    )
    return CoordinationState(
        runtime_id=state.runtime_id,
        entries=state.entries,
        decision_history=state.decision_history,
        candidate_dispositions=tuple(dispositions[key] for key in sorted(dispositions)),
    )


def surface_candidate_once(
    state: CoordinationState,
    *,
    candidate_id: str,
    candidate_kind: str,
    source_record_ids: Sequence[str],
) -> CoordinationState:
    """Advance a generated or queued derived candidate to one observable surface."""

    existing = next((item for item in state.candidate_dispositions if item.candidate_id == candidate_id), None)
    if existing is not None and existing.state not in {"generated", "queued"}:
        return state
    return set_candidate_disposition(
        state,
        candidate_id=candidate_id,
        candidate_kind=candidate_kind,
        disposition="surfaced",
        source_record_ids=source_record_ids,
    )


def build_workspace_snapshot(
    state: ConversationalRuntimeState,
    *,
    episode: ActiveCognitiveEpisodeState | None = None,
    graph: ProvisionalSemanticGraphState | None = None,
    coordination: CoordinationState | None = None,
    foreground_message: str = "",
    foreground_turn_id: str = "",
    ui_visibility: Mapping[str, Any] | None = None,
    model_request_summaries: Sequence[Mapping[str, Any]] = (),
    runtime_health: Sequence[Mapping[str, Any]] = (),
) -> CognitiveWorkspaceSnapshot:
    """Build a bounded, immutable view without mutating any input owner."""

    metadata = {item.thread_id: item for item in (coordination.entries if coordination else ())}
    threads: list[CognitiveThread] = []
    if foreground_message.strip():
        threads.append(_thread(
            "foreground_conversation", "conversational_runtime", (foreground_turn_id or _digest(foreground_message),),
            status="awaiting_response", focus=foreground_message.strip(), originating_reference=foreground_turn_id,
            created_at="", last_activity_at="", interruptibility="not_applicable", authority_requirement="none",
            resource_requirements=(), resume_cursor_ref="", expiry_policy="consumed_when_response_persisted",
            operator_visibility="conversation", dependency_refs=(), semantic_refs=(), epistemic_status="operator_statement",
            inclusion_reason="unanswered_foreground_operator_message",
            attention=AttentionInputs(direct_operator_obligation=3, foreground_binding=3, conversational_relevance=3, recency=3),
        ))
    if state.active_objective:
        objective = state.active_objective
        is_paused = state.lifecycle_state.startswith("paused") or objective.lifecycle_state == "paused"
        threads.append(_thread(
            "paused_goal" if is_paused else "active_goal", "conversational_runtime", (objective.objective_id,),
            status="paused" if is_paused else "ready", focus=objective.interpreted_objective,
            originating_reference=objective.objective_id, created_at="", last_activity_at="", interruptibility=objective.interruption_policy,
            authority_requirement=objective.authority_boundary, resource_requirements=("local_model",) if objective.model_call_budget != 0 else (),
            resume_cursor_ref=state.active_episode_path, expiry_policy=objective.completion_or_review_condition,
            operator_visibility="observation", dependency_refs=(), semantic_refs=(), epistemic_status="operator_authorized_goal",
            inclusion_reason="active_conversational_objective",
            attention=AttentionInputs(goal_importance=3, recency=2, interruption_cost=1, operator_interest_alignment=3),
        ))
    for request in sorted(state.pending_chat_requests, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id)):
        if request.status != "pending" or request.consumption_count:
            continue
        kind = "pending_authority_request" if request.authority_impact or request.request_type in {"provider_authority", "knowledge_model_budget_increase"} else "pending_operator_question"
        threads.append(_thread(
            kind, "chat_addressable_request", (request.request_id,), status="pending", focus=request.prompt_text,
            originating_reference=request.created_turn_id, created_at=request.created_at, last_activity_at=request.created_at,
            interruptibility="wait_for_operator", authority_requirement=request.authority_impact or "operator_response_required",
            resource_requirements=(), resume_cursor_ref=request.request_id, expiry_policy="request_resolution_or_expiration",
            operator_visibility="conversation", dependency_refs=(request.objective_id,) if request.objective_id else (), semantic_refs=(),
            epistemic_status="pending_operator_response", inclusion_reason="durable_chat_addressable_request",
            attention=AttentionInputs(authority_boundary=3 if kind == "pending_authority_request" else 1, conversational_relevance=2, recency=2),
        ))
    if episode:
        _add_episode_threads(threads, episode, state.active_objective.objective_id if state.active_objective else "")
    if graph:
        _add_graph_threads(threads, graph)
    for summary in model_request_summaries[:8]:
        request_id = str(summary.get("request_id") or "")
        if not request_id:
            continue
        lifecycle = str(summary.get("lifecycle_state") or "")
        if lifecycle not in {"executing", "approved", "pending_operator_approval"}:
            continue
        threads.append(_thread(
            "local_inquiry", "local_model_request_result_ledger", (request_id,), status=lifecycle,
            focus=str(summary.get("question_objective") or summary.get("question") or "local inquiry"),
            originating_reference=str(summary.get("mission_id") or ""), created_at=str(summary.get("created_at") or ""),
            last_activity_at=str(summary.get("claimed_at") or summary.get("approved_at") or ""),
            interruptibility="atomic_model_request" if lifecycle == "executing" else "before_execution",
            authority_requirement=str(summary.get("authority_state") or "operator_approval_required"), resource_requirements=("local_model",),
            resume_cursor_ref=request_id, expiry_policy="terminal_ledger_state", operator_visibility="observation",
            dependency_refs=(), semantic_refs=(), epistemic_status="inquiry_in_progress", inclusion_reason="active_local_model_ledger_request",
            attention=AttentionInputs(resource_cost=2, interruption_cost=3 if lifecycle == "executing" else 1, recency=2),
        ))
    for item in runtime_health[:8]:
        health_id = str(item.get("health_id") or item.get("event_id") or _digest(item))
        severity = 3 if str(item.get("severity") or "").lower() in {"high", "critical", "error"} else 1
        threads.append(_thread(
            "runtime_health_issue", "runtime_health", (health_id,), status=str(item.get("status") or "open"),
            focus=str(item.get("summary") or item.get("message") or "runtime health issue"), originating_reference=health_id,
            created_at=str(item.get("created_at") or ""), last_activity_at=str(item.get("updated_at") or ""),
            interruptibility="not_applicable", authority_requirement="none", resource_requirements=(), resume_cursor_ref="",
            expiry_policy="resolved_or_superseded", operator_visibility="observation", dependency_refs=(), semantic_refs=(),
            epistemic_status="runtime_observation", inclusion_reason="reported_runtime_health_event",
            attention=AttentionInputs(runtime_health_priority=severity, safety_priority=severity),
        ))
    threads = _apply_coordination_metadata(threads, metadata)
    dispositions = {item.candidate_id: item for item in (coordination.candidate_dispositions if coordination else ())}
    associations = _apply_candidate_dispositions(_derive_near_association_candidates(graph), dispositions)
    curiosity = _apply_candidate_dispositions(
        _derive_curiosity_candidates(graph) + _derive_cognitive_pressure_candidates(episode),
        dispositions,
    )
    for association in associations:
        threads.append(_thread(
            "near_association", "provisional_semantic_graph", association.provenance_refs,
            status=association.state, focus=association.shared_structure, originating_reference=association.association_id,
            created_at="", last_activity_at="", interruptibility="next_cycle_boundary", authority_requirement="none",
            resource_requirements=(), resume_cursor_ref=association.association_id, expiry_policy="superseded_by_graph_change",
            operator_visibility="observation", dependency_refs=association.source_refs + association.target_refs,
            semantic_refs=association.source_refs + association.target_refs, epistemic_status="provisional_association",
            inclusion_reason="explicit_provisional_graph_dependency_path",
            attention=AttentionInputs(
                authority_boundary=2 if association.state == "approved_for_bounded_exploration" else 0,
                association_strength=association.strength,
                expected_information_gain=3 if association.state == "approved_for_bounded_exploration" else 1,
                operator_interest_alignment=3 if association.state == "approved_for_bounded_exploration" else association.operator_relevance,
            ),
        ))
    for candidate in curiosity:
        threads.append(_thread(
            "curiosity_candidate", candidate.canonical_owner, candidate.source_record_ids,
            status=candidate.state, focus=candidate.rationale, originating_reference=candidate.candidate_id,
            created_at="", last_activity_at="", interruptibility="next_cycle_boundary", authority_requirement="none",
            resource_requirements=(), resume_cursor_ref=candidate.candidate_id, expiry_policy=candidate.expiry_policy,
            operator_visibility="observation", dependency_refs=candidate.source_record_ids,
            semantic_refs=candidate.source_record_ids, epistemic_status="revisit_candidate",
            inclusion_reason="epistemic_instability_requires_governed_revisit",
            attention=AttentionInputs(
                contradiction_severity=3 if candidate.trigger == "contradiction" else 0,
                epistemic_instability=2,
                expected_information_gain=2,
                operator_interest_alignment=candidate.operator_relevance,
            ),
        ))
    threads = sorted(threads, key=lambda item: (item.thread_kind, item.created_at, item.thread_id))
    questions = _derive_question_candidates(state, threads)
    sources = {
        "conversational_runtime": _digest(state.as_record()),
        "active_episode": _digest(episode.as_record()) if episode else "",
        "provisional_graph": _digest(graph.as_record()) if graph else "",
        # Decision history is audit output, not workspace input. Including it here
        # would make every observation create a different successor snapshot.
        "coordination": _digest({
            "runtime_id": coordination.runtime_id,
            "entries": [_jsonable(asdict(item)) for item in coordination.entries],
            "candidate_dispositions": [_jsonable(asdict(item)) for item in coordination.candidate_dispositions],
        }) if coordination else "",
    }
    payload = {
        "runtime_id": state.runtime_id,
        "lifecycle_state": state.lifecycle_state,
        "foreground_message": foreground_message.strip(),
        "foreground_turn_id": foreground_turn_id,
        "active_objective_id": state.active_objective.objective_id if state.active_objective else "",
        "active_episode_id": episode.episode_id if episode else "",
        "graph_id": graph.graph_id if graph else "",
        "threads": [item.as_record() for item in threads],
        "question_candidates": [item.as_record() for item in questions],
        "association_candidates": [item.as_record() for item in associations],
        "curiosity_candidates": [item.as_record() for item in curiosity],
        "source_digests": sources,
        "ui_visibility": _jsonable(dict(ui_visibility or {})),
    }
    digest = _digest(payload)
    return CognitiveWorkspaceSnapshot(
        snapshot_id=_stable_id("cognitive-workspace", state.runtime_id, digest), snapshot_digest=digest,
        runtime_id=state.runtime_id, lifecycle_state=state.lifecycle_state, foreground_message=foreground_message.strip(),
        foreground_turn_id=foreground_turn_id, active_objective_id=payload["active_objective_id"], active_episode_id=payload["active_episode_id"],
        graph_id=payload["graph_id"], threads=tuple(threads), question_candidates=questions,
        association_candidates=associations, curiosity_candidates=curiosity,
        source_digests=sources, ui_visibility=_jsonable(dict(ui_visibility or {})),
    )


def _derive_question_candidates(
    state: ConversationalRuntimeState,
    threads: Sequence[CognitiveThread],
) -> tuple[QuestionCandidate, ...]:
    """Expose pending request semantics without creating another question queue."""

    thread_by_request = {
        item.source_record_ids[0]: item
        for item in threads
        if item.canonical_owner == "chat_addressable_request" and item.source_record_ids
    }
    candidates: list[QuestionCandidate] = []
    for request in sorted(state.pending_chat_requests, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id)):
        if request.status != "pending" or request.consumption_count:
            continue
        thread = thread_by_request.get(request.request_id)
        if thread is None:
            continue
        question_class = _question_class_for_request(request.request_type, request.authority_impact)
        authority_bound = bool(request.authority_impact)
        candidates.append(QuestionCandidate(
            question_id=_stable_id("interactive-question", request.request_id, question_class),
            question_class=question_class,
            originating_thread_id=thread.thread_id,
            canonical_owner="chat_addressable_request",
            source_record_ids=(request.request_id,),
            target_operator_role="operator",
            purpose="Resolve the existing bounded request before dependent work proceeds.",
            expected_information_gain=3 if authority_bound else 2,
            urgency="high" if authority_bound else "normal",
            expiry_policy=thread.expiry_policy,
            safe_independent_work_may_continue=not authority_bound,
            dependency_refs=thread.dependency_refs,
            operator_visible_wording=request.prompt_text,
            accepted_response_types=tuple(request.accepted_response_types) or ("approved", "denied"),
            answer_binding_contract="resolve_only_the_matching_chat_addressable_request_once",
            status="pending",
            surface_in_chat=True,
        ))
    return tuple(candidates)


def _question_class_for_request(request_type: str, authority_impact: str) -> str:
    normalized = str(request_type or "")
    if authority_impact or normalized in {"knowledge_model_budget_increase", "provider_authority", "capability_adoption"}:
        return "authority"
    if "clarif" in normalized:
        return "clarification"
    if "provider" in normalized or "evidence" in normalized:
        return "missing-evidence"
    if "preference" in normalized:
        return "operator-preference"
    return "progress-choice"


def _derive_near_association_candidates(
    graph: ProvisionalSemanticGraphState | None,
) -> tuple[AssociationCandidate, ...]:
    """Use explicit graph dependencies only; lexical resemblance is not evidence."""

    if graph is None:
        return ()
    versions = {item.claim_version_id: item for item in graph.claim_versions}
    candidates: list[AssociationCandidate] = []
    for edge in graph.edges:
        if edge.edge_type != "depends_on":
            continue
        source = versions.get(edge.source_ref)
        target = versions.get(edge.target_ref)
        if source is None or target is None:
            continue
        source_text = source.exact_text[:180]
        target_text = target.exact_text[:180]
        candidates.append(AssociationCandidate(
            association_id=_stable_id("near-association", edge.edge_id),
            association_type="explicit_dependency",
            source_refs=(source.claim_version_id,),
            target_refs=(target.claim_version_id,),
            relation_path=(edge.edge_id,),
            shared_structure="A provisional claim depends on another provisional claim.",
            strength=2,
            uncertainty="The dependency establishes a review path, not a causal or factual equivalence.",
            operator_relevance=1,
            proposed_question=(
                f"Should DELTA revisit the dependency between '{source_text}' and '{target_text}'?"
            ),
            provenance_refs=(edge.edge_id, source.claim_version_id, target.claim_version_id),
            surface_worthy=False,
        ))
    return tuple(sorted(candidates, key=lambda item: item.association_id))


def _derive_curiosity_candidates(
    graph: ProvisionalSemanticGraphState | None,
) -> tuple[CuriosityCandidate, ...]:
    """Generate revisit pressure only from actual unresolved graph state."""

    if graph is None:
        return ()
    candidates = []
    for version in graph.claim_versions:
        if version.epistemic_state not in {"contradicted", "locally_contradicted", "unstable", "invalidated"}:
            continue
        trigger = "contradiction" if version.epistemic_state in {"contradicted", "locally_contradicted"} else "epistemic_instability"
        candidates.append(CuriosityCandidate(
            candidate_id=_stable_id("curiosity-revisit", version.claim_version_id, trigger),
            trigger=trigger,
            source_record_ids=(version.claim_version_id,),
            canonical_owner="provisional_semantic_graph",
            state="generated",
            rationale=f"Revisit the {version.epistemic_state} provisional claim through its existing review path.",
            safe_next_step="inspect_existing_provenance_or_wait_for_review",
            operator_relevance=1,
            surface_worthy=False,
            expiry_policy="retire_when_claim_is_resolved_or_superseded",
        ))
    for feedback in derive_consolidation_feedback(graph):
        if feedback.cognitive_consequence not in {
            "revisit_required",
            "high_priority_contradiction_review",
            "targeted_remaining_gap",
        }:
            continue
        trigger = {
            "revisit_required": "consolidation_correction",
            "high_priority_contradiction_review": "consolidation_contradiction",
            "targeted_remaining_gap": "consolidation_remaining_gap",
        }[feedback.cognitive_consequence]
        candidates.append(CuriosityCandidate(
            candidate_id=_stable_id("curiosity-review-feedback", feedback.feedback_id),
            trigger=trigger,
            source_record_ids=feedback.source_ids,
            canonical_owner="provisional_semantic_graph",
            rationale=f"Consolidation review {feedback.verdict}: {feedback.rationale}.",
            safe_next_step="ask_one_bounded_revision_or_contradiction_question",
            operator_relevance=3 if feedback.cognitive_consequence == "high_priority_contradiction_review" else 2,
            surface_worthy=False,
            expiry_policy="retire_when_reviewed_claim_is_superseded_or_operator_rejects",
        ))
    return tuple(sorted(candidates, key=lambda item: item.candidate_id))


def _derive_cognitive_pressure_candidates(
    episode: ActiveCognitiveEpisodeState | None,
) -> tuple[CuriosityCandidate, ...]:
    """Surface only explicit, bounded evidence gaps already declared by the live episode."""

    if episode is None:
        return ()
    candidates = []
    for result in episode.operation_results:
        if result.operation_result_type != "declare_insufficient_evidence_result":
            continue
        request = str(result.recommended_action or result.next_evidence_need or "").strip()
        if not request:
            continue
        candidates.append(CuriosityCandidate(
            candidate_id=_stable_id("missing-evidence-question", episode.episode_id, result.operation_id),
            trigger="missing_evidence",
            source_record_ids=(episode.episode_id, result.operation_id),
            canonical_owner="active_cognitive_episode",
            rationale=str(result.interpretation or "A bounded evidence gap blocked this local step."),
            safe_next_step=request,
            operator_relevance=2,
            surface_worthy=False,
            expiry_policy="retire_when_evidence_request_is_answered_or_episode_is_superseded",
        ))
    return tuple(sorted(candidates, key=lambda item: item.candidate_id))


def _apply_candidate_dispositions(
    candidates: Sequence[Any],
    dispositions: Mapping[str, CandidateDisposition],
) -> tuple[Any, ...]:
    return tuple(
        replace(candidate, state=dispositions[candidate.candidate_id].state)
        if candidate.candidate_id in dispositions
        else candidate
        for candidate in candidates
    )


def arbitrate_attention(snapshot: CognitiveWorkspaceSnapshot) -> AttentionDecisionRecord:
    """Select a posture without executing, authorizing, or mutating anything."""

    eligible = [
        thread for thread in snapshot.threads
        if thread.status not in {"completed", "accepted", "expired", "suppressed", "deferred", "rejected", "resolved", "explored_pending_consolidation", "exploration_blocked", "exploration_failed", "exploration_interrupted_indeterminate", "awaiting_administrative_review"}
    ]
    ranked = sorted(eligible, key=_priority_key)
    selected = ranked[0] if ranked else None
    posture = _posture_for(selected)
    competitors = tuple(
        {"thread_id": item.thread_id, "posture": _posture_for(item), "reason": _primary_reason(item)}
        for item in ranked[1:5]
    )
    if selected is None:
        return AttentionDecisionRecord(
            decision_id=_stable_id("attention-decision", snapshot.snapshot_digest, "idle"), snapshot_digest=snapshot.snapshot_digest,
            selected_posture="remain_idle", target_thread_id="", target_owner="", reason_codes=("no_eligible_thread",),
            rejected_competitors=(), urgency="none", maximum_step_budget=0, preemption_policy="none", operator_visibility="observation",
            required_authority="none", expected_completion_boundary="next_event",
        )
    return AttentionDecisionRecord(
        decision_id=_stable_id("attention-decision", snapshot.snapshot_digest, selected.thread_id, posture), snapshot_digest=snapshot.snapshot_digest,
        selected_posture=posture, target_thread_id=selected.thread_id, target_owner=selected.canonical_owner,
        reason_codes=_reason_codes(selected), rejected_competitors=competitors, urgency=_urgency(selected),
        maximum_step_budget=0 if posture in {"answer_operator", "ask_operator", "report_current_focus"} else 1,
        preemption_policy="wait_for_atomic_ledger_boundary" if selected.interruptibility == "atomic_model_request" else "preemptible_at_next_boundary",
        operator_visibility=selected.operator_visibility, required_authority=selected.authority_requirement,
        expected_completion_boundary="existing_owner_atomic_step" if posture == "continue_active_goal" else "response_or_next_event",
    )


def _add_episode_threads(threads: list[CognitiveThread], episode: ActiveCognitiveEpisodeState, objective_id: str) -> None:
    if episode.attention and episode.attention.active_focus_id:
        threads.append(_thread(
            "local_inquiry", "active_cognitive_episode", (episode.episode_id, episode.attention.active_focus_id),
            status=episode.loop_state, focus=episode.attention.active_focus_summary, originating_reference=objective_id,
            created_at=episode.attention.focus_started_at, last_activity_at=episode.attention.last_progress_at,
            interruptibility="atomic_model_request" if episode.loop_state == "executing" else "next_cycle_boundary",
            authority_requirement="none_for_local_analysis", resource_requirements=("local_model",),
            resume_cursor_ref=episode.attention.active_focus_id, expiry_policy="episode_terminal_state", operator_visibility="observation",
            dependency_refs=(objective_id,) if objective_id else (), semantic_refs=episode.attention.evidence_refs,
            epistemic_status="goal_local_focus", inclusion_reason="active_episode_attention_focus",
            attention=AttentionInputs(goal_importance=2, recency=2, interruption_cost=2),
        ))
    for hypothesis in episode.hypotheses[-8:]:
        if hypothesis.lifecycle_state not in {"active", "under_review"}:
            continue
        threads.append(_thread(
            "provisional_hypothesis", "active_cognitive_episode", (episode.episode_id, hypothesis.hypothesis_id),
            status=hypothesis.lifecycle_state, focus=hypothesis.statement, originating_reference=hypothesis.originating_goal_id,
            created_at=hypothesis.created_at, last_activity_at=hypothesis.revised_at or hypothesis.created_at,
            interruptibility="next_cycle_boundary", authority_requirement="none_for_local_analysis", resource_requirements=(),
            resume_cursor_ref=hypothesis.originating_focus_id, expiry_policy="hypothesis_disposition", operator_visibility="observation",
            dependency_refs=(hypothesis.originating_goal_id,), semantic_refs=hypothesis.evidence_for + hypothesis.evidence_against,
            epistemic_status=hypothesis.confidence_state, inclusion_reason="active_or_reviewable_goal_hypothesis",
            attention=AttentionInputs(epistemic_instability=2, expected_information_gain=1),
        ))


def _add_graph_threads(threads: list[CognitiveThread], graph: ProvisionalSemanticGraphState) -> None:
    for cohort in graph.cohorts[-4:]:
        packet = next((item for item in graph.packets if item.cohort_id == cohort.cohort_id), None)
        threads.append(_thread(
            "consolidation_cluster", "provisional_semantic_graph", (cohort.cohort_id,),
            status="awaiting_administrative_review" if packet else "ready_to_seal",
            focus=cohort.trigger, originating_reference=cohort.cohort_id, created_at=cohort.created_at, last_activity_at=cohort.created_at,
            interruptibility="atomic_graph_write", authority_requirement="administrative_review_required", resource_requirements=(),
            resume_cursor_ref=cohort.cohort_id, expiry_policy="packet_or_retirement", operator_visibility="observation",
            dependency_refs=cohort.claim_version_refs, semantic_refs=cohort.claim_version_refs,
            epistemic_status="pending_consolidation", inclusion_reason="active_consolidation_cohort",
            attention=AttentionInputs(consolidation_urgency=2, epistemic_instability=2),
        ))
    reviewed = {overlay.claim_version_id for overlay in graph.overlays}
    for version in graph.claim_versions[-12:]:
        if version.epistemic_state not in {"pending_consolidation", "provisional", "contradicted", "unstable"}:
            continue
        kind = "contradiction_review" if version.epistemic_state in {"contradicted", "unstable"} else "provisional_hypothesis"
        threads.append(_thread(
            kind, "provisional_semantic_graph", (version.claim_version_id,), status=version.epistemic_state,
            focus=version.exact_text, originating_reference=version.claim_id, created_at=version.created_at, last_activity_at=version.validation_timestamp or version.created_at,
            interruptibility="atomic_graph_write", authority_requirement="review_required" if version.claim_version_id not in reviewed else "administrative_overlay_present",
            resource_requirements=(), resume_cursor_ref=version.claim_version_id, expiry_policy="review_or_invalidation",
            operator_visibility="observation", dependency_refs=version.rationale_refs, semantic_refs=version.source_experience_refs,
            epistemic_status=version.epistemic_state, inclusion_reason="recent_unresolved_semantic_claim",
            attention=AttentionInputs(epistemic_instability=3 if kind == "contradiction_review" else 2, contradiction_severity=3 if kind == "contradiction_review" else 0),
        ))


def _thread(
    kind: str,
    owner: str,
    source_ids: Iterable[str],
    *,
    status: str,
    focus: str,
    originating_reference: str,
    created_at: str,
    last_activity_at: str,
    interruptibility: str,
    authority_requirement: str,
    resource_requirements: Iterable[str],
    resume_cursor_ref: str,
    expiry_policy: str,
    operator_visibility: str,
    dependency_refs: Iterable[str],
    semantic_refs: Iterable[str],
    epistemic_status: str,
    inclusion_reason: str,
    attention: AttentionInputs,
) -> CognitiveThread:
    ids = tuple(str(item) for item in source_ids if str(item))
    return CognitiveThread(
        thread_id=_stable_id("cognitive-thread", owner, kind, *ids), thread_kind=kind, canonical_owner=owner,
        source_record_ids=ids, status=status, focus=" ".join(str(focus or "").split())[:600], originating_reference=originating_reference,
        created_at=created_at, last_activity_at=last_activity_at, interruptibility=interruptibility,
        authority_requirement=authority_requirement, resource_requirements=tuple(resource_requirements), resume_cursor_ref=resume_cursor_ref,
        expiry_policy=expiry_policy, operator_visibility=operator_visibility, dependency_refs=tuple(str(item) for item in dependency_refs if str(item)),
        semantic_refs=tuple(str(item) for item in semantic_refs if str(item)), epistemic_status=epistemic_status,
        inclusion_reason=inclusion_reason, attention=attention,
    )


def _apply_coordination_metadata(threads: Sequence[CognitiveThread], metadata: Mapping[str, CoordinationMetadata]) -> list[CognitiveThread]:
    updated: list[CognitiveThread] = []
    for thread in threads:
        entry = metadata.get(thread.thread_id)
        if not entry:
            updated.append(thread)
            continue
        status = "suppressed" if entry.suppressed else thread.status
        attention = AttentionInputs(**{**thread.attention.as_record(), "starvation": max(thread.attention.starvation, entry.starvation_count)})
        updated.append(replace(thread, status=status, attention=attention))
    return updated


def _priority_key(thread: CognitiveThread) -> tuple[Any, ...]:
    item = thread.attention
    return (
        -item.direct_operator_obligation,
        -item.foreground_binding,
        -item.authority_boundary,
        -item.safety_priority,
        -item.runtime_health_priority,
        -item.conversational_relevance,
        -item.goal_importance,
        -item.contradiction_severity,
        -item.consolidation_urgency,
        -item.association_strength,
        -item.epistemic_instability,
        -item.expected_information_gain,
        -item.novelty,
        -item.operator_interest_alignment,
        -item.starvation,
        -item.recency,
        item.interruption_cost,
        item.resource_cost,
        thread.created_at or "~",
        thread.thread_id,
    )


def _posture_for(thread: CognitiveThread | None) -> str:
    if thread is None:
        return "remain_idle"
    if thread.thread_kind == "foreground_conversation":
        return "answer_operator"
    if thread.thread_kind in {"pending_operator_question", "pending_authority_request"}:
        return "ask_operator"
    if thread.thread_kind == "runtime_health_issue":
        return "surface_contradiction" if thread.attention.contradiction_severity else "report_current_focus"
    if thread.thread_kind == "contradiction_review":
        return "surface_contradiction"
    if thread.thread_kind in {"active_goal", "local_inquiry"} and thread.status not in {"paused", "blocked_operator_decision"}:
        return "continue_active_goal"
    if thread.thread_kind == "consolidation_cluster":
        return "perform_one_consolidation_step"
    if thread.thread_kind == "near_association":
        return "execute_approved_association" if thread.status in {"approved_for_bounded_exploration", "exploration_queued", "exploration_running"} else "explore_near_association"
    if thread.thread_kind == "far_analogy":
        return "explore_far_analogy"
    if thread.thread_kind == "curiosity_candidate":
        if thread.status in {"approved_for_revisit", "revisit_queued", "revisit_running"}:
            return "execute_approved_revisit"
        return "inspect_curiosity_candidate"
    return "report_current_focus"


def _reason_codes(thread: CognitiveThread) -> tuple[str, ...]:
    pairs = ((name, value) for name, value in thread.attention.as_record().items() if value)
    return tuple([thread.inclusion_reason, *(f"{name}={value}" for name, value in pairs)]) or ("eligible_thread",)


def _primary_reason(thread: CognitiveThread) -> str:
    return _reason_codes(thread)[0]


def _urgency(thread: CognitiveThread) -> str:
    maximum = max(thread.attention.as_record().values(), default=0)
    return "high" if maximum >= 3 else "normal" if maximum >= 2 else "low"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
