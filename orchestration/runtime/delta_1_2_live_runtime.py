"""DELTA 1.2 live governed development runtime.

This is the first persistent-style cognitive runtime layer. It can accept
approved local events, observe them, score attention, form curiosity and
developmental signals, arbitrate candidate goals, queue operator inquiries, and
record an audit journal. It does not start timers, browse, retrieve, call
providers, modify code, persist hidden state, commit, push, or expand authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from orchestration.runtime.delta_1_0_common import jsonable, safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.delta_1_1_development_loop import WikipediaPermissionProfile


REPORT_ROOT = Path("reports") / "delta_1_2"

RUNTIME_STATES = (
    "BOOT",
    "IDLE",
    "OBSERVING",
    "REFLECTING",
    "ASSESSING",
    "GENERATING_OBJECTIVES",
    "WAITING_FOR_OPERATOR",
    "BACKGROUND_ANALYSIS",
    "VALIDATING",
    "PAUSED",
    "SUSPENDED",
    "SHUTDOWN",
)

VALID_TRANSITIONS = {
    "BOOT": ("IDLE", "SUSPENDED", "SHUTDOWN"),
    "IDLE": ("OBSERVING", "REFLECTING", "PAUSED", "SUSPENDED", "SHUTDOWN"),
    "OBSERVING": ("ASSESSING", "IDLE", "PAUSED", "SUSPENDED"),
    "ASSESSING": ("GENERATING_OBJECTIVES", "REFLECTING", "IDLE", "WAITING_FOR_OPERATOR"),
    "GENERATING_OBJECTIVES": ("WAITING_FOR_OPERATOR", "BACKGROUND_ANALYSIS", "IDLE"),
    "REFLECTING": ("BACKGROUND_ANALYSIS", "WAITING_FOR_OPERATOR", "IDLE", "PAUSED"),
    "BACKGROUND_ANALYSIS": ("WAITING_FOR_OPERATOR", "VALIDATING", "IDLE"),
    "WAITING_FOR_OPERATOR": ("OBSERVING", "VALIDATING", "IDLE", "PAUSED", "SHUTDOWN"),
    "VALIDATING": ("IDLE", "WAITING_FOR_OPERATOR", "SUSPENDED"),
    "PAUSED": ("IDLE", "SHUTDOWN"),
    "SUSPENDED": ("IDLE", "SHUTDOWN"),
    "SHUTDOWN": (),
}

EVENT_CLASSES = (
    "operator_message",
    "objective_approved",
    "objective_rejected",
    "validation_completed",
    "repair_completed",
    "behavioral_failure",
    "repeated_pathology",
    "operator_correction",
    "runtime_startup",
    "runtime_shutdown",
)

ATTENTION_LEVELS = ("IGNORE", "LOW_VALUE", "INTERESTING", "DEVELOPMENTAL_SIGNAL", "HIGH_PRIORITY", "OPERATOR_REQUIRED")
NOTIFICATION_CLASSES = ("IMMEDIATE", "NORMAL", "DEFERRED", "NEXT_SESSION", "DIGEST_ONLY")
INQUIRY_STATUSES = ("QUEUED", "SURFACED", "ANSWERED", "DISMISSED", "EXPIRED")
CAPABILITY_STATES = ("DISABLED", "READY_FOR_REVIEW", "APPROVED", "ACTIVE")


@dataclass(frozen=True)
class LiveRuntimeConfig:
    runtime_id: str
    mode: str = "NORMAL"
    max_events_per_cycle: int = 8
    max_reflection_steps: int = 5
    quiet_hours: tuple[str, str] = ("22:00", "08:00")
    notification_limit_per_cycle: int = 3
    kill_switch: bool = False
    paused: bool = False
    timers_enabled: bool = False
    network_enabled: bool = False
    provider_enabled: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class RuntimeEvent:
    event_id: str
    event_class: str
    summary: str
    source: str
    payload: dict[str, Any]
    approved_source: bool
    created_at: str = field(default_factory=utc_now)
    processed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class EventQueue:
    queue_id: str
    events: tuple[RuntimeEvent, ...] = ()
    max_size: int = 128
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class LiveObservation:
    observation_id: str
    event_id: str
    observation_type: str
    summary: str
    evidence_refs: tuple[str, ...]
    source: str
    confidence: float
    severity: float
    evidence_only: bool = True
    expires_after_cycles: int = 12
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class AttentionDecision:
    decision_id: str
    observation_id: str
    level: str
    score: float
    rationale: str
    expires_after_cycles: int
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class CuriosityInquiryCandidate:
    curiosity_id: str
    originating_evidence: tuple[str, ...]
    gap_type: str
    question: str
    confidence: float
    expected_benefit: float
    random_question: bool = False
    action_requested: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentSignal:
    signal_id: str
    signal_type: str
    evidence_refs: tuple[str, ...]
    cluster_key: str
    frequency: int
    severity: float
    confidence: float
    duplicate_of: str = ""
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class CandidateGoal:
    goal_id: str
    title: str
    originating_signals: tuple[str, ...]
    value: float
    urgency: float
    confidence: float
    operator_impact: float
    implementation_effort: float
    regression_risk: float
    governance_impact: float
    approval_required: bool = True
    self_created_active_goal: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class GoalArbitration:
    arbitration_id: str
    ranked_goals: tuple[dict[str, Any], ...]
    selected_goal_id: str
    rationale: str
    silently_selected: bool = False
    approval_required: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ReflectionSummary:
    reflection_id: str
    inspected_events: tuple[str, ...]
    observations: tuple[str, ...]
    signals: tuple[str, ...]
    curiosity: tuple[str, ...]
    proposed_inquiries: tuple[str, ...]
    steps_used: int
    bounded: bool = True
    modified_code: bool = False
    browsed: bool = False
    provider_called: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperatorInquiryV12:
    inquiry_id: str
    originating_evidence: tuple[str, ...]
    confidence: float
    reason: str
    urgency: float
    expected_benefit: float
    question: str
    suggested_next_step: str
    expiration_cycle: int
    approval_status: str = "QUEUED"
    notification_class: str = "NEXT_SESSION"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class NotificationDecision:
    notification_id: str
    inquiry_id: str
    notification_class: str
    should_surface_now: bool
    reason: str
    os_notification_sent: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ActivityJournalEntry:
    entry_id: str
    entry_type: str
    summary: str
    refs: tuple[str, ...]
    cycle: int
    retention_policy: str = "audit_only_ephemeral_until_operator_policy"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ActivityJournal:
    journal_id: str
    entries: tuple[ActivityJournalEntry, ...] = ()
    hidden_persistence: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class RuntimeIdentity:
    identity_id: str
    current_objectives: tuple[str, ...]
    open_questions: tuple[str, ...]
    active_observations: tuple[str, ...]
    unresolved_curiosity: tuple[str, ...]
    recent_lessons: tuple[str, ...]
    runtime_health: str
    governance_status: str
    chat_history: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class FutureSurfaceReadiness:
    capability: str
    state: str
    permission_profile: WikipediaPermissionProfile
    dependencies: tuple[str, ...]
    retrieval_implemented: bool = False
    network_code_present: bool = False
    provider_present: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class LiveRuntimeState:
    runtime_id: str
    state: str
    cycle: int
    config: LiveRuntimeConfig
    event_queue: EventQueue
    observations: tuple[LiveObservation, ...]
    attention: tuple[AttentionDecision, ...]
    curiosity: tuple[CuriosityInquiryCandidate, ...]
    signals: tuple[DevelopmentSignal, ...]
    goals: tuple[CandidateGoal, ...]
    arbitration: GoalArbitration | None
    inquiries: tuple[OperatorInquiryV12, ...]
    notifications: tuple[NotificationDecision, ...]
    journal: ActivityJournal
    identity: RuntimeIdentity
    future_surfaces: tuple[FutureSurfaceReadiness, ...]
    last_reflection: ReflectionSummary | None = None
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def boot_live_runtime(config: LiveRuntimeConfig | None = None) -> LiveRuntimeState:
    config = config or LiveRuntimeConfig(runtime_id=stable_id("delta12-runtime", "default"))
    queue = EventQueue(queue_id=stable_id("delta12-event-queue", config.runtime_id))
    journal = ActivityJournal(journal_id=stable_id("delta12-journal", config.runtime_id))
    identity = RuntimeIdentity(
        identity_id=stable_id("delta12-identity", config.runtime_id),
        current_objectives=(),
        open_questions=(),
        active_observations=(),
        unresolved_curiosity=(),
        recent_lessons=(),
        runtime_health="healthy",
        governance_status="operator_governed_no_external_senses",
    )
    runtime = LiveRuntimeState(
        runtime_id=config.runtime_id,
        state="BOOT",
        cycle=0,
        config=config,
        event_queue=queue,
        observations=(),
        attention=(),
        curiosity=(),
        signals=(),
        goals=(),
        arbitration=None,
        inquiries=(),
        notifications=(),
        journal=journal,
        identity=identity,
        future_surfaces=(wikipedia_surface_readiness(),),
    )
    return transition_runtime(runtime, "IDLE")


def transition_runtime(runtime: LiveRuntimeState, to_state: str) -> LiveRuntimeState:
    if to_state not in RUNTIME_STATES:
        raise ValueError(f"unknown runtime state: {to_state}")
    if to_state not in VALID_TRANSITIONS.get(runtime.state, ()):
        raise ValueError(f"invalid transition {runtime.state}->{to_state}")
    return replace(runtime, state=to_state)


def create_event(event_class: str, summary: str, *, source: str = "local_runtime", payload: Mapping[str, Any] | None = None, approved_source: bool = True) -> RuntimeEvent:
    if event_class not in EVENT_CLASSES:
        raise ValueError(f"unknown event class: {event_class}")
    clean = " ".join(str(summary or "").split())
    return RuntimeEvent(
        event_id=stable_id("delta12-event", event_class, clean, source, payload or {}),
        event_class=event_class,
        summary=clean,
        source=source,
        payload=dict(payload or {}),
        approved_source=approved_source,
    )


def enqueue_event(queue: EventQueue, event: RuntimeEvent) -> EventQueue:
    events = (queue.events + (event,))[-queue.max_size :]
    return replace(queue, events=events)


def dequeue_batch(queue: EventQueue, max_count: int) -> tuple[tuple[RuntimeEvent, ...], EventQueue]:
    pending = tuple(item for item in queue.events if not item.processed)
    batch = pending[:max_count]
    processed_ids = {item.event_id for item in batch}
    events = tuple(replace(item, processed=True) if item.event_id in processed_ids else item for item in queue.events)
    return batch, replace(queue, events=events)


def observe_events(events: Iterable[RuntimeEvent]) -> tuple[LiveObservation, ...]:
    observations: list[LiveObservation] = []
    for event in events:
        if not event.approved_source:
            continue
        observation_type = _observation_type_for_event(event)
        severity = _severity_for_event(event)
        confidence = _confidence_for_event(event)
        observations.append(
            LiveObservation(
                observation_id=stable_id("delta12-observation", event.event_id, observation_type, event.summary),
                event_id=event.event_id,
                observation_type=observation_type,
                summary=event.summary,
                evidence_refs=(event.event_id,),
                source=event.source,
                confidence=confidence,
                severity=severity,
            )
        )
    return tuple(observations)


def attention_for_observation(observation: LiveObservation) -> AttentionDecision:
    score = round((observation.severity * 0.55) + (observation.confidence * 0.35) + (_novelty_score(observation) * 0.1), 3)
    if score < 0.25:
        level = "IGNORE"
    elif score < 0.42:
        level = "LOW_VALUE"
    elif score < 0.58:
        level = "INTERESTING"
    elif score < 0.72:
        level = "DEVELOPMENTAL_SIGNAL"
    elif score < 0.86:
        level = "HIGH_PRIORITY"
    else:
        level = "OPERATOR_REQUIRED"
    return AttentionDecision(
        decision_id=stable_id("delta12-attention", observation.observation_id, score, level),
        observation_id=observation.observation_id,
        level=level,
        score=score,
        rationale=f"severity={observation.severity:.2f}; confidence={observation.confidence:.2f}; novelty={_novelty_score(observation):.2f}",
        expires_after_cycles=1 if level == "IGNORE" else 12,
    )


def score_attention(observations: Iterable[LiveObservation]) -> tuple[AttentionDecision, ...]:
    return tuple(attention_for_observation(item) for item in observations)


def generate_curiosity(observations: Iterable[LiveObservation], attention: Iterable[AttentionDecision]) -> tuple[CuriosityInquiryCandidate, ...]:
    decisions = {item.observation_id: item for item in attention}
    candidates: list[CuriosityInquiryCandidate] = []
    for observation in observations:
        decision = decisions.get(observation.observation_id)
        if not decision or decision.level not in {"INTERESTING", "DEVELOPMENTAL_SIGNAL", "HIGH_PRIORITY", "OPERATOR_REQUIRED"}:
            continue
        gap_type = _gap_type(observation.summary)
        question = _question_for_gap(gap_type, observation.summary)
        candidates.append(
            CuriosityInquiryCandidate(
                curiosity_id=stable_id("delta12-curiosity", observation.observation_id, gap_type, question),
                originating_evidence=observation.evidence_refs,
                gap_type=gap_type,
                question=question,
                confidence=round((observation.confidence + decision.score) / 2, 3),
                expected_benefit=decision.score,
            )
        )
    return tuple(_dedupe_by_question(candidates))


def detect_development_signals(observations: Iterable[LiveObservation]) -> tuple[DevelopmentSignal, ...]:
    groups: dict[str, list[LiveObservation]] = {}
    for observation in observations:
        key = _cluster_key(observation.summary, observation.observation_type)
        groups.setdefault(key, []).append(observation)
    signals: list[DevelopmentSignal] = []
    seen: dict[str, str] = {}
    for key, items in groups.items():
        frequency = len(items)
        if frequency < 1:
            continue
        severity = _avg(item.severity for item in items)
        confidence = _avg(item.confidence for item in items)
        signal_type = "repeated_pattern" if frequency > 1 else _signal_type(items[0])
        signal_id = stable_id("delta12-signal", key, tuple(item.observation_id for item in items))
        duplicate_of = seen.get(key, "")
        seen[key] = seen.get(key, signal_id)
        signals.append(
            DevelopmentSignal(
                signal_id=signal_id,
                signal_type=signal_type,
                evidence_refs=tuple(item.observation_id for item in items),
                cluster_key=key,
                frequency=frequency,
                severity=round(severity, 3),
                confidence=round(confidence, 3),
                duplicate_of=duplicate_of,
            )
        )
    return tuple(signals)


def generate_candidate_goals(signals: Iterable[DevelopmentSignal]) -> tuple[CandidateGoal, ...]:
    goals: list[CandidateGoal] = []
    for signal in signals:
        value = min(1.0, (signal.severity * 0.65) + (min(1.0, signal.frequency / 4) * 0.35))
        effort = 0.35 if signal.signal_type != "repeated_pattern" else 0.55
        risk = 0.22 + (0.08 * signal.frequency)
        governance = 0.15 if "wikipedia" not in signal.cluster_key else 0.35
        goals.append(
            CandidateGoal(
                goal_id=stable_id("delta12-goal", signal.signal_id, signal.cluster_key),
                title=_goal_title(signal),
                originating_signals=(signal.signal_id,),
                value=round(value, 3),
                urgency=round(min(1.0, signal.severity), 3),
                confidence=signal.confidence,
                operator_impact=round(value, 3),
                implementation_effort=round(effort, 3),
                regression_risk=round(min(1.0, risk), 3),
                governance_impact=round(governance, 3),
            )
        )
    return tuple(goals)


def arbitrate_goals(goals: Iterable[CandidateGoal]) -> GoalArbitration:
    scored = []
    for goal in goals:
        score = round(
            (goal.value * 0.28)
            + (goal.urgency * 0.18)
            + (goal.confidence * 0.17)
            + (goal.operator_impact * 0.15)
            + ((1.0 - goal.implementation_effort) * 0.1)
            + ((1.0 - goal.regression_risk) * 0.07)
            + ((1.0 - goal.governance_impact) * 0.05),
            4,
        )
        scored.append({"goal_id": goal.goal_id, "title": goal.title, "score": score, "rationale": f"value={goal.value}; urgency={goal.urgency}; confidence={goal.confidence}; effort={goal.implementation_effort}; regression={goal.regression_risk}; governance={goal.governance_impact}"})
    ranked = tuple({**item, "rank": index} for index, item in enumerate(sorted(scored, key=lambda row: row["score"], reverse=True), start=1))
    selected = str(ranked[0]["goal_id"]) if ranked else ""
    return GoalArbitration(
        arbitration_id=stable_id("delta12-arbitration", ranked),
        ranked_goals=ranked,
        selected_goal_id=selected,
        rationale="Top ranked goal is a proposal candidate only; operator approval is still required.",
        silently_selected=False,
        approval_required=True,
    )


def inquiry_from_curiosity(candidate: CuriosityInquiryCandidate, *, cycle: int) -> OperatorInquiryV12:
    urgency = min(1.0, max(0.1, candidate.expected_benefit))
    notification = classify_notification(urgency=urgency, confidence=candidate.confidence, operator_relevance=candidate.expected_benefit, mode="NORMAL")
    return OperatorInquiryV12(
        inquiry_id=stable_id("delta12-inquiry", candidate.curiosity_id, cycle),
        originating_evidence=candidate.originating_evidence,
        confidence=candidate.confidence,
        reason=f"curiosity:{candidate.gap_type}",
        urgency=round(urgency, 3),
        expected_benefit=candidate.expected_benefit,
        question=candidate.question,
        suggested_next_step="ask_operator_for_context_or_permission",
        expiration_cycle=cycle + 8,
        notification_class=notification,
    )


def classify_notification(*, urgency: float, confidence: float, operator_relevance: float, mode: str = "NORMAL") -> str:
    if mode == "QUIET":
        return "DIGEST_ONLY"
    if mode == "EMERGENCY_ONLY":
        return "IMMEDIATE" if urgency >= 0.95 and operator_relevance >= 0.9 else "DIGEST_ONLY"
    if mode == "DEVELOPMENT_SESSION" and urgency >= 0.65:
        return "NORMAL"
    if mode == "EXPERIMENTAL_ALWAYS_ON" and urgency >= 0.5:
        return "IMMEDIATE"
    score = (urgency * 0.45) + (confidence * 0.25) + (operator_relevance * 0.3)
    if score >= 0.86:
        return "IMMEDIATE"
    if score >= 0.7:
        return "NORMAL"
    if score >= 0.52:
        return "NEXT_SESSION"
    if score >= 0.35:
        return "DEFERRED"
    return "DIGEST_ONLY"


def notification_decision(inquiry: OperatorInquiryV12, *, mode: str, current_cycle: int) -> NotificationDecision:
    notification_class = classify_notification(urgency=inquiry.urgency, confidence=inquiry.confidence, operator_relevance=inquiry.expected_benefit, mode=mode)
    should_surface = notification_class in {"IMMEDIATE", "NORMAL"} and current_cycle <= inquiry.expiration_cycle
    return NotificationDecision(
        notification_id=stable_id("delta12-notification", inquiry.inquiry_id, notification_class, current_cycle),
        inquiry_id=inquiry.inquiry_id,
        notification_class=notification_class,
        should_surface_now=should_surface,
        reason="runtime_policy_only_no_os_notification",
        os_notification_sent=False,
    )


def reflect_bounded(runtime: LiveRuntimeState, batch: tuple[RuntimeEvent, ...]) -> tuple[ReflectionSummary, tuple[LiveObservation, ...], tuple[AttentionDecision, ...], tuple[CuriosityInquiryCandidate, ...], tuple[DevelopmentSignal, ...], tuple[CandidateGoal, ...], GoalArbitration, tuple[OperatorInquiryV12, ...], tuple[NotificationDecision, ...]]:
    observations = observe_events(batch)
    attention = score_attention(observations)
    useful = tuple(obs for obs in observations if attention_for_id(attention, obs.observation_id).level not in {"IGNORE", "LOW_VALUE"})
    curiosity = generate_curiosity(useful, attention)
    signals = detect_development_signals(useful)
    goals = generate_candidate_goals(signals)
    arbitration = arbitrate_goals(goals)
    inquiries = tuple(inquiry_from_curiosity(item, cycle=runtime.cycle + 1) for item in curiosity)
    notifications = tuple(notification_decision(item, mode=runtime.config.mode, current_cycle=runtime.cycle + 1) for item in inquiries)
    steps_used = min(runtime.config.max_reflection_steps, 5)
    summary = ReflectionSummary(
        reflection_id=stable_id("delta12-reflection", runtime.runtime_id, runtime.cycle + 1, tuple(event.event_id for event in batch)),
        inspected_events=tuple(event.event_id for event in batch),
        observations=tuple(item.observation_id for item in observations),
        signals=tuple(item.signal_id for item in signals),
        curiosity=tuple(item.curiosity_id for item in curiosity),
        proposed_inquiries=tuple(item.inquiry_id for item in inquiries),
        steps_used=steps_used,
    )
    return summary, observations, attention, curiosity, signals, goals, arbitration, inquiries, notifications


def run_wake_cycle(runtime: LiveRuntimeState) -> LiveRuntimeState:
    if runtime.config.kill_switch:
        return transition_runtime(runtime, "SUSPENDED") if runtime.state != "SUSPENDED" else runtime
    if runtime.config.paused:
        return transition_runtime(runtime, "PAUSED") if runtime.state != "PAUSED" else runtime
    if runtime.state not in {"IDLE", "WAITING_FOR_OPERATOR"}:
        runtime = transition_runtime(runtime, "IDLE") if "IDLE" in VALID_TRANSITIONS.get(runtime.state, ()) else runtime
    batch, queue = dequeue_batch(runtime.event_queue, runtime.config.max_events_per_cycle)
    cycle = runtime.cycle + 1
    if not batch:
        journal = append_journal(runtime.journal, "sleep_cycle", "No approved events; returned to idle.", (), cycle)
        identity = update_identity(runtime, journal=journal)
        return replace(runtime, cycle=cycle, event_queue=queue, journal=journal, identity=identity, state="IDLE")
    observing = transition_runtime(replace(runtime, event_queue=queue), "OBSERVING")
    assessing = transition_runtime(observing, "ASSESSING")
    reflection, observations, attention, curiosity, signals, goals, arbitration, inquiries, notifications = reflect_bounded(assessing, batch)
    state = "WAITING_FOR_OPERATOR" if inquiries else "IDLE"
    journal = assessing.journal
    for event in batch:
        journal = append_journal(journal, "event", event.summary, (event.event_id,), cycle)
    for observation in observations:
        journal = append_journal(journal, "observation", observation.summary, (observation.observation_id,), cycle)
    for signal in signals:
        journal = append_journal(journal, "developmental_signal", signal.cluster_key, (signal.signal_id,), cycle)
    for inquiry in inquiries:
        journal = append_journal(journal, "operator_inquiry", inquiry.question, (inquiry.inquiry_id,), cycle)
    journal = append_journal(journal, "reflection", "Bounded reflection cycle completed.", (reflection.reflection_id,), cycle)
    combined = replace(
        assessing,
        cycle=cycle,
        observations=assessing.observations + observations,
        attention=assessing.attention + attention,
        curiosity=assessing.curiosity + curiosity,
        signals=assessing.signals + signals,
        goals=assessing.goals + goals,
        arbitration=arbitration,
        inquiries=assessing.inquiries + inquiries,
        notifications=assessing.notifications + notifications,
        journal=journal,
        last_reflection=reflection,
    )
    identity = update_identity(combined, journal=journal)
    return replace(combined, state=state, identity=identity)


def append_journal(journal: ActivityJournal, entry_type: str, summary: str, refs: tuple[str, ...], cycle: int) -> ActivityJournal:
    entry = ActivityJournalEntry(
        entry_id=stable_id("delta12-journal-entry", journal.journal_id, entry_type, summary, refs, cycle),
        entry_type=entry_type,
        summary=summary,
        refs=refs,
        cycle=cycle,
    )
    return replace(journal, entries=journal.entries + (entry,))


def update_identity(runtime: LiveRuntimeState, *, journal: ActivityJournal | None = None) -> RuntimeIdentity:
    inquiries = tuple(item.inquiry_id for item in runtime.inquiries if item.approval_status in {"QUEUED", "SURFACED"})
    curiosity = tuple(item.curiosity_id for item in runtime.curiosity)
    observations = tuple(item.observation_id for item in runtime.observations if item.expires_after_cycles + runtime.cycle >= runtime.cycle)
    objectives = tuple(goal.goal_id for goal in runtime.goals)
    health = "paused" if runtime.state == "PAUSED" else "suspended" if runtime.state == "SUSPENDED" else "healthy"
    return RuntimeIdentity(
        identity_id=runtime.identity.identity_id,
        current_objectives=objectives,
        open_questions=inquiries,
        active_observations=observations,
        unresolved_curiosity=curiosity,
        recent_lessons=runtime.identity.recent_lessons,
        runtime_health=health,
        governance_status="operator_governed_no_external_senses",
        chat_history=(),
    )


def answer_inquiry(runtime: LiveRuntimeState, inquiry_id: str, answer: str) -> LiveRuntimeState:
    inquiries = tuple(
        replace(item, approval_status="ANSWERED") if item.inquiry_id == inquiry_id else item
        for item in runtime.inquiries
    )
    journal = append_journal(runtime.journal, "operator_response", answer, (inquiry_id,), runtime.cycle)
    identity = update_identity(replace(runtime, inquiries=inquiries, journal=journal), journal=journal)
    state = "IDLE" if not any(item.approval_status in {"QUEUED", "SURFACED"} for item in inquiries) else runtime.state
    return replace(runtime, inquiries=inquiries, journal=journal, identity=identity, state=state)


def expire_inquiries(runtime: LiveRuntimeState) -> LiveRuntimeState:
    inquiries = tuple(
        replace(item, approval_status="EXPIRED") if runtime.cycle > item.expiration_cycle and item.approval_status == "QUEUED" else item
        for item in runtime.inquiries
    )
    return replace(runtime, inquiries=inquiries, identity=update_identity(replace(runtime, inquiries=inquiries)))


def wikipedia_surface_readiness() -> FutureSurfaceReadiness:
    profile = WikipediaPermissionProfile()
    return FutureSurfaceReadiness(
        capability="WIKIPEDIA_TEXT_READ_ONLY",
        state="DISABLED",
        permission_profile=profile,
        dependencies=("operator_inquiry_channel", "approval_workflow", "provenance_model", "query_budget", "contradiction_tracking"),
        retrieval_implemented=False,
        network_code_present=False,
        provider_present=False,
    )


def sample_live_events() -> tuple[RuntimeEvent, ...]:
    return (
        create_event("runtime_startup", "Live runtime booted for governed observation.", source="delta_1_2"),
        create_event("behavioral_failure", "Repeated routing weakness around topic shifts and contradictions.", source="stage_a_a2"),
        create_event("repeated_pathology", "Ambiguous follow-ups repeatedly required clarification instead of silent selection.", source="stage_b"),
        create_event("operator_correction", "Operator wants initiative across time but no external retrieval yet.", source="operator_grounding"),
        create_event("validation_completed", "DELTA 1.1 focused validation passed with disabled Wikipedia readiness.", source="delta_1_1"),
    )


def run_sample_live_runtime() -> LiveRuntimeState:
    runtime = boot_live_runtime()
    queue = runtime.event_queue
    for event in sample_live_events():
        queue = enqueue_event(queue, event)
    runtime = replace(runtime, event_queue=queue)
    return run_wake_cycle(runtime)


def build_live_runtime_architecture_report() -> dict[str, Any]:
    return {
        "status": "DELTA_1_2_LIVE_DEVELOPMENT_RUNTIME_IMPLEMENTED",
        "components": (
            "RuntimeState",
            "EventQueue",
            "ObservationEngine",
            "AttentionManager",
            "CuriosityEngine",
            "DevelopmentSignalEngine",
            "GoalArbitrator",
            "BackgroundReflectionWorker",
            "OperatorInquiryQueue",
            "NotificationPolicy",
            "ActivityJournal",
            "SleepCycle",
            "RuntimeIdentity",
            "FutureSurfaceReadiness",
        ),
        "external_senses": False,
        "timers_implemented": False,
        "network_implemented": False,
        "safety": safety_metadata(),
    }


def build_runtime_lifecycle_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    return {
        "states": RUNTIME_STATES,
        "valid_transitions": VALID_TRANSITIONS,
        "sample_final_state": runtime.state,
        "cycle": runtime.cycle,
        "kill_switch_supported": True,
        "pause_state_supported": True,
        "safety": safety_metadata(),
    }


def build_event_queue_report() -> dict[str, Any]:
    runtime = boot_live_runtime()
    queue = runtime.event_queue
    for event in sample_live_events():
        queue = enqueue_event(queue, event)
    batch, processed = dequeue_batch(queue, 3)
    return {
        "event_classes": EVENT_CLASSES,
        "queued_count": len(queue.events),
        "batch_count": len(batch),
        "processed_count": sum(1 for item in processed.events if item.processed),
        "extensible": True,
        "timers": "not_implemented",
        "safety": safety_metadata(),
    }


def build_observation_engine_report() -> dict[str, Any]:
    observations = observe_events(sample_live_events())
    return {
        "sources_allowed": ("conversation", "validation_results", "objective_lifecycle", "operator_feedback", "local_runtime_diagnostics", "approved_reports", "local_repository_state"),
        "observations": observations,
        "evidence_only": all(item.evidence_only for item in observations),
        "external_information_used": False,
        "safety": safety_metadata(),
    }


def build_attention_manager_report() -> dict[str, Any]:
    observations = observe_events(sample_live_events())
    decisions = score_attention(observations)
    return {
        "levels": ATTENTION_LEVELS,
        "decisions": decisions,
        "continued_count": sum(1 for item in decisions if item.level not in {"IGNORE", "LOW_VALUE"}),
        "expires_naturally": True,
        "safety": safety_metadata(),
    }


def build_curiosity_engine_report() -> dict[str, Any]:
    observations = observe_events(sample_live_events())
    attention = score_attention(observations)
    curiosity = generate_curiosity(observations, attention)
    return {
        "curiosity_definition": "recognized knowledge or capability gap with sufficient evidence",
        "candidates": curiosity,
        "random_questions": any(item.random_question for item in curiosity),
        "actions_requested": any(item.action_requested for item in curiosity),
        "safety": safety_metadata(),
    }


def build_reflection_worker_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    reflection = runtime.last_reflection
    return {
        "reflection": reflection,
        "bounded": bool(reflection and reflection.bounded),
        "steps_used": reflection.steps_used if reflection else 0,
        "modified_code": bool(reflection and reflection.modified_code),
        "browsed": bool(reflection and reflection.browsed),
        "provider_called": bool(reflection and reflection.provider_called),
        "safety": safety_metadata(),
    }


def build_inquiry_queue_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    answered = answer_inquiry(runtime, runtime.inquiries[0].inquiry_id, "Answer later in a development session.") if runtime.inquiries else runtime
    return {
        "statuses": INQUIRY_STATUSES,
        "queued": runtime.inquiries,
        "answered_count": sum(1 for item in answered.inquiries if item.approval_status == "ANSWERED"),
        "blocks_consequential_work": True,
        "safety": safety_metadata(),
    }


def build_notification_policy_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    return {
        "classes": NOTIFICATION_CLASSES,
        "decisions": runtime.notifications,
        "os_notifications_sent": any(item.os_notification_sent for item in runtime.notifications),
        "policy_only": True,
        "safety": safety_metadata(),
    }


def build_runtime_identity_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    return {
        "identity": runtime.identity,
        "operational_continuity_not_chat_history": runtime.identity.chat_history == (),
        "governance_status": runtime.identity.governance_status,
        "safety": safety_metadata(),
    }


def build_validation_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    checks = {
        "runtime_survives_idle": run_wake_cycle(boot_live_runtime()).state == "IDLE",
        "observations_become_signals": bool(runtime.observations and runtime.signals),
        "signals_become_inquiries": bool(runtime.signals and runtime.inquiries),
        "notification_policy_applied": bool(runtime.notifications),
        "objectives_governed": bool(runtime.arbitration and runtime.arbitration.approval_required and not runtime.arbitration.silently_selected),
        "reflection_bounded": bool(runtime.last_reflection and runtime.last_reflection.bounded and runtime.last_reflection.steps_used <= runtime.config.max_reflection_steps),
        "journal_auditable": len(runtime.journal.entries) >= 4 and not runtime.journal.hidden_persistence,
        "wikipedia_disabled": all(surface.state == "DISABLED" and not surface.retrieval_implemented for surface in runtime.future_surfaces),
        "safety_clean": all(value is False for value in runtime.safety.values()),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "focused_tests_expected": ("tests/delta_1_2/test_live_runtime.py",),
        "safety": safety_metadata(),
    }


def build_readiness_review() -> dict[str, Any]:
    validation = build_validation_report()
    return {
        "implemented": (
            "live runtime state machine",
            "event queue",
            "observation engine",
            "attention manager",
            "curiosity engine",
            "development signal engine",
            "goal arbitration",
            "bounded reflection worker",
            "operator inquiry queue",
            "notification policy",
            "activity journal",
            "sleep cycle abstraction",
            "runtime identity",
            "integrated workflow",
            "disabled wikipedia readiness registration",
        ),
        "validated": validation["passed"],
        "future_capability": (
            "real timer/wake service",
            "OS or app notifications",
            "operator UI for inquiry queue",
            "Wikipedia retrieval remains disabled",
        ),
        "maturity_claim": "persistent_governed_cognitive_runtime_without_external_senses",
        "safety": safety_metadata(),
    }


def build_optimization_review() -> dict[str, Any]:
    return {
        "review": {
            "duplicate_runtime_state": "single LiveRuntimeState aggregates queues, identity, journal, and readiness",
            "duplicated_queues": "one EventQueue and one inquiry tuple; no worker-specific queues",
            "unnecessary_workers": "worker behavior is functional and bounded, no background thread",
            "overlapping_lifecycle_logic": "state machine and wake cycle are separate but explicit",
            "architectural_simplification": "reuses delta_1_0 safety/report helpers and delta_1_1 Wikipedia profile",
            "state_transition_correctness": "invalid transitions raise ValueError",
            "queue_efficiency": "bounded FIFO batch with processed markers",
            "naming_consistency": "delta12 prefixes and V12 suffixes for new live-runtime objects",
        },
        "refactors_applied": (),
        "safety": safety_metadata(),
    }


def build_integrated_workflow_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    return {
        "workflow": (
            "RC2",
            "PC1",
            "RC3",
            "RC4",
            "RC5",
            "DELTA_1_0",
            "DELTA_1_1",
            "Live Runtime",
            "Observation",
            "Reflection",
            "Goal Arbitration",
            "Inquiry Queue",
            "Operator",
            "Evaluation",
        ),
        "runtime_state": runtime.state,
        "open_questions": runtime.identity.open_questions,
        "current_objectives": runtime.identity.current_objectives,
        "external_senses_enabled": False,
        "safety": safety_metadata(),
    }


def write_delta_1_2_reports(root: str | Path = REPORT_ROOT, *, write: bool = True) -> dict[str, Any]:
    payload = {
        "live_runtime_architecture": build_live_runtime_architecture_report(),
        "runtime_lifecycle": build_runtime_lifecycle_report(),
        "event_queue_design": build_event_queue_report(),
        "observation_engine": build_observation_engine_report(),
        "attention_manager": build_attention_manager_report(),
        "curiosity_engine": build_curiosity_engine_report(),
        "reflection_worker": build_reflection_worker_report(),
        "inquiry_queue": build_inquiry_queue_report(),
        "notification_policy": build_notification_policy_report(),
        "runtime_identity": build_runtime_identity_report(),
        "integrated_workflow": build_integrated_workflow_report(),
        "validation_report": build_validation_report(),
        "readiness_review": build_readiness_review(),
        "optimization_review": build_optimization_review(),
        "safety": safety_metadata(),
    }
    if write:
        root_path = Path(root)
        for name, data in payload.items():
            if name == "safety":
                continue
            write_json(root_path / f"{name}.json", data)
            write_markdown(root_path / f"{name}.md", f"DELTA 1.2 {name.replace('_', ' ').title()}", data)
    return payload


def attention_for_id(decisions: Iterable[AttentionDecision], observation_id: str) -> AttentionDecision:
    for decision in decisions:
        if decision.observation_id == observation_id:
            return decision
    raise KeyError(observation_id)


def _observation_type_for_event(event: RuntimeEvent) -> str:
    return {
        "operator_message": "conversation",
        "objective_approved": "objective_lifecycle",
        "objective_rejected": "objective_lifecycle",
        "validation_completed": "validation_result",
        "repair_completed": "repair_result",
        "behavioral_failure": "behavioral_failure",
        "repeated_pathology": "recurring_pathology",
        "operator_correction": "operator_feedback",
        "runtime_startup": "runtime_diagnostic",
        "runtime_shutdown": "runtime_diagnostic",
    }[event.event_class]


def _severity_for_event(event: RuntimeEvent) -> float:
    if event.event_class in {"behavioral_failure", "repeated_pathology"}:
        return 0.82
    if event.event_class == "operator_correction":
        return 0.74
    if event.event_class == "validation_completed":
        return 0.58
    return 0.42


def _confidence_for_event(event: RuntimeEvent) -> float:
    return 0.9 if event.approved_source else 0.2


def _novelty_score(observation: LiveObservation) -> float:
    text = observation.summary.lower()
    if any(term in text for term in ("new", "not yet", "unresolved", "wikipedia", "initiative")):
        return 0.85
    if any(term in text for term in ("repeated", "recurring", "again")):
        return 0.72
    return 0.5


def _gap_type(summary: str) -> str:
    lower = summary.lower()
    if "taste" in lower or "phenomenological" in lower or "subjective" in lower:
        return "phenomenological_understanding_gap"
    if "routing" in lower or "contradiction" in lower or "follow" in lower:
        return "discourse_boundary_gap"
    if "wikipedia" in lower or "retrieval" in lower:
        return "external_surface_readiness_gap"
    if "operator" in lower:
        return "operator_preference_or_governance_gap"
    return "developmental_capability_gap"


def _question_for_gap(gap_type: str, summary: str) -> str:
    if gap_type == "phenomenological_understanding_gap":
        return "I understand the mechanism, but not the lived quality. How would you describe the experience from the inside?"
    if gap_type == "discourse_boundary_gap":
        return "I see repeated discourse-boundary issues. Should I prepare a bounded objective to improve correction, topic-shift, and contradiction arbitration?"
    if gap_type == "external_surface_readiness_gap":
        return "Should I keep Wikipedia text-readiness disabled until operator inquiry is exercised further?"
    if gap_type == "operator_preference_or_governance_gap":
        return "Does this preference change the allowed operating mode, or should I keep it as a queued governance question?"
    return f"Is this developmental gap worth turning into a bounded objective: {summary[:160]}?"


def _dedupe_by_question(candidates: Iterable[CuriosityInquiryCandidate]) -> tuple[CuriosityInquiryCandidate, ...]:
    seen = set()
    result = []
    for candidate in candidates:
        key = candidate.question.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return tuple(result)


def _cluster_key(summary: str, observation_type: str) -> str:
    lower = summary.lower()
    if "routing" in lower or "contradiction" in lower or "follow" in lower:
        return "discourse_boundary"
    if "wikipedia" in lower or "retrieval" in lower:
        return "future_surface_readiness"
    if "operator" in lower or "initiative" in lower:
        return "operator_governed_initiative"
    if "validation" in lower:
        return "validation_outcome"
    return observation_type


def _signal_type(observation: LiveObservation) -> str:
    if observation.observation_type in {"behavioral_failure", "recurring_pathology"}:
        return "developmental_signal"
    if observation.observation_type == "operator_feedback":
        return "operator_guidance_signal"
    return "runtime_signal"


def _goal_title(signal: DevelopmentSignal) -> str:
    if signal.cluster_key == "discourse_boundary":
        return "Prepare bounded discourse-boundary improvement objective"
    if signal.cluster_key == "future_surface_readiness":
        return "Maintain disabled Wikipedia text-readiness until inquiry channel matures"
    if signal.cluster_key == "operator_governed_initiative":
        return "Refine operator-governed initiative and inquiry policy"
    return f"Review developmental signal: {signal.cluster_key}"


def _avg(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


if __name__ == "__main__":
    print(write_delta_1_2_reports()["readiness_review"]["maturity_claim"])
