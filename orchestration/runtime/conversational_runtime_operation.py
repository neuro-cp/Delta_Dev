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
    cycle_budget: int
    model_call_budget: int
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
    created_turn_id: str = ""
    resolved_turn_id: str = ""
    resolution_text: str = ""
    resolution_policy: str = ""
    side_thread_effect: str = "does_not_replace_foreground_topic"
    consumption_count: int = 0
    created_at: str = field(default_factory=utc_now)
    resolved_at: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TurnRelationDecision:
    turn_id: str
    foreground_topic: str
    active_goal_id: str
    relation_class: str
    evidence: tuple[str, ...]
    confidence: float
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
    if re.search(r"\byour goal\b|\bgoal today\b|\bwork on\b|\bkeep studying\b|\bkeep working\b", lower):
        goal_score += 2
        signals.append("explicit_goal_language")
    if any(term in lower for term in ("improve", "learn", "understand", "comprehension", "communicate better", "corrections")):
        goal_score += 1
        signals.append("learning_or_improvement_target")
    if any(term in lower for term in ("today", "this session", "until", "keep")):
        goal_score += 1
        signals.append("scope_or_duration")
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


def compile_conversational_objective(message: str, intent: ConversationIntent) -> ConversationalObjective:
    text = " ".join(message.split())
    objective_id = stable_id("conversational-objective", text, intent.persistence_scope)
    interpreted = "Improve operator-specific English comprehension during conversation by observing misunderstandings, incorporating corrections, and testing later transfer."
    return ConversationalObjective(
        objective_id=objective_id,
        operator_wording=text,
        interpreted_objective=interpreted,
        persistence_scope=intent.persistence_scope,
        practical_success_indicators=(
            "operator corrections attach to exact turns",
            "strategy revisions reduce repeated misunderstanding",
            "later related cases use the scoped lesson",
            "unrelated cases do not receive false transfer",
            "ordinary chat remains responsive",
        ),
        allowed_actions=DEFAULT_ALLOWED_ACTIONS,
        prohibited_actions=DEFAULT_PROHIBITED_ACTIONS,
        local_evidence_sources=("conversation turns", "operator corrections", "active cognitive episode state", "continuity lessons"),
        cycle_budget=16,
        model_call_budget=12,
        interruption_policy="foreground chat preempts background objective work",
        correction_learning_policy="attach corrections to exact turns; consolidate only scoped non-authoritative lessons",
        completion_or_review_condition="review after at least one correction, one transfer case, one false-transfer guard, and restart restoration",
        authority_boundary="standing authority covers routine local cognition only; material actions require explicit operator approval",
        provenance={"source": "ordinary_chat", "intent": intent.as_record(), "compiler": "conversational_runtime_operation"},
    )


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
        return _state_from_record(read_json(state_path))
    state = ConversationalRuntimeState(
        runtime_id=stable_id("conversational-runtime", str(Path(root))),
        lifecycle_state="running",
    )
    save_runtime_state(root, state)
    return state


def save_runtime_state(root: str | Path, state: ConversationalRuntimeState) -> None:
    write_json(Path(root) / "state.json", state.as_record())


def _request_from_record(item: Any) -> ChatAddressableRequest:
    if isinstance(item, ChatAddressableRequest):
        return item
    payload = dict(item)
    for key in ("permitted_data", "prohibited_data"):
        payload[key] = tuple(payload.get(key, ()))
    return ChatAddressableRequest(**payload)


def _turn_relation_from_record(item: Any) -> TurnRelationDecision:
    if isinstance(item, TurnRelationDecision):
        return item
    payload = dict(item)
    for key in ("evidence", "negative_instruction_tokens", "lesson_ids_considered", "lesson_ids_applied", "lesson_ids_rejected"):
        payload[key] = tuple(payload.get(key, ()))
    return TurnRelationDecision(**payload)


def _insufficiency_from_record(item: Any) -> LocalSemanticInsufficiency:
    if isinstance(item, LocalSemanticInsufficiency):
        return item
    payload = dict(item)
    for key in ("local_evidence_references", "prohibited_data"):
        payload[key] = tuple(payload.get(key, ()))
    return LocalSemanticInsufficiency(**payload)


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
        "archived_at": utc_now(),
    }


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
    if "previous message" in lower:
        return "linguistic_example_previous_message"
    if "what is" in lower or lower.endswith("?"):
        return "foreground_question"
    return "ordinary_conversation"


def _is_unrelated_factual_topic(message: str) -> bool:
    topic = _foreground_topic(message)
    lower = message.lower()
    if topic in {"angular_momentum", "euclidean_geometry", "chemistry"}:
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
    approval_terms = ("approve", "approved", "yes", "okay", "ok", "use one call", "use only one call", "1 call")
    denial_terms = ("no", "deny", "continue locally", "not approved")
    if "not approved" in lower:
        return "denied"
    if "approve" in lower or "approved" in lower:
        return "approved"
    if lower.startswith(("no", "deny")) or any(term in lower for term in denial_terms):
        return "denied"
    if any(term in lower for term in approval_terms):
        return "approved"
    if re.search(r"\bprioriti[sz]e\b", lower) or lower.startswith(("yes,", "yes ")):
        return "directional"
    return None


def _pending_request_for_reply(state: ConversationalRuntimeState, message: str) -> ChatAddressableRequest | None:
    if not state.pending_chat_requests:
        return None
    kind = _chat_request_resolution_kind(message)
    if kind is None:
        return None
    latest = state.pending_chat_requests[-1]
    if latest.status != "pending" or latest.consumption_count:
        return None
    if latest.request_type == "provider_authority" and kind in {"approved", "denied"}:
        return latest
    if latest.request_type == "directional_question" and kind in {"directional", "denied", "approved"}:
        return latest
    return None


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
    progress = state.objective_progress + (
        {
            "event": "foreground_message_queued_for_reconciliation",
            "turn_id": user_turn.turn_id,
            "message": message,
            "at": utc_now(),
        },
    )
    updated = _replace_state(state, conversation=state.conversation + (user_turn,), objective_progress=progress)
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
    if request.request_type == "provider_authority":
        policy, authority = _resolve_provider_policy(request, message, resolution_kind)
    resolved = ChatAddressableRequest(
        **{
            **request.as_record(),
            "status": "denied" if policy == "denied_continue_locally" else "resolved",
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
        schema_version=str(payload.get("schema_version") or SCHEMA_VERSION),
    )


def handle_conversational_message(
    state: ConversationalRuntimeState,
    message: str,
    *,
    runtime_root: str | Path,
    run_background_cycle: bool = True,
    model_runner: ModelRunner | None = None,
) -> RuntimeTurnResult:
    resolved = resolve_pending_chat_request(state, message, runtime_root=runtime_root)
    if resolved is not None:
        return resolved
    if _is_provider_learning_packet_request(message, state):
        return request_provider_learning_packet(state, message, runtime_root=runtime_root)
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
    if intent.intent_type == "persistent_or_session_goal":
        objective = compile_conversational_objective(message, intent)
        if state.active_objective and state.active_objective.objective_id == objective.objective_id:
            assistant_reply = "That matches the active goal already. I kept the existing objective identity and did not reset its cycle or authority state."
            assistant_turn = ConversationTurn(
                turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), assistant_reply),
                role="assistant",
                text=assistant_reply,
                intent_type="duplicate_objective_acknowledgement",
                objective_id=state.active_objective.objective_id,
            )
            updated = _replace_state(
                state,
                conversation=state.conversation + (user_turn, assistant_turn),
                objective_progress=state.objective_progress + ({"event": "duplicate_objective_rejected", "objective_id": objective.objective_id, "at": utc_now()},),
            )
            save_runtime_state(runtime_root, updated)
            return RuntimeTurnResult(state=updated, intent=intent, reply=assistant_reply)
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
        episode = initialize_episode(
            title="Conversational English comprehension objective",
            goal_summary=objective.interpreted_objective,
            expected_state="Operator-specific comprehension improves through correction-linked strategy revision and transfer checks.",
            evidence=(
                EvidenceRef(
                    evidence_id="operator-natural-goal",
                    summary=message,
                    source="ordinary_chat",
                ),
            ),
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
        updated = _replace_state(
            state,
            lifecycle_state="running",
            active_objective=objective,
            authority=authority,
            conversation=state.conversation + (goal_user_turn,),
            active_episode_path=episode_path,
            completed_cycle_keys=(),
            pending_material_authority=(),
            pending_chat_requests=(),
            resolved_chat_requests=(),
            provider_authorities=(),
            turn_relation_decisions=(),
            local_semantic_insufficiencies=(),
            goal_reviews=(),
            objective_progress=progress,
            focus_history=state.focus_history + (focus,),
            archived_objectives=state.archived_objectives + ((archived,) if archived else ()),
        )
        if run_background_cycle:
            updated = run_background_objective_cycle(updated, runtime_root=runtime_root, reason="objective_registered", model_runner=model_runner)
        reply = "I registered that as a bounded session goal: improve my operator-specific English comprehension through this conversation. I can run routine local cognition and learn from corrections under standing bounded authority; source changes, network use, installs, deletion, commits, pushes, and protected paths still need explicit approval."
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", updated.runtime_id, str(len(updated.conversation) + 1), reply),
            role="assistant",
            text=reply,
            intent_type="objective_confirmation",
            objective_id=objective.objective_id,
        )
        updated = _replace_state(updated, conversation=updated.conversation + (assistant_turn,))
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(state=updated, intent=intent, reply=reply, objective_created=True, background_cycle_started=run_background_cycle)
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
        if run_background_cycle:
            updated = run_background_objective_cycle(updated, runtime_root=runtime_root, reason="correction_attached", model_runner=model_runner)
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(state=updated, intent=intent, reply=reply, correction_attached=True, background_cycle_started=run_background_cycle, transfer_applied=False)
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
    if state.active_objective and run_background_cycle and intent.intent_type == "ordinary_conversation":
        updated = run_background_objective_cycle(updated, runtime_root=runtime_root, reason="ordinary_chat_yield", model_runner=model_runner)
    save_runtime_state(runtime_root, updated)
    return RuntimeTurnResult(state=updated, intent=intent, reply=reply, background_cycle_started=state.active_objective is not None and run_background_cycle, transfer_applied=bool(transfer["applied"]))


def run_background_objective_cycle(
    state: ConversationalRuntimeState,
    *,
    runtime_root: str | Path,
    reason: str,
    model_runner: ModelRunner | None = None,
) -> ConversationalRuntimeState:
    if not state.active_objective or not state.authority or state.authority.revoked:
        return state
    cycle_key = stable_id("conversational-cycle", state.active_objective.objective_id, reason, str(len(state.completed_cycle_keys) + 1))
    if cycle_key in state.completed_cycle_keys:
        return state
    if len(state.completed_cycle_keys) >= state.active_objective.cycle_budget:
        return _replace_state(state, lifecycle_state="paused_budget")
    episode_path = Path(state.active_episode_path or Path(runtime_root) / "active_episode.json")
    episode = read_episode_state(episode_path) if episode_path.exists() else initialize_episode(
        title="Conversational English comprehension objective",
        goal_summary=state.active_objective.interpreted_objective,
        expected_state="Operator-specific comprehension improves through correction-linked strategy revision and transfer checks.",
        state_path=episode_path,
    )
    episode = replace(episode, budgets={**episode.budgets, "max_cycles": state.active_objective.cycle_budget, "max_model_calls": state.active_objective.model_call_budget})
    if episode.completed or episode.loop_state == "completed":
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
    if episode.model_call_count < state.active_objective.model_call_budget:
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
    return _replace_state(
        state,
        active_episode_path=str(episode_path),
        completed_cycle_keys=state.completed_cycle_keys + (cycle_key,),
        objective_progress=state.objective_progress + (progress,),
        focus_history=state.focus_history + ({"event": "focus_tick", "reason": reason, "at": utc_now()},),
    )


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
        if "angular momentum" in lower:
            return "Angular momentum is the rotational counterpart of linear momentum. It depends on how much mass is rotating, how far it is from the axis, and how fast it is rotating."
        if "euclidean geometry" in lower:
            return "Euclidean geometry is the geometry of flat space: points, lines, angles, triangles, circles, and shapes measured with Euclid's familiar rules."
        if "chemistry" in lower:
            return "I will answer the chemistry question on its own terms and will not apply the reference-correction lesson unless the chemistry question actually depends on conversational reference."
    if transfer.get("applied"):
        if "style" in lower or "explain" in lower:
            return "Short version: I will answer more directly here and avoid repeating the same clarification unless it changes the meaning."
        return "I will interpret that in the current conversational context first, then ask only if the ambiguity would change the answer."
    if "how are you" in lower:
        return "I'm here and running. We can chat normally."
    if "what are you doing" in lower:
        return "I'm keeping ordinary chat responsive while the bounded conversational objective continues in the background."
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


def render_goal_review(state: ConversationalRuntimeState, *, status: str = "implementation_review_required") -> tuple[ConversationalRuntimeState, str]:
    objective = state.active_objective
    objective_id = objective.objective_id if objective else ""
    active_lessons = _active_lessons(state)
    active_decisions = tuple(item for item in state.turn_relation_decisions if item.active_goal_id == objective_id)
    active_provider_authorities = tuple(auth for auth in state.provider_authorities if auth.get("objective_id") == objective_id)
    active_insufficiencies = tuple(item for item in state.local_semantic_insufficiencies if item.goal_id == objective_id)
    goal_label = "Language understanding"
    completed = "I reached an implementation-review boundary for the active language-comprehension goal."
    learned = []
    if active_decisions:
        learned.append("foreground messages must be routed separately from background goal work")
    if active_insufficiencies:
        learned.append("external escalation requires a recorded local insufficiency first")
    if active_lessons:
        learned.append(f"{len(active_lessons)} scoped correction-derived lesson(s) are available")
    if not learned:
        learned.append("no durable learning has been validated yet")
    retained = [lesson.summary for lesson in active_lessons[-3:]] or ["no scoped lessons retained"]
    rejected = [item.rejection_reason for item in active_decisions[-5:] if item.rejection_reason] or ["no rejected lesson applicability recorded"]
    unresolved = []
    if status == "implementation_review_required":
        unresolved.append("implementation review is required before source-level semantic capability changes")
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
        "Next recommended step:\nReview the proposed foreground-isolation and local-first repair before any broader semantic capability implementation."
    )
    review = {
        "review_id": stable_id("goal-review", state.runtime_id, str(len(state.goal_reviews) + 1), status),
        "status": status,
        "objective_id": objective.objective_id if objective else "",
        "text": review_text,
        "provider_use": provider_use,
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


def _replace_state(state: ConversationalRuntimeState, **updates: Any) -> ConversationalRuntimeState:
    payload = state.as_record()
    payload.update(updates)
    return _state_from_record(payload)
