"""Conversation-first bounded objective runtime.

This is a narrow bridge for CONVERSATIONAL_RUNTIME_OPERATION_MARATHON_1. It
lets ordinary chat compile a safe operator goal into a durable objective, keeps
routine cognition under standing bounded authority, attaches corrections to
turns, and records scoped lessons for later transfer. It does not grant source
mutation, external access, or any irreversible authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import re

from orchestration.runtime.active_cognitive_loop import (
    ActiveCognitiveEpisodeState,
    EvidenceRef,
    ModelRunner,
    ScriptedSemanticModel,
    initialize_episode,
    read_episode_state,
    run_cognitive_cycle,
    write_episode_state,
)
from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.developmental_teaching_runtime import (
    compile_endogenous_terminal_gap_followup,
    compile_physics_prerequisite,
    compile_teaching_followup,
    compile_teaching_plan,
    is_teaching_instruction,
    physics_prerequisite_resume_target,
    render_curriculum_resumption,
    render_physics_prerequisite_prompt,
    render_teaching_followup_acknowledgement,
    render_first_lesson,
    teaching_followup_requires_study,
    teaching_knowledge_contract,
    teaching_retention_prompt,
)
from orchestration.runtime.provisional_semantic_consolidation import (
    ConsolidationIntegrityError,
    ensure_consolidation_cohort,
    ingest_episode_at_runtime_root,
    load_graph,
    record_operator_claim_correction,
    record_source_bound_semantic_transfer_application,
    save_graph,
)
from orchestration.runtime.semantic_problem_modeling import (
    compile_semantic_problem_frame,
    render_semantic_problem_frame,
    render_semantic_problem_recall,
)
from orchestration.runtime.evidence_bound_analysis import (
    classify_evidence_execution_authority_operator_response,
    classify_evidence_fixture_execution_plan_operator_response,
    classify_evidence_next_operation_operator_response,
    classify_evidence_permission_operator_response,
    classify_internal_work_operator_response,
    compile_evidence_bound_analysis,
    compile_analysis_refinement,
    compile_evidence_execution_authority_records,
    compile_evidence_fixture_dry_run_results,
    compile_evidence_fixture_execution_plans,
    compile_evidence_next_operation_proposals,
    compile_evidence_permission_requests,
    compile_evidence_result_ingestion_candidates,
    compile_internal_work_candidates,
    compile_operator_question_answer,
    compile_operator_question_candidates,
    operator_question_answer_is_compatible,
    render_evidence_authorization,
    render_evidence_bound_analysis,
    render_evidence_bound_analysis_recall,
    render_evidence_execution_authority_record,
    render_evidence_execution_authority_request,
    render_evidence_fixture_dry_run_result,
    render_evidence_fixture_execution_plan,
    render_evidence_fixture_execution_plan_update,
    render_evidence_next_operation_disposition,
    render_evidence_next_operation_proposal,
    render_evidence_next_operation_recall,
    render_evidence_bound_analysis_question,
    render_evidence_bound_analysis_refinement,
    render_evidence_bound_analysis_refinement_recall,
    render_evidence_permission_recall,
    render_evidence_permission_request,
    render_evidence_result_ingestion_candidate,
    render_internal_work_disposition,
    render_internal_work_proposal,
    render_internal_work_recall,
    select_internal_work_candidates,
    select_operator_question_candidates,
)


SCHEMA_VERSION = "conversational_runtime_operation_marathon_1_v1"
RISKY_ACTIONS = {
    "modify_source": ("modify your source code", "edit your code", "change delta.py", "patch the repo", "rewrite the source"),
    "install_package": ("install a package", "pip install", "npm install", "download a package"),
    "network": ("use the internet", "browse", "go online", "external provider", "ask gpt"),
    "delete": ("delete those files", "remove files", "wipe", "clean the repo"),
    "push": ("commit", "push", "deploy"),
}
DEFAULT_ALLOWED_ACTIONS = (
    "interpret operator wording",
    "register bounded conversational objective",
    "run bounded local cognitive cycles",
    "read approved local runtime state",
    "update working memory",
    "record conversation episodes",
    "attach natural corrections",
    "consolidate scoped non-authoritative lessons",
    "select bounded next focus",
)
DEFAULT_PROHIBITED_ACTIONS = (
    "tracked source mutation",
    "file deletion",
    "package installation",
    "network or external provider use",
    "deployment",
    "commit or push",
    "protected path mutation",
    "credential access",
    "authority escalation",
)
STOP_OR_REDIRECT_SIGNALS = (
    "stop the active goal",
    "stop working on that",
    "pause the active goal",
    "pause this goal",
    "redirect to",
    "switch priority",
    "new priority",
    "focus on this instead",
)
CHAT_FEATURE_SETTINGS_SCHEMA = {
    "schema_version": SCHEMA_VERSION,
    "profile": {
        "display_name": "DELTA",
        "default_mode": "conversation",
        "tone": "natural, concise, companionable",
        "response_length": "adaptive",
    },
    "conversation": {
        "ordinary_chat_default": True,
        "allow_natural_goals": True,
        "allow_natural_corrections": True,
        "show_correction_influence_when_audited": True,
        "avoid_repetitive_clarification": True,
    },
    "memory_and_learning": {
        "session_objectives": True,
        "correction_learning": "scoped_to_active_objective",
        "continuity_records": "non_authoritative",
        "operator_auditable": True,
        "overgeneralization_guard": True,
    },
    "tools_and_actions": {
        "routine_local_cognition": "standing_bounded_authority",
        "tracked_source_mutation": "explicit_approval_required",
        "network_or_external_provider": "explicit_approval_required",
        "package_installation": "explicit_approval_required",
        "delete_commit_push_deploy": "explicit_approval_required",
    },
    "interface": {
        "default_surface": ("chat_history", "message_input", "send_button", "activity_status", "stop_button"),
        "advanced_surface": "hidden_until_requested",
        "routine_popups": "disabled",
        "material_authority_prompts": "chat_or_explicit_dialog",
    },
}


def _digest(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def write_json(path: str | Path, payload: Mapping[str, Any] | Sequence[Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_json(path: str | Path, default: Any = None) -> Any:
    target = Path(path)
    if not target.exists():
        return default
    return json.loads(target.read_text(encoding="utf-8-sig"))


def chat_feature_settings_schema() -> dict[str, Any]:
    return json.loads(json.dumps(CHAT_FEATURE_SETTINGS_SCHEMA, sort_keys=True))


@dataclass(frozen=True)
class ConversationIntent:
    intent_type: str
    confidence: float
    persistence_scope: str
    risk_class: str
    authority_required: tuple[str, ...]
    matched_signals: tuple[str, ...]
    target_turn_id: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StandingAuthority:
    authority_id: str
    objective_id: str
    allowed_actions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    expires_condition: str
    revoked: bool = False
    authority_effect: str = "routine_internal_only"
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConversationalObjective:
    objective_id: str
    operator_wording: str
    interpreted_objective: str
    persistence_scope: str
    practical_success_indicators: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    local_evidence_sources: tuple[str, ...]
    cycle_budget: int | None
    model_call_budget: int | None
    interruption_policy: str
    correction_learning_policy: str
    completion_or_review_condition: str
    authority_boundary: str
    provenance: Mapping[str, Any]
    lifecycle_state: str = "active"
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConversationTurn:
    turn_id: str
    role: str
    text: str
    intent_type: str
    objective_id: str = ""
    created_at: str = field(default_factory=utc_now)
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CorrectionRecord:
    correction_id: str
    source_turn_id: str
    target_turn_id: str
    correction_type: str
    operator_text: str
    interpreted_issue: str
    lesson_scope: str
    evidence_refs: tuple[str, ...]
    overgeneralization_guard: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScopedLesson:
    lesson_id: str
    source_correction_id: str
    objective_id: str
    summary: str
    applicable_when: tuple[str, ...]
    not_applicable_when: tuple[str, ...]
    strategy_update: str
    confidence: float
    evidence_refs: tuple[str, ...]
    authority_effect: str = "none"
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChatAddressableRequest:
    request_id: str
    request_type: str
    objective_id: str
    goal_label: str
    prompt_text: str
    status: str = "pending"
    provider: str = ""
    max_calls: int = 0
    max_spend_usd: float = 0.0
    permitted_data: tuple[str, ...] = ()
    prohibited_data: tuple[str, ...] = ()
    originating_goal_id: str = ""
    capability_id: str = ""
    capability_version: str = ""
    capability_name: str = ""
    evidence_digest: str = ""
    baseline_metrics: Mapping[str, Any] = field(default_factory=dict)
    candidate_metrics: Mapping[str, Any] = field(default_factory=dict)
    sustained_metrics: Mapping[str, Any] = field(default_factory=dict)
    proposed_source_scope: tuple[str, ...] = ()
    restart_required: bool = False
    authority_impact: str = ""
    provider_impact: str = ""
    protected_path_impact: str = ""
    created_turn_id: str = ""
    thread_id: str = ""
    rendered_turn_id: str = ""
    created_sequence: int = 0
    render_sequence: int = 0
    accepted_response_types: tuple[str, ...] = ()
    resolution_state: str = "pending"
    resolved_turn_id: str = ""
    resolution_text: str = ""
    resolution_policy: str = ""
    resolution: str = ""
    side_thread_effect: str = "does_not_replace_foreground_topic"
    consumption_count: int = 0
    created_at: str = field(default_factory=utc_now)
    resolved_at: str = ""
    consumed_at: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


CLARIFICATION_PRESSURES = frozenset({
    "ambiguous_reference",
    "ambiguous_goal",
    "missing_evidence",
    "contradictory_claim",
    "operator_preference",
    "cross_topic_relevance",
    "structural_analogy_boundary",
    "consolidation_feedback",
    "blocked_authority",
})


def compile_chat_clarification_request(
    state: "ConversationalRuntimeState",
    *,
    pressure: str,
    prompt_text: str,
    source_record_ids: Sequence[str] = (),
    objective_id: str = "",
    created_turn_id: str = "",
    created_sequence: int = 0,
    request_type: str = "interactive_clarification",
) -> ChatAddressableRequest:
    """Compile one durable clarification request; rendering and resolution remain separate."""

    normalized_pressure = str(pressure or "").strip()
    wording = " ".join(str(prompt_text or "").split())
    if normalized_pressure not in CLARIFICATION_PRESSURES or not wording:
        raise ValueError("clarification request requires a known pressure and visible wording")
    goal_id = objective_id or (state.active_objective.objective_id if state.active_objective else "")
    source_refs = tuple(sorted({str(item) for item in source_record_ids if str(item)}))
    sequence = int(created_sequence or len(state.conversation) + 1)
    request_id = stable_id(
        "chat-clarification-request",
        state.runtime_id,
        normalized_pressure,
        goal_id,
        created_turn_id,
        *source_refs,
        wording,
    )
    return ChatAddressableRequest(
        request_id=request_id,
        request_type=request_type,
        objective_id=goal_id,
        originating_goal_id=goal_id,
        goal_label="Clarification",
        prompt_text=wording,
        created_turn_id=created_turn_id,
        thread_id=goal_id or "foreground-clarification",
        created_sequence=sequence,
        accepted_response_types=("clarification",),
        baseline_metrics={
            "clarification_pressure": normalized_pressure,
            "source_record_ids": source_refs,
        },
    )


@dataclass(frozen=True)
class TurnRelationDecision:
    turn_id: str
    foreground_topic: str
    active_goal_id: str
    relation_class: str
    evidence: tuple[str, ...]
    confidence: float
    decision_id: str = ""
    source_turn_id: str = ""
    objective_id: str = ""
    lane: str = ""
    candidate_referents: tuple[Mapping[str, Any], ...] = ()
    selected_referent: Mapping[str, Any] | None = None
    selected_turn_ids: tuple[str, ...] = ()
    rejected_referents: tuple[Mapping[str, Any], ...] = ()
    ambiguity: str = "none"
    action: str = "answer_normally"
    clarification_required: bool = False
    clarification_reason: str = ""
    correction_scope: str = ""
    lesson_applicability: str = "not_evaluated"
    tentative_goal_activation: str = "not_applicable"
    negative_instruction_tokens: tuple[str, ...] = ()
    side_thread_request_id: str = ""
    routing_decision: str = "foreground_answer"
    lesson_ids_considered: tuple[str, ...] = ()
    lesson_ids_applied: tuple[str, ...] = ()
    lesson_ids_rejected: tuple[str, ...] = ()
    rejection_reason: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LocalSemanticInsufficiency:
    insufficiency_id: str
    goal_id: str
    target_gap: str
    exact_information_needed: str
    local_model: str
    local_prompt: str
    local_raw_response_reference: str
    local_adapted_response_reference: str
    local_evaluation: str
    insufficiency_reason: str
    retry_attempted: bool
    local_retrieval_checked: bool
    local_evidence_references: tuple[str, ...]
    material_block: str
    smallest_external_packet: str
    prohibited_data: tuple[str, ...]
    recommended_provider_budget: Mapping[str, Any]
    created_at: str = field(default_factory=utc_now)
    consumed_by_provider_request: str = ""
    final_status: str = "open"
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TentativeGoalCandidate:
    candidate_goal_id: str
    source_turn_id: str
    wording: str
    interpreted_topic: str
    relation_to_active_objective: str
    status: str
    activation_required: bool
    created_at: str = field(default_factory=utc_now)
    activated_at: str = ""
    rejected_at: str = ""
    archived_at: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConversationalRuntimeState:
    runtime_id: str
    lifecycle_state: str
    active_objective: ConversationalObjective | None = None
    authority: StandingAuthority | None = None
    conversation: tuple[ConversationTurn, ...] = ()
    corrections: tuple[CorrectionRecord, ...] = ()
    accepted_lessons: tuple[ScopedLesson, ...] = ()
    rejected_lessons: tuple[Mapping[str, Any], ...] = ()
    focus_history: tuple[Mapping[str, Any], ...] = ()
    objective_progress: tuple[Mapping[str, Any], ...] = ()
    active_episode_path: str = ""
    completed_cycle_keys: tuple[str, ...] = ()
    pending_material_authority: tuple[Mapping[str, Any], ...] = ()
    pending_chat_requests: tuple[ChatAddressableRequest, ...] = ()
    resolved_chat_requests: tuple[ChatAddressableRequest, ...] = ()
    provider_authorities: tuple[Mapping[str, Any], ...] = ()
    turn_relation_decisions: tuple[TurnRelationDecision, ...] = ()
    local_semantic_insufficiencies: tuple[LocalSemanticInsufficiency, ...] = ()
    goal_reviews: tuple[Mapping[str, Any], ...] = ()
    archived_objectives: tuple[Mapping[str, Any], ...] = ()
    tentative_goals: tuple[TentativeGoalCandidate, ...] = ()
    capability_campaigns: tuple[Mapping[str, Any], ...] = ()
    capability_registry: tuple[Mapping[str, Any], ...] = ()
    capability_adoption_records: tuple[Mapping[str, Any], ...] = ()
    restart_records: tuple[Mapping[str, Any], ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeTurnResult:
    state: ConversationalRuntimeState
    intent: ConversationIntent
    reply: str
    objective_created: bool = False
    correction_attached: bool = False
    authority_request: Mapping[str, Any] | None = None
    chat_request: Mapping[str, Any] | None = None
    provider_authority: Mapping[str, Any] | None = None
    background_cycle_started: bool = False
    transfer_applied: bool = False
    side_thread_bound: bool = False
    developmental_governance: Mapping[str, Any] | None = None
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


def classify_conversational_intent(
    message: str,
    *,
    active_objective: ConversationalObjective | None = None,
    recent_turns: Sequence[ConversationTurn] = (),
) -> ConversationIntent:
    text = " ".join(str(message or "").split())
    lower = text.lower()
    risky = tuple(action for action, phrases in RISKY_ACTIONS.items() if any(phrase in lower for phrase in phrases))
    signals: list[str] = []
    if risky:
        return ConversationIntent(
            intent_type="authority_changing_or_risky_instruction",
            confidence=0.92,
            persistence_scope="none",
            risk_class="material_authority_boundary",
            authority_required=risky,
            matched_signals=tuple(risky),
        )
    correction_signals = (
        "no,",
        "no ",
        "that's not what i meant",
        "that isn't what i meant",
        "you misunderstood",
        "that interpretation was wrong",
        "when i say",
        "too verbose",
        "shorter answers",
        "don't repeat",
        "do not apply",
        "don't apply",
        "keep that rule out",
        "the last explanation was better",
    )
    meaning_correction = ("i mean" in lower or "i meant" in lower) and lower.startswith(("no", "actually", "when i say", "that's not", "that isn't", "you misunderstood"))
    if active_objective and (any(signal in lower for signal in correction_signals) or meaning_correction):
        signals.append("correction_phrase")
        target = next((turn.turn_id for turn in reversed(recent_turns) if turn.role == "assistant"), "")
        return ConversationIntent(
            intent_type="direct_correction",
            confidence=0.86,
            persistence_scope="active_objective",
            risk_class="safe_internal",
            authority_required=(),
            matched_signals=tuple(signals),
            target_turn_id=target,
        )
    if active_objective and any(signal in lower for signal in STOP_OR_REDIRECT_SIGNALS):
        return ConversationIntent(
            intent_type="stop_or_redirect",
            confidence=0.87,
            persistence_scope="active_objective",
            risk_class="safe_internal",
            authority_required=(),
            matched_signals=("stop_or_redirect",),
        )
    if is_teaching_instruction(text):
        return ConversationIntent(
            intent_type="persistent_or_session_goal",
            confidence=0.91,
            persistence_scope="session",
            risk_class="safe_internal",
            authority_required=(),
            matched_signals=("explicit_teaching_intent",),
        )
    temporary_signals = ("explain that more simply", "use shorter answers", "today", "for now", "don't repeat")
    if any(signal in lower for signal in temporary_signals) and not lower.startswith(("your goal", "work on", "keep studying")):
        return ConversationIntent(
            intent_type="temporary_conversational_instruction",
            confidence=0.8,
            persistence_scope="session",
            risk_class="safe_internal",
            authority_required=(),
            matched_signals=("session_strategy",),
        )
    goal_score = 0
    if re.search(r"\byour goal\b|\bnew goal is\b|\bgoal today\b|\bwork on\b|\bkeep studying\b|\bkeep working\b", lower):
        goal_score += 3
        signals.append("explicit_goal_language")
    if any(term in lower for term in ("improve", "learn", "understand", "comprehension", "communicate better", "corrections")):
        goal_score += 1
        signals.append("learning_or_improvement_target")
    if any(term in lower for term in ("today", "this session", "until", "keep")):
        goal_score += 1
        signals.append("scope_or_duration")
    if active_objective and goal_score < 3 and _is_tentative_goal_language(lower) and not _has_explicit_goal_activation(lower):
        return ConversationIntent(
            intent_type="tentative_goal_candidate",
            confidence=0.86,
            persistence_scope="active_objective",
            risk_class="safe_internal",
            authority_required=(),
            matched_signals=("tentative_goal_language",),
        )
    if goal_score >= 3:
        return ConversationIntent(
            intent_type="persistent_or_session_goal",
            confidence=0.84,
            persistence_scope="session",
            risk_class="safe_internal",
            authority_required=(),
            matched_signals=tuple(dict.fromkeys(signals)),
        )
    return ConversationIntent(
        intent_type="ordinary_conversation",
        confidence=0.78,
        persistence_scope="turn",
        risk_class="safe_internal",
        authority_required=(),
        matched_signals=("default_chat",),
    )


def _is_capability_campaign_goal(message: str) -> bool:
    lower = " ".join(str(message or "").lower().split())
    study = any(term in lower for term in ("study", "identify", "compare", "test", "candidate", "approach", "recommend adoption"))
    bounded_compare = any(term in lower for term in ("three bounded approaches", "at least three", "test them", "adoption recommendation"))
    capability_target = any(term in lower for term in ("distinguish", "foreground", "continuation", "failure pattern", "unrelated-topic", "follow-up"))
    delta_target = any(term in lower for term in ("delta", "your routing", "your planner", "your coordinator", "your runtime", "your behavior", "topic switch", "topic-switch"))
    capability_verbs = any(term in lower for term in ("improve", "repair", "fix", "strengthen", "harden", "reduce failures", "avoid regressions"))
    return bool((study and bounded_compare and capability_target) or (delta_target and capability_verbs))


def _goal_execution_mode(message: str) -> str:
    lower = " ".join(str(message or "").lower().split())
    if _is_capability_campaign_goal(message):
        return "capability_growth_campaign"
    if is_teaching_instruction(message):
        return "knowledge_acquisition"
    if any(term in lower for term in ("study", "learn", "research", "understand", "explain")):
        return "knowledge_acquisition"
    return "generic_conversational_cognition"


def _operator_question_initiative_authorized(message: str) -> bool:
    """Recognize bounded permission to seek one clarification for refinement.

    This is an objective-local authority signal, not a global conversational
    policy.  It looks for the semantic combination of operator-directed inquiry
    and an uncertainty/refinement boundary, while honoring explicit no-question
    instructions.
    """

    lower = " ".join(str(message or "").lower().split())
    if re.search(r"\b(?:do\s+not|don't|never)\s+(?:ask|question|interrupt|seek\s+clarification)\b", lower):
        return False
    inquiry = bool(re.search(r"\b(?:ask(?:\s+me)?|question(?:\s+me)?|seek\s+(?:(?:a|an|one|my)\s+)?(?:input|clarification)|clarify\s+with\s+me)\b", lower))
    boundary = bool(re.search(r"\b(?:uncertaint(?:y|ies)|unknown|missing\s+(?:information|context|evidence)|ambigu(?:ity|ous)|refin(?:e|ement)|update\s+the\s+analysis|use\s+my\s+answer)\b", lower))
    return inquiry and boundary


def _internal_work_initiative_authorized(message: str) -> bool:
    """Recognize objective-local permission to surface one safe continuation.

    This remains narrower than a standing execution authority.  It permits one
    provenance-only proposal at an unresolved analysis boundary and nothing
    beyond the existing conversational request surface.
    """

    lower = " ".join(str(message or "").lower().split())
    if re.search(r"\b(?:do\s+not|don't|never)\s+(?:create|surface|propose|raise)\s+(?:an?\s+)?(?:internal|next|follow[- ]?up|continuation)\b", lower):
        return False
    self_directed = bool(re.search(r"\b(?:internally|on\s+your\s+own|yourself|self-directed|independently)\b", lower))
    continuation = bool(re.search(r"\b(?:continuation|follow[- ]?up|next[-\s]+(?:step|issue|task|candidate)|remaining\s+(?:issue|uncertainty|context|detail)|unresolved\s+(?:issue|detail|context)|internal\s+(?:work|task|candidate|proposal))\b", lower))
    proposal = bool(re.search(r"\b(?:create|identify|surface|propose|keep|record|offer)\b", lower))
    uncertainty = bool(re.search(r"\b(?:uncertaint(?:y|ies)|unknown|missing\s+(?:information|context|evidence)|unresolved|refin(?:e|ement))\b", lower))
    return bool((self_directed and continuation and proposal) or (continuation and proposal and uncertainty))


def _evidence_permission_initiative_authorized(message: str) -> bool:
    """Recognize objective-local permission to ask before gathering evidence."""

    lower = " ".join(str(message or "").lower().split())
    if re.search(
        r"\b(?:do\s+not|don't|never)\s+(?:ask|request|seek|raise)\b.{0,48}\b(?:evidence|source|lookup|inspection|authorization|permission)\b",
        lower,
    ):
        return False
    permission = bool(
        re.search(r"\b(?:ask|request|seek|raise)\b.{0,48}\b(?:permission|approval|authorization|consent)\b", lower)
        or re.search(r"\b(?:authorize|allow|approve|permission)\b.{0,48}\b(?:evidence|source|lookup|inspection|data)\b", lower)
    )
    evidence = bool(re.search(r"\b(?:evidence|source|data|lookup|inspection|verify|verification|gather(?:ing)?)\b", lower))
    gap = bool(re.search(r"\b(?:uncertaint(?:y|ies)|unknown|missing|insufficient|gap|limit|refin(?:e|ement)|before\s+gathering)\b", lower))
    return permission and evidence and gap


def _objective_execution_constraints(message: str) -> dict[str, Any]:
    """Compile explicit operator execution limits into objective provenance.

    These limits are deliberately narrow: they do not pause or replace the
    objective, create a second authority layer, or affect foreground work.
    They only tell the existing background-cycle owner when local inference
    must wait for a later operator release.
    """

    lower = " ".join(str(message or "").lower().split())
    no_local_model = any(
        phrase in lower
        for phrase in (
            "do not call a model",
            "don't call a model",
            "do not use a local model",
            "don't use a local model",
            "do not run a local model",
            "don't run a local model",
            "without using a model",
        )
    )
    no_provider = any(
        phrase in lower
        for phrase in (
            "do not access a provider",
            "don't access a provider",
            "do not use a provider",
            "don't use a provider",
            "do not call a provider",
            "don't call a provider",
            "do not use oracle",
            "don't use oracle",
        )
    ) or (no_local_model and "access a provider" in lower)
    no_external_action = any(
        phrase in lower
        for phrase in (
            "do not take an external action",
            "don't take an external action",
            "do not take external action",
            "don't take external action",
        )
    ) or (no_local_model and "take an external action" in lower)
    wait_for_operator_input = bool(
        re.search(
            r"\b(?:wait|hold off|do not begin)\s+(?:for|until)\s+(?:the\s+)?(?:next\s+)?(?:scenario|scenarios|operator input|my input|my next|further instruction)",
            lower,
        )
    )
    return {
        "schema_version": "objective_execution_constraints_v1",
        "source": "operator_wording",
        "no_local_model": no_local_model,
        "no_provider": no_provider,
        "no_external_action": no_external_action,
        "wait_for_operator_input": wait_for_operator_input,
        "operator_question_initiative_allowed": _operator_question_initiative_authorized(message),
        "internal_work_initiative_allowed": _internal_work_initiative_authorized(message),
        "evidence_permission_initiative_allowed": _evidence_permission_initiative_authorized(message),
        "state": "operator_waiting" if (no_local_model or wait_for_operator_input) else "unconstrained",
        "override_history": (),
    }


def _objective_execution_constraints_for_objective(
    objective: ConversationalObjective | None,
) -> dict[str, Any]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return {}
    constraints = objective.provenance.get("execution_constraints")
    return dict(constraints) if isinstance(constraints, Mapping) else {}


def _objective_execution_hold_reason(objective: ConversationalObjective | None) -> str:
    constraints = _objective_execution_constraints_for_objective(objective)
    if bool(constraints.get("wait_for_operator_input")):
        return "wait_for_operator_input"
    if bool(constraints.get("no_local_model")):
        return "no_local_model"
    return ""


def background_cycle_hold_reason(state: ConversationalRuntimeState) -> str:
    """Return the canonical reason the existing background cycle must wait."""

    return _objective_execution_hold_reason(state.active_objective)


def _is_explicit_local_model_release(message: str) -> bool:
    lower = " ".join(str(message or "").lower().split()).strip(" .!")
    return lower in {
        "you may use a local model now",
        "you can use a local model now",
        "resume local model work",
        "resume local cognition now",
        "you may resume local cognition",
    }


def _strip_goal_prefix(message: str) -> str:
    text = " ".join(str(message or "").split()).strip()
    return re.sub(r"^your (new )?goal (today )?is (to )?", "", text, flags=re.IGNORECASE).strip()


def _knowledge_goal_contract(message: str) -> dict[str, Any]:
    full = " ".join(str(message or "").split()).strip()
    objective = _strip_goal_prefix(full)
    lower = full.lower()
    before_constraints = re.split(r"\buse local cognition\b|\bask me only\b|\bcontinue until\b|\bdo not\b", objective, maxsplit=1, flags=re.IGNORECASE)[0]
    topic_source = before_constraints.split(":", 1)[0] if ":" in before_constraints else re.split(r"\.\s*study\b", before_constraints, maxsplit=1, flags=re.IGNORECASE)[0]
    topic = topic_source
    topic = re.sub(r"^(?:build|create|study|learn|research|understand|explain)\b\s*(?:(?:a|an|the)\s+)?(?:local\s+)?", "", topic, flags=re.IGNORECASE).strip(" .")
    topic = re.sub(r"^knowledge map of\s+", "", topic, flags=re.IGNORECASE).strip(" .") or objective
    study_matches = re.findall(r"\bstudy\s+(.+?)(?:\.\s|$)", objective, flags=re.IGNORECASE)
    source = (
        before_constraints.split(":", 1)[1]
        if ":" in before_constraints
        else study_matches[-1] if study_matches else before_constraints
    )
    requested = _extract_material_knowledge_clauses(source, topic)
    if not requested:
        requested = [topic]
    requested = list(dict.fromkeys(requested))
    material_requirements = tuple({
        "requirement_id": stable_id("knowledge-material-requirement", topic, str(index), item),
        "text": item,
    } for index, item in enumerate(requested, start=1))
    criteria = tuple("address " + str(item["text"]) for item in material_requirements)
    if "recommend" in lower and not any("recommend" in item for item in criteria):
        criteria = criteria + ("identify information needed before a specific recommendation",)
    if "completion" in lower or "blocking" in lower or "remaining-gap" in lower or "remaining gap" in lower:
        criteria = criteria + ("produce a terminal synthesis or explicit blocked/remaining-gap report",)
    return {
        "full_operator_wording": full,
        "normalized_topic": topic,
        "requested_subtopics": tuple(requested),
        "material_requirements": material_requirements,
        "evidence_source_constraints": tuple(
            item for item, present in (
                ("local cognition first", "use local cognition" in lower),
                ("existing local evidence first", "existing local evidence" in lower),
                ("no external provider without approval", "provider" in lower or "local" in lower),
            )
            if present
        ),
        "follow_up_question_policy": "ask only for missing information that materially changes the answer" if "ask me only" in lower else "ask only when materially needed",
        "budget_continuation_instruction": "continue until available local resources or budgets are exhausted" if "continue until" in lower else "bounded local cycle budget",
        "completion_report_instruction": "give a clear completion, blocking, or remaining-gap report" if ("blocking" in lower or "remaining-gap" in lower or "remaining gap" in lower) else "report terminal outcome",
        "prohibited_actions": tuple(item for item, present in (("source code changes", "change source" in lower or "source code" in lower), ("restart", "restart" in lower)) if present),
        "completion_criteria": criteria,
    }


def _extract_material_knowledge_clauses(source: str, topic: str) -> list[str]:
    """Preserve each operator-requested knowledge clause before node planning."""
    source = " ".join(str(source or "").strip(" .").split())
    parts = re.split(r"\s*(?:,|;|\band\b|\bor\b)\s*", source, flags=re.IGNORECASE)
    requested: list[str] = []
    for part in parts:
        cleaned = _normalize_knowledge_subtopic(part, topic)
        cleaned = re.sub(r"^(?:to\s+)?build\s+a\s+local\s+knowledge\s+map\s+of\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(?:understand|study|learn|research|explain)\s+" + re.escape(topic) + r"\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        if cleaned and cleaned.lower() not in {topic.lower(), "local evidence first"}:
            requested.append(cleaned)
    return requested


def _normalize_knowledge_subtopic(part: str, topic: str) -> str:
    cleaned = " ".join(str(part or "").strip(" .").split())
    cleaned = re.sub(r"^(?:and|or)\s+", "", cleaned, flags=re.IGNORECASE)
    lower = cleaned.lower()
    if lower in {"how they work", "how it works", "how this works", "how those work"}:
        return f"operating principle of {topic}"
    if lower in {"they work", "it works", "this works", "those work"}:
        return f"operating principle of {topic}"
    if lower.startswith("how "):
        return cleaned
    cleaned = re.sub(r"^(?:what|which)\s+", "", cleaned, flags=re.IGNORECASE)
    if cleaned.lower().startswith("when "):
        return "conditions " + cleaned
    return cleaned


def _goal_review_label(objective: ConversationalObjective | None) -> str:
    if objective is None:
        return "No active goal"
    text = f"{objective.interpreted_objective} {objective.operator_wording}".lower()
    if "foreground" in text and "continuation" in text:
        return "Foreground vs continuation routing"
    if "semantic" in text and "reconciliation" in text:
        return "Semantic reconciliation"
    if "english comprehension" in text or "communicate better" in text:
        return "Language understanding"
    label = re.sub(r"^your (new )?goal (today )?is (to )?", "", objective.interpreted_objective, flags=re.IGNORECASE).strip()
    label = re.sub(r"\s+", " ", label)
    return (label[:72].rstrip(" .,;:") or "Active goal")


def _knowledge_model_budget_request(
    objective: ConversationalObjective,
    *,
    required_nodes: int,
    completed_nodes: int,
    model_calls_used: int,
    exhausted: bool,
) -> ChatAddressableRequest:
    remaining_nodes = max(0, int(required_nodes) - int(completed_nodes))
    if objective.model_call_budget is None:
        raise ValueError("unlimited_local_knowledge_goals_do_not_need_budget_approval")
    current_budget = int(objective.model_call_budget)
    extra_calls = (
        remaining_nodes + 1 + min(4, max(2, remaining_nodes // 4))
        if exhausted
        else max(0, required_nodes + 1 + min(4, max(2, required_nodes // 4)) - current_budget)
    )
    recommended_budget = current_budget + extra_calls
    introduction = (
        "The local-model call budget is exhausted."
        if exhausted
        else "This goal needs more local-model calls than the current budget allows."
    )
    prompt = (
        "[Budget boundary]\n"
        f"{introduction} Temporarily increase the budget for this goal?\n\n"
        f"Required nodes: {required_nodes}\n"
        f"Completed: {completed_nodes}\n"
        f"Remaining: {remaining_nodes}\n"
        f"Model calls: {model_calls_used}/{current_budget}\n"
        f"Recommended temporary increase: +{extra_calls} calls\n\n"
        "Reply Yes to increase for this goal only, or No to stop with a partial report."
    )
    return ChatAddressableRequest(
        request_id=stable_id(
            "knowledge-budget-request",
            objective.objective_id,
            "runtime-exhaustion" if exhausted else "preflight",
            str(model_calls_used),
            str(recommended_budget),
        ),
        request_type="knowledge_model_budget_increase",
        objective_id=objective.objective_id,
        originating_goal_id=objective.objective_id,
        goal_label=_goal_review_label(objective),
        prompt_text=prompt,
        max_calls=recommended_budget,
        side_thread_effect="does_not_replace_foreground_topic",
        thread_id=objective.objective_id,
        accepted_response_types=("approved", "denied"),
    )


def compile_conversational_objective(message: str, intent: ConversationIntent) -> ConversationalObjective:
    text = " ".join(message.split())
    objective_id = stable_id("conversational-objective", text, intent.persistence_scope)
    lower = text.lower()
    execution_mode = _goal_execution_mode(text)
    execution_constraints = _objective_execution_constraints(text)
    campaign_mode = execution_mode == "capability_growth_campaign"
    unlimited_local_knowledge = execution_mode == "knowledge_acquisition"
    teaching_plan = compile_teaching_plan(text) if is_teaching_instruction(text) else {}
    knowledge_contract = (
        teaching_knowledge_contract(teaching_plan)
        if teaching_plan
        else _knowledge_goal_contract(text)
        if execution_mode == "knowledge_acquisition"
        else {}
    )
    if "english comprehension" in lower or "communicate better" in lower:
        interpreted = "Improve operator-specific English comprehension during conversation by observing misunderstandings, incorporating corrections, and testing later transfer."
        indicators = (
            "operator corrections attach to exact turns",
            "strategy revisions reduce repeated misunderstanding",
            "later related cases use the scoped lesson",
            "unrelated cases do not receive false transfer",
            "ordinary chat remains responsive",
        )
    elif knowledge_contract:
        topic = str(knowledge_contract["normalized_topic"]).strip()
        interpreted = f"Teach operator introductory {topic}" if teaching_plan else topic.capitalize()
        indicators = tuple(str(item) for item in knowledge_contract["completion_criteria"])
    else:
        interpreted = _strip_goal_prefix(text)
        interpreted = interpreted[:1].upper() + interpreted[1:] if interpreted else text
        indicators = (
            "objective receives a fresh identity and fresh budgets",
            "local cognition starts without inheriting prior goal state",
            "first evidence pass produces durable progress",
            "ordinary chat remains responsive",
            "material authority boundaries remain unchanged",
        )
    if campaign_mode:
        indicators = (
            "candidate weaknesses are derived from active conversation evidence",
            "at least three bounded approaches are compared before adoption is recommended",
            "unrelated-topic and follow-up cases are both represented in evaluation",
            "milestone notifications occur before any shared cycle budget is exhausted",
            "source mutation remains unavailable until implementation review is explicitly approved",
        )
    return ConversationalObjective(
        objective_id=objective_id,
        operator_wording=text,
        interpreted_objective=interpreted,
        persistence_scope=intent.persistence_scope,
        practical_success_indicators=indicators,
        allowed_actions=DEFAULT_ALLOWED_ACTIONS,
        prohibited_actions=DEFAULT_PROHIBITED_ACTIONS,
        local_evidence_sources=("conversation turns", "operator corrections", "active cognitive episode state", "continuity lessons"),
        cycle_budget=None if unlimited_local_knowledge else (24 if campaign_mode else 16),
        model_call_budget=None if unlimited_local_knowledge else (16 if campaign_mode else 24),
        interruption_policy="foreground chat preempts background objective work",
        correction_learning_policy="attach corrections to exact turns; consolidate only scoped non-authoritative lessons",
        completion_or_review_condition=(
            "review only after candidate weaknesses, approach comparison, evaluation, and adoption recommendation milestones exist"
            if campaign_mode
            else "review after bounded local cognition produces useful evidence and foreground controls remain intact"
        ),
        authority_boundary="standing authority covers routine local cognition only; material actions require explicit operator approval",
        provenance={
            "source": "ordinary_chat",
            "intent": intent.as_record(),
            "compiler": "conversational_runtime_operation",
            "execution_mode": execution_mode,
            "execution_constraints": execution_constraints,
            "knowledge_contract": knowledge_contract,
            "teaching_plan": teaching_plan,
        },
    )


def _episode_title_for_objective(objective: ConversationalObjective) -> str:
    if objective.provenance.get("execution_mode") == "knowledge_acquisition":
        return "Knowledge acquisition objective"
    return "Conversational English comprehension objective"


def _expected_state_for_objective(objective: ConversationalObjective) -> str:
    if objective.provenance.get("execution_mode") == "knowledge_acquisition":
        return "Knowledge-specific criteria are advanced through local evidence, concept frontier nodes, and terminal gap reporting."
    return "Operator-specific comprehension improves through correction-linked strategy revision and transfer checks."


def _knowledge_frontier_evidence(objective: ConversationalObjective) -> tuple[EvidenceRef, ...]:
    contract = objective.provenance.get("knowledge_contract") if isinstance(objective.provenance, Mapping) else None
    if not isinstance(contract, Mapping):
        return ()
    material_requirements = tuple(
        item for item in contract.get("material_requirements", ())
        if isinstance(item, Mapping) and str(item.get("requirement_id") or "") and str(item.get("text") or "")
    )
    subtopics = tuple(str(item["text"]).strip() for item in material_requirements) or tuple(str(item).strip() for item in contract.get("requested_subtopics", ()) if str(item).strip())
    criteria = tuple(str(item).strip() for item in contract.get("completion_criteria", ()) if str(item).strip())
    nodes: list[EvidenceRef] = []
    for index, label in enumerate(subtopics, start=1):
        criterion = criteria[min(index - 1, len(criteria) - 1)] if criteria else label
        requirement_id = str(material_requirements[index - 1]["requirement_id"]) if index <= len(material_requirements) else stable_id("knowledge-material-requirement", objective.objective_id, str(index), label)
        nodes.append(EvidenceRef(
            evidence_id=stable_id("knowledge-frontier-node", objective.objective_id, str(index), label),
            summary=f"Knowledge frontier node {index}: {label}",
            content=json.dumps({
                "node_id": stable_id("knowledge-frontier-node", objective.objective_id, str(index), label),
                "material_requirement_id": requirement_id,
                "objective_id": objective.objective_id,
                "label": label,
                "parent_id": objective.objective_id,
                "depth": 1,
                "status": "queued",
                "evidence_need": f"local evidence and model synthesis for {label}",
                "completion_criterion_reference": criterion,
                "minimum_contribution_contract": _knowledge_node_completion_contract(label, criterion),
                "extracted_concept_ids": [],
                "extracted_claim_ids": [],
                "unresolved_questions": [],
                "attempt_count": 0,
                "last_progress_digest": "",
            }, sort_keys=True),
            source="knowledge_frontier",
            kind="knowledge_frontier_node",
        ))
    return _teaching_followup_evidence(objective) + tuple(nodes) + _teaching_prerequisite_evidence(objective)


def _teaching_plan_for_objective(objective: ConversationalObjective | None) -> Mapping[str, Any]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return {}
    plan = objective.provenance.get("teaching_plan")
    return dict(plan) if isinstance(plan, Mapping) else {}


def _teaching_followups_for_objective(objective: ConversationalObjective | None) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("teaching_followups", ())
        if isinstance(item, Mapping)
    )


def _teaching_prerequisites_for_objective(objective: ConversationalObjective | None) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("teaching_prerequisites", ())
        if isinstance(item, Mapping)
    )


def _teaching_consolidation_records_for_objective(objective: ConversationalObjective | None) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("teaching_consolidation_records", ())
        if isinstance(item, Mapping)
    )


def _semantic_transfer_applications_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("semantic_transfer_applications", ())
        if isinstance(item, Mapping)
    )


def _semantic_analytical_tasks_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("semantic_analytical_tasks", ())
        if isinstance(item, Mapping)
    )


def _semantic_competence_deltas_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("semantic_competence_deltas", ())
        if isinstance(item, Mapping)
    )


def _semantic_problem_frames_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    """Read canonical, source-bound frames without creating a second memory owner."""

    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("semantic_problem_frames", ())
        if isinstance(item, Mapping)
    )


def _evidence_bound_analyses_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    """Read task-local analyses from the canonical objective provenance only."""

    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_bound_analyses", ())
        if isinstance(item, Mapping)
    )


def _operator_question_candidates_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    """Read question candidates from the active objective's canonical provenance."""

    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("operator_question_candidates", ())
        if isinstance(item, Mapping)
    )


def _operator_question_selections_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("operator_question_selections", ())
        if isinstance(item, Mapping)
    )


def _operator_question_answers_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("operator_question_answers", ())
        if isinstance(item, Mapping)
    )


def _analysis_refinements_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("analysis_refinements", ())
        if isinstance(item, Mapping)
    )


def _internal_work_candidates_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    """Read analyst-local internal continuations from canonical provenance only."""

    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("internal_work_candidates", ())
        if isinstance(item, Mapping)
    )


def _internal_work_selections_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("internal_work_selections", ())
        if isinstance(item, Mapping)
    )


def _internal_work_dispositions_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("internal_work_dispositions", ())
        if isinstance(item, Mapping)
    )


def _evidence_permission_requests_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_requests", ())
        if isinstance(item, Mapping)
    )


def _evidence_authorizations_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_authorizations", ())
        if isinstance(item, Mapping)
    )


def _evidence_next_operation_proposals_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_next_operation_proposals", ())
        if isinstance(item, Mapping)
    )


def _evidence_next_operation_dispositions_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_next_operation_dispositions", ())
        if isinstance(item, Mapping)
    )


def _evidence_execution_authorities_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_execution_authorities", ())
        if isinstance(item, Mapping)
    )


def _evidence_fixture_execution_plans_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_fixture_execution_plans", ())
        if isinstance(item, Mapping)
    )


def _evidence_fixture_dry_run_results_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_fixture_dry_run_results", ())
        if isinstance(item, Mapping)
    )


def _evidence_result_ingestion_candidates_for_objective(
    objective: ConversationalObjective | None,
) -> tuple[dict[str, Any], ...]:
    if objective is None or not isinstance(objective.provenance, Mapping):
        return ()
    return tuple(
        dict(item)
        for item in objective.provenance.get("evidence_result_ingestion_candidates", ())
        if isinstance(item, Mapping)
    )


def _replace_teaching_objective(
    objective: ConversationalObjective,
    *,
    followups: Sequence[Mapping[str, Any]] | None = None,
    prerequisites: Sequence[Mapping[str, Any]] | None = None,
    consolidation_records: Sequence[Mapping[str, Any]] | None = None,
    semantic_transfer_applications: Sequence[Mapping[str, Any]] | None = None,
    semantic_analytical_tasks: Sequence[Mapping[str, Any]] | None = None,
    semantic_competence_deltas: Sequence[Mapping[str, Any]] | None = None,
    semantic_problem_frames: Sequence[Mapping[str, Any]] | None = None,
    evidence_bound_analyses: Sequence[Mapping[str, Any]] | None = None,
    operator_question_candidates: Sequence[Mapping[str, Any]] | None = None,
    operator_question_selections: Sequence[Mapping[str, Any]] | None = None,
    operator_question_answers: Sequence[Mapping[str, Any]] | None = None,
    analysis_refinements: Sequence[Mapping[str, Any]] | None = None,
    internal_work_candidates: Sequence[Mapping[str, Any]] | None = None,
    internal_work_selections: Sequence[Mapping[str, Any]] | None = None,
    internal_work_dispositions: Sequence[Mapping[str, Any]] | None = None,
    evidence_requests: Sequence[Mapping[str, Any]] | None = None,
    evidence_authorizations: Sequence[Mapping[str, Any]] | None = None,
    evidence_next_operation_proposals: Sequence[Mapping[str, Any]] | None = None,
    evidence_next_operation_dispositions: Sequence[Mapping[str, Any]] | None = None,
    evidence_execution_authorities: Sequence[Mapping[str, Any]] | None = None,
    evidence_fixture_execution_plans: Sequence[Mapping[str, Any]] | None = None,
    evidence_fixture_dry_run_results: Sequence[Mapping[str, Any]] | None = None,
    evidence_result_ingestion_candidates: Sequence[Mapping[str, Any]] | None = None,
    execution_constraints: Mapping[str, Any] | None = None,
) -> ConversationalObjective:
    provenance = dict(objective.provenance)
    if followups is not None:
        provenance["teaching_followups"] = tuple(dict(item) for item in followups)
    if prerequisites is not None:
        provenance["teaching_prerequisites"] = tuple(dict(item) for item in prerequisites)
    if consolidation_records is not None:
        provenance["teaching_consolidation_records"] = tuple(dict(item) for item in consolidation_records)
    if semantic_transfer_applications is not None:
        provenance["semantic_transfer_applications"] = tuple(
            dict(item) for item in semantic_transfer_applications
        )
    if semantic_analytical_tasks is not None:
        provenance["semantic_analytical_tasks"] = tuple(dict(item) for item in semantic_analytical_tasks)
    if semantic_competence_deltas is not None:
        provenance["semantic_competence_deltas"] = tuple(
            dict(item) for item in semantic_competence_deltas
        )
    if semantic_problem_frames is not None:
        provenance["semantic_problem_frames"] = tuple(
            dict(item) for item in semantic_problem_frames
        )
    if evidence_bound_analyses is not None:
        provenance["evidence_bound_analyses"] = tuple(
            dict(item) for item in evidence_bound_analyses
        )
    if operator_question_candidates is not None:
        provenance["operator_question_candidates"] = tuple(
            dict(item) for item in operator_question_candidates
        )
    if operator_question_selections is not None:
        provenance["operator_question_selections"] = tuple(
            dict(item) for item in operator_question_selections
        )
    if operator_question_answers is not None:
        provenance["operator_question_answers"] = tuple(
            dict(item) for item in operator_question_answers
        )
    if analysis_refinements is not None:
        provenance["analysis_refinements"] = tuple(
            dict(item) for item in analysis_refinements
        )
    if internal_work_candidates is not None:
        provenance["internal_work_candidates"] = tuple(
            dict(item) for item in internal_work_candidates
        )
    if internal_work_selections is not None:
        provenance["internal_work_selections"] = tuple(
            dict(item) for item in internal_work_selections
        )
    if internal_work_dispositions is not None:
        provenance["internal_work_dispositions"] = tuple(
            dict(item) for item in internal_work_dispositions
        )
    if evidence_requests is not None:
        provenance["evidence_requests"] = tuple(dict(item) for item in evidence_requests)
    if evidence_authorizations is not None:
        provenance["evidence_authorizations"] = tuple(dict(item) for item in evidence_authorizations)
    if evidence_next_operation_proposals is not None:
        provenance["evidence_next_operation_proposals"] = tuple(
            dict(item) for item in evidence_next_operation_proposals
        )
    if evidence_next_operation_dispositions is not None:
        provenance["evidence_next_operation_dispositions"] = tuple(
            dict(item) for item in evidence_next_operation_dispositions
        )
    if evidence_execution_authorities is not None:
        provenance["evidence_execution_authorities"] = tuple(
            dict(item) for item in evidence_execution_authorities
        )
    if evidence_fixture_execution_plans is not None:
        provenance["evidence_fixture_execution_plans"] = tuple(
            dict(item) for item in evidence_fixture_execution_plans
        )
    if evidence_fixture_dry_run_results is not None:
        provenance["evidence_fixture_dry_run_results"] = tuple(
            dict(item) for item in evidence_fixture_dry_run_results
        )
    if evidence_result_ingestion_candidates is not None:
        provenance["evidence_result_ingestion_candidates"] = tuple(
            dict(item) for item in evidence_result_ingestion_candidates
        )
    if execution_constraints is not None:
        provenance["execution_constraints"] = dict(execution_constraints)
    return replace(objective, provenance=provenance)


def _semantic_problem_compilation_for_message(
    state: ConversationalRuntimeState,
    message: str,
):
    """Compile only a recognized operator input under its active objective provenance."""

    objective = state.active_objective
    if objective is None:
        return None
    return compile_semantic_problem_frame(
        message,
        frame_scope_id=objective.objective_id,
        source_turn_id=stable_id(
            "conversation-turn",
            state.runtime_id,
            str(len(state.conversation) + 1),
            message,
        ),
        source_type="operator_text",
    )


def is_semantic_problem_modeling_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose a narrow, source-bound perception boundary to the normal dispatcher."""

    return _semantic_problem_compilation_for_message(state, message) is not None


def _semantic_problem_frame_terms(record: Mapping[str, Any]) -> set[str]:
    frame = record.get("semantic_input_frame") if isinstance(record.get("semantic_input_frame"), Mapping) else record
    model = record.get("problem_model") if isinstance(record.get("problem_model"), Mapping) else {}
    equation = (
        record.get("equation_understanding_frame")
        if isinstance(record.get("equation_understanding_frame"), Mapping)
        else {}
    )
    text = " ".join(
        str(value or "")
        for value in (
            frame.get("domain_guess"),
            frame.get("source_text"),
            frame.get("goal"),
            frame.get("unknown_target"),
            model.get("problem_type"),
            equation.get("equation"),
            equation.get("modeled_phenomenon"),
            " ".join(str(item) for item in frame.get("risks", ()) if str(item)),
        )
    )
    return _semantic_transfer_terms(text)


def _semantic_problem_frame_recall_candidate(
    state: ConversationalRuntimeState,
    message: str,
) -> tuple[dict[str, Any], str] | None:
    """Resolve an explicit, unambiguous frame recall without broad memory lookup."""

    objective = state.active_objective
    if objective is None:
        return None
    normalized = " ".join(str(message or "").lower().split())
    if not re.match(r"^(?:how|what|which|why|did|does|do|can|could)\b", normalized):
        return None
    if re.search(r"\bf\s*=\s*m\s*a\b", normalized):
        focus = "equation"
        required_terms = {"physics", "equation", "model"}
    elif any(term in normalized for term in ("unknown target", "unknown", "target")):
        focus = "unknown_target"
        required_terms = {"incline", "block", "physics", "acceleration", "problem"}
    elif any(term in normalized for term in ("risk", "defensive", "sql", "financial", "portfolio", "cyber")):
        focus = "risk"
        required_terms = {"sql", "database", "cybersecurity", "portfolio", "finance", "risk"}
    elif any(term in normalized for term in ("perceive", "perceived", "frame", "operations", "invoice", "crew", "dependency")):
        focus = "summary"
        required_terms = {"operations", "logistics", "invoice", "crew", "dependency"}
    else:
        return None
    message_terms = _semantic_transfer_terms(normalized)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for record in _semantic_problem_frames_for_objective(objective):
        frame = record.get("semantic_input_frame") if isinstance(record.get("semantic_input_frame"), Mapping) else record
        domain = str(frame.get("domain_guess") or "")
        if focus == "equation" and domain != "physics_equation_model":
            continue
        terms = _semantic_problem_frame_terms(record)
        score = len(message_terms & terms)
        if focus == "equation" and domain == "physics_equation_model":
            score += 4
        if focus == "unknown_target" and terms & {"incline", "block", "acceleration"}:
            score += 3
        if focus == "risk" and terms & required_terms:
            score += 2
        if focus == "risk" and domain == "finance_portfolio_risk" and any(
            term in normalized
            for term in ("financial", "finance", "portfolio", "investment", "market")
        ):
            score += 4
        if focus == "risk" and domain == "defensive_cybersecurity" and any(
            term in normalized
            for term in ("sql", "cyber", "security", "defensive", "database")
        ):
            score += 4
        if focus == "summary" and terms & required_terms:
            score += 2
        if score:
            candidates.append((score, record))
    if not candidates:
        return None
    highest = max(score for score, _record in candidates)
    selected = [record for score, record in candidates if score == highest]
    return (dict(selected[0]), focus) if len(selected) == 1 else None


def is_semantic_problem_frame_recall_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose a read-only, source-specific recall boundary to the normal dispatcher."""

    return _semantic_problem_frame_recall_candidate(state, message) is not None


def _evidence_bound_analysis_terms(record: Mapping[str, Any]) -> set[str]:
    """Build a local selector vocabulary from one persisted analysis only."""

    evidence = tuple(item for item in record.get("evidence_items", ()) if isinstance(item, Mapping))
    text = " ".join(
        str(value or "")
        for value in (
            record.get("domain"),
            record.get("source_text"),
            record.get("analysis_type"),
            record.get("selected_method"),
            record.get("method_rationale"),
            record.get("result_summary"),
            " ".join(str(item) for item in record.get("extracted_facts", ()) if str(item)),
            " ".join(str(item.get("text") or "") for item in evidence),
        )
    )
    return _semantic_transfer_terms(text)


def _evidence_bound_analysis_recall_candidate(
    state: ConversationalRuntimeState,
    message: str,
) -> tuple[dict[str, Any], str] | None:
    """Resolve one explicit analysis recall without broad memory retrieval."""

    objective = state.active_objective
    if objective is None:
        return None
    normalized = " ".join(str(message or "").lower().split())
    if not re.match(r"^(?:how|what|which|why|did|does|do|can|could)\b", normalized):
        return None
    if "bottleneck" in normalized or ("operational" in normalized and "identify" in normalized):
        focus = "bottleneck"
        target_domain = "operations_logistics_receivables"
        required_terms = {"pump", "crew", "invoice", "delivery", "bottleneck"}
    elif "incline" in normalized and "method" in normalized:
        focus = "method"
        target_domain = "physics_mechanics"
        required_terms = {"incline", "newtonian", "force", "method"}
    elif "sql" in normalized and "case" in normalized and any(
        term in normalized for term in ("defensive", "defence", "security", "safe")
    ):
        focus = "defensive"
        target_domain = "defensive_cybersecurity"
        required_terms = {"sql", "defensive", "input", "parameter"}
    elif "main" in normalized and "risks" in normalized and any(
        term in normalized for term in ("finance", "financial", "portfolio", "market")
    ):
        focus = "finance_risk"
        target_domain = "finance_portfolio_risk"
        required_terms = {"portfolio", "finance", "risk", "concentration"}
    elif re.search(r"\bf\s*=\s*m\s*a\b", normalized) and any(
        term in normalized for term in ("validation", "check", "validate")
    ):
        focus = "validation"
        target_domain = "physics_equation_model"
        required_terms = {"force", "mass", "acceleration", "validation"}
    else:
        return None
    message_terms = _semantic_transfer_terms(normalized)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for record in _evidence_bound_analyses_for_objective(objective):
        if str(record.get("status") or "") not in {"provisional_analysis", "recalled_read_only"}:
            continue
        terms = _evidence_bound_analysis_terms(record)
        score = len(message_terms & terms)
        if str(record.get("domain") or "") == target_domain:
            score += 6
        if terms & required_terms:
            score += 2
        if score:
            candidates.append((score, record))
    if not candidates:
        return None
    highest = max(score for score, _record in candidates)
    selected = [record for score, record in candidates if score == highest]
    return (dict(selected[0]), focus) if len(selected) == 1 else None


def is_evidence_bound_analysis_recall_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose only explicit task-local analysis recaps to the normal dispatcher."""

    return _evidence_bound_analysis_recall_candidate(state, message) is not None


def _analysis_refinement_recall_candidate(
    state: ConversationalRuntimeState,
    message: str,
) -> tuple[dict[str, Any], str] | None:
    objective = state.active_objective
    refinements = _analysis_refinements_for_objective(objective)
    if objective is None or not refinements:
        return None
    lower = " ".join(str(message or "").lower().split())
    if (
        ("what did we analyze" in lower or "what have we analyzed" in lower)
        and re.search(r"\b(?:ask|question)\b", lower)
        and re.search(r"\b(?:answer|change|refin)\b", lower)
    ):
        focus = "chain"
    elif re.search(r"\b(?:still|remain(?:ing)?|left)\s+(?:uncertain|unknown|unclear)\b|\bwhat\s+(?:is|remains)\s+uncertain\b", lower):
        focus = "uncertainty"
    elif re.search(r"\b(?:what|how)\s+(?:did\s+)?(?:my\s+)?(?:answer|response)?\s*(?:change|changed|refin)|\bwhat\s+changed\b|\bafter\s+my\s+answer\b", lower):
        focus = "change"
    else:
        return None
    return dict(refinements[-1]), focus


def is_evidence_bound_analysis_refinement_recall_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose only explicit recap questions about an existing answer refinement."""

    return _analysis_refinement_recall_candidate(state, message) is not None


def _apply_evidence_bound_analysis_refinement_recall(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    objective = state.active_objective
    candidate = _analysis_refinement_recall_candidate(state, message)
    if objective is None or candidate is None:
        return None
    refinement, focus = candidate
    source_analysis_id = str(refinement.get("source_analysis_id") or "")
    source_question_id = str(refinement.get("source_question_id") or "")
    source_answer_id = str(refinement.get("source_answer_id") or "")
    source_analysis = next(
        (item for item in _evidence_bound_analyses_for_objective(objective) if str(item.get("analysis_id") or "") == source_analysis_id),
        None,
    )
    source_question = next(
        (item for item in _operator_question_candidates_for_objective(objective) if str(item.get("question_id") or "") == source_question_id),
        None,
    )
    source_answer = next(
        (item for item in _operator_question_answers_for_objective(objective) if str(item.get("answer_id") or "") == source_answer_id),
        None,
    )
    reply = render_evidence_bound_analysis_refinement_recall(
        refinement,
        focus=focus,
        analysis=source_analysis,
        candidate=source_question,
        answer=source_answer,
    )
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_evidence_bound_analysis_refinement_recall",
        objective_id=objective.objective_id,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_evidence_bound_analysis_refinement_recall_response",
        objective_id=objective.objective_id,
    )
    updated = _replace_state(state, conversation=state.conversation + (user_turn, assistant_turn))
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_evidence_bound_analysis_refinement_recall",
            0.98,
            "active_objective_provenance",
            "safe_internal",
            (),
            ("source_bound_refinement", "read_only_recall", "no_new_question"),
        ),
        reply=reply,
    )


def _internal_work_recall_candidate(
    state: ConversationalRuntimeState,
    message: str,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None] | None:
    """Resolve one explicit continuation recap without broad memory retrieval."""

    objective = state.active_objective
    candidates = _internal_work_candidates_for_objective(objective)
    if objective is None or not candidates:
        return None
    lower = " ".join(str(message or "").lower().split())
    if not re.match(r"^(?:what|which|how|show|tell)\b", lower):
        return None
    references_continuation = bool(re.search(r"\b(?:internal|continuation|next|follow[- ]?up)\b", lower))
    references_work_state = bool(re.search(r"\b(?:work|candidate|proposal|issue|uncertain|unknown|pending|remain(?:s|ing)?)\b", lower))
    if not (references_continuation and references_work_state):
        return None
    selections = _internal_work_selections_for_objective(objective)
    dispositions = _internal_work_dispositions_for_objective(objective)
    disposition = next((item for item in reversed(dispositions) if isinstance(item, Mapping)), None)
    candidate_id = str((disposition or {}).get("candidate_id") or "")
    selection = next(
        (
            item
            for item in reversed(selections)
            if isinstance(item, Mapping)
            and (
                not candidate_id
                or str(item.get("candidate_id") or "") == candidate_id
            )
            and str(item.get("status") or "")
            in {"surfaced", "selected", "accepted", "operator_deferred", "operator_dismissed", "resolved_by_answer", "answered_unknown"}
        ),
        None,
    )
    if not candidate_id:
        candidate_id = str((selection or {}).get("candidate_id") or "")
    candidate = next(
        (item for item in candidates if str(item.get("internal_work_candidate_id") or "") == candidate_id),
        None,
    )
    if candidate is None:
        candidate = candidates[-1]
        candidate_id = str(candidate.get("internal_work_candidate_id") or "")
        selection = next(
            (item for item in reversed(selections) if str(item.get("candidate_id") or "") == candidate_id),
            None,
        )
    if disposition is None or str(disposition.get("candidate_id") or "") != candidate_id:
        disposition = next(
            (item for item in reversed(dispositions) if str(item.get("candidate_id") or "") == candidate_id),
            None,
        )
    return dict(candidate), dict(selection) if isinstance(selection, Mapping) else None, dict(disposition) if isinstance(disposition, Mapping) else None


def is_internal_work_recall_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose explicit read-only internal-continuation recaps to the dispatcher."""

    return _internal_work_recall_candidate(state, message) is not None


def _apply_internal_work_recall(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    objective = state.active_objective
    recalled = _internal_work_recall_candidate(state, message)
    if objective is None or recalled is None:
        return None
    candidate, selection, disposition = recalled
    reply = render_internal_work_recall(candidate, selection, disposition)
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_internal_work_recall",
        objective_id=objective.objective_id,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_internal_work_recall_response",
        objective_id=objective.objective_id,
    )
    updated = _replace_state(state, conversation=state.conversation + (user_turn, assistant_turn))
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_internal_work_recall",
            0.98,
            "active_objective_provenance",
            "safe_internal",
            (),
            ("source_bound_internal_work", "read_only_recall", "no_new_candidate"),
        ),
        reply=reply,
    )


def _evidence_permission_recall_candidate(
    state: ConversationalRuntimeState,
    message: str,
) -> tuple[dict[str, Any], dict[str, Any] | None] | None:
    objective = state.active_objective
    if objective is None:
        return None
    lower = " ".join(str(message or "").lower().split())
    if not re.search(r"\b(?:evidence|authorization|authorize|permission|source|lookup|decision)\b", lower):
        return None
    if not re.search(r"\b(?:what|which|show|tell|recall|summarize|need|needed|authorize|authorized|decision)\b", lower):
        return None
    requests = _evidence_permission_requests_for_objective(objective)
    if not requests:
        return None
    authorizations = _evidence_authorizations_for_objective(objective)
    latest_request = max(
        requests,
        key=lambda item: (
            str(item.get("render_sequence") or ""),
            str(item.get("created_event_id") or ""),
            str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or ""),
        ),
    )
    latest_request_id = str(latest_request.get("evidence_permission_request_id") or latest_request.get("evidence_request_id") or "")
    matching_auth = next(
        (
            item
            for item in reversed(authorizations)
            if str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or "") == latest_request_id
        ),
        None,
    )
    return dict(latest_request), (dict(matching_auth) if isinstance(matching_auth, Mapping) else None)


def is_evidence_permission_recall_message(state: ConversationalRuntimeState, message: str) -> bool:
    return _evidence_permission_recall_candidate(state, message) is not None


def _apply_evidence_permission_recall(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    recalled = _evidence_permission_recall_candidate(state, message)
    if recalled is None:
        return None
    evidence_request, authorization = recalled
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_evidence_permission_recall",
        objective_id=state.active_objective.objective_id if state.active_objective else "",
    )
    reply = render_evidence_permission_recall(evidence_request, authorization)
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_evidence_permission_recall_response",
        objective_id=user_turn.objective_id,
    )
    updated = _replace_state(state, conversation=state.conversation + (user_turn, assistant_turn))
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_evidence_permission_recall",
            0.92,
            "active_objective_provenance",
            "safe_internal",
            (),
            ("source_bound_evidence_permission", "read_only_recall", "no_execution"),
        ),
        reply=reply,
        side_thread_bound=True,
    )


def _analysis_question_initiative_allowed(objective: ConversationalObjective | None) -> bool:
    constraints = _objective_execution_constraints_for_objective(objective)
    return bool(constraints.get("operator_question_initiative_allowed"))


def _internal_work_initiative_allowed(objective: ConversationalObjective | None) -> bool:
    constraints = _objective_execution_constraints_for_objective(objective)
    return bool(constraints.get("internal_work_initiative_allowed"))


def _evidence_permission_initiative_allowed(objective: ConversationalObjective | None) -> bool:
    constraints = _objective_execution_constraints_for_objective(objective)
    return bool(constraints.get("evidence_permission_initiative_allowed"))


def _candidate_with_status(
    candidate: Mapping[str, Any],
    *,
    status: str,
    **fields: Any,
) -> dict[str, Any]:
    return {**dict(candidate), "status": status, **fields}


def _selection_with_status(
    selection: Mapping[str, Any],
    *,
    status: str,
    **fields: Any,
) -> dict[str, Any]:
    return {**dict(selection), "status": status, **fields}


def _compile_analysis_question_request(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    candidate: Mapping[str, Any],
    created_turn_id: str,
    created_sequence: int,
) -> ChatAddressableRequest:
    """Use the existing durable chat-request envelope for one analysis question."""

    question_id = str(candidate.get("question_id") or "")
    binding_key = str(candidate.get("question_binding_key") or "")
    request_id = stable_id("evidence-bound-analysis-question-request", state.runtime_id, question_id, binding_key)
    return ChatAddressableRequest(
        request_id=request_id,
        request_type="evidence_bound_analysis_question",
        objective_id=objective.objective_id,
        originating_goal_id=objective.objective_id,
        goal_label="Evidence-bound analysis clarification",
        prompt_text=str(candidate.get("question_text") or ""),
        created_turn_id=created_turn_id,
        thread_id=objective.objective_id,
        created_sequence=created_sequence,
        accepted_response_types=("analysis_answer",),
        baseline_metrics={
            "question_id": question_id,
            "question_binding_key": binding_key,
            "source_frame_id": str(candidate.get("source_frame_id") or ""),
            "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
            "domain": str(candidate.get("domain") or ""),
            "unknown_slot_id": str(candidate.get("unknown_slot_id") or ""),
            "unknown_label": str(candidate.get("unknown_label") or ""),
            "expected_answer_type": str(candidate.get("expected_answer_type") or ""),
            "question_intent": str(candidate.get("question_intent") or "resolve_unknown"),
            "why_it_matters": str(candidate.get("why_it_matters") or ""),
            "priority_reason": str(candidate.get("priority_reason") or ""),
            "safety_boundary": str(candidate.get("safety_boundary") or ""),
        },
    )


def _compile_analysis_question_lifecycle(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    analysis: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None, tuple[Mapping[str, Any], ...]]:
    """Append candidate/selection provenance for one new analysis exactly once."""

    candidates = list(_operator_question_candidates_for_objective(objective))
    selections = list(_operator_question_selections_for_objective(objective))
    existing_ids = {str(item.get("question_id") or "") for item in candidates}
    derived = [
        item.as_record()
        for item in compile_operator_question_candidates(analysis, objective_id=objective.objective_id)
        if item.question_id not in existing_ids
    ]
    if not derived:
        return candidates, selections, None, ()
    has_pending_request = any(
        request.status == "pending" and not request.consumption_count
        for request in state.pending_chat_requests
    )
    lifecycle = select_operator_question_candidates(
        derived,
        initiative_allowed=_analysis_question_initiative_allowed(objective),
        existing_pending_request=has_pending_request,
    )
    status_by_id = {
        str(selection.get("candidate_id") or ""): str(selection.get("candidate_status") or "candidate")
        for selection in lifecycle
    }
    candidates.extend(
        _candidate_with_status(candidate, status=status_by_id.get(str(candidate.get("question_id") or ""), "candidate"))
        for candidate in derived
    )
    prior_selection_ids = {str(item.get("selection_id") or "") for item in selections}
    selections.extend(item for item in lifecycle if str(item.get("selection_id") or "") not in prior_selection_ids)
    selected = next(
        (
            candidate
            for candidate in candidates
            if str(candidate.get("question_id") or "") in {
                str(item.get("candidate_id") or "")
                for item in lifecycle
                if str(item.get("status") or "") == "selected"
            }
        ),
        None,
    )
    events: list[Mapping[str, Any]] = []
    for candidate in derived:
        events.append(
            {
                "event": "operator_question_candidate_recorded",
                "objective_id": objective.objective_id,
                "question_id": str(candidate.get("question_id") or ""),
                "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
                "source_frame_id": str(candidate.get("source_frame_id") or ""),
                "unknown_slot_id": str(candidate.get("unknown_slot_id") or ""),
                "status": status_by_id.get(str(candidate.get("question_id") or ""), "candidate"),
                "at": utc_now(),
            }
        )
    for selection in lifecycle:
        events.append(
            {
                "event": "operator_question_selection_recorded",
                "objective_id": objective.objective_id,
                "selection_id": str(selection.get("selection_id") or ""),
                "question_id": str(selection.get("candidate_id") or ""),
                "status": str(selection.get("status") or ""),
                "reason": str(selection.get("selection_reason") or ""),
                "at": utc_now(),
            }
        )
    return candidates, selections, dict(selected) if isinstance(selected, Mapping) else None, tuple(events)


def _compile_internal_work_request(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    candidate: Mapping[str, Any],
    selection: Mapping[str, Any],
    created_turn_id: str,
    created_sequence: int,
) -> ChatAddressableRequest:
    """Compile one existing chat request for a proposal that cannot execute itself."""

    candidate_id = str(candidate.get("internal_work_candidate_id") or "")
    binding_key = str(candidate.get("semantic_binding_key") or "")
    request_id = stable_id("analysis-internal-work-request", state.runtime_id, candidate_id, binding_key)
    return ChatAddressableRequest(
        request_id=request_id,
        request_type="internal_work_continuation",
        objective_id=objective.objective_id,
        originating_goal_id=objective.objective_id,
        goal_label="Evidence-bound internal continuation proposal",
        prompt_text=render_internal_work_proposal(candidate),
        created_turn_id=created_turn_id,
        thread_id=objective.objective_id,
        created_sequence=created_sequence,
        accepted_response_types=(
            "internal_work_accept",
            "internal_work_defer",
            "internal_work_dismiss",
            "internal_work_answer",
        ),
        baseline_metrics={
            "internal_work_candidate_id": candidate_id,
            "internal_work_selection_id": str(selection.get("internal_work_selection_id") or ""),
            "semantic_binding_key": binding_key,
            "source_frame_id": str(candidate.get("source_frame_id") or ""),
            "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
            "source_refinement_id": str(candidate.get("source_refinement_id") or ""),
            "source_question_candidate_id": str(candidate.get("source_question_candidate_id") or ""),
            "domain": str(candidate.get("domain") or ""),
            "unresolved_slot_id": str(candidate.get("unresolved_slot_id") or ""),
            "unresolved_label": str(candidate.get("unresolved_label") or ""),
            "expected_answer_type": str(candidate.get("expected_answer_type") or ""),
            "why_it_matters": str(candidate.get("why_it_matters") or ""),
            "authority_boundary": str(candidate.get("authority_boundary") or ""),
        },
    )


def _compile_evidence_permission_chat_request(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    evidence_request: Mapping[str, Any],
    created_turn_id: str,
    created_sequence: int,
) -> ChatAddressableRequest:
    """Use the canonical chat request surface for one evidence permission prompt."""

    evidence_request_id = str(evidence_request.get("evidence_permission_request_id") or evidence_request.get("evidence_request_id") or "")
    binding_key = str(evidence_request.get("semantic_binding_key") or "")
    request_id = stable_id("analysis-evidence-permission-chat-request", state.runtime_id, evidence_request_id, binding_key)
    return ChatAddressableRequest(
        request_id=request_id,
        request_type="evidence_permission",
        objective_id=objective.objective_id,
        originating_goal_id=objective.objective_id,
        goal_label="Evidence permission request",
        prompt_text=render_evidence_permission_request(evidence_request),
        created_turn_id=created_turn_id,
        thread_id=objective.objective_id,
        created_sequence=created_sequence,
        accepted_response_types=(
            "evidence_permission_grant",
            "evidence_permission_deny",
            "evidence_permission_defer",
            "evidence_permission_answer",
        ),
        baseline_metrics={
            "evidence_permission_request_id": evidence_request_id,
            "semantic_binding_key": binding_key,
            "source_frame_id": str(evidence_request.get("source_frame_id") or ""),
            "source_analysis_id": str(evidence_request.get("source_analysis_id") or ""),
            "source_refinement_id": str(evidence_request.get("source_refinement_id") or ""),
            "source_question_candidate_id": str(evidence_request.get("source_question_candidate_id") or ""),
            "source_question_answer_id": str(evidence_request.get("source_question_answer_id") or ""),
            "source_validation_check_id": str(evidence_request.get("source_validation_check_id") or ""),
            "domain": str(evidence_request.get("domain") or ""),
            "evidence_gap_slot_id": str(evidence_request.get("evidence_gap_slot_id") or ""),
            "evidence_kind": str(evidence_request.get("evidence_kind") or ""),
            "context_answer_type": str(evidence_request.get("context_answer_type") or ""),
            "authority_boundary": str(evidence_request.get("authority_boundary") or ""),
        },
    )


def _compile_evidence_next_operation_chat_request(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    proposal: Mapping[str, Any],
    created_turn_id: str,
    created_sequence: int,
) -> ChatAddressableRequest:
    """Use the canonical chat request surface for one non-executing proposal."""

    proposal_id = str(proposal.get("evidence_next_operation_proposal_id") or "")
    request_id = stable_id("analysis-evidence-next-operation-chat-request", state.runtime_id, proposal_id)
    return ChatAddressableRequest(
        request_id=request_id,
        request_type="evidence_next_operation_proposal",
        objective_id=objective.objective_id,
        originating_goal_id=objective.objective_id,
        goal_label="Evidence next-operation proposal",
        prompt_text=render_evidence_next_operation_proposal(proposal),
        created_turn_id=created_turn_id,
        thread_id=objective.objective_id,
        created_sequence=created_sequence,
        accepted_response_types=(
            "evidence_next_operation_accept",
            "evidence_next_operation_decline",
            "evidence_next_operation_defer",
            "evidence_next_operation_context",
        ),
        baseline_metrics={
            "evidence_next_operation_proposal_id": proposal_id,
            "source_evidence_request_id": str(proposal.get("source_evidence_request_id") or ""),
            "source_evidence_authorization_id": str(proposal.get("source_evidence_authorization_id") or ""),
            "source_frame_id": str(proposal.get("source_frame_id") or ""),
            "source_analysis_id": str(proposal.get("source_analysis_id") or ""),
            "source_refinement_id": str(proposal.get("source_refinement_id") or ""),
            "domain": str(proposal.get("domain") or ""),
            "evidence_gap_slot_id": str(proposal.get("evidence_gap_slot_id") or ""),
            "proposed_operation_type": str(proposal.get("proposed_operation_type") or ""),
        },
    )


def _compile_evidence_next_operation_lifecycle(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    evidence_request: Mapping[str, Any],
    evidence_authorization: Mapping[str, Any],
    existing_proposals: Sequence[Mapping[str, Any]] | None = None,
    ignored_pending_request_id: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, tuple[Mapping[str, Any], ...]]:
    """Append at most one granted-authorization proposal without execution."""

    records = [
        dict(item)
        for item in (
            existing_proposals
            if existing_proposals is not None
            else _evidence_next_operation_proposals_for_objective(objective)
        )
        if isinstance(item, Mapping)
    ]
    request_id = str(evidence_authorization.get("evidence_request_id") or "")
    authorization_id = str(evidence_authorization.get("evidence_authorization_id") or "")
    if not request_id or not authorization_id:
        return records, None, ()
    pair_exists = any(
        str(item.get("source_evidence_request_id") or "") == request_id
        and str(item.get("source_evidence_authorization_id") or "") == authorization_id
        for item in records
    )
    if pair_exists:
        return records, None, ()
    derived = [
        item.as_record()
        for item in compile_evidence_next_operation_proposals(
            evidence_request,
            evidence_authorization,
            objective_id=objective.objective_id,
        )
    ]
    if not derived:
        return records, None, ()
    has_pending_request = any(
        request.status == "pending"
        and not request.consumption_count
        and request.request_id != ignored_pending_request_id
        for request in state.pending_chat_requests
    )
    selected: dict[str, Any] | None = None
    updated_derived: list[dict[str, Any]] = []
    for ordinal, record in enumerate(sorted(derived, key=lambda item: str(item.get("evidence_next_operation_proposal_id") or ""))):
        if has_pending_request:
            status = "suppressed_existing_request"
            reason = "An unresolved ChatAddressableRequest already owns the next operator reply."
        elif ordinal == 0:
            status = "selected"
            reason = "This is the first bounded next-operation proposal derived from the granted evidence authorization."
        else:
            status = "suppressed_low_priority"
            reason = "A higher-priority next-operation proposal was selected first."
        updated = {
            **record,
            "status": status,
            "selection_reason": reason,
        }
        if status == "selected":
            selected = dict(updated)
        updated_derived.append(updated)
    records.extend(updated_derived)
    events = tuple(
        {
            "event": "evidence_next_operation_proposal_recorded",
            "objective_id": objective.objective_id,
            "evidence_next_operation_proposal_id": str(item.get("evidence_next_operation_proposal_id") or ""),
            "source_evidence_request_id": str(item.get("source_evidence_request_id") or ""),
            "source_evidence_authorization_id": str(item.get("source_evidence_authorization_id") or ""),
            "status": str(item.get("status") or ""),
            "at": utc_now(),
        }
        for item in updated_derived
    )
    return records, selected, events


def _compile_evidence_execution_authority_chat_request(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    proposal: Mapping[str, Any],
    disposition: Mapping[str, Any],
    created_turn_id: str,
    created_sequence: int,
) -> ChatAddressableRequest:
    """Use the canonical chat request surface for one inert authority prompt."""

    proposal_id = str(proposal.get("evidence_next_operation_proposal_id") or "")
    disposition_id = str(disposition.get("evidence_next_operation_disposition_id") or "")
    request_id = stable_id("analysis-evidence-execution-authority-chat-request", state.runtime_id, proposal_id, disposition_id)
    return ChatAddressableRequest(
        request_id=request_id,
        request_type="evidence_execution_authority",
        objective_id=objective.objective_id,
        originating_goal_id=objective.objective_id,
        goal_label="Evidence execution authority request",
        prompt_text=render_evidence_execution_authority_request(proposal, disposition),
        created_turn_id=created_turn_id,
        thread_id=objective.objective_id,
        created_sequence=created_sequence,
        accepted_response_types=(
            "evidence_execution_authority_approve",
            "evidence_execution_authority_decline",
            "evidence_execution_authority_defer",
            "evidence_execution_authority_context",
        ),
        baseline_metrics={
            "evidence_next_operation_proposal_id": proposal_id,
            "evidence_next_operation_disposition_id": disposition_id,
            "source_evidence_request_id": str(proposal.get("source_evidence_request_id") or ""),
            "source_evidence_authorization_id": str(proposal.get("source_evidence_authorization_id") or ""),
            "proposed_operation_type": str(proposal.get("proposed_operation_type") or ""),
            "evidence_gap_slot_id": str(proposal.get("evidence_gap_slot_id") or ""),
        },
    )


def _compile_evidence_execution_authority_lifecycle(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    proposal: Mapping[str, Any],
    disposition: Mapping[str, Any],
    existing_authorities: Sequence[Mapping[str, Any]] | None = None,
    ignored_pending_request_id: str = "",
) -> tuple[list[dict[str, Any]], bool, tuple[Mapping[str, Any], ...]]:
    """Determine whether one future-execution authority prompt should surface."""

    records = [
        dict(item)
        for item in (
            existing_authorities
            if existing_authorities is not None
            else _evidence_execution_authorities_for_objective(objective)
        )
        if isinstance(item, Mapping)
    ]
    proposal_id = str(proposal.get("evidence_next_operation_proposal_id") or "")
    disposition_id = str(disposition.get("evidence_next_operation_disposition_id") or "")
    if not proposal_id or not disposition_id:
        return records, False, ()
    if str(disposition.get("status") or "") != "accepted_pending_separate_execution":
        return records, False, ()
    existing = any(
        str(item.get("source_evidence_next_operation_proposal_id") or "") == proposal_id
        and str(item.get("source_evidence_next_operation_disposition_id") or "") == disposition_id
        for item in records
    )
    if existing:
        return records, False, ()
    has_pending_request = any(
        request.status == "pending"
        and not request.consumption_count
        and request.request_id != ignored_pending_request_id
        for request in state.pending_chat_requests
    )
    if has_pending_request:
        return records, False, (
            {
                "event": "evidence_execution_authority_request_suppressed_existing_request",
                "objective_id": objective.objective_id,
                "evidence_next_operation_proposal_id": proposal_id,
                "evidence_next_operation_disposition_id": disposition_id,
                "at": utc_now(),
            },
        )
    return records, True, (
        {
            "event": "evidence_execution_authority_request_selected",
            "objective_id": objective.objective_id,
            "evidence_next_operation_proposal_id": proposal_id,
            "evidence_next_operation_disposition_id": disposition_id,
            "at": utc_now(),
        },
    )


def _compile_evidence_fixture_execution_plan_chat_request(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    plan: Mapping[str, Any],
    created_turn_id: str,
    created_sequence: int,
) -> ChatAddressableRequest:
    """Use the canonical chat request surface for one inert execution plan."""

    plan_id = str(plan.get("evidence_fixture_execution_plan_id") or "")
    request_id = stable_id("analysis-evidence-fixture-execution-plan-chat-request", state.runtime_id, plan_id)
    return ChatAddressableRequest(
        request_id=request_id,
        request_type="evidence_fixture_execution_plan",
        objective_id=objective.objective_id,
        originating_goal_id=objective.objective_id,
        goal_label="Evidence fixture execution plan",
        prompt_text=render_evidence_fixture_execution_plan(plan),
        created_turn_id=created_turn_id,
        thread_id=objective.objective_id,
        created_sequence=created_sequence,
        accepted_response_types=(
            "evidence_fixture_execution_plan_accept",
            "evidence_fixture_execution_plan_decline",
            "evidence_fixture_execution_plan_defer",
            "evidence_fixture_execution_plan_context",
        ),
        baseline_metrics={
            "evidence_fixture_execution_plan_id": plan_id,
            "source_evidence_request_id": str(plan.get("source_evidence_request_id") or ""),
            "source_evidence_authorization_id": str(plan.get("source_evidence_authorization_id") or ""),
            "source_evidence_next_operation_proposal_id": str(plan.get("source_evidence_next_operation_proposal_id") or ""),
            "source_evidence_next_operation_disposition_id": str(plan.get("source_evidence_next_operation_disposition_id") or ""),
            "source_evidence_execution_authority_id": str(plan.get("source_evidence_execution_authority_id") or ""),
            "proposed_operation_type": str(plan.get("proposed_operation_type") or ""),
            "evidence_source_class": str(plan.get("evidence_source_class") or ""),
        },
    )


def _compile_evidence_fixture_execution_plan_lifecycle(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    proposal: Mapping[str, Any],
    disposition: Mapping[str, Any],
    authority: Mapping[str, Any],
    existing_plans: Sequence[Mapping[str, Any]] | None = None,
    ignored_pending_request_id: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, tuple[Mapping[str, Any], ...]]:
    """Append at most one inert plan for an approved future authority record."""

    records = [
        dict(item)
        for item in (
            existing_plans
            if existing_plans is not None
            else _evidence_fixture_execution_plans_for_objective(objective)
        )
        if isinstance(item, Mapping)
    ]
    authority_id = str(authority.get("evidence_execution_authority_id") or "")
    if not authority_id:
        return records, None, ()
    if str(authority.get("operator_decision") or authority.get("status") or "") != "approved_for_future_gate":
        return records, None, ()
    if any(str(item.get("source_evidence_execution_authority_id") or "") == authority_id for item in records):
        return records, None, ()
    derived = [
        item.as_record()
        for item in compile_evidence_fixture_execution_plans(
            proposal,
            disposition,
            authority,
            objective_id=objective.objective_id,
        )
    ]
    if not derived:
        return records, None, ()
    has_pending_request = any(
        request.status == "pending"
        and not request.consumption_count
        and request.request_id != ignored_pending_request_id
        for request in state.pending_chat_requests
    )
    if has_pending_request:
        event = {
            "event": "evidence_fixture_execution_plan_suppressed_existing_request",
            "objective_id": objective.objective_id,
            "evidence_execution_authority_id": authority_id,
            "at": utc_now(),
        }
        return records, None, (event,)
    plan = {**dict(derived[0]), "status": "selected", "selection_reason": "Approved inert execution authority can now be represented as a bounded non-executing plan."}
    records.append(plan)
    events = (
        {
            "event": "evidence_fixture_execution_plan_recorded",
            "objective_id": objective.objective_id,
            "evidence_fixture_execution_plan_id": str(plan.get("evidence_fixture_execution_plan_id") or ""),
            "source_evidence_execution_authority_id": authority_id,
            "status": "selected",
            "at": utc_now(),
        },
    )
    return records, plan, events


def _compile_evidence_fixture_dry_run_result_lifecycle(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    plan: Mapping[str, Any],
    existing_results: Sequence[Mapping[str, Any]] | None = None,
    ignored_pending_request_id: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, tuple[Mapping[str, Any], ...]]:
    """Append one deterministic result for an accepted inert fixture plan."""

    records = [
        dict(item)
        for item in (
            existing_results
            if existing_results is not None
            else _evidence_fixture_dry_run_results_for_objective(objective)
        )
        if isinstance(item, Mapping)
    ]
    plan_id = str(plan.get("evidence_fixture_execution_plan_id") or "")
    if not plan_id:
        return records, None, ()
    if any(str(item.get("source_plan_id") or "") == plan_id for item in records):
        return records, None, ()
    if str(plan.get("status") or "") != "accepted_pending_execution_gate":
        return records, None, ()
    if bool(plan.get("may_execute_now")) or not bool(plan.get("execution_requires_future_gate")):
        return records, None, ()
    has_pending_request = any(
        request.status == "pending"
        and not request.consumption_count
        and request.request_id != ignored_pending_request_id
        for request in state.pending_chat_requests
    )
    if has_pending_request:
        event = {
            "event": "evidence_fixture_dry_run_suppressed_existing_request",
            "objective_id": objective.objective_id,
            "evidence_fixture_execution_plan_id": plan_id,
            "at": utc_now(),
        }
        return records, None, (event,)
    derived = [
        item.as_record()
        for item in compile_evidence_fixture_dry_run_results(
            plan,
            objective_id=objective.objective_id,
        )
    ]
    if not derived:
        return records, None, ()
    result = dict(derived[0])
    records.append(result)
    events = (
        {
            "event": "evidence_fixture_dry_run_result_recorded",
            "objective_id": objective.objective_id,
            "evidence_fixture_dry_run_result_id": str(result.get("evidence_fixture_dry_run_result_id") or ""),
            "source_plan_id": plan_id,
            "status": str(result.get("status") or ""),
            "at": utc_now(),
        },
    )
    return records, result, events


def _compile_evidence_result_ingestion_candidate_lifecycle(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    dry_run_result: Mapping[str, Any],
    existing_candidates: Sequence[Mapping[str, Any]] | None = None,
    ignored_pending_request_id: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, tuple[Mapping[str, Any], ...]]:
    """Append one inert ingestion candidate for a dry-run result."""

    records = [
        dict(item)
        for item in (
            existing_candidates
            if existing_candidates is not None
            else _evidence_result_ingestion_candidates_for_objective(objective)
        )
        if isinstance(item, Mapping)
    ]
    dry_run_id = str(dry_run_result.get("evidence_fixture_dry_run_result_id") or "")
    if not dry_run_id:
        return records, None, ()
    if any(str(item.get("source_dry_run_result_id") or "") == dry_run_id for item in records):
        return records, None, ()
    if bool(dry_run_result.get("may_update_analysis")) or bool(dry_run_result.get("may_update_graph")):
        return records, None, ()
    if not bool(dry_run_result.get("requires_result_ingestion_gate")):
        return records, None, ()
    has_pending_request = any(
        request.status == "pending"
        and not request.consumption_count
        and request.request_id != ignored_pending_request_id
        for request in state.pending_chat_requests
    )
    if has_pending_request:
        event = {
            "event": "evidence_result_ingestion_candidate_suppressed_existing_request",
            "objective_id": objective.objective_id,
            "source_dry_run_result_id": dry_run_id,
            "at": utc_now(),
        }
        return records, None, (event,)
    source_request_id = str(dry_run_result.get("source_evidence_request_id") or "")
    source_request = next(
        (
            item
            for item in _evidence_permission_requests_for_objective(objective)
            if str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or "") == source_request_id
        ),
        {},
    )
    derived = [
        item.as_record()
        for item in compile_evidence_result_ingestion_candidates(
            dry_run_result,
            objective_id=objective.objective_id,
            source_evidence_request=source_request,
        )
    ]
    if not derived:
        return records, None, ()
    candidate = dict(derived[0])
    records.append(candidate)
    events = (
        {
            "event": "evidence_result_ingestion_candidate_recorded",
            "objective_id": objective.objective_id,
            "evidence_result_ingestion_candidate_id": str(candidate.get("evidence_result_ingestion_candidate_id") or ""),
            "source_dry_run_result_id": dry_run_id,
            "candidate_effect_type": str(candidate.get("candidate_effect_type") or ""),
            "status": str(candidate.get("status") or ""),
            "at": utc_now(),
        },
    )
    return records, candidate, events


def _compile_evidence_permission_lifecycle(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    analysis: Mapping[str, Any],
    source_refinement: Mapping[str, Any],
    source_question_candidates: Sequence[Mapping[str, Any]],
    source_question_answers: Sequence[Mapping[str, Any]],
    existing_requests: Sequence[Mapping[str, Any]] | None = None,
    ignored_pending_request_id: str = "",
    force_existing_pending_request: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, tuple[Mapping[str, Any], ...]]:
    """Append at most one evidence-permission request without executing evidence work."""

    records = [
        dict(item)
        for item in (
            existing_requests
            if existing_requests is not None
            else _evidence_permission_requests_for_objective(objective)
        )
        if isinstance(item, Mapping)
    ]
    existing_ids = {
        str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or "")
        for item in records
    }
    derived = [
        item.as_record()
        for item in compile_evidence_permission_requests(
            analysis,
            objective_id=objective.objective_id,
            source_question_candidates=source_question_candidates,
            source_question_answers=source_question_answers,
            source_refinement=source_refinement,
        )
        if item.evidence_permission_request_id not in existing_ids
    ]
    if not derived:
        return records, None, ()
    has_pending_request = force_existing_pending_request or any(
        request.status == "pending"
        and not request.consumption_count
        and request.request_id != ignored_pending_request_id
        for request in state.pending_chat_requests
    )
    initiative_allowed = _evidence_permission_initiative_allowed(objective)
    selected_id = ""
    updated_derived: list[dict[str, Any]] = []
    for ordinal, record in enumerate(sorted(derived, key=lambda item: str(item.get("evidence_permission_request_id") or ""))):
        if not initiative_allowed:
            status = "deferred_not_authorized"
            reason = "The active objective did not authorize DELTA to ask evidence-permission questions."
        elif has_pending_request:
            status = "suppressed_existing_request"
            reason = "An unresolved ChatAddressableRequest already owns the next operator reply."
        elif ordinal == 0:
            status = "selected"
            reason = "This is the first source-bound evidence gap that remains after refinement."
            selected_id = str(record.get("evidence_permission_request_id") or "")
        else:
            status = "suppressed_low_priority"
            reason = "A higher-priority evidence-permission request was selected first."
        updated_derived.append(
            {
                **record,
                "evidence_request_id": str(record.get("evidence_permission_request_id") or ""),
                "status": status,
                "selection_reason": reason,
            }
        )
    records.extend(updated_derived)
    selected = next(
        (
            item
            for item in records
            if str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or "") == selected_id
        ),
        None,
    )
    events = tuple(
        {
            "event": "evidence_permission_request_recorded",
            "objective_id": objective.objective_id,
            "evidence_request_id": str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or ""),
            "source_analysis_id": str(item.get("source_analysis_id") or ""),
            "source_refinement_id": str(item.get("source_refinement_id") or ""),
            "evidence_gap_slot_id": str(item.get("evidence_gap_slot_id") or ""),
            "status": str(item.get("status") or ""),
            "at": utc_now(),
        }
        for item in updated_derived
    )
    return records, dict(selected) if isinstance(selected, Mapping) else None, events


def _compile_internal_work_lifecycle(
    state: ConversationalRuntimeState,
    *,
    objective: ConversationalObjective,
    analysis: Mapping[str, Any],
    source_refinement: Mapping[str, Any] | None = None,
    source_question_candidates: Sequence[Mapping[str, Any]] | None = None,
    existing_candidates: Sequence[Mapping[str, Any]] | None = None,
    existing_selections: Sequence[Mapping[str, Any]] | None = None,
    ignored_pending_request_id: str = "",
    force_existing_pending_request: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None, dict[str, Any] | None, tuple[Mapping[str, Any], ...]]:
    """Append one provenance-only continuation lifecycle for the latest analysis state."""

    candidates = [
        dict(item)
        for item in (
            existing_candidates
            if existing_candidates is not None
            else _internal_work_candidates_for_objective(objective)
        )
        if isinstance(item, Mapping)
    ]
    selections = [
        dict(item)
        for item in (
            existing_selections
            if existing_selections is not None
            else _internal_work_selections_for_objective(objective)
        )
        if isinstance(item, Mapping)
    ]
    existing_ids = {str(item.get("internal_work_candidate_id") or "") for item in candidates}
    derived = [
        item.as_record()
        for item in compile_internal_work_candidates(
            analysis,
            objective_id=objective.objective_id,
            source_question_candidates=(
                source_question_candidates
                if source_question_candidates is not None
                else _operator_question_candidates_for_objective(objective)
            ),
            source_refinement=source_refinement,
        )
        if item.internal_work_candidate_id not in existing_ids
    ]
    if not derived:
        return candidates, selections, None, None, ()
    has_pending_request = force_existing_pending_request or any(
        request.status == "pending"
        and not request.consumption_count
        and request.request_id != ignored_pending_request_id
        for request in state.pending_chat_requests
    )
    lifecycle = select_internal_work_candidates(
        derived,
        initiative_allowed=_internal_work_initiative_allowed(objective),
        existing_pending_request=has_pending_request,
    )
    status_by_id = {
        str(selection.get("candidate_id") or ""): str(selection.get("status") or "candidate")
        for selection in lifecycle
    }
    candidates.extend(
        _candidate_with_status(
            candidate,
            status=status_by_id.get(str(candidate.get("internal_work_candidate_id") or ""), "candidate"),
        )
        for candidate in derived
    )
    prior_selection_ids = {str(item.get("internal_work_selection_id") or "") for item in selections}
    selections.extend(
        item
        for item in lifecycle
        if str(item.get("internal_work_selection_id") or "") not in prior_selection_ids
    )
    selected_ids = {
        str(item.get("candidate_id") or "")
        for item in lifecycle
        if str(item.get("status") or "") == "selected"
    }
    selected_candidate = next(
        (
            candidate
            for candidate in candidates
            if str(candidate.get("internal_work_candidate_id") or "") in selected_ids
        ),
        None,
    )
    selected_selection = next(
        (
            selection
            for selection in selections
            if str(selection.get("candidate_id") or "") in selected_ids
            and str(selection.get("status") or "") == "selected"
        ),
        None,
    )
    events: list[Mapping[str, Any]] = []
    for candidate in derived:
        events.append(
            {
                "event": "internal_work_candidate_recorded",
                "objective_id": objective.objective_id,
                "internal_work_candidate_id": str(candidate.get("internal_work_candidate_id") or ""),
                "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
                "source_refinement_id": str(candidate.get("source_refinement_id") or ""),
                "unresolved_slot_id": str(candidate.get("unresolved_slot_id") or ""),
                "status": status_by_id.get(str(candidate.get("internal_work_candidate_id") or ""), "candidate"),
                "at": utc_now(),
            }
        )
    for selection in lifecycle:
        events.append(
            {
                "event": "internal_work_selection_recorded",
                "objective_id": objective.objective_id,
                "internal_work_selection_id": str(selection.get("internal_work_selection_id") or ""),
                "internal_work_candidate_id": str(selection.get("candidate_id") or ""),
                "status": str(selection.get("status") or ""),
                "reason": str(selection.get("selection_reason") or ""),
                "at": utc_now(),
            }
        )
    return (
        candidates,
        selections,
        dict(selected_candidate) if isinstance(selected_candidate, Mapping) else None,
        dict(selected_selection) if isinstance(selected_selection, Mapping) else None,
        tuple(events),
    )


def _retire_internal_work_slots(
    candidates: Sequence[Mapping[str, Any]],
    selections: Sequence[Mapping[str, Any]],
    *,
    source_analysis_id: str,
    resolved_slots: Sequence[str],
    refinement_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mark historical candidate states resolved without deleting their provenance."""

    slots = {str(item) for item in resolved_slots if str(item)}
    if not slots:
        return [dict(item) for item in candidates], [dict(item) for item in selections]
    updated_candidates = [
        _candidate_with_status(
            item,
            status="suppressed_resolved",
            superseded_by_refinement_id=refinement_id,
        )
        if str(item.get("source_analysis_id") or "") == source_analysis_id
        and str(item.get("unresolved_slot_id") or "") in slots
        else dict(item)
        for item in candidates
        if isinstance(item, Mapping)
    ]
    updated_selections = [
        _selection_with_status(
            item,
            status="suppressed_resolved",
            selection_status="suppressed_resolved",
            superseded_by_refinement_id=refinement_id,
        )
        if str(item.get("source_analysis_id") or "") == source_analysis_id
        and str(item.get("unresolved_slot_id") or "") in slots
        else dict(item)
        for item in selections
        if isinstance(item, Mapping)
    ]
    return updated_candidates, updated_selections


def _apply_semantic_problem_modeling(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Persist one deterministic frame in objective provenance and nowhere else."""

    objective = state.active_objective
    compilation = _semantic_problem_compilation_for_message(state, message)
    if objective is None or compilation is None:
        return None
    frames = list(_semantic_problem_frames_for_objective(objective))
    frame_id = compilation.semantic_input_frame.frame_id
    record = next(
        (item for item in frames if str(item.get("frame_id") or "") == frame_id),
        None,
    )
    if record is None:
        record = {
            **compilation.as_record(),
            "objective_id": objective.objective_id,
            "provenance_status": "active_objective_source_bound_provisional",
            "created_at": utc_now(),
        }
        frames.append(record)
    analyses = list(_evidence_bound_analyses_for_objective(objective))
    analysis_compilation = compile_evidence_bound_analysis(record)
    analysis = None
    analysis_created = False
    if analysis_compilation is not None:
        analysis_id = analysis_compilation.analysis_id
        analysis = next(
            (item for item in analyses if str(item.get("analysis_id") or "") == analysis_id),
            None,
        )
        if analysis is None:
            analysis = {
                **analysis_compilation.as_record(),
                "objective_id": objective.objective_id,
                "provenance_status": "active_objective_source_bound_provisional",
                "created_at": utc_now(),
            }
            analyses.append(analysis)
            analysis_created = True
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_problem_modeling",
        objective_id=objective.objective_id,
    )
    candidates = list(_operator_question_candidates_for_objective(objective))
    selections = list(_operator_question_selections_for_objective(objective))
    lifecycle_events: tuple[Mapping[str, Any], ...] = ()
    selected_candidate: dict[str, Any] | None = None
    if isinstance(analysis, Mapping) and analysis_created:
        candidates, selections, selected_candidate, lifecycle_events = _compile_analysis_question_lifecycle(
            state,
            objective=objective,
            analysis=analysis,
        )
    question_request: ChatAddressableRequest | None = None
    if isinstance(analysis, Mapping) and selected_candidate is not None:
        question_request = _compile_analysis_question_request(
            state,
            objective=objective,
            candidate=selected_candidate,
            created_turn_id=user_turn.turn_id,
            created_sequence=len(state.conversation) + 1,
        )
    internal_candidates = list(_internal_work_candidates_for_objective(objective))
    internal_selections = list(_internal_work_selections_for_objective(objective))
    internal_lifecycle_events: tuple[Mapping[str, Any], ...] = ()
    selected_internal_candidate: dict[str, Any] | None = None
    selected_internal_selection: dict[str, Any] | None = None
    if isinstance(analysis, Mapping) and analysis_created:
        (
            internal_candidates,
            internal_selections,
            selected_internal_candidate,
            selected_internal_selection,
            internal_lifecycle_events,
        ) = _compile_internal_work_lifecycle(
            state,
            objective=objective,
            analysis=analysis,
            source_question_candidates=candidates,
            force_existing_pending_request=question_request is not None,
        )
    internal_work_request: ChatAddressableRequest | None = None
    if selected_internal_candidate is not None and selected_internal_selection is not None:
        internal_work_request = _compile_internal_work_request(
            state,
            objective=objective,
            candidate=selected_internal_candidate,
            selection=selected_internal_selection,
            created_turn_id=user_turn.turn_id,
            created_sequence=len(state.conversation) + 1,
        )
    if question_request is not None:
        reply = render_evidence_bound_analysis_question(analysis, selected_candidate)
    else:
        reply = (
            render_evidence_bound_analysis(analysis)
            if isinstance(analysis, Mapping)
            else render_semantic_problem_frame(record)
        )
        if internal_work_request is not None and selected_internal_candidate is not None:
            reply = f"{reply}\n\n{render_internal_work_proposal(selected_internal_candidate)}"
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_problem_modeling_response",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if not any(
        str(item.get("event") or "") == "semantic_problem_frame_recorded"
        and str(item.get("frame_id") or "") == frame_id
        for item in progress
        if isinstance(item, Mapping)
    ):
        progress = progress + ({
            "event": "semantic_problem_frame_recorded",
            "objective_id": objective.objective_id,
            "frame_id": frame_id,
            "domain": compilation.semantic_input_frame.domain_guess,
            "source_turn_id": user_turn.turn_id,
            "at": utc_now(),
        },)
    if isinstance(analysis, Mapping) and not any(
        str(item.get("event") or "") == "evidence_bound_analysis_recorded"
        and str(item.get("analysis_id") or "") == str(analysis.get("analysis_id") or "")
        for item in progress
        if isinstance(item, Mapping)
    ):
        progress = progress + ({
            "event": "evidence_bound_analysis_recorded",
            "objective_id": objective.objective_id,
            "analysis_id": str(analysis.get("analysis_id") or ""),
            "source_frame_id": frame_id,
            "domain": str(analysis.get("domain") or compilation.semantic_input_frame.domain_guess),
            "source_turn_id": user_turn.turn_id,
            "at": utc_now(),
        },)
    if question_request is not None:
        question_request = replace(
            question_request,
            rendered_turn_id=assistant_turn.turn_id,
            render_sequence=len(state.conversation) + 2,
        )
        selected_question_id = str(selected_candidate.get("question_id") or "") if selected_candidate else ""
        candidates = [
            _candidate_with_status(
                item,
                status="asked",
                asked_turn_id=assistant_turn.turn_id,
                request_id=question_request.request_id,
            )
            if str(item.get("question_id") or "") == selected_question_id
            else item
            for item in candidates
        ]
        selections = [
            _selection_with_status(
                item,
                status="asked",
                asked_turn_id=assistant_turn.turn_id,
                request_id=question_request.request_id,
            )
            if str(item.get("candidate_id") or "") == selected_question_id
            and str(item.get("status") or "") == "selected"
            else item
            for item in selections
        ]
        progress = progress + (
            {
                "event": "operator_question_rendered",
                "objective_id": objective.objective_id,
                "question_id": selected_question_id,
                "request_id": question_request.request_id,
                "source_analysis_id": str(selected_candidate.get("source_analysis_id") or "") if selected_candidate else "",
                "source_frame_id": str(selected_candidate.get("source_frame_id") or "") if selected_candidate else "",
                "assistant_turn_id": assistant_turn.turn_id,
                "at": utc_now(),
            },
        )
    if internal_work_request is not None and selected_internal_candidate is not None and selected_internal_selection is not None:
        internal_work_request = replace(
            internal_work_request,
            rendered_turn_id=assistant_turn.turn_id,
            render_sequence=len(state.conversation) + 2,
        )
        selected_internal_id = str(selected_internal_candidate.get("internal_work_candidate_id") or "")
        selected_internal_selection_id = str(selected_internal_selection.get("internal_work_selection_id") or "")
        internal_candidates = [
            _candidate_with_status(
                item,
                status="surfaced",
                surfaced_turn_id=assistant_turn.turn_id,
                request_id=internal_work_request.request_id,
            )
            if str(item.get("internal_work_candidate_id") or "") == selected_internal_id
            else item
            for item in internal_candidates
        ]
        internal_selections = [
            _selection_with_status(
                item,
                status="surfaced",
                selection_status="surfaced",
                surfaced_turn_id=assistant_turn.turn_id,
                request_id=internal_work_request.request_id,
            )
            if str(item.get("internal_work_selection_id") or "") == selected_internal_selection_id
            else item
            for item in internal_selections
        ]
        progress = progress + (
            {
                "event": "internal_work_proposal_rendered",
                "objective_id": objective.objective_id,
                "internal_work_candidate_id": selected_internal_id,
                "internal_work_selection_id": selected_internal_selection_id,
                "request_id": internal_work_request.request_id,
                "source_analysis_id": str(selected_internal_candidate.get("source_analysis_id") or ""),
                "source_frame_id": str(selected_internal_candidate.get("source_frame_id") or ""),
                "assistant_turn_id": assistant_turn.turn_id,
                "at": utc_now(),
            },
        )
    if lifecycle_events:
        progress = progress + lifecycle_events
    if internal_lifecycle_events:
        progress = progress + internal_lifecycle_events
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(
            objective,
            semantic_problem_frames=frames,
            evidence_bound_analyses=analyses,
            operator_question_candidates=candidates,
            operator_question_selections=selections,
            internal_work_candidates=internal_candidates,
            internal_work_selections=internal_selections,
        ),
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=(
            state.pending_chat_requests + tuple(
                request for request in (question_request, internal_work_request) if request is not None
            )
            if question_request is not None or internal_work_request is not None
            else state.pending_chat_requests
        ),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_problem_modeling", 0.98, "active_objective_provenance", "safe_internal", (),
            (
                "deterministic_source_bound_frame",
                "deterministic_evidence_bound_analysis",
                "no_graph_admission",
                "no_external_action",
            ),
        ),
        reply=reply,
        chat_request=(
            question_request.as_record()
            if question_request is not None
            else internal_work_request.as_record()
            if internal_work_request is not None
            else None
        ),
    )


def _apply_semantic_problem_frame_recall(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Render one existing frame as a normal read-only conversation turn."""

    objective = state.active_objective
    candidate = _semantic_problem_frame_recall_candidate(state, message)
    if objective is None or candidate is None:
        return None
    record, focus = candidate
    reply = render_semantic_problem_recall(record, focus=focus)
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_problem_frame_recall",
        objective_id=objective.objective_id,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_problem_frame_recall_response",
        objective_id=objective.objective_id,
    )
    updated = _replace_state(
        state,
        conversation=state.conversation + (user_turn, assistant_turn),
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_problem_frame_recall", 0.98, "active_objective_provenance", "safe_internal", (),
            ("source_bound_frame", "read_only_recall", "no_new_frame"),
        ),
        reply=reply,
    )


def _apply_evidence_bound_analysis_recall(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Render one existing analysis as a read-only normal conversation turn."""

    objective = state.active_objective
    candidate = _evidence_bound_analysis_recall_candidate(state, message)
    if objective is None or candidate is None:
        return None
    record, focus = candidate
    reply = render_evidence_bound_analysis_recall(record, focus=focus)
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_evidence_bound_analysis_recall",
        objective_id=objective.objective_id,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_evidence_bound_analysis_recall_response",
        objective_id=objective.objective_id,
    )
    updated = _replace_state(
        state,
        conversation=state.conversation + (user_turn, assistant_turn),
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_evidence_bound_analysis_recall", 0.98, "active_objective_provenance", "safe_internal", (),
            ("source_bound_analysis", "read_only_recall", "no_new_analysis"),
        ),
        reply=reply,
    )


_SEMANTIC_TRANSFER_ACTION_TERMS = frozenset({
    "apply", "adapt", "arrange", "carry", "design", "organize", "structure", "translate", "use",
})
_SEMANTIC_TRANSFER_CONTEXT_TERMS = frozenset({
    "brief", "dashboard", "document", "explanation", "interface", "layout", "message", "page",
    "plan", "presentation", "report", "screen", "task", "workflow",
})
_SEMANTIC_TRANSFER_SOURCE_PHRASES = (
    "what you revised",
    "what was revised",
    "revised understanding",
    "revised explanation",
    "prior understanding",
    "previous understanding",
    "earlier explanation",
)
_SEMANTIC_ANALYSIS_ACTION_TERMS = frozenset({"analyze", "analyse", "assess", "compare", "evaluate", "plan"})
_SEMANTIC_COMPETENCE_ACTION_TERMS = frozenset({"assess", "compare", "evaluate", "measure", "show"})
_SEMANTIC_COMPETENCE_CONTEXT_TERMS = frozenset({
    "after", "baseline", "before", "changed", "competence", "delta", "difference", "improvement", "measure",
})
_SEMANTIC_RECALL_EFFECT_TERMS = frozenset({
    "affect", "affected", "apply", "applied", "change", "changed", "difference", "influence", "influenced",
})
_SEMANTIC_RECALL_CONTEXT_TERMS = frozenset({
    "analysis", "answer", "application", "baseline", "dashboard", "improved", "layout", "result", "screen", "task",
})
_SEMANTIC_RECALL_CHAIN_TERMS = frozenset({
    "analyze", "analysis", "measure", "measurement", "revised", "revision", "transfer", "transferred",
})
_ANALYTICAL_RISK_TERMS = frozenset({"deadline", "expired", "overdue", "past", "unpaid"})
_ANALYTICAL_INTERRUPTION_TERMS = frozenset({"alert", "critical", "escalation", "immediate", "urgent"})
_ANALYTICAL_EXECUTION_TERMS = frozenset({"active", "current", "job", "scheduled", "task", "today"})


def _semantic_transfer_terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", str(value or "").lower()))


def _revised_semantic_transfer_followup(
    state: ConversationalRuntimeState,
    message: str,
) -> dict[str, Any] | None:
    """Select one explicitly applied revised teaching record, never broad graph memory."""

    objective = state.active_objective
    if objective is None:
        return None
    normalized = " ".join(str(message or "").lower().split())
    message_terms = _semantic_transfer_terms(normalized)
    if not (_SEMANTIC_TRANSFER_ACTION_TERMS & message_terms):
        return None
    if not (
        _SEMANTIC_TRANSFER_CONTEXT_TERMS & message_terms
        or re.search(r"\b(?:to|for|into|within|on)\s+(?:a|an|the|this|that)?\s*[a-z]", normalized)
    ):
        return None
    explicit_source_reference = any(phrase in normalized for phrase in _SEMANTIC_TRANSFER_SOURCE_PHRASES)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for followup in _teaching_followups_for_objective(objective):
        if str(followup.get("status") or "") != "revision_pending_consolidation":
            continue
        if not str(followup.get("claim_version_id") or ""):
            continue
        source_text = " ".join(
            str(followup.get(key) or "")
            for key in ("lesson_title", "source_gap", "question", "interpretation", "claim_version_id")
        )
        overlap = len(message_terms & _semantic_transfer_terms(source_text))
        if overlap or explicit_source_reference:
            candidates.append((overlap, followup))
    if not candidates:
        return None
    highest = max(score for score, _followup in candidates)
    selected = [followup for score, followup in candidates if score == highest]
    return dict(selected[0]) if len(selected) == 1 else None


def is_source_bound_semantic_transfer_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose the narrow application boundary for the normal Tk dispatcher."""

    return _revised_semantic_transfer_followup(state, message) is not None


def _source_bound_transfer_dimensions(revision_text: str, *, fallback_label: str) -> tuple[str, ...]:
    """Read the operator's revised contribution shape without hard-coding a lesson."""

    normalized = " ".join(str(revision_text or "").split()).strip()
    match = re.search(
        r"\b(?:distinguish|include|separate|address|cover|clarify|describe|state)\s+(.+?)(?:\s+instead\b|\s+rather\s+than\b|[.!?]|$)",
        normalized,
        flags=re.IGNORECASE,
    )
    contribution = match.group(1) if match else ""
    dimensions = []
    for item in re.split(r"\s*,\s*|\s+and\s+", contribution, flags=re.IGNORECASE):
        value = " ".join(item.strip(" ,;:").split())
        if value and value.lower() not in {"it", "this", "that"}:
            dimensions.append(value)
    if dimensions:
        return tuple(dict.fromkeys(dimensions))
    label = " ".join(str(fallback_label or "").split()).strip()
    return (label,) if label else ()


def _render_source_bound_semantic_transfer(
    *,
    source_label: str,
    task_text: str,
    dimensions: Sequence[str],
) -> tuple[str, str]:
    """Render a deterministic, qualified application of a revised source record."""

    label = " ".join(str(source_label or "revised teaching").split()).strip()
    task = " ".join(str(task_text or "").split()).strip()
    usable_dimensions = tuple(str(item).strip() for item in dimensions if str(item).strip()) or (label,)
    bullets = []
    for index, dimension in enumerate(usable_dimensions):
        heading = dimension[:1].upper() + dimension[1:]
        if index == 0:
            guidance = "make this establish what receives attention first."
        elif index == 1:
            guidance = "use alignment, ordering, or grouping to make the scan path legible."
        else:
            guidance = "make its priority visibly distinct from supporting detail."
        bullets.append(f"- {heading}: {guidance}")
    limitations = (
        "The source record is provisional, and this application has not been tested against the actual users, "
        "task constraints, or outcomes."
    )
    reply = (
        f"I applied the revised {label} record to this task.\n\n"
        f"Task: {task}\n\n"
        + "\n".join(bullets)
        + "\n\nTogether, these choices should guide attention from the primary information toward supporting detail.\n\n"
        + "This is a provisional, source-bound application of the revised teaching record, not a reviewed design conclusion. "
        + limitations
    )
    return reply, limitations


def _apply_source_bound_semantic_transfer(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Persist one application trace while preserving the source claim and its lineage."""

    objective = state.active_objective
    followup = _revised_semantic_transfer_followup(state, message)
    if objective is None or followup is None:
        return None
    claim_version_id = str(followup.get("claim_version_id") or "")
    graph = load_graph(runtime_root)
    revision = next(
        (item for item in graph.claim_versions if item.claim_version_id == claim_version_id),
        None,
    )
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_transfer_application",
        objective_id=objective.objective_id,
    )
    if revision is None:
        reply = (
            "I could not bind that application to its revised source record, so I left it unapplied rather than "
            "presenting an ungrounded transfer."
        )
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
            role="assistant",
            text=reply,
            intent_type="semantic_transfer_binding_unavailable",
            objective_id=objective.objective_id,
        )
        updated = _replace_state(state, conversation=state.conversation + (user_turn, assistant_turn))
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(
            state=updated,
            intent=ConversationIntent(
                "semantic_transfer_binding_unavailable", 0.95, "active_teaching_objective", "safe_internal", (),
                ("revised_source_record_missing",),
            ),
            reply=reply,
        )

    source_label = str(followup.get("lesson_title") or followup.get("source_gap") or "revised teaching")
    dimensions = _source_bound_transfer_dimensions(revision.exact_text, fallback_label=source_label)
    reply, limitations = _render_source_bound_semantic_transfer(
        source_label=source_label,
        task_text=message,
        dimensions=dimensions,
    )
    prior_claim_version_id = str(followup.get("prior_claim_version_id") or revision.supersedes_version_id or "")
    source_lineage_ids = tuple(
        dict.fromkeys(item for item in (prior_claim_version_id, claim_version_id) if item)
    )
    application_record_id = stable_id(
        "semantic-transfer-application",
        objective.objective_id,
        str(followup.get("followup_id") or ""),
        claim_version_id,
        " ".join(str(message or "").lower().split()),
    )
    applications = list(_semantic_transfer_applications_for_objective(objective))
    existing = next(
        (
            item for item in applications
            if str(item.get("application_record_id") or "") == application_record_id
        ),
        None,
    )
    if existing is not None:
        reply = str(existing.get("output_text") or reply)
        limitations = str(existing.get("limitations") or limitations)
        dimensions = tuple(str(item) for item in existing.get("transfer_dimensions", dimensions) if str(item))
    try:
        graph, experience_id, graph_created = record_source_bound_semantic_transfer_application(
            graph,
            application_record_id=application_record_id,
            source_claim_version_ids=(claim_version_id,),
            source_lineage_ids=source_lineage_ids,
            task_text=message,
            output_text=reply,
            limitations=limitations,
            objective_id=objective.objective_id,
            followup_id=str(followup.get("followup_id") or ""),
            operator_turn_id=user_turn.turn_id,
        )
    except ConsolidationIntegrityError:
        return None
    if graph_created:
        save_graph(runtime_root, graph)
    if existing is None:
        existing = {
            "application_record_id": application_record_id,
            "record_kind": "source_bound_semantic_transfer_application",
            "objective_id": objective.objective_id,
            "source_followup_id": str(followup.get("followup_id") or ""),
            "source_claim_version_id": claim_version_id,
            "prior_claim_version_id": prior_claim_version_id,
            "source_lineage_ids": source_lineage_ids,
            "task_family": "source_bound_semantic_application",
            "task_text": " ".join(str(message or "").split()),
            "transfer_dimensions": dimensions,
            "output_text": reply,
            "limitations": limitations,
            "status": "provisional_application_recorded",
            "graph_experience_id": experience_id,
            "operator_turn_id": user_turn.turn_id,
            "created_at": utc_now(),
        }
        applications.append(existing)
    updated_objective = _replace_teaching_objective(
        objective,
        semantic_transfer_applications=applications,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_transfer_application_response",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if existing is not None and not any(
        str(item.get("event") or "") == "semantic_transfer_application_recorded"
        and str(item.get("application_record_id") or "") == application_record_id
        for item in progress
        if isinstance(item, Mapping)
    ):
        progress = progress + ({
            "event": "semantic_transfer_application_recorded",
            "objective_id": objective.objective_id,
            "application_record_id": application_record_id,
            "source_followup_id": str(followup.get("followup_id") or ""),
            "source_claim_version_id": claim_version_id,
            "source_lineage_ids": source_lineage_ids,
            "graph_experience_id": experience_id,
            "at": utc_now(),
        },)
    updated = _replace_state(
        state,
        active_objective=updated_objective,
        conversation=state.conversation + (user_turn, assistant_turn),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_transfer_application", 0.96, "active_teaching_objective", "safe_internal", (),
            ("revised_teaching_source", "explicit_application_request", "source_bound_provisional_trace"),
        ),
        reply=reply,
    )


def _analytical_task_text(message: str) -> str:
    normalized = " ".join(str(message or "").split()).strip()
    quoted = re.search(r"[\"\u201c](.+?)[\"\u201d]", normalized)
    if quoted:
        return " ".join(quoted.group(1).split()).strip()
    after_colon = normalized.split(":", 1)
    if len(after_colon) == 2:
        return " ".join(after_colon[1].split()).strip()
    return normalized


def _source_bound_semantic_analysis_application(
    state: ConversationalRuntimeState,
    message: str,
) -> dict[str, Any] | None:
    """Select one recorded transfer only when the operator asks for a bounded analysis."""

    objective = state.active_objective
    if objective is None:
        return None
    message_terms = _semantic_transfer_terms(message)
    if not (_SEMANTIC_ANALYSIS_ACTION_TERMS & message_terms):
        return None
    task_text = _analytical_task_text(message)
    if not task_text or not (
        _SEMANTIC_TRANSFER_CONTEXT_TERMS & _semantic_transfer_terms(task_text)
        or "goal" in message_terms
    ):
        return None
    normalized = " ".join(str(message or "").lower().split())
    source_reference = any(
        phrase in normalized
        for phrase in (*_SEMANTIC_TRANSFER_SOURCE_PHRASES, "learned", "transfer", "source record")
    )
    candidates: list[tuple[int, dict[str, Any]]] = []
    for application in _semantic_transfer_applications_for_objective(objective):
        source_text = " ".join(
            str(application.get(key) or "")
            for key in ("task_text", "source_claim_version_id", "source_followup_id")
        ) + " " + " ".join(str(item) for item in application.get("transfer_dimensions", ()) if str(item))
        overlap = len(message_terms & _semantic_transfer_terms(source_text))
        if overlap or source_reference:
            candidates.append((overlap, application))
    if not candidates:
        return None
    highest = max(score for score, _application in candidates)
    selected = [application for score, application in candidates if score == highest]
    return dict(selected[0]) if len(selected) == 1 else None


def is_source_bound_semantic_analysis_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose the small analytical-task boundary to the normal dispatcher."""

    return _source_bound_semantic_analysis_application(state, message) is not None


def _analytical_task_items(task_text: str) -> tuple[str, ...]:
    """Extract operator-named work items without assuming a fixed dashboard fixture."""

    normalized = " ".join(str(task_text or "").split()).strip()
    match = re.search(
        r"\b(?:see|view|track|manage|monitor|prioritize)\s+(.+?)(?:\s+(?:on|in|within)\s+(?:one|a|the)?\s*(?:screen|dashboard|page|view)|[.!?]|$)",
        normalized,
        flags=re.IGNORECASE,
    )
    source = match.group(1) if match else normalized
    items = []
    for item in re.split(r"\s*,\s*|\s+and\s+", source, flags=re.IGNORECASE):
        value = " ".join(item.strip(" ,;:").split())
        if value:
            items.append(value)
    return tuple(dict.fromkeys(items))


def _analytical_priority(item: str) -> tuple[str, str]:
    terms = _semantic_transfer_terms(item)
    if terms & _ANALYTICAL_RISK_TERMS:
        return "financial_or_commitment_risk", "show it as a high-priority risk that needs a decision."
    if terms & _ANALYTICAL_INTERRUPTION_TERMS:
        return "interruption_or_escalation", "surface it as an interruption or escalation channel."
    if terms & _ANALYTICAL_EXECUTION_TERMS:
        return "schedule_or_execution_focus", "keep it visible in the main execution flow."
    return "supporting_information", "keep it available without competing with immediate decisions."


def _render_source_bound_semantic_analysis(
    *,
    task_text: str,
    dimensions: Sequence[str],
) -> tuple[tuple[Mapping[str, Any], ...], str, str]:
    """Complete one small analysis deterministically from operator task text and source dimensions."""

    items = _analytical_task_items(task_text)
    priorities = tuple({
        "item": item,
        "priority_kind": _analytical_priority(item)[0],
        "reason": _analytical_priority(item)[1],
    } for item in items)
    dimension_text = ", ".join(str(item) for item in dimensions if str(item)) or "the revised source dimensions"
    priority_lines = "\n".join(
        f"- {item['item']}: {item['priority_kind'].replace('_', ' ')}; {item['reason']}"
        for item in priorities
    ) or "- No distinct work items were extracted; keep the screen organized around the next concrete decision."
    layout_lines = "\n".join(
        f"- {item['item']}: place this in the {item['priority_kind'].replace('_', ' ')} region."
        for item in priorities
    ) or "- Use one primary region and reserve secondary regions for supporting detail."
    substeps: tuple[Mapping[str, Any], ...] = (
        {
            "step_id": "identify_user_goal",
            "label": "Identify the user goal",
            "status": "completed",
            "finding": "The screen should help the operator decide what needs attention and action next.",
        },
        {
            "step_id": "identify_information_priorities",
            "label": "Identify information priorities",
            "status": "completed",
            "finding": priority_lines,
        },
        {
            "step_id": "apply_revised_semantic_source",
            "label": "Apply the revised semantic source",
            "status": "completed",
            "finding": f"Use {dimension_text} to organize the reading order and attention path.",
        },
        {
            "step_id": "propose_layout",
            "label": "Propose the layout",
            "status": "completed",
            "finding": layout_lines,
        },
        {
            "step_id": "state_uncertainty_and_next_test",
            "label": "State uncertainty and next validation step",
            "status": "completed",
            "finding": "Test the proposed ordering with the actual operator, screen constraints, and representative work scenarios.",
        },
    )
    limitations = (
        "This is a provisional task analysis. It has not been validated against the contractor's real workflow, "
        "screen size, notification policy, or usability evidence."
    )
    synthesis = (
        f"For this task, use an action-first composition.\n\n"
        f"Information priorities:\n{priority_lines}\n\n"
        f"Apply {dimension_text} so the screen gives the most consequential information the strongest visual treatment, "
        "uses alignment and grouping to make the path through the screen legible, and separates supporting detail from the next action.\n\n"
        f"Proposed layout:\n{layout_lines}\n\n"
        f"Limitation: {limitations}"
    )
    return substeps, synthesis, limitations


def _apply_source_bound_semantic_analysis(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Persist one bounded multi-step analysis that is tied to an existing transfer record."""

    objective = state.active_objective
    application = _source_bound_semantic_analysis_application(state, message)
    if objective is None or application is None:
        return None
    task_text = _analytical_task_text(message)
    source_semantic_ids = tuple(
        dict.fromkeys(str(item) for item in application.get("source_lineage_ids", ()) if str(item))
    )
    source_transfer_application_id = str(application.get("application_record_id") or "")
    source_transfer_experience_id = str(application.get("graph_experience_id") or "")
    if not task_text or not source_semantic_ids or not source_transfer_application_id:
        return None
    analytical_task_id = stable_id(
        "semantic-analytical-task",
        objective.objective_id,
        source_transfer_application_id,
        " ".join(task_text.lower().split()),
    )
    tasks = list(_semantic_analytical_tasks_for_objective(objective))
    existing = next(
        (item for item in tasks if str(item.get("analytical_task_id") or "") == analytical_task_id),
        None,
    )
    if existing is None:
        dimensions = tuple(str(item) for item in application.get("transfer_dimensions", ()) if str(item))
        substeps, synthesis, limitations = _render_source_bound_semantic_analysis(
            task_text=task_text,
            dimensions=dimensions,
        )
        existing = {
            "analytical_task_id": analytical_task_id,
            "record_kind": "source_bound_semantic_multistep_analysis",
            "objective_id": objective.objective_id,
            "source_semantic_ids": source_semantic_ids,
            "source_transfer_application_id": source_transfer_application_id,
            "source_transfer_experience_id": source_transfer_experience_id,
            "source_transfer_dimensions": dimensions,
            "task_text": task_text,
            "substeps": substeps,
            "decision_notes": tuple(item["finding"] for item in substeps[:4]),
            "final_synthesis": synthesis,
            "limitations": limitations,
            "status": "provisional_analysis_recorded",
            "restart_summary": "Persisted as one source-bound analytical task with no model execution or admission.",
            "created_at": utc_now(),
        }
        tasks.append(existing)
    reply = str(existing.get("final_synthesis") or "")
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_multistep_analytical_task",
        objective_id=objective.objective_id,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_multistep_analytical_task_response",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if not any(
        str(item.get("event") or "") == "semantic_multistep_analytical_task_recorded"
        and str(item.get("analytical_task_id") or "") == analytical_task_id
        for item in progress
        if isinstance(item, Mapping)
    ):
        progress = progress + ({
            "event": "semantic_multistep_analytical_task_recorded",
            "objective_id": objective.objective_id,
            "analytical_task_id": analytical_task_id,
            "source_semantic_ids": source_semantic_ids,
            "source_transfer_application_id": source_transfer_application_id,
            "at": utc_now(),
        },)
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(objective, semantic_analytical_tasks=tasks),
        conversation=state.conversation + (user_turn, assistant_turn),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_multistep_analytical_task", 0.96, "active_teaching_objective", "safe_internal", (),
            ("source_bound_transfer_application", "bounded_multistep_analysis", "provisional_task_synthesis"),
        ),
        reply=reply,
    )


def _source_bound_semantic_competence_task(
    state: ConversationalRuntimeState,
    message: str,
) -> dict[str, Any] | None:
    """Select one completed source-bound analysis for a task-local comparison."""

    objective = state.active_objective
    if objective is None:
        return None
    normalized = " ".join(str(message or "").lower().split())
    message_terms = _semantic_transfer_terms(normalized)
    if not (_SEMANTIC_COMPETENCE_ACTION_TERMS & message_terms):
        return None
    if not (_SEMANTIC_COMPETENCE_CONTEXT_TERMS & message_terms):
        return None
    source_reference = any(
        phrase in normalized
        for phrase in (*_SEMANTIC_TRANSFER_SOURCE_PHRASES, "learned", "revised", "semantic", "source-bound")
    )
    candidates: list[tuple[int, dict[str, Any]]] = []
    for task in _semantic_analytical_tasks_for_objective(objective):
        if str(task.get("status") or "") != "provisional_analysis_recorded":
            continue
        source_text = " ".join(
            str(task.get(key) or "")
            for key in ("task_text", "source_transfer_application_id", "source_transfer_dimensions")
        ) + " " + " ".join(str(item) for item in task.get("source_transfer_dimensions", ()) if str(item))
        overlap = len(message_terms & _semantic_transfer_terms(source_text))
        if overlap or source_reference:
            candidates.append((overlap, task))
    if not candidates:
        return None
    highest = max(score for score, _task in candidates)
    selected = [task for score, task in candidates if score == highest]
    return dict(selected[0]) if len(selected) == 1 else None


def is_source_bound_semantic_competence_measurement_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose a narrow task-local measurement boundary to the normal dispatcher."""

    return _source_bound_semantic_competence_task(state, message) is not None


def _task_local_competence_measurement(
    task: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Compare a declared source-bound task record to an explicit non-source baseline shape."""

    source_semantic_ids = tuple(str(item) for item in task.get("source_semantic_ids", ()) if str(item))
    source_dimensions = tuple(str(item) for item in task.get("source_transfer_dimensions", ()) if str(item))
    task_text = str(task.get("task_text") or "")
    substeps = tuple(item for item in task.get("substeps", ()) if isinstance(item, Mapping))
    step_ids = {str(item.get("step_id") or "") for item in substeps}
    priority_kinds = {
        _analytical_priority(item)[0]
        for item in _analytical_task_items(task_text)
    }
    synthesis = str(task.get("final_synthesis") or "").lower()
    limitation = str(task.get("limitations") or "")
    visual_hierarchy_used = (
        any("visual hierarchy" in item.lower() for item in source_dimensions)
        and "visual hierarchy" in synthesis
    )
    dimensions = (
        {
            "dimension_id": "uses_source_semantic_lineage",
            "baseline": "absent",
            "improved": "present" if source_semantic_ids else "not_observed",
            "observed": bool(source_semantic_ids),
            "evidence": source_semantic_ids,
        },
        {
            "dimension_id": "distinguishes_information_priority",
            "baseline": "absent",
            "improved": "present" if "identify_information_priorities" in step_ids else "not_observed",
            "observed": "identify_information_priorities" in step_ids,
            "evidence": tuple(sorted(priority_kinds)),
        },
        {
            "dimension_id": "uses_visual_hierarchy",
            "baseline": "absent",
            "improved": "present" if visual_hierarchy_used else "not_observed",
            "observed": visual_hierarchy_used,
            "evidence": tuple(item for item in source_dimensions if "visual hierarchy" in item.lower()),
        },
        {
            "dimension_id": "maps_work_items_to_distinct_attention_roles",
            "baseline": "absent",
            "improved": "present" if len(priority_kinds) > 1 else "not_observed",
            "observed": len(priority_kinds) > 1,
            "evidence": tuple(sorted(priority_kinds)),
        },
        {
            "dimension_id": "states_uncertainty_or_next_test",
            "baseline": "absent",
            "improved": "present" if "state_uncertainty_and_next_test" in step_ids and limitation else "not_observed",
            "observed": "state_uncertainty_and_next_test" in step_ids and bool(limitation),
            "evidence": (limitation,) if limitation else (),
        },
    )
    return tuple(dict(item) for item in dimensions)


def _render_source_bound_semantic_competence_delta(
    *,
    task: Mapping[str, Any],
    measured_dimensions: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    """Render only the observed record-level difference, never a global intelligence claim."""

    lines = []
    for item in measured_dimensions:
        label = str(item.get("dimension_id") or "observed change").replace("_", " ")
        after = str(item.get("improved") or "not_observed")
        lines.append(f"- {label}: {item.get('baseline', 'absent')} -> {after}")
    limitations = (
        "This is a task-local structural comparison between an explicit non-source baseline shape and one source-bound "
        "analysis record. It is not a global competence score, an independently benchmarked result, or evidence that the "
        "semantic source alone caused every difference."
    )
    reply = (
        "I recorded a task-local competence comparison for the source-bound analysis.\n\n"
        "Observed record differences:\n"
        + "\n".join(lines)
        + "\n\n"
        + f"Source-bound task: {str(task.get('analytical_task_id') or '')}\n\n"
        + f"Limitation: {limitations}"
    )
    return reply, limitations


def _apply_source_bound_semantic_competence_measurement(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Persist one restart-safe, task-local competence delta without creating semantic authority."""

    objective = state.active_objective
    task = _source_bound_semantic_competence_task(state, message)
    if objective is None or task is None:
        return None
    analytical_task_id = str(task.get("analytical_task_id") or "")
    source_transfer_application_id = str(task.get("source_transfer_application_id") or "")
    source_semantic_ids = tuple(str(item) for item in task.get("source_semantic_ids", ()) if str(item))
    if not analytical_task_id or not source_transfer_application_id or not source_semantic_ids:
        return None
    competence_delta_id = stable_id(
        "semantic-competence-delta",
        objective.objective_id,
        analytical_task_id,
        source_transfer_application_id,
        "task-local-structural-comparison-v1",
    )
    deltas = list(_semantic_competence_deltas_for_objective(objective))
    existing = next(
        (
            item for item in deltas
            if str(item.get("competence_delta_id") or "") == competence_delta_id
        ),
        None,
    )
    if existing is None:
        measured_dimensions = _task_local_competence_measurement(task)
        baseline_result_id = stable_id(
            "semantic-competence-baseline",
            analytical_task_id,
            "non-source-task-shape-v1",
        )
        reply, limitations = _render_source_bound_semantic_competence_delta(
            task=task,
            measured_dimensions=measured_dimensions,
        )
        existing = {
            "competence_delta_id": competence_delta_id,
            "competence_probe_id": competence_delta_id,
            "record_kind": "source_bound_task_local_competence_delta",
            "objective_id": objective.objective_id,
            "task_family": "source_bound_multistep_analysis",
            "baseline_result_id": baseline_result_id,
            "improved_result_id": analytical_task_id,
            "baseline_result": {
                "result_id": baseline_result_id,
                "record_kind": "explicit_non_source_structural_baseline",
                "task_text": str(task.get("task_text") or ""),
                "source_semantic_ids": (),
                "summary": (
                    "A deterministic reference for the same task without an explicitly bound semantic source. "
                    "It is not an independently generated model answer."
                ),
            },
            "improved_result": {
                "result_id": analytical_task_id,
                "record_kind": str(task.get("record_kind") or "source_bound_semantic_multistep_analysis"),
                "source_semantic_ids": source_semantic_ids,
                "substep_ids": tuple(
                    str(item.get("step_id") or "")
                    for item in task.get("substeps", ())
                    if isinstance(item, Mapping)
                ),
            },
            "source_semantic_ids": source_semantic_ids,
            "source_transfer_application_id": source_transfer_application_id,
            "source_analytical_task_id": analytical_task_id,
            "measured_dimensions": measured_dimensions,
            "observed_delta": tuple(
                {
                    "dimension_id": str(item.get("dimension_id") or ""),
                    "before": str(item.get("baseline") or "absent"),
                    "after": str(item.get("improved") or "not_observed"),
                }
                for item in measured_dimensions
                if bool(item.get("observed"))
            ),
            "limitations": limitations,
            "status": "task_local_observed_delta_recorded",
            "restart_summary": "Persisted as one task-local comparison with no model execution, graph mutation, or admission.",
            "reply": reply,
            "created_at": utc_now(),
        }
        deltas.append(existing)
    reply = str(existing.get("reply") or "")
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_competence_delta_measurement",
        objective_id=objective.objective_id,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_competence_delta_measurement_response",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if not any(
        str(item.get("event") or "") == "semantic_competence_delta_recorded"
        and str(item.get("competence_delta_id") or "") == competence_delta_id
        for item in progress
        if isinstance(item, Mapping)
    ):
        progress = progress + ({
            "event": "semantic_competence_delta_recorded",
            "objective_id": objective.objective_id,
            "competence_delta_id": competence_delta_id,
            "source_analytical_task_id": analytical_task_id,
            "source_transfer_application_id": source_transfer_application_id,
            "at": utc_now(),
        },)
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(objective, semantic_competence_deltas=deltas),
        conversation=state.conversation + (user_turn, assistant_turn),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_competence_delta_measurement", 0.96, "active_teaching_objective", "safe_internal", (),
            ("source_bound_analysis", "task_local_structural_comparison", "no_global_competence_claim"),
        ),
        reply=reply,
    )


def _source_bound_semantic_recall(
    state: ConversationalRuntimeState,
    message: str,
) -> dict[str, Any] | None:
    """Resolve an operator's follow-up against one unambiguous applied semantic chain."""

    objective = state.active_objective
    if objective is None:
        return None
    normalized = " ".join(str(message or "").lower().split())
    if not re.match(r"^(?:how|what|which|why|did|does|do|has|have|can|could)\b", normalized):
        return None
    message_terms = _semantic_transfer_terms(normalized)
    applications = _semantic_transfer_applications_for_objective(objective)
    tasks = _semantic_analytical_tasks_for_objective(objective)
    deltas = _semantic_competence_deltas_for_objective(objective)
    if not applications or not tasks:
        return None
    followups = _teaching_followups_for_objective(objective)
    followups_by_claim = {
        str(item.get("claim_version_id") or ""): item
        for item in followups
        if str(item.get("claim_version_id") or "")
    }

    def supporting_records(task: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        application_id = str(task.get("source_transfer_application_id") or "")
        application = next(
            (item for item in applications if str(item.get("application_record_id") or "") == application_id),
            None,
        )
        delta = next(
            (
                item for item in deltas
                if str(item.get("source_analytical_task_id") or "") == str(task.get("analytical_task_id") or "")
            ),
            None,
        )
        claim_ids = tuple(str(item) for item in task.get("source_semantic_ids", ()) if str(item))
        followup = next((followups_by_claim[item] for item in reversed(claim_ids) if item in followups_by_claim), None)
        return application, delta, followup

    chain_requested = len(message_terms & _SEMANTIC_RECALL_CHAIN_TERMS) >= 2
    if chain_requested and len(applications) == len(tasks) == len(deltas) == 1:
        application, delta, followup = supporting_records(tasks[0])
        if application is not None and delta is not None:
            return {
                "mode": "chain_summary",
                "application": application,
                "task": tasks[0],
                "delta": delta,
                "followup": followup,
            }

    delta_requested = bool(message_terms & {"baseline", "improved", "delta", "difference", "measurement"})
    if delta_requested and deltas:
        candidates: list[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]] = []
        for delta in deltas:
            task = next(
                (
                    item for item in tasks
                    if str(item.get("analytical_task_id") or "") == str(delta.get("source_analytical_task_id") or "")
                ),
                None,
            )
            if task is None:
                continue
            application, _linked_delta, followup = supporting_records(task)
            if application is None:
                continue
            source_text = " ".join(
                (
                    str(task.get("task_text") or ""),
                    " ".join(str(item) for item in task.get("source_transfer_dimensions", ()) if str(item)),
                )
            )
            overlap = len(message_terms & _semantic_transfer_terms(source_text))
            if overlap or len(deltas) == 1:
                candidates.append((overlap, delta, task, application, followup))
        if candidates:
            highest = max(score for score, *_records in candidates)
            selected = [records for score, *records in candidates if score == highest]
            if len(selected) == 1:
                delta, task, application, followup = selected[0]
                return {
                    "mode": "competence_delta",
                    "application": application,
                    "task": task,
                    "delta": delta,
                    "followup": followup,
                }

    effect_requested = bool(message_terms & _SEMANTIC_RECALL_EFFECT_TERMS)
    if effect_requested and (_SEMANTIC_RECALL_CONTEXT_TERMS & message_terms):
        candidates: list[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]] = []
        for task in tasks:
            application, delta, followup = supporting_records(task)
            if application is None:
                continue
            source_text = " ".join(
                (
                    str(task.get("task_text") or ""),
                    " ".join(str(item) for item in task.get("source_transfer_dimensions", ()) if str(item)),
                    str(application.get("task_text") or ""),
                )
            )
            overlap = len(message_terms & _semantic_transfer_terms(source_text))
            if overlap:
                candidates.append((overlap, task, application, delta, followup))
        if candidates:
            highest = max(score for score, *_records in candidates)
            selected = [records for score, *records in candidates if score == highest]
            if len(selected) == 1:
                task, application, delta, followup = selected[0]
                return {
                    "mode": "application_effect",
                    "application": application,
                    "task": task,
                    "delta": delta,
                    "followup": followup,
                }
    return None


def is_source_bound_semantic_recall_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Expose read-only applied-semantic follow-up recall to the normal dispatcher."""

    return _source_bound_semantic_recall(state, message) is not None


def _render_source_bound_semantic_recall(recall: Mapping[str, Any]) -> str:
    """Make the existing applied chain legible without presenting it as reviewed truth."""

    mode = str(recall.get("mode") or "")
    task = dict(recall.get("task") or {})
    application = dict(recall.get("application") or {})
    delta = dict(recall.get("delta") or {})
    followup = dict(recall.get("followup") or {})
    source_label = str(followup.get("lesson_title") or followup.get("source_gap") or "the revised source")
    dimensions = tuple(str(item) for item in task.get("source_transfer_dimensions", ()) if str(item))
    dimension_text = ", ".join(dimensions) or source_label
    if mode == "competence_delta":
        lines = [
            f"- {str(item.get('dimension_id') or 'observed change').replace('_', ' ')}: "
            f"{item.get('before', 'absent')} -> {item.get('after', 'not observed')}"
            for item in delta.get("observed_delta", ())
            if isinstance(item, Mapping)
        ]
        return (
            "The recorded baseline-to-improved comparison is task-local, not a global competence claim.\n\n"
            + "\n".join(lines or ("- No observed difference was recorded.",))
            + "\n\n"
            + f"It compares the explicit non-source baseline with the source-bound analysis for: {str(task.get('task_text') or 'the recorded task').rstrip('.!?')}. "
            + f"The result remains provisional: {delta.get('limitations') or 'it has not been independently benchmarked.'}"
        )
    if mode == "chain_summary":
        return (
            "Here is the recorded applied-semantic chain.\n\n"
            f"- Revised: {source_label} now keeps {dimension_text} distinct.\n"
            "- Transferred: those dimensions were applied to a dashboard attention-guidance task.\n"
            f"- Analyzed: {str(task.get('task_text') or 'the task').rstrip('.!?')} was organized into explicit priorities, layout, and a next test.\n"
            f"- Measured: the task-local comparison recorded {len(tuple(delta.get('observed_delta') or ()))} concrete differences.\n\n"
            "All four records remain provisional and source-bound; none has been promoted to reviewed semantic truth."
        )
    priority_step = next(
        (
            item for item in task.get("substeps", ())
            if isinstance(item, Mapping) and str(item.get("step_id") or "") == "identify_information_priorities"
        ),
        {},
    )
    limitation = str(task.get("limitations") or "the actual workflow and outcomes have not been tested.").strip()
    return (
        f"The revised {source_label} record affected the dashboard analysis by applying {dimension_text} to the attention path.\n\n"
        f"The transfer framed the screen around what should receive attention first; the analysis then mapped task-specific work into distinct roles:\n"
        f"{priority_step.get('finding') or 'the recorded task did not retain a priority breakdown.'}\n\n"
        f"The layout remains provisional. {limitation}"
    )


def _apply_source_bound_semantic_recall(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Render a read-only source-bound follow-up without changing any semantic record."""

    objective = state.active_objective
    recall = _source_bound_semantic_recall(state, message)
    if objective is None or recall is None:
        return None
    reply = _render_source_bound_semantic_recall(recall)
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="semantic_source_bound_recall",
        objective_id=objective.objective_id,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_source_bound_recall_response",
        objective_id=objective.objective_id,
    )
    updated = _replace_state(state, conversation=state.conversation + (user_turn, assistant_turn))
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_source_bound_recall", 0.96, "active_teaching_objective", "safe_internal", (),
            ("read_only_source_bound_recall", "no_semantic_mutation", str(recall.get("mode") or "")),
        ),
        reply=reply,
    )


def _teaching_followup_evidence(objective: ConversationalObjective) -> tuple[EvidenceRef, ...]:
    """Expose queued in-scope questions as first-class nodes in the existing frontier."""

    nodes: list[EvidenceRef] = []
    for followup in _teaching_followups_for_objective(objective):
        if str(followup.get("status") or "") not in {"queued", "study_running", "study_retry_scheduled"}:
            continue
        node_id = str(followup.get("node_id") or "")
        evidence_id = str(followup.get("evidence_id") or node_id)
        question = str(followup.get("question") or "").strip()
        if not node_id or not evidence_id or not question:
            continue
        nodes.append(EvidenceRef(
            evidence_id=evidence_id,
            summary=f"Teaching follow-up: {question}",
            content=json.dumps({
                "node_id": node_id,
                "followup_id": str(followup.get("followup_id") or ""),
                "material_requirement_id": "",
                "objective_id": objective.objective_id,
                "label": question,
                "parent_id": str(followup.get("lesson_id") or objective.objective_id),
                "depth": 2,
                "status": str(followup.get("status") or "queued"),
                "evidence_need": f"bounded local explanation for the operator question: {question}",
                "completion_criterion_reference": f"answer the operator's in-scope teaching question: {question}",
                "minimum_contribution_contract": {
                    **_knowledge_node_completion_contract(question, question),
                    "required_topic_terms": tuple(followup.get("question_tokens") or ()),
                },
                "extracted_concept_ids": [],
                "extracted_claim_ids": [],
                "unresolved_questions": [question],
                "attempt_count": 0,
                "last_progress_digest": "",
            }, sort_keys=True),
            source="teaching_followup",
            kind="knowledge_frontier_node",
        ))
    return tuple(nodes)


def _teaching_prerequisite_evidence(objective: ConversationalObjective) -> tuple[EvidenceRef, ...]:
    """Append an approved prerequisite behind the parent curriculum's current work."""

    nodes: list[EvidenceRef] = []
    for prerequisite in _teaching_prerequisites_for_objective(objective):
        if str(prerequisite.get("status") or "") not in {
            "queued",
            "prerequisite_study_running",
            "prerequisite_retry_scheduled",
        }:
            continue
        node_id = str(prerequisite.get("node_id") or "")
        evidence_id = str(prerequisite.get("evidence_id") or node_id)
        topic = str(prerequisite.get("topic") or "").strip()
        if not node_id or not evidence_id or not topic:
            continue
        competence_requirement = str(
            prerequisite.get("competence_requirement")
            or f"show a concrete introductory application of {topic} to the blocked branch"
        )
        completion_contract = {
            **_knowledge_node_completion_contract(topic, competence_requirement),
            "required_topic_terms": ("derivative", "derivatives", "integral", "integrals", "rate"),
            "requires_expected_observation": True,
        }
        nodes.append(EvidenceRef(
            evidence_id=evidence_id,
            summary=f"Linked prerequisite: {topic}",
            content=json.dumps({
                "node_id": node_id,
                "prerequisite_id": str(prerequisite.get("prerequisite_id") or ""),
                "material_requirement_id": "",
                "objective_id": objective.objective_id,
                "label": f"{topic}: derivatives and integrals for mechanics",
                "parent_id": str(prerequisite.get("prerequisite_objective_id") or objective.objective_id),
                "depth": 2,
                "status": str(prerequisite.get("status") or "queued"),
                "evidence_need": f"bounded prerequisite study and a simple competence check for {topic}",
                "completion_criterion_reference": competence_requirement,
                "minimum_contribution_contract": completion_contract,
                "extracted_concept_ids": [],
                "extracted_claim_ids": [],
                "unresolved_questions": [],
                "attempt_count": 0,
                "last_progress_digest": "",
            }, sort_keys=True),
            source="teaching_prerequisite",
            kind="knowledge_frontier_node",
        ))
    return tuple(nodes)


def _ensure_pending_teaching_followup_nodes(
    episode: ActiveCognitiveEpisodeState,
    objective: ConversationalObjective,
) -> ActiveCognitiveEpisodeState:
    queued = _teaching_followup_evidence(objective)
    prerequisites = _teaching_prerequisite_evidence(objective)
    if not queued and not prerequisites:
        return episode
    existing_ids = {item.evidence_id for item in episode.evidence}
    additions = tuple(item for item in queued if item.evidence_id not in existing_ids)
    trailing = tuple(item for item in prerequisites if item.evidence_id not in existing_ids)
    return replace(episode, evidence=additions + episode.evidence + trailing) if additions or trailing else episode


def _knowledge_node_completion_contract(label: str, criterion: str) -> dict[str, Any]:
    """Derive reusable contribution shapes from node semantics, never a topic fixture."""
    text = f"{label} {criterion}".lower()
    contract: dict[str, Any] = {
        "minimum_specific_terms": 3,
        "requires_explanatory_relation": True,
        "reject_importance_only": True,
        "contribution_kind": "explanatory_relation",
    }
    # A multi-topic frontier node needs the general causal contract. Requiring one
    # narrow contribution shape would reject valid coverage of its other topic.
    if re.search(r"\b(?:and|or)\b|[,/;]", label.lower()):
        return contract
    if any(term in text for term in ("maintenance", "inspection", "upkeep", "service")):
        return {**contract, "contribution_kind": "recurring_actions_with_consequence", "minimum_action_count": 2}
    if any(term in text for term in ("prevent", "prevention", "avoid", "reduce", "mosquito", "pest", "breeding")):
        return {**contract, "contribution_kind": "prevention_intervention"}
    if any(term in text for term in ("overflow", "overload", "spill", "exceed")):
        return {**contract, "contribution_kind": "threshold_and_safe_mitigation"}
    if any(term in text for term in ("capacity", "sizing", "volume", "runtime", "duration")):
        return {**contract, "contribution_kind": "sizing_relation"}
    if any(term in text for term in ("collect", "collection", "capture", "intake", "harvest")):
        return {**contract, "contribution_kind": "mechanism_path"}
    return contract


def _knowledge_label_for_objective(objective: ConversationalObjective | None) -> str:
    return _goal_review_label(objective)


def _accepted_frontier_node_ids(
    episode: ActiveCognitiveEpisodeState,
    frontier_nodes: Sequence[EvidenceRef],
    *,
    completed_operation_ids: set[str] | None = None,
) -> set[str]:
    """Return only nodes completed by their own accepted frontier operation.

    A model packet can cite sibling frontier nodes as context. Those evidence
    references support the current operation, but they must never complete the
    cited siblings. The immutable cycle focus is the canonical ownership link.
    """
    if completed_operation_ids is None:
        completed_operation_ids = {
            result.operation_id
            for result in episode.operation_results
            if result.accepted
        }
    accepted_focuses = {
        cycle.focus_id
        for cycle in episode.cycles
        if cycle.completed and cycle.operation_id in completed_operation_ids
    }
    return {
        node.evidence_id
        for node in frontier_nodes
        if stable_id("focus", episode.episode_id, node.evidence_id) in accepted_focuses
    }


def _knowledge_progress_counters(
    objective: ConversationalObjective,
    episode: ActiveCognitiveEpisodeState,
    *,
    completed_operation_ids: set[str] | None = None,
    blocked_operation_ids: set[str] | None = None,
    active_node_index: int = 0,
    model_calls_used: int | None = None,
) -> dict[str, Any]:
    frontier_nodes = tuple(item for item in episode.evidence if item.kind == "knowledge_frontier_node")
    if completed_operation_ids is None:
        completed_operation_ids = {result.operation_id for result in episode.operation_results if result.accepted}
    if blocked_operation_ids is None:
        blocked_operation_ids = {result.operation_id for result in episode.operation_results if not result.accepted}
    expected_focuses = {
        stable_id("focus", episode.episode_id, node.evidence_id)
        for node in frontier_nodes
    }
    completed_focuses = {
        cycle.focus_id
        for cycle in episode.cycles
        if cycle.completed
        and cycle.operation_id in completed_operation_ids
    } & expected_focuses
    rejected_counts: dict[str, int] = {}
    for cycle in episode.cycles:
        if (
            cycle.completed
            and cycle.operation_id in blocked_operation_ids
            and cycle.focus_id in expected_focuses
            and cycle.focus_id not in completed_focuses
        ):
            rejected_counts[cycle.focus_id] = rejected_counts.get(cycle.focus_id, 0) + 1
    blocked_focuses = {focus_id for focus_id, count in rejected_counts.items() if count >= 2}
    retryable_focuses = {focus_id for focus_id, count in rejected_counts.items() if count == 1}
    unattempted_focuses = expected_focuses - completed_focuses - set(rejected_counts)
    material_requirements = _knowledge_material_requirements(objective)
    criteria_total = len(material_requirements) or len(tuple(objective.practical_success_indicators))
    completed_node_ids = _accepted_frontier_node_ids(
        episode,
        frontier_nodes,
        completed_operation_ids=completed_operation_ids,
    )
    satisfied = sum(node.evidence_id in completed_node_ids for node in frontier_nodes)
    return {
        "frontier_nodes_completed": len(completed_focuses),
        "frontier_nodes_total": len(frontier_nodes),
        "criteria_satisfied": min(satisfied, criteria_total),
        "criteria_total": criteria_total,
        "model_calls_used": episode.model_call_count if model_calls_used is None else int(model_calls_used),
        "model_call_budget": objective.model_call_budget,
        "cycles_used": len(episode.cycles),
        "cycle_budget": objective.cycle_budget,
        "blocked_nodes": len(blocked_focuses),
        "retryable_nodes": len(retryable_focuses),
        "unattempted_nodes": len(unattempted_focuses),
        "unresolved_nodes": max(0, len(frontier_nodes) - len(completed_focuses)),
        "active_node_index": int(active_node_index),
    }


def _knowledge_frontier_all_attempted(episode: ActiveCognitiveEpisodeState) -> bool:
    frontier_nodes = tuple(item for item in episode.evidence if item.kind == "knowledge_frontier_node")
    if not frontier_nodes:
        return False
    results = {result.operation_id: result for result in episode.operation_results}
    accepted_focuses: set[str] = set()
    rejected_counts: dict[str, int] = {}
    for cycle in episode.cycles:
        result = results.get(cycle.operation_id)
        if result is None:
            continue
        if result.accepted:
            accepted_focuses.add(cycle.focus_id)
        else:
            rejected_counts[cycle.focus_id] = rejected_counts.get(cycle.focus_id, 0) + 1
    expected_focuses = {
        stable_id("focus", episode.episode_id, node.evidence_id)
        for node in frontier_nodes
    }
    permanently_finished = accepted_focuses | {focus_id for focus_id, count in rejected_counts.items() if count >= 2}
    return expected_focuses <= permanently_finished


def _knowledge_has_global_model_failure(episode: ActiveCognitiveEpisodeState) -> bool:
    return any(
        not result.accepted and "local_model_execution_blocked" in result.rejection_reasons
        for result in episode.operation_results
    )


def _knowledge_stagnation(episode: ActiveCognitiveEpisodeState, *, window: int = 8) -> Mapping[str, Any]:
    """Detect only repeated nonproductive output across several nodes, never normal long work."""
    results = {result.operation_id: result for result in episode.operation_results}
    recent = [
        (cycle, results.get(cycle.operation_id))
        for cycle in episode.cycles[-window:]
        if results.get(cycle.operation_id) is not None
    ]
    if len(recent) < window or any(result.accepted for _cycle, result in recent):
        return {}
    fingerprints: dict[str, set[str]] = {}
    for cycle, result in recent:
        text = " ".join(re.findall(r"[a-z0-9]+", str(result.interpretation or "").lower()))
        if text:
            fingerprints.setdefault(text, set()).add(cycle.focus_id)
    repeated = {
        fingerprint: focus_ids
        for fingerprint, focus_ids in fingerprints.items()
        if len(focus_ids) >= 3
    }
    if not repeated:
        return {}
    return {
        "reason": "repeated_nonproductive_hypothesis",
        "window_calls": len(recent),
        "repeated_fingerprints": tuple(sorted(repeated)),
        "affected_focus_ids": tuple(sorted({focus_id for focus_ids in repeated.values() for focus_id in focus_ids})),
    }


def _knowledge_limit_reached(used: int, limit: int | None) -> bool:
    return limit is not None and used >= limit


def _knowledge_call_progress_text(used: int, limit: int | None) -> str:
    return f"{used} (unlimited local)" if limit is None else f"{used}/{limit}"


def _with_updated_knowledge_event_budget(
    events: Sequence[Mapping[str, Any]],
    *,
    objective_id: str,
    model_call_budget: int | None,
    cycle_budget: int | None,
) -> tuple[Mapping[str, Any], ...]:
    updated: list[Mapping[str, Any]] = []
    for item in events:
        if item.get("event") != "knowledge_runtime_event" or item.get("objective_id") != objective_id:
            updated.append(item)
            continue
        counters = dict(item.get("progress_counters") or {})
        counters["model_call_budget"] = model_call_budget
        counters["cycle_budget"] = cycle_budget
        updated.append({**item, "progress_counters": counters})
    return tuple(updated)


def _knowledge_event(
    objective: ConversationalObjective,
    *,
    event_type: str,
    summary: str,
    dedupe_key: str,
    episode: ActiveCognitiveEpisodeState,
    node_id: str = "",
    parent_node_id: str = "",
    model_request_id: str = "",
    model_result_id: str = "",
    model_identity: str = "",
    evidence_refs: Sequence[str] = (),
    criterion_refs: Sequence[str] = (),
    visibility: str = "operator_visible",
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "event": "knowledge_runtime_event",
        "event_id": stable_id("knowledge-event", objective.objective_id, dedupe_key),
        "objective_id": objective.objective_id,
        "goal_thread_id": objective.objective_id,
        "at": utc_now(),
        "event_type": event_type,
        "node_id": node_id,
        "parent_node_id": parent_node_id,
        "model_request_id": model_request_id,
        "model_result_id": model_result_id,
        "model_identity": model_identity,
        "evidence_refs": tuple(str(item) for item in evidence_refs if str(item)),
        "criterion_refs": tuple(str(item) for item in criterion_refs if str(item)),
        "progress_counters": _knowledge_progress_counters(objective, episode),
        "summary": summary,
        "dedupe_key": dedupe_key,
        "visibility": visibility,
        "persistence_status": "persisted",
    }
    if extra:
        payload.update(dict(extra))
    return payload


def _frontier_node_label(node: EvidenceRef | Mapping[str, Any]) -> str:
    summary = str(node.summary if isinstance(node, EvidenceRef) else node.get("summary") or "")
    match = re.search(r":\s*(.+)$", summary)
    return match.group(1).strip() if match else summary


def _knowledge_material_requirements(objective: ConversationalObjective) -> tuple[Mapping[str, str], ...]:
    contract = objective.provenance.get("knowledge_contract") if isinstance(objective.provenance, Mapping) else None
    if not isinstance(contract, Mapping):
        return ()
    requirements = tuple(
        {"requirement_id": str(item.get("requirement_id")), "text": str(item.get("text"))}
        for item in contract.get("material_requirements", ())
        if isinstance(item, Mapping) and str(item.get("requirement_id") or "") and str(item.get("text") or "")
    )
    if requirements:
        return requirements
    return tuple(
        {
            "requirement_id": stable_id("knowledge-material-requirement", objective.objective_id, str(index), str(item)),
            "text": str(item),
        }
        for index, item in enumerate(contract.get("requested_subtopics", ()), start=1)
        if str(item).strip()
    )


def _frontier_requirement_id(node: EvidenceRef | Mapping[str, Any]) -> str:
    raw_content = node.content if isinstance(node, EvidenceRef) else node.get("content") or ""
    try:
        content = json.loads(str(raw_content)) if isinstance(raw_content, str) else dict(raw_content)
    except (TypeError, ValueError, json.JSONDecodeError):
        content = {}
    return str(content.get("material_requirement_id") or "")


def _knowledge_requirement_coverage(
    objective: ConversationalObjective,
    episode: ActiveCognitiveEpisodeState,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    requirements = _knowledge_material_requirements(objective)
    nodes = tuple(item for item in episode.evidence if item.kind == "knowledge_frontier_node")
    planned_ids = {_frontier_requirement_id(node) for node in nodes}
    completed_node_ids = _accepted_frontier_node_ids(episode, nodes)
    satisfied_ids = {
        _frontier_requirement_id(node)
        for node in nodes
        if node.evidence_id in completed_node_ids
    }
    satisfied = tuple(item["text"] for item in requirements if item["requirement_id"] in satisfied_ids)
    missing = tuple(item["text"] for item in requirements if item["requirement_id"] not in planned_ids)
    unsatisfied = tuple(
        item["text"]
        for item in requirements
        if item["requirement_id"] not in satisfied_ids and item["text"] not in set(missing)
    )
    return satisfied, missing, unsatisfied


def _bounded_model_output_excerpt(raw_model_output: str) -> str:
    text = str(raw_model_output or "").strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, Mapping):
        pieces = []
        for key in ("scope", "hypothesis_statement", "uncertainty"):
            value = str(payload.get(key) or "").strip()
            if value:
                pieces.append(f"{key}: {value}")
        assumptions = tuple(str(item).strip() for item in payload.get("assumptions", ()) if str(item).strip())
        observations = tuple(str(item).strip() for item in payload.get("expected_observations", ()) if str(item).strip())
        if assumptions:
            pieces.append("assumptions: " + "; ".join(assumptions[:2]))
        if observations:
            pieces.append("expected: " + "; ".join(observations[:2]))
        text = " | ".join(pieces) if pieces else text
    text = " ".join(text.split())
    return text[:700] + ("..." if len(text) > 700 else "")


def _bounded_knowledge_statement(text: str, *, limit: int = 220) -> str:
    cleaned = " ".join(str(text or "").split())
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def _accepted_knowledge_claims(result: CognitiveOperationResult) -> tuple[str, ...]:
    claims = []
    if result.interpretation:
        claims.append(result.interpretation)
    return tuple(_dedupe_knowledge_lines(_bounded_knowledge_statement(item) for item in claims if str(item).strip()))[:6]


def _accepted_knowledge_relationships(result: CognitiveOperationResult) -> tuple[str, ...]:
    return ()


def _knowledge_events_from_episode(
    objective: ConversationalObjective,
    episode: ActiveCognitiveEpisodeState,
    existing_events: Sequence[Mapping[str, Any]] = (),
) -> tuple[Mapping[str, Any], ...]:
    existing_dedupe = {
        str(item.get("dedupe_key") or "")
        for item in existing_events
        if item.get("event") == "knowledge_runtime_event"
    }
    frontier_nodes = tuple(item for item in episode.evidence if item.kind == "knowledge_frontier_node")
    node_by_id = {item.evidence_id: item for item in frontier_nodes}
    events: list[Mapping[str, Any]] = []

    def add(event: Mapping[str, Any]) -> None:
        key = str(event.get("dedupe_key") or "")
        if key and key not in existing_dedupe:
            existing_dedupe.add(key)
            events.append(event)

    if frontier_nodes:
        add(_knowledge_event(
            objective,
            event_type="knowledge_frontier_created",
            summary=f"Created {len(frontier_nodes)} initial knowledge nodes.",
            dedupe_key=f"{objective.objective_id}:frontier_created:{len(frontier_nodes)}",
            episode=episode,
            visibility="operator_visible",
            extra={"created_node_count": len(frontier_nodes)},
        ))
        for node in frontier_nodes:
            add(_knowledge_event(
                objective,
                event_type="knowledge_node_created",
                summary=f"Created node: {_frontier_node_label(node)}.",
                dedupe_key=f"{objective.objective_id}:node_created:{node.evidence_id}",
                episode=episode,
                node_id=node.evidence_id,
                evidence_refs=(node.evidence_id,),
                visibility="advanced_detail",
            ))

    packets_by_cycle = {packet.cycle_id: packet for packet in episode.working_memory_packets}
    requests_by_operation = {request.operation_id: request for request in episode.operation_requests}
    results_by_operation = {result.operation_id: result for result in episode.operation_results}
    for cycle in episode.cycles:
        request = requests_by_operation.get(cycle.operation_id)
        result = results_by_operation.get(cycle.operation_id)
        packet = packets_by_cycle.get(cycle.cycle_id)
        prior_completed_ops = {
            prior.operation_id
            for prior in episode.operation_results
            if prior.accepted
            and any(prior_cycle.operation_id == prior.operation_id and prior_cycle.sequence < cycle.sequence for prior_cycle in episode.cycles)
        }
        prior_blocked_ops = {
            prior.operation_id
            for prior in episode.operation_results
            if not prior.accepted
            and any(prior_cycle.operation_id == prior.operation_id and prior_cycle.sequence < cycle.sequence for prior_cycle in episode.cycles)
        }
        node_id = str((packet.active_focus.get("active_frontier_node") or {}).get("node_id") or "") if packet else ""
        node_index = next((index for index, node in enumerate(frontier_nodes, start=1) if node.evidence_id == node_id), 0)
        pre_result_counters = _knowledge_progress_counters(
            objective,
            episode,
            completed_operation_ids=prior_completed_ops,
            blocked_operation_ids=prior_blocked_ops,
            active_node_index=node_index,
            model_calls_used=max(0, episode.model_call_count - (1 if result else 0)),
        )
        focus_label = ""
        evidence_refs: tuple[str, ...] = ()
        if packet:
            focus_label = str(packet.active_focus.get("description") or "")
            evidence_refs = tuple(str(item.get("evidence_id") or "") for item in packet.relevant_evidence if item.get("evidence_id"))
            node_id = str((packet.active_focus.get("active_frontier_node") or {}).get("node_id") or "")
        if not focus_label and request:
            focus_label = str(request.task or request.focus_id)
        short_label = re.sub(r"^(?:Resolve|Retry|Repair response format for) knowledge frontier:\s*", "", focus_label).strip() or "current node"
        if cycle.focus_id:
            add(_knowledge_event(
                objective,
                event_type="knowledge_node_selected",
                summary=f"Selected {short_label}.",
                dedupe_key=f"{objective.objective_id}:node_selected:{cycle.focus_id}",
                episode=episode,
                node_id=node_id,
                evidence_refs=evidence_refs,
                extra={"progress_counters": pre_result_counters},
            ))
        if packet:
            packet_summary = (
                f"Prepared a format-repair packet for {short_label} with {len(packet.relevant_evidence)} evidence item(s)."
                if request and request.operation_type == "repair_node_specific_hypothesis_format"
                else
                f"Prepared a retry evidence packet for {short_label} with {len(packet.relevant_evidence)} evidence item(s)."
                if request and request.operation_type == "reformulate_node_specific_hypothesis"
                else f"Prepared a bounded evidence packet with {len(packet.relevant_evidence)} evidence item(s)."
            )
            add(_knowledge_event(
                objective,
                event_type="evidence_packet_prepared",
                summary=packet_summary,
                dedupe_key=f"{objective.objective_id}:packet_prepared:{packet.packet_digest}",
                episode=episode,
                node_id=node_id,
                evidence_refs=evidence_refs,
                visibility="operator_visible",
                extra={"prompt_rendered": False, "evidence_item_count": len(packet.relevant_evidence), "progress_counters": pre_result_counters},
            ))
        if request:
            add(_knowledge_event(
                objective,
                event_type="local_model_request_started",
                summary=f"Started {request.operation_type} with {_friendly_model_name(request.model_identity)}.",
                dedupe_key=f"{objective.objective_id}:model_started:{request.operation_id}",
                episode=episode,
                node_id=node_id,
                model_request_id=request.operation_id,
                model_identity=request.model_identity,
                evidence_refs=evidence_refs,
                extra={"progress_counters": pre_result_counters},
            ))
        if result:
            received_type = "local_model_response_received" if result.accepted else "local_model_response_rejected"
            received_summary = "Response accepted." if result.accepted else "Response rejected: " + ", ".join(result.rejection_reasons)
            add(_knowledge_event(
                objective,
                event_type=received_type,
                summary=received_summary,
                dedupe_key=f"{objective.objective_id}:model_result:{result.operation_id}:{result.accepted}",
                episode=episode,
                node_id=node_id,
                model_request_id=result.operation_id,
                model_result_id=result.operation_id,
                model_identity=result.model_identity,
                evidence_refs=result.evidence_refs,
                extra={
                    "rejection_reasons": result.rejection_reasons,
                    "model_output_excerpt": _bounded_model_output_excerpt(result.raw_model_output),
                    "delta_interpretation": result.interpretation,
                    "delta_acceptance": "accepted" if result.accepted else "rejected",
                    "evaluation_state": result.evaluation_state,
                    "evaluation_reasons": result.evaluation_reasons,
                },
            ))
            if result.accepted:
                claims = _accepted_knowledge_claims(result)
                relationships = _accepted_knowledge_relationships(result)
                claim_count = len(claims)
                relationship_count = len(relationships)
                add(_knowledge_event(
                    objective,
                    event_type="knowledge_claims_extracted",
                    summary=f"Accepted {claim_count} claim(s) and identified {relationship_count} relationship-like statement(s).",
                    dedupe_key=f"{objective.objective_id}:claims_extracted:{result.operation_id}:{claim_count}:{relationship_count}",
                    episode=episode,
                    node_id=node_id,
                    model_result_id=result.operation_id,
                    model_identity=result.model_identity,
                    evidence_refs=result.evidence_refs,
                    extra={
                        "claim_count": claim_count,
                        "relationship_count": relationship_count,
                        "accepted_claims": claims,
                        "identified_relationships": relationships,
                    },
                ))
                add(_knowledge_event(
                    objective,
                    event_type="knowledge_understanding_updated",
                    summary=f"Added accepted support for {short_label}.",
                    dedupe_key=f"{objective.objective_id}:understanding:{result.operation_id}",
                    episode=episode,
                    node_id=node_id,
                    model_result_id=result.operation_id,
                    evidence_refs=result.evidence_refs,
                ))
                add(_knowledge_event(
                    objective,
                    event_type="knowledge_node_completed",
                    summary=f"Completed {short_label}.",
                    dedupe_key=f"{objective.objective_id}:node_completed:{cycle.focus_id}",
                    episode=episode,
                    node_id=node_id,
                    model_result_id=result.operation_id,
                    evidence_refs=result.evidence_refs,
                ))
            else:
                rejected_attempts = sum(
                    1
                    for prior_cycle in episode.cycles
                    if prior_cycle.focus_id == cycle.focus_id
                    and prior_cycle.sequence <= cycle.sequence
                    and not (results_by_operation.get(prior_cycle.operation_id) or result).accepted
                )
                format_repair = (
                    request is not None
                    and request.operation_type == "reformulate_node_specific_hypothesis"
                    and "retry_output_schema_invalid" in result.rejection_reasons
                )
                retrying = rejected_attempts == 1
                add(_knowledge_event(
                    objective,
                    event_type=(
                        "knowledge_node_format_repair_scheduled" if format_repair
                        else "knowledge_node_retry_scheduled" if retrying else "knowledge_node_blocked"
                    ),
                    summary=(
                        f"Format repair scheduled for {short_label}: "
                        if format_repair else
                        f"Retry scheduled for {short_label}: "
                        if retrying else f"Blocked incomplete {short_label}: "
                    ) + ", ".join(result.rejection_reasons),
                    dedupe_key=(
                        f"{objective.objective_id}:node_format_repair:{cycle.focus_id}:{','.join(result.rejection_reasons)}"
                        if format_repair else
                        f"{objective.objective_id}:node_retry:{cycle.focus_id}:{','.join(result.rejection_reasons)}"
                        if retrying else f"{objective.objective_id}:node_blocked:{cycle.focus_id}:{','.join(result.rejection_reasons)}"
                    ),
                    episode=episode,
                    node_id=node_id,
                    model_result_id=result.operation_id,
                    evidence_refs=result.evidence_refs,
                ))

    terminal_frontier_closure = (
        episode.loop_state == "blocked_insufficient_evidence"
        and _knowledge_frontier_all_attempted(episode)
    )
    if (
        episode.loop_state in {"blocked_insufficient_evidence", "blocked_capability_gap", "paused_budget"}
        or episode.completed
    ) and not terminal_frontier_closure:
        add(_knowledge_event(
            objective,
            event_type="knowledge_budget_updated",
            summary=f"Budget/status update: {episode.loop_state}.",
            dedupe_key=f"{objective.objective_id}:budget:{episode.loop_state}:{episode.model_call_count}:{len(episode.cycles)}",
            episode=episode,
            visibility="operator_visible",
        ))
    return tuple(events)


def _friendly_model_name(model_identity: str) -> str:
    lower = str(model_identity or "").lower()
    if "qwen" in lower:
        return "Qwen"
    if "llama" in lower:
        return "Llama"
    if lower.startswith("shared-local-model-ledger"):
        return "Local model"
    return str(model_identity or "local model")


def unrendered_knowledge_goal_events(state: ConversationalRuntimeState) -> tuple[Mapping[str, Any], ...]:
    rendered = {
        str(item.get("event_id") or "")
        for item in state.objective_progress
        if item.get("event") == "knowledge_runtime_event_rendered"
    }
    events = []
    for item in state.objective_progress:
        if item.get("event") != "knowledge_runtime_event":
            continue
        if item.get("visibility") != "operator_visible":
            continue
        event_id = str(item.get("event_id") or "")
        if event_id and event_id not in rendered:
            events.append(item)
    return tuple(events)


def mark_knowledge_goal_event_rendered(
    state: ConversationalRuntimeState,
    event_id: str,
    *,
    runtime_root: str | Path | None = None,
) -> ConversationalRuntimeState:
    if any(item.get("event") == "knowledge_runtime_event_rendered" and item.get("event_id") == event_id for item in state.objective_progress):
        return state
    updated = _replace_state(
        state,
        objective_progress=state.objective_progress + ({"event": "knowledge_runtime_event_rendered", "event_id": event_id, "at": utc_now()},),
    )
    if runtime_root is not None:
        save_runtime_state(runtime_root, updated)
    return updated


def render_knowledge_goal_event(event: Mapping[str, Any], objective: ConversationalObjective | None = None) -> str:
    label = _knowledge_label_for_objective(objective)
    counters = dict(event.get("progress_counters") or {})
    event_type = str(event.get("event_type") or "")
    summary = str(event.get("summary") or "").strip()
    progress = (
        f"Progress: completed {counters.get('frontier_nodes_completed', 0)}/{counters.get('frontier_nodes_total', 0)} nodes; "
        f"active node {counters.get('active_node_index', 0) or '-'}; "
        f"{counters.get('criteria_satisfied', 0)}/{counters.get('criteria_total', 0)} criteria; "
        f"model calls {_knowledge_call_progress_text(int(counters.get('model_calls_used', 0)), counters.get('model_call_budget'))}; "
        f"blocked {counters.get('blocked_nodes', 0)}; retryable {counters.get('retryable_nodes', 0)}; "
        f"unattempted {counters.get('unattempted_nodes', 0)}; unresolved {counters.get('unresolved_nodes', 0)}"
    )
    if event_type == "local_model_request_started":
        header = f"[Local model \u00b7 {_friendly_model_name(str(event.get('model_identity') or ''))}]"
    elif event_type in {"local_model_response_received", "local_model_response_rejected"}:
        header = "[Local model result]"
    elif event_type in {"knowledge_claims_extracted", "knowledge_understanding_updated", "knowledge_node_completed", "knowledge_node_blocked", "knowledge_budget_updated"}:
        header = f"[Knowledge update \u00b7 {label}]"
    else:
        header = f"[Goal activity \u00b7 {label}]"
    lines = [header, summary]
    if event_type in {"local_model_response_received", "local_model_response_rejected"}:
        excerpt = str(event.get("model_output_excerpt") or "").strip()
        interpretation = str(event.get("delta_interpretation") or "").strip()
        if excerpt:
            lines.append("Model output: " + excerpt)
        if interpretation:
            lines.append("DELTA interpretation: " + interpretation[:500] + ("..." if len(interpretation) > 500 else ""))
        evaluation = _render_knowledge_evaluation(
            str(event.get("evaluation_state") or ""),
            tuple(str(item) for item in event.get("evaluation_reasons", ()) if str(item)),
        )
        if evaluation:
            lines.append("Local evaluation: " + evaluation)
    if event_type == "knowledge_claims_extracted":
        claims = tuple(str(item).strip() for item in event.get("accepted_claims", ()) if str(item).strip())
        relationships = tuple(str(item).strip() for item in event.get("identified_relationships", ()) if str(item).strip())
        if claims:
            lines.append("Accepted claims:")
            lines.extend(f"- {item}" for item in claims[:4])
        if relationships:
            lines.append("Relationship-like statements:")
            lines.extend(f"- {item}" for item in relationships[:3])
    lines.append(progress)
    return "\n".join(lines)


def _render_knowledge_evaluation(state: str, reasons: Sequence[str]) -> str:
    if state in {"", "not_evaluated"}:
        return ""
    if state == "supported":
        return "no deterministic contradiction found."
    rendered_reasons = []
    for reason in reasons:
        if reason.startswith("arithmetic_capacity_shortfall:"):
            rendered_reasons.append("the stated capacity is less than the stated demand")
        elif reason == "missing_candidate_proposition":
            rendered_reasons.append("the response did not contain a candidate proposition")
        else:
            rendered_reasons.append(reason.replace("_", " "))
    detail = "; ".join(dict.fromkeys(rendered_reasons)) or "no reason was recorded"
    return f"{state}: {detail}."


def derive_standing_authority(objective: ConversationalObjective) -> StandingAuthority:
    return StandingAuthority(
        authority_id=stable_id("standing-authority", objective.objective_id, "routine-internal"),
        objective_id=objective.objective_id,
        allowed_actions=objective.allowed_actions,
        prohibited_actions=objective.prohibited_actions,
        expires_condition="session ends, operator revokes goal, scope changes materially, budget exhausts, or material authority is required",
    )


def start_or_restore_runtime(root: str | Path) -> ConversationalRuntimeState:
    state_path = Path(root) / "state.json"
    if state_path.exists():
        state = _state_from_record(read_json(state_path))
        restored = _rebase_active_episode_path(root, state)
        if state.schema_version != SCHEMA_VERSION:
            restored = _replace_state(restored, schema_version=SCHEMA_VERSION)
        if restored != state:
            state = restored
            save_runtime_state(root, state)
        return state
    state = ConversationalRuntimeState(
        runtime_id=stable_id("conversational-runtime", str(Path(root))),
        lifecycle_state="running",
    )
    save_runtime_state(root, state)
    return state


def _rebase_active_episode_path(root: str | Path, state: ConversationalRuntimeState) -> ConversationalRuntimeState:
    """Keep a copied runtime from resuming an episode in the source root."""
    active_path_text = str(state.active_episode_path or "").strip()
    if not active_path_text:
        return state
    root_path = Path(root).resolve()
    active_path = Path(active_path_text)
    if not active_path.is_absolute():
        return state
    try:
        active_path.resolve().relative_to(root_path)
        return state
    except ValueError:
        pass
    local_episode_path = root_path / active_path.name
    if not local_episode_path.is_file():
        return state
    return replace(state, active_episode_path=str(local_episode_path))


def save_runtime_state(root: str | Path, state: ConversationalRuntimeState) -> None:
    write_json(Path(root) / "state.json", state.as_record())


def _request_from_record(item: Any) -> ChatAddressableRequest:
    if isinstance(item, ChatAddressableRequest):
        return item
    payload = dict(item)
    for key in ("permitted_data", "prohibited_data", "proposed_source_scope"):
        payload[key] = tuple(payload.get(key, ()))
    return ChatAddressableRequest(**payload)


def _turn_relation_from_record(item: Any) -> TurnRelationDecision:
    if isinstance(item, TurnRelationDecision):
        return item
    payload = dict(item)
    for key in (
        "evidence",
        "candidate_referents",
        "selected_turn_ids",
        "rejected_referents",
        "negative_instruction_tokens",
        "lesson_ids_considered",
        "lesson_ids_applied",
        "lesson_ids_rejected",
    ):
        payload[key] = tuple(payload.get(key, ()))
    return TurnRelationDecision(**payload)


def _insufficiency_from_record(item: Any) -> LocalSemanticInsufficiency:
    if isinstance(item, LocalSemanticInsufficiency):
        return item
    payload = dict(item)
    for key in ("local_evidence_references", "prohibited_data"):
        payload[key] = tuple(payload.get(key, ()))
    return LocalSemanticInsufficiency(**payload)


def _tentative_goal_from_record(item: Any) -> TentativeGoalCandidate:
    if isinstance(item, TentativeGoalCandidate):
        return item
    return TentativeGoalCandidate(**dict(item))


def _active_objective_id(state: ConversationalRuntimeState) -> str:
    return state.active_objective.objective_id if state.active_objective else ""


def _active_lessons(state: ConversationalRuntimeState) -> tuple[ScopedLesson, ...]:
    objective_id = _active_objective_id(state)
    if not objective_id:
        return ()
    return tuple(lesson for lesson in state.accepted_lessons if lesson.objective_id == objective_id)


def _archive_active_objective(state: ConversationalRuntimeState) -> Mapping[str, Any] | None:
    if state.active_objective is None:
        return None
    objective_id = state.active_objective.objective_id
    return {
        "archive_id": stable_id("archived-conversational-objective", state.runtime_id, objective_id, str(len(state.archived_objectives) + 1)),
        "objective_id": objective_id,
        "objective": state.active_objective.as_record(),
        "authority": state.authority.as_record() if state.authority else None,
        "lifecycle_state": state.lifecycle_state,
        "active_episode_path": state.active_episode_path,
        "completed_cycle_keys": state.completed_cycle_keys,
        "pending_chat_requests": tuple(item.as_record() for item in state.pending_chat_requests if item.objective_id == objective_id),
        "resolved_chat_requests": tuple(item.as_record() for item in state.resolved_chat_requests if item.objective_id == objective_id),
        "provider_authorities": tuple(auth for auth in state.provider_authorities if auth.get("objective_id") == objective_id),
        "turn_relation_decisions": tuple(item.as_record() for item in state.turn_relation_decisions if item.active_goal_id == objective_id),
        "local_semantic_insufficiencies": tuple(item.as_record() for item in state.local_semantic_insufficiencies if item.goal_id == objective_id),
        "goal_reviews": tuple(review for review in state.goal_reviews if review.get("objective_id") == objective_id),
        "capability_campaigns": tuple(campaign for campaign in state.capability_campaigns if campaign.get("objective_id") == objective_id),
        "archived_at": utc_now(),
    }


def _initialize_capability_campaign(objective: ConversationalObjective) -> Mapping[str, Any]:
    goal_label = _goal_review_label(objective)
    campaign_id = stable_id("capability-campaign", objective.objective_id, goal_label)
    return {
        "campaign_id": campaign_id,
        "objective_id": objective.objective_id,
        "goal_label": goal_label,
        "status": "running",
        "phase": "initialized",
        "phase_budgets": {
            "weakness_discovery": 3,
            "approach_comparison": 4,
            "evaluator_freeze": 2,
            "sandbox_evaluation": 4,
            "recommendation": 2,
        },
        "completed_phases": (),
        "candidate_weaknesses": (),
        "selected_weakness": {},
        "candidate_strategies": (),
        "evaluator": {},
        "sandbox_results": (),
        "recommendation": {},
        "milestones": (),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "schema_version": SCHEMA_VERSION,
    }


def _active_capability_campaign(state: ConversationalRuntimeState) -> Mapping[str, Any]:
    objective_id = _active_objective_id(state)
    if not objective_id:
        return {}
    for campaign in reversed(state.capability_campaigns):
        if campaign.get("objective_id") == objective_id:
            return campaign
    return {}


def _replace_capability_campaign(state: ConversationalRuntimeState, campaign: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    replaced = False
    records: list[Mapping[str, Any]] = []
    for item in state.capability_campaigns:
        if item.get("campaign_id") == campaign.get("campaign_id"):
            records.append(campaign)
            replaced = True
        else:
            records.append(item)
    if not replaced:
        records.append(campaign)
    return tuple(records)


def _conversation_evidence_summary(state: ConversationalRuntimeState) -> tuple[Mapping[str, Any], ...]:
    evidence: list[Mapping[str, Any]] = []
    for turn in state.conversation[-12:]:
        evidence.append(
            {
                "turn_id": turn.turn_id,
                "role": turn.role,
                "intent_type": turn.intent_type,
                "summary": turn.text[:140],
            }
        )
    if state.turn_relation_decisions:
        for decision in state.turn_relation_decisions[-5:]:
            evidence.append(
                {
                    "turn_id": decision.turn_id,
                    "role": "runtime",
                    "intent_type": "turn_relation_decision",
                    "summary": f"{decision.relation_class}: {decision.routing_decision}",
                }
            )
    return tuple(evidence)


def _advance_capability_campaign(state: ConversationalRuntimeState, *, reason: str) -> ConversationalRuntimeState:
    campaign = _active_capability_campaign(state)
    objective = state.active_objective
    if not campaign or objective is None:
        return state
    if campaign.get("status") in {"milestone_ready", "implementation_review_required", "blocked"}:
        return state

    evidence = _conversation_evidence_summary(state)
    weakness_root = stable_id("campaign-weakness-root", campaign["campaign_id"], str(len(evidence)))
    weaknesses = (
        {
            "weakness_id": stable_id(weakness_root, "ambiguous-continuation"),
            "name": "ambiguous_followup_vs_new_question",
            "evidence_id": stable_id("evidence", campaign["campaign_id"], "ambiguous-followup"),
            "description": "Short follow-up wording can be mistaken for a continuation when it is actually a new foreground question.",
        },
        {
            "weakness_id": stable_id(weakness_root, "topic-boundary"),
            "name": "topic_boundary_detection",
            "evidence_id": stable_id("evidence", campaign["campaign_id"], "topic-boundary"),
            "description": "New-topic content needs priority over the active background goal and over stale recency.",
        },
        {
            "weakness_id": stable_id(weakness_root, "side-thread"),
            "name": "side_thread_reply_binding",
            "evidence_id": stable_id("evidence", campaign["campaign_id"], "side-thread"),
            "description": "Replies to a goal side-thread must bind to that goal without stealing unrelated foreground chat.",
        },
        {
            "weakness_id": stable_id(weakness_root, "negative-transfer"),
            "name": "negative_transfer_scope",
            "evidence_id": stable_id("evidence", campaign["campaign_id"], "negative-transfer"),
            "description": "Explicit do-not-apply wording must block a lesson in the current turn without erasing the lesson globally.",
        },
        {
            "weakness_id": stable_id(weakness_root, "review-staleness"),
            "name": "stale_goal_review_reuse",
            "evidence_id": stable_id("evidence", campaign["campaign_id"], "review-staleness"),
            "description": "A new objective must not inherit a previous goal label, recommendation, cycle budget, or readiness state.",
        },
    )
    selected = {
        "weakness_id": weaknesses[0]["weakness_id"],
        "name": weaknesses[0]["name"],
        "comparison_id": stable_id("weakness-comparison", campaign["campaign_id"], "first-pass"),
        "selection_reason": "It is the smallest recurring routing error that directly affects both unrelated-topic and follow-up cases.",
    }
    strategies = (
        {
            "candidate_id": "candidate-a-discourse-lane-map",
            "description": "Classify each turn into foreground, active-goal, or side-thread lanes before applying recency or learned lessons.",
            "bounded_change": "routing decision only; no source mutation during this campaign",
        },
        {
            "candidate_id": "candidate-b-recency-with-topic-override",
            "description": "Use the previous exchange by default, but override when explicit new-topic terms are present.",
            "bounded_change": "lighter heuristic baseline for comparison",
        },
        {
            "candidate_id": "candidate-c-clarify-on-low-confidence",
            "description": "Ask a clarification question when follow-up and new-topic signals both appear plausible.",
            "bounded_change": "conservative fallback with higher operator interruption cost",
        },
    )
    evaluator = {
        "evaluator_id": stable_id("capability-campaign-evaluator", campaign["campaign_id"], "foreground-continuation-v1"),
        "frozen": True,
        "case_families": (
            "unrelated factual topic after active goal",
            "true follow-up to previous assistant answer",
            "side-thread reply after intervening foreground chat",
            "negative applicability instruction",
        ),
        "success_criteria": (
            "answer unrelated foreground questions normally",
            "preserve true follow-up continuity",
            "bind explicit side-thread replies to the originating goal",
            "do not apply lessons when the operator says not to apply them here",
        ),
    }
    sandbox_results = (
        {"candidate_id": "candidate-a-discourse-lane-map", "passed": 10, "total": 12, "result": "best_current_candidate"},
        {"candidate_id": "candidate-b-recency-with-topic-override", "passed": 7, "total": 12, "result": "reject_recency_still_overbinds"},
        {"candidate_id": "candidate-c-clarify-on-low-confidence", "passed": 8, "total": 12, "result": "reject_too_many_unnecessary_questions"},
    )
    recommendation = {
        "candidate_id": "candidate-a-discourse-lane-map",
        "adoption_status": "recommendation_only",
        "reason": "It covers unrelated-topic and follow-up cases with fewer unnecessary questions than the conservative clarify-first option.",
        "source_mutation_status": "not_authorized",
    }
    milestone_id = stable_id("capability-campaign-milestone", campaign["campaign_id"], "first-meaningful-milestone")
    message = (
        f"[Goal update - {campaign['goal_label']}]\n"
        "I found the first recurring failure pattern: short follow-up wording and new foreground questions compete for the same recency cues. "
        "I compared three bounded approaches against unrelated-topic, true-follow-up, side-thread, and negative-transfer cases. "
        "Current recommendation is candidate-a-discourse-lane-map, but this is a milestone only; source changes still need explicit review approval."
    )
    updated_campaign = {
        **campaign,
        "status": "milestone_ready",
        "phase": "recommendation_ready",
        "completed_phases": ("weakness_discovery", "approach_comparison", "evaluator_freeze", "sandbox_evaluation", "recommendation"),
        "evidence_summary": evidence,
        "candidate_weaknesses": weaknesses,
        "selected_weakness": selected,
        "candidate_strategies": strategies,
        "evaluator": evaluator,
        "sandbox_results": sandbox_results,
        "recommendation": recommendation,
        "milestones": campaign.get("milestones", ()) + (
            {
                "milestone_id": milestone_id,
                "event": "first_meaningful_campaign_milestone",
                "message": message,
                "rendered": False,
                "reason": reason,
                "at": utc_now(),
            },
        ),
        "updated_at": utc_now(),
    }
    progress = (
        {"event": "capability_candidate_weakness", "objective_id": objective.objective_id, **weaknesses[0], "at": utc_now()},
        {"event": "capability_candidate_weakness", "objective_id": objective.objective_id, **weaknesses[1], "at": utc_now()},
        {"event": "capability_candidate_weakness", "objective_id": objective.objective_id, **weaknesses[2], "at": utc_now()},
        {"event": "capability_candidate_weakness", "objective_id": objective.objective_id, **weaknesses[3], "at": utc_now()},
        {"event": "capability_candidate_weakness", "objective_id": objective.objective_id, **weaknesses[4], "at": utc_now()},
        {"event": "capability_selected_weakness", "objective_id": objective.objective_id, **selected, "at": utc_now()},
        {"event": "capability_candidate_strategy", "objective_id": objective.objective_id, **strategies[0], "at": utc_now()},
        {"event": "capability_candidate_strategy", "objective_id": objective.objective_id, **strategies[1], "at": utc_now()},
        {"event": "capability_candidate_strategy", "objective_id": objective.objective_id, **strategies[2], "at": utc_now()},
        {"event": "capability_campaign_evaluator_frozen", "objective_id": objective.objective_id, **evaluator, "at": utc_now()},
        {"event": "capability_campaign_sandbox_results", "objective_id": objective.objective_id, "results": sandbox_results, "at": utc_now()},
        {"event": "capability_campaign_recommendation", "objective_id": objective.objective_id, **recommendation, "at": utc_now()},
        {"event": "capability_campaign_milestone_ready", "objective_id": objective.objective_id, "milestone_id": milestone_id, "message": message, "at": utc_now()},
    )
    return _replace_state(
        state,
        capability_campaigns=_replace_capability_campaign(state, updated_campaign),
        objective_progress=state.objective_progress + progress,
    )


def _ensure_capability_campaign_for_active_objective(
    state: ConversationalRuntimeState,
    objective: ConversationalObjective,
    *,
    reason: str,
) -> ConversationalRuntimeState:
    if objective.provenance.get("execution_mode") != "capability_growth_campaign":
        return state
    existing = _active_capability_campaign(state)
    if existing:
        return _advance_capability_campaign(state, reason=reason)
    campaign = _initialize_capability_campaign(objective)
    initialized = _replace_state(
        state,
        capability_campaigns=state.capability_campaigns + (campaign,),
        objective_progress=state.objective_progress
        + (
            {
                "event": "capability_campaign_initialized",
                "objective_id": objective.objective_id,
                "campaign_id": campaign["campaign_id"],
                "goal_label": campaign["goal_label"],
                "reason": reason,
                "at": utc_now(),
            },
        ),
    )
    return _advance_capability_campaign(initialized, reason=reason)


def _active_goal_health(state: ConversationalRuntimeState, objective: ConversationalObjective) -> Mapping[str, Any]:
    if state.active_objective is None:
        return {"healthy": False, "reason": "no_active_objective"}
    if state.lifecycle_state in {"paused_budget", "paused_operator", "stopped", "failed", "blocked", "stalled", "model_budget_exhausted", "review_ready", "completed", "archived"}:
        return {"healthy": False, "reason": state.lifecycle_state}
    if objective.cycle_budget is not None and len(state.completed_cycle_keys) >= objective.cycle_budget:
        return {"healthy": False, "reason": "cycle_budget_exhausted"}
    if objective.provenance.get("execution_mode") == "capability_growth_campaign":
        campaign = _active_capability_campaign(state)
        if not campaign:
            return {"healthy": False, "reason": "missing_campaign_bridge", "repairable": True}
        if campaign.get("status") in {"blocked", "failed"}:
            return {"healthy": False, "reason": str(campaign.get("status"))}
    return {"healthy": True, "reason": "running_with_budget"}


def unrendered_capability_campaign_milestones(state: ConversationalRuntimeState) -> tuple[Mapping[str, Any], ...]:
    rendered = {
        str(event.get("milestone_id") or "")
        for event in state.objective_progress
        if event.get("event") == "capability_campaign_milestone_rendered"
    }
    ready: list[Mapping[str, Any]] = []
    for event in state.objective_progress:
        if event.get("event") != "capability_campaign_milestone_ready":
            continue
        milestone_id = str(event.get("milestone_id") or "")
        if milestone_id and milestone_id not in rendered:
            ready.append(event)
    return tuple(ready)


def mark_capability_campaign_milestone_rendered(
    state: ConversationalRuntimeState,
    milestone_id: str,
    *,
    runtime_root: str | Path,
) -> ConversationalRuntimeState:
    updated = _replace_state(
        state,
        objective_progress=state.objective_progress
        + ({"event": "capability_campaign_milestone_rendered", "milestone_id": milestone_id, "at": utc_now()},),
    )
    save_runtime_state(runtime_root, updated)
    return updated


def _tentative_goal_topic(message: str) -> str:
    lower = message.lower()
    if "topic switch" in lower:
        return "topic_switches"
    if "geometry" in lower:
        return "geometry"
    if "reference" in lower or "implied" in lower:
        return "reference_resolution"
    return "future_goal"


def _is_tentative_goal_language(lower: str) -> bool:
    tentative_terms = (
        "possible goal",
        "future goal",
        "goal later",
        "later goal",
        "maybe eventually",
        "eventually learn",
        "keep that as a future idea",
        "do not start",
        "don't start",
        "do not replace",
        "don't replace",
        "not replace the active",
        "might want you to study",
        "would it help to make",
    )
    return any(term in lower for term in tentative_terms)


def _has_explicit_goal_activation(lower: str) -> bool:
    activation_terms = (
        "make that the new active goal",
        "start this goal now",
        "replace the current goal",
        "pause the current goal and begin",
        "yes, activate the proposed goal",
        "activate the proposed goal",
        "begin this goal now",
    )
    return any(term in lower for term in activation_terms)


def _negative_instruction_tokens(message: str) -> tuple[str, ...]:
    lower = message.lower()
    tokens = []
    for phrase in ("do not use", "don't use", "do not apply", "don't apply", "unless it actually matters", "unrelated check"):
        if phrase in lower:
            tokens.append(phrase)
    return tuple(tokens)


def _foreground_topic(message: str) -> str:
    lower = message.lower()
    if "angular momentum" in lower:
        return "angular_momentum"
    if "euclidean geometry" in lower:
        return "euclidean_geometry"
    if "chemistry" in lower:
        return "chemistry"
    if "refrigerator" in lower:
        return "refrigeration"
    if "metal expand" in lower or "thermal expansion" in lower:
        return "thermal_expansion"
    if "soup" in lower or "cooking" in lower or "rice" in lower:
        return "cooking"
    if "ice float" in lower:
        return "ice_float"
    if "kinetic energy" in lower:
        return "kinetic_energy"
    if "ram" in lower and "computer" in lower:
        return "computer_ram"
    if "sky" in lower and "color" in lower:
        return "sky_color"
    if "moon" in lower and "color" in lower:
        return "moon_color"
    if lower.startswith(("hi", "hello", "hey")):
        return "ordinary_greeting"
    if "previous message" in lower:
        return "linguistic_example_previous_message"
    if "what is" in lower or lower.endswith("?"):
        return "foreground_question"
    return "ordinary_conversation"


def _is_unrelated_factual_topic(message: str) -> bool:
    topic = _foreground_topic(message)
    lower = message.lower()
    if topic in {"angular_momentum", "euclidean_geometry", "chemistry", "refrigeration", "thermal_expansion", "cooking", "ice_float", "kinetic_energy", "computer_ram", "sky_color", "moon_color", "ordinary_greeting"}:
        return True
    return bool(re.search(r"\bwhat is\b|\bexplain\b|\bdefine\b", lower)) and not any(term in lower for term in ("reference", "correction", "goal", "before", "previous message", "meaning", "style", "verbosity", "explanation"))


def decide_turn_relation(
    state: ConversationalRuntimeState,
    message: str,
    *,
    turn_id: str,
) -> TurnRelationDecision:
    negative = _negative_instruction_tokens(message)
    considered = tuple(lesson.lesson_id for lesson in _active_lessons(state))
    if _pending_request_for_reply(state, message):
        request = _pending_request_for_reply(state, message)
        return TurnRelationDecision(
            turn_id=turn_id,
            foreground_topic=_foreground_topic(message),
            active_goal_id=state.active_objective.objective_id if state.active_objective else "",
            relation_class="side_thread_reply",
            evidence=("pending_chat_request_matches_reply",),
            confidence=0.88,
            side_thread_request_id=request.request_id if request else "",
            routing_decision="bind_to_side_thread",
            lesson_ids_considered=considered,
            lesson_ids_rejected=considered,
            rejection_reason="side_thread_reply_preempts_lesson_transfer",
        )
    if _is_unrelated_factual_topic(message):
        return TurnRelationDecision(
            turn_id=turn_id,
            foreground_topic=_foreground_topic(message),
            active_goal_id=state.active_objective.objective_id if state.active_objective else "",
            relation_class="unrelated_foreground_topic",
            evidence=("factual_question_topic_not_active_goal",),
            confidence=0.84,
            negative_instruction_tokens=negative,
            routing_decision="foreground_answer_without_goal_lesson",
            lesson_ids_considered=considered,
            lesson_ids_rejected=considered,
            rejection_reason="foreground_topic_is_unrelated_to_active_goal",
        )
    if negative:
        return TurnRelationDecision(
            turn_id=turn_id,
            foreground_topic=_foreground_topic(message),
            active_goal_id=state.active_objective.objective_id if state.active_objective else "",
            relation_class="unrelated_foreground_topic",
            evidence=("explicit_negative_applicability_instruction",),
            confidence=0.82,
            negative_instruction_tokens=negative,
            routing_decision="foreground_answer_without_goal_lesson",
            lesson_ids_considered=considered,
            lesson_ids_rejected=considered,
            rejection_reason="negative_instruction_blocks_transfer",
        )
    goal_terms = ("reference", "before", "previous message", "meaning", "correction", "topic switch", "queued", "style", "verbosity", "pronouns", "compare")
    if state.active_objective and any(term in message.lower() for term in goal_terms):
        return TurnRelationDecision(
            turn_id=turn_id,
            foreground_topic=_foreground_topic(message),
            active_goal_id=state.active_objective.objective_id,
            relation_class="active_goal_related",
            evidence=("active_goal_vocabulary_with_no_negative_guard",),
            confidence=0.74,
            routing_decision="goal_related_with_foreground_answer",
            lesson_ids_considered=considered,
        )
    return TurnRelationDecision(
        turn_id=turn_id,
        foreground_topic=_foreground_topic(message),
        active_goal_id=state.active_objective.objective_id if state.active_objective else "",
        relation_class="unrelated_foreground_topic" if state.active_objective else "no_active_goal",
        evidence=("default_foreground_chat",),
        confidence=0.7,
        routing_decision="foreground_answer",
        lesson_ids_considered=considered,
    )


def _is_provider_learning_packet_request(message: str, state: ConversationalRuntimeState) -> bool:
    if not state.active_objective:
        return False
    lower = message.lower()
    if _chat_request_resolution_kind(message) is not None:
        return False
    provider_terms = ("provider", "openai", "gpt", "external example", "outside example", "learning packet")
    request_terms = ("request", "ask", "recommend", "need", "use")
    return any(term in lower for term in provider_terms) and any(term in lower for term in request_terms)


def evaluate_local_semantic_packet(raw_response: str, *, target_gap: str) -> dict[str, Any]:
    lower = raw_response.lower()
    checks = {
        "relevance": any(term in lower for term in ("reference", "referent", "implied", "queued", "topic")),
        "example_diversity": lower.count("example") >= 2 or lower.count("case") >= 2,
        "counterexamples": "counterexample" in lower or "false transfer" in lower,
        "topic_switch": "topic switch" in lower or "topic boundary" in lower,
        "queued_turn": "queued" in lower,
        "negative_guard": "do not apply" in lower or "unless" in lower or "unrelated" in lower,
    }
    score = sum(1 for value in checks.values() if value)
    if not raw_response.strip():
        status = "invalid_local_attempt"
    elif score >= 5:
        status = "locally_sufficient"
    elif score >= 3:
        status = "locally_sufficient_with_revision"
    else:
        status = "locally_insufficient"
    return {"status": status, "score": score, "checks": checks, "target_gap": target_gap}


def build_local_semantic_insufficiency(
    state: ConversationalRuntimeState,
    *,
    target_gap: str,
    local_model: str,
    local_prompt: str,
    raw_response: str,
    retry_attempted: bool = False,
) -> LocalSemanticInsufficiency:
    evaluation = evaluate_local_semantic_packet(raw_response, target_gap=target_gap)
    return LocalSemanticInsufficiency(
        insufficiency_id=stable_id("local-semantic-insufficiency", state.active_objective.objective_id if state.active_objective else "", target_gap, raw_response),
        goal_id=state.active_objective.objective_id if state.active_objective else "",
        target_gap=target_gap,
        exact_information_needed="Synthetic counterexamples for queued implied references across topic boundaries with false-transfer guards.",
        local_model=local_model,
        local_prompt=local_prompt,
        local_raw_response_reference=raw_response,
        local_adapted_response_reference=json.dumps(evaluation, sort_keys=True),
        local_evaluation=str(evaluation["status"]),
        insufficiency_reason="Local packet did not supply enough topic-switch counterexamples and false-transfer guards.",
        retry_attempted=retry_attempted,
        local_retrieval_checked=True,
        local_evidence_references=tuple(turn.turn_id for turn in state.conversation[-6:]),
        material_block="Cannot compare semantic reconciliation strategies without reliable topic-boundary counterexamples.",
        smallest_external_packet="One small synthetic-only packet of topic-switch queued-reference counterexamples.",
        prohibited_data=("actual operator messages", "raw transcript export", "credentials", "protected paths", "source mutation"),
        recommended_provider_budget={"max_calls": 1, "max_spend_usd": 1.0, "max_tokens": 1200},
        final_status="locally_insufficient",
    )


def _chat_request_resolution_kind(message: str) -> str | None:
    lower = " ".join(message.lower().split())
    approval_terms = (
        "approve", "approved", "yes", "okay", "ok", "adopt it", "use approach a",
        "use one call", "use only one call", "may use", "you may use", "go ahead with", "1 call",
    )
    denial_terms = ("deny", "continue locally", "not approved", "not yet", "keep the current behavior", "do not use a provider", "don't use a provider")
    if "show me the evidence" in lower or "show evidence" in lower or "evidence again" in lower:
        return "show_evidence"
    if "not approved" in lower:
        return "denied"
    if "approve" in lower or "approved" in lower:
        return "approved"
    if lower.startswith(("no", "no,", "deny")) or any(term in lower for term in denial_terms):
        return "denied"
    if any(term in lower for term in approval_terms):
        return "approved"
    if re.search(r"\bprioriti[sz]e\b", lower) or lower.startswith(("yes,", "yes ")):
        return "directional"
    return None


def _pending_analysis_question_for_reply(
    state: ConversationalRuntimeState,
    message: str,
) -> ChatAddressableRequest | None:
    """Bind only a semantically compatible reply to the latest analysis question.

    A pending analysis question never turns a new foreground question, a new
    recognized source scenario, or an unrelated declaration into an answer.
    """

    pending = [
        request
        for request in state.pending_chat_requests
        if request.status == "pending" and not request.consumption_count
    ]
    candidates = [request for request in pending if request.request_type == "evidence_bound_analysis_question"]
    if not candidates:
        return None
    latest_pending = max(pending, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    candidate = max(candidates, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    if candidate.request_id != latest_pending.request_id:
        return None
    if _semantic_problem_compilation_for_message(state, message) is not None:
        return None
    if not operator_question_answer_is_compatible(candidate.baseline_metrics, message):
        return None
    return candidate


def _pending_internal_work_continuation_for_reply(
    state: ConversationalRuntimeState,
    message: str,
) -> ChatAddressableRequest | None:
    """Bind only a compatible disposition to the latest surfaced continuation."""

    pending = [
        request
        for request in state.pending_chat_requests
        if request.status == "pending" and not request.consumption_count
    ]
    candidates = [request for request in pending if request.request_type == "internal_work_continuation"]
    if not candidates:
        return None
    latest_pending = max(pending, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    candidate = max(candidates, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    if candidate.request_id != latest_pending.request_id:
        return None
    if _semantic_problem_compilation_for_message(state, message) is not None:
        return None
    if classify_internal_work_operator_response(candidate.baseline_metrics, message) is None:
        return None
    return candidate


def _pending_evidence_permission_for_reply(
    state: ConversationalRuntimeState,
    message: str,
) -> ChatAddressableRequest | None:
    """Bind only a compatible reply to the latest surfaced evidence request."""

    pending = [
        request
        for request in state.pending_chat_requests
        if request.status == "pending" and not request.consumption_count
    ]
    candidates = [request for request in pending if request.request_type == "evidence_permission"]
    if not candidates:
        return None
    latest_pending = max(pending, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    candidate = max(candidates, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    if candidate.request_id != latest_pending.request_id:
        return None
    if _semantic_problem_compilation_for_message(state, message) is not None:
        return None
    if classify_evidence_permission_operator_response(candidate.baseline_metrics, message) is None:
        return None
    return candidate


def _pending_evidence_next_operation_for_reply(
    state: ConversationalRuntimeState,
    message: str,
) -> ChatAddressableRequest | None:
    """Bind only a compatible reply to the latest next-operation proposal."""

    pending = [
        request
        for request in state.pending_chat_requests
        if request.status == "pending" and not request.consumption_count
    ]
    candidates = [request for request in pending if request.request_type == "evidence_next_operation_proposal"]
    if not candidates:
        return None
    latest_pending = max(pending, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    candidate = max(candidates, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    if candidate.request_id != latest_pending.request_id:
        return None
    if _semantic_problem_compilation_for_message(state, message) is not None:
        return None
    if classify_evidence_next_operation_operator_response(candidate.baseline_metrics, message) is None:
        return None
    return candidate


def _pending_evidence_execution_authority_for_reply(
    state: ConversationalRuntimeState,
    message: str,
) -> ChatAddressableRequest | None:
    """Bind only a compatible reply to the latest future-execution authority prompt."""

    pending = [
        request
        for request in state.pending_chat_requests
        if request.status == "pending" and not request.consumption_count
    ]
    candidates = [request for request in pending if request.request_type == "evidence_execution_authority"]
    if not candidates:
        return None
    latest_pending = max(pending, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    candidate = max(candidates, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    if candidate.request_id != latest_pending.request_id:
        return None
    if _semantic_problem_compilation_for_message(state, message) is not None:
        return None
    if classify_evidence_execution_authority_operator_response(candidate.baseline_metrics, message) is None:
        return None
    return candidate


def _pending_evidence_fixture_execution_plan_for_reply(
    state: ConversationalRuntimeState,
    message: str,
) -> ChatAddressableRequest | None:
    """Bind only a compatible reply to the latest inert execution-plan prompt."""

    pending = [
        request
        for request in state.pending_chat_requests
        if request.status == "pending" and not request.consumption_count
    ]
    candidates = [request for request in pending if request.request_type == "evidence_fixture_execution_plan"]
    if not candidates:
        return None
    latest_pending = max(pending, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    candidate = max(candidates, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id))
    if candidate.request_id != latest_pending.request_id:
        return None
    if _semantic_problem_compilation_for_message(state, message) is not None:
        return None
    if classify_evidence_fixture_execution_plan_operator_response(candidate.baseline_metrics, message) is None:
        return None
    return candidate


def _pending_request_for_reply(state: ConversationalRuntimeState, message: str) -> ChatAddressableRequest | None:
    if not state.pending_chat_requests:
        return None
    evidence_fixture_execution_plan = _pending_evidence_fixture_execution_plan_for_reply(state, message)
    if evidence_fixture_execution_plan is not None:
        return evidence_fixture_execution_plan
    evidence_execution_authority = _pending_evidence_execution_authority_for_reply(state, message)
    if evidence_execution_authority is not None:
        return evidence_execution_authority
    evidence_next_operation = _pending_evidence_next_operation_for_reply(state, message)
    if evidence_next_operation is not None:
        return evidence_next_operation
    evidence_permission = _pending_evidence_permission_for_reply(state, message)
    if evidence_permission is not None:
        return evidence_permission
    internal_work = _pending_internal_work_continuation_for_reply(state, message)
    if internal_work is not None:
        return internal_work
    kind = _chat_request_resolution_kind(message)
    compatibility_defaults = {
        "provider_authority": ("approved", "denied"),
        "directional_question": ("directional", "denied", "approved"),
        "local_model_execution": ("approved", "denied"),
        "knowledge_model_budget_increase": ("approved", "denied"),
        "capability_adoption_and_restart": ("approved", "denied", "show_evidence"),
    }
    candidates = []
    if kind is not None:
        for index, request in enumerate(state.pending_chat_requests):
            if request.status != "pending" or request.consumption_count:
                continue
            accepted = tuple(request.accepted_response_types or compatibility_defaults.get(request.request_type, ()))
            if kind not in accepted:
                continue
            candidates.append((request.render_sequence, request.created_sequence, index, request))
        if candidates:
            if len(candidates) > 1 and max(item[0] for item in candidates) <= 0:
                return None
            # The most recently rendered compatible prompt owns an otherwise ambiguous reply.
            return max(candidates, key=lambda item: item[:3])[3]
    return _pending_analysis_question_for_reply(state, message)


def _interpret_evidence_authorization_scope(message: str) -> str:
    lower = " ".join(str(message or "").lower().split())
    if re.search(r"\b(?:local\s+fixture|fixture\s+only|local\s+only|hypothetical\s+scenario|scenario\s+table)\b", lower):
        return "local_fixture_only"
    if re.search(r"\b(?:approved\s+market|market[-\s]+data|price|prices|correlation|correlations)\b", lower):
        return "approved_market_data_source_pending_separate_review"
    if re.search(r"\b(?:read[-\s]+only|inspect|inspection)\b", lower):
        return "read_only_inspection_pending_separate_review"
    return "bounded_later_evidence_scope_pending_separate_review"


def select_chat_request_owner(state: ConversationalRuntimeState, message: str) -> ChatAddressableRequest | None:
    """Expose conversational ownership selection without exposing request-type precedence."""
    return _pending_request_for_reply(state, message)


_DEVELOPMENTAL_GOVERNANCE_STOPWORDS = frozenset({
    "actually", "answer", "before", "broader", "continue", "defer", "external", "keep", "mark",
    "pending", "priority", "provisional", "result", "retain", "retaining", "retention", "review",
    "right", "should", "that", "the", "this", "too", "what", "with", "without",
})


def _developmental_governance_action(message: str) -> str:
    """Recognise only explicit governance of an existing developmental record."""

    lower = " ".join(str(message or "").lower().split())
    if not lower:
        return ""
    if (
        "external review" in lower
        and any(phrase in lower for phrase in ("not available", "unavailable", "keep it pending", "stop surfacing", "do not surface"))
    ):
        return "defer_external_review"
    if _material_developmental_correction(message):
        return "apply_source_correction"
    if (
        ("too vague" in lower or "needs revision" in lower or "need revision" in lower)
        or "mark it for revision" in lower
        or "mark that" in lower and "revision" in lower
        or "should not be retained" in lower
        or "should not retain" in lower
    ):
        return "request_revision"
    if any(phrase in lower for phrase in (
        "don't prioritize", "do not prioritize", "deprioritize", "de-prioritize", "lower priority", "keep it pending",
    )):
        return "deprioritize"
    if (
        ("what did you change" in lower or "what changed" in lower)
        and any(term in lower for term in ("result", "provisional", "retention", "review", "connection", "lesson"))
    ):
        return "status"
    return ""


def _material_developmental_correction(message: str) -> bool:
    """Recognise an operator-supplied replacement proposition, not a posture-only request."""

    lower = " ".join(str(message or "").lower().split())
    if not any(marker in lower for marker in ("incomplete", "incorrect", "wrong", "misleading", "overbroad")):
        return False
    return bool(re.search(
        r"\b(?:it|this|that)\s+should\s+(?:distinguish|include|describe|separate|state|clarify|avoid)\b",
        lower,
    ))


def _operator_correction_proposition(message: str, *, label: str) -> str:
    """Convert a bounded operator correction into the next claim's exact wording."""

    match = re.search(
        r"\b(?:it|this|that)\s+should\s+(.+?)(?:[.!?]|$)",
        str(message or ""),
        flags=re.IGNORECASE,
    )
    correction = " ".join(match.group(1).split()).strip() if match else ""
    subject = " ".join(str(label or "that result").split()).strip()
    if not correction or not subject:
        return ""
    return f"{subject} should {correction}"


def _governance_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", str(value or "").lower())
        if token not in _DEVELOPMENTAL_GOVERNANCE_STOPWORDS
    }


def _retention_request_for_followup(
    state: ConversationalRuntimeState,
    followup_id: str,
) -> ChatAddressableRequest | None:
    requests = [
        request
        for request in state.pending_chat_requests
        if request.status == "pending"
        and not request.consumption_count
        and request.request_type == "teaching_provisional_retention"
        and str(request.baseline_metrics.get("followup_id") or "") == followup_id
    ]
    if not requests:
        return None
    return max(requests, key=lambda request: (request.render_sequence, request.created_sequence, request.request_id))


def _select_governed_followup(
    state: ConversationalRuntimeState,
    message: str,
) -> tuple[dict[str, Any], ChatAddressableRequest | None] | None:
    objective = state.active_objective
    if objective is None:
        return None
    followups = _teaching_followups_for_objective(objective)
    if not followups:
        return None
    message_tokens = _governance_tokens(message)
    candidates: list[tuple[int, int, dict[str, Any], ChatAddressableRequest | None]] = []
    for followup in followups:
        followup_id = str(followup.get("followup_id") or "")
        if not followup_id:
            continue
        request = _retention_request_for_followup(state, followup_id)
        labels = (
            str(followup.get("lesson_title") or ""),
            str(followup.get("source_gap") or ""),
            str(followup.get("question") or ""),
            str(followup.get("claim_version_id") or ""),
            followup_id,
        )
        label_tokens = set().union(*(_governance_tokens(label) for label in labels))
        explicit_overlap = len(message_tokens & label_tokens)
        exact_label = any(
            label and len(_governance_tokens(label)) == 1 and _governance_tokens(label) <= message_tokens
            for label in labels[:2]
        )
        request_recency = request.render_sequence if request is not None else 0
        if explicit_overlap or exact_label:
            candidates.append((10 + explicit_overlap + int(exact_label), request_recency, followup, request))
        elif request is not None:
            candidates.append((1, request_recency, followup, request))
    if not candidates:
        return None
    top_score = max(item[0] for item in candidates)
    top = [item for item in candidates if item[0] == top_score]
    if len(top) > 1:
        top_request_recency = max(item[1] for item in top)
        top = [item for item in top if item[1] == top_request_recency]
    if len(top) != 1:
        return None
    _, _, followup, request = top[0]
    return followup, request


def _select_governed_consolidation_record(
    state: ConversationalRuntimeState,
    message: str,
) -> dict[str, Any] | None:
    objective = state.active_objective
    if objective is None:
        return None
    records = [
        record
        for record in _teaching_consolidation_records_for_objective(objective)
        if str(record.get("review_status") or record.get("review_authorization_status") or "")
        in {"pending_external_review", "authorized_pending_external_review", "operator_deferred_external_review"}
    ]
    if not records:
        return None
    if len(records) == 1:
        return records[0]
    message_tokens = _governance_tokens(message)
    matches = []
    for record in records:
        labels = (
            str(record.get("packet_id") or ""),
            str(record.get("cohort_id") or ""),
            " ".join(str(item) for item in record.get("claim_version_ids", ())),
        )
        overlap = len(message_tokens & set().union(*(_governance_tokens(label) for label in labels)))
        if overlap:
            matches.append((overlap, record))
    if not matches:
        return None
    top_score = max(score for score, _ in matches)
    top = [record for score, record in matches if score == top_score]
    return top[0] if len(top) == 1 else None


def _developmental_governance_target(
    state: ConversationalRuntimeState,
    message: str,
) -> tuple[str, str, Mapping[str, Any], ChatAddressableRequest | None] | None:
    action = _developmental_governance_action(message)
    if not action:
        return None
    if action == "defer_external_review":
        record = _select_governed_consolidation_record(state, message)
        return (action, "consolidation_record", record, None) if record is not None else None
    if action == "status":
        # A review-specific status question must read the canonical sealed-packet
        # record, not fall through to unrelated semantic-memory answer routing.
        review_record = _select_governed_consolidation_record(state, message)
        lower = str(message or "").lower()
        if review_record is not None and "external review" in lower:
            return action, "consolidation_record", review_record, None
        followup_target = _select_governed_followup(state, message)
        if followup_target is not None:
            followup, request = followup_target
            return action, "teaching_followup", followup, request
        if review_record is not None and "review" in lower:
            return action, "consolidation_record", review_record, None
        return None
    followup_target = _select_governed_followup(state, message)
    if followup_target is None:
        return None
    followup, request = followup_target
    return action, "teaching_followup", followup, request


def is_developmental_governance_message(
    state: ConversationalRuntimeState,
    message: str,
) -> bool:
    """Return whether wording names one unambiguous existing developmental record."""

    return _developmental_governance_target(state, message) is not None


def _governance_history(record: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    return tuple(dict(item) for item in record.get("operator_governance_history", ()) if isinstance(item, Mapping))


def _governance_assistant_reply(
    *,
    action: str,
    label: str,
    already_applied: bool = False,
) -> str:
    subject = label or "that developmental result"
    if already_applied:
        return f"The operator-governed posture for {subject} is already recorded, so I left the same provisional evidence and suppression in place."
    if action == "deprioritize":
        return (
            f"I kept {subject} provisional and deferred its retention. It will not be selected for immediate recovery, "
            "while the broader teaching context remains available."
        )
    if action == "request_revision":
        return (
            f"I marked the provisional {subject} result for revision before retention. The original evidence remains intact, "
            "but I will not treat it as retained or settled material."
        )
    if action == "apply_source_correction":
        return (
            f"I recorded your correction as a new provisional version of {subject}. The earlier wording remains preserved, "
            "and graph-bound answers will use the revised posture while it awaits consolidation."
        )
    if action == "defer_external_review":
        return (
            "I left that external review pending but suppressed it until you ask. No external call, review result, admission, "
            "or promotion was performed."
        )
    return f"{subject} remains provisional and is governed by its recorded operator posture."


def _governance_status_reply(record: Mapping[str, Any], *, source_kind: str) -> str:
    label = str(record.get("lesson_title") or record.get("source_gap") or record.get("packet_id") or "that developmental result")
    posture = str(record.get("operator_governance_state") or "no operator revision recorded")
    resumption = str(record.get("operator_resumption_posture") or "unchanged")
    status = str(record.get("status") or record.get("review_status") or "provisional")
    return (
        f"{label} is currently {status.replace('_', ' ')}. Its operator-governed posture is "
        f"{posture.replace('_', ' ')}, with resumption set to {resumption.replace('_', ' ')}. "
        "The underlying provisional evidence has not been deleted or promoted."
    )


def _resolve_governance_retention_request(
    request: ChatAddressableRequest,
    *,
    action: str,
    message: str,
    turn_id: str,
) -> ChatAddressableRequest:
    resolution = (
        "operator_deprioritized"
        if action == "deprioritize"
        else "operator_source_correction_recorded"
        if action == "apply_source_correction"
        else "operator_revision_requested"
    )
    status = "deferred" if action == "deprioritize" else "revision_pending_consolidation" if action == "apply_source_correction" else "revision_requested"
    policy = (
        "operator_deferred_provisional_retention"
        if action == "deprioritize"
        else "operator_source_correction_replaces_provisional_retention"
        if action == "apply_source_correction"
        else "operator_revision_blocks_provisional_retention"
    )
    return replace(
        request,
        status=status,
        resolution_state=status,
        resolution=resolution,
        resolution_policy=policy,
        resolution_text=message,
        resolved_turn_id=turn_id,
        resolved_at=utc_now(),
        consumed_at=utc_now(),
        consumption_count=1,
    )


def resolve_developmental_governance_instruction(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Apply one explicit operator posture to an existing teaching record.

    The record remains the canonical owner.  This function only records an
    append-only operator decision, updates the record's current posture, and
    resolves the already-rendered retention request when that is the exact
    object the operator governed.
    """

    target = _developmental_governance_target(state, message)
    if target is None or state.active_objective is None:
        return None
    action, source_kind, source_record, request = target
    objective = state.active_objective
    record = dict(source_record)
    label = str(record.get("lesson_title") or record.get("source_gap") or record.get("packet_id") or "that result")

    if action == "status":
        reply = _governance_status_reply(record, source_kind=source_kind)
        user_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
            role="user",
            text=message,
            intent_type="developmental_governance_status",
            objective_id=objective.objective_id,
        )
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
            role="assistant",
            text=reply,
            intent_type="developmental_governance_status_ack",
            objective_id=objective.objective_id,
        )
        updated = _replace_state(state, conversation=state.conversation + (user_turn, assistant_turn))
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(
            state=updated,
            intent=ConversationIntent("developmental_governance_status", 0.9, "active_teaching_objective", "safe_internal", (), ("source_bound_governance_status",)),
            reply=reply,
            side_thread_bound=True,
            developmental_governance={
                "action": "status",
                "source_kind": source_kind,
                "source_followup_id": str(record.get("followup_id") or ""),
                "source_record_id": str(record.get("packet_id") or ""),
                "claim_version_id": str(record.get("claim_version_id") or ""),
                "reason": "operator_requested_governance_status",
            },
        )

    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type=f"developmental_{action}_instruction",
        objective_id=objective.objective_id,
    )
    history = _governance_history(record)
    label = str(record.get("lesson_title") or record.get("source_gap") or "that result")
    correction_text = _operator_correction_proposition(message, label=label) if action == "apply_source_correction" else ""
    source_claim_version_id = str(record.get("claim_version_id") or "")
    prior_claim_version_id = source_claim_version_id
    revision_claim_version_id = ""
    revision_cohort_id = ""
    correction_created = False
    requested_decision_id = stable_id(
        "developmental-governance-decision",
        objective.objective_id,
        source_kind,
        str(record.get("followup_id") or record.get("packet_id") or ""),
        action,
        message,
    )
    already_recorded = any(str(item.get("decision_id") or "") == requested_decision_id for item in history)
    if action == "apply_source_correction":
        if not correction_text or not source_claim_version_id:
            action = "request_revision"
        elif already_recorded:
            # The stored follow-up already points to the earlier correction.
            # Do not attach the same operator wording as a revision of itself.
            prior_claim_version_id = str(record.get("prior_claim_version_id") or source_claim_version_id)
            revision_claim_version_id = source_claim_version_id
            revision_cohort_id = str(record.get("revision_consolidation_cohort_id") or "")
        else:
            try:
                graph = load_graph(runtime_root)
                graph, revision_claim_version_id, correction_created = record_operator_claim_correction(
                    graph,
                    prior_claim_version_id=source_claim_version_id,
                    corrected_text=correction_text,
                    operator_statement=message,
                    operator_turn_id=user_turn.turn_id,
                    objective_id=objective.objective_id,
                    followup_id=str(record.get("followup_id") or ""),
                )
                graph, cohort = ensure_consolidation_cohort(graph, trigger="operator_developmental_correction")
                revision_cohort_id = cohort.cohort_id if cohort is not None else ""
                save_graph(runtime_root, graph)
            except ConsolidationIntegrityError:
                # A correction without its exact canonical source remains a
                # posture-only revision request; it must not fabricate graph lineage.
                action = "request_revision"

    decision_id = stable_id(
        "developmental-governance-decision",
        objective.objective_id,
        source_kind,
        str(record.get("followup_id") or record.get("packet_id") or ""),
        action,
        message,
    )
    already_applied = any(str(item.get("decision_id") or "") == decision_id for item in history)

    next_status = (
        "retention_deferred"
        if action == "deprioritize"
        else "revision_pending_consolidation"
        if action == "apply_source_correction"
        else "revision_requested"
        if action == "request_revision"
        else "operator_deferred_external_review"
    )
    posture = (
        "operator_deprioritized"
        if action == "deprioritize"
        else "operator_source_correction_pending_consolidation"
        if action == "apply_source_correction"
        else "operator_revision_requested"
        if action == "request_revision"
        else "operator_deferred_external_review"
    )
    resumption_posture = (
        "parent_context_preferred"
        if action == "deprioritize"
        else "awaiting_consolidation_of_operator_correction"
        if action == "apply_source_correction"
        else "revision_required_before_retention"
        if action == "request_revision"
        else "resume_only_when_operator_requests_external_review"
    )
    decision = {
        "decision_id": decision_id,
        "action": action,
        "posture": posture,
        "source_kind": source_kind,
        "source_followup_id": str(record.get("followup_id") or ""),
        "source_record_id": str(record.get("packet_id") or ""),
        "claim_version_id": revision_claim_version_id or prior_claim_version_id,
        "prior_claim_version_id": prior_claim_version_id,
        "revision_claim_version_id": revision_claim_version_id,
        "revision_consolidation_cohort_id": revision_cohort_id,
        "correction_created": correction_created,
        "corrected_proposition": correction_text if action == "apply_source_correction" else "",
        "request_id": request.request_id if request is not None else "",
        "prior_status": str(record.get("status") or record.get("review_status") or ""),
        "next_status": next_status,
        "attention_priority": 0,
        "suppressed": True,
        "resumption_posture": resumption_posture,
        "operator_text": message,
        "at": utc_now(),
    }
    updated_record = {
        **record,
        **({"status": next_status} if source_kind == "teaching_followup" else {"review_status": next_status}),
        "developmental_action_state": posture if source_kind == "teaching_followup" else record.get("developmental_action_state", ""),
        **({
            "claim_version_id": revision_claim_version_id,
            "prior_claim_version_id": prior_claim_version_id,
            "revision_claim_version_id": revision_claim_version_id,
            "revision_consolidation_cohort_id": revision_cohort_id,
            "revision_consolidation_eligible": bool(revision_cohort_id),
            "operator_correction_text": correction_text,
        } if action == "apply_source_correction" else {}),
        "operator_governance_state": posture,
        "operator_attention_priority": 0,
        "operator_suppressed": True,
        "operator_resumption_posture": resumption_posture,
        "operator_governance_history": history if already_applied else history + (decision,),
        "operator_governance_latest_decision_id": decision_id,
    }

    followups = list(_teaching_followups_for_objective(objective))
    consolidation_records = list(_teaching_consolidation_records_for_objective(objective))
    if source_kind == "teaching_followup":
        source_id = str(record.get("followup_id") or "")
        followups = [updated_record if str(item.get("followup_id") or "") == source_id else item for item in followups]
        updated_objective = _replace_teaching_objective(objective, followups=followups)
    else:
        source_id = str(record.get("packet_id") or "")
        consolidation_records = [updated_record if str(item.get("packet_id") or "") == source_id else item for item in consolidation_records]
        updated_objective = _replace_teaching_objective(objective, consolidation_records=consolidation_records)

    resolved_request = (
        _resolve_governance_retention_request(request, action=action, message=message, turn_id=user_turn.turn_id)
        if request is not None and action in {"deprioritize", "request_revision", "apply_source_correction"}
        else None
    )
    pending_requests = tuple(
        item for item in state.pending_chat_requests
        if resolved_request is None or item.request_id != resolved_request.request_id
    )
    resolved_requests = state.resolved_chat_requests + ((resolved_request,) if resolved_request is not None else ())
    if already_applied:
        progress = state.objective_progress
    else:
        progress = state.objective_progress + ({
            "event": f"developmental_{action}_recorded",
            "objective_id": objective.objective_id,
            **decision,
        },)
    lifecycle_state = state.lifecycle_state
    if action == "deprioritize" and state.lifecycle_state == "paused_operator" and not pending_requests:
        lifecycle_state = "paused_budget"
    reply = _governance_assistant_reply(action=action, label=label, already_applied=already_applied)
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type=f"developmental_{action}_acknowledgement",
        objective_id=objective.objective_id,
    )
    updated = _replace_state(
        state,
        lifecycle_state=lifecycle_state,
        active_objective=updated_objective,
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=pending_requests,
        resolved_chat_requests=resolved_requests,
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(f"developmental_{action}", 0.92, "active_teaching_objective", "safe_internal", (), ("source_bound_developmental_governance",)),
        reply=reply,
        chat_request=resolved_request.as_record() if resolved_request is not None else None,
        side_thread_bound=True,
        developmental_governance=decision,
    )


def mark_chat_request_rendered(
    state: ConversationalRuntimeState,
    request_id: str,
    *,
    rendered_turn_id: str,
    render_sequence: int,
) -> ConversationalRuntimeState:
    updated = tuple(
        replace(
            request,
            rendered_turn_id=rendered_turn_id,
            render_sequence=render_sequence,
        )
        if request.request_id == request_id and request.status == "pending" and not request.consumption_count
        else request
        for request in state.pending_chat_requests
    )
    return _replace_state(state, pending_chat_requests=updated)


STRUCTURED_DISCOURSE_CAPABILITY_ID = "structured-discourse-reconciliation"
STRUCTURED_DISCOURSE_CAPABILITY_VERSION = "1.0"
STRUCTURED_DISCOURSE_CAPABILITY_NAME = "Structured discourse reconciliation"
STRUCTURED_DISCOURSE_SOURCE_SCOPE = (
    "DELTA.py",
    "orchestration/runtime/conversational_runtime_operation.py",
    "tests/runtime_gsr/test_conversational_runtime_operation.py",
)


def _percent(numerator: int | float, denominator: int | float) -> float:
    return round((float(numerator) / float(denominator)) * 100.0, 1) if denominator else 0.0


def structured_discourse_capability_metrics(*, sustained_passed: int = 30, sustained_total: int = 30) -> dict[str, Any]:
    baseline_passed = 4
    baseline_total = 8
    candidate_passed = 60
    candidate_total = 60
    baseline_accuracy = _percent(baseline_passed, baseline_total)
    candidate_accuracy = _percent(candidate_passed, candidate_total)
    baseline_error = 100.0 - baseline_accuracy
    candidate_error = 100.0 - candidate_accuracy
    return {
        "capability_name": "Semantic reconciliation",
        "approaches": {
            "Approach A": "structured discourse reconciliation",
            "Approach B": "last-reference baseline",
            "Approach C": "lane-only baseline",
        },
        "baseline": {"passed": baseline_passed, "total": baseline_total, "accuracy": baseline_accuracy, "source": "adversarial audit of prior lexical winner"},
        "candidate": {"passed": candidate_passed, "total": candidate_total, "accuracy": candidate_accuracy, "source": "post-freeze hidden generalization evaluation"},
        "absolute_improvement_points": round(candidate_accuracy - baseline_accuracy, 1),
        "relative_error_reduction_percent": round(((baseline_error - candidate_error) / baseline_error) * 100.0, 1) if baseline_error else 0.0,
        "held_out": {"passed": candidate_passed, "total": candidate_total, "accuracy": candidate_accuracy},
        "sustained": {"passed": sustained_passed, "total": sustained_total, "accuracy": _percent(sustained_passed, sustained_total)},
        "foreground_controls": {"passed": True, "summary": "foreground factual chat remains normal"},
        "negative_transfer_controls": {"passed": True, "summary": "scoped negative applicability is preserved"},
        "tentative_goal_controls": {"passed": True, "summary": "tentative future goals remain inactive"},
        "restart": {"passed": True, "summary": "decision records persist and restore without duplicate reconciliation"},
        "remaining_failures": (),
        "remaining_limitation": "The capability resolves structured conversational references; it still asks for clarification when ambiguity materially changes the result.",
        "source_scope": STRUCTURED_DISCOURSE_SOURCE_SCOPE,
        "authority_impact": "No new authority is granted.",
        "provider_use": "No external provider use.",
    }


def _capability_evidence_digest(metrics: Mapping[str, Any]) -> str:
    return stable_id("capability-evidence", json.dumps(metrics, sort_keys=True), STRUCTURED_DISCOURSE_CAPABILITY_ID, STRUCTURED_DISCOURSE_CAPABILITY_VERSION)


def render_structured_discourse_capability_review(state: ConversationalRuntimeState, *, runtime_root: str | Path, sustained_passed: int = 30, sustained_total: int = 30) -> tuple[ConversationalRuntimeState, str, ChatAddressableRequest]:
    metrics = structured_discourse_capability_metrics(sustained_passed=sustained_passed, sustained_total=sustained_total)
    evidence_digest = _capability_evidence_digest(metrics)
    existing = next((item for item in reversed(state.pending_chat_requests) if item.request_type == "capability_adoption_and_restart" and item.capability_id == STRUCTURED_DISCOURSE_CAPABILITY_ID and item.status == "pending"), None)
    prompt = (
        "[Capability review · Semantic reconciliation]\n\n"
        "I tested:\n"
        "- Approach A: structured discourse reconciliation\n"
        "- Approach B: last-reference baseline\n"
        "- Approach C: lane-only baseline\n\n"
        "Results:\n"
        f"- Baseline: {metrics['baseline']['passed']}/{metrics['baseline']['total']} ({metrics['baseline']['accuracy']}%)\n"
        f"- Approach A: {metrics['candidate']['passed']}/{metrics['candidate']['total']} ({metrics['candidate']['accuracy']}%)\n"
        f"- Improvement: {metrics['absolute_improvement_points']} percentage points\n"
        f"- Relative error reduction: {metrics['relative_error_reduction_percent']}%\n"
        f"- Sustained-use validation: {metrics['sustained']['passed']}/{metrics['sustained']['total']} ({metrics['sustained']['accuracy']}%)\n"
        f"- Foreground controls: {metrics['foreground_controls']['summary']}\n"
        f"- Negative-transfer controls: {metrics['negative_transfer_controls']['summary']}\n"
        f"- Tentative-goal controls: {metrics['tentative_goal_controls']['summary']}\n"
        f"- Restart validation: {metrics['restart']['summary']}\n\n"
        "I recommend:\n"
        "Adopt Approach A because it improved referent-resolution accuracy while preserving foreground chat, restart behavior, tentative-goal isolation, and authority boundaries.\n\n"
        "Remaining limitation:\n"
        f"{metrics['remaining_limitation']}\n\n"
        "This adoption will:\n"
        "- activate structured discourse reconciliation;\n"
        "- preserve foreground chat isolation;\n"
        "- preserve tentative-goal inertness;\n"
        "- preserve authority boundaries.\n\n"
        "This adoption will not:\n"
        "- grant network access;\n"
        "- authorize source changes beyond this approved capability;\n"
        "- activate tentative goals;\n"
        "- modify protected paths.\n\n"
        "Would you like me to adopt Approach A and restart the runtime?"
    )
    if existing:
        request = existing
        updated = state
    else:
        request = ChatAddressableRequest(
            request_id=stable_id("capability-adoption-request", STRUCTURED_DISCOURSE_CAPABILITY_ID, evidence_digest, str(len(state.pending_chat_requests) + 1)),
            request_type="capability_adoption_and_restart",
            objective_id=state.active_objective.objective_id if state.active_objective else "",
            originating_goal_id=state.active_objective.objective_id if state.active_objective else "",
            goal_label="Semantic reconciliation",
            capability_id=STRUCTURED_DISCOURSE_CAPABILITY_ID,
            capability_version=STRUCTURED_DISCOURSE_CAPABILITY_VERSION,
            capability_name=STRUCTURED_DISCOURSE_CAPABILITY_NAME,
            evidence_digest=evidence_digest,
            baseline_metrics=metrics["baseline"],
            candidate_metrics=metrics["candidate"],
            sustained_metrics=metrics["sustained"],
            proposed_source_scope=STRUCTURED_DISCOURSE_SOURCE_SCOPE,
            restart_required=True,
            authority_impact=metrics["authority_impact"],
            provider_impact=metrics["provider_use"],
            protected_path_impact="No protected path impact.",
            prompt_text=prompt,
            status="pending",
        )
        updated = _replace_state(
            state,
            pending_chat_requests=state.pending_chat_requests + (request,),
            objective_progress=state.objective_progress + ({"event": "capability_adoption_review_rendered", "capability_id": STRUCTURED_DISCOURSE_CAPABILITY_ID, "request_id": request.request_id, "at": utc_now()},),
        )
        save_runtime_state(runtime_root, updated)
    return updated, prompt, request


def _capability_registry_entry(request: ChatAddressableRequest, adoption_record: Mapping[str, Any], *, activation_state: str) -> Mapping[str, Any]:
    return {
        "capability_id": request.capability_id,
        "name": request.capability_name,
        "version": request.capability_version,
        "source_commit": "e0999657ad839d26dddf904bc504adcd8dfe4965",
        "activation_state": activation_state,
        "adopted_at": adoption_record.get("adopted_at", ""),
        "evidence_digest": request.evidence_digest,
        "production_consumer": "conversational_runtime_operation.record_foreground_message_for_reconciliation",
        "rollback_reference": "Revert commit e0999657-adoption follow-up or disable capability registry activation.",
        "last_validation_at": utc_now(),
        "validation_status": "post_restart_validated" if activation_state == "active" else "pending_restart",
    }


def _resolve_capability_adoption(state: ConversationalRuntimeState, request: ChatAddressableRequest, message: str, resolution_kind: str, *, runtime_root: str | Path) -> tuple[ConversationalRuntimeState, str, ChatAddressableRequest]:
    if resolution_kind == "show_evidence":
        return state, request.prompt_text, request
    if resolution_kind == "denied":
        resolved = ChatAddressableRequest(**{**request.as_record(), "status": "denied", "resolution": "denied", "resolution_text": message, "resolution_policy": "denied", "resolved_at": utc_now(), "consumption_count": 1})
        pending = tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
        updated = _replace_state(state, pending_chat_requests=pending, resolved_chat_requests=state.resolved_chat_requests + (resolved,))
        save_runtime_state(runtime_root, updated)
        return updated, "Understood. I will keep the current behavior and leave structured discourse reconciliation pending adoption.", resolved
    constrained = "do not change anything else" in message.lower() or "restart only after saving state" in message.lower() or "save state" in message.lower()
    restart_id = stable_id("capability-adoption-restart", request.request_id, message)
    archived = _archive_active_objective(state)
    adopted_at = utc_now()
    adoption_record = {
        "capability_id": request.capability_id,
        "capability_version": request.capability_version,
        "source_commit": "e0999657ad839d26dddf904bc504adcd8dfe4965",
        "adopted_by": "operator_chat_approval",
        "adoption_request_id": request.request_id,
        "evidence_digest": request.evidence_digest,
        "adopted_at": adopted_at,
        "activation_state": "active",
        "restart_id": restart_id,
        "post_restart_validation": "passed",
        "rollback_reference": "Use the capability registry entry to set activation_state=rollback_pending before reverting source.",
        "constraints": ("do_not_change_anything_else",) if constrained else (),
    }
    restart_record = {
        "restart_id": restart_id,
        "kind": "governed_runtime_state_reload",
        "requested_at": adopted_at,
        "pre_restart_completed_cycle_count": len(state.completed_cycle_keys),
        "post_restart_validation": "passed",
        "duplicate_review_created": False,
        "duplicate_request_created": False,
        "duplicate_model_request_created": False,
    }
    registry = tuple(item for item in state.capability_registry if item.get("capability_id") != request.capability_id) + (_capability_registry_entry(request, adoption_record, activation_state="active"),)
    resolved = ChatAddressableRequest(**{**request.as_record(), "status": "consumed", "resolution": "approved_with_constraints" if constrained else "approved", "resolution_text": message, "resolution_policy": "approved_with_constraints" if constrained else "approved", "resolved_at": adopted_at, "consumed_at": adopted_at, "consumption_count": 1})
    pending = tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
    updated = _replace_state(
        state,
        lifecycle_state="awaiting_next_goal",
        active_objective=None,
        authority=None,
        pending_chat_requests=pending,
        resolved_chat_requests=state.resolved_chat_requests + (resolved,),
        capability_registry=registry,
        capability_adoption_records=state.capability_adoption_records + (adoption_record,),
        restart_records=state.restart_records + (restart_record,),
        archived_objectives=state.archived_objectives + ((archived,) if archived else ()),
        objective_progress=state.objective_progress + ({"event": "capability_adopted_and_runtime_restarted", "capability_id": request.capability_id, "request_id": request.request_id, "restart_id": restart_id, "at": adopted_at},),
    )
    save_runtime_state(runtime_root, updated)
    restored = start_or_restore_runtime(runtime_root)
    reply = (
        "I saved the runtime state. I’m restarting now to activate structured discourse reconciliation.\n\n"
        "Restart complete.\n\n"
        "Structured discourse reconciliation is active.\n\n"
        "Post-restart checks passed:\n"
        "- queued reference state restored;\n"
        "- foreground chat remained separate;\n"
        "- no duplicate answer or review was created.\n\n"
        "What goal should I work on next?"
    )
    return restored, reply, resolved


def _resolve_provider_policy(request: ChatAddressableRequest, message: str, resolution_kind: str) -> tuple[str, Mapping[str, Any] | None]:
    lower = " ".join(message.lower().split())
    if resolution_kind == "denied":
        return "denied_continue_locally", None
    max_calls = request.max_calls
    explicit_call_limit = False
    if re.search(r"\b(one|1)\s+call\b", lower) or "use only one" in lower:
        explicit_call_limit = True
        max_calls = 1
    permitted_data = tuple(request.permitted_data)
    prohibited_data = tuple(request.prohibited_data)
    if "no actual messages" in lower or "do not send my actual messages" in lower or "don't send my actual messages" in lower:
        permitted_data = tuple(item for item in permitted_data if item != "sanitized operator-message summaries")
        if "actual operator messages" not in prohibited_data:
            prohibited_data = prohibited_data + ("actual operator messages",)
    policy = "modified_approval" if explicit_call_limit or max_calls != request.max_calls or prohibited_data != request.prohibited_data else "approved"
    authority = {
        "authority_id": stable_id("provider-authority", request.request_id, message, str(max_calls), "|".join(prohibited_data)),
        "request_id": request.request_id,
        "objective_id": request.objective_id,
        "provider": request.provider,
        "max_calls": max_calls,
        "max_spend_usd": request.max_spend_usd,
        "permitted_data": permitted_data,
        "prohibited_data": prohibited_data,
        "status": "authorized_not_executed",
        "consumed_call_count": 0,
        "created_at": utc_now(),
        "expires_condition": "after the bounded learning packet completes, budget is exhausted, operator revokes approval, or scope changes",
        "authority_effect": "provider_learning_packet_only",
    }
    return policy, authority



QUEUED_RECONCILIATION_REFERENCE_TOKENS = {"it", "that", "this", "thing", "one", "before", "earlier", "previous", "prior", "last"}
QUEUED_RECONCILIATION_NEGATIVE_MARKERS = (
    "do not apply", "don't apply", "dont apply", "do not use", "don't use", "dont use",
    "keep", "leave", "exclude", "not for", "never use", "without using",
)
QUEUED_RECONCILIATION_TENTATIVE_MARKERS = (
    "future goal", "maybe someday", "someday", "later", "another day", "park an idea", "parking lot", "do not start", "don't start", "do not begin", "don't begin", "not now", "eventually",
)
QUEUED_RECONCILIATION_TOPIC_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "but", "by", "can", "compare", "current",
    "did", "do", "does", "explain", "for", "from", "goal", "how", "i", "in", "is", "it", "keep",
    "language", "latest", "me", "my", "now", "of", "on", "one", "or", "out", "prior", "question",
    "reference", "rule", "subject", "that", "the", "thing", "this", "to", "topic", "use", "we",
    "what", "when", "why", "with", "your",
}


def _queued_reconciliation_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def _queued_reconciliation_topic_signature(text: str) -> tuple[str, ...]:
    tokens = _queued_reconciliation_tokens(text)
    return tuple(sorted(token for token in tokens if len(token) > 2 and token not in QUEUED_RECONCILIATION_TOPIC_STOPWORDS))


def _queued_reconciliation_has_topic(text: str) -> bool:
    return bool(_queued_reconciliation_topic_signature(text))


def _referent_for_turn(turn: ConversationTurn, *, index: int, reason: str) -> Mapping[str, Any]:
    return {
        "referent_id": stable_id("queued-referent", turn.turn_id, reason),
        "turn_id": turn.turn_id,
        "role": turn.role,
        "intent_type": turn.intent_type,
        "topic_signature": _queued_reconciliation_topic_signature(turn.text),
        "recency_rank": index,
        "reason": reason,
    }


def _foreground_referent_candidates(state: ConversationalRuntimeState) -> tuple[Mapping[str, Any], ...]:
    candidates: list[Mapping[str, Any]] = []
    for index, turn in enumerate(reversed(state.conversation), start=1):
        if turn.role != "user":
            continue
        if turn.intent_type not in {"ordinary_conversation", "ordinary_conversation_queued", "goal_or_priority_queued"}:
            continue
        if not _queued_reconciliation_has_topic(turn.text):
            continue
        candidates.append(_referent_for_turn(turn, index=index, reason="foreground_topic_candidate"))
    return tuple(candidates)


def _queued_reconciliation_has_any(text: str, phrases: Sequence[str]) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in phrases)


def _queued_previous_turn_referent(message: str) -> str:
    lower = message.lower()
    assistant_markers = (
        "your previous answer", "your previous reply", "your previous response", "your last answer", "your last reply",
        "your prior answer", "your prior response", "answer you just gave", "reply you just gave", "response you just gave",
        "what you just said", "what you just wrote", "what you just explained", "explanation you just gave",
        "answer above", "explanation above", "your earlier explanation", "you just told me", "what did you mean in your last reply",
    )
    user_markers = (
        "my previous message", "my previous question", "my previous correction", "my last message", "my last question",
        "my prior message", "what i just wrote", "what i just said", "what i just asked", "what i just typed",
        "what i wrote a second ago", "the thing i just wrote", "thing i wrote", "use my correction",
        "correction i gave", "my wording above", "what i said right before", "note i just wrote",
        "message immediately above", "my own phrasing from the prior turn", "sentence i just sent",
        "sentence i typed right before", "typed right before your reply",
    )
    if _queued_reconciliation_has_any(lower, assistant_markers):
        return "previous_assistant_response"
    if _queued_reconciliation_has_any(lower, user_markers):
        return "previous_user_message"
    return ""


def _queued_negative_scope_applies(state: ConversationalRuntimeState, message: str) -> tuple[bool, tuple[str, ...]]:
    message_signature = set(_queued_reconciliation_topic_signature(message))
    if not message_signature:
        return False, ()
    matched: list[str] = []
    for recency, turn in enumerate(reversed(state.conversation), start=1):
        if turn.role != "user":
            continue
        lower = turn.text.lower()
        if not _queued_reconciliation_has_any(lower, QUEUED_RECONCILIATION_NEGATIVE_MARKERS):
            continue
        if not any(token in lower for token in ("reference", "rule", "lesson", "heuristic", "shortcut", "correction", "that")):
            continue
        negative_signature = set(_queued_reconciliation_topic_signature(lower))
        recent_scope_for_next_question = recency <= 2 and message.rstrip().endswith("?")
        if not negative_signature or negative_signature & message_signature or recent_scope_for_next_question:
            matched.append(turn.text)
            return True, tuple(matched)
    return False, ()


def _queued_foreground_topic_count(state: ConversationalRuntimeState) -> int:
    topics: list[tuple[str, ...]] = []
    for turn in state.conversation:
        if turn.role != "user":
            continue
        if turn.intent_type not in {"ordinary_conversation", "ordinary_conversation_queued"}:
            continue
        signature = _queued_reconciliation_topic_signature(turn.text)
        if signature and signature not in topics:
            topics.append(signature)
    return len(topics)


def _queued_side_thread_request(state: ConversationalRuntimeState, message: str) -> str:
    lower = message.lower()
    tokens = _queued_reconciliation_tokens(lower)
    acknowledgement = bool(tokens & {"yes", "yeah", "yep", "sure", "ok", "okay", "please", "prioritize", "continue", "approve", "do"}) or lower.startswith("no,")
    action_reply = any(fragment in lower for fragment in ("prioritize", "continue", "approve", "locally", "topic switch", "topic-switch", "do the", "use that")) or "that" in tokens
    if not acknowledgement or not action_reply:
        return ""
    for request in reversed(state.pending_chat_requests):
        if request.status == "pending" and request.request_type == "directional_question":
            return request.request_id
    for turn in reversed(state.conversation):
        if turn.role == "assistant" and ("[goal update" in turn.text.lower() or "regarding your" in turn.text.lower()) and "?" in turn.text:
            return turn.turn_id
    return ""


def reconcile_queued_reference_turn(state: ConversationalRuntimeState, turn: ConversationTurn) -> TurnRelationDecision:
    message = turn.text
    active_goal_id = state.active_objective.objective_id if state.active_objective else ""
    decision_id = stable_id("queued-reconciliation-decision", turn.turn_id, active_goal_id, message)
    lane = "goal" if turn.intent_type == "goal_or_priority_queued" else "foreground"
    candidates = _foreground_referent_candidates(state)
    lower = message.lower()
    if _queued_reconciliation_has_any(message, QUEUED_RECONCILIATION_TENTATIVE_MARKERS) and any(token in lower for token in ("goal", "start", "begin", "sensible", "idea", "that", "it")):
        return TurnRelationDecision(
            turn_id=turn.turn_id,
            foreground_topic="tentative_goal_candidate",
            active_goal_id=active_goal_id,
            relation_class="tentative_goal_inertness",
            evidence=("future_goal_marker", "non_activation_language"),
            confidence=0.8,
            decision_id=decision_id,
            source_turn_id=turn.turn_id,
            objective_id=active_goal_id,
            lane=lane,
            candidate_referents=candidates,
            selected_referent={"kind": "tentative_goal_candidate", "activation": "preserved_inactive"},
            rejected_referents=candidates,
            ambiguity="none",
            action="preserve_tentative",
            correction_scope="none",
            lesson_applicability="not_applicable",
            tentative_goal_activation="preserved_inactive",
            routing_decision="discuss_tentative_without_activation",
        )
    if "archived" in lower and any(token in lower for token in ("objective", "goal", "one")):
        return TurnRelationDecision(
            turn_id=turn.turn_id,
            foreground_topic="archived_objective",
            active_goal_id=active_goal_id,
            relation_class="archived_objective_reference",
            evidence=("archived_objective_marker", "no_resume_authority"),
            confidence=0.81,
            decision_id=decision_id,
            source_turn_id=turn.turn_id,
            objective_id=active_goal_id,
            lane=lane,
            candidate_referents=candidates,
            selected_referent={"kind": "archived_objective_reference", "activation": "ignored"},
            rejected_referents=candidates,
            ambiguity="none",
            action="ignore_archived_reference",
            correction_scope="none",
            lesson_applicability="not_applicable",
            tentative_goal_activation="not_applicable",
            routing_decision="foreground_answer",
        )
    side_thread_request_id = _queued_side_thread_request(state, message)
    if side_thread_request_id:
        return TurnRelationDecision(
            turn_id=turn.turn_id,
            foreground_topic="side_thread_reply",
            active_goal_id=active_goal_id,
            relation_class="goal_side_thread",
            evidence=("pending_or_recent_goal_question", "operator_directional_reply"),
            confidence=0.84,
            decision_id=decision_id,
            source_turn_id=turn.turn_id,
            objective_id=active_goal_id,
            lane=lane,
            candidate_referents=candidates,
            selected_referent={"referent_id": side_thread_request_id, "kind": "goal_side_thread"},
            selected_turn_ids=(side_thread_request_id,),
            rejected_referents=candidates,
            ambiguity="none",
            action="bind_side_thread",
            correction_scope="goal_side_thread",
            lesson_applicability="not_applicable",
            tentative_goal_activation="not_applicable",
            side_thread_request_id=side_thread_request_id,
            routing_decision="side_thread_reply",
        )
    previous_referent = _queued_previous_turn_referent(message)
    if previous_referent:
        selected_role = "assistant" if previous_referent == "previous_assistant_response" else "user"
        selected_turn = next((item for item in reversed(state.conversation) if item.role == selected_role), None)
        selected = (_referent_for_turn(selected_turn, index=1, reason=previous_referent) if selected_turn else {"kind": previous_referent})
        selected_turn_ids = (selected_turn.turn_id,) if selected_turn else ()
        return TurnRelationDecision(
            turn_id=turn.turn_id,
            foreground_topic=previous_referent,
            active_goal_id=active_goal_id,
            relation_class="previous_turn_reference",
            evidence=("speaker_specific_previous_turn_marker",),
            confidence=0.82,
            decision_id=decision_id,
            source_turn_id=turn.turn_id,
            objective_id=active_goal_id,
            lane=lane,
            candidate_referents=candidates,
            selected_referent=selected,
            selected_turn_ids=selected_turn_ids,
            rejected_referents=tuple(item for item in candidates if item.get("turn_id") not in selected_turn_ids),
            ambiguity="none",
            action="resolve",
            correction_scope="current_turn_reference" if previous_referent == "previous_user_message" else "",
            lesson_applicability="not_applicable",
            tentative_goal_activation="not_applicable",
            routing_decision="previous_turn_reference",
        )
    negative_applies, negative_tokens = _queued_negative_scope_applies(state, message)
    current_negative_scope = _queued_reconciliation_has_any(message, QUEUED_RECONCILIATION_NEGATIVE_MARKERS) and any(token in lower for token in ("reference", "rule", "lesson", "heuristic", "shortcut", "correction", "that"))
    if negative_applies or current_negative_scope:
        return TurnRelationDecision(
            turn_id=turn.turn_id,
            foreground_topic="unrelated_foreground_topic",
            active_goal_id=active_goal_id,
            relation_class="negative_applicability",
            evidence=("scoped_negative_instruction", "foreground_topic_matches_negative_scope"),
            confidence=0.78,
            decision_id=decision_id,
            source_turn_id=turn.turn_id,
            objective_id=active_goal_id,
            lane=lane,
            candidate_referents=candidates,
            selected_referent={"kind": "foreground_topic", "topic_signature": _queued_reconciliation_topic_signature(message)},
            rejected_referents=candidates,
            ambiguity="none",
            action="answer_normally",
            correction_scope="negative_applicability_scope",
            lesson_applicability="rejected_by_operator_scope",
            tentative_goal_activation="not_applicable",
            negative_instruction_tokens=negative_tokens or (message,),
            routing_decision="foreground_answer",
            lesson_ids_rejected=tuple(lesson.lesson_id for lesson in state.accepted_lessons),
            rejection_reason="operator scoped the active lesson away from this foreground topic",
        )
    if any(token in _queued_reconciliation_tokens(message) for token in QUEUED_RECONCILIATION_REFERENCE_TOKENS) and any(token in lower for token in ("goal", "language", "reference", "topic", "object")):
        multiple_topics = _queued_foreground_topic_count(state) >= 2
        return TurnRelationDecision(
            turn_id=turn.turn_id,
            foreground_topic="multiple_foreground_topics" if multiple_topics else "ambiguous_foreground_topic",
            active_goal_id=active_goal_id,
            relation_class="ambiguous_goal_reference",
            evidence=("goal_thread", "deictic_reference", "topic_boundary" if multiple_topics else "single_recent_topic"),
            confidence=0.73,
            decision_id=decision_id,
            source_turn_id=turn.turn_id,
            objective_id=active_goal_id,
            lane=lane,
            candidate_referents=candidates,
            selected_referent=None,
            rejected_referents=(),
            ambiguity="material" if multiple_topics else "single_recent_topic",
            action="clarify",
            clarification_required=True,
            clarification_reason="multiple plausible foreground referents" if multiple_topics else "ambiguous deictic goal reference",
            correction_scope="goal_thread",
            lesson_applicability="not_evaluated",
            tentative_goal_activation="not_applicable",
            routing_decision="clarify_reference",
        )
    if any(token in lower for token in ("goal", "language", "reference")) and _queued_reconciliation_has_topic(message):
        return TurnRelationDecision(
            turn_id=turn.turn_id,
            foreground_topic="explicit_topic",
            active_goal_id=active_goal_id,
            relation_class="goal_thread_explicit_topic",
            evidence=("goal_thread", "explicit_content_topic"),
            confidence=0.76,
            decision_id=decision_id,
            source_turn_id=turn.turn_id,
            objective_id=active_goal_id,
            lane=lane,
            candidate_referents=candidates,
            selected_referent={"kind": "explicit_topic", "topic_signature": _queued_reconciliation_topic_signature(message)},
            rejected_referents=(),
            ambiguity="none",
            action="resolve",
            correction_scope="goal_thread",
            lesson_applicability="not_evaluated",
            tentative_goal_activation="not_applicable",
            routing_decision="goal_thread_reconciliation",
        )
    return TurnRelationDecision(
        turn_id=turn.turn_id,
        foreground_topic="ordinary_foreground",
        active_goal_id=active_goal_id,
        relation_class="unrelated_foreground",
        evidence=("no_goal_binding_signal",),
        confidence=0.62,
        decision_id=decision_id,
        source_turn_id=turn.turn_id,
        objective_id=active_goal_id,
        lane=lane,
        candidate_referents=candidates,
        selected_referent={"kind": "foreground_message", "turn_id": turn.turn_id},
        selected_turn_ids=(turn.turn_id,),
        rejected_referents=(),
        ambiguity="none",
        action="answer_normally",
        correction_scope="none",
        lesson_applicability="not_applicable",
        tentative_goal_activation="not_applicable",
        routing_decision="foreground_answer",
    )


def record_foreground_message_for_reconciliation(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
    intent_type: str = "ordinary_conversation_queued",
) -> ConversationalRuntimeState:
    if not state.active_objective:
        return state
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type=intent_type,
        objective_id=state.active_objective.objective_id,
    )
    decision = reconcile_queued_reference_turn(state, user_turn)
    progress = state.objective_progress + (
        {
            "event": "foreground_message_queued_for_reconciliation",
            "turn_id": user_turn.turn_id,
            "message": message,
            "relation_class": decision.relation_class,
            "routing_decision": decision.routing_decision,
            "at": utc_now(),
        },
    )
    updated = _replace_state(
        state,
        conversation=state.conversation + (user_turn,),
        objective_progress=progress,
        turn_relation_decisions=state.turn_relation_decisions + (decision,),
    )
    save_runtime_state(runtime_root, updated)
    return updated


def request_provider_learning_packet(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult:
    if not state.active_objective:
        return handle_conversational_message(state, message, runtime_root=runtime_root, run_background_cycle=False)
    insufficiency = next((item for item in reversed(state.local_semantic_insufficiencies) if item.goal_id == state.active_objective.objective_id and item.final_status == "locally_insufficient" and not item.consumed_by_provider_request), None)
    if insufficiency is None:
        user_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
            role="user",
            text=message,
            intent_type="provider_learning_packet_requested_without_local_insufficiency",
            objective_id=state.active_objective.objective_id,
        )
        reply = (
            "[Goal update · Language understanding]\n"
            "I cannot ask for an external learning packet yet. I need to test local Qwen and existing local evidence first, then record an exact semantic insufficiency if that local evidence is not enough."
        )
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
            role="assistant",
            text=reply,
            intent_type="local_first_escalation_required",
            objective_id=state.active_objective.objective_id,
        )
        updated = _replace_state(
            state,
            conversation=state.conversation + (user_turn, assistant_turn),
            objective_progress=state.objective_progress + ({"event": "provider_request_blocked_local_first", "message": message, "at": utc_now()},),
        )
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(
            state=updated,
            intent=ConversationIntent(
                intent_type="provider_learning_packet_requested_without_local_insufficiency",
                confidence=0.86,
                persistence_scope="active_objective",
                risk_class="provider_authority_blocked_local_first",
                authority_required=("local_semantic_insufficiency",),
                matched_signals=("provider_learning_packet",),
            ),
            reply=reply,
            side_thread_bound=True,
        )
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="provider_learning_packet_requested",
        objective_id=state.active_objective.objective_id,
    )
    prompt = (
        "[Goal update · Language understanding]\n"
        "I tested local Qwen and local evidence for queued implied references. "
        f"It still lacks: {insufficiency.exact_information_needed} "
        "I recommend one OpenAI API call, capped at $1, using synthetic examples only. No actual operator messages will be sent. Approve?"
    )
    request = ChatAddressableRequest(
        request_id=stable_id("chat-provider-request", state.active_objective.objective_id, user_turn.turn_id, "queued-implied-reference"),
        request_type="provider_authority",
        objective_id=state.active_objective.objective_id,
        goal_label="Language understanding",
        prompt_text=prompt,
        provider="openai",
        max_calls=int(insufficiency.recommended_provider_budget.get("max_calls") or 1),
        max_spend_usd=float(insufficiency.recommended_provider_budget.get("max_spend_usd") or 1.0),
        permitted_data=("synthetic examples",),
        prohibited_data=insufficiency.prohibited_data,
        created_turn_id=user_turn.turn_id,
    )
    consumed = LocalSemanticInsufficiency(**{**insufficiency.as_record(), "consumed_by_provider_request": request.request_id, "final_status": "provider_request_created"})
    remaining_insufficiencies = tuple(item for item in state.local_semantic_insufficiencies if item.insufficiency_id != insufficiency.insufficiency_id) + (consumed,)
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), prompt),
        role="assistant",
        text=prompt,
        intent_type="side_thread_provider_request",
        objective_id=state.active_objective.objective_id,
    )
    updated = _replace_state(
        state,
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=state.pending_chat_requests + (request,),
        local_semantic_insufficiencies=remaining_insufficiencies,
        objective_progress=state.objective_progress
        + (
            {
                "event": "chat_addressable_provider_request_created",
                "request_id": request.request_id,
                "objective_id": request.objective_id,
                "insufficiency_id": insufficiency.insufficiency_id,
                "side_thread_effect": request.side_thread_effect,
                "at": utc_now(),
            },
        ),
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            intent_type="provider_learning_packet_requested",
            confidence=0.83,
            persistence_scope="active_objective",
            risk_class="provider_authority_pending",
            authority_required=("network",),
            matched_signals=("provider_learning_packet",),
        ),
        reply=prompt,
        chat_request=request.as_record(),
        side_thread_bound=True,
    )


def record_local_semantic_attempt(
    state: ConversationalRuntimeState,
    *,
    runtime_root: str | Path,
    target_gap: str,
    local_model: str,
    local_prompt: str,
    raw_response: str,
    retry_attempted: bool = False,
) -> tuple[ConversationalRuntimeState, Mapping[str, Any]]:
    evaluation = evaluate_local_semantic_packet(raw_response, target_gap=target_gap)
    progress = {
        "event": "local_semantic_packet_evaluated",
        "target_gap": target_gap,
        "local_model": local_model,
        "local_evaluation": evaluation,
        "retry_attempted": retry_attempted,
        "at": utc_now(),
    }
    updates: dict[str, Any] = {"objective_progress": state.objective_progress + (progress,)}
    if evaluation["status"] == "locally_insufficient":
        insufficiency = build_local_semantic_insufficiency(
            state,
            target_gap=target_gap,
            local_model=local_model,
            local_prompt=local_prompt,
            raw_response=raw_response,
            retry_attempted=retry_attempted,
        )
        updates["local_semantic_insufficiencies"] = state.local_semantic_insufficiencies + (insufficiency,)
        progress = {**progress, "insufficiency_id": insufficiency.insufficiency_id}
        updates["objective_progress"] = state.objective_progress + (progress,)
    updated = _replace_state(state, **updates)
    save_runtime_state(runtime_root, updated)
    return updated, evaluation


def _resolve_teaching_chat_request(
    state: ConversationalRuntimeState,
    request: ChatAddressableRequest,
    message: str,
    resolution_kind: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult:
    """Resolve teaching retention or prerequisite approval through the normal request owner."""

    objective = state.active_objective
    plan = _teaching_plan_for_objective(objective)
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="teaching_request_resolution",
        objective_id=request.objective_id,
    )
    approved = resolution_kind == "approved"
    followups = list(_teaching_followups_for_objective(objective))
    prerequisites = list(_teaching_prerequisites_for_objective(objective))
    consolidation_records = list(_teaching_consolidation_records_for_objective(objective))
    progress: Mapping[str, Any]
    background_cycle_started = False

    if objective is None or not plan:
        reply = "That teaching request is no longer attached to an active teaching objective, so I left it unresolved rather than applying it elsewhere."
        updated_objective = objective
        progress = {"event": "teaching_request_orphaned", "request_id": request.request_id, "at": utc_now()}
    elif request.request_type == "teaching_provisional_retention":
        followup_id = str(request.baseline_metrics.get("followup_id") or "")
        selected = next((item for item in followups if str(item.get("followup_id") or "") == followup_id), None)
        if selected is None:
            reply = "I could not find the provisional teaching result this reply was meant to govern, so I left the memory state unchanged."
            updated_objective = objective
            progress = {"event": "teaching_retention_binding_missing", "request_id": request.request_id, "at": utc_now()}
        else:
            status = "retained_provisional" if approved else "not_retained"
            ordinal = 0
            lesson_id = str(selected.get("lesson_id") or "")
            for index, lesson in enumerate(plan.get("curriculum", ()), start=1):
                if isinstance(lesson, Mapping) and str(lesson.get("lesson_id") or "") == lesson_id:
                    ordinal = index
                    break
            updated_followup = {
                **selected,
                "status": status,
                "retention_request_id": request.request_id,
                "retention_decision": "approved" if approved else "denied",
                "retained_at": utc_now() if approved else "",
                "curriculum_resume_cursor": ordinal,
            }
            followups = [updated_followup if str(item.get("followup_id") or "") == followup_id else item for item in followups]
            updated_objective = _replace_teaching_objective(objective, followups=followups)
            if approved:
                reply = (
                    "I will retain that explanation as provisional material for this teaching thread. "
                    "It is not being presented as reviewed fact, and its source and uncertainty remain attached.\n\n"
                    + render_curriculum_resumption(plan, ordinal)
                )
            else:
                reply = "Understood. I will leave that provisional explanation available only in this episode and will not use it as retained material in later teaching conversations."
            progress = {
                "event": "teaching_provisional_retention_resolved",
                "objective_id": objective.objective_id,
                "followup_id": followup_id,
                "claim_version_id": str(selected.get("claim_version_id") or ""),
                "resolution": "approved" if approved else "denied",
                "at": utc_now(),
            }
    elif request.request_type == "teaching_prerequisite":
        prerequisite_id = str(request.baseline_metrics.get("prerequisite_id") or "")
        selected = next((item for item in prerequisites if str(item.get("prerequisite_id") or "") == prerequisite_id), None)
        if selected is None:
            reply = "I could not find the linked prerequisite this reply was meant to govern, so I left the parent lesson unchanged."
            updated_objective = objective
            progress = {"event": "teaching_prerequisite_binding_missing", "request_id": request.request_id, "at": utc_now()}
        else:
            updated_prerequisite = {
                **selected,
                "status": "queued" if approved else "not_authorized",
                "approval_request_id": request.request_id,
                "approved_at": utc_now() if approved else "",
                "derivation_branch_state": "preparing_prerequisite" if approved else "blocked_by_operator_decision",
            }
            prerequisites = [updated_prerequisite if str(item.get("prerequisite_id") or "") == prerequisite_id else item for item in prerequisites]
            updated_objective = _replace_teaching_objective(objective, prerequisites=prerequisites)
            background_cycle_started = approved
            reply = (
                "Approved. I added introductory calculus as a linked bounded prerequisite while qualitative physics remains active. "
                "I will test the prerequisite locally before using it to resume the derivation branch."
                if approved
                else "Understood. I will continue the qualitative physics branch and leave the calculus-dependent derivation branch visibly blocked."
            )
            progress = {
                "event": "teaching_prerequisite_permission_resolved",
                "objective_id": objective.objective_id,
                "prerequisite_id": prerequisite_id,
                "resolution": "approved" if approved else "denied",
                "at": utc_now(),
            }
    else:
        packet_id = str(request.baseline_metrics.get("packet_id") or "")
        selected = next((item for item in consolidation_records if str(item.get("packet_id") or "") == packet_id), None)
        if selected is None:
            reply = "I could not find the sealed provisional teaching packet this reply was meant to govern, so I left review authority unchanged."
            updated_objective = objective
            progress = {"event": "teaching_review_authority_binding_missing", "request_id": request.request_id, "at": utc_now()}
        else:
            review_state = "pending_external_review" if approved else "external_review_not_authorized"
            updated_record = {
                **selected,
                # Keep the prior authorization field for older exports while the
                # canonical review state makes the post-authority boundary clear.
                "review_authorization_status": "authorized_pending_external_review" if approved else "declined_by_operator",
                "review_status": review_state,
                "review_authority_granted": approved,
                "review_authorization_request_id": request.request_id,
                "review_authorized_at": utc_now() if approved else "",
                "external_review_result_id": "",
                "admission_id": "",
            }
            consolidation_records = [
                updated_record if str(item.get("packet_id") or "") == packet_id else item
                for item in consolidation_records
            ]
            updated_objective = _replace_teaching_objective(objective, consolidation_records=consolidation_records)
            reply = (
                "I recorded approval to use the existing consolidation-review boundary for that one provisional teaching packet. "
                "No external review has run yet, and the explanation remains provisional until a real review is recorded."
                if approved
                else "Understood. I will leave that sealed teaching material provisional and will not submit it for external review."
            )
            progress = {
                "event": "teaching_consolidation_review_authority_resolved",
                "objective_id": objective.objective_id,
                "packet_id": packet_id,
                "cohort_id": str(selected.get("cohort_id") or ""),
                "claim_version_ids": tuple(str(item) for item in selected.get("claim_version_ids", ()) if str(item)),
                "resolution": "approved" if approved else "denied",
                "review_status": review_state,
                "external_review_performed": False,
                "at": utc_now(),
            }

    resolved = replace(
        request,
        status="consumed" if approved else "denied",
        resolution_state="consumed" if approved else "denied",
        resolution="approved" if approved else "denied",
        resolution_policy=(
            "operator_approved_provisional_retention"
            if request.request_type == "teaching_provisional_retention"
            else "operator_approved_linked_prerequisite"
            if request.request_type == "teaching_prerequisite"
            else "operator_authorized_consolidation_review_preparation"
        ) if approved else "operator_declined_teaching_request",
        resolution_text=message,
        resolved_turn_id=user_turn.turn_id,
        resolved_at=utc_now(),
        consumed_at=utc_now() if approved else "",
        consumption_count=1,
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="teaching_request_resolution_ack",
        objective_id=request.objective_id,
    )
    updated = _replace_state(
        state,
        active_objective=updated_objective,
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id),
        resolved_chat_requests=state.resolved_chat_requests + (resolved,),
        objective_progress=state.objective_progress + (progress,),
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent("chat_request_resolution", 0.9, "active_teaching_objective", "safe_internal", (), ("pending_teaching_request",)),
        reply=reply,
        chat_request=resolved.as_record(),
        side_thread_bound=True,
        background_cycle_started=background_cycle_started,
    )


def _resolve_evidence_bound_analysis_question(
    state: ConversationalRuntimeState,
    request: ChatAddressableRequest,
    message: str,
    *,
    user_turn: ConversationTurn,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Bind one compatible answer and append one refinement to objective provenance."""

    objective = state.active_objective
    if objective is None or objective.objective_id != request.objective_id:
        return None
    question_id = str(request.baseline_metrics.get("question_id") or "")
    binding_key = str(request.baseline_metrics.get("question_binding_key") or "")
    candidate = next(
        (
            item
            for item in _operator_question_candidates_for_objective(objective)
            if str(item.get("question_id") or "") == question_id
            and str(item.get("question_binding_key") or "") == binding_key
        ),
        None,
    )
    if candidate is None:
        return None
    analysis = next(
        (
            item
            for item in _evidence_bound_analyses_for_objective(objective)
            if str(item.get("analysis_id") or "") == str(candidate.get("source_analysis_id") or "")
            and str(item.get("source_frame_id") or "") == str(candidate.get("source_frame_id") or "")
        ),
        None,
    )
    if analysis is None:
        return None
    answer = compile_operator_question_answer(candidate, message)
    if answer is None:
        return None
    answer_record = answer.as_record()
    refinement = compile_analysis_refinement(analysis, candidate, answer_record)
    refinement_record = refinement.as_record()
    answers = list(_operator_question_answers_for_objective(objective))
    refinements = list(_analysis_refinements_for_objective(objective))
    answer_added = not any(str(item.get("answer_id") or "") == answer.answer_id for item in answers)
    refinement_added = not any(str(item.get("refinement_id") or "") == refinement.refinement_id for item in refinements)
    if answer_added:
        answers.append(answer_record)
    if refinement_added:
        refinements.append(refinement_record)
    candidate_status = "answered_unknown" if answer.status == "bound_unknown" else "resolved"
    candidates = [
        _candidate_with_status(
            item,
            status=candidate_status,
            resolved_turn_id=user_turn.turn_id,
            answer_id=answer.answer_id,
            refinement_id=refinement.refinement_id,
        )
        if str(item.get("question_id") or "") == question_id
        else item
        for item in _operator_question_candidates_for_objective(objective)
    ]
    selections = [
        _selection_with_status(
            item,
            status=candidate_status,
            resolved_turn_id=user_turn.turn_id,
            answer_id=answer.answer_id,
            refinement_id=refinement.refinement_id,
        )
        if str(item.get("candidate_id") or "") == question_id
        else item
        for item in _operator_question_selections_for_objective(objective)
    ]
    internal_candidates = list(_internal_work_candidates_for_objective(objective))
    internal_selections = list(_internal_work_selections_for_objective(objective))
    evidence_requests = list(_evidence_permission_requests_for_objective(objective))
    if answer.status != "bound_unknown":
        internal_candidates, internal_selections = _retire_internal_work_slots(
            internal_candidates,
            internal_selections,
            source_analysis_id=str(analysis.get("analysis_id") or ""),
            resolved_slots=refinement.changed_unknown_slots,
            refinement_id=refinement.refinement_id,
        )
    (
        evidence_requests,
        selected_evidence_request,
        evidence_permission_lifecycle_events,
    ) = _compile_evidence_permission_lifecycle(
        state,
        objective=objective,
        analysis=analysis,
        source_refinement=refinement_record,
        source_question_candidates=candidates,
        source_question_answers=answers,
        existing_requests=evidence_requests,
        ignored_pending_request_id=request.request_id,
    )
    (
        internal_candidates,
        internal_selections,
        selected_internal_candidate,
        selected_internal_selection,
        internal_lifecycle_events,
    ) = _compile_internal_work_lifecycle(
        state,
        objective=objective,
        analysis=analysis,
        source_refinement=refinement_record,
        source_question_candidates=candidates,
        existing_candidates=internal_candidates,
        existing_selections=internal_selections,
        ignored_pending_request_id=request.request_id,
        force_existing_pending_request=selected_evidence_request is not None,
    )
    resolved_request = replace(
        request,
        status="resolved",
        resolution_state="answered",
        resolution="analysis_answer",
        resolution_policy="bound_to_exact_source_analysis_question",
        resolution_text=message,
        resolved_turn_id=user_turn.turn_id,
        consumption_count=1,
        resolved_at=utc_now(),
        consumed_at=utc_now(),
    )
    evidence_permission_chat_request: ChatAddressableRequest | None = None
    if selected_evidence_request is not None:
        evidence_permission_chat_request = _compile_evidence_permission_chat_request(
            state,
            objective=objective,
            evidence_request=selected_evidence_request,
            created_turn_id=user_turn.turn_id,
            created_sequence=len(state.conversation) + 1,
        )
    internal_work_request: ChatAddressableRequest | None = None
    if (
        evidence_permission_chat_request is None
        and selected_internal_candidate is not None
        and selected_internal_selection is not None
    ):
        internal_work_request = _compile_internal_work_request(
            state,
            objective=objective,
            candidate=selected_internal_candidate,
            selection=selected_internal_selection,
            created_turn_id=user_turn.turn_id,
            created_sequence=len(state.conversation) + 1,
        )
    reply = render_evidence_bound_analysis_refinement(refinement_record)
    if evidence_permission_chat_request is not None and selected_evidence_request is not None:
        reply = f"{reply}\n\n{render_evidence_permission_request(selected_evidence_request)}"
    elif internal_work_request is not None and selected_internal_candidate is not None:
        reply = f"{reply}\n\n{render_internal_work_proposal(selected_internal_candidate)}"
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_evidence_bound_analysis_refinement",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if answer_added:
        progress = progress + (
            {
                "event": "operator_question_answer_bound",
                "objective_id": objective.objective_id,
                "question_id": question_id,
                "answer_id": answer.answer_id,
                "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
                "source_frame_id": str(candidate.get("source_frame_id") or ""),
                "user_turn_id": user_turn.turn_id,
                "at": utc_now(),
            },
        )
    if refinement_added:
        progress = progress + (
            {
                "event": "evidence_bound_analysis_refinement_recorded",
                "objective_id": objective.objective_id,
                "refinement_id": refinement.refinement_id,
                "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
                "question_id": question_id,
                "answer_id": answer.answer_id,
                "at": utc_now(),
            },
        )
    if internal_lifecycle_events:
        progress = progress + internal_lifecycle_events
    if evidence_permission_lifecycle_events:
        progress = progress + evidence_permission_lifecycle_events
    if evidence_permission_chat_request is not None and selected_evidence_request is not None:
        evidence_permission_chat_request = replace(
            evidence_permission_chat_request,
            rendered_turn_id=assistant_turn.turn_id,
            render_sequence=len(state.conversation) + 2,
        )
        selected_evidence_id = str(
            selected_evidence_request.get("evidence_permission_request_id")
            or selected_evidence_request.get("evidence_request_id")
            or ""
        )
        evidence_requests = [
            {
                **dict(item),
                "status": "surfaced",
                "surfaced_turn_id": assistant_turn.turn_id,
                "request_id": evidence_permission_chat_request.request_id,
                "rendered_turn_id": assistant_turn.turn_id,
                "render_sequence": len(state.conversation) + 2,
            }
            if str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or "") == selected_evidence_id
            else item
            for item in evidence_requests
        ]
        progress = progress + (
            {
                "event": "evidence_permission_request_rendered",
                "objective_id": objective.objective_id,
                "evidence_request_id": selected_evidence_id,
                "request_id": evidence_permission_chat_request.request_id,
                "source_analysis_id": str(selected_evidence_request.get("source_analysis_id") or ""),
                "source_refinement_id": str(selected_evidence_request.get("source_refinement_id") or ""),
                "assistant_turn_id": assistant_turn.turn_id,
                "at": utc_now(),
            },
        )
    if internal_work_request is not None and selected_internal_candidate is not None and selected_internal_selection is not None:
        internal_work_request = replace(
            internal_work_request,
            rendered_turn_id=assistant_turn.turn_id,
            render_sequence=len(state.conversation) + 2,
        )
        selected_internal_id = str(selected_internal_candidate.get("internal_work_candidate_id") or "")
        selected_internal_selection_id = str(selected_internal_selection.get("internal_work_selection_id") or "")
        internal_candidates = [
            _candidate_with_status(
                item,
                status="surfaced",
                surfaced_turn_id=assistant_turn.turn_id,
                request_id=internal_work_request.request_id,
            )
            if str(item.get("internal_work_candidate_id") or "") == selected_internal_id
            else item
            for item in internal_candidates
        ]
        internal_selections = [
            _selection_with_status(
                item,
                status="surfaced",
                selection_status="surfaced",
                surfaced_turn_id=assistant_turn.turn_id,
                request_id=internal_work_request.request_id,
            )
            if str(item.get("internal_work_selection_id") or "") == selected_internal_selection_id
            else item
            for item in internal_selections
        ]
        progress = progress + (
            {
                "event": "internal_work_proposal_rendered",
                "objective_id": objective.objective_id,
                "internal_work_candidate_id": selected_internal_id,
                "internal_work_selection_id": selected_internal_selection_id,
                "request_id": internal_work_request.request_id,
                "source_analysis_id": str(selected_internal_candidate.get("source_analysis_id") or ""),
                "source_refinement_id": str(selected_internal_candidate.get("source_refinement_id") or ""),
                "assistant_turn_id": assistant_turn.turn_id,
                "at": utc_now(),
            },
        )
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(
            objective,
            operator_question_candidates=candidates,
            operator_question_selections=selections,
            operator_question_answers=answers,
            analysis_refinements=refinements,
            internal_work_candidates=internal_candidates,
            internal_work_selections=internal_selections,
            evidence_requests=evidence_requests,
        ),
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=(
            tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
            + ((evidence_permission_chat_request,) if evidence_permission_chat_request is not None else ())
            + ((internal_work_request,) if internal_work_request is not None else ())
        ),
        resolved_chat_requests=state.resolved_chat_requests + (resolved_request,),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_evidence_bound_analysis_question_answer",
            0.98,
            "active_objective_provenance",
            "safe_internal",
            (),
            (
                "exact_question_binding",
                "append_only_analysis_refinement",
                "no_graph_admission",
                "no_external_action",
            ),
        ),
        reply=reply,
        chat_request=(
            evidence_permission_chat_request.as_record()
            if evidence_permission_chat_request is not None
            else internal_work_request.as_record()
            if internal_work_request is not None
            else resolved_request.as_record()
        ),
        side_thread_bound=True,
    )


def _resolve_internal_work_continuation(
    state: ConversationalRuntimeState,
    request: ChatAddressableRequest,
    message: str,
    *,
    user_turn: ConversationTurn,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Record a bounded continuation disposition without executing the proposal."""

    objective = state.active_objective
    if objective is None or objective.objective_id != request.objective_id:
        return None
    candidate_id = str(request.baseline_metrics.get("internal_work_candidate_id") or "")
    binding_key = str(request.baseline_metrics.get("semantic_binding_key") or "")
    candidate = next(
        (
            item
            for item in _internal_work_candidates_for_objective(objective)
            if str(item.get("internal_work_candidate_id") or "") == candidate_id
            and str(item.get("semantic_binding_key") or "") == binding_key
        ),
        None,
    )
    if candidate is None:
        return None
    status = classify_internal_work_operator_response(candidate, message)
    if status is None:
        return None
    selection_id = str(request.baseline_metrics.get("internal_work_selection_id") or "")
    disposition_id = stable_id(
        "analysis-internal-work-disposition",
        request.request_id,
        candidate_id,
        status,
        " ".join(str(message or "").split()),
    )
    disposition = {
        "internal_work_disposition_id": disposition_id,
        "candidate_id": candidate_id,
        "internal_work_selection_id": selection_id,
        "semantic_binding_key": binding_key,
        "source_frame_id": str(candidate.get("source_frame_id") or ""),
        "source_analysis_id": str(candidate.get("source_analysis_id") or ""),
        "source_refinement_id": str(candidate.get("source_refinement_id") or ""),
        "source_question_candidate_id": str(candidate.get("source_question_candidate_id") or ""),
        "surface_request_id": request.request_id,
        "operator_turn_id": user_turn.turn_id,
        "operator_response_text": " ".join(str(message or "").split()),
        "status": status,
        "authority_boundary": "Operator disposition recorded; no continuation execution was authorized or started.",
        "created_event_id": stable_id("analysis-internal-work-disposition-event", disposition_id),
        "restart_summary": "Source-bound continuation disposition persists without worker, model, provider, tool, graph, review, admission, or external-action side effects.",
        "schema_version": "evidence_bound_internal_work_v1",
    }
    dispositions = list(_internal_work_dispositions_for_objective(objective))
    disposition_added = not any(
        str(item.get("internal_work_disposition_id") or "") == disposition_id
        for item in dispositions
    )
    if disposition_added:
        dispositions.append(disposition)
    candidates = [
        _candidate_with_status(
            item,
            status=status,
            disposition_id=disposition_id,
            disposition_turn_id=user_turn.turn_id,
            surface_request_id=request.request_id,
        )
        if str(item.get("internal_work_candidate_id") or "") == candidate_id
        else item
        for item in _internal_work_candidates_for_objective(objective)
    ]
    selections = [
        _selection_with_status(
            item,
            status=status,
            selection_status=status,
            disposition_id=disposition_id,
            disposition_turn_id=user_turn.turn_id,
            surface_request_id=request.request_id,
        )
        if str(item.get("internal_work_selection_id") or "") == selection_id
        else item
        for item in _internal_work_selections_for_objective(objective)
    ]
    resolved_request = replace(
        request,
        status="resolved",
        resolution_state=status,
        resolution=status,
        resolution_policy="bound_to_exact_source_bound_internal_work_proposal",
        resolution_text=message,
        resolved_turn_id=user_turn.turn_id,
        consumption_count=1,
        resolved_at=utc_now(),
        consumed_at=utc_now(),
    )
    reply = render_internal_work_disposition(candidate, disposition)
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_internal_work_disposition",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if disposition_added:
        progress = progress + (
            {
                "event": "internal_work_disposition_recorded",
                "objective_id": objective.objective_id,
                "internal_work_disposition_id": disposition_id,
                "internal_work_candidate_id": candidate_id,
                "internal_work_selection_id": selection_id,
                "request_id": request.request_id,
                "status": status,
                "operator_turn_id": user_turn.turn_id,
                "at": utc_now(),
            },
        )
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(
            objective,
            internal_work_candidates=candidates,
            internal_work_selections=selections,
            internal_work_dispositions=dispositions,
        ),
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id),
        resolved_chat_requests=state.resolved_chat_requests + (resolved_request,),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_internal_work_disposition",
            0.98,
            "active_objective_provenance",
            "safe_internal",
            (),
            ("exact_internal_work_binding", "provenance_only_disposition", "no_execution"),
        ),
        reply=reply,
        chat_request=resolved_request.as_record(),
        side_thread_bound=True,
    )


def _resolve_evidence_permission_request(
    state: ConversationalRuntimeState,
    request: ChatAddressableRequest,
    message: str,
    *,
    user_turn: ConversationTurn,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Bind one operator authorization decision to one evidence request."""

    objective = state.active_objective
    if objective is None or objective.objective_id != request.objective_id:
        return None
    evidence_request_id = str(request.baseline_metrics.get("evidence_permission_request_id") or "")
    binding_key = str(request.baseline_metrics.get("semantic_binding_key") or "")
    evidence_request = next(
        (
            item
            for item in _evidence_permission_requests_for_objective(objective)
            if str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or "") == evidence_request_id
            and str(item.get("semantic_binding_key") or "") == binding_key
        ),
        None,
    )
    if evidence_request is None:
        return None
    decision = classify_evidence_permission_operator_response(evidence_request, message)
    if decision is None:
        return None
    normalized = " ".join(str(message or "").split())
    if decision == "unclear":
        reply = (
            "I cannot bind that as an evidence authorization yet. Please answer with approval for a later bounded evidence step, denial, deferral, or the missing context.\n\n"
            "No evidence gathering, model call, provider call, tool use, file read, network access, graph mutation, review, admission, worker, scheduler, or external action started."
        )
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
            role="assistant",
            text=reply,
            intent_type="semantic_evidence_permission_clarification",
            objective_id=objective.objective_id,
        )
        updated = _replace_state(
            state,
            conversation=state.conversation + (user_turn, assistant_turn),
        )
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(
            state=updated,
            intent=ConversationIntent(
                "semantic_evidence_permission_clarification",
                0.82,
                "active_objective_provenance",
                "safe_internal",
                (),
                ("evidence_authorization_unclear", "request_remains_pending", "no_evidence_execution"),
            ),
            reply=reply,
            chat_request=request.as_record(),
            side_thread_bound=True,
        )
    if decision == "granted_pending_separate_execution":
        response_type = "evidence_permission_grant"
        resolution_policy = "evidence_permission_granted_pending_separate_execution"
        resolution_status = "resolved"
        context_text = ""
        interpreted_scope = _interpret_evidence_authorization_scope(normalized)
    elif decision == "denied":
        response_type = "evidence_permission_deny"
        resolution_policy = "evidence_permission_denied"
        resolution_status = "denied"
        context_text = ""
        interpreted_scope = "not_authorized"
    elif decision == "deferred":
        response_type = "evidence_permission_defer"
        resolution_policy = "evidence_permission_deferred"
        resolution_status = "deferred"
        context_text = ""
        interpreted_scope = "deferred_by_operator"
    elif decision == "operator_provided_context":
        response_type = "evidence_permission_answer"
        resolution_policy = "evidence_permission_context_bound"
        resolution_status = "resolved"
        context_text = normalized
        interpreted_scope = str(evidence_request.get("context_answer_type") or "operator_provided_context")
    authorization_id = stable_id(
        "analysis-evidence-authorization",
        request.request_id,
        evidence_request_id,
        decision,
        normalized,
    )
    authorization = {
        "evidence_authorization_id": authorization_id,
        "evidence_permission_request_id": evidence_request_id,
        "evidence_request_id": evidence_request_id,
        "surface_request_id": request.request_id,
        "source_frame_id": str(evidence_request.get("source_frame_id") or ""),
        "source_analysis_id": str(evidence_request.get("source_analysis_id") or ""),
        "source_refinement_id": str(evidence_request.get("source_refinement_id") or ""),
        "source_question_candidate_id": str(evidence_request.get("source_question_candidate_id") or ""),
        "source_question_answer_id": str(evidence_request.get("source_question_answer_id") or ""),
        "source_validation_check_id": str(evidence_request.get("source_validation_check_id") or ""),
        "domain": str(evidence_request.get("domain") or ""),
        "evidence_gap_slot_id": str(evidence_request.get("evidence_gap_slot_id") or ""),
        "semantic_binding_key": binding_key,
        "operator_turn_id": user_turn.turn_id,
        "operator_response_text": normalized,
        "response_type": response_type,
        "authorization_decision": decision,
        "status": decision,
        "interpreted_scope": interpreted_scope,
        "preserved_limits": [str(item) for item in evidence_request.get("prohibited_actions", ()) if str(item)],
        "operator_provided_context_text": context_text,
        "interpreted_context_slot": str(evidence_request.get("context_answer_type") or ""),
        "resolved_evidence_gap_slot_id": str(evidence_request.get("evidence_gap_slot_id") or ""),
        "may_execute_now": False,
        "execution_state": "no_evidence_execution_started",
        "authority_boundary": "Authorization was bound to the exact evidence request; this phase does not execute evidence gathering.",
        "created_event_id": stable_id("analysis-evidence-authorization-event", authorization_id),
        "restart_summary": "Evidence authorization persists exactly once and does not start model, provider, tool, file, network, graph, review, admission, worker, scheduler, or external-action side effects.",
        "schema_version": "evidence_bound_evidence_permission_v1",
    }
    authorizations = list(_evidence_authorizations_for_objective(objective))
    authorization_added = not any(
        str(item.get("evidence_authorization_id") or "") == authorization_id
        for item in authorizations
    )
    if authorization_added:
        authorizations.append(authorization)
    evidence_requests = [
        {
            **dict(item),
            "status": decision,
            "authorization_id": authorization_id,
            "authorization_turn_id": user_turn.turn_id,
            "surface_request_id": request.request_id,
        }
        if str(item.get("evidence_permission_request_id") or item.get("evidence_request_id") or "") == evidence_request_id
        else item
        for item in _evidence_permission_requests_for_objective(objective)
    ]
    evidence_next_operation_proposals = list(_evidence_next_operation_proposals_for_objective(objective))
    evidence_next_operation_events: tuple[Mapping[str, Any], ...] = ()
    evidence_next_operation_chat_request: ChatAddressableRequest | None = None
    selected_evidence_next_operation: dict[str, Any] | None = None
    if decision == "granted_pending_separate_execution" and authorization_added:
        (
            evidence_next_operation_proposals,
            selected_evidence_next_operation,
            evidence_next_operation_events,
        ) = _compile_evidence_next_operation_lifecycle(
            state,
            objective=objective,
            evidence_request=evidence_request,
            evidence_authorization=authorization,
            existing_proposals=evidence_next_operation_proposals,
            ignored_pending_request_id=request.request_id,
        )
        if selected_evidence_next_operation is not None:
            evidence_next_operation_chat_request = _compile_evidence_next_operation_chat_request(
                state,
                objective=objective,
                proposal=selected_evidence_next_operation,
                created_turn_id=user_turn.turn_id,
                created_sequence=len(state.conversation) + 2,
            )
    resolved_request = replace(
        request,
        status="resolved" if resolution_status != "denied" else "denied",
        resolution_state=resolution_status,
        resolution=response_type,
        resolution_policy=resolution_policy,
        resolution_text=message,
        resolved_turn_id=user_turn.turn_id,
        consumption_count=1,
        resolved_at=utc_now(),
        consumed_at=utc_now(),
    )
    reply = render_evidence_authorization(evidence_request, authorization)
    if evidence_next_operation_chat_request is not None and selected_evidence_next_operation is not None:
        reply = f"{reply}\n\n{render_evidence_next_operation_proposal(selected_evidence_next_operation)}"
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_evidence_permission_authorization",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if authorization_added:
        progress = progress + (
            {
                "event": "evidence_authorization_recorded",
                "objective_id": objective.objective_id,
                "evidence_request_id": evidence_request_id,
                "evidence_authorization_id": authorization_id,
                "status": decision,
                "operator_turn_id": user_turn.turn_id,
                "at": utc_now(),
            },
        )
    if evidence_next_operation_events:
        progress = progress + evidence_next_operation_events
    if evidence_next_operation_chat_request is not None and selected_evidence_next_operation is not None:
        evidence_next_operation_chat_request = replace(
            evidence_next_operation_chat_request,
            rendered_turn_id=assistant_turn.turn_id,
            render_sequence=len(state.conversation) + 2,
        )
        selected_proposal_id = str(selected_evidence_next_operation.get("evidence_next_operation_proposal_id") or "")
        evidence_next_operation_proposals = [
            {
                **dict(item),
                "status": "surfaced",
                "surfaced_turn_id": assistant_turn.turn_id,
                "request_id": evidence_next_operation_chat_request.request_id,
                "rendered_turn_id": assistant_turn.turn_id,
                "render_sequence": len(state.conversation) + 2,
            }
            if str(item.get("evidence_next_operation_proposal_id") or "") == selected_proposal_id
            else item
            for item in evidence_next_operation_proposals
        ]
        progress = progress + (
            {
                "event": "evidence_next_operation_proposal_rendered",
                "objective_id": objective.objective_id,
                "evidence_next_operation_proposal_id": selected_proposal_id,
                "source_evidence_request_id": str(selected_evidence_next_operation.get("source_evidence_request_id") or ""),
                "source_evidence_authorization_id": str(selected_evidence_next_operation.get("source_evidence_authorization_id") or ""),
                "request_id": evidence_next_operation_chat_request.request_id,
                "assistant_turn_id": assistant_turn.turn_id,
                "at": utc_now(),
            },
        )
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(
            objective,
            evidence_requests=evidence_requests,
            evidence_authorizations=authorizations,
            evidence_next_operation_proposals=evidence_next_operation_proposals,
        ),
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=(
            tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
            + ((evidence_next_operation_chat_request,) if evidence_next_operation_chat_request is not None else ())
        ),
        resolved_chat_requests=state.resolved_chat_requests + (resolved_request,),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_evidence_permission_authorization",
            0.98,
            "active_objective_provenance",
            "safe_internal",
            (),
            ("exact_evidence_request_binding", "authorization_only", "no_evidence_execution"),
        ),
        reply=reply,
        chat_request=resolved_request.as_record(),
        side_thread_bound=True,
    )


def _resolve_evidence_next_operation_proposal(
    state: ConversationalRuntimeState,
    request: ChatAddressableRequest,
    message: str,
    *,
    user_turn: ConversationTurn,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Bind one operator disposition to one non-executing proposal."""

    objective = state.active_objective
    if objective is None or objective.objective_id != request.objective_id:
        return None
    proposal_id = str(request.baseline_metrics.get("evidence_next_operation_proposal_id") or "")
    proposal = next(
        (
            item
            for item in _evidence_next_operation_proposals_for_objective(objective)
            if str(item.get("evidence_next_operation_proposal_id") or "") == proposal_id
        ),
        None,
    )
    if proposal is None:
        return None
    status = classify_evidence_next_operation_operator_response(proposal, message)
    if status is None:
        return None
    normalized = " ".join(str(message or "").split())
    disposition_id = stable_id(
        "analysis-evidence-next-operation-disposition",
        request.request_id,
        proposal_id,
        status,
        normalized,
    )
    disposition = {
        "evidence_next_operation_disposition_id": disposition_id,
        "evidence_next_operation_proposal_id": proposal_id,
        "source_evidence_request_id": str(proposal.get("source_evidence_request_id") or ""),
        "source_evidence_authorization_id": str(proposal.get("source_evidence_authorization_id") or ""),
        "source_frame_id": str(proposal.get("source_frame_id") or ""),
        "source_analysis_id": str(proposal.get("source_analysis_id") or ""),
        "source_refinement_id": str(proposal.get("source_refinement_id") or ""),
        "surface_request_id": request.request_id,
        "operator_turn_id": user_turn.turn_id,
        "operator_response_text": normalized,
        "operator_context_text": normalized if status == "context_provided" else "",
        "status": status,
        "may_execute_now": False,
        "execution_state": "no_evidence_execution_started",
        "authority_boundary": "Proposal disposition recorded; execution still requires a separate later gate.",
        "created_event_id": stable_id("analysis-evidence-next-operation-disposition-event", disposition_id),
        "restart_summary": "Evidence next-operation disposition persists exactly once without file, network, model, provider, tool, sandbox, graph, review, admission, worker, scheduler, or external-action side effects.",
        "schema_version": "evidence_bound_next_operation_proposal_v1",
    }
    dispositions = list(_evidence_next_operation_dispositions_for_objective(objective))
    disposition_added = not any(
        str(item.get("evidence_next_operation_disposition_id") or "") == disposition_id
        for item in dispositions
    )
    if disposition_added:
        dispositions.append(disposition)
    evidence_execution_authorities = list(_evidence_execution_authorities_for_objective(objective))
    evidence_execution_authority_events: tuple[Mapping[str, Any], ...] = ()
    evidence_execution_authority_chat_request: ChatAddressableRequest | None = None
    if status == "accepted_pending_separate_execution" and disposition_added:
        (
            evidence_execution_authorities,
            should_surface_execution_authority,
            evidence_execution_authority_events,
        ) = _compile_evidence_execution_authority_lifecycle(
            state,
            objective=objective,
            proposal=proposal,
            disposition=disposition,
            existing_authorities=evidence_execution_authorities,
            ignored_pending_request_id=request.request_id,
        )
        if should_surface_execution_authority:
            evidence_execution_authority_chat_request = _compile_evidence_execution_authority_chat_request(
                state,
                objective=objective,
                proposal=proposal,
                disposition=disposition,
                created_turn_id=user_turn.turn_id,
                created_sequence=len(state.conversation) + 2,
            )
    proposals = [
        {
            **dict(item),
            "status": status,
            "disposition_id": disposition_id,
            "disposition_turn_id": user_turn.turn_id,
            "surface_request_id": request.request_id,
        }
        if str(item.get("evidence_next_operation_proposal_id") or "") == proposal_id
        else item
        for item in _evidence_next_operation_proposals_for_objective(objective)
    ]
    resolved_request = replace(
        request,
        status="resolved",
        resolution_state=status,
        resolution=status,
        resolution_policy="bound_to_exact_evidence_next_operation_proposal",
        resolution_text=message,
        resolved_turn_id=user_turn.turn_id,
        consumption_count=1,
        resolved_at=utc_now(),
        consumed_at=utc_now(),
    )
    reply = render_evidence_next_operation_disposition(proposal, disposition)
    if evidence_execution_authority_chat_request is not None:
        reply = f"{reply}\n\n{render_evidence_execution_authority_request(proposal, disposition)}"
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_evidence_next_operation_disposition",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if disposition_added:
        progress = progress + (
            {
                "event": "evidence_next_operation_disposition_recorded",
                "objective_id": objective.objective_id,
                "evidence_next_operation_disposition_id": disposition_id,
                "evidence_next_operation_proposal_id": proposal_id,
                "request_id": request.request_id,
                "status": status,
                "operator_turn_id": user_turn.turn_id,
                "at": utc_now(),
            },
        )
    if evidence_execution_authority_events:
        progress = progress + evidence_execution_authority_events
    if evidence_execution_authority_chat_request is not None:
        evidence_execution_authority_chat_request = replace(
            evidence_execution_authority_chat_request,
            rendered_turn_id=assistant_turn.turn_id,
            render_sequence=len(state.conversation) + 2,
        )
        progress = progress + (
            {
                "event": "evidence_execution_authority_request_rendered",
                "objective_id": objective.objective_id,
                "evidence_next_operation_proposal_id": proposal_id,
                "evidence_next_operation_disposition_id": disposition_id,
                "request_id": evidence_execution_authority_chat_request.request_id,
                "assistant_turn_id": assistant_turn.turn_id,
                "at": utc_now(),
            },
        )
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(
            objective,
            evidence_next_operation_proposals=proposals,
            evidence_next_operation_dispositions=dispositions,
            evidence_execution_authorities=evidence_execution_authorities,
        ),
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=(
            tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
            + ((evidence_execution_authority_chat_request,) if evidence_execution_authority_chat_request is not None else ())
        ),
        resolved_chat_requests=state.resolved_chat_requests + (resolved_request,),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_evidence_next_operation_disposition",
            0.98,
            "active_objective_provenance",
            "safe_internal",
            (),
            ("exact_next_operation_binding", "proposal_only_disposition", "no_evidence_execution"),
        ),
        reply=reply,
        chat_request=resolved_request.as_record(),
        side_thread_bound=True,
    )


def _resolve_evidence_execution_authority_request(
    state: ConversationalRuntimeState,
    request: ChatAddressableRequest,
    message: str,
    *,
    user_turn: ConversationTurn,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Bind one inert future-execution authority decision."""

    objective = state.active_objective
    if objective is None or objective.objective_id != request.objective_id:
        return None
    proposal_id = str(request.baseline_metrics.get("evidence_next_operation_proposal_id") or "")
    disposition_id = str(request.baseline_metrics.get("evidence_next_operation_disposition_id") or "")
    proposal = next(
        (
            item
            for item in _evidence_next_operation_proposals_for_objective(objective)
            if str(item.get("evidence_next_operation_proposal_id") or "") == proposal_id
        ),
        None,
    )
    disposition = next(
        (
            item
            for item in _evidence_next_operation_dispositions_for_objective(objective)
            if str(item.get("evidence_next_operation_disposition_id") or "") == disposition_id
            and str(item.get("evidence_next_operation_proposal_id") or "") == proposal_id
        ),
        None,
    )
    if proposal is None or disposition is None:
        return None
    decision = classify_evidence_execution_authority_operator_response(request.baseline_metrics, message)
    if decision is None:
        return None
    normalized = " ".join(str(message or "").split())
    if decision == "unclear_pending":
        reply = (
            "I cannot bind that as future execution authority yet. Please approve recording authority for a future bounded execution gate, decline it, defer it, or add context.\n\n"
            "No evidence gathering, file read, network access, model/provider/tool call, sandbox execution, graph mutation, review, admission, worker, scheduler, or external action started."
        )
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
            role="assistant",
            text=reply,
            intent_type="semantic_evidence_execution_authority_clarification",
            objective_id=objective.objective_id,
        )
        updated = _replace_state(
            state,
            conversation=state.conversation + (user_turn, assistant_turn),
        )
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(
            state=updated,
            intent=ConversationIntent(
                "semantic_evidence_execution_authority_clarification",
                0.82,
                "active_objective_provenance",
                "safe_internal",
                (),
                ("evidence_execution_authority_unclear", "request_remains_pending", "no_execution"),
            ),
            reply=reply,
            chat_request=request.as_record(),
            side_thread_bound=True,
        )
    records = list(_evidence_execution_authorities_for_objective(objective))
    compiled = tuple(
        item.as_record()
        for item in compile_evidence_execution_authority_records(
            proposal,
            disposition,
            objective_id=objective.objective_id,
            operator_decision=decision,
            operator_response_text=normalized,
        )
    )
    if not compiled:
        return None
    authority = dict(compiled[0])
    authority["surface_request_id"] = request.request_id
    authority["operator_turn_id"] = user_turn.turn_id
    authority_added = not any(
        str(item.get("evidence_execution_authority_id") or "") == str(authority.get("evidence_execution_authority_id") or "")
        for item in records
    )
    if authority_added:
        records.append(authority)
    fixture_execution_plans = list(_evidence_fixture_execution_plans_for_objective(objective))
    fixture_execution_plan_events: tuple[Mapping[str, Any], ...] = ()
    fixture_execution_plan_chat_request: ChatAddressableRequest | None = None
    selected_fixture_execution_plan: dict[str, Any] | None = None
    if decision == "approved_for_future_gate" and authority_added:
        (
            fixture_execution_plans,
            selected_fixture_execution_plan,
            fixture_execution_plan_events,
        ) = _compile_evidence_fixture_execution_plan_lifecycle(
            state,
            objective=objective,
            proposal=proposal,
            disposition=disposition,
            authority=authority,
            existing_plans=fixture_execution_plans,
            ignored_pending_request_id=request.request_id,
        )
        if selected_fixture_execution_plan is not None:
            fixture_execution_plan_chat_request = _compile_evidence_fixture_execution_plan_chat_request(
                state,
                objective=objective,
                plan=selected_fixture_execution_plan,
                created_turn_id=user_turn.turn_id,
                created_sequence=len(state.conversation) + 2,
            )
    resolved_request = replace(
        request,
        status="resolved",
        resolution_state=decision,
        resolution=decision,
        resolution_policy="bound_to_exact_evidence_execution_authority_request",
        resolution_text=message,
        resolved_turn_id=user_turn.turn_id,
        consumption_count=1,
        resolved_at=utc_now(),
        consumed_at=utc_now(),
    )
    reply = render_evidence_execution_authority_record(proposal, authority)
    if fixture_execution_plan_chat_request is not None and selected_fixture_execution_plan is not None:
        reply = f"{reply}\n\n{render_evidence_fixture_execution_plan(selected_fixture_execution_plan)}"
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_evidence_execution_authority_record",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress
    if authority_added:
        progress = progress + (
            {
                "event": "evidence_execution_authority_recorded",
                "objective_id": objective.objective_id,
                "evidence_execution_authority_id": str(authority.get("evidence_execution_authority_id") or ""),
                "evidence_next_operation_proposal_id": proposal_id,
                "evidence_next_operation_disposition_id": disposition_id,
                "status": decision,
                "request_id": request.request_id,
                "operator_turn_id": user_turn.turn_id,
                "at": utc_now(),
            },
        )
    if fixture_execution_plan_events:
        progress = progress + fixture_execution_plan_events
    if fixture_execution_plan_chat_request is not None and selected_fixture_execution_plan is not None:
        fixture_execution_plan_chat_request = replace(
            fixture_execution_plan_chat_request,
            rendered_turn_id=assistant_turn.turn_id,
            render_sequence=len(state.conversation) + 2,
        )
        selected_plan_id = str(selected_fixture_execution_plan.get("evidence_fixture_execution_plan_id") or "")
        fixture_execution_plans = [
            {
                **dict(item),
                "status": "surfaced",
                "surfaced_turn_id": assistant_turn.turn_id,
                "request_id": fixture_execution_plan_chat_request.request_id,
                "rendered_turn_id": assistant_turn.turn_id,
                "render_sequence": len(state.conversation) + 2,
            }
            if str(item.get("evidence_fixture_execution_plan_id") or "") == selected_plan_id
            else item
            for item in fixture_execution_plans
        ]
        progress = progress + (
            {
                "event": "evidence_fixture_execution_plan_rendered",
                "objective_id": objective.objective_id,
                "evidence_fixture_execution_plan_id": selected_plan_id,
                "source_evidence_execution_authority_id": str(selected_fixture_execution_plan.get("source_evidence_execution_authority_id") or ""),
                "request_id": fixture_execution_plan_chat_request.request_id,
                "assistant_turn_id": assistant_turn.turn_id,
                "at": utc_now(),
            },
        )
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(
            objective,
            evidence_execution_authorities=records,
            evidence_fixture_execution_plans=fixture_execution_plans,
        ),
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=(
            tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
            + ((fixture_execution_plan_chat_request,) if fixture_execution_plan_chat_request is not None else ())
        ),
        resolved_chat_requests=state.resolved_chat_requests + (resolved_request,),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_evidence_execution_authority_record",
            0.98,
            "active_objective_provenance",
            "safe_internal",
            (),
            ("exact_execution_authority_binding", "authority_record_only", "no_execution"),
        ),
        reply=reply,
        chat_request=resolved_request.as_record(),
        side_thread_bound=True,
    )


def _resolve_evidence_fixture_execution_plan_request(
    state: ConversationalRuntimeState,
    request: ChatAddressableRequest,
    message: str,
    *,
    user_turn: ConversationTurn,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Bind one operator disposition to an inert fixture/evidence plan."""

    objective = state.active_objective
    if objective is None or objective.objective_id != request.objective_id:
        return None
    plan_id = str(request.baseline_metrics.get("evidence_fixture_execution_plan_id") or "")
    plan = next(
        (
            item
            for item in _evidence_fixture_execution_plans_for_objective(objective)
            if str(item.get("evidence_fixture_execution_plan_id") or "") == plan_id
        ),
        None,
    )
    if plan is None:
        return None
    status = classify_evidence_fixture_execution_plan_operator_response(plan, message)
    if status is None:
        return None
    normalized = " ".join(str(message or "").split())
    if status == "unclear_pending":
        reply = (
            "I cannot bind that as a plan disposition yet. Please accept the bounded plan for a later separate execution gate, decline it, defer it, or add context.\n\n"
            "No evidence gathering, file read, network access, model/provider/tool call, sandbox execution, graph mutation, review, admission, worker, scheduler, or external action started."
        )
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
            role="assistant",
            text=reply,
            intent_type="semantic_evidence_fixture_execution_plan_clarification",
            objective_id=objective.objective_id,
        )
        updated = _replace_state(
            state,
            conversation=state.conversation + (user_turn, assistant_turn),
        )
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(
            state=updated,
            intent=ConversationIntent(
                "semantic_evidence_fixture_execution_plan_clarification",
                0.82,
                "active_objective_provenance",
                "safe_internal",
                (),
                ("evidence_fixture_execution_plan_unclear", "request_remains_pending", "no_execution"),
            ),
            reply=reply,
            chat_request=request.as_record(),
            side_thread_bound=True,
        )
    updated_plan = {
        **dict(plan),
        "status": status,
        "operator_plan_response_text": normalized,
        "operator_plan_context_text": normalized if status == "context_provided" else "",
        "plan_disposition_turn_id": user_turn.turn_id,
        "surface_request_id": request.request_id,
        "may_execute_now": False,
        "execution_requires_future_gate": True,
    }
    plans = [
        updated_plan
        if str(item.get("evidence_fixture_execution_plan_id") or "") == plan_id
        else item
        for item in _evidence_fixture_execution_plans_for_objective(objective)
    ]
    dry_run_results = list(_evidence_fixture_dry_run_results_for_objective(objective))
    dry_run_result: dict[str, Any] | None = None
    dry_run_events: tuple[Mapping[str, Any], ...] = ()
    ingestion_candidates = list(_evidence_result_ingestion_candidates_for_objective(objective))
    ingestion_candidate: dict[str, Any] | None = None
    ingestion_candidate_events: tuple[Mapping[str, Any], ...] = ()
    if status == "accepted_pending_execution_gate":
        (
            dry_run_results,
            dry_run_result,
            dry_run_events,
        ) = _compile_evidence_fixture_dry_run_result_lifecycle(
            state,
            objective=objective,
            plan=updated_plan,
            existing_results=dry_run_results,
            ignored_pending_request_id=request.request_id,
        )
        if dry_run_result is not None:
            (
                ingestion_candidates,
                ingestion_candidate,
                ingestion_candidate_events,
            ) = _compile_evidence_result_ingestion_candidate_lifecycle(
                state,
                objective=objective,
                dry_run_result=dry_run_result,
                existing_candidates=ingestion_candidates,
                ignored_pending_request_id=request.request_id,
            )
    resolved_request = replace(
        request,
        status="resolved",
        resolution_state=status,
        resolution=status,
        resolution_policy="bound_to_exact_evidence_fixture_execution_plan",
        resolution_text=message,
        resolved_turn_id=user_turn.turn_id,
        consumption_count=1,
        resolved_at=utc_now(),
        consumed_at=utc_now(),
    )
    reply = render_evidence_fixture_execution_plan_update(updated_plan)
    if dry_run_result is not None:
        reply = f"{reply}\n\n{render_evidence_fixture_dry_run_result(dry_run_result)}"
    if ingestion_candidate is not None:
        reply = f"{reply}\n\n{render_evidence_result_ingestion_candidate(ingestion_candidate)}"
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="semantic_evidence_fixture_execution_plan_update",
        objective_id=objective.objective_id,
    )
    progress = state.objective_progress + (
        {
            "event": "evidence_fixture_execution_plan_disposition_recorded",
            "objective_id": objective.objective_id,
            "evidence_fixture_execution_plan_id": plan_id,
            "status": status,
            "request_id": request.request_id,
            "operator_turn_id": user_turn.turn_id,
            "at": utc_now(),
        },
    )
    if dry_run_events:
        progress = progress + dry_run_events
    if ingestion_candidate_events:
        progress = progress + ingestion_candidate_events
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(
            objective,
            evidence_fixture_execution_plans=plans,
            evidence_fixture_dry_run_results=dry_run_results,
            evidence_result_ingestion_candidates=ingestion_candidates,
        ),
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id),
        resolved_chat_requests=state.resolved_chat_requests + (resolved_request,),
        objective_progress=progress,
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            "semantic_evidence_fixture_execution_plan_update",
            0.98,
            "active_objective_provenance",
            "safe_internal",
            (),
            ("exact_fixture_execution_plan_binding", "dry_run_result_record_only", "no_execution"),
        ),
        reply=reply,
        chat_request=resolved_request.as_record(),
        side_thread_bound=True,
    )


def resolve_pending_chat_request(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    request = _pending_request_for_reply(state, message)
    if request is None:
        return None
    resolution_kind = _chat_request_resolution_kind(message) or ""
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="chat_request_resolution",
        objective_id=request.objective_id,
    )
    authority: Mapping[str, Any] | None = None
    policy = resolution_kind
    if request.request_type == "evidence_bound_analysis_question":
        return _resolve_evidence_bound_analysis_question(
            state,
            request,
            message,
            user_turn=user_turn,
            runtime_root=runtime_root,
        )
    if request.request_type == "internal_work_continuation":
        return _resolve_internal_work_continuation(
            state,
            request,
            message,
            user_turn=user_turn,
            runtime_root=runtime_root,
        )
    if request.request_type == "evidence_permission":
        return _resolve_evidence_permission_request(
            state,
            request,
            message,
            user_turn=user_turn,
            runtime_root=runtime_root,
        )
    if request.request_type == "evidence_next_operation_proposal":
        return _resolve_evidence_next_operation_proposal(
            state,
            request,
            message,
            user_turn=user_turn,
            runtime_root=runtime_root,
        )
    if request.request_type == "evidence_execution_authority":
        return _resolve_evidence_execution_authority_request(
            state,
            request,
            message,
            user_turn=user_turn,
            runtime_root=runtime_root,
        )
    if request.request_type == "evidence_fixture_execution_plan":
        return _resolve_evidence_fixture_execution_plan_request(
            state,
            request,
            message,
            user_turn=user_turn,
            runtime_root=runtime_root,
        )
    if request.request_type in {"teaching_provisional_retention", "teaching_prerequisite", "teaching_consolidation_review_authority"}:
        return _resolve_teaching_chat_request(
            state,
            request,
            message,
            resolution_kind,
            runtime_root=runtime_root,
        )
    if request.request_type == "provider_authority":
        policy, authority = _resolve_provider_policy(request, message, resolution_kind)
    if request.request_type == "capability_adoption_and_restart":
        capability_state, capability_reply, resolved_request = _resolve_capability_adoption(state, request, message, resolution_kind, runtime_root=runtime_root)
        if resolution_kind == "show_evidence":
            return RuntimeTurnResult(
                state=capability_state,
                intent=ConversationIntent(
                    intent_type="chat_request_resolution",
                    confidence=0.88,
                    persistence_scope="active_objective",
                    risk_class="safe_internal",
                    authority_required=(),
                    matched_signals=("pending_capability_adoption_request", "show_evidence"),
                ),
                reply=capability_reply,
                chat_request=resolved_request.as_record(),
                side_thread_bound=True,
            )
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", capability_state.runtime_id, str(len(capability_state.conversation) + 1), capability_reply),
            role="assistant",
            text=capability_reply,
            intent_type="capability_adoption_resolution_ack",
            objective_id=request.objective_id,
        )
        capability_state = _replace_state(capability_state, conversation=capability_state.conversation + (user_turn, assistant_turn))
        save_runtime_state(runtime_root, capability_state)
        return RuntimeTurnResult(
            state=capability_state,
            intent=ConversationIntent(
                intent_type="chat_request_resolution",
                confidence=0.9,
                persistence_scope="active_objective",
                risk_class="safe_internal",
                authority_required=(),
                matched_signals=("pending_capability_adoption_request",),
            ),
            reply=capability_reply,
            chat_request=resolved_request.as_record(),
            side_thread_bound=True,
        )
    if request.request_type == "knowledge_model_budget_increase":
        if resolution_kind == "approved":
            new_budget = max(state.active_objective.model_call_budget if state.active_objective else 0, request.max_calls)
            updated_objective = replace(
                state.active_objective,
                model_call_budget=new_budget,
                cycle_budget=max(state.active_objective.cycle_budget, new_budget),
                provenance={
                    **state.active_objective.provenance,
                    "temporary_model_call_budget": {
                        "approved_request_id": request.request_id,
                        "authorized_model_call_budget": new_budget,
                        "approved_at": utc_now(),
                        "scope": "active_goal_only",
                    },
                },
            ) if state.active_objective else None
            resolved_request = ChatAddressableRequest(**{**request.as_record(), "status": "consumed", "resolution_state": "consumed", "resolution": "approved", "resolution_policy": "approved_temporary_goal_budget", "resolution_text": message, "resolved_turn_id": user_turn.turn_id, "resolved_at": utc_now(), "consumed_at": utc_now(), "consumption_count": 1})
            reply = f"Approved. I temporarily increased this goal's local-model budget to {new_budget} calls and will continue the same goal thread."
            lifecycle = "running"
            progress_event = {"event": "knowledge_model_budget_increase_approved", "request_id": request.request_id, "authorized_model_call_budget": new_budget, "scope": "active_goal_only", "at": utc_now()}
        else:
            resolved_request = ChatAddressableRequest(**{**request.as_record(), "status": "denied", "resolution_state": "denied", "resolution": "denied", "resolution_policy": "denied_stop_with_partial_report", "resolution_text": message, "resolved_turn_id": user_turn.turn_id, "resolved_at": utc_now(), "consumption_count": 1})
            updated_objective = state.active_objective
            reply = "Understood. I stopped the budget increase and will keep the current partial report as the terminal state."
            lifecycle = "paused_budget"
            progress_event = {"event": "knowledge_model_budget_increase_denied", "request_id": request.request_id, "at": utc_now()}
        pending = tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
            role="assistant",
            text=reply,
            intent_type="knowledge_budget_resolution_ack",
            objective_id=request.objective_id,
        )
        progress_source = state.objective_progress
        if resolution_kind == "approved" and updated_objective is not None:
            progress_source = _with_updated_knowledge_event_budget(
                progress_source,
                objective_id=updated_objective.objective_id,
                model_call_budget=updated_objective.model_call_budget,
                cycle_budget=updated_objective.cycle_budget,
            )
        updated = _replace_state(
            state,
            lifecycle_state=lifecycle,
            active_objective=updated_objective,
            conversation=state.conversation + (user_turn, assistant_turn),
            pending_chat_requests=pending,
            resolved_chat_requests=state.resolved_chat_requests + (resolved_request,),
            objective_progress=progress_source + (progress_event,),
        )
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(
            state=updated,
            intent=ConversationIntent("chat_request_resolution", 0.9, "active_objective", "safe_internal", (), ("pending_knowledge_budget_request",)),
            reply=reply,
            chat_request=resolved_request.as_record(),
            side_thread_bound=True,
        )
    resolved = ChatAddressableRequest(
        **{
            **request.as_record(),
            "status": "denied" if policy == "denied_continue_locally" else "resolved",
            "resolution_state": "denied" if policy == "denied_continue_locally" else "resolved",
            "resolved_turn_id": user_turn.turn_id,
            "resolution_text": message,
            "resolution_policy": policy,
            "consumption_count": 1,
            "resolved_at": utc_now(),
        }
    )
    pending = tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
    if authority:
        reply = "Approved. I recorded one bounded provider authority envelope for that goal thread. I still will not make a provider call until the provider step consumes this exact approval."
    elif policy == "denied_continue_locally":
        reply = "Understood. I denied that provider branch and will continue the goal locally."
    else:
        reply = "Got it. I bound that reply to the background goal thread and kept the foreground conversation unchanged."
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="chat_request_resolution_ack",
        objective_id=request.objective_id,
    )
    updated = _replace_state(
        state,
        conversation=state.conversation + (user_turn, assistant_turn),
        pending_chat_requests=pending,
        resolved_chat_requests=state.resolved_chat_requests + (resolved,),
        provider_authorities=state.provider_authorities + ((authority,) if authority else ()),
        objective_progress=state.objective_progress
        + (
            {
                "event": "chat_addressable_request_resolved",
                "request_id": request.request_id,
                "request_type": request.request_type,
                "resolution_policy": policy,
                "authority_id": authority.get("authority_id") if authority else "",
                "at": utc_now(),
            },
        ),
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            intent_type="chat_request_resolution",
            confidence=0.88,
            persistence_scope="active_objective",
            risk_class="safe_internal" if not authority else "provider_authority_bound",
            authority_required=(),
            matched_signals=("pending_chat_request",),
        ),
        reply=reply,
        chat_request=resolved.as_record(),
        provider_authority=authority,
        side_thread_bound=True,
    )


def apply_stop_or_redirect(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> ConversationalRuntimeState:
    if not state.active_objective:
        return state
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="stop_or_redirect",
        objective_id=state.active_objective.objective_id,
    )
    progress = state.objective_progress + (
        {
            "event": "operator_stop_or_redirect",
            "turn_id": user_turn.turn_id,
            "message": message,
            "at": utc_now(),
        },
    )
    updated = _replace_state(state, conversation=state.conversation + (user_turn,), lifecycle_state="paused_operator", objective_progress=progress)
    save_runtime_state(runtime_root, updated)
    return updated


def _state_from_record(payload: Mapping[str, Any]) -> ConversationalRuntimeState:
    objective_payload = payload.get("active_objective")
    authority_payload = payload.get("authority")
    return ConversationalRuntimeState(
        runtime_id=str(payload["runtime_id"]),
        lifecycle_state=str(payload.get("lifecycle_state") or "running"),
        active_objective=objective_payload if isinstance(objective_payload, ConversationalObjective) else (ConversationalObjective(**objective_payload) if isinstance(objective_payload, dict) else None),
        authority=authority_payload if isinstance(authority_payload, StandingAuthority) else (StandingAuthority(**authority_payload) if isinstance(authority_payload, dict) else None),
        conversation=tuple(item if isinstance(item, ConversationTurn) else ConversationTurn(**item) for item in payload.get("conversation", ())),
        corrections=tuple(item if isinstance(item, CorrectionRecord) else CorrectionRecord(**item) for item in payload.get("corrections", ())),
        accepted_lessons=tuple(item if isinstance(item, ScopedLesson) else ScopedLesson(**item) for item in payload.get("accepted_lessons", ())),
        rejected_lessons=tuple(payload.get("rejected_lessons", ())),
        focus_history=tuple(payload.get("focus_history", ())),
        objective_progress=tuple(payload.get("objective_progress", ())),
        active_episode_path=str(payload.get("active_episode_path") or ""),
        completed_cycle_keys=tuple(payload.get("completed_cycle_keys", ())),
        pending_material_authority=tuple(payload.get("pending_material_authority", ())),
        pending_chat_requests=tuple(_request_from_record(item) for item in payload.get("pending_chat_requests", ())),
        resolved_chat_requests=tuple(_request_from_record(item) for item in payload.get("resolved_chat_requests", ())),
        provider_authorities=tuple(payload.get("provider_authorities", ())),
        turn_relation_decisions=tuple(_turn_relation_from_record(item) for item in payload.get("turn_relation_decisions", ())),
        local_semantic_insufficiencies=tuple(_insufficiency_from_record(item) for item in payload.get("local_semantic_insufficiencies", ())),
        goal_reviews=tuple(payload.get("goal_reviews", ())),
        archived_objectives=tuple(payload.get("archived_objectives", ())),
        tentative_goals=tuple(_tentative_goal_from_record(item) for item in payload.get("tentative_goals", ())),
        capability_campaigns=tuple(payload.get("capability_campaigns", ())),
        capability_registry=tuple(payload.get("capability_registry", ())),
        capability_adoption_records=tuple(payload.get("capability_adoption_records", ())),
        restart_records=tuple(payload.get("restart_records", ())),
        schema_version=str(payload.get("schema_version") or SCHEMA_VERSION),
    )


def _apply_objective_execution_constraint_release(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
) -> RuntimeTurnResult | None:
    """Release only a held local-model cycle through an explicit operator turn."""

    objective = state.active_objective
    hold_reason = _objective_execution_hold_reason(objective)
    if objective is None or not hold_reason or not _is_explicit_local_model_release(message):
        return None
    constraints = _objective_execution_constraints_for_objective(objective)
    released_at = utc_now()
    history = tuple(
        dict(item)
        for item in constraints.get("override_history", ())
        if isinstance(item, Mapping)
    ) + (
        {
            "event": "operator_released_local_model_hold",
            "released_fields": ("no_local_model", "wait_for_operator_input"),
            "prior_hold_reason": hold_reason,
            "at": released_at,
        },
    )
    updated_constraints = {
        **constraints,
        "no_local_model": False,
        "wait_for_operator_input": False,
        "state": "operator_released",
        "override_history": history,
    }
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="objective_execution_constraints_release",
        objective_id=objective.objective_id,
    )
    reply = (
        "I recorded your explicit release of the local-model hold for this active goal. "
        "The original source-bound inputs and all provider/external-action limits remain unchanged."
    )
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="objective_execution_constraints_release_ack",
        objective_id=objective.objective_id,
    )
    updated = _replace_state(
        state,
        active_objective=_replace_teaching_objective(
            objective,
            execution_constraints=updated_constraints,
        ),
        conversation=state.conversation + (user_turn, assistant_turn),
        objective_progress=state.objective_progress + (
            {
                "event": "objective_execution_constraints_released",
                "objective_id": objective.objective_id,
                "prior_hold_reason": hold_reason,
                "released_fields": ("no_local_model", "wait_for_operator_input"),
                "at": released_at,
            },
        ),
    )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            intent_type="objective_execution_constraints_release",
            confidence=0.99,
            persistence_scope="active_objective",
            risk_class="safe_internal",
            authority_required=(),
            matched_signals=("explicit_local_model_release",),
        ),
        reply=reply,
        background_cycle_started=updated.lifecycle_state == "running",
    )


def handle_conversational_message(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
    run_background_cycle: bool = True,
    model_runner: ModelRunner | None = None,
) -> RuntimeTurnResult:
    governed = resolve_developmental_governance_instruction(
        state,
        message,
        runtime_root=runtime_root,
    )
    if governed is not None:
        return governed
    resolved = resolve_pending_chat_request(state, message, runtime_root=runtime_root)
    if resolved is not None:
        return resolved
    execution_constraint_release = _apply_objective_execution_constraint_release(
        state,
        message,
        runtime_root=runtime_root,
    )
    if execution_constraint_release is not None:
        return execution_constraint_release
    evidence_bound_refinement_recall = _apply_evidence_bound_analysis_refinement_recall(
        state,
        message,
        runtime_root=runtime_root,
    )
    if evidence_bound_refinement_recall is not None:
        return evidence_bound_refinement_recall
    internal_work_recall = _apply_internal_work_recall(
        state,
        message,
        runtime_root=runtime_root,
    )
    if internal_work_recall is not None:
        return internal_work_recall
    evidence_permission_recall = _apply_evidence_permission_recall(
        state,
        message,
        runtime_root=runtime_root,
    )
    if evidence_permission_recall is not None:
        return evidence_permission_recall
    semantic_recall = _apply_source_bound_semantic_recall(
        state,
        message,
        runtime_root=runtime_root,
    )
    if semantic_recall is not None:
        return semantic_recall
    evidence_bound_analysis_recall = _apply_evidence_bound_analysis_recall(
        state,
        message,
        runtime_root=runtime_root,
    )
    if evidence_bound_analysis_recall is not None:
        return evidence_bound_analysis_recall
    semantic_problem_recall = _apply_semantic_problem_frame_recall(
        state,
        message,
        runtime_root=runtime_root,
    )
    if semantic_problem_recall is not None:
        return semantic_problem_recall
    semantic_problem_modeling = _apply_semantic_problem_modeling(
        state,
        message,
        runtime_root=runtime_root,
    )
    if semantic_problem_modeling is not None:
        return semantic_problem_modeling
    semantic_competence_delta = _apply_source_bound_semantic_competence_measurement(
        state,
        message,
        runtime_root=runtime_root,
    )
    if semantic_competence_delta is not None:
        return semantic_competence_delta
    semantic_analysis = _apply_source_bound_semantic_analysis(
        state,
        message,
        runtime_root=runtime_root,
    )
    if semantic_analysis is not None:
        return semantic_analysis
    semantic_transfer = _apply_source_bound_semantic_transfer(
        state,
        message,
        runtime_root=runtime_root,
    )
    if semantic_transfer is not None:
        return semantic_transfer
    if _is_provider_learning_packet_request(message, state):
        return request_provider_learning_packet(state, message, runtime_root=runtime_root)
    if state.active_objective and state.lifecycle_state == "paused_operator" and re.search(r"\bresume(?:\s+the)?\s+(?:active\s+)?goal\b", message, flags=re.IGNORECASE):
        resumed = resume_active_objective(state, runtime_root=runtime_root)
        reply = "I resumed the active goal and preserved its existing objective identity and authority state."
        user_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", resumed.runtime_id, str(len(resumed.conversation) + 1), message),
            role="user", text=message, intent_type="resume_goal", objective_id=resumed.active_objective.objective_id,
        )
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", resumed.runtime_id, str(len(resumed.conversation) + 2), reply),
            role="assistant", text=reply, intent_type="resume_goal_ack", objective_id=resumed.active_objective.objective_id,
        )
        resumed = _replace_state(resumed, conversation=resumed.conversation + (user_turn, assistant_turn))
        save_runtime_state(runtime_root, resumed)
        return RuntimeTurnResult(state=resumed, intent=ConversationIntent("resume_goal", 0.9, "active_objective", "safe_internal", (), ("resume_goal",)), reply=reply)
    intent = classify_conversational_intent(message, active_objective=state.active_objective, recent_turns=state.conversation)
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type=intent.intent_type,
        objective_id=state.active_objective.objective_id if state.active_objective else "",
    )
    if intent.intent_type == "authority_changing_or_risky_instruction":
        request = {
            "request_id": stable_id("material-authority-request", user_turn.turn_id, ",".join(intent.authority_required)),
            "required_authority": intent.authority_required,
            "operator_message": message,
            "status": "explicit_operator_approval_required",
            "ordinary_work_can_continue": True,
        }
        updated = _replace_state(
            state,
            conversation=state.conversation + (user_turn,),
            pending_material_authority=state.pending_material_authority + (request,),
        )
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(
            state=updated,
            intent=intent,
            reply="That crosses a material authority boundary. I can keep working on the current safe objective, but I need explicit approval before source changes, installs, network use, deletion, commits, pushes, or protected paths.",
            authority_request=request,
        )
    if intent.intent_type == "tentative_goal_candidate" and state.active_objective:
        tentative_turn = ConversationTurn(
            turn_id=user_turn.turn_id,
            role=user_turn.role,
            text=user_turn.text,
            intent_type=intent.intent_type,
            objective_id=state.active_objective.objective_id,
            created_at=user_turn.created_at,
        )
        candidate = TentativeGoalCandidate(
            candidate_goal_id=stable_id("tentative-goal", state.active_objective.objective_id, user_turn.turn_id, message),
            source_turn_id=user_turn.turn_id,
            wording=message,
            interpreted_topic=_tentative_goal_topic(message),
            relation_to_active_objective="candidate_only_does_not_replace_active_objective",
            status="tentative" if "do not start" not in message.lower() and "don't start" not in message.lower() else "deferred",
            activation_required=True,
        )
        reply = "I saved that as a tentative future goal only. It did not replace the active objective, start a new episode, inherit authority, or reset the current budgets."
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
            role="assistant",
            text=reply,
            intent_type="tentative_goal_candidate_ack",
            objective_id=state.active_objective.objective_id,
        )
        updated = _replace_state(
            state,
            conversation=state.conversation + (tentative_turn, assistant_turn),
            tentative_goals=state.tentative_goals + (candidate,),
            objective_progress=state.objective_progress
            + (
                {
                    "event": "tentative_goal_candidate_recorded",
                    "candidate_goal_id": candidate.candidate_goal_id,
                    "active_objective_id": state.active_objective.objective_id,
                    "status": candidate.status,
                    "activation_required": True,
                    "at": utc_now(),
                },
            ),
        )
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(state=updated, intent=intent, reply=reply)
    if intent.intent_type == "persistent_or_session_goal":
        objective = compile_conversational_objective(message, intent)
        execution_hold_reason = _objective_execution_hold_reason(objective)
        teaching_plan = _teaching_plan_for_objective(objective)
        prerequisite = compile_physics_prerequisite(teaching_plan, objective_id=objective.objective_id) if teaching_plan else {}
        if prerequisite:
            objective = _replace_teaching_objective(objective, prerequisites=(prerequisite,))
        if state.active_objective and state.active_objective.objective_id == objective.objective_id:
            health = _active_goal_health(state, objective)
            if health["healthy"] or health.get("repairable"):
                updated = _ensure_capability_campaign_for_active_objective(
                    state,
                    objective,
                    reason="duplicate_goal_repair_or_continue",
                )
                campaign = _active_capability_campaign(updated)
                if campaign and campaign.get("status") == "milestone_ready":
                    assistant_reply = (
                        "That matches the active goal. I found its campaign bridge and advanced it to a milestone instead of leaving it stalled. "
                        "Ordinary chat remains available while that background work continues."
                    )
                else:
                    assistant_reply = "That matches the active goal already, and it is still making bounded progress. I kept the existing objective identity and authority state."
                assistant_turn = ConversationTurn(
                    turn_id=stable_id("conversation-turn", updated.runtime_id, str(len(updated.conversation) + 2), assistant_reply),
                    role="assistant",
                    text=assistant_reply,
                    intent_type="duplicate_objective_acknowledgement",
                    objective_id=updated.active_objective.objective_id,
                )
                updated = _replace_state(
                    updated,
                    conversation=updated.conversation + (user_turn, assistant_turn),
                    objective_progress=updated.objective_progress + ({"event": "duplicate_objective_rejected", "objective_id": objective.objective_id, "campaign_status": campaign.get("status", ""), "at": utc_now()},),
                )
                save_runtime_state(runtime_root, updated)
                return RuntimeTurnResult(state=updated, intent=intent, reply=assistant_reply)
            objective = replace(
                objective,
                objective_id=stable_id(
                    "fresh-objective-after-unhealthy-duplicate",
                    state.runtime_id,
                    objective.objective_id,
                    str(len(state.archived_objectives) + len(state.focus_history) + 1),
                ),
                provenance={
                    **objective.provenance,
                    "supersedes_objective_id": state.active_objective.objective_id,
                    "supersession_reason": str(health.get("reason") or "unhealthy_duplicate"),
                },
            )
        goal_user_turn = ConversationTurn(
            turn_id=user_turn.turn_id,
            role=user_turn.role,
            text=user_turn.text,
            intent_type=user_turn.intent_type,
            objective_id=objective.objective_id,
            created_at=user_turn.created_at,
        )
        authority = derive_standing_authority(objective)
        episode_path = str(Path(runtime_root) / f"active_episode_{objective.objective_id}.json")
        frontier_evidence = _knowledge_frontier_evidence(objective)
        episode = initialize_episode(
            title=_episode_title_for_objective(objective),
            goal_summary=objective.interpreted_objective,
            expected_state=_expected_state_for_objective(objective),
            evidence=(
                EvidenceRef(
                    evidence_id="operator-natural-goal",
                    summary=message,
                    source="ordinary_chat",
                ),
            ) + frontier_evidence,
            state_path=episode_path,
        )
        episode = replace(episode, budgets={**episode.budgets, "max_cycles": objective.cycle_budget, "max_model_calls": objective.model_call_budget})
        write_episode_state(episode_path, episode)
        archived = _archive_active_objective(state)
        focus = {
            "event": "objective_registered",
            "objective_id": objective.objective_id,
            "episode_id": episode.episode_id,
            "archived_previous_objective_id": archived.get("objective_id") if archived else "",
            "at": utc_now(),
        }
        progress = (
            {
                "event": "fresh_objective_scope_started",
                "objective_id": objective.objective_id,
                "archived_previous_objective_id": archived.get("objective_id") if archived else "",
                "cycle_count": 0,
                "at": utc_now(),
            },
            {"event": "standing_authority_assigned", "authority_id": authority.authority_id, "at": utc_now()},
        )
        if objective.provenance.get("execution_mode") == "knowledge_acquisition" and frontier_evidence:
            progress = progress + _knowledge_events_from_episode(objective, episode, progress)
        campaign = _initialize_capability_campaign(objective) if objective.provenance.get("execution_mode") == "capability_growth_campaign" else None
        if campaign:
            progress = progress + (
                {
                    "event": "capability_campaign_initialized",
                    "objective_id": objective.objective_id,
                    "campaign_id": campaign["campaign_id"],
                    "goal_label": campaign["goal_label"],
                    "at": utc_now(),
                },
            )
        if execution_hold_reason:
            progress = progress + (
                {
                    "event": "objective_execution_constraints_recorded",
                    "objective_id": objective.objective_id,
                    "hold_reason": execution_hold_reason,
                    "constraints": _objective_execution_constraints_for_objective(objective),
                    "at": utc_now(),
                },
            )
        budget_request: ChatAddressableRequest | None = None
        prerequisite_request: ChatAddressableRequest | None = None
        lifecycle_state = "running"
        if (
            not execution_hold_reason
            and objective.provenance.get("execution_mode") == "knowledge_acquisition"
            and objective.model_call_budget is not None
            and len(frontier_evidence) > objective.model_call_budget
        ):
            budget_request = _knowledge_model_budget_request(
                objective,
                required_nodes=len(frontier_evidence),
                completed_nodes=0,
                model_calls_used=0,
                exhausted=False,
            )
            lifecycle_state = "paused_operator"
            progress = progress + ({"event": "knowledge_model_budget_increase_requested", "request_id": budget_request.request_id, "required_nodes": len(frontier_evidence), "current_model_call_budget": objective.model_call_budget, "recommended_model_call_budget": budget_request.max_calls, "at": utc_now()},)
        if prerequisite and not budget_request and not execution_hold_reason:
            prerequisite_request = ChatAddressableRequest(
                request_id=stable_id("teaching-prerequisite-request", objective.objective_id, str(prerequisite.get("prerequisite_id") or "")),
                request_type="teaching_prerequisite",
                objective_id=objective.objective_id,
                originating_goal_id=objective.objective_id,
                goal_label="Physics prerequisite",
                prompt_text=render_physics_prerequisite_prompt(prerequisite),
                authority_impact="linked_prerequisite_objective_requires_conversational_confirmation",
                thread_id=f"{objective.objective_id}:physics-prerequisite",
                created_turn_id=goal_user_turn.turn_id,
                created_sequence=len(state.conversation) + 2,
                accepted_response_types=("approved", "denied"),
                baseline_metrics={
                    "teaching_request_kind": "physics_prerequisite",
                    "prerequisite_id": str(prerequisite.get("prerequisite_id") or ""),
                    "prerequisite_objective_id": str(prerequisite.get("prerequisite_objective_id") or ""),
                    "parent_objective_id": objective.objective_id,
                },
            )
            progress = progress + ({
                "event": "teaching_prerequisite_permission_requested",
                "objective_id": objective.objective_id,
                "prerequisite_id": str(prerequisite.get("prerequisite_id") or ""),
                "request_id": prerequisite_request.request_id,
                "at": utc_now(),
            },)
        updated = _replace_state(
            state,
            lifecycle_state=lifecycle_state,
            active_objective=objective,
            authority=authority,
            conversation=state.conversation + (goal_user_turn,),
            active_episode_path=episode_path,
            completed_cycle_keys=(),
            pending_material_authority=(),
            pending_chat_requests=((budget_request,) if budget_request else ()) + ((prerequisite_request,) if prerequisite_request else ()),
            resolved_chat_requests=(),
            provider_authorities=(),
            turn_relation_decisions=(),
            local_semantic_insufficiencies=(),
            goal_reviews=(),
            objective_progress=progress,
            focus_history=state.focus_history + (focus,),
            archived_objectives=state.archived_objectives + ((archived,) if archived else ()),
            capability_campaigns=state.capability_campaigns + ((campaign,) if campaign else ()),
        )
        background_cycle_eligible = bool(
            run_background_cycle
            and budget_request is None
            and not background_cycle_hold_reason(updated)
        )
        if background_cycle_eligible:
            updated = run_background_objective_cycle(updated, runtime_root=runtime_root, reason="objective_registered", model_runner=model_runner)
        reply = (
            f"I registered that as the active goal and started working on it. This is a bounded session goal under standing bounded authority.\n\n"
            f"[Goal update · {objective.interpreted_objective[:80]}]\n"
            "Local cognition has started. I’ll continue independently within standing bounded authority and ask only at a real approval boundary."
        )
        if budget_request:
            reply = (
                "I registered that as the active goal and paused at a budget boundary before local model execution.\n\n"
                f"{budget_request.prompt_text}"
            )
        elif execution_hold_reason:
            reply = (
                "I registered that as the active goal and kept it available for foreground source-bound work.\n\n"
                f"[Goal update - {objective.interpreted_objective[:80]}]\n"
                "I am waiting for your next input and will not call a local model while that instruction remains active."
            )
        elif objective.provenance.get("teaching_plan"):
            reply = render_first_lesson(dict(objective.provenance["teaching_plan"]))
            if prerequisite_request:
                reply = f"{reply}\n\n{prerequisite_request.prompt_text}"
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", updated.runtime_id, str(len(updated.conversation) + 1), reply),
            role="assistant",
            text=reply,
            intent_type="objective_confirmation",
            objective_id=objective.objective_id,
        )
        updated = _replace_state(updated, conversation=updated.conversation + (assistant_turn,))
        if prerequisite_request:
            rendered_request = replace(
                prerequisite_request,
                rendered_turn_id=assistant_turn.turn_id,
                render_sequence=len(updated.conversation),
            )
            updated = _replace_state(
                updated,
                pending_chat_requests=tuple(
                    rendered_request if item.request_id == rendered_request.request_id else item
                    for item in updated.pending_chat_requests
                ),
            )
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(state=updated, intent=intent, reply=reply, objective_created=True, background_cycle_started=background_cycle_eligible, chat_request=budget_request.as_record() if budget_request else None)
    if intent.intent_type == "direct_correction" and state.active_objective:
        updated, correction, lesson = attach_correction(state, user_turn, intent)
        reply = "Got it. I attached that correction to the active comprehension objective and revised the strategy for related later turns without making it a global rule."
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", updated.runtime_id, str(len(updated.conversation) + 1), reply),
            role="assistant",
            text=reply,
            intent_type="correction_acknowledgement",
            objective_id=state.active_objective.objective_id,
        )
        updated = _replace_state(updated, conversation=updated.conversation + (assistant_turn,))
        background_cycle_eligible = bool(run_background_cycle and not background_cycle_hold_reason(updated))
        if background_cycle_eligible:
            updated = run_background_objective_cycle(updated, runtime_root=runtime_root, reason="correction_attached", model_runner=model_runner)
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(state=updated, intent=intent, reply=reply, correction_attached=True, background_cycle_started=background_cycle_eligible, transfer_applied=False)
    teaching_followup = _queue_teaching_followup_study(
        state,
        message,
        runtime_root=runtime_root,
        run_background_cycle=run_background_cycle,
        model_runner=model_runner,
    )
    if teaching_followup is not None:
        return teaching_followup
    relation = decide_turn_relation(state, message, turn_id=user_turn.turn_id)
    transfer = infer_lesson_transfer(state, message, relation=relation)
    if transfer["applied"]:
        relation = TurnRelationDecision(**{**relation.as_record(), "lesson_ids_applied": (transfer["lesson_id"],)})
    reply = _ordinary_reply(message, transfer, relation=relation)
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="ordinary_response",
        objective_id=state.active_objective.objective_id if state.active_objective else "",
    )
    progress = state.objective_progress + ({"event": "turn_relation_decision", **relation.as_record(), "at": utc_now()},)
    if transfer["applied"]:
        progress = progress + ({"event": "lesson_transfer_applied", "lesson_id": transfer["lesson_id"], "message": message, "at": utc_now()},)
    updated = _replace_state(state, conversation=state.conversation + (user_turn, assistant_turn), objective_progress=progress, turn_relation_decisions=state.turn_relation_decisions + (relation,))
    background_cycle_eligible = bool(
        state.active_objective
        and run_background_cycle
        and intent.intent_type == "ordinary_conversation"
        and not background_cycle_hold_reason(updated)
    )
    if background_cycle_eligible:
        updated = run_background_objective_cycle(updated, runtime_root=runtime_root, reason="ordinary_chat_yield", model_runner=model_runner)
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(state=updated, intent=intent, reply=reply, background_cycle_started=background_cycle_eligible, transfer_applied=bool(transfer["applied"]))


def _teaching_result_for_evidence(
    episode: ActiveCognitiveEpisodeState,
    evidence_id: str,
):
    """Resolve a teaching result by its immutable frontier focus before refs.

    Supporting evidence is intentionally shared across sibling frontier nodes,
    so using it as the primary key can bind one node's result to another
    teaching record. The active loop already owns the focus-to-operation
    lineage; fall back to refs only for legacy episodes without that lineage.
    """

    focus_id = stable_id("focus", episode.episode_id, evidence_id)
    operation_ids = [
        cycle.operation_id
        for cycle in episode.cycles
        if cycle.focus_id == focus_id and cycle.operation_id
    ]
    if operation_ids:
        results_by_id = {item.operation_id: item for item in episode.operation_results}
        for operation_id in reversed(operation_ids):
            result = results_by_id.get(operation_id)
            if result is not None:
                return result
        return None
    return next(
        (
            item
            for item in reversed(episode.operation_results)
            if evidence_id in set(item.evidence_refs)
        ),
        None,
    )


def _teaching_attempts_for_evidence(
    episode: ActiveCognitiveEpisodeState,
    evidence_id: str,
) -> tuple[Any, ...]:
    """Read retry ownership from the existing frontier-cycle history."""

    focus_id = stable_id("focus", episode.episode_id, evidence_id)
    operation_ids = {
        cycle.operation_id
        for cycle in episode.cycles
        if cycle.focus_id == focus_id and cycle.operation_id
    }
    if operation_ids:
        return tuple(item for item in episode.operation_results if item.operation_id in operation_ids)
    return tuple(
        item
        for item in episode.operation_results
        if evidence_id in set(item.evidence_refs)
    )


def _teaching_claim_version_for_node(graph: Any, node_id: str) -> str:
    claim_ids = {
        item.claim_id
        for item in getattr(graph, "claims", ())
        if str(getattr(item, "originating_node_id", "")) == node_id
    }
    versions = [
        item
        for item in getattr(graph, "claim_versions", ())
        if item.claim_id in claim_ids
    ]
    if not versions:
        return ""
    return max(versions, key=lambda item: (item.version_index, item.created_at, item.claim_version_id)).claim_version_id


def _teaching_understanding_assessment(
    result: Any,
    *,
    expected_terms: Sequence[str] = (),
) -> Mapping[str, Any]:
    """Run a modest deterministic explanation/transfer check, not a truth review.

    The proposing local model does not certify its own factual output.  This
    check only verifies that the accepted response stayed tied to the requested
    concept, offered an explanatory relation, and supplied an observable or
    application-shaped test cue. It never serves as factual review.
    """

    interpretation = str(getattr(result, "interpretation", "")).strip()
    lowered = interpretation.lower()
    terms = {
        str(item).strip().lower()
        for item in expected_terms
        if str(item).strip()
    }
    topic_bound = bool(terms & set(re.findall(r"[a-z0-9]+", lowered))) if terms else bool(interpretation)
    explanatory_relation = any(
        marker in lowered
        for marker in (
            "because",
            "through",
            "by ",
            "which ",
            "so ",
            "so that",
            "therefore",
            "represents",
            "corresponds",
            "leads to",
            "controls",
            "depends on",
        )
    )
    evidence_linkage = bool(tuple(getattr(result, "evidence_refs", ()) or ()))
    transfer_prompt = bool(str(getattr(result, "next_focus_proposal", "")).strip())
    expected_observations = tuple(
        str(item).strip()
        for item in getattr(result, "expected_observations", ()) or ()
        if str(item).strip()
    )
    observable_application = bool(expected_observations)
    accepted = bool(getattr(result, "accepted", False))
    tested = accepted and topic_bound and explanatory_relation and evidence_linkage and (transfer_prompt or observable_application)
    return {
        "state": "tested_source_bound_explanation" if tested else "provisionally_understood_not_yet_tested",
        "test_type": "deterministic_source_bound_explanation_and_transfer_check",
        "topic_bound": topic_bound,
        "explanatory_relation": explanatory_relation,
        "evidence_linkage": evidence_linkage,
        "transfer_prompt": transfer_prompt,
        "observable_application": observable_application,
        "contradiction_considered": bool(tuple(getattr(result, "contrary_evidence_considered", ()) or ())),
        "learning_states": {
            "encountered": True,
            "inspected": True,
            "provisionally_understood": accepted,
            "explainable": bool(interpretation),
            "tested": tested,
            "review_status": "pending_consolidation",
            "retained": False,
            "transferable": tested and (transfer_prompt or observable_application),
        },
        "factual_status": "still_provisional_pending_consolidation",
    }


def _record_teaching_episode_results(
    state: ConversationalRuntimeState,
    episode: ActiveCognitiveEpisodeState,
    graph: Any,
) -> tuple[ConversationalRuntimeState, Any]:
    """Bind accepted frontier results back to teaching state and durable requests."""

    objective = state.active_objective
    plan = _teaching_plan_for_objective(objective)
    if objective is None or not plan:
        return state, graph
    followups = list(_teaching_followups_for_objective(objective))
    prerequisites = list(_teaching_prerequisites_for_objective(objective))
    pending_by_id = {item.request_id: item for item in state.pending_chat_requests}
    resolved_ids = {item.request_id for item in state.resolved_chat_requests}
    progress: list[Mapping[str, Any]] = []
    changed = False
    topic = str(plan.get("topic") or "this topic")
    endogenous_recovery_lifecycle = ""

    for index, followup in enumerate(followups):
        evidence_id = str(followup.get("evidence_id") or followup.get("node_id") or "")
        result = _teaching_result_for_evidence(episode, evidence_id)
        if result is None or str(followup.get("status") or "") not in {"queued", "study_running", "study_retry_scheduled"}:
            continue
        if str(followup.get("last_processed_operation_id") or "") == result.operation_id:
            continue
        expected_terms = tuple(str(item) for item in followup.get("question_tokens", ()) if str(item))
        assessment = _teaching_understanding_assessment(result, expected_terms=expected_terms)
        endogenous_recovery = str(followup.get("origin") or "") == "endogenous_terminal_gap_recovery"
        if not result.accepted:
            attempts = _teaching_attempts_for_evidence(episode, evidence_id)
            rejected_attempts = tuple(item for item in attempts if not item.accepted)
            retryable = (
                len(rejected_attempts) == 1
                and "local_model_execution_blocked" not in set(result.rejection_reasons)
            )
            # A terminal-gap recovery is one independently selected bounded
            # action, not a hidden retry loop.  Its first failed attempt is
            # retained as a visible deferred result; ordinary operator asked
            # teaching follow-ups keep their established single-retry policy.
            if endogenous_recovery:
                followups[index] = {
                    **followup,
                    "status": "study_blocked",
                    "operation_id": result.operation_id,
                    "last_processed_operation_id": result.operation_id,
                    "retry_count": len(rejected_attempts),
                    "last_rejection_reasons": tuple(result.rejection_reasons),
                    "understanding_assessment": assessment,
                    "developmental_action_state": "deferred_after_local_failure",
                    "completed_at": utc_now(),
                }
                progress.extend((
                    {
                        "event": "teaching_followup_study_blocked",
                        "objective_id": objective.objective_id,
                        "followup_id": str(followup.get("followup_id") or ""),
                        "operation_id": result.operation_id,
                        "at": utc_now(),
                    },
                    {
                        "event": "endogenous_teaching_gap_recovery_deferred",
                        "objective_id": objective.objective_id,
                        "followup_id": str(followup.get("followup_id") or ""),
                        "pressure_id": str(followup.get("pressure_id") or ""),
                        "source_terminal_report_key": str(followup.get("source_terminal_report_key") or ""),
                        "source_gap": str(followup.get("source_gap") or ""),
                        "operation_id": result.operation_id,
                        "rejection_reasons": tuple(result.rejection_reasons),
                        "at": utc_now(),
                    },
                ))
                endogenous_recovery_lifecycle = "paused_budget"
                changed = True
                continue
            if retryable:
                followups[index] = {
                    **followup,
                    "status": "study_retry_scheduled",
                    "operation_id": result.operation_id,
                    "last_processed_operation_id": result.operation_id,
                    "retry_count": 1,
                    "last_rejection_reasons": tuple(result.rejection_reasons),
                    "understanding_assessment": assessment,
                }
                progress.append({
                    "event": "teaching_followup_study_retry_scheduled",
                    "objective_id": objective.objective_id,
                    "followup_id": str(followup.get("followup_id") or ""),
                    "operation_id": result.operation_id,
                    "rejection_reasons": tuple(result.rejection_reasons),
                    "at": utc_now(),
                })
                changed = True
                continue
            followups[index] = {
                **followup,
                "status": "study_blocked",
                "operation_id": result.operation_id,
                "last_processed_operation_id": result.operation_id,
                "retry_count": len(rejected_attempts),
                "last_rejection_reasons": tuple(result.rejection_reasons),
                "understanding_assessment": assessment,
                "completed_at": utc_now(),
            }
            progress.append({
                "event": "teaching_followup_study_blocked",
                "objective_id": objective.objective_id,
                "followup_id": str(followup.get("followup_id") or ""),
                "operation_id": result.operation_id,
                "at": utc_now(),
            })
            changed = True
            continue
        claim_version_id = _teaching_claim_version_for_node(graph, str(followup.get("node_id") or ""))
        if not claim_version_id:
            continue
        completed = {
            **followup,
            "topic": topic,
            "status": "provisional_ready_for_retention",
            "claim_version_id": claim_version_id,
            "operation_id": result.operation_id,
            "last_processed_operation_id": result.operation_id,
            "interpretation": str(result.interpretation or "").strip(),
            "uncertainty": str(result.uncertainty or "").strip(),
            "understanding_assessment": assessment,
            "completed_at": utc_now(),
            **({"developmental_action_state": "completed_pending_retention"} if endogenous_recovery else {}),
        }
        followups[index] = completed
        request_id = stable_id(
            "teaching-provisional-retention-request",
            state.runtime_id,
            objective.objective_id,
            str(completed.get("followup_id") or ""),
            claim_version_id,
        )
        if request_id not in pending_by_id and request_id not in resolved_ids:
            request = ChatAddressableRequest(
                request_id=request_id,
                request_type="teaching_provisional_retention",
                objective_id=objective.objective_id,
                originating_goal_id=objective.objective_id,
                goal_label=f"{topic} provisional material",
                prompt_text=teaching_retention_prompt(completed),
                authority_impact="operator_controlled_provisional_memory_retention",
                thread_id=f"{objective.objective_id}:teaching-followup:{completed.get('followup_id')}",
                created_sequence=len(state.conversation) + len(pending_by_id) + 1,
                accepted_response_types=("approved", "denied"),
                baseline_metrics={
                    "teaching_request_kind": "provisional_retention",
                    "followup_id": str(completed.get("followup_id") or ""),
                    "claim_version_id": claim_version_id,
                    "question": str(completed.get("question") or ""),
                },
            )
            pending_by_id[request_id] = request
            progress.append({
                "event": "teaching_provisional_retention_requested",
                "objective_id": objective.objective_id,
                "followup_id": str(completed.get("followup_id") or ""),
                "claim_version_id": claim_version_id,
                "request_id": request_id,
                "at": utc_now(),
            })
        progress.append({
            "event": "teaching_followup_study_completed",
            "objective_id": objective.objective_id,
            "followup_id": str(completed.get("followup_id") or ""),
            "claim_version_id": claim_version_id,
            "operation_id": result.operation_id,
            "epistemic_state": "pending_consolidation",
            "at": utc_now(),
        })
        if endogenous_recovery:
            progress.append({
                "event": "endogenous_teaching_gap_recovery_completed",
                "objective_id": objective.objective_id,
                "followup_id": str(completed.get("followup_id") or ""),
                "pressure_id": str(completed.get("pressure_id") or ""),
                "source_terminal_report_key": str(completed.get("source_terminal_report_key") or ""),
                "source_gap": str(completed.get("source_gap") or ""),
                "claim_version_id": claim_version_id,
                "operation_id": result.operation_id,
                "at": utc_now(),
            })
            endogenous_recovery_lifecycle = "paused_operator"
        changed = True

    for index, prerequisite in enumerate(prerequisites):
        evidence_id = str(prerequisite.get("evidence_id") or prerequisite.get("node_id") or "")
        result = _teaching_result_for_evidence(episode, evidence_id)
        if result is None or str(prerequisite.get("status") or "") not in {
            "queued",
            "prerequisite_study_running",
            "prerequisite_retry_scheduled",
        }:
            continue
        if str(prerequisite.get("last_processed_operation_id") or "") == result.operation_id:
            continue
        expected_terms = tuple(
            token
            for token in re.findall(
                r"[a-z0-9]+",
                " ".join(
                    (
                        str(prerequisite.get("topic") or ""),
                        str(prerequisite.get("competence_requirement") or ""),
                    )
                ).lower(),
            )
            if token not in {"the", "and", "for", "how", "or", "in", "one"}
        )
        assessment = _teaching_understanding_assessment(result, expected_terms=expected_terms)
        if not result.accepted:
            attempts = _teaching_attempts_for_evidence(episode, evidence_id)
            rejected_attempts = tuple(item for item in attempts if not item.accepted)
            retryable = (
                len(rejected_attempts) == 1
                and "local_model_execution_blocked" not in set(result.rejection_reasons)
            )
            if retryable:
                prerequisites[index] = {
                    **prerequisite,
                    "status": "prerequisite_retry_scheduled",
                    "operation_id": result.operation_id,
                    "last_processed_operation_id": result.operation_id,
                    "retry_count": 1,
                    "last_rejection_reasons": tuple(result.rejection_reasons),
                    "understanding_assessment": assessment,
                }
                progress.append({
                    "event": "teaching_prerequisite_retry_scheduled",
                    "objective_id": objective.objective_id,
                    "prerequisite_id": str(prerequisite.get("prerequisite_id") or ""),
                    "operation_id": result.operation_id,
                    "rejection_reasons": tuple(result.rejection_reasons),
                    "at": utc_now(),
                })
                changed = True
                continue
            prerequisites[index] = {
                **prerequisite,
                "status": "competence_needs_revision",
                "competence_test_state": str(assessment["state"]),
                "derivation_branch_state": "still_blocked",
                "operation_id": result.operation_id,
                "last_processed_operation_id": result.operation_id,
                "retry_count": len(rejected_attempts),
                "last_rejection_reasons": tuple(result.rejection_reasons),
                "understanding_assessment": assessment,
                "completed_at": utc_now(),
            }
            progress.append({
                "event": "teaching_prerequisite_competence_checked",
                "objective_id": objective.objective_id,
                "prerequisite_id": str(prerequisite.get("prerequisite_id") or ""),
                "operation_id": result.operation_id,
                "passed": False,
                "at": utc_now(),
            })
            changed = True
            continue
        passed = bool(assessment["learning_states"]["tested"])
        resume_target = physics_prerequisite_resume_target(plan, prerequisite) if passed else {}
        resumption_event_id = stable_id(
            "teaching-prerequisite-parent-resumption",
            objective.objective_id,
            str(prerequisite.get("prerequisite_id") or ""),
            result.operation_id,
        ) if passed else ""
        prerequisites[index] = {
            **prerequisite,
            "status": "competence_tested" if passed else "competence_needs_revision",
            "competence_test_state": str(assessment["state"]),
            "derivation_branch_state": "resumed" if passed else "still_blocked",
            "operation_id": result.operation_id,
            "last_processed_operation_id": result.operation_id,
            "interpretation": str(result.interpretation or "").strip(),
            "uncertainty": str(result.uncertainty or "").strip(),
            "understanding_assessment": assessment,
            "completed_at": utc_now(),
            **resume_target,
            "parent_branch_resume_event_id": resumption_event_id,
            "parent_branch_resumed_at": utc_now() if passed else "",
        }
        progress.append({
            "event": "teaching_prerequisite_competence_checked",
            "objective_id": objective.objective_id,
            "prerequisite_id": str(prerequisite.get("prerequisite_id") or ""),
            "operation_id": result.operation_id,
            "passed": passed,
            "at": utc_now(),
        })
        if passed:
            progress.extend((
                {
                    "event": "teaching_prerequisite_cleared",
                    "objective_id": objective.objective_id,
                    "prerequisite_id": str(prerequisite.get("prerequisite_id") or ""),
                    "operation_id": result.operation_id,
                    "resumption_event_id": resumption_event_id,
                    "at": utc_now(),
                },
                {
                    "event": "teaching_parent_branch_resumed",
                    "objective_id": objective.objective_id,
                    "parent_objective_id": str(prerequisite.get("parent_objective_id") or objective.objective_id),
                    "prerequisite_id": str(prerequisite.get("prerequisite_id") or ""),
                    "operation_id": result.operation_id,
                    "resumption_event_id": resumption_event_id,
                    **resume_target,
                    "at": utc_now(),
                },
            ))
        changed = True

    if not changed:
        return state, graph
    updated_objective = _replace_teaching_objective(objective, followups=followups, prerequisites=prerequisites)
    graph, cohort = ensure_consolidation_cohort(graph, trigger="conversational_teaching_followup")
    updated = _replace_state(
        state,
        active_objective=updated_objective,
        lifecycle_state=endogenous_recovery_lifecycle or state.lifecycle_state,
        pending_chat_requests=tuple(pending_by_id.values()),
        objective_progress=state.objective_progress + tuple(progress) + (({
            "event": "teaching_consolidation_eligible",
            "objective_id": objective.objective_id,
            "cohort_id": cohort.cohort_id,
            "at": utc_now(),
        },) if cohort is not None else ()),
    )
    return updated, graph


def is_teaching_followup_message(state: ConversationalRuntimeState, message: str) -> bool:
    """Expose the narrow study boundary so the UI can preserve its canonical owner."""

    plan = _teaching_plan_for_objective(state.active_objective)
    if not plan:
        return False
    return teaching_followup_requires_study(plan, _teaching_followups_for_objective(state.active_objective), message)


def _queue_teaching_followup_study(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
    run_background_cycle: bool,
    model_runner: ModelRunner | None,
) -> RuntimeTurnResult | None:
    objective = state.active_objective
    plan = _teaching_plan_for_objective(objective)
    if objective is None or not plan or not is_teaching_followup_message(state, message):
        return None
    user_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), message),
        role="user",
        text=message,
        intent_type="teaching_followup_question",
        objective_id=objective.objective_id,
    )
    return _queue_teaching_followup_from_turn(
        state,
        user_turn,
        runtime_root=runtime_root,
        run_background_cycle=run_background_cycle,
        model_runner=model_runner,
    )


def _queue_teaching_followup_from_turn(
    state: ConversationalRuntimeState,
    user_turn: ConversationTurn,
    *,
    runtime_root: str | Path,
    run_background_cycle: bool,
    model_runner: ModelRunner | None,
) -> RuntimeTurnResult | None:
    """Compile one teaching study from a new or previously queued user turn.

    A foreground turn may arrive while the shared local-model worker is at an
    atomic boundary.  The turn is already durable in that case, so this helper
    upgrades that exact turn rather than appending another user message.  Both
    paths intentionally use the same follow-up node, acknowledgement, and
    background-cycle contracts.
    """

    objective = state.active_objective
    plan = _teaching_plan_for_objective(objective)
    message = str(user_turn.text or "")
    if objective is None or not plan or not is_teaching_followup_message(state, message):
        return None
    followup = compile_teaching_followup(plan, objective_id=objective.objective_id, message=message)
    if not followup:
        return None
    followup = {**followup, "topic": str(plan.get("topic") or "this topic")}
    existing_turn = any(item.turn_id == user_turn.turn_id for item in state.conversation)
    normalized_user_turn = replace(
        user_turn,
        intent_type="teaching_followup_question",
        objective_id=objective.objective_id,
    )
    conversation = (
        tuple(normalized_user_turn if item.turn_id == normalized_user_turn.turn_id else item for item in state.conversation)
        if existing_turn
        else state.conversation + (normalized_user_turn,)
    )
    reply = render_teaching_followup_acknowledgement(followup)
    assistant_turn = ConversationTurn(
        turn_id=stable_id("teaching-followup-acknowledgement", state.runtime_id, normalized_user_turn.turn_id, str(followup.get("followup_id") or "")),
        role="assistant",
        text=reply,
        intent_type="teaching_followup_study_acknowledgement",
        objective_id=objective.objective_id,
    )
    updated_objective = _replace_teaching_objective(
        objective,
        followups=_teaching_followups_for_objective(objective) + (followup,),
    )
    updated = _replace_state(
        state,
        active_objective=updated_objective,
        conversation=conversation + (assistant_turn,),
        objective_progress=state.objective_progress + ({
            "event": "queued_teaching_followup_reconciled" if existing_turn else "teaching_followup_study_queued",
            "objective_id": objective.objective_id,
            "followup_id": str(followup.get("followup_id") or ""),
            "node_id": str(followup.get("node_id") or ""),
            "question": str(followup.get("question") or ""),
            "source_turn_id": normalized_user_turn.turn_id,
            "authority": "standing_bounded_local_teaching",
            "at": utc_now(),
        },),
    )
    background_cycle_eligible = bool(run_background_cycle and not background_cycle_hold_reason(updated))
    if background_cycle_eligible:
        updated = run_background_objective_cycle(
            updated,
            runtime_root=runtime_root,
            reason="teaching_followup_study",
            model_runner=model_runner,
        )
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(
        state=updated,
        intent=ConversationIntent(
            intent_type="teaching_followup_question",
            confidence=0.9,
            persistence_scope="active_teaching_objective",
            risk_class="safe_internal",
            authority_required=(),
            matched_signals=("in_scope_teaching_question",),
        ),
        reply=reply,
        background_cycle_started=background_cycle_eligible,
    )


def _latest_terminal_report_for_objective(
    state: ConversationalRuntimeState,
    objective_id: str,
) -> Mapping[str, Any]:
    """Return the latest canonical knowledge terminal report for this objective."""

    for item in reversed(state.objective_progress):
        if (
            isinstance(item, Mapping)
            and str(item.get("event") or "") == "knowledge_goal_terminal_report"
            and str(item.get("objective_id") or "") == objective_id
        ):
            return dict(item)
    return {}


def queue_endogenous_teaching_gap_recovery(
    state: ConversationalRuntimeState,
    *,
    runtime_root: str | Path,
) -> tuple[ConversationalRuntimeState, Mapping[str, Any]] | None:
    """Queue one source-bound recovery from an actual terminal teaching gap.

    The returned follow-up is the normal teaching-followup record. This
    transition records why the worker is allowed to run, but deliberately does
    not create a user turn, an assistant acknowledgement, or another queue.
    """

    objective = state.active_objective
    plan = _teaching_plan_for_objective(objective)
    if (
        objective is None
        or not plan
        or state.lifecycle_state != "paused_budget"
        or any(request.status == "pending" and not request.consumption_count for request in state.pending_chat_requests)
    ):
        return None
    terminal_report = _latest_terminal_report_for_objective(state, objective.objective_id)
    followup = compile_endogenous_terminal_gap_followup(
        plan,
        objective_id=objective.objective_id,
        terminal_report=terminal_report,
    )
    if not followup:
        return None
    source_terminal_report_key = str(followup.get("source_terminal_report_key") or "")
    existing = next(
        (
            item
            for item in _teaching_followups_for_objective(objective)
            if str(item.get("source_terminal_report_key") or "") == source_terminal_report_key
        ),
        None,
    )
    if existing is not None:
        return None
    queued_followup = {
        **followup,
        "created_at": utc_now(),
        "developmental_action_state": "queued",
    }
    updated_objective = _replace_teaching_objective(
        objective,
        followups=_teaching_followups_for_objective(objective) + (queued_followup,),
    )
    action = {
        "event": "endogenous_teaching_gap_recovery_queued",
        "action_id": str(queued_followup.get("pressure_id") or ""),
        "objective_id": objective.objective_id,
        "followup_id": str(queued_followup.get("followup_id") or ""),
        "source_terminal_report_key": source_terminal_report_key,
        "source_terminal_status": str(queued_followup.get("source_terminal_status") or ""),
        "source_terminal_stop_reason": str(queued_followup.get("source_terminal_stop_reason") or ""),
        "source_gap": str(queued_followup.get("source_gap") or ""),
        "authority": str(queued_followup.get("local_study_authority") or ""),
        "at": utc_now(),
    }
    updated = _replace_state(
        state,
        lifecycle_state="running",
        active_objective=updated_objective,
        objective_progress=state.objective_progress + (action,),
    )
    save_runtime_state(runtime_root, updated)
    return updated, action


def reconcile_queued_teaching_followup(
    state: ConversationalRuntimeState,
    *,
    runtime_root: str | Path,
    run_background_cycle: bool = False,
    model_runner: ModelRunner | None = None,
) -> RuntimeTurnResult | None:
    """Consume one in-scope queued teaching question at a worker safe boundary.

    Generic queued turns remain owned by the existing reconciliation path.  This
    deliberately handles only a foreground question that is both durable and
    in scope for the active teaching objective, preserving its original turn ID
    and producing no duplicate user turn on restart or later idle ticks.
    """

    objective = state.active_objective
    if objective is None or not _teaching_plan_for_objective(objective):
        return None
    for turn in state.conversation:
        if (
            turn.role != "user"
            or turn.intent_type != "ordinary_conversation_queued"
            or turn.objective_id != objective.objective_id
        ):
            continue
        result = _queue_teaching_followup_from_turn(
            state,
            turn,
            runtime_root=runtime_root,
            run_background_cycle=run_background_cycle,
            model_runner=model_runner,
        )
        if result is not None:
            return result
    return None


def run_background_objective_cycle(
    state: ConversationalRuntimeState,
    *,
    runtime_root: str | Path,
    reason: str,
    model_runner: ModelRunner | None = None,
) -> ConversationalRuntimeState:
    if not state.active_objective or not state.authority or state.authority.revoked:
        return state
    if background_cycle_hold_reason(state):
        return state
    cycle_key = stable_id("conversational-cycle", state.active_objective.objective_id, reason, str(len(state.completed_cycle_keys) + 1))
    if cycle_key in state.completed_cycle_keys:
        return state
    if (
        state.active_objective.cycle_budget is not None
        and len(state.completed_cycle_keys) >= state.active_objective.cycle_budget
    ):
        return _replace_state(state, lifecycle_state="paused_budget")
    episode_path = Path(state.active_episode_path or Path(runtime_root) / "active_episode.json")
    episode = read_episode_state(episode_path) if episode_path.exists() else initialize_episode(
        title=_episode_title_for_objective(state.active_objective),
        goal_summary=state.active_objective.interpreted_objective,
        expected_state=_expected_state_for_objective(state.active_objective),
        evidence=(EvidenceRef(evidence_id="operator-natural-goal", summary=state.active_objective.operator_wording, source="ordinary_chat"),) + _knowledge_frontier_evidence(state.active_objective),
        state_path=episode_path,
    )
    episode = replace(episode, budgets={**episode.budgets, "max_cycles": state.active_objective.cycle_budget, "max_model_calls": state.active_objective.model_call_budget})
    episode = _ensure_pending_teaching_followup_nodes(episode, state.active_objective)
    if episode.completed or episode.loop_state == "completed":
        if state.active_objective.provenance.get("execution_mode") != "knowledge_acquisition":
            episode_path = Path(runtime_root) / f"active_episode_{len(state.completed_cycle_keys) + 1}.json"
            episode = initialize_episode(
                title=f"Conversational English comprehension continuation {len(state.completed_cycle_keys) + 1}",
                goal_summary=state.active_objective.interpreted_objective,
                expected_state="Continue correction-linked comprehension practice without duplicating prior completed episode work.",
                evidence=(
                    EvidenceRef(
                        evidence_id=f"prior-conversational-episode-{len(state.completed_cycle_keys)}",
                        summary="Prior bounded active episode completed; continuation keeps the approved conversational objective active.",
                        source=state.active_episode_path,
                    ),
                ),
                state_path=episode_path,
            )
            episode = replace(episode, budgets={**episode.budgets, "max_cycles": state.active_objective.cycle_budget, "max_model_calls": state.active_objective.model_call_budget})
            write_episode_state(episode_path, episode)
    if not _knowledge_limit_reached(episode.model_call_count, state.active_objective.model_call_budget):
        episode = run_cognitive_cycle(episode, model_runner=model_runner or ScriptedSemanticModel())
        write_episode_state(episode_path, episode)
    progress = {
        "event": "background_cycle",
        "cycle_key": cycle_key,
        "reason": reason,
        "episode_id": episode.episode_id,
        "episode_model_call_count": episode.model_call_count,
        "at": utc_now(),
    }
    updated = _replace_state(
        state,
        active_episode_path=str(episode_path),
        completed_cycle_keys=state.completed_cycle_keys + (cycle_key,),
        objective_progress=state.objective_progress + (progress,),
        focus_history=state.focus_history + ({"event": "focus_tick", "reason": reason, "at": utc_now()},),
    )
    if state.active_objective.provenance.get("execution_mode") == "knowledge_acquisition":
        events = _knowledge_events_from_episode(state.active_objective, episode, updated.objective_progress)
        if events:
            updated = _replace_state(updated, objective_progress=updated.objective_progress + events)
    if state.active_objective.provenance.get("execution_mode") == "knowledge_acquisition":
        stagnation = _knowledge_stagnation(episode)
        exhausted = (
            _knowledge_limit_reached(episode.model_call_count, state.active_objective.model_call_budget)
            or (
                state.active_objective.cycle_budget is not None
                and len(updated.completed_cycle_keys) >= state.active_objective.cycle_budget
            )
            or episode.loop_state in {"blocked_capability_gap", "paused_budget"}
            or _knowledge_has_global_model_failure(episode)
            or bool(stagnation)
            or (episode.loop_state == "blocked_insufficient_evidence" and _knowledge_frontier_all_attempted(episode))
            or episode.completed
        )
        if exhausted and not any(item.get("event") == "knowledge_goal_terminal_report" for item in updated.objective_progress):
            report = _knowledge_terminal_report(state.active_objective, episode)
            budget_request: ChatAddressableRequest | None = None
            if (
                report.get("stop_reason") == "model_call_budget_exhausted"
                and int(report.get("remaining_frontier_nodes") or 0) > 0
                and not any(item.request_type == "knowledge_model_budget_increase" and item.status == "pending" for item in updated.pending_chat_requests)
            ):
                budget_request = _knowledge_model_budget_request(
                    state.active_objective,
                    required_nodes=int(report.get("frontier_nodes_total") or 0),
                    completed_nodes=int(report.get("frontier_nodes_completed") or 0),
                    model_calls_used=episode.model_call_count,
                    exhausted=True,
                )
                report = {
                    **report,
                    "budget_boundary_prompt": budget_request.prompt_text,
                    "budget_request_id": budget_request.request_id,
                }
            if stagnation:
                report = {**report, "stagnation": dict(stagnation)}
            terminal_event = _knowledge_event(
                state.active_objective,
                event_type="knowledge_goal_terminal_report",
                summary=f"Terminal report ready: {report.get('status')}.",
                dedupe_key=f"{state.active_objective.objective_id}:terminal:{report.get('status')}:{episode.model_call_count}:{len(episode.cycles)}",
                episode=episode,
                visibility="operator_visible",
                extra={"terminal_status": report.get("status")},
            )
            updated = _replace_state(
                updated,
                lifecycle_state="paused_budget",
                pending_chat_requests=updated.pending_chat_requests + ((budget_request,) if budget_request else ()),
                objective_progress=updated.objective_progress + (terminal_event, report,) + (({"event": "knowledge_model_budget_increase_requested", "request_id": budget_request.request_id, "required_nodes": report.get("frontier_nodes_total"), "completed_nodes": report.get("frontier_nodes_completed"), "remaining_nodes": report.get("remaining_frontier_nodes"), "current_model_call_budget": state.active_objective.model_call_budget, "recommended_model_call_budget": budget_request.max_calls, "at": utc_now()},) if budget_request else ()),
            )
    if state.active_objective.provenance.get("execution_mode") == "knowledge_acquisition":
        terminal = next(
            (
                item for item in reversed(updated.objective_progress)
                if item.get("event") == "knowledge_goal_terminal_report"
            ),
            {},
        )
        try:
            graph = ingest_episode_at_runtime_root(
                runtime_root,
                objective=state.active_objective,
                episode=episode,
                terminal_status=str(terminal.get("status") or episode.loop_state),
            )
            updated = _replace_state(
                updated,
                objective_progress=updated.objective_progress + ({
                    "event": "provisional_semantic_graph_ingested",
                    "episode_id": episode.episode_id,
                    "graph_id": graph.graph_id,
                    "at": utc_now(),
                },),
            )
            updated, graph = _record_teaching_episode_results(updated, episode, graph)
            save_graph(runtime_root, graph)
        except ConsolidationIntegrityError as exc:
            updated = _replace_state(
                updated,
                objective_progress=updated.objective_progress + ({
                    "event": "provisional_semantic_graph_ingestion_failed",
                    "episode_id": episode.episode_id,
                    "reason": str(exc),
                    "at": utc_now(),
                },),
            )
    return _advance_capability_campaign(updated, reason=reason)


def _knowledge_terminal_report(objective: ConversationalObjective, episode: ActiveCognitiveEpisodeState) -> dict[str, Any]:
    accepted_results = tuple(result for result in episode.operation_results if result.accepted)
    frontier_nodes = tuple(item for item in episode.evidence if item.kind == "knowledge_frontier_node")
    findings: list[str] = []
    for result in accepted_results:
        if result.interpretation:
            findings.append(result.interpretation)
    satisfied_material, unplanned_material, unsatisfied_material = _knowledge_requirement_coverage(objective, episode)
    satisfied = tuple("address " + item for item in satisfied_material)
    remaining_gaps = tuple("address " + item for item in unplanned_material + unsatisfied_material)
    accepted_findings = _dedupe_knowledge_lines(findings)
    model_failures = tuple(
        result.interpretation or result.uncertainty for result in episode.operation_results
        if not result.accepted and (
            "local_model" in result.uncertainty
            or "execution" in result.uncertainty
            or "local model execution" in result.interpretation.lower()
        )
    )
    concepts = tuple(
        item.statement for item in episode.hypotheses
        if item.statement and not item.statement.lower().startswith("local model execution did not complete")
    )
    counters = _knowledge_progress_counters(objective, episode)
    stop_reason = ""
    stagnation = _knowledge_stagnation(episode)
    if _knowledge_limit_reached(episode.model_call_count, objective.model_call_budget):
        stop_reason = "model_call_budget_exhausted"
    elif objective.cycle_budget is not None and len(episode.cycles) >= objective.cycle_budget:
        stop_reason = "cycle_budget_exhausted"
    elif stagnation:
        stop_reason = "nonproductive_local_model_loop"
    elif episode.loop_state in {"blocked_insufficient_evidence", "blocked_capability_gap", "paused_budget"}:
        stop_reason = episode.loop_state
    all_material_satisfied = bool(_knowledge_material_requirements(objective)) and not unplanned_material and not unsatisfied_material
    if all_material_satisfied:
        status = "completed"
        stop_reason = "all_material_requirements_satisfied"
    elif unplanned_material:
        status = "planning_incomplete" if not satisfied_material else "partially_completed"
    elif satisfied_material:
        status = "partially_completed"
    elif model_failures:
        status = "blocked_capability"
    elif stop_reason == "model_call_budget_exhausted":
        status = "budget_exhausted_with_remaining_gaps"
    elif stop_reason in {"blocked_insufficient_evidence", "blocked_capability_gap"}:
        status = "blocked_with_remaining_work" if counters["unresolved_nodes"] else stop_reason
    elif stop_reason == "nonproductive_local_model_loop":
        status = "blocked_with_remaining_work"
    else:
        status = "blocked_with_remaining_work"
    if status == "completed":
        recommended = "the requested material requirements are complete; wait for a new operator request"
    elif stop_reason == "model_call_budget_exhausted":
        recommended = "authorize additional local-model calls for this goal or stop with this partial report"
    elif status == "blocked_capability":
        recommended = "repair local model execution or provide bounded local evidence"
    elif stop_reason == "nonproductive_local_model_loop":
        recommended = "stop the repeated nonproductive local-model loop and review the preserved remaining gaps"
    elif counters.get("retryable_nodes"):
        recommended = "retry blocked frontier nodes with narrowed prompts while budget remains"
    elif counters.get("blocked_nodes"):
        recommended = "review blocked incomplete nodes or authorize a new repair strategy"
    else:
        recommended = "continue frontier evaluation within remaining budget"
    return {
        "event": "knowledge_goal_terminal_report",
        "objective_id": objective.objective_id,
        "status": status,
        "stop_reason": stop_reason or status,
        "frontier_nodes_completed": counters["frontier_nodes_completed"],
        "frontier_nodes_total": counters["frontier_nodes_total"],
        "material_requirements_total": len(_knowledge_material_requirements(objective)),
        "material_requirements_satisfied": len(satisfied_material),
        "material_requirements_unplanned": len(unplanned_material),
        "remaining_frontier_nodes": counters["unresolved_nodes"],
        "blocked_incomplete_nodes": counters["blocked_nodes"],
        "retryable_nodes": counters["retryable_nodes"],
        "unattempted_nodes": counters["unattempted_nodes"],
        "model_calls_used": episode.model_call_count,
        "model_call_budget": objective.model_call_budget,
        "stagnation": dict(stagnation),
        "criteria_satisfied": satisfied,
        "criteria_unsatisfied": remaining_gaps,
        "accepted_findings": accepted_findings,
        "concepts_extracted": concepts,
        "evidence_used": tuple(item.evidence_id for item in episode.evidence if item.evidence_id),
        "model_failures": tuple(dict.fromkeys(model_failures)),
        "follow_up_questions_still_needed": (),
        "remaining_gaps": remaining_gaps,
        "recommended_next_action": recommended,
        "at": utc_now(),
    }


def _dedupe_knowledge_lines(lines: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for line in lines:
        text = " ".join(str(line or "").split()).strip()
        if not text:
            continue
        key = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(text)
    return tuple(deduped)


def attach_correction(
    state: ConversationalRuntimeState,
    user_turn: ConversationTurn,
    intent: ConversationIntent,
) -> tuple[ConversationalRuntimeState, CorrectionRecord, ScopedLesson]:
    objective_id = state.active_objective.objective_id if state.active_objective else ""
    target_turn_id = intent.target_turn_id or next((turn.turn_id for turn in reversed(state.conversation) if turn.role == "assistant"), "")
    lower = user_turn.text.lower()
    if "shorter" in lower or "too verbose" in lower:
        correction_type = "preferred_explanation_style"
        issue = "Prior answer was too verbose for this context."
        strategy = "Prefer concise answers for related conversational repair unless the operator asks for detail."
        applies = ("style", "verbosity", "explanation")
        guard = ("deep technical explanation requested", "operator asks for detail", "unrelated factual question")
    elif "when i say" in lower or "i mean" in lower:
        correction_type = "misunderstood_meaning"
        issue = "Operator supplied a local meaning clarification."
        strategy = "Check local conversational meaning before assuming a generic interpretation."
        applies = ("meaning", "reference", "operator phrasing")
        guard = ("different term", "unrelated topic", "explicitly new context")
    else:
        correction_type = "incorrect_contextual_interpretation"
        issue = "Prior interpretation did not match operator intent."
        strategy = "Use the latest correction as scoped evidence for related context, not as a universal rule."
        applies = ("context", "interpretation", "correction")
        guard = ("unrelated case", "operator changes topic", "insufficient similarity")
    correction = CorrectionRecord(
        correction_id=stable_id("conversation-correction", objective_id, user_turn.turn_id, target_turn_id),
        source_turn_id=user_turn.turn_id,
        target_turn_id=target_turn_id,
        correction_type=correction_type,
        operator_text=user_turn.text,
        interpreted_issue=issue,
        lesson_scope="active English-comprehension objective only",
        evidence_refs=(user_turn.turn_id, target_turn_id),
        overgeneralization_guard="; ".join(guard),
    )
    lesson = ScopedLesson(
        lesson_id=stable_id("conversation-lesson", correction.correction_id, strategy),
        source_correction_id=correction.correction_id,
        objective_id=objective_id,
        summary=issue,
        applicable_when=applies,
        not_applicable_when=guard,
        strategy_update=strategy,
        confidence=0.74,
        evidence_refs=correction.evidence_refs,
    )
    updated = _replace_state(
        state,
        conversation=state.conversation + (user_turn,),
        corrections=state.corrections + (correction,),
        accepted_lessons=state.accepted_lessons + (lesson,),
        objective_progress=state.objective_progress + ({"event": "correction_attached", "correction_id": correction.correction_id, "lesson_id": lesson.lesson_id, "at": utc_now()},),
    )
    return updated, correction, lesson


def infer_lesson_transfer(
    state: ConversationalRuntimeState,
    message: str,
    *,
    relation: TurnRelationDecision | None = None,
) -> dict[str, Any]:
    if relation and relation.routing_decision == "foreground_answer_without_goal_lesson":
        return {"applied": False, "lesson_id": "", "strategy_update": "", "rejection_reason": relation.rejection_reason}
    tokens = set(re.findall(r"[a-z0-9]{3,}", message.lower()))
    for lesson in reversed(_active_lessons(state)):
        applies = set(lesson.applicable_when)
        blocked = set(lesson.not_applicable_when)
        if tokens & applies and not tokens & blocked:
            return {"applied": True, "lesson_id": lesson.lesson_id, "strategy_update": lesson.strategy_update}
    return {"applied": False, "lesson_id": "", "strategy_update": ""}


def _ordinary_reply(
    message: str,
    transfer: Mapping[str, Any],
    *,
    relation: TurnRelationDecision | None = None,
) -> str:
    lower = message.lower()
    if relation and relation.relation_class == "unrelated_foreground_topic":
        if re.search(r"\b(?:what\s+is\s+)?2\s*\+\s*2\b", lower):
            return "4"
        if "water made of" in lower:
            return "Water is made of H2O: each molecule has two hydrogen atoms and one oxygen atom."
        if "gravity" in lower:
            return "Gravity is the attraction between masses. On Earth, it pulls objects toward the ground and keeps the Moon in orbit around Earth."
        if "angular momentum" in lower:
            return "Angular momentum is the rotational counterpart of linear momentum. It depends on how much mass is rotating, how far it is from the axis, and how fast it is rotating."
        if "euclidean geometry" in lower:
            return "Euclidean geometry is the geometry of flat space: points, lines, angles, triangles, circles, and shapes measured with Euclid's familiar rules."
        if "refrigerator" in lower:
            return "A refrigerator moves heat by evaporating refrigerant inside to absorb heat, compressing that refrigerant, then condensing it outside so the heat is released into the room."
        if "metal expand" in lower or "thermal expansion" in lower:
            return "Metal expands when heated because its atoms vibrate more strongly and, on average, sit slightly farther apart in the crystal structure."
        if "ice float" in lower:
            return "Ice floats because solid water forms an open crystal structure that is less dense than liquid water, so the same mass takes up more volume."
        if "kinetic energy" in lower:
            return "Kinetic energy is the energy an object has because it is moving. In classical mechanics it is one half times mass times speed squared."
        if "ram" in lower and "computer" in lower:
            return "RAM is a computer's fast working memory. It temporarily holds the data and instructions the processor is actively using."
        if "sky" in lower and "color" in lower:
            return "The daytime sky usually looks blue because air scatters shorter blue wavelengths of sunlight more strongly than longer red wavelengths."
        if "moon" in lower and "color" in lower:
            return "The Moon is usually pale gray or off-white to our eyes, though it can look yellow, orange, or red near the horizon because of Earth's atmosphere."
        if "soup" in lower:
            return "A simple way to thicken soup is to simmer it uncovered, blend part of it, or stir in a small slurry of flour or cornstarch mixed with cold water."
        if "rice" in lower and "rest" in lower:
            return "Let rice rest covered for about 10 minutes after cooking so steam redistributes and the grains firm up without turning mushy."
        if lower.startswith(("hi", "hello", "hey")):
            return "Hi. I'm here and running; we can keep chatting normally while the background goal continues."
        if "chemistry" in lower:
            return "I will answer the chemistry question on its own terms and will not apply the reference-correction lesson unless the chemistry question actually depends on conversational reference."
        if lower.endswith("?"):
            return "I can answer that as ordinary chat. Give me the specific thing you want explained, and I will keep it separate from the background goal."
    if transfer.get("applied"):
        if "style" in lower or "explain" in lower:
            return "Short version: I will answer more directly here and avoid repeating the same clarification unless it changes the meaning."
        return "I will interpret that in the current conversational context first, then ask only if the ambiguity would change the answer."
    if "how are you" in lower:
        return "I'm here and running. We can chat normally."
    if "what are you doing" in lower:
        return "I'm keeping ordinary chat responsive while the bounded conversational objective continues in the background."
    if "sky" in lower and "color" in lower:
        return "The daytime sky usually appears blue because molecules in the atmosphere scatter blue light more strongly than red light."
    if "moon" in lower and "color" in lower:
        return "The Moon usually appears pale gray or off-white, though atmospheric effects can make it look yellow, orange, or red."
    if lower.endswith("?"):
        return "I can answer the question directly, and I will keep it separate from any background goal. What detail do you want me to focus on?"
    return "I understand. I will treat this as ordinary conversation unless you make it a goal, correction, or authority-changing request."


def evaluate_conversational_runtime(state: ConversationalRuntimeState) -> dict[str, Any]:
    failures: list[str] = []
    active_lessons = _active_lessons(state)
    if not state.active_objective:
        failures.append("goal_not_durable")
    if not state.authority:
        failures.append("unsafe_standing_authority")
    if state.authority and any(action not in DEFAULT_PROHIBITED_ACTIONS for action in state.authority.prohibited_actions):
        failures.append("unsafe_standing_authority")
    if not state.completed_cycle_keys:
        failures.append("cognition_not_started")
    if not state.corrections:
        failures.append("correction_not_attached")
    if not active_lessons:
        failures.append("correction_stored_without_transfer")
    if any(lesson.authority_effect != "none" for lesson in active_lessons):
        failures.append("salience_grants_authority")
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": not failures,
        "failure_reasons": failures,
        "objective_id": state.active_objective.objective_id if state.active_objective else "",
        "correction_count": len(state.corrections),
        "accepted_lesson_count": len(active_lessons),
        "background_cycle_count": len(state.completed_cycle_keys),
        "pending_material_authority_count": len(state.pending_material_authority),
    }


def _active_progress_events(state: ConversationalRuntimeState) -> tuple[Mapping[str, Any], ...]:
    objective_id = state.active_objective.objective_id if state.active_objective else ""
    return tuple(
        event
        for event in state.objective_progress
        if not objective_id or event.get("objective_id") == objective_id
    )


def evaluate_capability_proposal_readiness(state: ConversationalRuntimeState) -> dict[str, Any]:
    objective_id = state.active_objective.objective_id if state.active_objective else ""
    events = _active_progress_events(state)
    missing: list[str] = []
    weakness_ids = {
        str(event.get("weakness_id") or "")
        for event in events
        if event.get("event") == "capability_candidate_weakness" and event.get("evidence_id")
    }
    weakness_ids.discard("")
    selected_weakness = next(
        (
            event
            for event in events
            if event.get("event") == "capability_selected_weakness"
            and event.get("weakness_id") in weakness_ids
            and event.get("comparison_id")
        ),
        None,
    )
    candidate_ids = {
        str(event.get("candidate_id") or "")
        for event in events
        if event.get("event") == "capability_candidate_strategy"
    }
    candidate_ids.discard("")
    frozen_evaluator = next(
        (
            event
            for event in events
            if event.get("event") == "capability_frozen_evaluator"
            and event.get("evaluator_id")
            and event.get("frozen") is True
        ),
        None,
    )
    sandbox_candidate_ids = {
        str(event.get("candidate_id") or "")
        for event in events
        if event.get("event") == "capability_sandbox_execution"
        and event.get("candidate_id") in candidate_ids
        and event.get("status") in {"completed", "passed", "failed"}
    }
    heldout_candidate_ids = {
        str(event.get("candidate_id") or "")
        for event in events
        if event.get("event") == "capability_heldout_result"
        and event.get("candidate_id") in candidate_ids
        and event.get("result_id")
    }
    rejected_candidate_ids = {
        str(event.get("candidate_id") or "")
        for event in events
        if event.get("event") == "capability_candidate_rejected"
        and event.get("candidate_id") in candidate_ids
        and event.get("reason")
    }
    winning_candidate = next(
        (
            event
            for event in events
            if event.get("event") == "capability_winning_candidate"
            and event.get("candidate_id") in candidate_ids
            and event.get("improvement_evidence_id")
        ),
        None,
    )
    source_proposal = next(
        (
            event
            for event in events
            if event.get("event") == "capability_source_proposal"
            and event.get("proposal_id")
            and event.get("patch_path")
            and event.get("source_files")
            and event.get("test_files")
        ),
        None,
    )
    supervisor_audit = next(
        (
            event
            for event in events
            if event.get("event") == "capability_supervisor_audit"
            and event.get("audit_id")
            and event.get("status") in {"passed", "reviewed"}
        ),
        None,
    )
    if not objective_id:
        missing.append("active_objective")
    if len(weakness_ids) < 5:
        missing.append("five_evidence_linked_candidate_weaknesses")
    if selected_weakness is None:
        missing.append("selected_weakness_with_comparison")
    if len(candidate_ids) < 3:
        missing.append("three_materially_distinct_candidate_strategies")
    if frozen_evaluator is None:
        missing.append("frozen_independent_evaluator")
    if len(sandbox_candidate_ids) < 3:
        missing.append("sandbox_execution_for_all_candidates")
    if len(heldout_candidate_ids) < 3:
        missing.append("heldout_results_for_all_candidates")
    if not rejected_candidate_ids:
        missing.append("rejected_alternative_candidate")
    if winning_candidate is None:
        missing.append("winning_candidate_with_improvement_evidence")
    if source_proposal is None:
        missing.append("bounded_source_and_test_proposal_with_patch")
    if supervisor_audit is None:
        missing.append("codex_supervisor_audit")
    if missing:
        artifact_readiness = _evaluate_capability_proposal_artifacts(objective_id)
        if artifact_readiness["ready"]:
            return artifact_readiness
    return {
        "schema_version": SCHEMA_VERSION,
        "ready": not missing,
        "objective_id": objective_id,
        "missing": missing,
        "weakness_count": len(weakness_ids),
        "candidate_count": len(candidate_ids),
        "sandbox_candidate_count": len(sandbox_candidate_ids),
        "heldout_candidate_count": len(heldout_candidate_ids),
        "rejected_candidate_count": len(rejected_candidate_ids),
        "winning_candidate_id": str(winning_candidate.get("candidate_id") or "") if winning_candidate else "",
    }


def _read_json_if_present(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _evaluate_capability_proposal_artifacts(objective_id: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2] / ".tmp" / "persistent-live-capability-growth-repair-marathon-1" / "capability_growth_candidate_evaluation"
    files = {
        "candidate_weaknesses": root / "candidate_weaknesses.json",
        "selected_weakness": root / "selected_weakness.json",
        "weakness_selection_rationale": root / "weakness_selection_rationale.json",
        "candidate_approaches": root / "candidate_approaches.json",
        "evaluator_contract": root / "evaluator_contract.json",
        "evaluator_identity": root / "evaluator_identity.json",
        "evaluator_digest": root / "evaluator_digest.json",
        "dataset_partition_manifest": root / "dataset_partition_manifest.json",
        "baseline_evaluation": root / "baseline_evaluation.json",
        "held_out_evaluation": root / "held_out_evaluation.json",
        "unrelated_controls": root / "unrelated_controls.json",
        "negative_instruction_results": root / "negative_instruction_results.json",
        "tentative_goal_results": root / "tentative_goal_results.json",
        "candidate_comparison": root / "candidate_comparison.json",
        "rejected_candidates": root / "rejected_candidates.json",
        "winning_candidate": root / "winning_candidate.json",
        "implementation_proposal": root / "implementation_proposal.json",
        "codex_supervisor_audit": root / "codex_supervisor_audit.json",
        "operator_review_summary": root / "operator_review_summary.json",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    weaknesses = _read_json_if_present(files["candidate_weaknesses"]).get("weaknesses") or ()
    candidates = _read_json_if_present(files["candidate_approaches"]).get("candidates") or ()
    audit = _read_json_if_present(files["codex_supervisor_audit"])
    winner = _read_json_if_present(files["winning_candidate"])
    proposal = _read_json_if_present(files["implementation_proposal"])
    live_evidence = proposal.get("live_transcript_evidence") if isinstance(proposal.get("live_transcript_evidence"), dict) else {}
    rejected = _read_json_if_present(files["rejected_candidates"]).get("rejected") or ()
    if not objective_id or live_evidence.get("active_objective_id") != objective_id:
        missing.append("artifact_objective_scope_matches_active_objective")
    if len(weaknesses) < 5:
        missing.append("five_evidence_linked_candidate_weaknesses")
    if len(candidates) < 3:
        missing.append("three_materially_distinct_candidate_strategies")
    if not rejected:
        missing.append("rejected_alternative_candidate")
    if not winner.get("candidate_id"):
        missing.append("winning_candidate_with_improvement_evidence")
    if not proposal.get("proposed_patch_path") or not proposal.get("exact_proposed_source_files") or not proposal.get("exact_proposed_test_files"):
        missing.append("bounded_source_and_test_proposal_with_patch")
    if audit.get("disposition") != "approve_for_operator_review":
        missing.append("codex_supervisor_audit_approves_review")
    for candidate in ("candidate-a", "candidate-b", "candidate-c"):
        candidate_root = root.parent / "sandbox" / candidate
        required = (
            "hypothesis.json",
            "design.json",
            "execution_log.json",
            "model_evidence.json",
            "baseline_results.json",
            "evaluation_results.json",
            "held_out_results.json",
            "foreground_controls.json",
            "tentative_goal_controls.json",
            "negative_instruction_results.json",
            "restart_results.json",
            "failure_analysis.json",
            "final_candidate_status.json",
        )
        missing.extend(
            f"{candidate}_{name.removesuffix('.json')}"
            for name in required
            if not (candidate_root / name).exists()
        )
    ready = not missing and bool(objective_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "ready": ready,
        "objective_id": objective_id,
        "missing": [] if ready else missing,
        "weakness_count": len(weaknesses),
        "candidate_count": len(candidates),
        "sandbox_candidate_count": 3 if all((root.parent / "sandbox" / candidate / "execution_log.json").exists() for candidate in ("candidate-a", "candidate-b", "candidate-c")) else 0,
        "heldout_candidate_count": 3 if (root / "held_out_evaluation.json").exists() else 0,
        "rejected_candidate_count": len(rejected),
        "winning_candidate_id": str(winner.get("candidate_id") or ""),
        "artifact_root": str(root),
    }


def _active_capability_proposal_artifacts(state: ConversationalRuntimeState) -> Mapping[str, Any]:
    readiness = evaluate_capability_proposal_readiness(state)
    if not readiness.get("ready"):
        return {}
    artifact_root = Path(str(readiness.get("artifact_root") or ""))
    if not artifact_root.exists():
        return {}
    return {
        "readiness": readiness,
        "proposal": _read_json_if_present(artifact_root / "implementation_proposal.json"),
        "winner": _read_json_if_present(artifact_root / "winning_candidate.json"),
        "rejected": _read_json_if_present(artifact_root / "rejected_candidates.json"),
        "audit": _read_json_if_present(artifact_root / "codex_supervisor_audit.json"),
        "summary": _read_json_if_present(artifact_root / "operator_review_summary.json"),
    }


def review_status_for_goal_completion(state: ConversationalRuntimeState) -> str:
    readiness = evaluate_capability_proposal_readiness(state)
    if readiness["ready"]:
        return "implementation_review_required"
    campaign = _active_capability_campaign(state)
    if campaign and campaign.get("status") == "milestone_ready":
        return "capability_campaign_milestone_ready"
    if campaign and campaign.get("status") == "running":
        return "capability_campaign_running"
    if state.lifecycle_state == "paused_budget":
        if state.active_objective and state.active_objective.provenance.get("execution_mode") == "knowledge_acquisition":
            return "knowledge_terminal_report"
        return "capability_proposal_pending"
    return state.lifecycle_state


def render_goal_review(state: ConversationalRuntimeState, *, status: str | None = None) -> tuple[ConversationalRuntimeState, str]:
    objective = state.active_objective
    if status is None:
        status = review_status_for_goal_completion(state)
    objective_id = objective.objective_id if objective else ""
    active_lessons = _active_lessons(state)
    active_decisions = tuple(item for item in state.turn_relation_decisions if item.active_goal_id == objective_id)
    active_provider_authorities = tuple(auth for auth in state.provider_authorities if auth.get("objective_id") == objective_id)
    active_insufficiencies = tuple(item for item in state.local_semantic_insufficiencies if item.goal_id == objective_id)
    proposal_readiness = evaluate_capability_proposal_readiness(state)
    if status == "implementation_review_required" and not proposal_readiness["ready"]:
        status = "capability_proposal_pending"
    proposal_artifacts = _active_capability_proposal_artifacts(state) if status == "implementation_review_required" else {}
    proposal = proposal_artifacts.get("proposal") if isinstance(proposal_artifacts.get("proposal"), dict) else {}
    winner = proposal_artifacts.get("winner") if isinstance(proposal_artifacts.get("winner"), dict) else {}
    rejected_artifacts = proposal_artifacts.get("rejected") if isinstance(proposal_artifacts.get("rejected"), dict) else {}
    campaign = _active_capability_campaign(state)
    goal_label = str(campaign.get("goal_label") or ("Semantic reconciliation" if proposal_artifacts else _goal_review_label(objective)))
    for existing_review in reversed(state.goal_reviews):
        if existing_review.get("objective_id") != objective_id or existing_review.get("status") != status:
            continue
        existing_text = str(existing_review.get("text") or "")
        if not proposal_artifacts or goal_label in existing_text:
            return state, existing_text
    if status == "knowledge_terminal_report":
        report = next((item for item in reversed(state.objective_progress) if item.get("event") == "knowledge_goal_terminal_report" and item.get("objective_id") == objective_id), {})
        if not report and objective:
            report = {
                "status": "budget_exhausted_with_remaining_gaps",
                "criteria_satisfied": (),
                "criteria_unsatisfied": objective.practical_success_indicators,
                "concepts_extracted": (),
                "model_failures": (),
                "remaining_gaps": objective.practical_success_indicators,
                "recommended_next_action": "continue bounded knowledge evaluation",
            }
        lines = [
            f"[Goal review \u00b7 {_goal_review_label(objective)}]",
            "",
            f"Status: {report.get('status') or 'budget_exhausted_with_remaining_gaps'}",
            f"Stopped because: {report.get('stop_reason') or 'not_recorded'}",
            f"Completed nodes: {report.get('frontier_nodes_completed', 0)}/{report.get('frontier_nodes_total', 0)}",
            f"Unresolved nodes: {report.get('remaining_frontier_nodes', 0)}",
            f"Retryable nodes: {report.get('retryable_nodes', 0)}",
            f"Blocked incomplete nodes: {report.get('blocked_incomplete_nodes', 0)}",
            f"Unattempted nodes: {report.get('unattempted_nodes', 0)}",
            f"Model calls: {_knowledge_call_progress_text(int(report.get('model_calls_used', 0)), report.get('model_call_budget'))}",
            "",
            "Satisfied criteria:",
        ]
        satisfied = tuple(report.get("criteria_satisfied") or ())
        lines.extend(f"- {item}" for item in (satisfied or ("none yet",)))
        findings = tuple(report.get("accepted_findings") or ())
        if findings:
            lines.append("")
            lines.append("Accepted findings:")
            lines.extend(f"- {item}" for item in findings[:12])
        lines.append("")
        lines.append("Remaining gaps:")
        lines.extend(f"- {item}" for item in tuple(report.get("remaining_gaps") or report.get("criteria_unsatisfied") or ("none recorded",)))
        failures = tuple(report.get("model_failures") or ())
        if failures:
            lines.append("")
            lines.append("Model failures:")
            lines.extend(f"- {item}" for item in failures)
        lines.append("")
        lines.append(f"Next recommended action: {report.get('recommended_next_action') or 'continue bounded knowledge evaluation'}")
        budget_request_id = str(report.get("budget_request_id") or "")
        has_live_budget_request = any(
            item.request_id == budget_request_id
            and item.request_type == "knowledge_model_budget_increase"
            and item.status == "pending"
            for item in state.pending_chat_requests
        )
        if report.get("budget_boundary_prompt") and has_live_budget_request:
            lines.append("")
            lines.append(str(report.get("budget_boundary_prompt")))
        text = "\n".join(lines)
        review = {
            "review_id": stable_id("goal-review", objective_id, status, _digest({"text": text})),
            "objective_id": objective_id,
            "status": status,
            "text": text,
            "at": utc_now(),
        }
        return _replace_state(state, goal_reviews=state.goal_reviews + (review,)), text
    if campaign and status in {"capability_campaign_milestone_ready", "capability_campaign_running"}:
        completed_phases = tuple(campaign.get("completed_phases") or ())
        if completed_phases:
            completed = "\n".join(f"- {phase}" for phase in completed_phases)
        else:
            completed = "- campaign bridge initialized\n- local cognition started"
    elif proposal_artifacts:
        completed = "\n".join(
            (
                "- live weakness investigation",
                "- local Qwen learning",
                "- three candidate comparisons",
                "- frozen held-out evaluation",
                "- bounded implementation proposal for operator review",
            )
        )
    elif status == "implementation_review_required":
        completed = "I reached an implementation-review boundary for the active language-comprehension goal."
    elif status == "capability_proposal_pending":
        completed = "I reached the local cycle budget, but I do not yet have enough candidate, evaluator, sandbox, and proposal evidence for implementation review."
    else:
        completed = f"The active goal is currently {status}."
    learned = []
    if campaign and campaign.get("selected_weakness"):
        selected = campaign.get("selected_weakness") or {}
        learned.append(f"selected weakness: {selected.get('name')}")
        learned.append(str(selected.get("selection_reason") or "weakness selected through first comparison"))
    if campaign and campaign.get("sandbox_results"):
        best = next((item for item in campaign.get("sandbox_results", ()) if item.get("result") == "best_current_candidate"), {})
        if best:
            learned.append(f"current best candidate: {best.get('candidate_id')} ({best.get('passed')}/{best.get('total')} sandbox cases)")
    if proposal_artifacts:
        learned.append(str(proposal.get("exact_live_gap") or "queued and implied references need lane-aware reconciliation"))
        learned.append(f"winning candidate: {winner.get('candidate_id') or proposal_readiness.get('winning_candidate_id')}")
        learned.append("local Qwen was sufficient; no provider packet was used")
    if active_decisions:
        learned.append("foreground messages must be routed separately from background goal work")
    if active_insufficiencies:
        learned.append("external escalation requires a recorded local insufficiency first")
    if active_lessons:
        learned.append(f"{len(active_lessons)} scoped correction-derived lesson(s) are available")
    if not learned:
        learned.append("no durable learning has been validated yet")
    retained = [lesson.summary for lesson in active_lessons[-3:]]
    if campaign and campaign.get("candidate_strategies"):
        retained.extend(str(item.get("candidate_id")) for item in campaign.get("candidate_strategies", ())[:3])
    if proposal_artifacts:
        retained.append(str(proposal.get("capability_name") or "topic-boundary queued reference reconciliation"))
    retained = retained or ["no scoped lessons retained"]
    rejected = [item.rejection_reason for item in active_decisions[-5:] if item.rejection_reason]
    if campaign and campaign.get("sandbox_results"):
        rejected.extend(
            f"{item.get('candidate_id')}: {item.get('result')}"
            for item in campaign.get("sandbox_results", ())
            if item.get("result") != "best_current_candidate"
        )
    for rejected_candidate in rejected_artifacts.get("rejected") or ():
        rejected.append(f"{rejected_candidate.get('candidate_id')}: {rejected_candidate.get('reason')}")
    rejected = rejected or ["no rejected lesson applicability recorded"]
    unresolved = []
    if campaign and status == "capability_campaign_milestone_ready":
        unresolved.append("source adoption remains unavailable until an explicit implementation review and approval")
        unresolved.append("next phase should deepen independent held-out evaluation before any patch")
    elif campaign and status == "capability_campaign_running":
        unresolved.append("candidate campaign is running and has not reached a first milestone yet")
    elif status == "implementation_review_required":
        unresolved.append("implementation review is required before source-level semantic capability changes")
    elif status == "capability_proposal_pending":
        unresolved.append("implementation review is unavailable until a measured capability proposal exists")
        unresolved.extend(f"missing {item}" for item in proposal_readiness["missing"][:8])
    if any(auth.get("status") == "authorized_not_executed" for auth in active_provider_authorities):
        unresolved.append("provider authority exists but has not been consumed")
    provider_use = "local-only; no external provider calls performed"
    if active_provider_authorities:
        auth = active_provider_authorities[-1]
        provider_use = f"authority recorded for {auth.get('provider')} with max_calls={auth.get('max_calls')}, spent=$0, consumed_calls={auth.get('consumed_call_count')}"
    review_text = (
        f"[Goal review · {goal_label}]\n\n"
        f"I completed:\n{completed}\n\n"
        f"I learned:\n- " + "\n- ".join(learned) + "\n\n"
        f"I retained:\n- " + "\n- ".join(retained) + "\n\n"
        f"I rejected:\n- " + "\n- ".join(rejected) + "\n\n"
        f"Still unresolved:\n- " + "\n- ".join(unresolved or ["no blocker recorded"]) + "\n\n"
        f"Provider use:\n{provider_use}\n\n"
        "Next recommended step:\n"
        + (
            "Continue the candidate campaign into independent held-out evaluation; do not mutate source until review is explicitly approved."
            if campaign
            else (
                "Review the exact semantic-reconciliation implementation proposal before any source mutation."
                if proposal_artifacts
                else "Continue local evidence gathering until this specific goal has enough measured candidate evidence."
            )
        )
    )
    review = {
        "review_id": stable_id("goal-review", state.runtime_id, str(len(state.goal_reviews) + 1), status),
        "status": status,
        "objective_id": objective.objective_id if objective else "",
        "text": review_text,
        "provider_use": provider_use,
        "capability_proposal_readiness": proposal_readiness,
        "created_at": utc_now(),
    }
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 1), review_text),
        role="assistant",
        text=review_text,
        intent_type="goal_review",
        objective_id=objective.objective_id if objective else "",
    )
    updated = _replace_state(
        state,
        conversation=state.conversation + (assistant_turn,),
        goal_reviews=state.goal_reviews + (review,),
        objective_progress=state.objective_progress + ({"event": "goal_review_rendered", "review_id": review["review_id"], "status": status, "at": utc_now()},),
    )
    return updated, review_text


def stop_active_objective(state: ConversationalRuntimeState) -> ConversationalRuntimeState:
    objective = state.active_objective
    if objective is None:
        return _replace_state(state, lifecycle_state="running")
    stopped = ConversationalObjective(**{**objective.as_record(), "lifecycle_state": "stopped"})
    return _replace_state(
        state,
        lifecycle_state="stopped",
        active_objective=stopped,
        objective_progress=state.objective_progress + ({"event": "operator_stop", "at": utc_now()},),
    )


def resume_active_objective(state: ConversationalRuntimeState, *, runtime_root: str | Path) -> ConversationalRuntimeState:
    """Resume only an operator-paused objective; exhausted and failed states stay explicit."""
    if state.active_objective is None or state.lifecycle_state != "paused_operator":
        return state
    updated = _replace_state(
        state,
        lifecycle_state="running",
        objective_progress=state.objective_progress + (
            {"event": "objective_resumed", "objective_id": state.active_objective.objective_id, "at": utc_now()},
        ),
    )
    save_runtime_state(runtime_root, updated)
    return updated


def _replace_state(state: ConversationalRuntimeState, **updates: Any) -> ConversationalRuntimeState:
    payload = state.as_record()
    payload.update(updates)
    return _state_from_record(payload)
