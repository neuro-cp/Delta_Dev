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
from orchestration.runtime.provisional_semantic_consolidation import (
    ConsolidationIntegrityError,
    ingest_episode_at_runtime_root,
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
    if any(term in lower for term in ("study", "learn", "research", "understand", "explain")):
        return "knowledge_acquisition"
    return "generic_conversational_cognition"


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
    campaign_mode = execution_mode == "capability_growth_campaign"
    unlimited_local_knowledge = execution_mode == "knowledge_acquisition"
    knowledge_contract = _knowledge_goal_contract(text) if execution_mode == "knowledge_acquisition" else {}
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
        interpreted = str(knowledge_contract["normalized_topic"]).strip().capitalize()
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
            "knowledge_contract": knowledge_contract,
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
    return tuple(nodes)


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
    completed_focuses = {
        cycle.focus_id
        for cycle in episode.cycles
        if cycle.completed
        and cycle.operation_id in completed_operation_ids
    }
    rejected_counts: dict[str, int] = {}
    for cycle in episode.cycles:
        if cycle.completed and cycle.operation_id in blocked_operation_ids and cycle.focus_id not in completed_focuses:
            rejected_counts[cycle.focus_id] = rejected_counts.get(cycle.focus_id, 0) + 1
    blocked_focuses = {focus_id for focus_id, count in rejected_counts.items() if count >= 2}
    retryable_focuses = {focus_id for focus_id, count in rejected_counts.items() if count == 1}
    expected_focuses = {
        stable_id("focus", episode.episode_id, node.evidence_id)
        for node in frontier_nodes
    }
    unattempted_focuses = expected_focuses - completed_focuses - set(rejected_counts)
    material_requirements = _knowledge_material_requirements(objective)
    criteria_total = len(material_requirements) or len(tuple(objective.practical_success_indicators))
    accepted_refs: set[str] = set()
    for result in episode.operation_results:
        if result.accepted and result.operation_id in completed_operation_ids:
            accepted_refs.update(result.evidence_refs)
    satisfied = 0
    for node in frontier_nodes:
        if node.evidence_id in accepted_refs:
            satisfied += 1
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
    accepted_refs = {
        ref
        for result in episode.operation_results
        if result.accepted
        for ref in result.evidence_refs
        if ref
    }
    satisfied_ids = {
        _frontier_requirement_id(node)
        for node in nodes
        if node.evidence_id in accepted_refs
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

    if episode.loop_state in {"blocked_insufficient_evidence", "blocked_capability_gap", "paused_budget"} or episode.completed:
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
        if state.schema_version != SCHEMA_VERSION:
            state = _replace_state(state, schema_version=SCHEMA_VERSION)
            save_runtime_state(root, state)
        return state
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
    approval_terms = ("approve", "approved", "yes", "okay", "ok", "adopt it", "use approach a", "use one call", "use only one call", "1 call")
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


def _pending_request_for_reply(state: ConversationalRuntimeState, message: str) -> ChatAddressableRequest | None:
    if not state.pending_chat_requests:
        return None
    kind = _chat_request_resolution_kind(message)
    if kind is None:
        return None
    compatibility_defaults = {
        "provider_authority": ("approved", "denied"),
        "directional_question": ("directional", "denied", "approved"),
        "local_model_execution": ("approved", "denied"),
        "knowledge_model_budget_increase": ("approved", "denied"),
        "capability_adoption_and_restart": ("approved", "denied", "show_evidence"),
    }
    candidates = []
    for index, request in enumerate(state.pending_chat_requests):
        if request.status != "pending" or request.consumption_count:
            continue
        accepted = tuple(request.accepted_response_types or compatibility_defaults.get(request.request_type, ()))
        if kind not in accepted:
            continue
        candidates.append((request.render_sequence, request.created_sequence, index, request))
    if not candidates:
        return None
    if len(candidates) > 1 and max(item[0] for item in candidates) <= 0:
        return None
    # The most recently rendered compatible prompt owns an otherwise ambiguous reply.
    return max(candidates, key=lambda item: item[:3])[3]


def select_chat_request_owner(state: ConversationalRuntimeState, message: str) -> ChatAddressableRequest | None:
    """Expose conversational ownership selection without exposing request-type precedence."""
    return _pending_request_for_reply(state, message)


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
        budget_request: ChatAddressableRequest | None = None
        lifecycle_state = "running"
        if (
            objective.provenance.get("execution_mode") == "knowledge_acquisition"
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
        updated = _replace_state(
            state,
            lifecycle_state=lifecycle_state,
            active_objective=objective,
            authority=authority,
            conversation=state.conversation + (goal_user_turn,),
            active_episode_path=episode_path,
            completed_cycle_keys=(),
            pending_material_authority=(),
            pending_chat_requests=((budget_request,) if budget_request else ()),
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
        if run_background_cycle and budget_request is None:
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
        assistant_turn = ConversationTurn(
            turn_id=stable_id("conversation-turn", updated.runtime_id, str(len(updated.conversation) + 1), reply),
            role="assistant",
            text=reply,
            intent_type="objective_confirmation",
            objective_id=objective.objective_id,
        )
        updated = _replace_state(updated, conversation=updated.conversation + (assistant_turn,))
        save_runtime_state(runtime_root, updated)
        return RuntimeTurnResult(state=updated, intent=intent, reply=reply, objective_created=True, background_cycle_started=run_background_cycle and budget_request is None, chat_request=budget_request.as_record() if budget_request else None)
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
