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
    background_cycle_started: bool = False
    transfer_applied: bool = False
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
        authority = derive_standing_authority(objective)
        episode_path = str(Path(runtime_root) / "active_episode.json")
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
        focus = {"event": "objective_registered", "objective_id": objective.objective_id, "episode_id": episode.episode_id, "at": utc_now()}
        updated = _replace_state(
            state,
            active_objective=objective,
            authority=authority,
            conversation=state.conversation + (user_turn,),
            active_episode_path=episode_path,
            focus_history=state.focus_history + (focus,),
            objective_progress=state.objective_progress + ({"event": "standing_authority_assigned", "authority_id": authority.authority_id, "at": utc_now()},),
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
    transfer = infer_lesson_transfer(state, message)
    reply = _ordinary_reply(message, transfer)
    assistant_turn = ConversationTurn(
        turn_id=stable_id("conversation-turn", state.runtime_id, str(len(state.conversation) + 2), reply),
        role="assistant",
        text=reply,
        intent_type="ordinary_response",
        objective_id=state.active_objective.objective_id if state.active_objective else "",
    )
    progress = state.objective_progress
    if transfer["applied"]:
        progress = progress + ({"event": "lesson_transfer_applied", "lesson_id": transfer["lesson_id"], "message": message, "at": utc_now()},)
    updated = _replace_state(state, conversation=state.conversation + (user_turn, assistant_turn), objective_progress=progress)
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


def infer_lesson_transfer(state: ConversationalRuntimeState, message: str) -> dict[str, Any]:
    tokens = set(re.findall(r"[a-z0-9]{3,}", message.lower()))
    for lesson in reversed(state.accepted_lessons):
        applies = set(lesson.applicable_when)
        blocked = set(lesson.not_applicable_when)
        if tokens & applies and not tokens & blocked:
            return {"applied": True, "lesson_id": lesson.lesson_id, "strategy_update": lesson.strategy_update}
    return {"applied": False, "lesson_id": "", "strategy_update": ""}


def _ordinary_reply(message: str, transfer: Mapping[str, Any]) -> str:
    lower = message.lower()
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
    if not state.accepted_lessons:
        failures.append("correction_stored_without_transfer")
    if any(lesson.authority_effect != "none" for lesson in state.accepted_lessons):
        failures.append("salience_grants_authority")
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": not failures,
        "failure_reasons": failures,
        "objective_id": state.active_objective.objective_id if state.active_objective else "",
        "correction_count": len(state.corrections),
        "accepted_lesson_count": len(state.accepted_lessons),
        "background_cycle_count": len(state.completed_cycle_keys),
        "pending_material_authority_count": len(state.pending_material_authority),
    }


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
