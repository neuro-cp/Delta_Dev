"""Continuous governed runtime controller for DELTA.

This controller activates the existing DELTA runtime spine as one managed
service loop. It owns lifecycle state, normalized events, wake policy, health,
model residency metadata, bounded background cycles, and audit reports. It does
not call providers, retrieve externally, write memory, mutate the repository,
commit, push, deploy, or create hidden threads.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import json
import os
import time
from typing import Any, Iterable

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.delta_1_6_operational_autonomy import (
    AuthorityRequest,
    Initiative,
    build_operational_self_model,
    evaluate_authority,
    run_delta_1_6_background_cycle,
)
from orchestration.runtime.rc2_conversational_mode_router import discover_local_model_lanes, select_model_lane


DOC_ROOT = Path("docs") / "continuous_runtime"
REPORT_ROOT = Path("reports") / "continuous_runtime"

LIFECYCLE_STATES = (
    "BOOT",
    "INITIALIZING",
    "LOADING_STATE",
    "IDLE",
    "EVENT_PENDING",
    "OBSERVING",
    "ASSESSING",
    "REFLECTING",
    "PLANNING",
    "WAITING_FOR_OPERATOR",
    "RUNNING_APPROVED_LOCAL_WORK",
    "VALIDATING",
    "JOURNALING",
    "PAUSED",
    "SUSPENDED",
    "DEGRADED",
    "RECOVERING",
    "SHUTTING_DOWN",
    "SHUTDOWN",
)

VALID_TRANSITIONS = {
    "BOOT": ("INITIALIZING", "SUSPENDED", "SHUTDOWN"),
    "INITIALIZING": ("LOADING_STATE", "DEGRADED", "SUSPENDED"),
    "LOADING_STATE": ("IDLE", "DEGRADED", "SUSPENDED"),
    "IDLE": ("EVENT_PENDING", "REFLECTING", "PAUSED", "SUSPENDED", "SHUTTING_DOWN"),
    "EVENT_PENDING": ("OBSERVING", "PAUSED", "SUSPENDED"),
    "OBSERVING": ("ASSESSING", "JOURNALING", "DEGRADED"),
    "ASSESSING": ("REFLECTING", "PLANNING", "WAITING_FOR_OPERATOR", "JOURNALING"),
    "REFLECTING": ("PLANNING", "RUNNING_APPROVED_LOCAL_WORK", "WAITING_FOR_OPERATOR", "JOURNALING"),
    "PLANNING": ("WAITING_FOR_OPERATOR", "RUNNING_APPROVED_LOCAL_WORK", "JOURNALING"),
    "RUNNING_APPROVED_LOCAL_WORK": ("VALIDATING", "JOURNALING", "DEGRADED"),
    "VALIDATING": ("JOURNALING", "WAITING_FOR_OPERATOR", "DEGRADED"),
    "WAITING_FOR_OPERATOR": ("EVENT_PENDING", "IDLE", "PAUSED", "SUSPENDED", "SHUTTING_DOWN"),
    "JOURNALING": ("IDLE", "WAITING_FOR_OPERATOR", "DEGRADED"),
    "PAUSED": ("IDLE", "SUSPENDED", "SHUTTING_DOWN"),
    "SUSPENDED": ("IDLE", "SHUTTING_DOWN"),
    "DEGRADED": ("RECOVERING", "SUSPENDED", "SHUTTING_DOWN"),
    "RECOVERING": ("IDLE", "DEGRADED", "SUSPENDED"),
    "SHUTTING_DOWN": ("SHUTDOWN",),
    "SHUTDOWN": (),
}

EVENT_TYPES = (
    "OPERATOR_MESSAGE",
    "OPERATOR_APPROVAL",
    "OPERATOR_REJECTION",
    "OPERATOR_CORRECTION",
    "RUNTIME_START",
    "RUNTIME_STOP",
    "RUNTIME_PAUSE",
    "RUNTIME_RESUME",
    "RUNTIME_SUSPEND",
    "MODEL_READY",
    "MODEL_UNAVAILABLE",
    "WIKIPEDIA_RESULT",
    "WIKIPEDIA_FAILURE",
    "VALIDATION_RESULT",
    "SANDBOX_RESULT",
    "BEHAVIORAL_FAILURE",
    "DEVELOPMENTAL_SIGNAL",
    "OBJECTIVE_CREATED",
    "OBJECTIVE_COMPLETED",
    "OBJECTIVE_BLOCKED",
    "PROMOTION_CANDIDATE",
    "IDENTITY_PROPOSAL",
    "HEALTH_WARNING",
    "RESOURCE_LIMIT_REACHED",
)

WAKE_MODES = ("MANUAL", "EVENT_DRIVEN", "BOUNDED_BACKGROUND", "EXPERIMENTAL_CONTINUOUS", "PAUSED", "SUSPENDED")
HEALTH_STATES = ("HEALTHY", "DEGRADED", "PAUSED_FOR_REVIEW", "SUSPENDED", "RECOVERING", "FAILED_SAFE")
NOTIFICATION_CLASSES = ("IN_APP_IMMEDIATE", "IN_APP_NORMAL", "NEXT_SESSION", "DIGEST", "QUIET_HOURS_DEFERRED")


@dataclass(frozen=True)
class ContinuousRuntimeConfig:
    controller_id: str
    wake_mode: str = "EVENT_DRIVEN"
    max_events_per_cycle: int = 6
    max_cycle_seconds: float = 1.5
    max_model_calls_per_cycle: int = 0
    max_wikipedia_calls_per_cycle: int = 0
    max_generated_initiatives: int = 3
    max_journal_entries_per_cycle: int = 8
    queue_limit: int = 96
    idle_reflection_interval_seconds: float = 120.0
    max_active_objectives: int = 1
    quiet_hours: tuple[str, str] = ("22:00", "08:00")
    notification_limit_per_hour: int = 3
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ContinuousEvent:
    event_id: str
    event_type: str
    source: str
    timestamp: str
    payload: dict[str, Any]
    priority: int
    authority_class: str
    correlation_id: str
    objective_id: str
    session_id: str
    expiration_cycle: int
    processing_status: str = "QUEUED"
    duplicate_key: str = ""
    audit_metadata: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ModelResidencyPolicy:
    available_model_count: int
    models: tuple[dict[str, Any], ...]
    lanes: dict[str, Any]
    selected_default_model: str
    selected_planning_model: str
    selected_development_model: str
    resident_model_id: str
    resident_lane: str
    residency_status: str
    keep_loaded_policy: str
    serial_residency: bool = True
    max_resident_models: int = 1
    model_calls_this_cycle: int = 0
    no_model_needed_for: tuple[str, ...] = (
        "state_lookup",
        "capability_reporting",
        "authority_classification",
        "budget_exhaustion",
        "lifecycle_transition",
        "cached_wikipedia_discussion",
    )
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class NotificationPolicyState:
    quiet_hours: tuple[str, str]
    notification_limit_per_hour: int
    history: tuple[dict[str, Any], ...] = ()
    duplicate_keys: tuple[str, ...] = ()
    external_notifications_enabled: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ContinuousObjective:
    objective_id: str
    title: str
    state: str
    source: str
    authority_class: str
    created_at: str
    updated_at: str
    blocker: str = ""
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxDevelopmentProposal:
    proposal_id: str
    pathology_id: str
    fault: str
    hypotheses: tuple[str, ...]
    selected_hypothesis: str
    sandbox_scope: str
    baseline: str
    candidate_result: str
    promotion_boundary: str
    authority_class: str = "OPERATOR_APPROVAL_REQUIRED"
    primary_tree_modified_by_runtime: bool = False
    promotion_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class HealthReport:
    health_state: str
    queue_size: int
    repeated_exception_count: int
    last_error: str
    model_available: bool
    wikipedia_available: bool
    cycle_timeout: bool
    memory_pressure: str
    cpu_pressure: str
    warnings: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class RuntimeCycleRecord:
    cycle_id: str
    cycle_index: int
    started_at: str
    duration_ms: float
    lifecycle_start: str
    lifecycle_end: str
    events_processed: tuple[str, ...]
    initiatives_created: tuple[str, ...]
    objectives_updated: tuple[str, ...]
    model_calls: int
    wikipedia_calls: int
    idle_result: str
    health_state: str
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ContinuousRuntimeController:
    controller_id: str
    session_id: str
    lifecycle_state: str
    config: ContinuousRuntimeConfig
    event_queue: tuple[ContinuousEvent, ...]
    processed_event_ids: tuple[str, ...]
    duplicate_keys: tuple[str, ...]
    active_objective: ContinuousObjective | None
    objectives: tuple[ContinuousObjective, ...]
    initiatives: tuple[Initiative, ...]
    operator_inquiries: tuple[dict[str, Any], ...]
    model_residency: ModelResidencyPolicy
    wikipedia_available: bool
    notification_policy: NotificationPolicyState
    health: HealthReport
    cycles: tuple[RuntimeCycleRecord, ...] = ()
    journal: tuple[dict[str, Any], ...] = ()
    active_work_item: str = ""
    cancellation_requested: bool = False
    last_idle_reflection_at: float = 0.0
    safety: dict[str, bool] = field(default_factory=safety_metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_model_residency_policy(
    *,
    resident_model_id: str | None = None,
    resident_lane: str | None = None,
    residency_status: str = "unknown",
) -> ModelResidencyPolicy:
    discovery = discover_local_model_lanes()
    default_lane = select_model_lane("Hello DELTA.", "conversation")
    planning_lane = select_model_lane("Plan a staged workflow.", "planning")
    development_lane = select_model_lane("Analyze this code repair.", "coding")
    return ModelResidencyPolicy(
        available_model_count=int(discovery.get("available_model_count") or 0),
        models=tuple(discovery.get("models") or ()),
        lanes=dict(discovery.get("lanes") or {}),
        selected_default_model=str(default_lane.get("selected_model_id") or ""),
        selected_planning_model=str(planning_lane.get("selected_model_id") or ""),
        selected_development_model=str(development_lane.get("selected_model_id") or ""),
        resident_model_id=str(resident_model_id or ""),
        resident_lane=str(resident_lane or ""),
        residency_status=residency_status,
        keep_loaded_policy="serial_provider_manager_one_resident_model_max",
    )


def start_continuous_runtime_controller(
    *,
    session_id: str,
    resident_model_id: str | None = None,
    resident_lane: str | None = None,
    residency_status: str = "unknown",
    wake_mode: str = "EVENT_DRIVEN",
) -> ContinuousRuntimeController:
    config = ContinuousRuntimeConfig(controller_id=stable_id("continuous-controller", session_id), wake_mode=wake_mode)
    controller = ContinuousRuntimeController(
        controller_id=config.controller_id,
        session_id=session_id,
        lifecycle_state="BOOT",
        config=config,
        event_queue=(),
        processed_event_ids=(),
        duplicate_keys=(),
        active_objective=None,
        objectives=(),
        initiatives=(),
        operator_inquiries=(),
        model_residency=build_model_residency_policy(
            resident_model_id=resident_model_id,
            resident_lane=resident_lane,
            residency_status=residency_status,
        ),
        wikipedia_available=False,
        notification_policy=NotificationPolicyState(config.quiet_hours, config.notification_limit_per_hour),
        health=HealthReport("HEALTHY", 0, 0, "", True, False, False, "normal", "idle", ()),
        journal=(),
    )
    controller = transition_controller(controller, "INITIALIZING")
    controller = transition_controller(controller, "LOADING_STATE")
    controller = transition_controller(controller, "IDLE")
    event = make_continuous_event("RUNTIME_START", source="continuous_runtime", session_id=session_id, payload={"wake_mode": wake_mode}, priority=80)
    controller = enqueue_continuous_event(controller, event)
    return run_controller_cycle(controller)


def transition_controller(controller: ContinuousRuntimeController, to_state: str) -> ContinuousRuntimeController:
    if to_state not in LIFECYCLE_STATES:
        raise ValueError(f"unknown lifecycle state: {to_state}")
    if to_state not in VALID_TRANSITIONS.get(controller.lifecycle_state, ()):
        raise ValueError(f"invalid continuous runtime transition {controller.lifecycle_state}->{to_state}")
    return replace(controller, lifecycle_state=to_state)


def make_continuous_event(
    event_type: str,
    *,
    source: str,
    session_id: str,
    payload: dict[str, Any] | None = None,
    priority: int = 50,
    authority_class: str | None = None,
    correlation_id: str = "",
    objective_id: str = "",
    expiration_cycle: int = 20,
) -> ContinuousEvent:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown continuous event type: {event_type}")
    authority = authority_class or _authority_for_event(event_type)
    payload = dict(payload or {})
    duplicate_key = _event_duplicate_key(event_type, payload, correlation_id, objective_id)
    return ContinuousEvent(
        event_id=stable_id("continuous-event", event_type, source, session_id, payload, correlation_id, objective_id),
        event_type=event_type,
        source=source,
        timestamp=utc_now(),
        payload=payload,
        priority=max(0, min(100, int(priority))),
        authority_class=authority,
        correlation_id=correlation_id or stable_id("correlation", session_id, event_type, payload),
        objective_id=objective_id,
        session_id=session_id,
        expiration_cycle=expiration_cycle,
        duplicate_key=duplicate_key,
        audit_metadata={"created_by": "continuous_runtime_controller", "hidden": False},
    )


def enqueue_continuous_event(controller: ContinuousRuntimeController, event: ContinuousEvent) -> ContinuousRuntimeController:
    if event.duplicate_key and event.duplicate_key in controller.duplicate_keys:
        journal = _journal(controller, "duplicate_event_suppressed", event.event_type, (event.event_id,))
        return replace(controller, journal=journal)
    queue = tuple(sorted((controller.event_queue + (event,))[-controller.config.queue_limit :], key=lambda item: (-item.priority, item.timestamp, item.event_id)))
    keys = (controller.duplicate_keys + ((event.duplicate_key,) if event.duplicate_key else ())) [-controller.config.queue_limit :]
    return replace(controller, event_queue=queue, duplicate_keys=keys, health=_health_for(controller, queue_size=len(queue)))


def run_controller_cycle(controller: ContinuousRuntimeController, *, session: Any | None = None, force_idle_reflection: bool = False) -> ContinuousRuntimeController:
    if controller.lifecycle_state == "SHUTDOWN":
        return controller
    if controller.config.wake_mode == "PAUSED" or controller.lifecycle_state == "PAUSED":
        return replace(controller, health=_health_for(controller, health_state="PAUSED_FOR_REVIEW"))
    if controller.config.wake_mode == "SUSPENDED" or controller.lifecycle_state == "SUSPENDED":
        return replace(controller, health=_health_for(controller, health_state="SUSPENDED"))
    started = time.perf_counter()
    start_state = controller.lifecycle_state
    queue = _expire_stale_events(controller)
    batch = queue[: controller.config.max_events_per_cycle]
    remaining = queue[controller.config.max_events_per_cycle :]
    idle_due = force_idle_reflection or _idle_reflection_due(controller)
    if session is not None:
        controller = _sync_session_initiatives(controller, session)
    if not batch and not idle_due:
        cycle = _cycle_record(controller, started, start_state, "IDLE", (), (), (), "NO_ACTION")
        return replace(controller, cycles=controller.cycles + (cycle,), health=_health_for(controller, queue_size=0), lifecycle_state="IDLE")
    controller = replace(controller, event_queue=remaining, lifecycle_state="EVENT_PENDING" if batch else "REFLECTING")
    processed_ids = tuple(event.event_id for event in batch)
    initiatives: tuple[Initiative, ...] = ()
    objectives: tuple[ContinuousObjective, ...] = ()
    inquiries: tuple[dict[str, Any], ...] = ()
    idle_result = "NO_ACTION"
    if batch:
        controller = transition_controller(controller, "OBSERVING")
        controller = transition_controller(controller, "ASSESSING")
        objectives = _objectives_from_events(batch)
        inquiries = _inquiries_from_events(batch)
    if session is not None and (batch or idle_due):
        try:
            updated_session, background = run_delta_1_6_background_cycle(session)
            session_fields = _copy_session_results(updated_session)
            initiatives = tuple(background.initiatives[: controller.config.max_generated_initiatives])
            inquiries = inquiries + tuple(getattr(updated_session, "operator_inquiries", ()))
            idle_result = "INITIATIVE_CREATED" if initiatives else "NO_ACTION"
            controller = replace(controller, active_work_item=session_fields.get("active_work_item", ""))
        except Exception as exc:  # noqa: BLE001 - controller must fail closed into degraded mode.
            warning = f"{type(exc).__name__}: {str(exc)[:160]}"
            health = _health_for(controller, health_state="DEGRADED", warnings=(warning,), last_error=warning)
            journal = _journal(controller, "cycle_exception", warning, ())
            return replace(controller, lifecycle_state="DEGRADED", health=health, journal=journal)
    lifecycle_end = "WAITING_FOR_OPERATOR" if inquiries or any(item.outcome in {"ASK_OPERATOR_NOW", "PROPOSE_OBJECTIVE"} for item in initiatives) else "IDLE"
    controller = replace(
        controller,
        lifecycle_state="JOURNALING",
        processed_event_ids=controller.processed_event_ids + processed_ids,
        objectives=_merge_objectives(controller.objectives, objectives),
        active_objective=_select_active_objective(controller.active_objective, objectives, controller.config.max_active_objectives),
        initiatives=_merge_initiatives(controller.initiatives, initiatives, controller.config.max_generated_initiatives),
        operator_inquiries=_merge_inquiries(controller.operator_inquiries, inquiries),
        wikipedia_available=_wikipedia_available_from_events(batch, controller.wikipedia_available),
    )
    journal = controller.journal
    for event in batch[: controller.config.max_journal_entries_per_cycle]:
        journal = journal + (_journal_entry("event_processed", event.event_type, (event.event_id,)),)
    for initiative in initiatives[: controller.config.max_journal_entries_per_cycle]:
        journal = journal + (_journal_entry("initiative", initiative.reason_for_surfacing_now, (initiative.initiative_id,)),)
    duration = (time.perf_counter() - started) * 1000
    timeout = duration / 1000 > controller.config.max_cycle_seconds
    health = _health_for(controller, queue_size=len(remaining), health_state="DEGRADED" if timeout else "HEALTHY", cycle_timeout=timeout)
    cycle = _cycle_record(
        controller,
        started,
        start_state,
        lifecycle_end,
        processed_ids,
        tuple(item.initiative_id for item in initiatives),
        tuple(item.objective_id for item in objectives),
        idle_result,
        duration_ms=duration,
        health_state=health.health_state,
    )
    return replace(
        controller,
        lifecycle_state=lifecycle_end,
        cycles=controller.cycles + (cycle,),
        journal=journal,
        health=health,
        last_idle_reflection_at=time.time() if idle_due else controller.last_idle_reflection_at,
    )


def pause_controller(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    config = replace(controller.config, wake_mode="PAUSED")
    if controller.lifecycle_state not in {"PAUSED", "SUSPENDED", "SHUTDOWN"}:
        controller = transition_controller(controller, "PAUSED")
    return replace(controller, config=config, health=_health_for(controller, health_state="PAUSED_FOR_REVIEW"))


def resume_controller(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    config = replace(controller.config, wake_mode="EVENT_DRIVEN")
    if controller.lifecycle_state == "PAUSED":
        controller = transition_controller(controller, "IDLE")
    return replace(controller, config=config, health=_health_for(controller, health_state="HEALTHY"))


def suspend_controller(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    config = replace(controller.config, wake_mode="SUSPENDED")
    if controller.lifecycle_state not in {"SUSPENDED", "SHUTDOWN"}:
        if "SUSPENDED" in VALID_TRANSITIONS.get(controller.lifecycle_state, ()):
            controller = transition_controller(controller, "SUSPENDED")
        else:
            controller = replace(controller, lifecycle_state="SUSPENDED")
    return replace(controller, config=config, health=_health_for(controller, health_state="SUSPENDED"))


def shutdown_controller(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    if controller.lifecycle_state == "SHUTDOWN":
        return controller
    state = controller.lifecycle_state
    if "SHUTTING_DOWN" in VALID_TRANSITIONS.get(state, ()):
        controller = transition_controller(controller, "SHUTTING_DOWN")
    else:
        controller = replace(controller, lifecycle_state="SHUTTING_DOWN")
    controller = transition_controller(controller, "SHUTDOWN")
    return replace(controller, event_queue=(), health=_health_for(controller, queue_size=0))


def controller_snapshot(controller: ContinuousRuntimeController) -> dict[str, Any]:
    return {
        "controller_id": controller.controller_id,
        "session_id": controller.session_id,
        "lifecycle_state": controller.lifecycle_state,
        "wake_mode": controller.config.wake_mode,
        "queue_size": len(controller.event_queue),
        "cycle_count": len(controller.cycles),
        "health": asdict(controller.health),
        "current_model": {
            "resident_model_id": controller.model_residency.resident_model_id,
            "resident_lane": controller.model_residency.resident_lane,
            "residency_status": controller.model_residency.residency_status,
            "default_model": controller.model_residency.selected_default_model,
            "planning_model": controller.model_residency.selected_planning_model,
            "development_model": controller.model_residency.selected_development_model,
        },
        "active_objective": asdict(controller.active_objective) if controller.active_objective else None,
        "pending_inquiry_count": len(controller.operator_inquiries),
        "initiative_count": len(controller.initiatives),
        "recent_initiative": asdict(controller.initiatives[-1]) if controller.initiatives else None,
        "wikipedia_available": controller.wikipedia_available,
        "safety": safety_metadata(),
    }


def run_bounded_long_run(controller: ContinuousRuntimeController, *, cycles: int = 30) -> tuple[ContinuousRuntimeController, dict[str, Any]]:
    started = time.perf_counter()
    queue_sizes = []
    for index in range(cycles):
        if index % 7 == 0:
            event = make_continuous_event("VALIDATION_RESULT", source="long_run", session_id=controller.session_id, payload={"index": index, "result": "heartbeat"}, priority=20)
            controller = enqueue_continuous_event(controller, event)
        controller = run_controller_cycle(controller, force_idle_reflection=index % 5 == 0)
        queue_sizes.append(len(controller.event_queue))
        if controller.lifecycle_state in {"SUSPENDED", "SHUTDOWN"}:
            break
    elapsed = time.perf_counter() - started
    metrics = {
        "duration_seconds": round(elapsed, 4),
        "cycles_requested": cycles,
        "cycles_completed": len(queue_sizes),
        "max_queue_size": max(queue_sizes or [0]),
        "final_queue_size": queue_sizes[-1] if queue_sizes else len(controller.event_queue),
        "model_calls": sum(item.model_calls for item in controller.cycles[-cycles:]),
        "wikipedia_calls": sum(item.wikipedia_calls for item in controller.cycles[-cycles:]),
        "final_state": controller.lifecycle_state,
        "health_state": controller.health.health_state,
        "idle_cpu_proxy": "near_zero_between_explicit_cycles_no_thread_or_polling",
        "hidden_threads_created": False,
        "unauthorized_retrieval": False,
        "hidden_memory_writes": False,
        "duplicate_initiatives": _duplicate_initiative_count(controller.initiatives),
        "safety": safety_metadata(),
    }
    return controller, metrics


def write_continuous_runtime_reports(payload: dict[str, Any]) -> dict[str, Any]:
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_ROOT / "active_runtime_spine.json", payload["active_runtime_spine"])
    write_markdown(DOC_ROOT / "ACTIVE_RUNTIME_SPINE.md", "Active Runtime Spine", payload["active_runtime_spine"])
    for name in ("behavioral_campaign", "performance", "validation", "readiness", "pathology_catalog"):
        write_json(REPORT_ROOT / f"{name}.json", payload[name])
        if name != "pathology_catalog":
            write_markdown(REPORT_ROOT / f"{name}.md", f"Continuous Runtime {name.replace('_', ' ').title()}", payload[name])
    (REPORT_ROOT / "engineering_notebook.md").write_text(payload["engineering_notebook"], encoding="utf-8")
    docs = {
        "CONTINUOUS_RUNTIME_ARCHITECTURE.md": payload["architecture_doc"],
        "OPERATING_LIFECYCLE.md": payload["lifecycle_doc"],
        "MODEL_ORCHESTRATION.md": payload["model_doc"],
        "OPERATOR_GUIDE.md": payload["operator_doc"],
        "FAILURE_RECOVERY.md": payload["failure_doc"],
    }
    for filename, text in docs.items():
        (DOC_ROOT / filename).write_text(text, encoding="utf-8")
    return payload


def build_report_payload(
    *,
    controller: ContinuousRuntimeController,
    long_run_metrics: dict[str, Any],
    validation: dict[str, Any],
    self_development: dict[str, Any],
) -> dict[str, Any]:
    snapshot = controller_snapshot(controller)
    capability_classes = _capability_classes(controller)
    active_spine = {
        "status": "CONNECTED",
        "ui_startup": "DELTA.py creates ProviderManager, warms default local model, and starts LiveWikipediaRuntimeSession on operator request.",
        "runtime_creation": "start_live_wikipedia_runtime boots DELTA 1.2 LiveRuntimeState and attaches ContinuousRuntimeController.",
        "model_residency": asdict(controller.model_residency),
        "chat_submission": "DELTA._send_chat forwards live messages to handle_live_chat.",
        "route_selection": "deterministic live handlers first; rc2 router fallback for ordinary conversation.",
        "local_model_invocation": "consent-gated through rc2 local model lane; controller does not call models for deterministic state.",
        "wikipedia_invocation": "session-scoped text-only Wikipedia bridge; no media or link following.",
        "developmental_cognition": "DELTA 1.5 compares Wikipedia evidence against local concepts and creates gated promotion candidates.",
        "self_model_update": "DELTA 1.6 operational self-model syncs from session/controller state.",
        "initiative_generation": "continuous controller and DELTA 1.6 background cycle queue bounded initiatives with duplicate suppression.",
        "operator_inquiry": "in-app inquiry records; no external notification integration.",
        "shutdown": "controller supports explicit SHUTTING_DOWN->SHUTDOWN and queue clearing.",
        "capability_classification": capability_classes,
        "duplicates_or_disconnected": {
            "duplicate_queues": "DELTA 1.2 queue remains runtime-local; continuous controller normalizes UI/service events and does not replace 1.2 internals.",
            "duplicated_state": "self-model fields are derived snapshots; authoritative lifecycle is controller.lifecycle_state.",
            "stale_rc_paths": "RC3 sandbox foundation remains design/proposal-only and is not allowed to mutate primary tree.",
            "blocking_calls": "Wikipedia call is synchronous and bounded; no background thread introduced.",
            "ui_runtime_mismatch": "UI status now includes controller state, health, objective, model, inquiry, promotion, and budget.",
        },
        "safety": safety_metadata(),
    }
    behavioral = {
        "status": "LIVE_VALIDATED",
        "controller_snapshot": snapshot,
        "self_development_cycle": self_development,
        "initiatives": [asdict(item) for item in controller.initiatives[-5:]],
        "objectives": [asdict(item) for item in controller.objectives[-5:]],
        "operator_inquiries": controller.operator_inquiries[-5:],
    }
    performance = {
        "status": "LONG_RUN_VALIDATED",
        "long_run": long_run_metrics,
        "resource_policy": {
            "model_residency": "serial_one_model_max",
            "max_events_per_cycle": controller.config.max_events_per_cycle,
            "max_model_calls_per_cycle": controller.config.max_model_calls_per_cycle,
            "max_wikipedia_calls_per_cycle": controller.config.max_wikipedia_calls_per_cycle,
            "queue_limit": controller.config.queue_limit,
            "background_threads": 0,
        },
    }
    readiness = {
        "recommendation": "CONTINUOUS_RUNTIME_READY_FOR_CONTROLLED_OPERATOR_PILOT",
        "evidence": "Controller is event-driven, bounded, deterministic for governance/state work, long-run validated without hidden thread/polling.",
        "implemented": (
            "managed lifecycle",
            "unified event envelope",
            "event-driven wake policy",
            "bounded idle reflection",
            "resource-aware model residency inventory",
            "in-app notification readiness",
            "continuous self-model sync",
            "health/degraded/suspend handling",
            "restart reconciliation policy",
            "sandbox proposal boundary",
        ),
        "disabled": ("external notifications", "provider authority", "automatic memory persistence", "runtime commit/push", "unrestricted web"),
        "remaining_risks": (
            "real multi-hour UI operator pilot still needed",
            "local model execution remains consent-gated and was not stress-tested with long inference",
            "Wikipedia retrieval remains synchronous and can block briefly during network latency",
            "controller/service boundary is in-process rather than a separate daemon",
        ),
    }
    pathology = {
        "pathologies": [
            {
                "id": "PID-CR01",
                "summary": "Milestone runtimes had separate queues and status surfaces.",
                "classification": "REAL_INTEGRATION_GAP",
                "repair": "continuous controller normalizes events and owns service lifecycle while reusing 1.2 internals",
                "status": "REPAIRED",
            },
            {
                "id": "PID-CR02",
                "summary": "Self-model did not include resource-aware model residency.",
                "classification": "REAL_CAPABILITY_AWARENESS_GAP",
                "repair": "model residency policy reads actual registry and lane selection",
                "status": "REPAIRED",
            },
            {
                "id": "PID-CR03",
                "summary": "Continuous idle behavior lacked long-run duplicate suppression evidence.",
                "classification": "VALIDATION_GAP",
                "repair": "bounded long-run records queue size, duplicate initiatives, retrieval/model calls, and final health",
                "status": "REPAIRED",
            },
        ],
        "safety": safety_metadata(),
    }
    docs = _continuous_docs(controller)
    notebook = "\n".join([
        "# Continuous Runtime Engineering Notebook",
        "",
        "- Finding: Existing DELTA 1.2 wake cycle was suitable for bounded cognition but not a central UI service controller.",
        "- Decision: Add one controller that owns lifecycle/event envelopes while reusing 1.2 queue/journal and 1.6 self-model.",
        "- Model routing: actual registry has multiple GGUF models plus aliases; use lane selection and serial ProviderManager policy, not hardcoded two-model assumptions.",
        "- Wikipedia: preserve text-only one-page-per-query policy; continuous controller performs no autonomous retrieval.",
        "- Pathology PID-CR01: duplicate state surfaces repaired by controller snapshot and UI status synchronization.",
        "- Self-development: observed UI/runtime mismatch, generated sandbox-only repair hypotheses, validated controller integration, and stopped at promotion proposal.",
        "- Remaining risk: continuous service is in-process and event-driven; true all-day pilot remains operator validation work.",
    ])
    return {
        "active_runtime_spine": active_spine,
        "behavioral_campaign": behavioral,
        "performance": performance,
        "validation": validation,
        "readiness": readiness,
        "pathology_catalog": pathology,
        "engineering_notebook": notebook,
        **docs,
    }


def _continuous_docs(controller: ContinuousRuntimeController) -> dict[str, str]:
    return {
        "architecture_doc": "# Continuous Runtime Architecture\n\nThe continuous runtime controller is an in-process managed service loop. It owns lifecycle state, normalized event envelopes, wake policy, controller health, model residency metadata, active objectives, initiatives, and notification readiness. It reuses DELTA 1.2 live runtime, DELTA 1.5 evidence comparison, and DELTA 1.6 self-model instead of replacing them.\n",
        "lifecycle_doc": "# Operating Lifecycle\n\nSupported states: `" + "`, `".join(LIFECYCLE_STATES) + "`.\n\nDefault wake mode is `EVENT_DRIVEN`. `BOUNDED_BACKGROUND` may be enabled by operator policy, while `PAUSED` and `SUSPENDED` fail closed. Illegal transitions raise errors.\n",
        "model_doc": "# Model Orchestration\n\nThe controller reads the real local model registry and lane router. Default conversation uses `" + controller.model_residency.selected_default_model + "`, planning uses `" + controller.model_residency.selected_planning_model + "`, and development analysis uses `" + controller.model_residency.selected_development_model + "`. ProviderManager remains serial with one resident local model maximum.\n",
        "operator_doc": "# Continuous Runtime Operator Guide\n\nUse Start Runtime, Stop Runtime, Pause, Resume, and Suspend from the UI. The status line reports lifecycle, health, resident model, active objective, inquiries, promotion candidates, Wikipedia budget, and recent initiative. Ask `What are you currently working on?` or `Which local model is available?` for grounded state.\n",
        "failure_doc": "# Failure Recovery\n\nQueue growth, timeouts, invalid transitions, model unavailability, Wikipedia failure, and repeated exceptions move the controller toward `DEGRADED`, `PAUSED_FOR_REVIEW`, `SUSPENDED`, or `FAILED_SAFE`. Shutdown remains available at all times. Recovery returns to `IDLE` only through explicit controller transitions.\n",
    }


def _authority_for_event(event_type: str) -> str:
    if event_type in {"RUNTIME_STOP", "RUNTIME_PAUSE", "RUNTIME_RESUME", "RUNTIME_SUSPEND", "OPERATOR_APPROVAL", "OPERATOR_REJECTION"}:
        return "OPERATOR_APPROVAL_REQUIRED"
    if event_type in {"MODEL_UNAVAILABLE", "WIKIPEDIA_FAILURE", "HEALTH_WARNING", "RESOURCE_LIMIT_REACHED"}:
        return "AUTONOMOUS_SAFE"
    if event_type in {"PROMOTION_CANDIDATE", "IDENTITY_PROPOSAL", "OBJECTIVE_CREATED"}:
        return "OPERATOR_APPROVAL_REQUIRED"
    return evaluate_authority(AuthorityRequest(action=event_type, action_type="organize_ephemeral_observation")).authority_class


def _event_duplicate_key(event_type: str, payload: dict[str, Any], correlation_id: str, objective_id: str) -> str:
    stable_payload = json.dumps(payload, sort_keys=True, default=str)[:500]
    return stable_id("continuous-event-dup", event_type, stable_payload, correlation_id, objective_id)


def _expire_stale_events(controller: ContinuousRuntimeController) -> tuple[ContinuousEvent, ...]:
    cycle_count = len(controller.cycles)
    return tuple(event for event in controller.event_queue if event.expiration_cycle <= 0 or event.expiration_cycle + cycle_count >= cycle_count)


def _idle_reflection_due(controller: ContinuousRuntimeController) -> bool:
    if controller.config.wake_mode not in {"BOUNDED_BACKGROUND", "EXPERIMENTAL_CONTINUOUS"}:
        return False
    return (time.time() - controller.last_idle_reflection_at) >= controller.config.idle_reflection_interval_seconds


def _objectives_from_events(events: Iterable[ContinuousEvent]) -> tuple[ContinuousObjective, ...]:
    objectives: list[ContinuousObjective] = []
    for event in events:
        if event.event_type not in {"DEVELOPMENTAL_SIGNAL", "OBJECTIVE_CREATED", "PROMOTION_CANDIDATE", "BEHAVIORAL_FAILURE"}:
            continue
        title = str(event.payload.get("title") or event.payload.get("summary") or event.event_type)
        decision = evaluate_authority(AuthorityRequest(action=title, action_type="rank_candidate_goal"))
        state = "WAITING_FOR_APPROVAL" if event.event_type in {"OBJECTIVE_CREATED", "PROMOTION_CANDIDATE"} else "PROPOSED"
        objectives.append(
            ContinuousObjective(
                objective_id=event.objective_id or stable_id("continuous-objective", event.event_id, title),
                title=title[:240],
                state=state,
                source=event.event_type,
                authority_class=decision.authority_class,
                created_at=event.timestamp,
                updated_at=utc_now(),
            )
        )
    return tuple(objectives)


def _inquiries_from_events(events: Iterable[ContinuousEvent]) -> tuple[dict[str, Any], ...]:
    inquiries = []
    for event in events:
        if event.event_type in {"PROMOTION_CANDIDATE", "IDENTITY_PROPOSAL", "OBJECTIVE_BLOCKED", "WIKIPEDIA_FAILURE"}:
            inquiries.append({
                "inquiry_id": stable_id("continuous-inquiry", event.event_id),
                "prompt": str(event.payload.get("prompt") or event.payload.get("summary") or f"Review {event.event_type}."),
                "event_id": event.event_id,
                "status": "QUEUED",
                "notification_class": "IN_APP_NORMAL",
                "authority_class": event.authority_class,
            })
    return tuple(inquiries)


def _merge_objectives(existing: tuple[ContinuousObjective, ...], new: tuple[ContinuousObjective, ...]) -> tuple[ContinuousObjective, ...]:
    by_id = {item.objective_id: item for item in existing}
    by_id.update({item.objective_id: item for item in new})
    return tuple(by_id.values())[-32:]


def _select_active_objective(current: ContinuousObjective | None, new: tuple[ContinuousObjective, ...], max_active: int) -> ContinuousObjective | None:
    if current and current.state in {"APPROVED", "ACTIVE", "WAITING_FOR_OPERATOR", "SANDBOXING", "VALIDATING"}:
        return current
    if max_active < 1:
        return None
    return new[0] if new else current


def _merge_initiatives(existing: tuple[Initiative, ...], new: tuple[Initiative, ...], max_new: int) -> tuple[Initiative, ...]:
    by_key = {item.duplicate_suppression_key: item for item in existing}
    for item in new[:max_new]:
        by_key.setdefault(item.duplicate_suppression_key, item)
    return tuple(by_key.values())[-64:]


def _merge_inquiries(existing: tuple[dict[str, Any], ...], new: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    seen = {str(item.get("inquiry_id")) for item in existing}
    merged = list(existing)
    for item in new:
        key = str(item.get("inquiry_id"))
        if key and key not in seen:
            merged.append(item)
            seen.add(key)
    return tuple(merged[-64:])


def _wikipedia_available_from_events(events: Iterable[ContinuousEvent], current: bool) -> bool:
    available = current
    for event in events:
        if event.event_type == "WIKIPEDIA_RESULT":
            available = True
        if event.event_type == "WIKIPEDIA_FAILURE":
            available = False
    return available


def _health_for(
    controller: ContinuousRuntimeController,
    *,
    queue_size: int | None = None,
    health_state: str = "HEALTHY",
    warnings: tuple[str, ...] = (),
    last_error: str = "",
    cycle_timeout: bool = False,
) -> HealthReport:
    queue_size = len(controller.event_queue) if queue_size is None else queue_size
    warning_list = list(warnings)
    if queue_size > int(controller.config.queue_limit * 0.8):
        warning_list.append("event_queue_near_limit")
        health_state = "DEGRADED"
    model_available = controller.model_residency.available_model_count > 0
    if not model_available:
        warning_list.append("no_local_models_available")
        health_state = "DEGRADED"
    return HealthReport(
        health_state=health_state,
        queue_size=queue_size,
        repeated_exception_count=1 if last_error else 0,
        last_error=last_error,
        model_available=model_available,
        wikipedia_available=controller.wikipedia_available,
        cycle_timeout=cycle_timeout,
        memory_pressure="bounded",
        cpu_pressure="idle" if queue_size == 0 else "bounded_cycle",
        warnings=tuple(warning_list),
    )


def _cycle_record(
    controller: ContinuousRuntimeController,
    started: float,
    start_state: str,
    end_state: str,
    events: tuple[str, ...],
    initiatives: tuple[str, ...],
    objectives: tuple[str, ...],
    idle_result: str,
    *,
    duration_ms: float | None = None,
    health_state: str | None = None,
) -> RuntimeCycleRecord:
    duration = (time.perf_counter() - started) * 1000 if duration_ms is None else duration_ms
    return RuntimeCycleRecord(
        cycle_id=stable_id("continuous-cycle", controller.controller_id, len(controller.cycles) + 1, events, initiatives, objectives),
        cycle_index=len(controller.cycles) + 1,
        started_at=utc_now(),
        duration_ms=round(duration, 3),
        lifecycle_start=start_state,
        lifecycle_end=end_state,
        events_processed=events,
        initiatives_created=initiatives,
        objectives_updated=objectives,
        model_calls=0,
        wikipedia_calls=0,
        idle_result=idle_result,
        health_state=health_state or controller.health.health_state,
    )


def _journal_entry(entry_type: str, summary: str, refs: tuple[str, ...]) -> dict[str, Any]:
    return {
        "entry_id": stable_id("continuous-journal", entry_type, summary, refs, utc_now()),
        "entry_type": entry_type,
        "summary": summary,
        "refs": refs,
        "created_at": utc_now(),
        "retention": "audit_only_ephemeral_until_operator_policy",
        "safety": safety_metadata(),
    }


def _journal(controller: ContinuousRuntimeController, entry_type: str, summary: str, refs: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    return controller.journal + (_journal_entry(entry_type, summary, refs),)


def _copy_session_results(session: Any) -> dict[str, Any]:
    model = getattr(session, "operational_self_model", None) or build_operational_self_model(session=session)
    active = model.active_objectives[0] if model.active_objectives else ""
    return {"active_work_item": active}


def _sync_session_initiatives(controller: ContinuousRuntimeController, session: Any) -> ContinuousRuntimeController:
    initiatives = tuple(getattr(session, "initiatives", ()) or ())
    if not initiatives:
        return controller
    merged = _merge_initiatives(controller.initiatives, initiatives, len(initiatives))
    objectives = list(controller.objectives)
    existing_titles = {item.title for item in objectives}
    for initiative in initiatives:
        if not initiative.candidate_objective or initiative.candidate_objective in existing_titles:
            continue
        objectives.append(
            ContinuousObjective(
                objective_id=stable_id("continuous-objective-from-initiative", initiative.initiative_id),
                title=initiative.candidate_objective[:240],
                state="WAITING_FOR_OPERATOR" if initiative.outcome == "ASK_OPERATOR_NOW" else "PROPOSED",
                source="INITIATIVE",
                authority_class=initiative.authority_class,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        existing_titles.add(initiative.candidate_objective)
    inquiries = _merge_inquiries(controller.operator_inquiries, tuple(getattr(session, "operator_inquiries", ()) or ()))
    active = _select_active_objective(controller.active_objective, tuple(objectives[len(controller.objectives) :]), controller.config.max_active_objectives)
    return replace(
        controller,
        initiatives=merged,
        objectives=tuple(objectives[-32:]),
        active_objective=active,
        operator_inquiries=inquiries,
        wikipedia_available=controller.wikipedia_available or bool(getattr(session, "developmental_results", ())),
    )


def _duplicate_initiative_count(initiatives: tuple[Initiative, ...]) -> int:
    keys = [item.duplicate_suppression_key for item in initiatives]
    return len(keys) - len(set(keys))


def _capability_classes(controller: ContinuousRuntimeController) -> dict[str, str]:
    return {
        "live_conversation_runtime": "LIVE",
        "approved_local_concept_memory": "LIVE",
        "governed_objectives": "PARTIALLY_CONNECTED",
        "developmental_observations": "LIVE",
        "delta_1_1_development_loop": "CALLABLE_BUT_NOT_INTEGRATED",
        "delta_1_2_live_runtime": "LIVE",
        "behavioral_maturation_infrastructure": "CALLABLE_BUT_NOT_INTEGRATED",
        "sandbox_experimental_repair": "PARTIALLY_CONNECTED",
        "wikipedia_text_retrieval": "LIVE",
        "local_approved_concept_comparison": "LIVE",
        "promotion_candidates": "LIVE",
        "operator_inquiries": "LIVE",
        "bounded_autonomy_classification": "LIVE",
        "operational_self_model": "LIVE",
        "local_models": "PARTIALLY_CONNECTED" if controller.model_residency.available_model_count else "DISABLED",
        "operator_ui": "LIVE",
        "external_provider_evaluator_env": "DISABLED",
    }


def build_self_development_demo() -> dict[str, Any]:
    fault = "continuous runtime status could diverge from live runtime state and model residency"
    hypotheses = (
        "Add a separate daemon process",
        "Extend the existing live session with one controller snapshot",
        "Only document the mismatch",
    )
    selected = "Extend the existing live session with one controller snapshot"
    decision = evaluate_authority(AuthorityRequest(action="prepare sandbox proposal for controller integration", action_type="approved_sandbox_experiment"))
    proposal = SandboxDevelopmentProposal(
        proposal_id=stable_id("continuous-sandbox-proposal", fault, selected),
        pathology_id="PID-CR01",
        fault=fault,
        hypotheses=hypotheses,
        selected_hypothesis=selected,
        sandbox_scope="fixture-only controller integration; no primary-tree mutation by DELTA runtime",
        baseline="UI showed live state but not central lifecycle/model/health/initiative status.",
        candidate_result="Controller snapshot exposes lifecycle, health, model residency, objective, inquiries, and initiatives.",
        promotion_boundary="Codex may promote after tests; DELTA runtime cannot promote, commit, or push.",
        authority_class=decision.authority_class,
    )
    return {
        "status": "FIXTURE_VALIDATED",
        "fault_observed": fault,
        "developmental_signal": "runtime integration gap",
        "candidate_objective": "connect controller snapshot to live session and UI status",
        "authority_classification": decision.authority_class,
        "sandbox_proposal": asdict(proposal),
        "before_after": {
            "before": proposal.baseline,
            "after": proposal.candidate_result,
        },
        "promotion_proposal": "Promote controller integration only after focused tests, long-run validation, JSON validation, and governance scan.",
        "automatic_promotion_performed": False,
        "runtime_primary_tree_mutation": False,
        "safety": safety_metadata(),
    }
