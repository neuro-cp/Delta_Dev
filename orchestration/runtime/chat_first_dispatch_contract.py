"""Pure shadow planning for the chat-first dispatch migration.

The planner intentionally does not execute, persist, render, or mutate runtime
state. DELTA.py records its output only as bounded in-memory diagnostics while
the legacy boolean routing path remains authoritative.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence
import json
import re

from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    ConversationTurn,
    ConversationalRuntimeState,
    classify_conversational_intent,
    reconcile_queued_reference_turn,
)
from orchestration.runtime.delta_1_0_common import stable_id


SCHEMA_VERSION = "chat_first_dispatch_contract_1_v1"
_CONTROL_TYPES = {
    "persistent_or_session_goal": "create_goal",
    "direct_correction": "correction",
    "authority_changing_or_risky_instruction": "authority_change",
    "stop_or_redirect": "pause_goal",
}
_CONTROL_WORDS = ("pause", "resume", "stop", "review", "approve", "adopt", "provider", "diagnostic", "replay", "evidence")
_GOAL_CONTEXT_TERMS = ("reference", "correction", "pronoun", "style", "verbosity", "lesson", "implied", "queued", "topic switch", "active goal")


@dataclass(frozen=True)
class MessageSegment:
    text: str
    kind: str
    confidence: float

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForegroundDispatch:
    requested: bool
    owner: str = "none"
    response_text: str = ""
    response_kind: str = "none"
    clarification_required: bool = False
    clarification_prompt: str = ""
    topic_id: str = ""
    referenced_turn_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    renderer: str = "none"
    should_render: bool = False
    render_order: int = 10

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlDispatch:
    detected: bool
    control_type: str = ""
    action: str = ""
    target_id: str = ""
    authority_effect: str = "none"
    requires_explicit_approval: bool = False
    approval_request_id: str = ""
    applied: bool = False
    deferred: bool = False
    denied: bool = False
    acknowledgment_text: str = ""
    should_render_acknowledgment: bool = False
    source_clause_index: int = -1

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BackgroundDispatch:
    attach_turn_as_evidence: bool
    objective_id: str = ""
    campaign_id: str = ""
    evidence_scope: str = "none"
    worker_signal: str = "none"
    start_requested: bool = False
    continuation_requested: bool = False
    phase_hint: str = ""

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PendingRequestDispatch:
    request_detected: bool
    request_id: str = ""
    request_type: str = ""
    resolution: str = ""
    constraints: Mapping[str, Any] = field(default_factory=dict)
    consume_once: bool = False
    already_consumed: bool = False
    reply_bound: bool = False

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClauseDispatch:
    clause_index: int
    text: str
    segment_kind: str
    control_type: str = ""
    foreground_requested: bool = False
    pending_request_id: str = ""
    state_mutation: str = "none"
    terminal_disposition: str = "unassigned"
    execution_order: int = 0
    dedupe_key: str = ""

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PersistenceDispatch:
    persist_user_turn: bool = True
    persist_foreground_response: bool = False
    persist_control_record: bool = False
    persist_background_evidence: bool = False
    persist_events: bool = False
    transcript_write_count: int = 1
    expected_single_user_turn: bool = True

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventPublication:
    event_id: str
    event_type: str
    objective_id: str
    scope: str
    text: str
    priority: str
    publish_inline: bool
    dedupe_key: str
    already_published: bool = False
    render_order: int = 30

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompatibilityDispatch:
    legacy_handler_consume: bool | None = None
    legacy_fallthrough: bool | None = None
    legacy_response_text: str = ""
    legacy_state_changed: bool | None = None
    compatibility_mode: str = "shadow_only"
    mismatch_detected: bool = False

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MessageDispatchResult:
    message_id: str
    user_turn_id: str
    original_message: str
    segments: tuple[MessageSegment, ...]
    segmentation_confidence: float
    unresolved_remainder: str
    foreground: ForegroundDispatch
    control: ControlDispatch
    controls: tuple[ControlDispatch, ...]
    clauses: tuple[ClauseDispatch, ...]
    background: BackgroundDispatch
    pending_request: PendingRequestDispatch
    persistence: PersistenceDispatch
    events: tuple[EventPublication, ...]
    diagnostics: Mapping[str, Any]
    compatibility: CompatibilityDispatch
    created_at: str = "planning_only"
    schema_version: str = SCHEMA_VERSION

    def as_record(self, *, include_message_text: bool = True) -> dict[str, Any]:
        record = asdict(self)
        if not include_message_text:
            record["original_message"] = ""
            record["segments"] = [
                {"kind": item["kind"], "confidence": item["confidence"], "length": len(item["text"])}
                for item in record["segments"]
            ]
        return json.loads(json.dumps(record, sort_keys=True, default=str))

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "MessageDispatchResult":
        payload = dict(record)
        payload["segments"] = tuple(MessageSegment(**dict(item)) for item in payload.get("segments", ()))
        foreground = dict(payload.get("foreground") or {})
        foreground["referenced_turn_ids"] = tuple(foreground.get("referenced_turn_ids", ()))
        payload["foreground"] = ForegroundDispatch(**foreground)
        payload["control"] = ControlDispatch(**dict(payload.get("control") or {}))
        payload["controls"] = tuple(ControlDispatch(**dict(item)) for item in payload.get("controls", ()))
        if not payload["controls"] and payload["control"].detected:
            payload["controls"] = (payload["control"],)
        payload["clauses"] = tuple(ClauseDispatch(**dict(item)) for item in payload.get("clauses", ()))
        payload["background"] = BackgroundDispatch(**dict(payload.get("background") or {}))
        pending = dict(payload.get("pending_request") or {})
        constraints = dict(pending.get("constraints") or {})
        for key in ("permitted_data", "prohibited_data"):
            if key in constraints:
                constraints[key] = tuple(constraints[key])
        pending["constraints"] = constraints
        payload["pending_request"] = PendingRequestDispatch(**pending)
        payload["persistence"] = PersistenceDispatch(**dict(payload.get("persistence") or {}))
        payload["events"] = tuple(EventPublication(**dict(item)) for item in payload.get("events", ()))
        payload["compatibility"] = CompatibilityDispatch(**dict(payload.get("compatibility") or {}))
        return cls(**payload)


def _normalize(message: str) -> str:
    return " ".join(str(message or "").split())


def segment_message(message: str) -> tuple[tuple[MessageSegment, ...], float, str]:
    """Bounded segmentation for explicit mixed clauses, not general parsing."""
    text = _normalize(message)
    if not text:
        return (), 1.0, ""
    foreground_match = re.search(r"\b(tell me\b.+)$", text, flags=re.IGNORECASE)
    background_preface = re.search(r"\b(?:while you(?:'re| are) working|while the goal is running|in the background)\b", text, flags=re.IGNORECASE)
    if foreground_match and background_preface and foreground_match.start() > 0:
        prefix = text[:foreground_match.start()].strip(" ,.;")
        foreground = foreground_match.group(1).strip()
        return (
            MessageSegment(text=prefix, kind="context_prefix", confidence=0.92),
            MessageSegment(text=foreground, kind="foreground_clause", confidence=0.96),
        ), 0.92, ""
    if re.search(r"\bstop\s+that\s+and\s+work\s+on\b", text, flags=re.IGNORECASE):
        return (MessageSegment(text=text, kind="unsegmented", confidence=0.94),), 0.94, ""
    connector = (
        r"(?:[.;!?]\s+(?:also\s+)?)(?=(?:your\s+new\s+goal|new\s+goal|stop|pause|resume|continue|review|show|approve|adopt|deny|don't|do\s+not|no,|yes,|i\s+meant|what|why|how|is|are|was|were|do|does|did|can|could|should|would|explain|remind|tell))"
        r"|(?:\s+also,?\s+)(?=(?:your\s+new\s+goal|new\s+goal|start|study|work\s+on|keep\s+working|continue|stop|pause|resume|review|show|approve|adopt|deny|don't|do\s+not|no,|yes,|you\s+may|what|why|how|is|are|was|were|do|does|did|can|could|should|would|explain|remind|tell))"
        r"|(?:\s+(?:and|but|then|while)\s+)(?=(?:your\s+new\s+goal|new\s+goal|start|study|work\s+on|keep\s+working|continue|stop|pause|resume|review|show|approve|adopt|deny|don't|do\s+not|no,|yes,|you\s+may|what|why|how|is|are|was|were|do|does|did|can|could|should|would|explain|remind|tell))"
    )
    parts = [part.strip(" ,.;") for part in re.split(connector, text, flags=re.IGNORECASE) if part.strip(" ,.;")]
    if not parts:
        return (MessageSegment(text=text, kind="unsegmented", confidence=0.9),), 0.9, ""
    if len(parts) == 1:
        return (MessageSegment(text=text, kind="unsegmented", confidence=0.9),), 0.9, ""
    return tuple(MessageSegment(text=part, kind="explicit_clause", confidence=0.94) for part in parts), 0.94, ""


def _resolution_kind(message: str) -> str:
    lower = _normalize(message).lower()
    if re.search(r"\bshow(?:\s+me)?\s+(?:the\s+)?evidence\b", lower):
        return "show_evidence"
    if "not approved" in lower or lower.startswith(("no", "deny")) or "continue locally" in lower or "do not use" in lower or "don't use" in lower:
        return "denied"
    if "approve" in lower or "adopt" in lower or "use only one call" in lower or "use one call" in lower or "may use" in lower or lower.startswith(("yes", "okay", "ok")):
        return "approved"
    if "prioritize" in lower:
        return "directional"
    return ""


def _matching_pending_request(state: ConversationalRuntimeState, message: str) -> ChatAddressableRequest | None:
    resolution = _resolution_kind(message)
    if not resolution:
        return None
    eligible = [item for item in state.pending_chat_requests if item.status == "pending" and not item.consumption_count]
    if len(eligible) != 1:
        return None
    request = eligible[0]
    if request.request_type == "provider_authority" and resolution in {"approved", "denied"}:
        return request
    if request.request_type == "capability_adoption_and_restart" and resolution in {"approved", "denied", "show_evidence"}:
        return request
    if request.request_type == "directional_question" and resolution in {"approved", "denied", "directional"}:
        return request
    if request.request_type == "local_model_execution" and resolution in {"approved", "denied"}:
        return request
    return None


def _pending_reference_clarification(state: ConversationalRuntimeState) -> ChatAddressableRequest | None:
    return next(
        (
            item for item in reversed(state.pending_chat_requests)
            if item.status == "pending"
            and not item.consumption_count
            and item.request_type == "reference_clarification"
        ),
        None,
    )


def _looks_like_reference_clarification_reply(clause: str) -> bool:
    lower = _normalize(clause).lower()
    if "?" in lower:
        return False
    return bool(re.search(r"\b(?:i\s+meant|i\s+mean|the\s+first|the\s+second|the\s+earlier|the\s+later|previous|prior|not\s+the|that\s+one)\b", lower))


def _control_for_clause(state: ConversationalRuntimeState, clause: str) -> tuple[ControlDispatch, PendingRequestDispatch]:
    request = _matching_pending_request(state, clause)
    if request:
        resolution = _resolution_kind(clause)
        control_type = {
            "provider_authority": "provider_approval",
            "capability_adoption_and_restart": "capability_adoption",
            "local_model_execution": "local_model_permission",
            "directional_question": "side_thread_resolution",
        }.get(request.request_type, "side_thread_resolution")
        return (
            ControlDispatch(True, control_type, "resolve_pending_request", request.request_id, "provider_bound" if control_type == "provider_approval" else "none", control_type == "provider_approval", request.request_id, deferred=True, denied=resolution == "denied", should_render_acknowledgment=True),
            PendingRequestDispatch(True, request.request_id, request.request_type, resolution, {"objective_id": request.objective_id, "max_calls": request.max_calls, "max_spend_usd": request.max_spend_usd, "prohibited_data": request.prohibited_data}, True, bool(request.consumption_count), True),
        )
    if _resolution_kind(clause):
        eligible = [item for item in state.pending_chat_requests if item.status == "pending" and not item.consumption_count]
        if len(eligible) > 1:
            return ControlDispatch(True, "clarification", "clarify_pending_request", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    lower = _normalize(clause).lower()
    contradictory_pairs = (
        ("adopt", "don't adopt"),
        ("stop", "keep working"),
        ("start", "don't start"),
        ("start", "keep the goal paused"),
    )
    if any(all(marker in lower for marker in pair) for pair in contradictory_pairs):
        return ControlDispatch(True, "clarification", "clarify_conflicting_control", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if re.search(r"\b(?:how|why) did you (?:route|misroute)\b|\bdecision record\b", lower):
        return ControlDispatch(True, "diagnostic_request", "route_advanced", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if re.search(r"\b(?:are you|is the runtime|chat runtime|runtime state|goal state|pending requests?|queued|last user question|last question|recorded once|discarded)\b", lower) and re.search(r"\b(?:paused|running|working|pending|queued|state|status|exactly once|how many|last|discarded|expired)\b", lower):
        return ControlDispatch(True, "runtime_state_query", "render_runtime_state", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if state.active_objective and re.search(r"\bstop\s+(?:working\s+on\s+)?(?:that|this|the\s+active\s+goal|goal)\b", lower):
        return ControlDispatch(True, "stop_goal", "stop", state.active_objective.objective_id, deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    pending_reference = _pending_reference_clarification(state)
    if pending_reference and _looks_like_reference_clarification_reply(clause):
        return (
            ControlDispatch(True, "reference_clarification_resolution", "resolve_reference_clarification", pending_reference.request_id, deferred=True, should_render_acknowledgment=True),
            PendingRequestDispatch(True, pending_reference.request_id, pending_reference.request_type, "resolved", {"objective_id": pending_reference.objective_id}, True, False, True),
        )
    if state.active_objective and any(token in lower for token in ("that", "it", "this", "prior", "previous", "earlier")) and any(token in lower for token in ("goal", "topic", "subject", "reference")):
        provisional = ConversationTurn(
            turn_id=stable_id("chat-first-reference-provisional", state.runtime_id, clause),
            role="user",
            text=clause,
            intent_type="ordinary_conversation_queued",
            objective_id=state.active_objective.objective_id,
        )
        decision = reconcile_queued_reference_turn(state, provisional)
        if decision.clarification_required:
            return ControlDispatch(True, "reference_clarification", "create_reference_clarification", state.active_objective.objective_id, deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "save state" in lower and "restart" in lower or lower.startswith("restart"):
        return ControlDispatch(True, "restart", "save_and_restart", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "continue where you left off" in lower or "keep working on" in lower or "keep working locally" in lower:
        return ControlDispatch(True, "goal_continuation", "continue_objective", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "stop" in lower and any(marker in lower for marker in ("instead", "work on", "study batteries", "battery")):
        return ControlDispatch(True, "replace_goal", "replace_objective", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "no, i meant that earlier thing" in lower:
        return ControlDispatch(True, "clarification", "clarify_correction_reference", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if any(marker in lower for marker in ("no, i meant that earlier", "i meant your earlier answer", "that was the jeep", "don't apply that rule", "keep that rule out", "explain things more simply")):
        return ControlDispatch(True, "correction", "attach_correction", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "do not use provider" in lower or "don't use provider" in lower:
        return ControlDispatch(True, "provider_prohibition", "record_provider_prohibition", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if re.search(r"\breview (?:the )?(?:approach|semantic.*capability)|\bcapability review\b", lower):
        return ControlDispatch(True, "capability_review", "render_capability_review", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if state.active_objective and any(term in lower for term in ("provider", "openai", "gpt", "external example", "outside example", "learning packet")) and any(term in lower for term in ("request", "ask", "recommend", "need", "use")):
        return ControlDispatch(True, "provider_request", "request_provider_packet", state.active_objective.objective_id, deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "semantic" in lower and "reconciliation" in lower and any(term in lower for term in ("review", "capability", "adopt")):
        return ControlDispatch(True, "capability_review", "render_capability_review", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    lifecycle_control = ("pause" in lower and "goal" in lower) or ("resume" in lower and "goal" in lower) or ("stop" in lower and "goal" in lower) or ("review" in lower and "goal" in lower)
    if state.active_objective and not lifecycle_control and any(term in lower for term in _GOAL_CONTEXT_TERMS):
        return ControlDispatch(True, "goal_continuation", "preserve_legacy_goal_context", state.active_objective.objective_id, deferred=True), PendingRequestDispatch(False)
    if "adopt" in lower and not any(term in lower for term in ("recommend", "whether", "should")):
        return ControlDispatch(True, "capability_adoption", "clarify_target", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if re.search(r"\b(?:how is|status of|progress on).{0,40}\bgoal\b", lower):
        return ControlDispatch(True, "goal_status", "render_status", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if re.search(r"\b(?:show me )?(?:what you(?:'ve| have) learned|goal review)\b", lower):
        return ControlDispatch(True, "goal_review", "render_review", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if re.search(r"\b(?:your\s+)?(?:new\s+)?goal\s+(?:is|today)\b", lower) or lower.startswith(("work on ", "keep studying ", "keep working ", "study ", "start studying ", "start working ")):
        control_type, action = ("replace_goal", "replace_objective") if state.active_objective else ("create_goal", "register_objective")
        return ControlDispatch(True, control_type, action, state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "pause" in lower and "goal" in lower:
        return ControlDispatch(True, "pause_goal", "pause", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "resume" in lower and "goal" in lower:
        return ControlDispatch(True, "resume_goal", "resume", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "stop" in lower and "goal" in lower:
        return ControlDispatch(True, "stop_goal", "stop", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if "review" in lower and "goal" in lower:
        return ControlDispatch(True, "goal_review", "render_review", state.active_objective.objective_id if state.active_objective else "", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    if any(term in lower for term in ("evidence", "replay", "diagnostic")) and any(term in lower for term in ("show", "request", "run", "open")):
        return ControlDispatch(True, "diagnostic_request", "route_advanced", deferred=True, should_render_acknowledgment=True), PendingRequestDispatch(False)
    intent = classify_conversational_intent(clause, active_objective=state.active_objective, recent_turns=state.conversation)
    control_type = _CONTROL_TYPES.get(intent.intent_type, "")
    if not control_type:
        return ControlDispatch(False), PendingRequestDispatch(False)
    action = "register_objective" if control_type == "create_goal" else control_type
    if control_type == "create_goal" and state.active_objective:
        control_type, action = "replace_goal", "replace_objective"
    return (
        ControlDispatch(True, control_type, action, state.active_objective.objective_id if state.active_objective else "", "material_boundary" if control_type == "authority_change" else "none", control_type == "authority_change", deferred=True, should_render_acknowledgment=True),
        PendingRequestDispatch(False),
    )


def _foreground_requested(clause: str, control: ControlDispatch) -> bool:
    lower = _normalize(clause).lower()
    if not clause:
        return False
    if lower in {"do not change anything else", "don't change anything else", "change nothing else"}:
        return False
    if re.search(r"\b(?:please\s+)?wait until\b", lower) and re.search(r"\b(?:reasoning step|current step|work step|cycle)\b", lower):
        return False
    if control.detected:
        return bool(re.search(r"\b(?:what|why|how|explain|tell me)\b", lower)) and control.control_type in {
            "correction",
            "provider_prohibition",
            "pause_goal",
            "resume_goal",
            "stop_goal",
        }
    return any(token in lower for token in ("?", "what", "why", "how", "explain", "remind me", "tell me", "color")) or not control.detected


def plan_message_dispatch(state: ConversationalRuntimeState, message: str) -> MessageDispatchResult:
    """Return a deterministic plan without mutating ``state`` or external systems."""
    normalized = _normalize(message)
    segments, segmentation_confidence, remainder = segment_message(normalized)
    state_key = {
        "runtime_id": state.runtime_id,
        "lifecycle": state.lifecycle_state,
        "objective_id": state.active_objective.objective_id if state.active_objective else "",
        "pending": [(item.request_id, item.request_type, item.status, item.consumption_count) for item in state.pending_chat_requests],
    }
    message_id = stable_id("chat-first-dispatch", json.dumps(state_key, sort_keys=True), normalized)
    controls: list[ControlDispatch] = []
    clause_plans: list[ClauseDispatch] = []
    pending = PendingRequestDispatch(False)
    foreground_clauses: list[str] = []
    for index, segment in enumerate(segments):
        if segment.kind == "context_prefix":
            clause_plans.append(ClauseDispatch(index, segment.text, segment.kind, terminal_disposition="context_retained", execution_order=index))
            continue
        control, candidate_pending = _control_for_clause(state, segment.text)
        if control.detected:
            planned = ControlDispatch(**{**control.as_record(), "source_clause_index": index})
            dedupe_key = (planned.control_type, planned.action, planned.target_id)
            if not any((item.control_type, item.action, item.target_id) == dedupe_key for item in controls):
                controls.append(planned)
        if candidate_pending.request_detected:
            pending = candidate_pending
        foreground_requested = _foreground_requested(segment.text, control)
        if foreground_requested:
            foreground_clauses.append(segment.text)
        if control.detected and foreground_requested:
            disposition = "control_and_foreground_planned"
        elif control.detected:
            disposition = "control_planned"
        elif foreground_requested:
            disposition = "foreground_planned"
        else:
            disposition = "observed_noop"
        clause_plans.append(ClauseDispatch(
            index,
            segment.text,
            segment.kind,
            control_type=control.control_type if control.detected else "",
            foreground_requested=foreground_requested,
            pending_request_id=candidate_pending.request_id if candidate_pending.request_detected else "",
            state_mutation="possible" if control.detected else "none",
            terminal_disposition=disposition,
            execution_order=index,
            dedupe_key=stable_id("chat-first-clause", message_id, str(index), segment.text, control.control_type if control.detected else "foreground"),
        ))
    control = controls[0] if controls else ControlDispatch(False)
    control_types = {item.control_type for item in controls}
    if ({"stop_goal", "goal_continuation"} <= control_types) or ({"capability_adoption", "provider_approval"} <= control_types):
        clarification = ControlDispatch(True, "clarification", "clarify_conflicting_control", deferred=True, should_render_acknowledgment=True)
        controls = [clarification]
        control = clarification
    foreground = ForegroundDispatch(
        requested=bool(foreground_clauses),
        owner="rc2_router" if foreground_clauses else "none",
        response_kind="foreground_answer" if foreground_clauses else "none",
        confidence=segmentation_confidence if foreground_clauses else 0.0,
        renderer="render_route" if foreground_clauses else "none",
        should_render=bool(foreground_clauses),
    )
    objective_id = state.active_objective.objective_id if state.active_objective else ""
    campaign_id = next((str(item.get("campaign_id") or "") for item in state.capability_campaigns if item.get("objective_id") == objective_id), "")
    background = BackgroundDispatch(
        attach_turn_as_evidence=bool(objective_id or control.control_type in {"create_goal", "replace_goal", "correction"}),
        objective_id=objective_id,
        campaign_id=campaign_id,
        evidence_scope="active_goal" if objective_id else "new_goal" if control.detected else "none",
        worker_signal="observe_only",
        start_requested=control.control_type in {"create_goal", "replace_goal"},
        continuation_requested=bool(objective_id and foreground_clauses),
        phase_hint="planner_only",
    )
    persistence = PersistenceDispatch(
        persist_user_turn=True,
        persist_foreground_response=foreground.requested,
        persist_control_record=control.detected,
        persist_background_evidence=background.attach_turn_as_evidence,
        transcript_write_count=1,
        expected_single_user_turn=True,
    )
    return MessageDispatchResult(
        message_id=message_id,
        user_turn_id=stable_id("chat-first-user-turn", state.runtime_id, normalized),
        original_message=normalized,
        segments=segments,
        segmentation_confidence=segmentation_confidence,
        unresolved_remainder=remainder,
        foreground=foreground,
        control=control,
        controls=tuple(controls),
        clauses=tuple(clause_plans),
        background=background,
        pending_request=pending,
        persistence=persistence,
        events=(),
        diagnostics={"planner": "pure", "control_count": len(controls), "foreground_clause_count": len(foreground_clauses), "state_key": state_key},
        compatibility=CompatibilityDispatch(),
    )
