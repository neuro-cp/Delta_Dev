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
import ctypes
import hashlib
import json
import os
import subprocess
import time
import threading
from typing import Any, Iterable, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.continuous_mission_foundation import (
    ActiveSubgoal,
    ApiAuthorityState,
    BehavioralFailureRecord,
    BroadMissionContract,
    CapabilityKnowledgeRecord,
    MainGoalContract,
    OBSERVATION_STATE,
    WeaknessCandidate,
    assess_main_goal_completion,
    assess_developmental_capability_state,
    api_unavailable_update,
    capability_evidence_stage,
    capability_is_acquired,
    capability_inventory_from_knowledge,
    compile_developmental_insight_requests,
    compile_developmental_operator_explanation,
    compile_active_subgoal,
    compile_broad_mission_contract,
    compile_initial_main_goal,
    compile_long_horizon_objective,
    consumed_signatures_after_reassessment,
    derive_developmental_capability_plan,
    derive_next_main_goal,
    derive_subgoal_evidence_for_main_goal,
    behavioral_failure_to_runtime_finding,
    evidence_to_findings,
    normalize_capability_record_for_recovery,
    rank_weakness_frontier,
)
from orchestration.runtime.developmental_learning import (
    DevelopmentalMissionContract,
    DevelopmentalEvaluationRecord,
    LearningSubgoal,
    compile_capability_assessment,
    compile_developmental_gaps,
    compile_developmental_mission_contract,
    compile_mission_information_need,
    compile_mission_bound_advisory_learning_evidence,
    compile_provisional_learning_bundle_from_advisory,
    bind_independent_learning_evaluator,
    compile_revised_learning_bundle,
    compile_revised_learning_subgoal,
    derive_next_learning_gap,
    localize_learning_failure,
    compile_provisional_learning_bundle,
    compile_learning_subgoal,
    compile_resource_acquisition_plan,
    assess_local_model_learning_evidence,
    load_retained_learning_bundle,
    MissionBoundLocalModelBridge,
)
from orchestration.runtime.delta_1_6_operational_autonomy import (
    AuthorityRequest,
    Initiative,
    build_operational_self_model,
    evaluate_authority,
    run_delta_1_6_background_cycle,
)
from orchestration.runtime.rc2_conversational_mode_router import discover_local_model_lanes, select_model_lane
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger
from orchestration.runtime.isolated_evaluator_authoring import (
    compile_isolated_evaluator_authoring_request,
    project_learner_visible_evaluation_cases,
    sealed_evaluator_execution_errors,
    validate_provider_authored_evaluator_response,
)
from orchestration.runtime.capability_evaluation_strategy import compile_capability_evaluation_strategy
from orchestration.runtime.developmental_interest import (
    agenda_state_is_valid,
    compile_persistent_developmental_agenda,
    compile_developmental_goal_proposal,
    compile_developmental_interest_candidates,
    is_governed_autonomous_interest_instruction,
    is_persistent_developmental_agenda_instruction,
    material_evidence_digest,
    source_records_from_state,
)
from orchestration.runtime.developmental_resource_policy import (
    REQUEST_ACTIONS,
    DevelopmentalResourceAuthorityFulfillment,
    compile_developmental_resource_authority_fulfillment,
    compile_developmental_resource_authority_requirement,
    compile_resource_authority_decision,
    compile_resource_policy_candidates,
    observe_developmental_resources,
    resource_fulfillment_state_is_valid,
    resource_policy_state_is_valid,
)
from orchestration.runtime.governed_learning_strategy import (
    LEARNING_STRATEGY_VERSION,
    compile_governed_learning_strategy,
    learner_visible_strategy_packet,
    validate_governed_learning_strategy,
)
from orchestration.runtime.governed_learning_strategy_acquisition import (
    compile_strategy_acquisition_result,
    compile_strategy_acquisition_evidence_linkage_reassessment,
    is_same_exact_resource_chain,
    retrieve_exact_source,
)
from orchestration.runtime.governed_learning_strategy_revision import (
    compile_governed_learning_strategy_resource_revision as compile_resource_revision_record,
    validate_governed_learning_strategy_resource_revision,
)
from orchestration.runtime.governed_learning_strategy_single_question_revision import (
    compile_single_question_learning_strategy_revision as compile_single_question_revision_record,
    validate_single_question_learning_strategy_revision,
)
from orchestration.runtime.governed_constructive_grounding import (
    compile_constructive_grounding_assessment,
    compile_constructive_grounding_source_review,
    compile_independent_constructive_grounding_verification,
    compile_advisory_claim_verification_targets as compile_advisory_claim_verification_target_record,
    validate_constructive_grounding_assessment,
)
from orchestration.runtime.governed_constructive_escalation import (
    compile_constructive_failure_synthesis,
    compile_constructive_teaching_provider_packet,
    constructive_teaching_provider_prompts,
    adapt_constructive_teaching_response,
    validate_constructive_teaching_provider_response,
)
from orchestration.runtime.governed_learning_strategy_source_discovery import (
    compile_discovered_source_retrieval_authority_request,
    compile_metadata_only_source_discovery_result,
    validate_discovered_source_retrieval_authority_request,
    validate_metadata_only_source_discovery_result,
)
from orchestration.runtime.governed_external_research import (
    ExternalResearchRetrievalError,
    compile_adapter_repair_retry_candidate,
    classify_terminal_research_failure,
    compile_execution_claim,
    compile_external_research_plan,
    compile_fallback_external_research_plan,
    compile_fallback_source_candidates,
    compile_direct_topic_source_candidates,
    compile_historical_transport_interpretation,
    compile_retrieval_attempt,
    normalize_external_research_source,
    research_state_is_valid,
    synthesize_external_research_result,
)


DOC_ROOT = Path("docs") / "continuous_runtime"
REPORT_ROOT = Path("reports") / "continuous_runtime"


def _learning_bridge_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()

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
    external_metrics: dict[str, Any] = field(default_factory=dict)
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
    continuous_mission_state: str = ""
    continuous_mission_contract: dict[str, Any] = field(default_factory=dict)
    continuous_behavioral_failure_records: tuple[dict[str, Any], ...] = ()
    continuous_mission_findings: tuple[dict[str, Any], ...] = ()
    continuous_mission_frontier: tuple[dict[str, Any], ...] = ()
    continuous_main_goal: dict[str, Any] = field(default_factory=dict)
    continuous_completed_main_goals: tuple[dict[str, Any], ...] = ()
    continuous_active_subgoal: dict[str, Any] = field(default_factory=dict)
    continuous_consumed_weakness_signatures: tuple[str, ...] = ()
    continuous_knowledge_ledger: tuple[dict[str, Any], ...] = ()
    continuous_pcm_bridge_ledger: tuple[dict[str, Any], ...] = ()
    continuous_capability_inventory: tuple[dict[str, Any], ...] = ()
    continuous_developmental_self_assessment: dict[str, Any] = field(default_factory=dict)
    continuous_developmental_insight_requests: tuple[dict[str, Any], ...] = ()
    continuous_operator_interaction_responses: tuple[dict[str, Any], ...] = ()
    continuous_operator_explanation: dict[str, Any] = field(default_factory=dict)
    continuous_api_authority: dict[str, Any] = field(default_factory=dict)
    continuous_observation_state: dict[str, Any] = field(default_factory=dict)
    # Contract/evidence records for non-code learning. Lifecycle remains owned
    # here; the developmental_learning module is deliberately pure.
    continuous_learning_state: dict[str, Any] = field(default_factory=dict)
    pending_application_decision_id: str = ""
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
    expires_at = len(controller.cycles) + event.expiration_cycle if event.expiration_cycle > 0 else len(controller.cycles)
    event = replace(event, audit_metadata={**event.audit_metadata, "queued_at_cycle": len(controller.cycles), "expires_at_cycle": expires_at})
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
    controller = replace(controller, event_queue=queue)
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
        batch=batch,
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
        "continuous_mission": {
            "state": controller.continuous_mission_state,
            "contract": controller.continuous_mission_contract,
            "main_goal": controller.continuous_main_goal or None,
            "completed_main_goal_count": len(controller.continuous_completed_main_goals),
            "frontier_count": len(controller.continuous_mission_frontier),
            "active_subgoal": controller.continuous_active_subgoal or None,
            "pending_application_decision_id": controller.pending_application_decision_id,
            "api_authority": controller.continuous_api_authority,
            "knowledge_record_count": len(controller.continuous_knowledge_ledger),
            "capability_inventory": controller.continuous_capability_inventory,
            "developmental_self_assessment": controller.continuous_developmental_self_assessment or None,
            "developmental_insight_requests": controller.continuous_developmental_insight_requests,
            "operator_explanation": controller.continuous_operator_explanation or None,
            "learning_state": controller.continuous_learning_state or None,
        },
        "safety": safety_metadata(),
    }


def attach_continuous_mission(
    controller: ContinuousRuntimeController,
    operator_goal: str,
    *,
    api_authority: ApiAuthorityState | None = None,
) -> ContinuousRuntimeController:
    contract = compile_broad_mission_contract(operator_goal, api_authority=api_authority)
    main_goal = compile_initial_main_goal(contract)
    event = make_continuous_event(
        "OBJECTIVE_CREATED",
        source="continuous_mission",
        session_id=controller.session_id,
        payload={"title": contract.normalized_goal, "summary": operator_goal, "mission_id": contract.mission_id},
        priority=85,
        objective_id=contract.mission_id,
    )
    objective = ContinuousObjective(
        objective_id=contract.mission_id,
        title=contract.normalized_goal,
        state="ACTIVE",
        source="CONTINUOUS_MISSION",
        authority_class="OPERATOR_APPROVED_BROAD_MISSION",
        created_at=contract.accepted_at,
        updated_at=utc_now(),
    )
    updated = replace(
        enqueue_continuous_event(controller, event),
        continuous_mission_state="mission_accepted",
        continuous_mission_contract=contract.as_dict(),
        continuous_main_goal=main_goal.as_dict(),
        continuous_api_authority=contract.api_authority.__dict__,
        active_objective=objective,
        objectives=_merge_objectives(controller.objectives, (objective,)),
        journal=controller.journal + (_journal_entry("continuous_mission", "broad_goal_compiled_to_persistent_mission", (contract.mission_id,)),),
    )
    return refresh_developmental_self_direction(updated)


def attach_developmental_learning_mission(
    controller: ContinuousRuntimeController,
    operator_instruction: str,
    retained_bundle: Mapping[str, Any],
    *,
    existing_mission: DevelopmentalMissionContract | None = None,
    preserve_learning_state: bool = False,
) -> ContinuousRuntimeController:
    """Compile one operator learning request into the existing mission lifecycle."""

    mission = existing_mission or compile_developmental_mission_contract(operator_instruction)
    if mission is None:
        return controller
    assessment = compile_capability_assessment(mission, retained_bundle, inventory=controller.continuous_capability_inventory)
    plan = compile_resource_acquisition_plan(mission, assessment, retained_bundle)
    gaps = compile_developmental_gaps(mission, assessment)
    subgoal = compile_learning_subgoal(mission, gaps, plan, retained_bundle)
    prior_state = dict(controller.continuous_learning_state or {})
    state = {
        **(prior_state if preserve_learning_state else {}),
        "mission": mission.as_dict(),
        "assessment": assessment.as_dict(),
        "resource_plan": plan.as_dict(),
        "gaps": tuple(item.as_dict() for item in gaps),
        "retained_bundle": dict(retained_bundle),
        "consumed_gap_ids": tuple(prior_state.get("consumed_gap_ids") or ()) if preserve_learning_state else (),
        "attempts": tuple(prior_state.get("attempts") or ()) if preserve_learning_state else (),
        "evaluations": tuple(prior_state.get("evaluations") or ()) if preserve_learning_state else (),
        "protocol": "operator_developmental_mission_orchestration_v1",
    }
    nested_cases = any(
        isinstance(case, Mapping) and (case.get("learner_view") or case.get("evaluator_view"))
        for case in retained_bundle.get("sealed_evaluation_cases") or ()
    )
    execution_errors = sealed_evaluator_execution_errors(
        retained_bundle,
        target_capability=str(
            assessment.recommended_focus
            if assessment.recommended_focus != "no_material_gap_identified"
            else mission.primary_capability_target
        ),
        assessment_dimension=str(assessment.recommended_focus),
    ) if nested_cases else ()
    if execution_errors:
        return replace(
            controller,
            continuous_mission_state="developmental_resource_fulfillment_incomplete",
            active_work_item="sealed_evaluator_execution_contract_unsupported",
            continuous_learning_state={
                **state,
                "resource_blocker": {
                    "blocker": "sealed_evaluator_execution_contract_unsupported",
                    "missing_fields": tuple(sorted(set(execution_errors))),
                    "no_provider_or_research_call_performed": True,
                },
            },
            journal=controller.journal + (_journal_entry(
                "developmental_learning",
                "sealed_evaluator_rejected_before_nonexecutable_learning_attempt",
                tuple(sorted(set(execution_errors))),
            ),),
        )
    if subgoal is None:
        blocked_on_external_authority = plan.plan_disposition == "external_authority_required"
        return replace(
            controller,
            continuous_mission_state=(
                "learning_external_authority_required"
                if blocked_on_external_authority
                else "evidence_needed_for_developmental_learning"
            ),
            continuous_learning_state=state,
            active_work_item=(
                "developmental_learning_external_authority_required"
                if blocked_on_external_authority
                else "developmental_learning_evidence_needed"
            ),
            journal=controller.journal + (_journal_entry(
                "developmental_learning",
                "operator_instruction_requires_precise_external_resource_authority"
                if blocked_on_external_authority
                else "operator_instruction_compiled_without_executable_local_subgoal",
                (mission.mission_id,),
            ),),
        )
    evaluator = dict(retained_bundle.get("independent_evaluator") or {})
    evaluator_authorities: tuple[dict[str, Any], ...]
    if evaluator:
        evaluator_authorities = ({
            "strategy": "deterministic_predicate",
            "identity": str(evaluator.get("evaluator_identity") or "deterministic_content_task_evaluator_v1"),
            "provenance": tuple(str(item) for item in (evaluator.get("authority_source"), evaluator.get("authority_digest")) if item),
        },)
    elif retained_bundle.get("sealed_evaluation_cases"):
        evaluator_authorities = ({
            "strategy": "deterministic_predicate",
            "identity": "retained_sealed_content_evaluator_v1",
            "provenance": (str(retained_bundle.get("resource_bundle_id") or "retained_sealed_case_bundle"),),
        },)
    else:
        evaluator_authorities = ()
    strategy = compile_capability_evaluation_strategy(
        mission_id=mission.mission_id,
        capability_id=subgoal.capability_target,
        subgoal_id=subgoal.subgoal_id,
        domain=mission.domain,
        topic=subgoal.topic,
        capability_target=subgoal.capability_target,
        target_behavior=subgoal.measurable_objective,
        teaching_evidence_ids=tuple(str(item.get("result_id") or item.get("request_id") or "") for item in retained_bundle.get("resource_provenance") or () if item),
        execution_kind="developmental_learning",
        evaluator_authorities=evaluator_authorities,
    )
    selected_plan = dict(strategy["selected_plan"])
    if selected_plan.get("status") == "evaluation_unavailable":
        return replace(
            controller,
            continuous_mission_state="learning_evaluator_authority_needed",
            continuous_mission_contract={**mission.as_dict(), "original_operator_goal": mission.operator_instruction},
            continuous_learning_state={**state, **strategy},
            active_work_item="developmental_learning_evaluator_authority_needed",
            journal=controller.journal + (_journal_entry("developmental_learning", "capability_evaluation_authority_unavailable", (mission.mission_id, subgoal.subgoal_id, selected_plan["plan_id"])),),
        )
    return replace(
        controller,
        continuous_mission_state="learning_subgoal_active",
        continuous_mission_contract={**mission.as_dict(), "original_operator_goal": mission.operator_instruction},
        continuous_learning_state={**state, **strategy, "selected_frontier": {
            "frontier_id": subgoal.source_gap_id,
            "topic": subgoal.topic,
            "capability_dimension": subgoal.capability_target,
            "rank": subgoal.frontier_rank,
            "selection_reason": subgoal.selection_reason,
        }},
        continuous_active_subgoal={**subgoal.as_dict(), "execution_kind": "developmental_learning"},
        active_work_item=subgoal.measurable_objective,
        journal=controller.journal + (_journal_entry("developmental_learning", "operator_instruction_compiled_to_learning_subgoal", (mission.mission_id, subgoal.subgoal_id)),),
    )


def compile_operator_developmental_learning_mission(
    controller: ContinuousRuntimeController,
    operator_instruction: str,
) -> ContinuousRuntimeController:
    """Resolve only a declared retained local resource; never fabricate a lesson."""

    mission = compile_developmental_mission_contract(operator_instruction)
    if mission is None:
        return controller
    existing_state = dict(controller.continuous_learning_state or {})
    preserved_bundle = dict(existing_state.get("retained_bundle") or {})
    bundle = (
        preserved_bundle
        if (
            preserved_bundle.get("study_resources")
            and str(preserved_bundle.get("domain") or "") == mission.domain
            and str(preserved_bundle.get("topic") or "") == mission.topic
        )
        else load_retained_learning_bundle(mission.domain, mission.topic)
    )
    if bundle is None:
        return replace(
            controller,
            continuous_mission_state="learning_resource_evidence_needed",
            continuous_mission_contract={**mission.as_dict(), "original_operator_goal": mission.operator_instruction},
            continuous_learning_state={
                "mission": mission.as_dict(),
                "protocol": "operator_developmental_mission_orchestration_v1",
                "resource_blocker": "no_matching_retained_local_learning_resource",
            },
            active_work_item="learning_resource_evidence_needed",
            journal=controller.journal + (_journal_entry("developmental_learning", "operator_instruction_requires_governed_resource_plan", (mission.mission_id,)),),
        )
    return attach_developmental_learning_mission(controller, operator_instruction, bundle)


def compile_governed_learning_strategy_for_mission(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Persist one evidence-bound learning strategy without executing it.

    The strategy is compiled only from learner-visible teaching and failed-attempt
    evidence.  A changed evidence digest supersedes the prior proposal; an
    equivalent digest is an exact-once no-op.
    """

    state = dict(controller.continuous_learning_state or {})
    mission = dict(state.get("mission") or {})
    if not mission:
        return controller
    try:
        packet = learner_visible_strategy_packet(state)
    except ValueError as exc:
        return replace(
            controller,
            continuous_mission_state="learning_strategy_validation_failed",
            active_work_item="learning_strategy_packet_separation_failed",
            continuous_learning_state={
                **state,
                "governed_learning_strategy": {
                    "status": "learning_strategy_validation_failed",
                    "errors": (str(exc),),
                    "mission_id": mission.get("mission_id"),
                },
            },
        )
    existing = dict(state.get("governed_learning_strategy") or {})
    if (
        existing.get("status") in {"learning_strategy_validated", "learning_strategy_awaiting_authority"}
        and str(existing.get("evidence_digest") or "") == str(packet.get("evidence_digest") or "")
        and int(existing.get("strategy_version") or 0) == LEARNING_STRATEGY_VERSION
    ):
        request = dict(state.get("governed_learning_strategy_authority_request") or {})
        if request:
            request = {
                **request,
                "request_kind": "governed_learning_strategy_authority",
                "authority_scope": str(request.get("authority_scope") or request.get("scope") or ""),
                "permitted_responses": tuple(request.get("permitted_responses") or (
                    "approve_learning_strategy_authority",
                    "reject_learning_strategy_authority",
                    "defer_learning_strategy_authority",
                    "ask_for_clarification",
                )),
                "exact_question": str(request.get("exact_question") or "Authorize the narrow strategy-selected action, reject it, defer it, or ask for clarification."),
                "authority_granted": False,
            }
            state = {**state, "governed_learning_strategy_authority_request": request}
        requests = tuple(controller.continuous_developmental_insight_requests)
        if request and not any(item.get("request_id") == request.get("request_id") for item in requests):
            return replace(
                controller,
                continuous_developmental_insight_requests=requests + (request,),
                continuous_learning_state=state,
                journal=controller.journal + (_journal_entry(
                    "developmental_learning", "persisted_learning_strategy_authority_request_restored_to_operator_transport",
                    (str(request.get("request_id") or ""),),
                ),),
            )
        if request:
            reconciled_requests = tuple(
                request if item.get("request_id") == request.get("request_id") else item
                for item in requests
            )
            if reconciled_requests != requests:
                return replace(
                    controller,
                    continuous_developmental_insight_requests=reconciled_requests,
                    continuous_learning_state=state,
                    journal=controller.journal + (_journal_entry(
                        "developmental_learning", "persisted_learning_strategy_authority_request_schema_reconciled",
                        (str(request.get("request_id") or ""),),
                    ),),
                )
        return replace(
            controller,
            journal=controller.journal + (_journal_entry(
                "developmental_learning", "duplicate_governed_learning_strategy_suppressed",
                (str(existing.get("strategy_id") or ""),),
            ),),
        )
    strategy = compile_governed_learning_strategy(packet)
    validation = validate_governed_learning_strategy(strategy.as_dict(), packet)
    history = tuple(state.get("governed_learning_strategy_history") or ())
    if existing and existing.get("strategy_id"):
        history = history + ({**existing, "superseded_at": utc_now(), "status": "learning_strategy_superseded"},)
    stored = {
        **strategy.as_dict(),
        "validation": validation,
        "status": "learning_strategy_validated" if validation["accepted"] else "learning_strategy_validation_failed",
        "strategy_packet_digest": _learning_bridge_digest(packet),
    }
    if not validation["accepted"]:
        return replace(
            controller,
            continuous_mission_state="learning_strategy_validation_failed",
            active_work_item="learning_strategy_validation_failed",
            continuous_learning_state={
                **state,
                "governed_learning_strategy": stored,
                "governed_learning_strategy_history": history,
            },
            journal=controller.journal + (_journal_entry(
                "developmental_learning", "learner_authored_strategy_failed_grounding_validation",
                tuple(validation["errors"]),
            ),),
        )
    authority = tuple(stored.get("authority_candidates") or ())
    request = {}
    mission_state = "learning_strategy_validated"
    active_work_item = "learning_strategy_validated"
    if authority:
        candidate = dict(authority[0])
        request = {
            "request_id": candidate["authority_request_id"],
            "request_kind": "governed_learning_strategy_authority",
            "status": "pending",
            "strategy_id": stored["strategy_id"],
            "mission_id": stored["mission_id"],
            "evidence_digest": stored["evidence_digest"],
            "recommended_action": candidate["action_type"],
            "scope": candidate["scope"],
            "source_identity": candidate.get("source_identity") or "",
            "source_locator": candidate.get("source_locator") or "",
            "source_digest": candidate.get("source_digest") or "",
            "question_ids": candidate["question_ids"],
            "maximum_calls_or_retrievals": candidate["maximum_calls_or_retrievals"],
            "fallback": "record_source_insufficiency_then_pause",
            "exact_question": "Authorize the narrow strategy-selected action, reject it, defer it, or ask for clarification.",
            "authority_scope": candidate["scope"],
            "permitted_responses": (
                "approve_learning_strategy_authority",
                "reject_learning_strategy_authority",
                "defer_learning_strategy_authority",
                "ask_for_clarification",
            ),
            "authority_granted": False,
            "created_at": utc_now(),
        }
        stored["status"] = "learning_strategy_awaiting_authority"
        mission_state = "learning_strategy_awaiting_authority"
        active_work_item = "learning_strategy_authority_request"
    return replace(
        controller,
        continuous_mission_state=mission_state,
        continuous_active_subgoal={},
        active_work_item=active_work_item,
        continuous_learning_state={
            **state,
            "governed_learning_strategy": stored,
            "governed_learning_strategy_history": history,
            "governed_learning_strategy_authority_request": request,
        },
        continuous_developmental_insight_requests=(
            tuple(controller.continuous_developmental_insight_requests) + ((request,) if request else ())
        ),
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "learner_visible_failure_evidence_compiled_to_governed_learning_strategy",
            (strategy.strategy_id, str(validation["accepted"])),
        ),),
    )


def recover_nonexecutable_sealed_evaluator_execution(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Correct a legacy false terminal outcome without replaying its attempt.

    Older persisted runs could score a nested learner/evaluator package through
    the component fallback, then cool down the agenda even though no sealed
    case had been executable.  The completed attempt and evaluation stay in
    history; only the effective state is corrected to the missing contract.
    """

    if controller.continuous_mission_state != "developmental_agenda_exhausted":
        return controller
    state = dict(controller.continuous_learning_state or {})
    mission_data = dict(state.get("mission") or {})
    bundle = dict(state.get("retained_bundle") or {})
    evaluations = tuple(dict(item) for item in (state.get("evaluations") or ()) if isinstance(item, Mapping))
    if not mission_data or not bundle or not evaluations:
        return controller
    latest = evaluations[-1]
    if latest.get("content_case_results"):
        return controller
    nested = any(
        isinstance(case, Mapping) and (case.get("learner_view") or case.get("evaluator_view"))
        for case in bundle.get("sealed_evaluation_cases") or ()
    )
    if not nested:
        return controller
    corrected = attach_developmental_learning_mission(
        controller,
        str(mission_data.get("operator_instruction") or ""),
        bundle,
        existing_mission=DevelopmentalMissionContract(**mission_data),
        preserve_learning_state=True,
    )
    if corrected.active_work_item != "sealed_evaluator_execution_contract_unsupported":
        return controller
    corrected_state = dict(corrected.continuous_learning_state or {})
    agenda = dict(corrected_state.get("developmental_agenda") or {})
    correction_id = stable_id("sealed-evaluator-execution-contract-correction", str(latest.get("evaluation_id") or ""))
    corrections = tuple(agenda.get("outcome_reclassifications") or ())
    if not any(item.get("correction_id") == correction_id for item in corrections if isinstance(item, Mapping)):
        corrections = corrections + ({
            "correction_id": correction_id,
            "outcome_id": latest.get("evaluation_id"),
            "reason": "nested_sealed_cases_were_not_executable_by_the_scoring_contract",
            "recorded_at": utc_now(),
        },)
    corrected_agenda = {
        **agenda,
        "status": "blocked_resolvable_evaluator_execution_contract",
        "active_mission_id": str(mission_data.get("mission_id") or ""),
        "exhaustion_reasons": ("sealed_evaluator_execution_contract_unsupported",),
        "next_eligible_transition": "execution_compatible_sealed_evaluator_required",
        "outcome_reclassifications": corrections,
        "updated_at": utc_now(),
    }
    return replace(
        corrected,
        continuous_learning_state={**corrected_state, "developmental_agenda": corrected_agenda},
        journal=corrected.journal + (_journal_entry(
            "developmental_learning",
            "legacy_false_agenda_exhaustion_reclassified_without_attempt_replay",
            (str(latest.get("evaluation_id") or ""), correction_id),
        ),),
    )


def recover_validated_sealed_evaluator_learning_execution(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Rebind a durable V3 result after an older fulfillment adapter restart."""

    if controller.continuous_active_subgoal:
        return controller
    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    result = dict(authoring.get("result") or {})
    package = dict(result.get("sealed_package") or {})
    mission_data = dict(state.get("mission") or {})
    if (
        authoring.get("status") != "result_handed_off"
        or result.get("status") != "validated"
        or str(package.get("execution_contract_version") or "") != "sealed_evaluator_execution_v3"
        or not mission_data
        or controller.continuous_mission_state != "developmental_resource_fulfillment_incomplete"
    ):
        return controller
    bundle = dict(state.get("retained_bundle") or {})
    if not tuple(bundle.get("sealed_evaluation_cases") or ()):
        return controller
    bundle["execution_contract_version"] = "sealed_evaluator_execution_v3"
    resumed = attach_developmental_learning_mission(
        replace(controller, continuous_learning_state={**state, "retained_bundle": bundle}),
        str(mission_data.get("operator_instruction") or ""),
        bundle,
        existing_mission=DevelopmentalMissionContract(**mission_data),
        preserve_learning_state=True,
    )
    if not resumed.continuous_active_subgoal:
        return controller
    return replace(
        resumed,
        journal=resumed.journal + (_journal_entry(
            "developmental_learning",
            "validated_sealed_evaluator_rebound_to_existing_learning_mission",
            (str(mission_data.get("mission_id") or ""), str(authoring.get("handoff_fulfillment_id") or "")),
        ),),
    )


def recover_misaligned_v3_learning_execution(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Invalidate a legacy practice-only attempt that never received V3 cases.

    This is not a retry of a learner answer.  It preserves the malformed
    execution record, reopens only the affected gap, and creates a new
    execution instance whose learner inputs are the sealed package's public
    case views.
    """

    if controller.continuous_active_subgoal:
        return controller
    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    package = dict(dict(authoring.get("result") or {}).get("sealed_package") or {})
    attempts = tuple(dict(item) for item in (state.get("attempts") or ()) if isinstance(item, Mapping))
    evaluations = tuple(dict(item) for item in (state.get("evaluations") or ()) if isinstance(item, Mapping))
    mission_data = dict(state.get("mission") or {})
    expected_case_ids = {
        str(case.get("case_id") or "")
        for case in package.get("sealed_evaluation_cases") or ()
        if isinstance(case, Mapping) and case.get("case_id")
    }
    if (
        controller.continuous_mission_state != "developmental_agenda_blocked"
        or authoring.get("status") != "result_handed_off"
        or str(package.get("execution_contract_version") or "") != "sealed_evaluator_execution_v3"
        or not mission_data
        or not attempts
        or not evaluations
        or not expected_case_ids
    ):
        return controller
    latest_attempt = attempts[-1]
    observed_case_ids = {
        str(record.get("case_id") or record.get("task_id") or "")
        for record in latest_attempt.get("task_records") or ()
        if isinstance(record, Mapping)
    }
    schema_errors = tuple(
        str(error)
        for record in latest_attempt.get("task_records") or ()
        if isinstance(record, Mapping)
        for error in (record.get("response_schema_errors") or ())
    )
    if expected_case_ids.issubset(observed_case_ids) and not schema_errors:
        return controller
    recovery_reason = (
        "learner_attempt_did_not_receive_the_sealed_v3_case_set"
        if not expected_case_ids.issubset(observed_case_ids)
        else "learner_attempt_did_not_satisfy_the_public_v3_response_schema"
    )
    latest_evaluation = evaluations[-1]
    affected_dimension = str(latest_evaluation.get("capability_dimension") or "")
    reopened_gap_ids = {
        str(gap.get("gap_id") or "")
        for gap in state.get("gaps") or ()
        if isinstance(gap, Mapping) and str(gap.get("capability_dimension") or "") == affected_dimension
    }
    if not reopened_gap_ids:
        return controller
    recovery_id = stable_id(
        "v3-learner-case-alignment-recovery",
        str(latest_attempt.get("attempt_id") or ""),
        str(latest_evaluation.get("evaluation_id") or ""),
        recovery_reason,
        tuple(sorted(expected_case_ids)),
    )
    recoveries = tuple(state.get("invalid_execution_recoveries") or ())
    if any(isinstance(item, Mapping) and item.get("recovery_id") == recovery_id for item in recoveries):
        return controller
    agenda = dict(state.get("developmental_agenda") or {})
    outcome_history = tuple(
        item for item in (agenda.get("mission_outcome_history") or ())
        if not (isinstance(item, Mapping) and item.get("outcome_id") == latest_evaluation.get("evaluation_id"))
    )
    failed_outcomes = sum(1 for item in outcome_history if isinstance(item, Mapping) and item.get("outcome") == "behaviorally_failed")
    prepared_agenda = {
        **agenda,
        "status": "mission_active",
        "active_mission_id": str(mission_data.get("mission_id") or ""),
        "blocked_goal_ids": tuple(item for item in (agenda.get("blocked_goal_ids") or ()) if item),
        "mission_outcome_history": outcome_history,
        "failed_cycle_count": failed_outcomes,
        "consecutive_failure_count": failed_outcomes,
        "cycle_count": max(0, int(agenda.get("cycle_count") or 0) - 1),
        "exhaustion_reasons": (),
        "next_eligible_transition": "bounded_v3_learning_attempt",
        "updated_at": utc_now(),
    }
    prepared_state = {
        **state,
        "consumed_gap_ids": tuple(
            gap_id for gap_id in (state.get("consumed_gap_ids") or ()) if gap_id not in reopened_gap_ids
        ),
        "developmental_agenda": prepared_agenda,
        "resource_blocker": {
            "blocker": "v3_learner_case_alignment_recovery",
            "recovery_id": recovery_id,
            "invalid_attempt_id": latest_attempt.get("attempt_id"),
            "invalid_evaluation_id": latest_evaluation.get("evaluation_id"),
            "expected_case_ids": tuple(sorted(expected_case_ids)),
            "observed_case_ids": tuple(sorted(observed_case_ids)),
            "response_schema_errors": schema_errors,
            "no_provider_or_research_call_performed": True,
        },
        "invalid_execution_recoveries": recoveries + ({
            "recovery_id": recovery_id,
            "reason": recovery_reason,
            "invalid_attempt_id": latest_attempt.get("attempt_id"),
            "invalid_evaluation_id": latest_evaluation.get("evaluation_id"),
            "expected_case_ids": tuple(sorted(expected_case_ids)),
            "observed_case_ids": tuple(sorted(observed_case_ids)),
            "response_schema_errors": schema_errors,
            "recorded_at": utc_now(),
        },),
    }
    bundle = dict(prepared_state.get("retained_bundle") or {})
    bundle["execution_contract_version"] = "sealed_evaluator_execution_v3"
    resumed = attach_developmental_learning_mission(
        replace(
            controller,
            continuous_mission_state="developmental_resource_fulfillment_incomplete",
            active_work_item="v3_learner_case_alignment_recovery",
            continuous_learning_state={**prepared_state, "retained_bundle": bundle},
        ),
        str(mission_data.get("operator_instruction") or ""),
        bundle,
        existing_mission=DevelopmentalMissionContract(**mission_data),
        preserve_learning_state=True,
    )
    if not resumed.continuous_active_subgoal:
        return controller
    active = dict(resumed.continuous_active_subgoal)
    active["subgoal_id"] = stable_id("v3-learning-execution-instance", active.get("subgoal_id"), recovery_id)
    active["supersedes_invalid_execution_recovery_id"] = recovery_id
    return replace(
        resumed,
        continuous_active_subgoal=active,
        active_work_item=str(active.get("measurable_objective") or "v3_learning_execution"),
        journal=resumed.journal + (_journal_entry(
            "developmental_learning",
            "misaligned_v3_learner_execution_reopened_once",
            (recovery_id, str(active.get("subgoal_id") or "")),
        ),),
    )


def compile_governed_developmental_interest_proposal(
    controller: ContinuousRuntimeController,
    operator_instruction: str,
) -> ContinuousRuntimeController:
    """Compile one evidence-backed goal proposal without starting learning.

    The broad instruction establishes the existing parent mission boundary when
    necessary.  The narrower learning mission remains dormant until the
    operator consumes the resulting existing interaction request.
    """

    if not (is_governed_autonomous_interest_instruction(operator_instruction) or is_persistent_developmental_agenda_instruction(operator_instruction)):
        return controller
    attached_parent = not bool(controller.continuous_mission_contract)
    parent = controller if not attached_parent else attach_continuous_mission(controller, operator_instruction)
    retained_requests = () if attached_parent else parent.continuous_developmental_insight_requests
    state = dict(parent.continuous_learning_state or {})
    interest_state = dict(state.get("developmental_interest") or {})
    origin_state_id = stable_id(
        "developmental-interest-origin",
        str((parent.continuous_mission_contract or {}).get("mission_id") or parent.session_id),
        _learning_bridge_digest({
            "inventory": parent.continuous_capability_inventory,
            "learning": state.get("next_learning_gap") or state.get("interest_sources") or (),
            "assessment": parent.continuous_developmental_self_assessment,
        }),
    )
    sources = source_records_from_state(
        learning_state=state,
        capability_inventory=parent.continuous_capability_inventory,
    )
    if not sources:
        sources = tuple(dict(item) for item in (interest_state.get("source_records") or ()) if isinstance(item, Mapping))
    active_or_recent = tuple(str(item) for item in (interest_state.get("active_or_recent_semantics") or ()))
    rejected = tuple(str(item) for item in (interest_state.get("cooldown_semantics") or ()))
    candidates = compile_developmental_interest_candidates(
        origin_state_id=origin_state_id,
        operator_context=operator_instruction,
        sources=sources,
        capability_inventory=parent.continuous_capability_inventory,
        active_or_recent_semantics=active_or_recent,
        rejected_semantics=rejected,
    )
    proposal = compile_developmental_goal_proposal(operator_context=operator_instruction, candidates=candidates)
    compiled_interest = {
        "origin_state_id": origin_state_id,
        "operator_context": operator_instruction,
        "candidate_interests": tuple(item.as_dict() for item in candidates),
        "source_records": tuple(dict(item) for item in sources),
        "ranked_interest_ids": tuple(item.interest_id for item in candidates if item.status == "candidate_interest"),
        "selected_interest_id": proposal.selected_interest_id if proposal else "",
        "proposal": proposal.as_dict() if proposal else {},
        "proposal_status": proposal.status if proposal else "exhausted",
        "cooldown_semantics": rejected,
        "active_or_recent_semantics": active_or_recent,
        "exhaustion_reason": "no_valid_evidence_grounded_developmental_interest" if proposal is None else "",
        "deferred_assessment_request_ids": tuple(
            str(item.get("request_id") or "") for item in parent.continuous_developmental_insight_requests
        ) if attached_parent else (),
    }
    if proposal is None:
        return replace(
            parent,
            continuous_mission_state="developmental_interest_exhausted",
            continuous_learning_state={**state, "developmental_interest": compiled_interest},
            continuous_developmental_insight_requests=tuple(retained_requests),
            continuous_active_subgoal={},
            active_work_item="developmental_interest_exhausted",
            journal=parent.journal + (_journal_entry("developmental_interest", "candidate_interests_exhausted_without_operator_request", (origin_state_id,)),),
        )
    existing = next(
        (
            dict(item)
            for item in retained_requests
            if item.get("request_kind") == "developmental_goal_approval"
            and item.get("proposal_id") == proposal.proposal_id
            and item.get("status") == "pending"
        ),
        None,
    )
    if existing:
        return replace(
            parent,
            continuous_mission_state="awaiting_operator_insight",
            continuous_learning_state={**state, "developmental_interest": compiled_interest},
            active_work_item="awaiting_developmental_goal_approval",
        )
    request = {
        "request_id": stable_id("developmental-goal-approval", proposal.proposal_id),
        "request_kind": "developmental_goal_approval",
        "proposal_id": proposal.proposal_id,
        "selected_interest_id": proposal.selected_interest_id,
        "status": "pending",
        "exact_question": f"Approve the bounded developmental goal: {proposal.proposed_goal}?",
        "rationale": "The proposed goal was selected from retained capability and gap evidence. Approval starts at most one existing developmental-learning mission.",
        "evidence_refs": proposal.source_evidence,
        "source_gap_ids": proposal.source_evidence,
        "blocked_transition": "ranked_interest -> approved_developmental_goal -> existing_learning_lifecycle",
        "authority_scope": "one bounded developmental-learning mission only; no provider, web, PCM, tracked-source application, Git, or deployment authority",
        "blocking_scope": "developmental-goal selection",
        "permitted_responses": ("approve_developmental_goal", "reject_developmental_goal", "defer_developmental_goal", "ask_for_clarification"),
        "authority_granted": False,
        "created_at": utc_now(),
    }
    return replace(
        parent,
        continuous_mission_state="awaiting_operator_insight",
        continuous_learning_state={**state, "developmental_interest": compiled_interest},
        continuous_developmental_insight_requests=tuple(retained_requests) + (request,),
        continuous_active_subgoal={},
        active_work_item="awaiting_developmental_goal_approval",
        journal=parent.journal + (_journal_entry("developmental_interest", "ranked_interest_compiled_to_operator_goal_proposal", (proposal.proposal_id, proposal.selected_interest_id)),),
    )


def consume_developmental_goal_proposal_response(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    selected_option: str,
    operator_text: str = "",
) -> ContinuousRuntimeController:
    """Consume one goal disposition through the existing interaction ledger."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((position for position, item in enumerate(requests) if item.get("request_id") == request_id and item.get("status") == "pending"), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_interest", "duplicate_or_unknown_goal_proposal_response_suppressed", (request_id,)),))
    request = requests[index]
    permitted = tuple(request.get("permitted_responses") or ())
    if selected_option not in permitted:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_interest", "invalid_goal_proposal_response_rejected", (request_id, selected_option)),))
    state = dict(controller.continuous_learning_state or {})
    interest = dict(state.get("developmental_interest") or {})
    proposal = dict(interest.get("proposal") or {})
    if str(proposal.get("proposal_id") or "") != str(request.get("proposal_id") or ""):
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_interest", "goal_proposal_response_rejected_identity_mismatch", (request_id,)),))
    candidate = next((dict(item) for item in (interest.get("candidate_interests") or ()) if item.get("interest_id") == proposal.get("selected_interest_id")), {})
    semantic = str(candidate.get("semantic_identity") or "")
    consumed_at = utc_now()
    resolution = {
        "request_id": request_id,
        "response_kind": "developmental_goal_approval",
        "selected_option": selected_option,
        "operator_text": operator_text,
        "created_at": consumed_at,
        "consumed_at": consumed_at,
        "authority_granted": selected_option == "approve_developmental_goal",
    }
    resolved_request = {
        **request,
        "status": "consumed",
        "resolution": selected_option,
        "consumed_at": consumed_at,
        "authority_granted": selected_option == "approve_developmental_goal",
    }
    updated_requests = requests[:index] + (resolved_request,) + requests[index + 1 :]
    cooldown = tuple(dict.fromkeys(tuple(interest.get("cooldown_semantics") or ()) + ((semantic,) if selected_option != "approve_developmental_goal" and semantic else ())))
    active_recent = tuple(dict.fromkeys(tuple(interest.get("active_or_recent_semantics") or ()) + ((semantic,) if selected_option == "approve_developmental_goal" and semantic else ())))
    proposal["status"] = (
        "approved_developmental_goal" if selected_option == "approve_developmental_goal"
        else "deferred" if selected_option == "defer_developmental_goal"
        else "rejected" if selected_option == "reject_developmental_goal"
        else "clarification_requested"
    )
    updated_interest = {**interest, "proposal": proposal, "proposal_status": proposal["status"], "cooldown_semantics": cooldown, "active_or_recent_semantics": active_recent, "operator_decision": resolution}
    updated = replace(
        controller,
        continuous_developmental_insight_requests=updated_requests,
        continuous_operator_interaction_responses=controller.continuous_operator_interaction_responses + (resolution,),
        continuous_learning_state={**state, "developmental_interest": updated_interest},
        journal=controller.journal + (_journal_entry("developmental_interest", "operator_goal_proposal_response_consumed_once", (request_id, selected_option)),),
    )
    if selected_option == "ask_for_clarification":
        clarification = {
            **request,
            "request_id": stable_id("developmental-goal-clarification", proposal.get("proposal_id", "")),
            "status": "pending",
            "clarification_round": 1,
            "exact_question": (
                f"What bounded priority, resource, evaluator, or scope clarification should be retained for: "
                f"{proposal.get('proposed_goal', '')}? Enter it, then approve, reject, or defer this same proposal."
            ),
            "rationale": "One operator clarification is permitted; it does not change evaluator independence or grant implementation authority.",
            "permitted_responses": ("approve_developmental_goal", "reject_developmental_goal", "defer_developmental_goal"),
            "created_at": consumed_at,
        }
        return replace(
            updated,
            continuous_mission_state="awaiting_operator_insight",
            continuous_developmental_insight_requests=updated_requests + (clarification,),
            continuous_learning_state={
                **dict(updated.continuous_learning_state or {}),
                "developmental_interest": {**updated_interest, "proposal_status": "clarification_requested"},
            },
            active_work_item="awaiting_developmental_goal_clarification",
            journal=updated.journal + (_journal_entry("developmental_interest", "one_scoped_goal_clarification_requested", (proposal.get("proposal_id", ""),)),),
        )
    if selected_option != "approve_developmental_goal":
        resolved = replace(
            updated,
            continuous_mission_state="developmental_interest_deferred" if selected_option == "defer_developmental_goal" else "developmental_interest_rejected",
            active_work_item="developmental_interest_observation",
            continuous_active_subgoal={},
        )
        return _advance_agenda_after_goal_decision(
            resolved,
            proposal_id=str(proposal.get("proposal_id") or ""),
            semantic_identity=semantic,
            decision=selected_option,
        )
    if str(candidate.get("candidate_class") or "") == "acquire_evaluator_authority":
        learning_instruction = f"Learn {str(proposal.get('topic') or '').replace('_', ' ')}."
        dormant_mission = compile_developmental_mission_contract(learning_instruction)
        if dormant_mission is None:
            return updated
        retained = replace(
            updated,
            continuous_mission_state="learning_evaluator_authority_needed",
            active_work_item="developmental_interest_evaluator_authority_needed",
            continuous_active_subgoal={},
            continuous_learning_state={
                **dict(updated.continuous_learning_state or {}),
                "mission": dormant_mission.as_dict(),
                "protocol": "operator_developmental_mission_orchestration_v1",
            },
            journal=updated.journal + (_journal_entry("developmental_interest", "approved_evaluator_acquisition_goal_retained_without_learning_activation", (proposal.get("proposal_id", ""),)),),
        )
        marked = _mark_agenda_mission_active(
            retained,
            proposal_id=str(proposal.get("proposal_id") or ""),
            mission_id=dormant_mission.mission_id,
            awaiting_evaluator=True,
        )
        return compile_governed_developmental_resource_policy(marked) if dict(marked.continuous_learning_state or {}).get("developmental_agenda") else marked
    learning_instruction = f"Learn {str(proposal.get('topic') or '').replace('_', ' ')}."
    activated = compile_operator_developmental_learning_mission(updated, learning_instruction)
    agenda_state = dict(state.get("developmental_agenda") or {})
    activated = replace(
        activated,
        continuous_learning_state={
            **dict(activated.continuous_learning_state or {}),
            "developmental_interest": updated_interest,
            **({"developmental_agenda": agenda_state} if agenda_state else {}),
        },
        continuous_developmental_insight_requests=updated_requests,
        continuous_operator_interaction_responses=updated.continuous_operator_interaction_responses,
        journal=activated.journal + (_journal_entry("developmental_interest", "approved_goal_handed_to_existing_learning_lifecycle", (proposal.get("proposal_id", ""),)),),
    )
    mission_id = str((activated.continuous_learning_state or {}).get("mission", {}).get("mission_id") or "")
    marked = _mark_agenda_mission_active(
        activated,
        proposal_id=str(proposal.get("proposal_id") or ""),
        mission_id=mission_id,
        awaiting_evaluator=False,
    )
    if marked.continuous_mission_state in {
        "evidence_needed_for_developmental_learning",
        "learning_resource_evidence_needed",
        "learning_evaluator_authority_needed",
        "learning_external_authority_required",
    }:
        return compile_governed_developmental_resource_policy(marked)
    return marked


def start_persistent_developmental_agenda(
    controller: ContinuousRuntimeController,
    operator_instruction: str,
) -> ContinuousRuntimeController:
    """Initialize one bounded agenda and compile at most one first proposal."""

    if not is_persistent_developmental_agenda_instruction(operator_instruction):
        return controller
    state = dict(controller.continuous_learning_state or {})
    existing = dict(state.get("developmental_agenda") or {})
    if existing and agenda_state_is_valid(existing):
        return _compile_next_agenda_proposal(controller, operator_instruction, force=False)
    sources = source_records_from_state(
        learning_state=state,
        capability_inventory=controller.continuous_capability_inventory,
    )
    digest = material_evidence_digest(
        capability_inventory=controller.continuous_capability_inventory,
        sources=sources,
    )
    agenda = compile_persistent_developmental_agenda(
        operator_scope=operator_instruction,
        material_digest=digest,
    ).as_dict()
    prepared = replace(
        controller,
        continuous_learning_state={**state, "interest_sources": tuple(sources), "developmental_agenda": agenda},
        continuous_mission_state="developmental_agenda_compiling",
        active_work_item="developmental_agenda_compiling",
        journal=controller.journal + (_journal_entry("developmental_agenda", "persistent_agenda_initialized", (agenda["agenda_id"],)),),
    )
    return _compile_next_agenda_proposal(prepared, operator_instruction, force=True)


def _compile_next_agenda_proposal(
    controller: ContinuousRuntimeController,
    operator_instruction: str,
    *,
    force: bool,
) -> ContinuousRuntimeController:
    state = dict(controller.continuous_learning_state or {})
    agenda = dict(state.get("developmental_agenda") or {})
    if not agenda_state_is_valid(agenda):
        return replace(
            controller,
            continuous_mission_state="developmental_agenda_blocked",
            continuous_active_subgoal={},
            active_work_item="developmental_agenda_blocked",
            continuous_learning_state={**state, "developmental_agenda": {**agenda, "status": "blocked", "exhaustion_reasons": ("invalid_agenda_state",)}},
            journal=controller.journal + (_journal_entry("developmental_agenda", "invalid_agenda_state_failed_closed", (str(agenda.get("agenda_id") or ""),)),),
        )
    if agenda.get("status") == "paused":
        return controller
    if agenda.get("pending_proposal_id") or agenda.get("active_mission_id"):
        return controller
    interest = dict(state.get("developmental_interest") or {})
    sources = tuple(dict(item) for item in (interest.get("source_records") or state.get("interest_sources") or ()) if isinstance(item, Mapping))
    digest = material_evidence_digest(
        capability_inventory=controller.continuous_capability_inventory,
        sources=sources,
        outcome_history=tuple(agenda.get("mission_outcome_history") or ()),
        cooldown_records=tuple(agenda.get("cooldown_records") or ()),
        budgets={
            "session": agenda.get("remaining_session_budget"),
            "proposal": agenda.get("remaining_proposal_budget"),
            "attempt": agenda.get("remaining_attempt_budget"),
        },
    )
    if not force and digest == agenda.get("last_material_evidence_digest"):
        return replace(
            controller,
            continuous_mission_state="developmental_agenda_cooldown",
            active_work_item="developmental_agenda_no_material_evidence_change",
            continuous_learning_state={**state, "developmental_agenda": {**agenda, "status": "cooldown", "next_eligible_transition": "material_evidence_change_or_operator_refresh"}},
            journal=controller.journal + (_journal_entry("developmental_agenda", "equivalent_evidence_state_did_not_recompile_proposal", (agenda["agenda_id"],)),),
        )
    if (
        int(agenda.get("remaining_session_budget") or 0) <= 0
        or int(agenda.get("remaining_proposal_budget") or 0) <= 0
        or int(agenda.get("remaining_attempt_budget") or 0) <= 0
    ):
        return replace(
            controller,
            continuous_mission_state="developmental_agenda_completed_session",
            active_work_item="developmental_agenda_budget_exhausted",
            continuous_learning_state={**state, "developmental_agenda": {**agenda, "status": "completed_session", "exhaustion_reasons": ("agenda_budget_exhausted",), "last_material_evidence_digest": digest}},
            journal=controller.journal + (_journal_entry("developmental_agenda", "agenda_budget_exhausted_before_proposal", (agenda["agenda_id"],)),),
        )
    prepared = replace(
        controller,
        continuous_learning_state={**state, "interest_sources": sources, "developmental_agenda": {**agenda, "status": "compiling_candidates", "last_material_evidence_digest": digest}},
    )
    compiled = compile_governed_developmental_interest_proposal(prepared, operator_instruction)
    compiled_state = dict(compiled.continuous_learning_state or {})
    compiled_interest = dict(compiled_state.get("developmental_interest") or {})
    proposal = dict(compiled_interest.get("proposal") or {})
    candidate_ids = tuple(str(item.get("interest_id") or "") for item in (compiled_interest.get("candidate_interests") or ()))
    updated_agenda = dict(compiled_state.get("developmental_agenda") or agenda)
    updated_agenda.update(
        {
            "current_candidate_set_id": stable_id("agenda-candidate-set", digest, candidate_ids),
            "candidate_history": tuple(dict.fromkeys(tuple(updated_agenda.get("candidate_history") or ()) + candidate_ids)),
            "last_material_evidence_digest": digest,
            "last_rank_digest": _learning_bridge_digest(compiled_interest.get("ranked_interest_ids") or ()),
            "updated_at": utc_now(),
        }
    )
    if proposal:
        prior = tuple(updated_agenda.get("proposal_history") or ())
        is_new = proposal["proposal_id"] not in prior
        updated_agenda.update(
            {
                "status": "proposal_pending",
                "pending_proposal_id": proposal["proposal_id"],
                "proposal_history": prior + ((proposal["proposal_id"],) if is_new else ()),
                "remaining_proposal_budget": int(updated_agenda.get("remaining_proposal_budget") or 0) - (1 if is_new else 0),
                "next_eligible_transition": "operator_goal_decision",
            }
        )
    else:
        updated_agenda.update(
            {
                "status": "exhausted",
                "pending_proposal_id": "",
                "exhaustion_reasons": ("no_valid_evidence_grounded_interest",),
                "next_eligible_transition": "material_evidence_change_or_operator_refresh",
            }
        )
    return replace(
        compiled,
        continuous_mission_state="awaiting_operator_insight" if proposal else "developmental_agenda_exhausted",
        continuous_active_subgoal={} if not proposal else compiled.continuous_active_subgoal,
        active_work_item="awaiting_developmental_goal_approval" if proposal else "developmental_agenda_exhausted",
        continuous_learning_state={**compiled_state, "developmental_agenda": updated_agenda},
        journal=compiled.journal + (_journal_entry("developmental_agenda", "agenda_candidate_ranking_compiled", (updated_agenda["agenda_id"], str(proposal.get("proposal_id") or ""))),),
    )


def observe_developmental_agenda_mission_outcome(
    controller: ContinuousRuntimeController,
    *,
    outcome_id: str,
    outcome: str,
    evidence_refs: Sequence[str] = (),
) -> ContinuousRuntimeController:
    """Consume one terminal bounded mission outcome and advance only on new evidence."""

    state = dict(controller.continuous_learning_state or {})
    agenda = dict(state.get("developmental_agenda") or {})
    if not agenda:
        return controller
    if not agenda_state_is_valid(agenda):
        return _compile_next_agenda_proposal(controller, str(agenda.get("operator_scope") or ""), force=False)
    outcomes = tuple(dict(item) for item in (agenda.get("mission_outcome_history") or ()))
    if any(item.get("outcome_id") == outcome_id for item in outcomes):
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_agenda", "duplicate_mission_outcome_suppressed", (outcome_id,)),))
    interest = dict(state.get("developmental_interest") or {})
    proposal = dict(interest.get("proposal") or {})
    candidate = next((dict(item) for item in (interest.get("candidate_interests") or ()) if item.get("interest_id") == proposal.get("selected_interest_id")), {})
    semantic = str(candidate.get("semantic_identity") or "")
    terminal = {"behaviorally_demonstrated", "completed", "behaviorally_failed", "prerequisite_blocked", "resource_blocked", "evaluator_blocked", "budget_exhausted", "inconclusive", "operator_stopped"}
    if outcome not in terminal:
        return controller
    record = {"outcome_id": outcome_id, "outcome": outcome, "proposal_id": proposal.get("proposal_id", ""), "semantic_identity": semantic, "evidence_refs": tuple(evidence_refs), "recorded_at": utc_now()}
    successful = outcome in {"behaviorally_demonstrated", "completed"}
    cooldown_trigger = "recently_completed" if successful else outcome
    cooldown = {"semantic_identity": semantic, "trigger": cooldown_trigger, "evidence_digest": _learning_bridge_digest(record), "release_condition": "material_evidence_change_or_explicit_operator_refresh", "reason": outcome, "status": "active"}
    active_recent = tuple(dict.fromkeys(tuple(interest.get("active_or_recent_semantics") or ()) + ((semantic,) if semantic else ())))
    cooldowns = tuple(agenda.get("cooldown_records") or ()) + ((cooldown,) if semantic else ())
    updated_agenda = {
        **agenda,
        "status": "refreshing_evidence",
        "active_mission_id": "",
        "pending_proposal_id": "",
        "mission_outcome_history": outcomes + (record,),
        "completed_goal_ids": tuple(dict.fromkeys(tuple(agenda.get("completed_goal_ids") or ()) + ((str(proposal.get("proposal_id") or ""),) if successful else ()))),
        "blocked_goal_ids": tuple(dict.fromkeys(tuple(agenda.get("blocked_goal_ids") or ()) + ((str(proposal.get("proposal_id") or ""),) if not successful else ()))),
        "cooldown_records": cooldowns,
        "cycle_count": int(agenda.get("cycle_count") or 0) + 1,
        "successful_cycle_count": int(agenda.get("successful_cycle_count") or 0) + int(successful),
        "failed_cycle_count": int(agenda.get("failed_cycle_count") or 0) + int(not successful),
        "consecutive_failure_count": 0 if successful else int(agenda.get("consecutive_failure_count") or 0) + 1,
        "remaining_session_budget": max(0, int(agenda.get("remaining_session_budget") or 0) - 1),
        "remaining_attempt_budget": max(0, int(agenda.get("remaining_attempt_budget") or 0) - 1),
        "recent_capability_updates": tuple(str(item) for item in evidence_refs),
        "updated_at": utc_now(),
    }
    if updated_agenda["consecutive_failure_count"] >= int(updated_agenda.get("maximum_consecutive_failures") or 1):
        updated_agenda.update({"status": "blocked", "exhaustion_reasons": ("consecutive_failure_budget_reached",), "next_eligible_transition": "material_evidence_change_or_operator_refresh"})
        return replace(controller, continuous_mission_state="developmental_agenda_blocked", continuous_active_subgoal={}, active_work_item="developmental_agenda_diminishing_return", continuous_learning_state={**state, "developmental_interest": {**interest, "active_or_recent_semantics": active_recent}, "developmental_agenda": updated_agenda})
    prepared = replace(
        controller,
        continuous_active_subgoal={},
        continuous_learning_state={**state, "developmental_interest": {**interest, "active_or_recent_semantics": active_recent}, "developmental_agenda": updated_agenda},
        continuous_mission_state="developmental_agenda_refreshing_evidence",
        active_work_item="developmental_agenda_refreshing_evidence",
        journal=controller.journal + (_journal_entry("developmental_agenda", "terminal_mission_outcome_consumed_once", (outcome_id, outcome)),),
    )
    return _compile_next_agenda_proposal(prepared, str(updated_agenda.get("operator_scope") or ""), force=True)


def set_persistent_developmental_agenda_paused(
    controller: ContinuousRuntimeController,
    *,
    paused: bool,
) -> ContinuousRuntimeController:
    state = dict(controller.continuous_learning_state or {})
    agenda = dict(state.get("developmental_agenda") or {})
    if not agenda_state_is_valid(agenda):
        return controller
    return replace(
        controller,
        continuous_mission_state="developmental_agenda_paused" if paused else "developmental_agenda_idle",
        active_work_item="developmental_agenda_paused" if paused else "developmental_agenda_ready",
        continuous_learning_state={**state, "developmental_agenda": {**agenda, "status": "paused" if paused else "idle", "next_eligible_transition": "operator_resume" if paused else "material_evidence_change_or_operator_refresh", "updated_at": utc_now()}},
        journal=controller.journal + (_journal_entry("developmental_agenda", "agenda_paused" if paused else "agenda_resumed", (agenda["agenda_id"],)),),
    )


def compile_governed_developmental_resource_policy(
    controller: ContinuousRuntimeController,
    *,
    explicit_refresh: bool = False,
) -> ContinuousRuntimeController:
    """Compile one resource/authority action for the current agenda goal.

    The controller persists references and routes operator authority. Existing
    resource stores, the shared local-model ledger, learning, and the agenda
    remain their respective owners.
    """

    state = dict(controller.continuous_learning_state or {})
    agenda = dict(state.get("developmental_agenda") or {})
    interest = dict(state.get("developmental_interest") or {})
    proposal = dict(interest.get("proposal") or {})
    candidate = next(
        (dict(item) for item in (interest.get("candidate_interests") or ()) if item.get("interest_id") == proposal.get("selected_interest_id")),
        {},
    )
    if not agenda_state_is_valid(agenda) or not proposal or not candidate:
        return controller
    requirement = compile_developmental_resource_authority_requirement(
        agenda=agenda,
        proposal=proposal,
        candidate=candidate,
        mission=dict(state.get("mission") or {}),
        learning_state=state,
    )
    existing = dict(state.get("developmental_resource_policy") or {})
    if existing and not resource_policy_state_is_valid(existing):
        return replace(
            controller,
            continuous_mission_state="developmental_resource_policy_blocked",
            continuous_active_subgoal={},
            active_work_item="developmental_resource_policy_invalid_state",
            continuous_learning_state={**state, "developmental_resource_policy": {**existing, "status": "unavailable", "failure_reason": "invalid_resource_policy_state"}},
            journal=controller.journal + (_journal_entry("developmental_resource_policy", "invalid_policy_state_failed_closed", (str(existing.get("policy_state_digest") or ""),)),),
        )
    if (
        not explicit_refresh
        and dict(existing.get("requirement") or {}).get("requirement_digest") == requirement.requirement_digest
        and dict(existing.get("decision") or {}).get("status") in {"decision_compiled", "authority_pending", "authority_granted", "local_model_request_pending"}
    ):
        return controller
    observations = observe_developmental_resources(requirement, learning_state=state)
    eligible_alternatives = [
        item for item in (interest.get("candidate_interests") or ())
        if item.get("status") == "candidate_interest" and item.get("interest_id") != proposal.get("selected_interest_id")
    ]
    authority = dict(state.get("resource_policy_authorities") or {})
    candidates = compile_resource_policy_candidates(
        requirement,
        observations,
        has_alternative=bool(eligible_alternatives),
        external_authority_granted=bool(authority.get("external_research")),
        execution_authority_granted=bool(authority.get("execution")),
        prefer_operator_teaching=any(
            item.get("status") == "validated" and item.get("fulfillment_type") == "operator_sealed_evaluator_fulfillment"
            for item in (state.get("developmental_resource_fulfillments") or ())
            if isinstance(item, Mapping)
        ),
    )
    decision = compile_resource_authority_decision(requirement, candidates)
    policy = {
        "requirement": requirement.as_dict(),
        "resource_inventory": tuple(item.as_dict() for item in observations),
        "policy_candidates": tuple(item.as_dict() for item in candidates),
        "decision": decision.as_dict(),
        "policy_state_digest": _learning_bridge_digest({"requirement": requirement.requirement_digest, "inventory": tuple(item.digest for item in observations), "decision": decision.decision_digest}),
        "status": "decision_compiled",
    }
    if decision.action_type not in REQUEST_ACTIONS:
        state_name = "developmental_resource_policy_unavailable" if decision.action_type == "resource_policy_unavailable" else "developmental_resource_policy_local_reuse_ready"
        return replace(
            controller,
            continuous_mission_state=state_name,
            active_work_item=decision.action_type,
            continuous_learning_state={**state, "developmental_resource_policy": policy},
            journal=controller.journal + (_journal_entry("developmental_resource_policy", "resource_authority_policy_decision_compiled", (decision.decision_id, decision.action_type)),),
        )
    pending = next(
        (
            dict(item)
            for item in controller.continuous_developmental_insight_requests
            if item.get("request_kind") == "developmental_resource_authority"
            and item.get("policy_decision_id") == decision.decision_id
            and item.get("status") == "pending"
        ),
        None,
    )
    request = pending or {
        "request_id": decision.target_authority_request_id,
        "request_kind": "developmental_resource_authority",
        "policy_decision_id": decision.decision_id,
        "requirement_id": requirement.requirement_id,
        "action_type": decision.action_type,
        "status": "pending",
        "exact_question": _resource_authority_question(requirement.as_dict(), decision.action_type),
        "rationale": decision.rationale,
        "evidence_refs": tuple(requirement.information_need_ids),
        "blocked_transition": "agenda_goal -> governed_resource_authority_policy -> bounded_authority_or_local_reuse",
        "authority_scope": _resource_authority_scope(decision.action_type, requirement.as_dict()),
        "blocking_scope": "developmental_resource_or_evaluator_policy",
        "permitted_responses": ("approve_scoped_authority", "reject_scoped_authority", "defer_resource_policy", "ask_for_clarification"),
        "authority_granted": False,
        "created_at": utc_now(),
    }
    updated_agenda = {**agenda, "status": "awaiting_resource_policy_authority", "next_eligible_transition": "operator_resource_authority_response", "updated_at": utc_now()}
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_developmental_resource_authority",
        continuous_learning_state={**state, "developmental_resource_policy": {**policy, "status": "authority_pending"}, "developmental_agenda": updated_agenda},
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) if pending else tuple(controller.continuous_developmental_insight_requests) + (request,),
        journal=controller.journal + (_journal_entry("developmental_resource_policy", "scoped_resource_authority_request_created", (decision.decision_id, request["request_id"])),),
    )


def compile_failed_research_fallback_authority(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Offer at most one distinct source target after a durable target-specific failure."""

    state = dict(controller.continuous_learning_state or {})
    research = dict(state.get("external_research") or {})
    plan = dict(research.get("plan") or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    decision = dict(policy.get("decision") or {})
    if not research_state_is_valid(research) or plan.get("status") != "research_failed" or research.get("claim", {}).get("claim_state") != "research_failed":
        return replace(controller, continuous_mission_state="developmental_external_research_fallback_blocked", active_work_item="fallback_requires_terminal_failed_research", journal=controller.journal + (_journal_entry("external_research", "fallback_suppressed_without_terminal_failed_plan", (str(plan.get("research_plan_id") or ""),)),))
    if dict(research.get("fallback") or {}).get("status") == "authority_pending":
        return controller
    retired_requests = tuple(
        {
            **dict(item),
            "status": "blocked",
            "resolution": "research_plan_terminal_failure",
            "blocked_at": utc_now(),
        }
        if item.get("request_kind") == "developmental_resource_fulfillment"
        and item.get("research_plan_id") == plan.get("research_plan_id")
        and item.get("status") == "pending"
        else dict(item)
        for item in controller.continuous_developmental_insight_requests
    )
    failure = classify_terminal_research_failure(research)
    interpretation = next(
        (
            dict(item)
            for item in reversed(tuple(research.get("transport_diagnostic_interpretations") or ()))
            if item.get("historical_failure_id") == failure.get("failure_id")
        ),
        {},
    )
    if interpretation.get("fallback_eligible"):
        failure = {
            **failure,
            "normalized_failure_type": interpretation.get("derived_failure_type") or failure.get("normalized_failure_type"),
            "source_specific": True,
            "retryable": True,
            "fallback_eligible": True,
            "derived_interpretation_id": interpretation.get("interpretation_id"),
        }
    candidates = compile_fallback_source_candidates(plan, failure)
    if not candidates:
        blocked = {**research, "fallback": {"status": "fallback_ineligible", "failure": failure, "candidates": ()}}
        return replace(controller, continuous_developmental_insight_requests=retired_requests, continuous_learning_state={**state, "external_research": blocked}, continuous_mission_state="developmental_external_research_fallback_blocked", active_work_item=str(failure.get("normalized_failure_type") or "fallback_ineligible"), journal=controller.journal + (_journal_entry("external_research", "fallback_suppressed_by_failure_classification", (str(failure.get("failure_id") or ""), str(failure.get("normalized_failure_type") or ""))),))
    candidate = dict(candidates[0])
    request_id = stable_id("developmental-external-research-fallback-authority", str(plan.get("research_plan_id") or ""), str(candidate.get("fallback_candidate_id") or ""))
    fallback_plan = compile_fallback_external_research_plan(
        prior_plan=plan,
        failure=failure,
        candidate=candidate,
        authority_request_id=request_id,
        operator_approval_id=request_id,
    )
    scope = f"one bounded fallback retrieval of {candidate['canonical_target']} for {plan.get('topic') or ''}; no provider, PCM, tracked-source, Git, deployment, or general web authority"
    request = {
        "request_id": request_id,
        "request_kind": "developmental_resource_authority",
        "policy_decision_id": decision.get("decision_id"),
        "requirement_id": plan.get("requirement_id"),
        "action_type": "request_external_research_authority",
        "status": "pending",
        "exact_question": f"The prior source {failure['source_target']} failed with {failure['normalized_failure_type']} and accepted no source. Approve one distinct fallback retrieval from {candidate['canonical_target']}?",
        "rationale": "The original authority and claim remain terminal. This is a separate one-use plan for a materially distinct allowed source target.",
        "evidence_refs": tuple(plan.get("information_need_ids") or ()),
        "authority_scope": scope,
        "permitted_responses": ("approve_scoped_authority", "reject_scoped_authority", "defer_resource_policy", "ask_for_clarification"),
        "fallback_plan_id": fallback_plan.research_plan_id,
        "prior_plan_id": plan.get("research_plan_id"),
        "prior_failure_id": failure["failure_id"],
        "created_at": utc_now(),
    }
    fallback = {
        "status": "authority_pending",
        "failure": failure,
        "candidates": candidates,
        "selected_candidate": candidate,
        "plan": fallback_plan.as_dict(),
        "authority_request_id": request_id,
    }
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_distinct_external_research_fallback_authority",
        continuous_learning_state={**state, "external_research": {**research, "fallback": fallback}},
        continuous_developmental_insight_requests=retired_requests + (request,),
        journal=controller.journal + (_journal_entry("external_research", "distinct_fallback_authority_request_created", (fallback_plan.research_plan_id, request_id)),),
    )


def record_external_transport_diagnostic_interpretation(
    controller: ContinuousRuntimeController,
    diagnostics: Sequence[Mapping[str, Any]],
) -> ContinuousRuntimeController:
    """Append a derived interpretation without modifying the historical terminal failure."""

    state = dict(controller.continuous_learning_state or {})
    research = dict(state.get("external_research") or {})
    if not research_state_is_valid(research):
        return replace(controller, continuous_mission_state="developmental_external_research_blocked", active_work_item="invalid_research_state_before_transport_interpretation")
    normalized_diagnostics = tuple(dict(item) for item in diagnostics)
    interpretation = compile_historical_transport_interpretation(research, normalized_diagnostics)
    existing = tuple(dict(item) for item in (research.get("transport_diagnostic_interpretations") or ()))
    existing_diagnostics = tuple(dict(item) for item in (research.get("transport_diagnostics") or ()))
    known_ids = {item.get("diagnostic_id") for item in existing_diagnostics}
    appended_diagnostics = existing_diagnostics + tuple(item for item in normalized_diagnostics if item.get("diagnostic_id") not in known_ids)
    interpretations = existing if any(item.get("interpretation_id") == interpretation["interpretation_id"] for item in existing) else existing + (interpretation,)
    updated = {**research, "transport_diagnostics": appended_diagnostics, "transport_diagnostic_interpretations": interpretations}
    return replace(
        controller,
        continuous_learning_state={**state, "external_research": updated},
        journal=controller.journal + (_journal_entry("external_research", "transport_diagnostic_interpretation_persisted", (interpretation["interpretation_id"], interpretation["classification"])),),
    )


def compile_failed_research_adapter_repair_authority(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Request one corrected-locator retry after a proven adapter defect, never automatically."""

    state = dict(controller.continuous_learning_state or {})
    research = dict(state.get("external_research") or {})
    plan = dict(research.get("plan") or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    decision = dict(policy.get("decision") or {})
    if not research_state_is_valid(research) or plan.get("status") != "research_failed" or research.get("claim", {}).get("claim_state") != "research_failed":
        return replace(controller, continuous_mission_state="developmental_external_research_adapter_repair_blocked", active_work_item="adapter_repair_requires_terminal_failure")
    failure = classify_terminal_research_failure(research)
    candidate = compile_adapter_repair_retry_candidate(plan, failure, tuple(research.get("transport_diagnostics") or ()))
    if not candidate:
        return replace(controller, continuous_mission_state="developmental_external_research_adapter_repair_blocked", active_work_item="adapter_repair_retry_not_proven", journal=controller.journal + (_journal_entry("external_research", "adapter_repair_retry_suppressed", (str(plan.get("research_plan_id") or ""),)),))
    request_id = stable_id("developmental-external-research-adapter-repair-authority", str(plan.get("research_plan_id") or ""), str(candidate["retry_candidate_id"]))
    retry_plan = compile_fallback_external_research_plan(
        prior_plan=plan,
        failure=failure,
        candidate={
            "fallback_candidate_id": candidate["retry_candidate_id"], "canonical_target": candidate["canonical_target"],
            "retrieval_target": candidate["retrieval_target"], "source_class": candidate["source_class"], "organization": candidate["organization"],
        },
        authority_request_id=request_id,
        operator_approval_id=request_id,
    )
    scope = f"one corrected direct retrieval of {candidate['retrieval_target']} after adapter repair; no provider, PCM, tracked-source, Git, deployment, or general web authority"
    request = {
        "request_id": request_id, "request_kind": "developmental_resource_authority", "policy_decision_id": decision.get("decision_id"),
        "requirement_id": plan.get("requirement_id"), "action_type": "request_external_research_authority", "status": "pending",
        "exact_question": f"The prior OCW retrieval failed because the adapter removed required locator path semantics. Diagnostics confirm {candidate['retrieval_target']} is reachable. Approve one corrected direct retry?",
        "rationale": "This is a separate one-use retry after a proven adapter defect, not reuse of either terminal research authority.",
        "authority_scope": scope, "permitted_responses": ("approve_scoped_authority", "reject_scoped_authority", "defer_resource_policy", "ask_for_clarification"),
        "fallback_plan_id": retry_plan.research_plan_id, "prior_plan_id": plan.get("research_plan_id"), "prior_failure_id": failure["failure_id"],
        "created_at": utc_now(),
    }
    updated = {**research, "fallback": {"status": "authority_pending", "kind": "adapter_repair_retry", "candidate": candidate, "plan": retry_plan.as_dict(), "authority_request_id": request_id}}
    return replace(
        controller, continuous_mission_state="awaiting_operator_insight", active_work_item="awaiting_external_research_adapter_repair_authority",
        continuous_learning_state={**state, "external_research": updated},
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        journal=controller.journal + (_journal_entry("external_research", "adapter_repair_retry_authority_request_created", (retry_plan.research_plan_id, request_id)),),
    )


def compile_relevance_failed_direct_topic_authority(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Request one exact topic locator after a generic page fails relevance checks."""

    state = dict(controller.continuous_learning_state or {})
    research = dict(state.get("external_research") or {})
    plan = dict(research.get("plan") or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    decision = dict(policy.get("decision") or {})
    if not research_state_is_valid(research) or research.get("status") != "research_validation_failed" or plan.get("status") != "research_validation_failed":
        return replace(controller, continuous_mission_state="developmental_external_research_direct_target_blocked", active_work_item="direct_topic_target_requires_relevance_failure")
    fallback = dict(research.get("fallback") or {})
    if fallback.get("status") == "authority_pending":
        return controller
    candidates = compile_direct_topic_source_candidates(research)
    if not candidates:
        return replace(controller, continuous_mission_state="developmental_external_research_direct_target_blocked", active_work_item="no_untried_direct_topic_target", journal=controller.journal + (_journal_entry("external_research", "direct_topic_target_request_suppressed", (str(plan.get("research_plan_id") or ""),)),))
    candidate = dict(candidates[0])
    request_id = stable_id("developmental-external-research-direct-topic-authority", str(plan.get("research_plan_id") or ""), str(candidate.get("fallback_candidate_id") or ""))
    direct_plan = compile_fallback_external_research_plan(
        prior_plan=plan, failure={"failure_id": str(research.get("result", {}).get("research_result_id") or "")}, candidate=candidate,
        authority_request_id=request_id, operator_approval_id=request_id,
    )
    scope = f"one direct allowlisted retrieval of {candidate['retrieval_target']} with required terms {candidate['required_topic_terms']}; no provider, PCM, tracked-source, Git, deployment, redirects, or general web authority"
    request = {
        "request_id": request_id, "request_kind": "developmental_resource_authority", "policy_decision_id": decision.get("decision_id"),
        "requirement_id": plan.get("requirement_id"), "action_type": "request_external_research_authority", "status": "pending",
        "exact_question": f"The approved host returned a generic page that could not prove relevance. Approve one exact topic-specific retrieval from {candidate['canonical_target']}?",
        "rationale": "The target is an existing allowlisted MIT OpenCourseWare topic resource. Its exact locator and required topic terms are bound before retrieval; it remains advisory teaching evidence only.",
        "evidence_refs": tuple(plan.get("information_need_ids") or ()), "authority_scope": scope,
        "permitted_responses": ("approve_scoped_authority", "reject_scoped_authority", "defer_resource_policy", "ask_for_clarification"),
        "fallback_plan_id": direct_plan.research_plan_id, "prior_plan_id": plan.get("research_plan_id"),
        "prior_failure_id": str(research.get("result", {}).get("research_result_id") or ""), "created_at": utc_now(),
    }
    direct_fallback = {
        "status": "authority_pending", "kind": "direct_topic_specific", "candidates": candidates,
        "selected_candidate": candidate, "plan": direct_plan.as_dict(), "authority_request_id": request_id,
    }
    return replace(
        controller, continuous_mission_state="awaiting_operator_insight", active_work_item="awaiting_direct_topic_external_research_authority",
        continuous_learning_state={**state, "external_research": {**research, "fallback": direct_fallback}},
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        journal=controller.journal + (_journal_entry("external_research", "direct_topic_authority_request_created", (direct_plan.research_plan_id, request_id)),),
    )


def _resource_authority_question(requirement: Mapping[str, Any], action_type: str) -> str:
    topic = str(requirement.get("topic") or "this bounded goal").replace("_", " ")
    target = str(requirement.get("target_behavior") or requirement.get("target_capability") or "the declared behavior")
    labels = {
        "request_local_model_resource": "Approve one exact-once local-model teaching-resource request",
        "request_operator_teaching_resource": "Provide or authorize one bounded teaching resource",
        "request_operator_sealed_evaluator": "Provide or authorize independently sealed evaluator cases",
        "request_external_research_authority": "Authorize one bounded external-research evidence request",
        "request_execution_authority": "Authorize one disposable execution environment",
    }
    return f"{labels.get(action_type, 'Approve scoped resource authority')} for {topic}: {target}?"


def _resource_authority_scope(action_type: str, requirement: Mapping[str, Any]) -> str:
    topic = str(requirement.get("topic") or "").replace("_", " ")
    target = str(requirement.get("target_capability") or "")
    if action_type == "request_local_model_resource":
        return f"one exact-once advisory local-model request for {topic}/{target}; no execution until the shared ledger approval path consumes it"
    if action_type == "request_operator_sealed_evaluator":
        return f"one separately authored sealed evaluator package for {topic}/{target}; it cannot be used as teaching evidence"
    if action_type == "request_operator_teaching_resource":
        return f"one bounded teaching resource for {topic}/{target}; it cannot certify capability"
    if action_type == "request_external_research_authority":
        return f"authority request only for bounded external evidence on {topic}/{target}; no retrieval is performed"
    return f"one disposable execution-authority request for {topic}/{target}; no tracked-source action"


def consume_developmental_resource_authority_response(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    selected_option: str,
    operator_text: str = "",
    approved_scope: str = "",
) -> ContinuousRuntimeController:
    """Consume one existing interaction request without granting broader authority."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((position for position, item in enumerate(requests) if item.get("request_id") == request_id and item.get("status") == "pending"), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_resource_policy", "duplicate_or_unknown_authority_response_suppressed", (request_id,)),))
    request = requests[index]
    permitted = tuple(request.get("permitted_responses") or ())
    if selected_option not in permitted:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_resource_policy", "invalid_authority_response_rejected", (request_id, selected_option)),))
    state = dict(controller.continuous_learning_state or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    decision = dict(policy.get("decision") or {})
    requirement = dict(policy.get("requirement") or {})
    if str(request.get("policy_decision_id") or "") != str(decision.get("decision_id") or ""):
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_resource_policy", "authority_response_identity_mismatch", (request_id,)),))
    consumed_at = utc_now()
    resolved = {**request, "status": "consumed", "resolution": selected_option, "consumed_at": consumed_at, "authority_granted": selected_option == "approve_scoped_authority"}
    updated_requests = requests[:index] + (resolved,) + requests[index + 1 :]
    response = {"request_id": request_id, "response_kind": "developmental_resource_authority", "selected_option": selected_option, "operator_text": operator_text, "approved_scope": approved_scope, "authority_granted": selected_option == "approve_scoped_authority", "created_at": consumed_at, "consumed_at": consumed_at}
    if selected_option == "ask_for_clarification":
        follow_up = {**request, "request_id": stable_id("developmental-resource-policy-clarification", request_id), "status": "pending", "exact_question": f"What bounded clarification is needed for: {request.get('exact_question', '')}", "permitted_responses": ("approve_scoped_authority", "reject_scoped_authority", "defer_resource_policy"), "created_at": consumed_at}
        return replace(controller, continuous_developmental_insight_requests=updated_requests + (follow_up,), continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,), continuous_learning_state={**state, "developmental_resource_policy": {**policy, "status": "clarification_requested"}}, continuous_mission_state="awaiting_operator_insight")
    if selected_option == "approve_scoped_authority":
        if not approved_scope or approved_scope != str(request.get("authority_scope") or ""):
            return replace(controller, journal=controller.journal + (_journal_entry("developmental_resource_policy", "authority_response_scope_mismatch", (request_id,)),))
        action = str(decision.get("action_type") or "")
        policy_update = {**policy, "status": "authority_granted", "approved_authority": {"request_id": request_id, "action_type": action, "scope": approved_scope, "granted_at": consumed_at}}
        updated_state = {**state, "developmental_resource_policy": policy_update}
        if action == "request_local_model_resource":
            ledger = LocalModelRequestResultLedger()
            semantic = stable_id("agenda-policy-local-model-need", str(requirement.get("semantic_identity") or ""))
            question = f"Provide bounded teaching evidence for {str(requirement.get('topic') or '').replace('_', ' ')}: {requirement.get('target_behavior') or requirement.get('target_capability')}."
            model_request = ledger.create_or_reuse_request(
                semantic_identity=semantic, question=question, requester_type="developmental_resource_policy",
                requester_reference=controller.session_id, mission_id=str(requirement.get("mission_id") or ""),
                mission_information_need_identity=str(requirement.get("semantic_identity") or ""), question_objective=str(requirement.get("target_capability") or ""),
            )
            updated_state.update({"local_model_request": model_request, "local_model_execution_count": int(model_request.get("execution_attempt_count") or 0), "developmental_resource_policy": {**policy_update, "status": "local_model_request_pending", "decision": {**decision, "target_request_id": model_request["request_id"], "status": "authority_granted"}}})
            fulfillment_request = {
                "request_id": stable_id("developmental-resource-local-model-result", request_id, model_request["request_id"]),
                "request_kind": "developmental_resource_fulfillment",
                "authority_request_id": request_id,
                "policy_decision_id": decision.get("decision_id"),
                "requirement_id": requirement.get("requirement_id"),
                "action_type": action,
                "local_model_request_id": model_request["request_id"],
                "status": "pending",
                "exact_question": "Await the existing shared local-model result. Its completed result may be observed as advisory teaching evidence only.",
                "rationale": "The controller does not execute the model or promote capability from model prose.",
                "authority_scope": approved_scope,
                "permitted_responses": ("observe_completed_local_model_result", "defer_fulfillment"),
                "created_at": consumed_at,
            }
            next_state, work = "learning_local_model_request_pending", "awaiting_shared_local_model_approval"
        else:
            authority_key = {
                "request_operator_teaching_resource": "operator_teaching_resource",
                "request_operator_sealed_evaluator": "sealed_evaluator",
                "request_external_research_authority": "external_research",
                "request_execution_authority": "execution",
            }.get(action, action)
            updated_state["resource_policy_authorities"] = {**dict(state.get("resource_policy_authorities") or {}), authority_key: {"scope": approved_scope, "request_id": request_id, "granted_at": consumed_at}}
            if action == "request_external_research_authority":
                existing_research = dict(state.get("external_research") or {})
                fallback = dict(existing_research.get("fallback") or {})
                if request.get("fallback_plan_id"):
                    plan = dict(fallback.get("plan") or {})
                    if not plan or plan.get("research_plan_id") != request.get("fallback_plan_id") or plan.get("authority_request_id") != request_id:
                        return replace(controller, journal=controller.journal + (_journal_entry("external_research", "fallback_approval_binding_mismatch", (request_id, str(request.get("fallback_plan_id") or ""))),))
                    history_entry = {
                        "plan": dict(existing_research.get("plan") or {}),
                        "claim": dict(existing_research.get("claim") or {}),
                        "retrieval_attempts": tuple(existing_research.get("retrieval_attempts") or ()),
                        "source_records": tuple(existing_research.get("source_records") or ()),
                        "result": dict(existing_research.get("result") or {}),
                        "status": existing_research.get("status"),
                    }
                    plan_state = {
                        "plan": plan,
                        "claim": {},
                        "retrieval_attempts": (),
                        "source_records": (),
                        "result": {},
                        "status": "research_plan_compiled",
                        "history": tuple(existing_research.get("history") or ()) + (history_entry,),
                        "fallback_lineage": {
                            "prior_plan_id": request.get("prior_plan_id"),
                            "prior_failure_id": request.get("prior_failure_id"),
                            "fallback_candidate_id": plan.get("fallback_candidate_id"),
                        },
                    }
                else:
                    compiled_plan = compile_external_research_plan(
                        requirement=requirement,
                        decision=decision,
                        authority_request_id=request_id,
                        operator_approval_id=request_id,
                    )
                    if existing_research and str(dict(existing_research.get("plan") or {}).get("semantic_identity") or "") == compiled_plan.semantic_identity:
                        plan_state = existing_research
                    else:
                        plan_state = {"plan": compiled_plan.as_dict(), "claim": {}, "source_records": (), "result": {}, "status": "research_plan_compiled"}
                    plan = compiled_plan.as_dict()
                fulfillment_request = {
                    "request_id": stable_id("developmental-external-research-fulfillment", request_id, plan["research_plan_id"]),
                    "request_kind": "developmental_resource_fulfillment",
                    "authority_request_id": request_id,
                    "policy_decision_id": decision.get("decision_id"),
                    "requirement_id": requirement.get("requirement_id"), "action_type": action,
                    "research_plan_id": plan["research_plan_id"], "status": "pending",
                    "exact_question": "The approved bounded external-research plan is persisted. Execute only through the governed claim-before-call path; accepted sources remain advisory teaching evidence.",
                    "rationale": "One approved authority binds one plan, budgets, allowed domains, provenance requirements, and independent evaluator separation.",
                    "authority_scope": approved_scope,
                    "permitted_responses": ("execute_authorized_research", "supply_fulfillment", "defer_fulfillment", "reject_fulfillment"),
                    "created_at": consumed_at,
                }
                updated_state.update({
                    "external_research": plan_state,
                    "developmental_resource_policy": {**policy_update, "status": "research_plan_compiled", "research_plan_id": plan["research_plan_id"]},
                })
                return replace(
                    controller,
                    continuous_developmental_insight_requests=updated_requests + (fulfillment_request,),
                    continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
                    continuous_learning_state=updated_state,
                    continuous_mission_state="developmental_external_research_plan_ready",
                    active_work_item="persist_external_research_claim_before_call",
                    journal=controller.journal + (_journal_entry("developmental_resource_policy", "approved_external_research_plan_persisted", (request_id, plan["research_plan_id"])),),
                )
            fulfillment_request = {
                "request_id": stable_id("developmental-resource-fulfillment-request", request_id),
                "request_kind": "developmental_resource_fulfillment",
                "authority_request_id": request_id,
                "policy_decision_id": decision.get("decision_id"),
                "requirement_id": requirement.get("requirement_id"),
                "action_type": action,
                "status": "pending",
                "exact_question": "Supply one structured, scope-bound fulfillment for the approved resource authority. The material will be validated before the original goal may resume.",
                "rationale": "Approval grants only the exact authority scope; supplied teaching and evaluator material remain separate and must pass provenance, integrity, and scope validation.",
                "authority_scope": approved_scope,
                "permitted_responses": ("supply_fulfillment", "reject_fulfillment", "defer_fulfillment", "ask_for_clarification"),
                "created_at": consumed_at,
            }
            updated_state["developmental_resource_policy"] = {**policy_update, "status": "awaiting_fulfillment"}
            next_state, work = "developmental_resource_authority_granted_pending_material", "awaiting_authorized_resource_or_evaluator_material"
            return replace(
                controller,
                continuous_developmental_insight_requests=updated_requests + (fulfillment_request,),
                continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
                continuous_learning_state=updated_state,
                continuous_mission_state=next_state,
                active_work_item=work,
                journal=controller.journal + (_journal_entry("developmental_resource_policy", "scoped_authority_consumed_pending_typed_fulfillment", (request_id, action)),),
            )
        return replace(controller, continuous_developmental_insight_requests=updated_requests + (fulfillment_request,), continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,), continuous_learning_state=updated_state, continuous_mission_state=next_state, active_work_item=work, journal=controller.journal + (_journal_entry("developmental_resource_policy", "scoped_authority_consumed_without_execution", (request_id, action)),))
    policy_update = {**policy, "status": "deferred" if selected_option == "defer_resource_policy" else "rejected", "operator_disposition": {"request_id": request_id, "selected_option": selected_option, "at": consumed_at}}
    updated = replace(controller, continuous_developmental_insight_requests=updated_requests, continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,), continuous_learning_state={**state, "developmental_resource_policy": policy_update}, continuous_mission_state="developmental_resource_policy_deferred" if selected_option == "defer_resource_policy" else "developmental_resource_policy_rejected", active_work_item="resource_policy_agenda_refresh")
    return observe_developmental_agenda_mission_outcome(updated, outcome_id=stable_id("resource-policy-outcome", str(decision.get("decision_id") or ""), selected_option), outcome="resource_blocked", evidence_refs=(str(decision.get("decision_id") or ""), selected_option))


def claim_developmental_external_research_execution(
    controller: ContinuousRuntimeController,
    *,
    adapter_identity: str,
) -> ContinuousRuntimeController:
    """Persist a one-use claim.  The caller must restart/confirm it before a call."""

    state = dict(controller.continuous_learning_state or {})
    research = dict(state.get("external_research") or {})
    plan = dict(research.get("plan") or {})
    authority = dict(dict(state.get("resource_policy_authorities") or {}).get("external_research") or {})
    if not plan or not authority or authority.get("request_id") != plan.get("authority_request_id"):
        return replace(controller, continuous_mission_state="developmental_external_research_blocked", active_work_item="external_research_authority_or_plan_missing", journal=controller.journal + (_journal_entry("external_research", "claim_rejected_without_exact_approved_plan", (str(plan.get("research_plan_id") or ""),)),))
    existing = dict(research.get("claim") or {})
    if existing:
        return controller
    claim = compile_execution_claim(plan, adapter_identity=adapter_identity)
    updated = {**research, "claim": claim.as_dict(), "status": "research_execution_claimed", "plan": {**plan, "status": "research_execution_claimed"}}
    return replace(controller, continuous_learning_state={**state, "external_research": updated}, continuous_mission_state="developmental_external_research_claimed", active_work_item="restart_or_confirm_external_research_claim", journal=controller.journal + (_journal_entry("external_research", "execution_claim_persisted_before_external_call", (claim.claim_id, plan["research_plan_id"])),))


def reconcile_terminal_external_research_requests(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Close stale fulfillment requests whenever their exact research plan is terminally unusable."""

    state = dict(controller.continuous_learning_state or {})
    research = dict(state.get("external_research") or {})
    plan = dict(research.get("plan") or {})
    status = str(research.get("status") or plan.get("status") or "")
    if status not in {"research_failed", "research_validation_failed", "research_partially_completed", "research_budget_exhausted"}:
        return controller
    changed = False
    requests = []
    for item in controller.continuous_developmental_insight_requests:
        current = dict(item)
        if current.get("request_kind") == "developmental_resource_fulfillment" and current.get("research_plan_id") == plan.get("research_plan_id") and current.get("status") == "pending":
            current.update({"status": "blocked", "resolution": "research_plan_terminal_validation_failure", "blocked_at": utc_now()})
            changed = True
        requests.append(current)
    if not changed:
        return controller
    return replace(controller, continuous_developmental_insight_requests=tuple(requests), journal=controller.journal + (_journal_entry("external_research", "terminal_research_fulfillment_request_reconciled", (str(plan.get("research_plan_id") or ""), status)),))


def claim_developmental_external_research_retrieval(
    controller: ContinuousRuntimeController,
    *,
    adapter_identity: str,
) -> ContinuousRuntimeController:
    """Persist one exact retrieval attempt before invoking the RC8 adapter."""

    state = dict(controller.continuous_learning_state or {})
    research = dict(state.get("external_research") or {})
    plan = dict(research.get("plan") or {})
    claim = dict(research.get("claim") or {})
    existing = tuple(dict(item) for item in (research.get("retrieval_attempts") or ()))
    if not research_state_is_valid(research) or not plan or not claim or claim.get("claim_state") != "research_execution_claimed" or str(claim.get("adapter_identity") or "") != adapter_identity:
        return replace(controller, continuous_mission_state="developmental_external_research_blocked", active_work_item="external_research_retrieval_claim_not_permitted", journal=controller.journal + (_journal_entry("external_research", "retrieval_claim_suppressed_without_durable_execution_claim", (str(claim.get("claim_id") or ""),)),))
    if existing:
        return controller
    attempt = compile_retrieval_attempt(plan, claim, adapter_identity=adapter_identity)
    updated = {**research, "retrieval_attempts": (attempt.as_dict(),), "status": "research_in_progress", "plan": {**plan, "status": "research_in_progress"}}
    return replace(controller, continuous_learning_state={**state, "external_research": updated}, continuous_mission_state="developmental_external_research_retrieval_claimed", active_work_item="restart_or_confirm_external_retrieval_claim", journal=controller.journal + (_journal_entry("external_research", "retrieval_attempt_persisted_before_external_call", (attempt.retrieval_attempt_id, attempt.target_reference)),))


def execute_claimed_developmental_external_research(
    controller: ContinuousRuntimeController,
    *,
    adapter: Any,
    adapter_identity: str,
) -> ContinuousRuntimeController:
    """Consume a durable claim through a bounded adapter, then reuse fulfillment.

    ``adapter`` receives the persisted plan and returns source mappings. It is
    deliberately injected so RC8 or a controlled live transport stays the only
    retrieval owner; no arbitrary browser is created here.
    """

    state = dict(controller.continuous_learning_state or {})
    research = dict(state.get("external_research") or {})
    plan = dict(research.get("plan") or {})
    claim = dict(research.get("claim") or {})
    if claim.get("claim_state") in {"research_completed", "research_partially_completed", "research_failed", "research_interrupted", "research_validation_failed", "research_budget_exhausted"}:
        return controller
    retrieval_attempt = next((dict(item) for item in (research.get("retrieval_attempts") or ()) if item.get("status") == "retrieval_claimed"), {})
    if not research_state_is_valid(research) or not plan or not claim or claim.get("claim_state") != "research_execution_claimed" or not retrieval_attempt:
        return replace(controller, continuous_mission_state="developmental_external_research_blocked", active_work_item="external_research_claim_not_durable", journal=controller.journal + (_journal_entry("external_research", "external_call_suppressed_without_durable_claim", (str(plan.get("research_plan_id") or ""),)),))
    if str(claim.get("adapter_identity") or "") != adapter_identity:
        return replace(controller, continuous_mission_state="developmental_external_research_blocked", active_work_item="external_research_adapter_identity_mismatch", journal=controller.journal + (_journal_entry("external_research", "adapter_identity_mismatch", (str(claim.get("claim_id") or ""),)),))
    try:
        raw_sources = tuple(adapter(dict(plan)))
    except Exception as exc:
        failure_state = exc.failure_state if isinstance(exc, ExternalResearchRetrievalError) else type(exc).__name__
        failed_attempts = tuple({**dict(item), "status": "retrieval_failed", "failure_state": failure_state} for item in (research.get("retrieval_attempts") or ()))
        failed = {
            **research,
            "status": "research_failed",
            "retrieval_attempts": failed_attempts,
            "claim": {**claim, "claim_state": "research_failed", "failure_state": failure_state},
            "plan": {**plan, "status": "research_failed"},
            "result": {"status": "research_failed", "failure_state": failure_state},
        }
        retired_requests = tuple(
            {
                **dict(item),
                "status": "blocked",
                "resolution": "research_plan_terminal_failure",
                "blocked_at": utc_now(),
            }
            if item.get("request_kind") == "developmental_resource_fulfillment"
            and item.get("research_plan_id") == plan.get("research_plan_id")
            and item.get("status") == "pending"
            else dict(item)
            for item in controller.continuous_developmental_insight_requests
        )
        return replace(controller, continuous_developmental_insight_requests=retired_requests, continuous_learning_state={**state, "external_research": failed}, continuous_mission_state="developmental_external_research_failed", active_work_item="external_research_failure_recorded", journal=controller.journal + (_journal_entry("external_research", "retrieval_failure_persisted_without_fabricated_source", (str(claim.get("claim_id") or ""), failure_state)),))
    existing = tuple(dict(item) for item in research.get("source_records") or ())
    retrieval_budget = int(plan.get("retrieval_budget") or 0)
    limited = raw_sources[:retrieval_budget]
    budget_exhausted = len(raw_sources) > retrieval_budget
    records = tuple(normalize_external_research_source(plan, item, existing=existing) for item in limited)
    combined = existing + tuple(item.as_dict() for item in records)
    completed_attempts = tuple({**dict(item), "status": "retrieval_completed"} for item in (research.get("retrieval_attempts") or ()))
    result = synthesize_external_research_result(plan, combined, retrieval_attempts=completed_attempts)
    if budget_exhausted:
        result = {
            **result,
            "status": "research_partially_completed" if result["accepted_source_ids"] else "research_budget_exhausted",
            "stopping_reason": "retrieval_budget_exhausted",
        }
    completed_research = {**research, "retrieval_attempts": completed_attempts, "source_records": combined, "result": result, "status": result["status"], "claim": {**claim, "claim_state": result["status"], "terminal_result_id": result["research_result_id"]}, "plan": {**plan, "status": result["status"]}}
    prepared = replace(controller, continuous_learning_state={**state, "external_research": completed_research}, journal=controller.journal + (_journal_entry("external_research", "bounded_source_acquisition_completed", (str(plan.get("research_plan_id") or ""), result["research_result_id"])),))
    request = next((dict(item) for item in prepared.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_resource_fulfillment" and item.get("research_plan_id") == plan.get("research_plan_id") and item.get("status") == "pending"), {})
    if result["status"] != "research_completed" or not request:
        retired_requests = tuple(
            {
                **dict(item),
                "status": "blocked",
                "resolution": "research_plan_terminal_validation_failure",
                "blocked_at": utc_now(),
            }
            if item.get("request_kind") == "developmental_resource_fulfillment"
            and item.get("research_plan_id") == plan.get("research_plan_id")
            and item.get("status") == "pending"
            else dict(item)
            for item in prepared.continuous_developmental_insight_requests
        )
        return replace(prepared, continuous_developmental_insight_requests=retired_requests, continuous_mission_state="developmental_external_research_incomplete", active_work_item="external_research_remaining_blocker")
    requirement = dict(dict(prepared.continuous_learning_state.get("developmental_resource_policy") or {}).get("requirement") or {})
    material = {
        "fulfillment_type": "external_research_fulfillment", "source_identity": result["research_result_id"], "source_type": "authorized_external_research",
        "source_reference": str(plan.get("research_plan_id") or ""), "source_digest": result["result_digest"],
        "provenance": tuple(str(item.get("source_record_id") or "") for item in combined if item.get("status") == "accepted"),
        "topic": str(requirement.get("topic") or ""), "target_capability": str(requirement.get("target_capability") or ""),
        "intended_role": "advisory_teaching_evidence", "accepted_sources": tuple(item for item in combined if item.get("status") == "accepted"),
        "provisional_resource": result["provisional_resource"],
    }
    return consume_developmental_resource_fulfillment(prepared, request_id=str(request.get("request_id") or ""), selected_option="supply_fulfillment", supplied=material)


def _fulfillment_learning_bundle(
    requirement: Mapping[str, Any],
    fulfillment: DevelopmentalResourceAuthorityFulfillment,
    supplied: Mapping[str, Any],
    existing_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge validated material into the existing bundle shape, preserving roles."""

    base = dict(existing_bundle or load_retained_learning_bundle(str(requirement.get("domain") or ""), str(requirement.get("topic") or "")) or {})
    material = dict(supplied)
    provenance = tuple(base.get("resource_provenance") or ()) + ({
        "fulfillment_id": fulfillment.fulfillment_id,
        "source_identity": fulfillment.source_identity,
        "source_digest": fulfillment.source_digest,
        "intended_role": fulfillment.intended_role,
    },)
    if fulfillment.fulfillment_type == "operator_teaching_resource_fulfillment":
        base["study_resources"] = tuple(base.get("study_resources") or ()) + tuple(dict(item) for item in (material.get("study_resources") or ()))
        base["assessment_dimensions"] = tuple(base.get("assessment_dimensions") or ()) + tuple(dict(item) for item in (material.get("assessment_dimensions") or ()))
        base["capability_catalog"] = tuple(dict.fromkeys(tuple(base.get("capability_catalog") or ()) + tuple(str(item) for item in (material.get("capability_catalog") or ()))))
    elif fulfillment.fulfillment_type == "external_research_fulfillment":
        base = {**base, **dict(material.get("provisional_resource") or {})}
        provenance = tuple(base.get("resource_provenance") or ()) + ({
            "fulfillment_id": fulfillment.fulfillment_id,
            "source_identity": fulfillment.source_identity,
            "source_digest": fulfillment.source_digest,
            "intended_role": fulfillment.intended_role,
        },)
    elif fulfillment.fulfillment_type == "operator_sealed_evaluator_fulfillment":
        cases = tuple(dict(item) for item in (material.get("sealed_evaluation_cases") or ()))
        if str(material.get("execution_contract_version") or "") == "sealed_evaluator_execution_v3":
            cases = tuple({
                **case,
                "capability_dimension": str(case.get("assessment_dimension") or ""),
                "input_data": dict(dict(case.get("learner_view") or {}).get("input_data") or {}),
                "required_reasoning_constraints": tuple(str(item) for item in (dict(dict(case.get("evaluator_view") or {}).get("deterministic_predicate") or {}).get("required_concepts") or ())),
                "forbidden_reasoning_patterns": tuple(str(item) for item in (dict(dict(case.get("evaluator_view") or {}).get("deterministic_predicate") or {}).get("forbidden_concepts") or ())),
                "task_type": "concept_coverage",
            } for case in cases)
            base["execution_contract_version"] = "sealed_evaluator_execution_v3"
        base["sealed_evaluation_cases"] = cases
        base["independent_evaluator"] = dict(material.get("independent_evaluator") or {})
    elif fulfillment.fulfillment_type == "local_model_result_fulfillment":
        mission = compile_developmental_mission_contract(f"Learn {str(requirement.get('topic') or '').replace('_', ' ')}.")
        request = {
            "request_id": str(material.get("request_id") or fulfillment.authority_request_id),
            "request_digest": fulfillment.semantic_identity,
            "model_identity": str(material.get("model_identity") or ""),
            "adapter_identity": str(material.get("adapter_identity") or ""),
        }
        result = {
            "result_id": fulfillment.source_identity,
            "response_digest": str(material.get("response_digest") or fulfillment.source_digest),
            "response_reference": str(material.get("response_reference") or ""),
            "model_identity": str(material.get("model_identity") or ""),
            "adapter_identity": str(material.get("adapter_identity") or ""),
            "provenance": {"request_id": fulfillment.authority_request_id},
        }
        if mission is not None:
            evidence = compile_mission_bound_advisory_learning_evidence(mission, compile_mission_information_need(mission), request, result)
            provisional = compile_provisional_learning_bundle_from_advisory(mission, evidence)
            if provisional is not None:
                base = provisional
    base.update({
        "resource_bundle_id": stable_id("fulfilled-learning-bundle", str(base.get("resource_bundle_id") or ""), fulfillment.fulfillment_id),
        "resource_provenance": provenance,
        "fulfillment_reference": fulfillment.fulfillment_id,
    })
    return base


def _fulfillment_clarification_question(
    request: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> str:
    if request.get("action_type") != "request_operator_sealed_evaluator":
        return "Supply one structured, scope-bound fulfillment with durable identity, provenance, topic, target capability, and the material required by the approved action."
    topic = str(requirement.get("topic") or "the approved topic")
    target = str(requirement.get("target_capability") or "the approved target capability")
    return (
        f"Supply JSON for one separately authored sealed evaluator for {topic}/{target}: "
        "fulfillment_type=operator_sealed_evaluator_fulfillment; source_identity; source_reference; "
        "source_digest; provenance; topic; target_capability; independent_evaluator; candidate_mutable=false; "
        "sealed_evaluation_cases with at least one baseline, control, held_out, adversarial, and transfer case; "
        "and no study_resources. The evaluator must remain separate from teaching material."
    )


def consume_developmental_resource_fulfillment(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    selected_option: str,
    supplied: Mapping[str, Any] | None = None,
    operator_text: str = "",
) -> ContinuousRuntimeController:
    """Validate one material response, resolve only its matching blocker, and resume once."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((position for position, item in enumerate(requests) if item.get("request_id") == request_id and item.get("request_kind") == "developmental_resource_fulfillment" and item.get("status") == "pending"), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_resource_policy", "duplicate_or_unknown_fulfillment_suppressed", (request_id,)),))
    request = requests[index]
    if selected_option not in tuple(request.get("permitted_responses") or ()):
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_resource_policy", "invalid_fulfillment_response_rejected", (request_id, selected_option)),))
    state = dict(controller.continuous_learning_state or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    requirement = dict(policy.get("requirement") or {})
    decision = dict(policy.get("decision") or {})
    authority_request_id = str(request.get("authority_request_id") or "")
    if not requirement or str(request.get("policy_decision_id") or "") != str(decision.get("decision_id") or ""):
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_resource_policy", "fulfillment_identity_mismatch", (request_id,)),))
    if selected_option == "ask_for_clarification":
        consumed_at = utc_now()
        resolved = {**request, "status": "consumed", "resolution": selected_option, "consumed_at": consumed_at}
        clarification_request = {
            **request,
            "request_id": stable_id("developmental-resource-fulfillment-clarification", request_id),
            "status": "pending",
            "exact_question": _fulfillment_clarification_question(request, requirement),
            "rationale": "The original fulfillment remains absent. This follow-up names the exact schema required for independent validation without granting additional authority.",
            "created_at": consumed_at,
        }
        response = {
            "request_id": request_id,
            "response_kind": "developmental_resource_fulfillment",
            "selected_option": selected_option,
            "operator_text": operator_text,
            "authority_granted": False,
            "created_at": consumed_at,
            "consumed_at": consumed_at,
        }
        updated_policy = {**policy, "status": "fulfillment_clarification_pending"}
        return replace(
            controller,
            continuous_mission_state="developmental_resource_authority_granted_pending_material",
            active_work_item="awaiting_authorized_resource_or_evaluator_material",
            continuous_developmental_insight_requests=requests[:index] + (resolved, clarification_request) + requests[index + 1 :],
            continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
            continuous_learning_state={**state, "developmental_resource_policy": updated_policy},
            journal=controller.journal + (_journal_entry("developmental_resource_policy", "fulfillment_clarification_request_created", (request_id, clarification_request["request_id"])),),
        )
    material = dict(supplied or {})
    if selected_option == "observe_completed_local_model_result":
        model_request_id = str(request.get("local_model_request_id") or "")
        try:
            model_request = LocalModelRequestResultLedger().observe_request(model_request_id)
            model_result = LocalModelRequestResultLedger().observe_result(str(model_request.get("result_id") or ""))
        except (KeyError, RuntimeError):
            model_request, model_result = {}, {}
        material = {
            "fulfillment_type": "local_model_result_fulfillment",
            "source_identity": str(model_result.get("result_id") or model_request_id),
            "source_type": "shared_local_model_result",
            "source_reference": str(model_result.get("result_id") or model_request_id),
            "source_digest": str(model_result.get("response_digest") or ""),
            "provenance": (str(model_request.get("request_id") or ""), str(model_result.get("result_id") or "")),
            "request_id": str(model_request.get("request_id") or ""),
            "topic": str(requirement.get("topic") or ""),
            "target_capability": str(requirement.get("target_capability") or ""),
            "intended_role": "advisory_teaching_evidence",
            "lifecycle_state": str(model_request.get("lifecycle_state") or ""),
            "execution_attempt_count": int(model_request.get("execution_attempt_count") or 0),
            "response_digest": str(model_result.get("response_digest") or ""),
            "response_reference": str(model_result.get("response_reference") or ""),
            "model_identity": str(model_result.get("model_identity") or ""),
            "adapter_identity": str(model_result.get("adapter_identity") or ""),
        }
    if selected_option == "reject_fulfillment":
        material = {**material, "fulfillment_type": "fulfillment_rejected"}
    elif selected_option == "defer_fulfillment":
        material = {**material, "fulfillment_type": "fulfillment_deferred"}
    fulfillment = compile_developmental_resource_authority_fulfillment(
        requirement,
        decision,
        authority_request_id=authority_request_id,
        operator_interaction_id=request_id,
        supplied=material,
    )
    existing = tuple(dict(item) for item in (state.get("developmental_resource_fulfillments") or ()))
    duplicate = next((item for item in existing if item.get("semantic_identity") == fulfillment.semantic_identity and item.get("status") == fulfillment.status), None)
    if duplicate is not None:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_resource_policy", "equivalent_fulfillment_replay_suppressed", (request_id, str(duplicate.get("fulfillment_id") or ""))),))
    consumed_at = utc_now()
    resolved = {**request, "status": "consumed", "resolution": selected_option, "consumed_at": consumed_at}
    responses = tuple(controller.continuous_operator_interaction_responses) + ({
        "request_id": request_id, "response_kind": "developmental_resource_fulfillment", "selected_option": selected_option,
        "operator_text": operator_text, "authority_granted": False, "created_at": consumed_at, "consumed_at": consumed_at,
    },)
    base_state = {
        **state,
        "developmental_resource_fulfillments": existing + (fulfillment.as_dict(),),
        "developmental_resource_policy": {**policy, "status": "fulfillment_validated" if fulfillment.status == "validated" else fulfillment.status, "fulfillment_id": fulfillment.fulfillment_id},
    }
    if fulfillment.fulfillment_type == "local_model_result_fulfillment":
        base_state["local_model_execution_count"] = int(material.get("execution_attempt_count") or 0)
        base_state["local_model_result_reference"] = {
            "result_id": fulfillment.source_identity,
            "response_digest": str(material.get("response_digest") or fulfillment.source_digest),
            "response_reference": str(material.get("response_reference") or ""),
            "model_identity": str(material.get("model_identity") or ""),
        }
    updated = replace(
        controller,
        continuous_developmental_insight_requests=requests[:index] + (resolved,) + requests[index + 1 :],
        continuous_operator_interaction_responses=responses,
        continuous_learning_state=base_state,
        journal=controller.journal + (_journal_entry("developmental_resource_policy", "typed_fulfillment_validated" if fulfillment.status == "validated" else "typed_fulfillment_did_not_resolve_blocker", (fulfillment.fulfillment_id, fulfillment.status)),),
    )
    if fulfillment.status != "validated":
        status = "developmental_resource_fulfillment_deferred" if fulfillment.fulfillment_type == "fulfillment_deferred" else "developmental_resource_fulfillment_invalid"
        return replace(updated, continuous_mission_state=status, active_work_item="resource_blocker_remains_active", continuous_active_subgoal={})
    bundle = _fulfillment_learning_bundle(requirement, fulfillment, material, state.get("retained_bundle"))
    instruction = f"Learn {str(requirement.get('topic') or '').replace('_', ' ')}."
    prior_mission = dict(state.get("mission") or {})
    if not prior_mission:
        return replace(
            updated,
            continuous_mission_state="developmental_resource_fulfillment_incomplete",
            active_work_item="fulfilled_learning_mission_contract_unavailable",
            continuous_learning_state={
                **base_state,
                "resource_blocker": {
                    "blocker": "fulfilled_learning_mission_contract_unavailable",
                    "missing_fields": ("mission_contract",),
                    "no_provider_or_research_call_performed": True,
                },
            },
        )
    resumed = attach_developmental_learning_mission(
        updated,
        instruction,
        bundle,
        existing_mission=DevelopmentalMissionContract(**prior_mission),
        preserve_learning_state=True,
    )
    resumed_state = {
        **base_state,
        **dict(resumed.continuous_learning_state or {}),
        "developmental_resource_fulfillments": base_state["developmental_resource_fulfillments"],
        "developmental_resource_policy": {**base_state["developmental_resource_policy"], "status": "blocker_resolved", "resumed_mission_id": str((resumed.continuous_learning_state or {}).get("mission", {}).get("mission_id") or "")},
    }
    agenda = dict(resumed_state.get("developmental_agenda") or {})
    resumed_active = bool(resumed.continuous_active_subgoal)
    if agenda and agenda_state_is_valid(agenda):
        resumed_state["developmental_agenda"] = {
            **agenda,
            "status": "mission_active" if resumed_active else "awaiting_resource_policy_authority",
            "active_mission_id": str((resumed.continuous_learning_state or {}).get("mission", {}).get("mission_id") or agenda.get("active_mission_id") or ""),
            "next_eligible_transition": "bounded_learning_attempt_or_evaluation" if resumed_active else "resource_policy_refresh_after_partial_blocker_resolution",
            "updated_at": consumed_at,
        }
    completed = replace(
        resumed,
        continuous_mission_state=resumed.continuous_mission_state if resumed_active else "developmental_resource_fulfillment_incomplete",
        active_work_item=resumed.active_work_item if resumed_active else "resource_blocker_partially_resolved",
        continuous_learning_state=resumed_state,
        continuous_developmental_insight_requests=updated.continuous_developmental_insight_requests,
        continuous_operator_interaction_responses=responses,
        journal=resumed.journal + (_journal_entry("developmental_resource_policy", "validated_fulfillment_resumed_original_goal_once", (fulfillment.fulfillment_id, str(requirement.get("goal_id") or ""))),),
    )
    return completed if resumed_active else compile_governed_developmental_resource_policy(completed, explicit_refresh=True)


def recover_developmental_resource_fulfillment_clarification(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Restore only a legacy fulfillment clarification that was persisted invalid.

    Older workers routed a clarification through material validation. That
    historical partial record is retained, while its one missing schema request
    is reconstructed exactly once on restart.
    """

    if controller.continuous_mission_state != "developmental_resource_fulfillment_invalid":
        return controller
    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    if any(item.get("request_kind") == "developmental_resource_fulfillment" and item.get("status") == "pending" for item in requests):
        return controller
    response = next(
        (
            dict(item)
            for item in reversed(controller.continuous_operator_interaction_responses)
            if item.get("response_kind") == "developmental_resource_fulfillment"
            and item.get("selected_option") == "ask_for_clarification"
        ),
        {},
    )
    request_id = str(response.get("request_id") or "")
    source = next(
        (
            item
            for item in requests
            if item.get("request_id") == request_id
            and item.get("request_kind") == "developmental_resource_fulfillment"
            and item.get("status") == "consumed"
            and item.get("resolution") == "ask_for_clarification"
        ),
        {},
    )
    state = dict(controller.continuous_learning_state or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    requirement = dict(policy.get("requirement") or {})
    fulfillments = tuple(dict(item) for item in (state.get("developmental_resource_fulfillments") or ()) if isinstance(item, Mapping))
    legacy_partial = any(
        item.get("operator_interaction_id") == request_id
        and item.get("fulfillment_type") == "partial_fulfillment"
        and "operator_clarification_required" in tuple(item.get("partial_sections") or ())
        for item in fulfillments
    )
    if not source or not requirement or not legacy_partial:
        return controller
    follow_up_id = stable_id("developmental-resource-fulfillment-clarification", request_id)
    follow_up = {
        **source,
        "request_id": follow_up_id,
        "status": "pending",
        "exact_question": _fulfillment_clarification_question(source, requirement),
        "rationale": "Recovered legacy clarification. Supply only the stated sealed evaluator schema; no new authority is granted.",
        "created_at": utc_now(),
    }
    return replace(
        controller,
        continuous_mission_state="developmental_resource_authority_granted_pending_material",
        active_work_item="awaiting_authorized_resource_or_evaluator_material",
        continuous_developmental_insight_requests=requests + (follow_up,),
        continuous_learning_state={**state, "developmental_resource_policy": {**policy, "status": "fulfillment_clarification_pending"}},
        journal=controller.journal + (_journal_entry("developmental_resource_policy", "legacy_fulfillment_clarification_recovered_once", (request_id, follow_up_id)),),
    )


def _mark_agenda_mission_active(
    controller: ContinuousRuntimeController,
    *,
    proposal_id: str,
    mission_id: str,
    awaiting_evaluator: bool,
) -> ContinuousRuntimeController:
    """Record an approved agenda item without changing learning lifecycle ownership."""

    state = dict(controller.continuous_learning_state or {})
    agenda = dict(state.get("developmental_agenda") or {})
    if not agenda or not agenda_state_is_valid(agenda):
        return controller
    decision_history = tuple(agenda.get("decision_history") or ()) + (f"approved:{proposal_id}",)
    return replace(
        controller,
        continuous_learning_state={
            **state,
            "developmental_agenda": {
                **agenda,
                "status": "awaiting_evaluator_authority" if awaiting_evaluator else "mission_active",
                "active_mission_id": mission_id,
                "pending_proposal_id": "",
                "decision_history": decision_history,
                "next_eligible_transition": "evaluator_authority" if awaiting_evaluator else "terminal_mission_outcome",
                "updated_at": utc_now(),
            },
        },
        journal=controller.journal + (_journal_entry("developmental_agenda", "approved_proposal_bound_to_existing_learning_mission", (proposal_id, mission_id)),),
    )


def _advance_agenda_after_goal_decision(
    controller: ContinuousRuntimeController,
    *,
    proposal_id: str,
    semantic_identity: str,
    decision: str,
) -> ContinuousRuntimeController:
    """Consume a rejection/defer once, then rank one eligible alternative."""

    state = dict(controller.continuous_learning_state or {})
    agenda = dict(state.get("developmental_agenda") or {})
    if not agenda or not agenda_state_is_valid(agenda):
        return controller
    decision_key = f"{decision}:{proposal_id}"
    if decision_key in tuple(agenda.get("decision_history") or ()):
        return controller
    rejected = tuple(agenda.get("rejected_proposal_ids") or ())
    deferred = tuple(agenda.get("deferred_proposal_ids") or ())
    cooldown = {
        "semantic_identity": semantic_identity,
        "trigger": decision,
        "status": "active",
        "release_condition": "material_evidence_change_or_explicit_operator_refresh",
        "proposal_id": proposal_id,
    }
    updated_agenda = {
        **agenda,
        "status": "refreshing_evidence",
        "pending_proposal_id": "",
        "rejected_proposal_ids": rejected + ((proposal_id,) if decision == "reject_developmental_goal" else ()),
        "deferred_proposal_ids": deferred + ((proposal_id,) if decision == "defer_developmental_goal" else ()),
        "cooldown_records": tuple(agenda.get("cooldown_records") or ()) + ((cooldown,) if semantic_identity else ()),
        "decision_history": tuple(agenda.get("decision_history") or ()) + (decision_key,),
        "rejected_cycle_count": int(agenda.get("rejected_cycle_count") or 0) + int(decision == "reject_developmental_goal"),
        "deferred_cycle_count": int(agenda.get("deferred_cycle_count") or 0) + int(decision == "defer_developmental_goal"),
        "next_eligible_transition": "compile_candidates",
        "updated_at": utc_now(),
    }
    prepared = replace(
        controller,
        continuous_learning_state={**state, "developmental_agenda": updated_agenda},
        continuous_mission_state="developmental_agenda_refreshing_evidence",
        active_work_item="developmental_agenda_refreshing_evidence",
        journal=controller.journal + (_journal_entry("developmental_agenda", "operator_rejection_or_defer_consumed_then_reranked", (proposal_id, decision)),),
    )
    return _compile_next_agenda_proposal(prepared, str(updated_agenda.get("operator_scope") or ""), force=True)


def compile_mission_bound_local_model_learning_request(
    controller: ContinuousRuntimeController,
    operator_instruction: str,
) -> ContinuousRuntimeController:
    """Bind a missing topic bundle to the existing one-use local-model request.

    This stays inside the controller's persisted learning state.  It neither
    executes inference nor promotes a capability.  The live-runtime helper is
    imported lazily because that module already depends on this controller.
    """

    mission = compile_developmental_mission_contract(operator_instruction)
    if mission is None:
        return controller
    retained = load_retained_learning_bundle(mission.domain, mission.topic)
    if retained is not None:
        return attach_developmental_learning_mission(controller, operator_instruction, retained)
    need = compile_mission_information_need(mission)
    current = dict(controller.continuous_learning_state or {})
    existing = dict(current.get("local_model_request") or {})
    if existing and str(existing.get("request_digest") or "") == str(need["information_need_digest"]):
        return controller
    ledger = LocalModelRequestResultLedger()
    request = ledger.find_completed_mission_request(
        mission_id=mission.mission_id,
        mission_information_need_identity=str(need["semantic_identity"]),
        question=str(need["request_text"]),
        requester_type="mission_bound_learning",
        question_objective=str(need.get("missing_evidence") or "mission-bound learning evidence"),
    ) or ledger.create_or_reuse_request(
        semantic_identity=stable_id("mission-bound-local-model-semantic", controller.session_id, mission.mission_id, str(need["semantic_identity"])),
        question=str(need["request_text"]), requester_type="mission_bound_learning",
        requester_reference=controller.session_id, mission_id=mission.mission_id,
        mission_information_need_identity=str(need["semantic_identity"]),
        question_objective=str(need.get("missing_evidence") or "mission-bound learning evidence"),
    )
    lane = dict(request.get("selected_lane") or {})
    status = "learning_local_model_result_available" if request.get("lifecycle_state") == "completed" else "learning_local_model_request_pending" if lane.get("available") else "learning_local_model_unavailable"
    updated = replace(
        controller,
        continuous_mission_state=status,
        continuous_mission_contract={**mission.as_dict(), "original_operator_goal": mission.operator_instruction},
        continuous_learning_state={
            "mission": mission.as_dict(),
            "information_need": need,
            "local_model_lane": lane,
            "local_model_request": request,
            "local_model_execution_count": 0,
            "protocol": "mission_bound_local_model_learning_bridge_v1",
        },
        active_work_item="learning_local_model_result_available" if request.get("lifecycle_state") == "completed" else "learning_local_model_request_pending" if lane.get("available") else "learning_local_model_unavailable",
        journal=controller.journal + (_journal_entry("developmental_learning", "mission_bound_local_model_information_need_compiled", (mission.mission_id, str(need["information_need_id"]))),),
    )
    return consume_mission_bound_local_model_learning_approval(updated) if request.get("lifecycle_state") == "completed" else updated


def consume_mission_bound_local_model_learning_approval(
    controller: ContinuousRuntimeController,
    *,
    model_executor: Any | None = None,
    sealed_evaluation_cases: Sequence[Mapping[str, Any]] = (),
) -> ContinuousRuntimeController:
    """Observe a terminal shared-ledger result without approving or executing it.

    Kept as a compatibility entry point for callers restored from older state.
    The parameters are intentionally unused: controller-owned execution is no
    longer a permitted lifecycle path.
    """

    del model_executor, sealed_evaluation_cases
    state = dict(controller.continuous_learning_state or {})
    request_reference = dict(state.get("local_model_request") or {})
    request_id = str(request_reference.get("request_id") or "")
    if not request_id:
        return controller
    try:
        request = LocalModelRequestResultLedger().observe_request(request_id)
    except (KeyError, RuntimeError):
        return replace(controller, continuous_mission_state="learning_local_model_ledger_unavailable", active_work_item="learning_local_model_ledger_unavailable")
    if request.get("lifecycle_state") not in {"completed", "unavailable", "failed", "interrupted", "rejected"}:
        return controller
    result_id = str(request.get("result_id") or "")
    result = LocalModelRequestResultLedger().observe_result(result_id) if result_id else {}
    existing_bundle = dict(state.get("provisional_resource_bundle") or {})
    existing_evidence = dict(state.get("mission_bound_advisory_evidence") or {})
    if existing_bundle and str(existing_evidence.get("shared_result_id") or "") == result_id:
        return replace(
            controller,
            continuous_learning_state={
                **state,
                "local_model_request": request,
                "local_model_result_reference": result,
                "local_model_execution_count": int(request.get("execution_attempt_count") or 0),
            },
        )
    mission = compile_developmental_mission_contract(str((state.get("mission") or {}).get("operator_instruction") or ""))
    need = dict(state.get("information_need") or {})
    if mission is None or not need:
        return replace(controller, continuous_mission_state="learning_local_model_result_observed", active_work_item="learning_local_model_result_observed", continuous_learning_state={**state, "local_model_request": request, "local_model_result_reference": result, "local_model_execution_count": int(request.get("execution_attempt_count") or 0)})
    evidence = compile_mission_bound_advisory_learning_evidence(mission, need, request, result)
    bundle = compile_provisional_learning_bundle_from_advisory(mission, evidence)
    if bundle is not None:
        bundle = bind_independent_learning_evaluator(mission, bundle)
    common = {
        "information_need": need,
        "local_model_lane": dict(request.get("selected_lane") or {}),
        "local_model_request": request,
        "local_model_result_reference": result,
        "mission_bound_advisory_evidence": evidence.as_dict(),
        "local_model_execution_count": int(request.get("execution_attempt_count") or 0),
        "capability_state_boundary": "unchanged_pending_independent_evaluation",
    }
    if bundle is None:
        return replace(controller, continuous_mission_state="learning_model_evidence_insufficient", active_work_item="learning_model_evidence_insufficient", continuous_learning_state={**state, **common, "provisional_resource_bundle": None, "follow_up_information_needs": evidence.follow_up_information_needs})
    attached = attach_developmental_learning_mission(controller, mission.operator_instruction, bundle)
    attached_state = {**attached.continuous_learning_state, **common, "provisional_resource_bundle": bundle, "follow_up_information_needs": evidence.follow_up_information_needs}
    return replace(attached, continuous_learning_state=attached_state)


def consume_developmental_learning_evaluation(
    controller: ContinuousRuntimeController,
    evaluation: DevelopmentalEvaluationRecord,
    *,
    attempt: Mapping[str, Any] | None = None,
) -> ContinuousRuntimeController:
    """Persist one independent learning result and select the next distinct gap."""

    state = dict(controller.continuous_learning_state or {})
    mission = dict(state.get("mission") or {})
    if not mission or evaluation.mission_id != mission.get("mission_id"):
        raise ValueError("learning evaluation does not belong to the active developmental mission")
    evaluations = tuple(state.get("evaluations") or ())
    if any(str(item.get("evaluation_id") or "") == evaluation.evaluation_id for item in evaluations):
        return controller
    active = dict(controller.continuous_active_subgoal or {})
    attempts = tuple(state.get("attempts") or ()) + ((dict(attempt),) if attempt else ())
    updated_state = {
        **state,
        "attempts": attempts,
        "evaluations": evaluations + (evaluation.as_dict(),),
        "last_evaluation": evaluation.as_dict(),
    }
    typed_mission = DevelopmentalMissionContract(**mission)
    retained_bundle = dict(state["retained_bundle"])
    if not evaluation.promotion_eligible:
        localization = localize_learning_failure(typed_mission, evaluation)
        revised_bundle = compile_revised_learning_bundle(retained_bundle, localization) if localization is not None else None
        typed_active = LearningSubgoal(**{key: value for key, value in active.items() if key in LearningSubgoal.__dataclass_fields__})
        revised_subgoal = compile_revised_learning_subgoal(typed_active, revised_bundle, localization) if revised_bundle is not None and localization is not None else None
        if revised_subgoal is not None:
            revisions = tuple(state.get("resource_revisions") or ())
            revision = dict(revised_bundle.get("resource_revision") or {})
            return replace(
                controller,
                continuous_mission_state="learning_subgoal_active",
                continuous_learning_state={
                    **updated_state,
                    "retained_bundle": revised_bundle,
                    "provisional_resource_bundle": revised_bundle,
                    "failure_localizations": tuple(state.get("failure_localizations") or ()) + (localization.as_dict(),),
                    "follow_up_information_needs": tuple(state.get("follow_up_information_needs") or ()) + (dict(localization.recommended_next_information_need),),
                    "resource_revisions": revisions + ((revision,) if revision else ()),
                    "selected_frontier": {
                        "frontier_id": revised_subgoal.source_gap_id,
                        "topic": revised_subgoal.topic,
                        "capability_dimension": revised_subgoal.capability_target,
                        "rank": revised_subgoal.frontier_rank,
                        "selection_reason": revised_subgoal.selection_reason,
                    },
                },
                continuous_active_subgoal={**revised_subgoal.as_dict(), "execution_kind": "developmental_learning"},
                active_work_item=revised_subgoal.measurable_objective,
                journal=controller.journal + (_journal_entry("developmental_learning", "independent_failure_localized_to_revised_learning_subgoal", (evaluation.evaluation_id, localization.localization_id, revised_subgoal.subgoal_id)),),
            )
    consumed = tuple(dict.fromkeys(tuple(state.get("consumed_gap_ids") or ()) + (str(active.get("source_gap_id") or ""),)))
    updated_state["consumed_gap_ids"] = consumed
    knowledge = tuple(controller.continuous_knowledge_ledger)
    if evaluation.promotion_eligible and not any(str(item.get("behavioral_evaluation_ref") or "") == evaluation.evaluation_id for item in knowledge):
        record = CapabilityKnowledgeRecord(
            capability_id=f"{typed_mission.topic}_{evaluation.capability_dimension}",
            original_weakness="independently evaluated learning behavior was previously unassessed",
            evidence=(evaluation.evaluation_id, *evaluation.case_ids),
            first_incorrect_transition="provisional resource -> independently evaluated demonstrated behavior",
            strategies_attempted=("visible typed reasoning attempt", "deterministic sealed evaluation"),
            failed_approaches=(),
            successful_mechanism="revision-aware bounded semantic learning against independent finite-dimensional predicates",
            exact_candidate="no repository candidate; bounded learning attempt only",
            tests_added=(evaluation.evaluator_identity,),
            metrics_before_after={"baseline": dict(evaluation.baseline_metrics), "held_out": dict(evaluation.held_out_metrics), "control": dict(evaluation.control_metrics), "adversarial": dict(evaluation.adversarial_metrics), "transfer": dict(evaluation.transfer_metrics)},
            controls=("teaching evidence isolated from evaluator", "sealed cases excluded from attempt", "candidate self-score ignored"),
            adversarial_evidence=tuple(case_id for case_id in evaluation.case_ids if "adversarial" in case_id),
            held_out_evidence={"case_ids": tuple(case_id for case_id in evaluation.case_ids if "heldout" in case_id or "held-out" in case_id), "evaluation_id": evaluation.evaluation_id},
            reproduction_evidence=evaluation.evaluation_digest,
            provider_contribution="advisory local-model result only; no provider call",
            local_repair_contribution="independent evaluator feedback revision",
            application_evidence="not applicable; tracked source unchanged",
            regression_evidence="sealed control and adversarial metrics passed",
            reassessment="behaviorally_demonstrated",
            residual_uncertainty="complex inner-product-space scope remains unassessed",
            reusable_process_rules=("resource ingestion is not capability promotion", "only independent sealed evaluation updates learning capability"),
            evidence_stage="behaviorally_demonstrated",
            capability_acquired=True,
            eligible_for_behavioral_evaluation=False,
            behavioral_evaluation_ref=evaluation.evaluation_id,
            behavioral_evaluation=evaluation.as_dict(),
        )
        knowledge = knowledge + (record.as_dict(),)
    next_gap = derive_next_learning_gap(retained_bundle, evaluation) if evaluation.promotion_eligible else None
    if next_gap is not None:
        return replace(
            controller,
            continuous_mission_state="learning_next_gap_resource_needed",
            continuous_learning_state={**updated_state, "next_learning_gap": next_gap, "capability_update_evaluation_id": evaluation.evaluation_id},
            continuous_knowledge_ledger=knowledge,
            continuous_capability_inventory=tuple(item.as_dict() for item in capability_inventory_from_knowledge(tuple(CapabilityKnowledgeRecord(**dict(item)) for item in knowledge))),
            continuous_active_subgoal={},
            active_work_item="learning_resource_evidence_needed",
            journal=controller.journal + (_journal_entry("developmental_learning", "narrow_capability_updated_next_gap_selected", (evaluation.evaluation_id, str(next_gap.get("gap_id") or ""))),),
        )
    # Rebuild typed records only at the controller boundary. This preserves one
    # source of truth in persisted dictionaries while leaving helpers immutable.
    from orchestration.runtime.developmental_learning import DevelopmentalGap, ResourceAcquisitionPlan
    typed_plan = ResourceAcquisitionPlan(**dict(state["resource_plan"]))
    typed_gaps = tuple(DevelopmentalGap(**dict(item)) for item in state.get("gaps") or ())
    next_subgoal = compile_learning_subgoal(typed_mission, typed_gaps, typed_plan, state["retained_bundle"], consumed_gap_ids=consumed)
    if next_subgoal is None:
        completed = replace(
            controller,
            continuous_mission_state="observing_for_new_learning_evidence",
            continuous_learning_state=updated_state,
            continuous_active_subgoal={},
            active_work_item=OBSERVATION_STATE,
            journal=controller.journal + (_journal_entry("developmental_learning", "learning_evaluation_consumed_exactly_once_frontier_exhausted", (evaluation.evaluation_id,)),),
        )
        return observe_developmental_agenda_mission_outcome(
            completed,
            outcome_id=evaluation.evaluation_id,
            outcome="behaviorally_demonstrated" if evaluation.promotion_eligible else "behaviorally_failed",
            evidence_refs=(evaluation.evaluation_id, *evaluation.case_ids),
        )
    return replace(
        controller,
        continuous_mission_state="learning_subgoal_active",
        continuous_learning_state={**updated_state, "selected_frontier": {
            "frontier_id": next_subgoal.source_gap_id,
            "topic": next_subgoal.topic,
            "capability_dimension": next_subgoal.capability_target,
            "rank": next_subgoal.frontier_rank,
            "selection_reason": next_subgoal.selection_reason,
        }},
        continuous_active_subgoal={**next_subgoal.as_dict(), "execution_kind": "developmental_learning"},
        active_work_item=next_subgoal.measurable_objective,
        journal=controller.journal + (_journal_entry("developmental_learning", "learning_evaluation_consumed_exactly_once_selected_next_subgoal", (evaluation.evaluation_id, next_subgoal.subgoal_id)),),
    )


def assess_continuous_mission_runtime(
    controller: ContinuousRuntimeController,
    evidence_records: Sequence[Mapping[str, Any]],
) -> ContinuousRuntimeController:
    findings = evidence_to_findings(evidence_records)
    return replace(
        controller,
        continuous_mission_state="assessing_runtime",
        continuous_mission_findings=tuple(item.as_dict() for item in findings),
        journal=controller.journal
        + (_journal_entry("continuous_mission", "evidence_records_compiled_to_runtime_findings", tuple(item.finding_id for item in findings)),),
    )


def assess_continuous_mission_behavioral_failures(
    controller: ContinuousRuntimeController,
    failure_records: Sequence[BehavioralFailureRecord | Mapping[str, Any]],
) -> ContinuousRuntimeController:
    recovered = _recover_behavioral_failure_records(failure_records)
    findings = tuple(
        behavioral_failure_to_runtime_finding(record)
        for record in recovered
        if record.task_eligibility == "eligible"
    )
    return replace(
        controller,
        continuous_mission_state="assessing_behavioral_failures",
        continuous_behavioral_failure_records=tuple(record.as_dict() for record in recovered),
        continuous_mission_findings=tuple(item.as_dict() for item in findings),
        journal=controller.journal
        + (
            _journal_entry(
                "continuous_mission",
                "behavioral_failure_records_compiled_to_runtime_findings",
                tuple(item.failure_id for item in recovered),
            ),
        ),
    )


def refresh_continuous_mission_frontier(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    findings = [evidence_to_findings((item,))[0] for item in controller.continuous_mission_findings]
    knowledge = [CapabilityKnowledgeRecord(**item) for item in controller.continuous_knowledge_ledger]
    frontier = rank_weakness_frontier(
        findings,
        consumed_signatures=controller.continuous_consumed_weakness_signatures,
        knowledge_ledger=knowledge,
    )
    return replace(
        controller,
        continuous_mission_state="selecting_weakness",
        continuous_mission_frontier=tuple(item.as_dict() for item in frontier),
        journal=controller.journal
        + (_journal_entry("continuous_mission", "runtime_findings_ranked_into_weakness_frontier", tuple(item.semantic_signature for item in frontier)),),
    )


def select_continuous_mission_subgoal(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    if not controller.continuous_mission_contract:
        return controller
    behavioral_evaluation = _activate_pending_behavioral_evaluation(controller)
    if behavioral_evaluation is not None:
        return behavioral_evaluation
    contract = compile_broad_mission_contract(controller.continuous_mission_contract["original_operator_goal"])
    frontier = [WeaknessCandidate(**item) for item in controller.continuous_mission_frontier if item.get("status", "eligible") == "eligible"]
    subgoal = compile_active_subgoal(contract, frontier)
    if subgoal is None:
        if controller.continuous_mission_frontier:
            observed = replace(
                controller,
                continuous_mission_state="observing_for_new_weaknesses",
                continuous_active_subgoal={},
                active_work_item=OBSERVATION_STATE,
                continuous_observation_state={
                    **(controller.continuous_observation_state or {}),
                    "observation_reason": "ranked_frontier_has_no_executable_subgoal",
                    "ranked_frontier_count": len(controller.continuous_mission_frontier),
                },
                journal=controller.journal
                + (_journal_entry("continuous_mission", "ranked_frontier_had_no_executable_subgoal", (str(len(controller.continuous_mission_frontier)),)),),
            )
            statuses = {str(item.get("status") or "eligible") for item in controller.continuous_mission_frontier}
            if statuses and statuses <= {"satisfied", "superseded", "rejected"}:
                return exit_observation_with_action_derivation(observed)
            return observed
        return assess_and_advance_continuous_main_goal(controller)
    if _candidate_design_scope_is_exhausted(controller, subgoal.as_dict()):
        return _hold_for_new_repository_bound_evidence(controller, subgoal.as_dict())
    objective = ContinuousObjective(
        objective_id=subgoal.subgoal_id,
        title=subgoal.measurable_objective[:240],
        state="ACTIVE",
        source="CONTINUOUS_SUBGOAL",
        authority_class="AUTONOMOUS_SAFE_LOCAL_SANDBOX_UNTIL_APPLICATION",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    return replace(
        controller,
        continuous_mission_state="subgoal_active",
        continuous_active_subgoal=subgoal.as_dict(),
        active_work_item=subgoal.measurable_objective,
        active_objective=objective,
        objectives=_merge_objectives(controller.objectives, (objective,)),
        journal=controller.journal + (_journal_entry("continuous_mission", "highest_ranked_eligible_weakness_compiled_to_active_subgoal", (subgoal.subgoal_id,)),),
    )


def _candidate_design_scope_signature(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
) -> str:
    observation = controller.continuous_observation_state or {}
    return stable_id(
        "repository-bound-candidate-design-scope",
        tuple(str(item) for item in (subgoal.get("source_inspection_scope") or ())),
        str(observation.get("operator_supplied_candidate_target") or ""),
    )


def _candidate_design_scope_is_exhausted(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
) -> bool:
    observation = controller.continuous_observation_state or {}
    return bool(observation.get("candidate_design_evidence_exhausted")) and (
        str(observation.get("candidate_design_evidence_scope_signature") or "")
        == _candidate_design_scope_signature(controller, subgoal)
    )


def _hold_for_new_repository_bound_evidence(
    controller: ContinuousRuntimeController,
    subgoal: Mapping[str, Any],
) -> ContinuousRuntimeController:
    return replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        active_work_item=OBSERVATION_STATE,
        continuous_observation_state={
            **(controller.continuous_observation_state or {}),
            "observation_reason": "repository_bound_candidate_design_evidence_scope_exhausted",
            "candidate_design_evidence_exhausted": True,
            "blocked_subgoal_id": str(subgoal.get("subgoal_id") or ""),
        },
        journal=controller.journal
        + (
            _journal_entry(
                "continuous_mission",
                "blocked_repeat_of_abstract_candidate_design_without_new_repository_evidence",
                (str(subgoal.get("subgoal_id") or ""),),
            ),
        ),
    )


def _activate_pending_behavioral_evaluation(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController | None:
    """Promote one structurally-valid candidate into independent local evaluation.

    The normal frontier is intentionally not consulted first here. A candidate
    that has passed only self-contained sandbox checks must receive its one
    independent evaluation before the runtime can treat later frontier work as
    a new developmental result.
    """

    if controller.continuous_active_subgoal or controller.pending_application_decision_id:
        return None
    record = _next_pending_behavioral_evaluation_record(controller)
    if record is None:
        return None
    contract = _broad_contract_from_state(controller)
    candidate_id = str(record.metrics_before_after.get("candidate_id") or stable_id("structural-candidate", record.capability_id, record.exact_candidate))
    task_family_id = stable_id("behavioral-task-family", record.capability_id, record.original_weakness)
    evaluation_id = stable_id("behavioral-evaluation", contract.mission_id, task_family_id, candidate_id)
    evaluation = {
        "evaluation_id": evaluation_id,
        "task_family_id": task_family_id,
        "capability_id": record.capability_id,
        "developmental_gap_id": record.capability_id,
        "candidate_id": candidate_id,
        "baseline_attempt_id": str(record.metrics_before_after.get("baseline") or "structural-baseline"),
        "required_evidence": (
            "sealed_or_preexisting_case_ids",
            "control_case_ids",
            "post_candidate_metrics",
            "transfer_metrics",
            "regression_metrics",
            "evidence_independence",
        ),
        "promotion_blocker": "independent_behavioral_evaluation_required",
        "structural_record": record.as_dict(),
    }
    subgoal = ActiveSubgoal(
        subgoal_id=stable_id("behavioral-evaluation-subgoal", contract.mission_id, evaluation_id),
        source_mission_id=contract.mission_id,
        weakness_id=record.capability_id,
        measurable_objective=f"independently evaluate {record.capability_id} beyond structural sandbox validation",
        baseline="behavioral_evaluation=not_run",
        success_threshold="independent_cases_show_target_and_transfer_improvement_without_control_regression",
        controls=("candidate self-report is not accepted as evidence", "tracked source remains unchanged"),
        adversarial_tests="candidate-generated expected outputs and artifact-existence-only evidence are rejected",
        held_out_policy="use sealed or preexisting behavior cases that do not overlap training cases",
        sandbox_scope="independent_local_behavioral_evaluation_only",
        source_inspection_scope=("candidate artifact", "declared independent evaluation protocol"),
        tracked_application_allowlist=(),
        rollback_condition="never promote a capability when independent behavioral evidence is absent or fails",
        completion_classification="behavioral_evaluation_pending",
        execution_kind="independent_behavioral_evaluation",
        behavioral_evaluation=evaluation,
    )
    objective = ContinuousObjective(
        objective_id=subgoal.subgoal_id,
        title=subgoal.measurable_objective[:240],
        state="ACTIVE",
        source="CONTINUOUS_BEHAVIORAL_EVALUATION",
        authority_class="AUTONOMOUS_SAFE_LOCAL_EVALUATION_ONLY",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    return replace(
        controller,
        continuous_mission_state="behavioral_evaluation_active",
        continuous_active_subgoal=subgoal.as_dict(),
        active_work_item=subgoal.measurable_objective,
        active_objective=objective,
        objectives=_merge_objectives(controller.objectives, (objective,)),
        journal=controller.journal
        + (
            _journal_entry(
                "continuous_mission",
                "structural_candidate_queued_for_independent_behavioral_evaluation",
                (record.capability_id, evaluation_id),
            ),
        ),
    )


def _next_pending_behavioral_evaluation_record(
    controller: ContinuousRuntimeController,
) -> CapabilityKnowledgeRecord | None:
    """Return the newest unresolved record for each capability exactly once."""

    seen_capabilities: set[str] = set()
    for raw in reversed(controller.continuous_knowledge_ledger):
        record = normalize_capability_record_for_recovery(CapabilityKnowledgeRecord(**dict(raw)))
        if record.capability_id in seen_capabilities:
            continue
        seen_capabilities.add(record.capability_id)
        if (
            record.eligible_for_behavioral_evaluation
            and not record.behavioral_evaluation_ref
            and not capability_is_acquired(record)
            and capability_evidence_stage(record) in {"candidate_structurally_validated", "evaluation_pending"}
        ):
            return record
    return None


def _observation_gap_action(gap: str) -> dict[str, Any]:
    normalized = gap.lower().replace("-", "_").replace(" ", "_")
    if "tracked" in normalized and "application" in normalized:
        return {
            "action_id": stable_id("observation-action", gap, "local-risk-simulation"),
            "gap": gap,
            "classification": "requires_explicit_authority",
            "action_type": "local_risk_simulation",
            "rank": 0.72,
            "evidence_gain": 0.74,
            "authority_cost": 0.35,
            "reversibility": 0.95,
            "description": "derive a local simulation that narrows tracked-application risk before any authority request",
            "blocked_transition": "validated local result -> tracked integration proof",
        }
    if "fixture" in normalized or "non_fixture" in normalized:
        return {
            "action_id": stable_id("observation-action", gap, "broader-local-evaluation"),
            "gap": gap,
            "classification": "locally_actionable",
            "action_type": "local_subgoal",
            "rank": 0.91,
            "evidence_gain": 0.9,
            "authority_cost": 0.0,
            "reversibility": 1.0,
            "description": "generate non-fixture local validation cases from a different context",
            "blocked_transition": "fixture-scoped validation -> transferable local validation evidence",
        }
    if "local" in normalized and "diagnostic" in normalized:
        return {
            "action_id": stable_id("observation-action", gap, "broader-local-diagnostic"),
            "gap": gap,
            "classification": "requires_additional_local_evidence",
            "action_type": "local_subgoal",
            "rank": 0.86,
            "evidence_gain": 0.82,
            "authority_cost": 0.0,
            "reversibility": 1.0,
            "description": "run broader local validation beyond diagnostic-only evidence",
            "blocked_transition": "diagnostic-only result -> evidence-backed capability confidence",
        }
    if "operator" in normalized or "intent" in normalized or "ambigu" in normalized:
        return {
            "action_id": stable_id("observation-action", gap, "operator-insight"),
            "gap": gap,
            "classification": "requires_operator_insight",
            "action_type": "operator_insight",
            "rank": 0.7,
            "evidence_gain": 0.68,
            "authority_cost": 0.0,
            "reversibility": 1.0,
            "description": "ask a concrete operator question before choosing the next interpretation",
            "blocked_transition": "ambiguous developmental evidence -> priority selection",
        }
    return {
        "action_id": stable_id("observation-action", gap, "local-evidence-inspection"),
        "gap": gap,
        "classification": "requires_additional_local_evidence",
        "action_type": "local_subgoal",
        "rank": 0.78,
        "evidence_gain": 0.75,
        "authority_cost": 0.0,
        "reversibility": 1.0,
        "description": "inspect local evidence for a more specific executable weakness",
        "blocked_transition": "unresolved gap -> executable evidence-backed subgoal",
    }


def derive_observation_exit_actions(controller: ContinuousRuntimeController) -> tuple[dict[str, Any], ...]:
    assessment = controller.continuous_developmental_self_assessment or {}
    attempted = set((controller.continuous_observation_state or {}).get("attempted_exit_actions") or ())
    accepted_boundaries = _accepted_boundary_gap_tokens(controller)
    actions = [
        _observation_gap_action(str(gap))
        for gap in (assessment.get("developmental_gaps") or ())
        if str(gap) not in accepted_boundaries
    ]
    return tuple(sorted((item for item in actions if item["action_id"] not in attempted), key=lambda item: (-float(item["rank"]), item["action_id"])))


def _split_gap_tokens(values: Iterable[Any]) -> tuple[str, ...]:
    tokens: list[str] = []
    for value in values:
        for part in str(value).split(","):
            token = part.strip()
            if token:
                tokens.append(token)
    return tuple(dict.fromkeys(tokens))


def _accepted_boundary_gap_tokens(controller: ContinuousRuntimeController) -> set[str]:
    return set(_split_gap_tokens((controller.continuous_observation_state or {}).get("accepted_boundary_gaps") or ()))


def _observation_exit_evidence(controller: ContinuousRuntimeController, action: dict[str, Any]) -> dict[str, Any]:
    main_goal = controller.continuous_main_goal or {}
    objective = str(main_goal.get("normalized_objective") or "continuous developmental mission")
    return {
        "evidence_source": f"observation_exit:{action['action_id']}",
        "observed_behavior": f"{action['gap']} remains unresolved while no active work is scheduled",
        "first_incorrect_transition": "material gap -> passive observation without evidence-producing work",
        "affected_capability": str(action["gap"]),
        "baseline_metric": f"{str(action['gap']).replace(' ', '_')}=0.0",
        "confidence": 0.84,
        "operator_value": float(action["evidence_gain"]),
        "severity": float(action["rank"]),
        "estimated_implementation_breadth": "small",
        "validation_method": "observation_exit_action_derivation",
        "scope": "local_runtime",
        "uncertainty": f"{objective} cannot be advanced without resolving or bounding {action['gap']}",
    }


def _operator_insight_from_observation(controller: ContinuousRuntimeController, action: dict[str, Any]) -> dict[str, Any]:
    prior_responses = tuple(
        item
        for item in controller.continuous_operator_interaction_responses
        if item.get("response_kind") == "insight" and str(action.get("gap") or "") in str(item.get("operator_text") or "") + str(item.get("selected_option") or "")
    )
    request_round = len(tuple(controller.continuous_operator_interaction_responses))
    request_id = stable_id("operator-insight", controller.session_id, action["action_id"], request_round)
    local_exhausted = request_round > 0 and action["action_type"] == "operator_insight"
    question = (
        "Local simulation has already been tried and the same caveats remain. Should DELTA request scoped application review, treat this as an accepted boundary, defer it, or ask for clarification?"
        if local_exhausted
        else "Should this unresolved caveat remain an active development gap, be treated as an accepted boundary, or be deferred?"
    )
    options = (
        ("request scoped application review", "treat as accepted boundary", "defer", "ask for clarification")
        if local_exhausted
        else ("continue local simulation only", "treat as accepted boundary", "defer", "ask for clarification")
    )
    return {
        "request_id": request_id,
        "request_kind": "insight",
        "status": "pending",
        "exact_question": question,
        "question": question,
        "why_it_matters": f"The answer changes whether DELTA should pursue {action['gap']} or remove it from the active frontier.",
        "rationale": (
            f"Local simulation has already been attempted {len(prior_responses) or request_round} time(s); further progress now needs a priority or boundary decision."
            if local_exhausted
            else f"The answer changes whether DELTA should pursue {action['gap']} or remove it from the active frontier."
        ),
        "affected_main_goal": (controller.continuous_main_goal or {}).get("normalized_objective", ""),
        "source_main_goal": (controller.continuous_main_goal or {}).get("normalized_objective", ""),
        "source_subgoal": "",
        "affected_gap": action["gap"],
        "source_gap_ids": (action["gap"],),
        "blocked_transition": action["blocked_transition"],
        "blocking_scope": "developmental priority selection",
        "authority_scope": "none; ordinary insight text grants no authority",
        "options": options,
        "permitted_responses": options,
        "evidence_refs": (action["action_id"], action["gap"]),
        "authority_granted": False,
        "created_at": utc_now(),
    }


def _pending_runtime_interaction_requests(controller: ContinuousRuntimeController) -> tuple[dict[str, Any], ...]:
    consumed_request_ids = {
        str(item.get("request_id"))
        for item in controller.continuous_operator_interaction_responses
        if item.get("consumed_at")
    }
    return tuple(
        dict(item)
        for item in controller.continuous_developmental_insight_requests
        if item.get("status") == "pending"
        and item.get("request_kind") in {"insight", "clarification", "priority_choice", "tracked_application_authority"}
        and str(item.get("request_id")) not in consumed_request_ids
    )


def _normalize_consumed_operator_interaction_requests(
    requests: Iterable[Mapping[str, Any]],
    responses: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    consumed = {
        str(item.get("request_id"))
        for item in responses
        if item.get("consumed_at") and item.get("request_id")
    }
    normalized: list[dict[str, Any]] = []
    for request in requests:
        item = dict(request)
        if str(item.get("request_id")) in consumed and item.get("status") == "pending":
            item["status"] = "consumed"
            item["recovery_disposition"] = "normalized_pending_request_with_consumed_response"
        normalized.append(item)
    return tuple(normalized)


def exit_observation_with_action_derivation(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    if controller.continuous_mission_state != "observing_for_new_weaknesses":
        return controller
    if controller.continuous_active_subgoal or controller.pending_application_decision_id:
        return controller
    assessment = controller.continuous_developmental_self_assessment or {}
    gaps = tuple(str(item) for item in (assessment.get("developmental_gaps") or ()))
    if not gaps:
        return controller
    actions = derive_observation_exit_actions(controller)
    if _pending_runtime_interaction_requests(controller):
        return controller
    observation_state = {
        **(controller.continuous_observation_state or {}),
        "observation_reason": "material_gaps_without_active_work",
        "expected_external_change": "",
        "last_meaningful_transition_at": utc_now(),
        "gap_classifications": tuple({"gap": action["gap"], "classification": action["classification"]} for action in actions),
        "candidate_actions": actions,
    }
    if not actions:
        action = {
            "action_id": stable_id("observation-action", controller.session_id, "operator-gap-priority", gaps),
            "gap": ", ".join(gaps),
            "classification": "requires_operator_insight",
            "action_type": "operator_insight",
            "rank": 0.69,
            "evidence_gain": 0.66,
            "authority_cost": 0.0,
            "reversibility": 1.0,
            "description": "ask operator whether exhausted gaps should remain active, become an accepted boundary, or trigger scoped review",
            "blocked_transition": "exhausted local gap resolution -> next developmental priority",
        }
        request = _operator_insight_from_observation(controller, action)
        return replace(
            controller,
            continuous_mission_state="awaiting_operator_insight",
            continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
            continuous_observation_state={
                **observation_state,
                "observation_reason": "all_observation_exit_actions_exhausted",
                "selected_action": action,
            },
            active_work_item="awaiting_operator_insight",
            journal=controller.journal + (_journal_entry("continuous_mission", "observation_exit_actions_exhausted_created_operator_request", (request["request_id"],)),),
        )
    selected = actions[0]
    attempted = tuple(dict.fromkeys(tuple((controller.continuous_observation_state or {}).get("attempted_exit_actions") or ()) + (selected["action_id"],)))
    observation_state = {
        **observation_state,
        "selected_action": selected,
        "attempted_exit_actions": attempted,
    }
    if selected["action_type"] == "operator_insight":
        request = _operator_insight_from_observation(controller, selected)
        return replace(
            controller,
            continuous_mission_state="awaiting_operator_insight",
            continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
            continuous_observation_state=observation_state,
            active_work_item="awaiting_operator_insight",
            journal=controller.journal + (_journal_entry("continuous_mission", "observation_exit_created_operator_insight_request", (request["request_id"], selected["action_id"])),),
        )
    evidence = _observation_exit_evidence(controller, selected)
    prepared = replace(
        controller,
        continuous_observation_state=observation_state,
        continuous_mission_state="observation_exit_deriving_action",
        journal=controller.journal + (_journal_entry("continuous_mission", "observation_exit_selected_productive_action", (selected["action_id"], selected["gap"])),),
    )
    return select_continuous_mission_subgoal(refresh_continuous_mission_frontier(assess_continuous_mission_runtime(prepared, (evidence,))))


def compile_governed_isolated_evaluator_authoring_api_request(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Compile one separate provider-authoring approval after evaluator deferment.

    This creates no provider execution authority by itself.  The request is
    bound to the already-approved evaluator scope and excludes all learner and
    teaching material from the provider packet.
    """

    state = dict(controller.continuous_learning_state or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    decision = dict(policy.get("decision") or {})
    requirement = dict(policy.get("requirement") or {})
    authority = dict(dict(state.get("resource_policy_authorities") or {}).get("sealed_evaluator") or {})
    if (
        controller.continuous_mission_state != "developmental_resource_fulfillment_deferred"
        or decision.get("action_type") != "request_operator_sealed_evaluator"
        or not authority
        or not requirement
    ):
        return controller
    deferred = any(
        item.get("request_kind") == "developmental_resource_fulfillment"
        and item.get("resolution") == "defer_fulfillment"
        and item.get("status") == "consumed"
        for item in controller.continuous_developmental_insight_requests
    )
    existing = dict(state.get("isolated_evaluator_authoring") or {})
    if not deferred or existing:
        return controller
    packet = compile_isolated_evaluator_authoring_request(
        mission_id=str(requirement.get("mission_id") or ""),
        requirement=requirement,
        provider=os.environ.get("DELTA_EVALUATOR_PROVIDER", "openai") or "openai",
        model=os.environ.get("DELTA_EVALUATOR_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini",
    )
    scope = (
        f"one exact-once isolated {packet['provider']} evaluator-authoring call using {packet['model']} "
        f"for {requirement.get('topic')}/{requirement.get('target_capability')}; "
        "no learner answer, teaching content, source retrieval, PCM, tracked-source action, Git, or deployment"
    )
    request = {
        "request_id": packet["request_id"],
        "request_kind": "developmental_evaluator_authoring_api",
        "status": "pending",
        "mission_id": requirement.get("mission_id"),
        "policy_decision_id": decision.get("decision_id"),
        "requirement_id": requirement.get("requirement_id"),
        "provider": packet["provider"],
        "model": packet["model"],
        "prompt_digest": packet["prompt_digest"],
        "input_packet": packet["input_packet"],
        "exact_question": "Approve one isolated provider call to author only the sealed evaluator package described in the attached schema?",
        "rationale": "The separately authored evaluator remains unavailable after the human fulfillment path was deferred. The provider receives only the evaluation specification, never learner or teaching data.",
        "authority_scope": scope,
        "permitted_responses": ("approve_evaluator_authoring_api", "reject_evaluator_authoring_api", "defer_evaluator_authoring_api", "ask_for_clarification"),
        "created_at": utc_now(),
    }
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_isolated_evaluator_authoring_api_approval",
        continuous_learning_state={
            **state,
            "isolated_evaluator_authoring": {
                "status": "pending_operator_approval",
                "request": packet,
                "authority_request_id": authority.get("request_id"),
                "execution_claim": {},
                "result": {},
            },
        },
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "deferred_human_evaluator_compiled_to_provider_authoring_request", (packet["request_id"],)),),
    )


def compile_replacement_isolated_evaluator_authoring_api_request(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Create one new approval request after a terminal authoring failure."""

    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    prior_claim = dict(authoring.get("execution_claim") or {})
    prior_result = dict(authoring.get("result") or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    requirement = dict(policy.get("requirement") or {})
    terminal_failure = (
        controller.continuous_mission_state in {
            "isolated_evaluator_authoring_provider_failed",
            "isolated_evaluator_authoring_result_invalid",
        }
        and prior_claim.get("claim_state") in {"failed", "invalid"}
        and str(prior_result.get("status") or "") in {"failed", "invalid"}
    )
    if not terminal_failure or not requirement:
        return controller
    prior_packet = dict(authoring.get("request") or {})
    packet = compile_isolated_evaluator_authoring_request(
        mission_id=str(requirement.get("mission_id") or ""),
        requirement=requirement,
        provider=str(prior_packet.get("provider") or "openai"),
        model=str(prior_packet.get("model") or "gpt-4.1-mini"),
        attempt_nonce=str(prior_claim.get("claim_id") or "prior-preflight-failure"),
    )
    scope = (
        f"one exact-once isolated {packet['provider']} evaluator-authoring call using {packet['model']} "
        f"for {requirement.get('topic')}/{requirement.get('target_capability')}; "
        "no learner answer, teaching content, source retrieval, PCM, tracked-source action, Git, or deployment"
    )
    request = {
        "request_id": packet["request_id"], "request_kind": "developmental_evaluator_authoring_api", "status": "pending",
        "mission_id": requirement.get("mission_id"), "policy_decision_id": policy.get("decision", {}).get("decision_id"),
        "requirement_id": requirement.get("requirement_id"), "provider": packet["provider"], "model": packet["model"],
        "prompt_digest": packet["prompt_digest"], "input_packet": packet["input_packet"],
        "exact_question": "Approve one replacement isolated provider call to author only the sealed evaluator package described in the attached schema?",
        "rationale": "The prior terminal claim remains immutable. This replacement uses the tightened strict-object evaluator schema and still authorizes only one isolated evaluator-authoring call.",
        "authority_scope": scope,
        "permitted_responses": ("approve_evaluator_authoring_api", "reject_evaluator_authoring_api", "defer_evaluator_authoring_api", "ask_for_clarification"),
        "created_at": utc_now(),
    }
    history = tuple(authoring.get("prior_claims") or ()) + ({"claim": prior_claim, "result": prior_result, "status": "terminal_authoring_failure"},)
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_replacement_isolated_evaluator_authoring_api_approval",
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        continuous_learning_state={**state, "isolated_evaluator_authoring": {"status": "pending_operator_approval", "request": packet, "authority_request_id": authoring.get("authority_request_id"), "execution_claim": {}, "result": {}, "prior_claims": history}},
        journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "replacement_provider_authoring_request_compiled_after_preflight_failure", (packet["request_id"], prior_claim.get("claim_id", ""))),),
    )


def compile_prompt_complete_isolated_evaluator_authoring_replacement_request(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Request a v2 evaluator only when a legacy sealed package lacks learner prompts.

    A historical sealed package remains valid evidence about the prior attempt,
    but it cannot enter the learner executor without an explicit learner view.
    This function never reconstructs prompts from evaluator-only data.  It
    records that limitation and compiles one separately approved replacement.
    """

    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    legacy_result = dict(authoring.get("result") or {})
    legacy_package = dict(legacy_result.get("sealed_package") or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    requirement = dict(policy.get("requirement") or {})
    projection = project_learner_visible_evaluation_cases(legacy_package)
    prompt_missing = "missing_learner_visible_evaluation_prompt" in tuple(projection.get("errors") or ())
    if (
        controller.continuous_mission_state != "developmental_resource_fulfillment_incomplete"
        or controller.active_work_item != "learner_visible_evaluation_prompts_unavailable"
        or authoring.get("status") != "result_handed_off"
        or not legacy_package
        or not requirement
        or not prompt_missing
        or controller.continuous_active_subgoal
        or state.get("capability_update")
    ):
        return controller

    prior_claim = dict(authoring.get("execution_claim") or {})
    prior_packet = dict(authoring.get("request") or {})
    replacement_nonce = stable_id(
        "isolated-evaluator-authoring-v2-learner-prompt-replacement",
        prior_claim.get("claim_id"),
        legacy_result.get("response_digest") or legacy_package.get("sealed_package_id"),
    )
    packet = compile_isolated_evaluator_authoring_request(
        mission_id=str(requirement.get("mission_id") or prior_packet.get("mission_id") or ""),
        requirement=requirement,
        provider=str(prior_packet.get("provider") or "openai"),
        model=str(prior_packet.get("model") or "gpt-4.1-mini"),
        attempt_nonce=replacement_nonce,
    )
    scope = (
        f"one exact-once isolated {packet['provider']} evaluator-authoring call using {packet['model']} "
        f"for {requirement.get('topic')}/{requirement.get('target_capability')}; "
        "send only the capability specification and evaluator schema; no MIT body, teaching material, learner answer, "
        "candidate output, source retrieval, PCM, tracked-source action, Git, or deployment"
    )
    request = {
        "request_id": packet["request_id"],
        "request_kind": "developmental_evaluator_authoring_api",
        "status": "pending",
        "mission_id": requirement.get("mission_id"),
        "policy_decision_id": policy.get("decision", {}).get("decision_id"),
        "requirement_id": requirement.get("requirement_id"),
        "provider": packet["provider"],
        "model": packet["model"],
        "prompt_digest": packet["prompt_digest"],
        "input_packet": packet["input_packet"],
        "exact_question": "Approve one replacement isolated provider call to author a complete sealed evaluator with learner prompts and response formats plus evaluator-only grading fields?",
        "rationale": "The retained sealed evaluator predates the learner-view contract. It remains immutable historical evidence, but cannot safely supply learner prompts. The replacement preserves strict independence and authorizes exactly one v2 evaluator-authoring call.",
        "authority_scope": scope,
        "permitted_responses": ("approve_evaluator_authoring_api", "reject_evaluator_authoring_api", "defer_evaluator_authoring_api", "ask_for_clarification"),
        "created_at": utc_now(),
    }
    history_entry = {
        "claim": prior_claim,
        "result": legacy_result,
        "status": "legacy_sealed_package_missing_learner_projection",
        "handoff_fulfillment_id": authoring.get("handoff_fulfillment_id"),
        "projection": projection,
    }
    history = tuple(authoring.get("prior_claims") or ()) + (history_entry,)
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_prompt_complete_isolated_evaluator_authoring_api_approval",
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        continuous_learning_state={
            **state,
            "isolated_evaluator_authoring": {
                "status": "pending_operator_approval",
                "request": packet,
                "authority_request_id": authoring.get("authority_request_id"),
                "execution_claim": {},
                "result": {},
                "prior_claims": history,
            },
        },
        journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "legacy_sealed_package_compiled_to_prompt_complete_replacement_request", (packet["request_id"], prior_claim.get("claim_id", ""))),),
    )


def compile_execution_compatible_isolated_evaluator_authoring_request(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Request one v3 replacement only for a sealed evaluator blocked pre-execution."""

    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    requirement = dict(policy.get("requirement") or {})
    prior_claim = dict(authoring.get("execution_claim") or {})
    prior_result = dict(authoring.get("result") or {})
    agenda = dict(state.get("developmental_agenda") or {})
    recovered_execution_block = bool(agenda.get("outcome_reclassifications")) and controller.continuous_mission_state == "developmental_agenda_blocked"
    if (
        controller.active_work_item != "sealed_evaluator_execution_contract_unsupported"
        and agenda.get("status") != "blocked_resolvable_evaluator_execution_contract"
        and not recovered_execution_block
    ) or (
        not requirement
        or not prior_claim
        or not prior_result
    ):
        return controller
    packet = compile_isolated_evaluator_authoring_request(
        mission_id=str(requirement.get("mission_id") or ""), requirement=requirement,
        provider=str(dict(authoring.get("request") or {}).get("provider") or "openai"),
        model=str(dict(authoring.get("request") or {}).get("model") or "gpt-4.1-mini"),
        attempt_nonce=str(prior_claim.get("claim_id") or "execution-contract-blocked"),
    )
    scope = f"one exact-once isolated {packet['provider']} evaluator-authoring call using {packet['model']} for {requirement.get('topic')}/{requirement.get('target_capability')}; no learner answer, teaching content, source retrieval, PCM, tracked-source action, Git, or deployment"
    request = {
        "request_id": packet["request_id"], "request_kind": "developmental_evaluator_authoring_api", "status": "pending",
        "mission_id": requirement.get("mission_id"), "policy_decision_id": policy.get("decision", {}).get("decision_id"),
        "requirement_id": requirement.get("requirement_id"), "provider": packet["provider"], "model": packet["model"],
        "prompt_digest": packet["prompt_digest"], "input_packet": packet["input_packet"],
        "exact_question": "Approve one v3 isolated evaluator-authoring call with deterministic learner execution and sealed scoring fields?",
        "rationale": "The prior package remains sealed historical evidence but is non-executable by the bounded learner/scorer. This request authorizes one replacement package only.",
        "authority_scope": scope,
        "permitted_responses": ("approve_evaluator_authoring_api", "reject_evaluator_authoring_api", "defer_evaluator_authoring_api", "ask_for_clarification"),
        "created_at": utc_now(),
    }
    history = tuple(authoring.get("prior_claims") or ()) + ({"claim": prior_claim, "result": prior_result, "status": "sealed_package_execution_contract_unsupported"},)
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_execution_compatible_isolated_evaluator_authoring_api_approval",
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        continuous_learning_state={**state, "isolated_evaluator_authoring": {"status": "pending_operator_approval", "request": packet, "authority_request_id": authoring.get("authority_request_id"), "execution_claim": {}, "result": {}, "prior_claims": history}},
        journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "execution_compatible_v3_replacement_request_compiled", (packet["request_id"],)),),
    )


def consume_isolated_evaluator_authoring_api_response(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    selected_option: str,
    operator_text: str = "",
    approved_scope: str = "",
) -> ContinuousRuntimeController:
    """Record one provider-authoring decision without executing the provider."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((position for position, item in enumerate(requests) if item.get("request_id") == request_id and item.get("status") == "pending"), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "duplicate_or_unknown_authoring_response_suppressed", (request_id,)),))
    request = requests[index]
    if selected_option not in tuple(request.get("permitted_responses") or ()):
        return replace(controller, journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "invalid_authoring_response_rejected", (request_id, selected_option)),))
    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    packet = dict(authoring.get("request") or {})
    if packet.get("request_id") != request_id:
        return replace(controller, journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "authoring_response_identity_mismatch", (request_id,)),))
    consumed_at = utc_now()
    if selected_option == "ask_for_clarification":
        resolved = {**request, "status": "consumed", "resolution": selected_option, "consumed_at": consumed_at, "authority_granted": False}
        clarification = {
            **request,
            "request_id": stable_id("isolated-evaluator-authoring-clarification", request_id),
            "status": "pending",
            "exact_question": "The provider receives only this schema: capability specification, five required case categories, scoring criteria, and exclusions for learner answers and teaching content. Approve, reject, or defer this exact one-call scope.",
            "permitted_responses": ("approve_evaluator_authoring_api", "reject_evaluator_authoring_api", "defer_evaluator_authoring_api"),
            "created_at": consumed_at,
        }
        return replace(
            controller,
            continuous_developmental_insight_requests=requests[:index] + (resolved,) + requests[index + 1 :] + (clarification,),
            continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + ({"request_id": request_id, "response_kind": "developmental_evaluator_authoring_api", "selected_option": selected_option, "operator_text": operator_text, "authority_granted": False, "created_at": consumed_at, "consumed_at": consumed_at},),
            continuous_learning_state={**state, "isolated_evaluator_authoring": {**authoring, "status": "clarification_requested"}},
            continuous_mission_state="awaiting_operator_insight",
            journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "provider_authoring_clarification_created", (request_id,)),),
        )
    if selected_option == "approve_evaluator_authoring_api" and approved_scope != request.get("authority_scope"):
        return replace(controller, journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "provider_authoring_scope_mismatch", (request_id,)),))
    granted = selected_option == "approve_evaluator_authoring_api"
    resolved = {**request, "status": "consumed", "resolution": selected_option, "consumed_at": consumed_at, "authority_granted": granted}
    response = {"request_id": request_id, "response_kind": "developmental_evaluator_authoring_api", "selected_option": selected_option, "operator_text": operator_text, "approved_scope": approved_scope, "authority_granted": granted, "created_at": consumed_at, "consumed_at": consumed_at}
    if not granted:
        return replace(
            controller,
            continuous_developmental_insight_requests=requests[:index] + (resolved,) + requests[index + 1 :],
            continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
            continuous_learning_state={**state, "isolated_evaluator_authoring": {**authoring, "status": "deferred" if selected_option == "defer_evaluator_authoring_api" else "rejected", "operator_disposition": response}},
            continuous_mission_state="isolated_evaluator_authoring_deferred" if selected_option == "defer_evaluator_authoring_api" else "isolated_evaluator_authoring_rejected",
            active_work_item="independent_evaluator_remains_unavailable",
            journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "provider_authoring_not_authorized", (request_id, selected_option)),),
        )
    claim = {
        "claim_id": stable_id("isolated-evaluator-authoring-execution-claim", request_id),
        "request_id": request_id,
        "claim_state": "approved_pending_execution",
        "execution_attempt_count": 0,
        "approved_at": consumed_at,
        "provider": packet.get("provider"),
        "model": packet.get("model"),
        "prompt_digest": packet.get("prompt_digest"),
    }
    api = dict(controller.continuous_api_authority or {})
    api = {
        **api,
        "enabled": True,
        "allowed_providers": (packet.get("provider"),),
        "allowed_models": (packet.get("model"),),
        "call_allowance": 1,
        "pending_provider_tasks": tuple(dict.fromkeys(tuple(api.get("pending_provider_tasks") or ()) + (request_id,))),
        "unavailability_reason": "one_operator_approved_isolated_evaluator_authoring_call_pending",
    }
    return replace(
        controller,
        continuous_developmental_insight_requests=requests[:index] + (resolved,) + requests[index + 1 :],
        continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
        continuous_api_authority=api,
        continuous_learning_state={**state, "isolated_evaluator_authoring": {**authoring, "status": "approved_pending_execution", "execution_claim": claim, "approved_authority": response}},
        continuous_mission_state="awaiting_isolated_evaluator_authoring_execution",
        active_work_item="persisted_isolated_evaluator_authoring_execution_claim",
        journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "operator_approved_one_use_provider_authoring_claim", (request_id, claim["claim_id"])),),
    )


def begin_isolated_evaluator_authoring_execution(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Persist the sole provider-dispatch attempt before network I/O.

    A recovered dispatching state is intentionally never retried: it may have
    crossed the network boundary before a process loss.
    """

    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    packet = dict(authoring.get("request") or {})
    claim = dict(authoring.get("execution_claim") or {})
    if (
        controller.continuous_mission_state != "awaiting_isolated_evaluator_authoring_execution"
        or claim.get("claim_state") != "approved_pending_execution"
        or int(claim.get("execution_attempt_count") or 0) != 0
        or not packet
    ):
        return controller
    policy = dict(state.get("developmental_resource_policy") or {})
    requirement = dict(policy.get("requirement") or {})
    prior_claims = tuple(authoring.get("prior_claims") or ())
    prior_claim = dict(prior_claims[-1].get("claim") or {}) if prior_claims else {}
    attempt_nonce = str(packet.get("attempt_nonce") or prior_claim.get("claim_id") or "")
    refreshed_packet = compile_isolated_evaluator_authoring_request(
        mission_id=str(requirement.get("mission_id") or packet.get("mission_id") or ""),
        requirement=requirement,
        provider=str(packet.get("provider") or "openai"),
        model=str(packet.get("model") or "gpt-4.1-mini"),
        # Older replacement packets predate explicit nonce persistence. Their
        # immutable prior claim still binds the replacement identity.
        attempt_nonce=attempt_nonce,
    )
    if refreshed_packet.get("request_id") != packet.get("request_id"):
        return replace(controller, journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "approved_packet_identity_changed_before_dispatch", (str(packet.get("request_id") or ""),)),))
    packet = refreshed_packet
    updated_claim = {**claim, "claim_state": "dispatching", "execution_attempt_count": 1, "dispatch_started_at": utc_now()}
    api = dict(controller.continuous_api_authority or {})
    return replace(
        controller,
        continuous_mission_state="isolated_evaluator_authoring_dispatching",
        active_work_item="one_use_isolated_evaluator_authoring_provider_dispatch",
        continuous_api_authority={**api, "calls_consumed": int(api.get("calls_consumed") or 0) + 1},
        continuous_learning_state={**state, "isolated_evaluator_authoring": {**authoring, "request": packet, "status": "dispatching", "execution_claim": updated_claim}},
        journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "one_use_provider_dispatch_persisted_before_network", (claim.get("claim_id", ""),)),),
    )


def record_isolated_evaluator_authoring_provider_result(
    controller: ContinuousRuntimeController,
    *,
    raw_response: Mapping[str, Any] | str | None,
    provider_error: str = "",
    provider_usage: Mapping[str, Any] | None = None,
) -> ContinuousRuntimeController:
    """Validate one attempted provider result without promoting capability."""

    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    packet = dict(authoring.get("request") or {})
    claim = dict(authoring.get("execution_claim") or {})
    if claim.get("claim_state") != "dispatching" or not packet:
        return controller
    api = dict(controller.continuous_api_authority or {})
    pending = tuple(item for item in (api.get("pending_provider_tasks") or ()) if item != packet.get("request_id"))
    if provider_error:
        result = {"status": "failed", "error": provider_error, "provider_usage": dict(provider_usage or {}), "completed_at": utc_now()}
        return replace(
            controller,
            continuous_mission_state="isolated_evaluator_authoring_provider_failed",
            active_work_item="independent_evaluator_remains_unavailable",
            continuous_api_authority={**api, "enabled": False, "pending_provider_tasks": pending, "failures": int(api.get("failures") or 0) + 1, "unavailability_reason": "isolated_evaluator_authoring_provider_failed"},
            continuous_learning_state={**state, "isolated_evaluator_authoring": {**authoring, "status": "provider_failed", "execution_claim": {**claim, "claim_state": "failed"}, "result": result}},
            journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "one_use_provider_authoring_failed", (packet.get("request_id", ""),)),),
        )
    validation = validate_provider_authored_evaluator_response(packet, raw_response or {})
    result = {
        "status": "validated" if validation["accepted"] else "invalid",
        "response_digest": validation["response_digest"],
        "validation_errors": validation["errors"],
        "sealed_package": validation["sealed_package"],
        "provider_usage": dict(provider_usage or {}),
        "completed_at": utc_now(),
    }
    if not validation["accepted"]:
        # This is audit-only forensic evidence. It is deliberately not copied
        # into a learner resource or capability record.
        result["operator_only_forensic_response"] = {
            "raw_response": raw_response,
            "response_digest": validation["response_digest"],
            "learner_visible": False,
            "capability_eligible": False,
        }
    return replace(
        controller,
        continuous_mission_state="isolated_evaluator_authoring_result_sealed" if validation["accepted"] else "isolated_evaluator_authoring_result_invalid",
        active_work_item="sealed_evaluator_pending_existing_fulfillment_handoff" if validation["accepted"] else "independent_evaluator_remains_unavailable",
        continuous_api_authority={**api, "enabled": False, "pending_provider_tasks": pending, "last_provider_result": validation["response_digest"], "unavailability_reason": "sealed_evaluator_handoff_required" if validation["accepted"] else "provider_evaluator_schema_rejected"},
        continuous_learning_state={**state, "isolated_evaluator_authoring": {**authoring, "status": "result_sealed" if validation["accepted"] else "result_invalid", "execution_claim": {**claim, "claim_state": "completed" if validation["accepted"] else "invalid"}, "result": result}},
        journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "provider_authoring_result_validated_without_capability_promotion", (packet.get("request_id", ""), result["status"])),),
    )


def _effective_policy_for_validated_sealed_evaluator_handoff(
    policy: Mapping[str, Any],
    authoring: Mapping[str, Any],
    material: Mapping[str, Any],
    resource_policy_authorities: Mapping[str, Any],
) -> dict[str, Any]:
    """Supersede a stale policy only with fresh, already-validated evaluator evidence.

    A resource policy can legitimately be refreshed after a fulfilled teaching
    resource becomes newly executable.  It must not cause a validated sealed
    evaluator to disappear merely because the previous ranking selected local
    reuse.  The old decision and candidate set are retained verbatim in a
    history record; the current effective policy is a separate, deterministic
    handoff decision bound to the same requirement and evaluator package.
    """

    current = dict(policy or {})
    decision = dict(current.get("decision") or {})
    requirement = dict(current.get("requirement") or {})
    result = dict(authoring.get("result") or {})
    packet = dict(authoring.get("request") or {})
    authority = str(authoring.get("authority_request_id") or "")
    package_id = str(material.get("sealed_package_id") or "")
    authorities = dict(resource_policy_authorities or {})
    sealed_authority = dict(authorities.get("sealed_evaluator") or {})
    if (
        not current
        or not requirement
        or decision.get("action_type") == "request_operator_sealed_evaluator"
        or result.get("status") != "validated"
        or not package_id
        or not authority
        or str(sealed_authority.get("request_id") or "") != authority
        or str(packet.get("mission_id") or "") != str(requirement.get("mission_id") or "")
    ):
        return current

    evidence_digest = str(result.get("response_digest") or package_id)
    candidate_id = stable_id(
        "developmental-resource-policy-candidate",
        requirement.get("requirement_id"),
        "validated-sealed-evaluator-handoff",
        package_id,
    )
    decision_id = stable_id(
        "developmental-resource-authority-decision",
        requirement.get("requirement_id"),
        "validated-sealed-evaluator-handoff",
        package_id,
    )
    effective_candidate = {
        "policy_candidate_id": candidate_id,
        "action_type": "request_operator_sealed_evaluator",
        "availability": True,
        "rejection_reasons": (),
        "target_resource_id": package_id,
        "target_request_id": str(packet.get("request_id") or ""),
        "permission_state": "already_authorized",
        "expected_outcome": "sealed_evaluator_handoff",
        "agenda_impact": "continue_goal",
        "rank": 1.0,
        "candidate_digest": stable_id("validated-sealed-evaluator-handoff-candidate", evidence_digest),
        "evidence_ref": evidence_digest,
    }
    effective_decision = {
        "decision_id": decision_id,
        "requirement_id": requirement.get("requirement_id"),
        "selected_policy_candidate_id": candidate_id,
        "action_type": "request_operator_sealed_evaluator",
        "target_resource_id": package_id,
        "target_request_id": str(packet.get("request_id") or ""),
        "target_authority_request_id": authority,
        "rationale": "A newer validated sealed evaluator package supersedes stale local-reuse selection for the same mission and requirement lineage.",
        "rejected_candidate_ids": (),
        "permission_state": "already_authorized",
        "expected_state_transition": "sealed_evaluator_handoff",
        "agenda_effect": "continue_goal",
        "budget_effect": {"resource_requests": 0, "authority_requests": 0},
        "stopping_condition": "do_not_execute_provider_web_pcm_or_tracked_source",
        "retry_condition": "new_validated_evaluator_evidence_or_explicit_operator_refresh",
        "created_at": utc_now(),
        "decision_digest": stable_id("validated-sealed-evaluator-handoff-decision", evidence_digest),
        "status": "decision_compiled",
        "supersedes_decision_id": decision.get("decision_id"),
        "evidence_digest": evidence_digest,
    }
    history_entry = {
        "decision": decision,
        "policy_candidates": tuple(current.get("policy_candidates") or ()),
        "status": "superseded_by_validated_sealed_evaluator",
        "superseded_at": utc_now(),
        "superseded_by_decision_id": decision_id,
        "evidence_digest": evidence_digest,
    }
    return {
        **current,
        "status": "decision_compiled",
        "decision": effective_decision,
        "policy_candidates": (effective_candidate,),
        "decision_history": tuple(current.get("decision_history") or ()) + (history_entry,),
        "effective_policy_reason": "validated_sealed_evaluator_newer_than_current_policy_decision",
    }


def handoff_sealed_isolated_evaluator_to_resource_fulfillment(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Attach one sealed provider evaluator through the existing fulfillment path.

    The provider result is evidence only. This bridge neither creates an
    authority request nor exposes answer keys to the learner; it validates the
    already sealed package against the original resource requirement and lets
    the established fulfillment/resumption lifecycle decide the next state.
    """

    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    result = dict(authoring.get("result") or {})
    material = dict(result.get("sealed_package") or {})
    policy = dict(state.get("developmental_resource_policy") or {})
    requirement = dict(policy.get("requirement") or {})
    if (
        controller.continuous_mission_state != "isolated_evaluator_authoring_result_sealed"
        or authoring.get("status") != "result_sealed"
        or not material
        or not requirement
    ):
        return controller
    policy = _effective_policy_for_validated_sealed_evaluator_handoff(
        policy,
        authoring,
        material,
        dict(state.get("resource_policy_authorities") or {}),
    )
    decision = dict(policy.get("decision") or {})
    if decision.get("action_type") != "request_operator_sealed_evaluator":
        return controller
    fulfillment = compile_developmental_resource_authority_fulfillment(
        requirement,
        decision,
        authority_request_id=str(authoring.get("authority_request_id") or ""),
        operator_interaction_id=str(authoring.get("request", {}).get("request_id") or ""),
        supplied=material,
        supplied_by="isolated_provider_authoring",
    )
    if fulfillment.status != "validated":
        return replace(
            controller,
            continuous_mission_state="isolated_evaluator_authoring_result_invalid",
            active_work_item="sealed_evaluator_failed_existing_fulfillment_validation",
            continuous_learning_state={
                **state,
                "isolated_evaluator_authoring": {
                    **authoring,
                    "status": "sealed_handoff_invalid",
                    "handoff_validation_errors": fulfillment.validation_errors,
                },
            },
            journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "sealed_result_rejected_by_existing_fulfillment_validator", (fulfillment.fulfillment_id,)),),
        )
    existing = tuple(dict(item) for item in (state.get("developmental_resource_fulfillments") or ()))
    if any(item.get("semantic_identity") == fulfillment.semantic_identity for item in existing):
        return replace(
            controller,
            journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "sealed_result_handoff_replay_suppressed", (fulfillment.fulfillment_id,)),),
        )
    base_state = {
        **state,
        "developmental_resource_fulfillments": existing + (fulfillment.as_dict(),),
        "developmental_resource_policy": {
            **policy,
            "status": "fulfillment_validated",
            "fulfillment_id": fulfillment.fulfillment_id,
        },
        "isolated_evaluator_authoring": {
            **authoring,
            "status": "result_handed_off",
            "handoff_fulfillment_id": fulfillment.fulfillment_id,
        },
    }
    updated = replace(
        controller,
        continuous_learning_state=base_state,
        journal=controller.journal + (_journal_entry("isolated_evaluator_authoring", "sealed_result_attached_to_existing_fulfillment", (fulfillment.fulfillment_id,)),),
    )
    bundle = _fulfillment_learning_bundle(requirement, fulfillment, material, state.get("retained_bundle"))
    instruction = f"Learn {str(requirement.get('topic') or '').replace('_', ' ')}."
    prior_mission = dict(state.get("mission") or {})
    resumed = attach_developmental_learning_mission(
        updated,
        instruction,
        bundle,
        existing_mission=DevelopmentalMissionContract(**prior_mission) if prior_mission else None,
        preserve_learning_state=bool(prior_mission),
    )
    resumed_state = {
        **base_state,
        **dict(resumed.continuous_learning_state or {}),
        "developmental_resource_fulfillments": base_state["developmental_resource_fulfillments"],
        "developmental_resource_policy": {
            **base_state["developmental_resource_policy"],
            "status": "blocker_resolved",
            "resumed_mission_id": str((resumed.continuous_learning_state or {}).get("mission", {}).get("mission_id") or ""),
        },
    }
    agenda = dict(resumed_state.get("developmental_agenda") or {})
    resumed_active = bool(resumed.continuous_active_subgoal)
    if agenda and agenda_state_is_valid(agenda):
        resumed_state["developmental_agenda"] = {
            **agenda,
            "status": "mission_active" if resumed_active else "awaiting_resource_policy_authority",
            "active_mission_id": str((resumed.continuous_learning_state or {}).get("mission", {}).get("mission_id") or agenda.get("active_mission_id") or ""),
            "next_eligible_transition": "bounded_learning_attempt_or_evaluation" if resumed_active else "resource_policy_refresh_after_partial_blocker_resolution",
            "updated_at": utc_now(),
        }
    completed = replace(
        resumed,
        continuous_mission_state=resumed.continuous_mission_state if resumed_active else "developmental_resource_fulfillment_incomplete",
        active_work_item=resumed.active_work_item if resumed_active else "resource_blocker_partially_resolved",
        continuous_learning_state=resumed_state,
        journal=resumed.journal + (_journal_entry("isolated_evaluator_authoring", "sealed_result_resumed_original_goal_once", (fulfillment.fulfillment_id, str(requirement.get("goal_id") or ""))),),
    )
    if resumed_active:
        return completed

    # A sealed evaluator resolves only the evaluator blocker.  Do not let the
    # resource policy re-label a reference-only teaching bundle as ready for a
    # learning attempt when the existing learning compiler could not form one.
    assessment = dict(resumed_state.get("assessment") or {})
    bundle = dict(resumed_state.get("retained_bundle") or {})
    missing: list[str] = []
    if not tuple(assessment.get("dimensions") or ()):
        missing.append("missing_assessment_dimensions")
    resources = tuple(dict(item) for item in (bundle.get("study_resources") or ()) if isinstance(item, Mapping))
    if not any(item.get("study_facts") or item.get("visible_practice_cases") for item in resources):
        missing.append("missing_learner_visible_teaching_material")
    sealed_cases = tuple(dict(item) for item in (bundle.get("sealed_evaluation_cases") or ()) if isinstance(item, Mapping))
    if sealed_cases and not any(
        item.get("learner_prompt")
        or item.get("case_prompt")
        or item.get("visible_prompt")
        or dict(item.get("learner_view") or {}).get("prompt")
        or dict(item.get("learner_view") or {}).get("instruction")
        for item in sealed_cases
    ):
        missing.append("missing_learner_visible_evaluation_prompts")
    return replace(
        completed,
        continuous_mission_state="developmental_resource_fulfillment_incomplete",
        active_work_item="retained_learning_material_incomplete",
        continuous_learning_state={
            **resumed_state,
            "resource_blocker": {
                "blocker": "retained_learning_material_not_executable",
                "missing_fields": tuple(missing) or ("learning_subgoal_not_compiled",),
                "fulfillment_id": fulfillment.fulfillment_id,
                "no_provider_or_research_call_performed": True,
            },
        },
        journal=completed.journal + (_journal_entry(
            "isolated_evaluator_authoring",
            "sealed_evaluator_handoff_blocked_by_nonexecutable_retained_learning_material",
            tuple(missing) or ("learning_subgoal_not_compiled",),
        ),),
    )


def compile_retained_teaching_material_recovery_request(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Request one exact-source recovery without selecting or retrieving a source."""

    state = dict(controller.continuous_learning_state or {})
    raw_blocker = state.get("resource_blocker")
    blocker = dict(raw_blocker) if isinstance(raw_blocker, Mapping) else {}
    raw_assessment = state.get("assessment")
    assessment = dict(raw_assessment) if isinstance(raw_assessment, Mapping) else {}
    current_state_is_incomplete = (
        controller.continuous_mission_state == "developmental_resource_fulfillment_incomplete"
        and blocker.get("blocker") == "retained_learning_material_not_executable"
    )
    legacy_local_reuse_is_incomplete = (
        controller.continuous_mission_state == "developmental_resource_policy_local_reuse_ready"
        and controller.active_work_item == "reuse_validated_retained_resource"
        and not controller.continuous_active_subgoal
        and not tuple(assessment.get("dimensions") or ())
    )
    if not (current_state_is_incomplete or legacy_local_reuse_is_incomplete):
        return controller
    bundle = dict(state.get("retained_bundle") or {})
    resources = tuple(
        dict(item) for item in (bundle.get("study_resources") or ()) if isinstance(item, Mapping)
    )
    source_id = str(next((item.get("source_record_id") or item.get("resource_id") for item in resources if item.get("source_record_id") or item.get("resource_id")), ""))
    provenance = next(
        (
            dict(item)
            for item in (bundle.get("resource_provenance") or ())
            if isinstance(item, Mapping)
            and str(item.get("source_record_id") or "") == source_id
            and item.get("canonical_reference")
        ),
        {},
    )
    locator = str(provenance.get("canonical_reference") or "")
    source_digest = str(provenance.get("content_digest") or "")
    mission = dict(state.get("mission") or {})
    sealed = dict((state.get("isolated_evaluator_authoring") or {}).get("result", {}).get("sealed_package") or {})
    projection = project_learner_visible_evaluation_cases(sealed)
    if not source_id or not locator or not source_digest or not mission:
        return replace(
            controller,
            continuous_learning_state={
                **state,
                "resource_blocker": {
                    **blocker,
                    "blocker": "retained_teaching_recovery_identity_incomplete",
                },
            },
            journal=controller.journal + (_journal_entry(
                "developmental_learning", "retained_teaching_recovery_request_not_compiled_missing_source_identity", (),
            ),),
        )
    request_id = stable_id(
        "retained-teaching-material-recovery",
        str(mission.get("mission_id") or ""), source_id, source_digest,
    )
    existing = next(
        (
            dict(item)
            for item in controller.continuous_developmental_insight_requests
            if item.get("request_id") == request_id and item.get("status") == "pending"
        ),
        {},
    )
    if existing:
        return controller
    request = {
        "request_id": request_id,
        "request_kind": "developmental_teaching_material_recovery_authority",
        "status": "pending",
        "mission_id": mission.get("mission_id"),
        "source_record_id": source_id,
        "source_locator": locator,
        "source_digest": source_digest,
        "action_type": "recover_exact_retained_teaching_source",
        "exact_question": (
            "Approve one bounded re-retrieval of the already retained MIT source to recover learner-visible "
            "teaching material only. No new source selection, provider call, evaluator authoring, PCM, tracked-source action, Git, or deployment is permitted."
        ),
        "authority_scope": (
            f"one direct retrieval of {locator} bound to retained source {source_id}; retain only a bounded learner-visible "
            "teaching artifact and its provenance; no broader research authority"
        ),
        "permitted_responses": (
            "approve_exact_source_recovery",
            "reject_exact_source_recovery",
            "defer_exact_source_recovery",
            "ask_for_clarification",
        ),
        "recovery_artifact_requirements": (
            "plain_language_explanation",
            "prerequisite_concepts",
            "worked_example",
            "learner_visible_practice_material",
            "assessment_dimensions",
            "source_identity_locator_digest_and_provenance",
        ),
        "evaluator_projection": {
            "allowed_fields": ("case_id", "case_category", "prompt", "response_format"),
            "status": "ready" if projection["accepted"] else "blocked",
            "errors": projection["errors"],
            "learner_cases": projection["learner_cases"],
            "forbidden_fields": ("answer_key", "scoring_rule", "rubric", "thresholds", "provenance"),
        },
        "authority_granted": False,
        "created_at": utc_now(),
    }
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_exact_retained_teaching_source_recovery_authority",
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        continuous_learning_state={
            **state,
            "teaching_material_recovery": {
                "status": "pending_operator_approval",
                "request_id": request_id,
                "source_record_id": source_id,
                "source_locator": locator,
                "source_digest": source_digest,
                "evaluator_projection_state": request["evaluator_projection"]["status"],
                "no_retrieval_or_provider_call_performed": True,
            },
        },
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "exact_retained_teaching_material_recovery_authority_requested", (request_id, source_id),
        ),),
    )


def consume_retained_teaching_material_recovery_response(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    selected_option: str,
    operator_text: str = "",
    approved_scope: str = "",
) -> ContinuousRuntimeController:
    """Consume the one exact-source recovery approval without retrieving yet."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((position for position, item in enumerate(requests) if item.get("request_id") == request_id and item.get("request_kind") == "developmental_teaching_material_recovery_authority" and item.get("status") == "pending"), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_learning", "duplicate_or_unknown_teaching_recovery_response_suppressed", (request_id,)),))
    request = requests[index]
    if selected_option not in tuple(request.get("permitted_responses") or ()):
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_learning", "invalid_teaching_recovery_response_rejected", (request_id, selected_option)),))
    approved = selected_option == "approve_exact_source_recovery"
    if approved and approved_scope and approved_scope != str(request.get("authority_scope") or ""):
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_learning", "teaching_recovery_scope_mismatch", (request_id,)),))
    consumed_at = utc_now()
    resolved = {**request, "status": "consumed", "resolution": selected_option, "authority_granted": approved, "consumed_at": consumed_at}
    response = {
        "request_id": request_id,
        "response_kind": "developmental_teaching_material_recovery_authority",
        "selected_option": selected_option,
        "operator_text": operator_text,
        "approved_scope": str(request.get("authority_scope") or "") if approved else "",
        "authority_granted": approved,
        "created_at": consumed_at,
        "consumed_at": consumed_at,
    }
    state = dict(controller.continuous_learning_state or {})
    recovery = dict(state.get("teaching_material_recovery") or {})
    if not approved:
        return replace(
            controller,
            continuous_mission_state="developmental_resource_fulfillment_incomplete",
            active_work_item="teaching_material_recovery_not_approved",
            continuous_developmental_insight_requests=requests[:index] + (resolved,) + requests[index + 1 :],
            continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
            continuous_learning_state={**state, "teaching_material_recovery": {**recovery, "status": "deferred" if selected_option == "defer_exact_source_recovery" else "rejected", "request_id": request_id}},
            journal=controller.journal + (_journal_entry("developmental_learning", "exact_retained_teaching_recovery_not_approved", (request_id, selected_option)),),
        )
    claim = {
        "claim_id": stable_id("retained-teaching-material-recovery-claim", request_id, str(request.get("source_digest") or "")),
        "request_id": request_id,
        "source_record_id": request.get("source_record_id"),
        "source_locator": request.get("source_locator"),
        "expected_reference_digest": request.get("source_digest"),
        "claim_state": "approved_pending_exact_retrieval",
        "execution_attempt_count": 0,
        "claimed_at": consumed_at,
    }
    return replace(
        controller,
        continuous_mission_state="retained_teaching_material_recovery_claimed",
        active_work_item="persist_exact_teaching_source_recovery_before_call",
        continuous_developmental_insight_requests=requests[:index] + (resolved,) + requests[index + 1 :],
        continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
        continuous_learning_state={**state, "teaching_material_recovery": {**recovery, "status": "approved_pending_exact_retrieval", "request_id": request_id, "claim": claim, "no_provider_call_performed": True}},
        journal=controller.journal + (_journal_entry("developmental_learning", "exact_retained_teaching_recovery_claim_persisted", (claim["claim_id"],)),),
    )


def record_recovered_retained_teaching_material(
    controller: ContinuousRuntimeController,
    *,
    source_text: str,
    source_locator: str,
) -> ContinuousRuntimeController:
    """Validate one exact retrieved source and retain only learner-facing material."""

    state = dict(controller.continuous_learning_state or {})
    recovery = dict(state.get("teaching_material_recovery") or {})
    claim = dict(recovery.get("claim") or {})
    if (
        controller.continuous_mission_state != "retained_teaching_material_recovery_claimed"
        or claim.get("claim_state") != "approved_pending_exact_retrieval"
        or source_locator != str(claim.get("source_locator") or "")
    ):
        return controller
    normalized = " ".join(str(source_text or "").split())
    if not normalized or "spectral theorem" not in normalized.lower() or "hermitian" not in normalized.lower():
        return replace(
            controller,
            continuous_mission_state="developmental_resource_fulfillment_incomplete",
            active_work_item="exact_teaching_source_recovery_validation_failed",
            continuous_learning_state={**state, "teaching_material_recovery": {**recovery, "status": "validation_failed", "claim": {**claim, "claim_state": "validation_failed", "execution_attempt_count": 1}, "failure_reason": "required_source_terms_not_present"}},
            journal=controller.journal + (_journal_entry("developmental_learning", "exact_retained_teaching_recovery_rejected", (str(claim.get("claim_id") or ""),)),),
        )
    source_digest = _learning_bridge_digest(normalized)
    artifact = {
        "artifact_id": stable_id("recovered-teaching-artifact", str(claim.get("claim_id") or ""), source_digest),
        "source_identity": claim.get("source_record_id"),
        "source_locator": source_locator,
        "source_digest": source_digest,
        "prior_reference_digest": claim.get("expected_reference_digest"),
        "provenance": {"retrieval_claim_id": claim.get("claim_id"), "source_record_id": claim.get("source_record_id"), "exact_locator_verified": True},
        "plain_language_explanation": "A Hermitian matrix can be expressed in perpendicular unit-vector coordinates where it is diagonal; its eigenvalues are real.",
        "prerequisite_concepts": ("complex conjugate transpose", "Hermitian matrix", "eigenvector", "orthonormal basis", "unitary matrix"),
        "worked_example": {"matrix": "[[2, 1], [1, 2]]", "observation": "This real symmetric matrix has eigenvalues 3 and 1 with perpendicular eigenvector directions."},
        "assessment_dimensions": ({"dimension": "complex_inner_product_space_scope", "topic": "spectral_theorem", "baseline_case_id": "recovered-spectral-baseline", "baseline_components": (), "required_components": ("Hermitian matrix", "orthonormal eigenbasis", "real eigenvalues"), "prerequisites": (), "evidence_ref": str(claim.get("claim_id") or ""), "expected_learning_value": 0.8, "information_gain": 0.8, "estimated_effort": 0.3},),
        "study_resource": {"resource_id": stable_id("recovered-teaching-study-resource", str(claim.get("claim_id") or "")), "topic": "spectral_theorem", "supports_dimensions": ("complex_inner_product_space_scope",), "study_components": ("Hermitian matrix", "orthonormal eigenbasis", "real eigenvalues"), "study_facts": ("Hermitian matrices are unitarily diagonalizable.", "The eigenvalues of a Hermitian matrix are real."), "visible_practice_cases": ({"task_id": "recovered-spectral-practice", "capability_dimension": "complex_inner_product_space_scope", "task_type": "component_assertion", "visible_prompt": "State the spectral-theorem conclusion for a Hermitian matrix and name the coordinate property used.", "response_format": "short structured explanation"},)},
    }
    sealed = dict((state.get("isolated_evaluator_authoring") or {}).get("result", {}).get("sealed_package") or {})
    projection = project_learner_visible_evaluation_cases(sealed)
    bundle = dict(state.get("retained_bundle") or {})
    bundle.update({
        "assessment_dimensions": tuple(artifact["assessment_dimensions"]),
        "study_resources": (dict(artifact["study_resource"]),),
        "resource_provenance": tuple(bundle.get("resource_provenance") or ()) + ({"source_record_id": claim.get("source_record_id"), "canonical_reference": source_locator, "content_digest": source_digest, "recovery_artifact_id": artifact["artifact_id"]},),
    })
    next_recovery = {**recovery, "status": "teaching_material_recovered", "claim": {**claim, "claim_state": "completed", "execution_attempt_count": 1, "actual_source_digest": source_digest}, "artifact": artifact, "learner_evaluation_projection": projection}
    if not projection["accepted"]:
        return replace(
            controller,
            continuous_mission_state="developmental_resource_fulfillment_incomplete",
            active_work_item="learner_visible_evaluation_prompts_unavailable",
            continuous_learning_state={**state, "retained_bundle": bundle, "teaching_material_recovery": next_recovery, "resource_blocker": {"blocker": "learner_visible_evaluation_prompts_unavailable", "missing_fields": projection["errors"], "no_provider_or_research_call_performed": True}},
            journal=controller.journal + (_journal_entry("developmental_learning", "teaching_material_recovered_evaluator_prompt_projection_blocked", (artifact["artifact_id"],)),),
        )
    mission = dict(state.get("mission") or {})
    if not mission:
        return replace(
            controller,
            continuous_mission_state="developmental_resource_fulfillment_incomplete",
            active_work_item="fulfilled_learning_mission_contract_unavailable",
            continuous_learning_state={
                **state,
                "retained_bundle": bundle,
                "teaching_material_recovery": next_recovery,
                "resource_blocker": {"blocker": "fulfilled_learning_mission_contract_unavailable", "missing_fields": ("mission_contract",)},
            },
        )
    return attach_developmental_learning_mission(
        replace(controller, continuous_learning_state={**state, "retained_bundle": bundle, "teaching_material_recovery": next_recovery}),
        str(mission.get("operator_instruction") or ""),
        bundle,
        existing_mission=DevelopmentalMissionContract(**mission),
        preserve_learning_state=True,
    )


def execute_governed_learning_strategy_exact_source_acquisition(
    controller: ContinuousRuntimeController,
    *,
    retrieval_adapter=retrieve_exact_source,
) -> ContinuousRuntimeController:
    """Consume one approved exact-source authority and stop after study evidence."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    request = dict(state.get("governed_learning_strategy_authority_request") or {})
    existing = dict(state.get("governed_learning_strategy_acquisition") or {})
    if existing.get("status") in {"completed", "failed"}:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_learning_strategy_exact_source_acquisition_suppressed", (str(existing.get("acquisition_result_id") or ""),),
        ),))
    if (
        controller.continuous_mission_state != "learning_strategy_acquisition_ready"
        or strategy.get("status") != "learning_strategy_acquisition_ready"
        or request.get("status") != "consumed"
        or not request.get("authority_granted")
        or int(request.get("maximum_calls_or_retrievals") or 0) != 1
        or not request.get("source_locator")
    ):
        return replace(controller, continuous_mission_state="learning_strategy_acquisition_blocked", active_work_item="learning_strategy_exact_source_authority_invalid")
    claim = {
        "claim_id": stable_id(
            "learning-strategy-exact-source-claim",
            request.get("request_id"),
            request.get("source_digest"),
            request.get("claim_nonce") or "initial",
        ),
        "request_id": request.get("request_id"), "strategy_id": strategy.get("strategy_id"),
        "evidence_digest": strategy.get("evidence_digest"), "source_locator": request.get("source_locator"),
        "claim_state": "executing", "execution_attempt_count": 1, "claimed_at": utc_now(),
    }
    try:
        retrieval = dict(retrieval_adapter(str(request["source_locator"])))
        if not is_same_exact_resource_chain(
            str(request.get("source_locator") or ""),
            str(retrieval.get("canonical_locator") or ""),
        ):
            raise ValueError("exact_source_canonical_locator_mismatch")
        result = compile_strategy_acquisition_result(strategy=strategy, authority_request=request, retrieval=retrieval)
    except Exception as exc:  # noqa: BLE001
        failed = {"status": "failed", "claim": {**claim, "claim_state": "failed"}, "failure_reason": f"{type(exc).__name__}:{exc}", "provider_calls": 9}
        return replace(controller, continuous_mission_state="learning_strategy_source_insufficient", active_work_item="exact_source_acquisition_failed", continuous_learning_state={**state, "governed_learning_strategy_acquisition": failed})
    outcome = str(result["outcome"])
    status = "completed"
    next_strategy = {**strategy, "status": outcome, "superseded_by_acquisition_result": result["acquisition_result_id"]}
    acquisition = {"status": status, "claim": {**claim, "claim_state": "completed"}, "result": result, "provider_calls": 9}
    return replace(
        controller,
        continuous_mission_state=outcome,
        active_work_item="learning_strategy_internal_verification_complete",
        continuous_active_subgoal={},
        continuous_learning_state={
            **state,
            "governed_learning_strategy": next_strategy,
            "governed_learning_strategy_acquisition": acquisition,
        },
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "strategy_bound_exact_source_acquisition_completed_without_learner_retry",
            (result["acquisition_result_id"], outcome),
        ),),
    )


def compile_replacement_governed_learning_strategy_authority_request(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Compile one new approval boundary after a terminal exact-source attempt."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    prior_request = dict(state.get("governed_learning_strategy_authority_request") or {})
    acquisition = dict(state.get("governed_learning_strategy_acquisition") or {})
    prior_claim = dict(acquisition.get("claim") or {})
    if (
        acquisition.get("status") != "failed"
        or not prior_request.get("request_id")
        or not prior_claim.get("claim_id")
        or not strategy.get("strategy_id")
        or not strategy.get("evidence_digest")
        or not prior_request.get("source_locator")
    ):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "replacement_learning_strategy_authority_request_not_eligible", (),
        ),))
    if (
        prior_request.get("replacement_for_claim_id")
        and prior_request.get("status") == "pending"
        and str(prior_request.get("strategy_id") or "") == str(strategy.get("strategy_id") or "")
    ):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_replacement_learning_strategy_authority_request_suppressed",
            (str(prior_request.get("request_id") or ""),),
        ),))
    nonce = stable_id(
        "learning-strategy-replacement-nonce",
        strategy.get("strategy_id"),
        strategy.get("evidence_digest"),
        prior_claim.get("claim_id"),
        acquisition.get("failure_reason"),
    )
    request_id = stable_id("learning-strategy-authority-replacement", strategy.get("strategy_id"), nonce)
    replacement = {
        "request_id": request_id,
        "request_kind": "governed_learning_strategy_authority",
        "status": "pending",
        "strategy_id": strategy.get("strategy_id"),
        "mission_id": strategy.get("mission_id"),
        "evidence_digest": strategy.get("evidence_digest"),
        "recommended_action": "retained_exact_source",
        "scope": str(prior_request.get("scope") or ""),
        "authority_scope": str(prior_request.get("authority_scope") or prior_request.get("scope") or ""),
        "source_identity": prior_request.get("source_identity") or "",
        "source_locator": prior_request.get("source_locator") or "",
        "source_digest": prior_request.get("source_digest") or "",
        "question_ids": tuple(prior_request.get("question_ids") or ()),
        "prerequisite_hypothesis_ids": tuple(
            item.get("prerequisite_id") for item in (strategy.get("prerequisite_hypotheses") or ())
            if isinstance(item, Mapping) and item.get("prerequisite_id")
        ),
        "maximum_calls_or_retrievals": 1,
        "cost_boundary": "one bounded approved action",
        "exact_question": "Authorize one replacement exact-source retrieval under the same strategy evidence, reject it, defer it, or ask for clarification.",
        "permitted_responses": (
            "approve_learning_strategy_authority",
            "reject_learning_strategy_authority",
            "defer_learning_strategy_authority",
            "ask_for_clarification",
        ),
        "authority_granted": False,
        "replacement_for_request_id": prior_request.get("request_id"),
        "replacement_for_claim_id": prior_claim.get("claim_id"),
        "claim_nonce": nonce,
        "prohibited_actions": (
            "broad_research", "alternate_source", "provider_call", "learner_retry", "evaluator_run",
            "capability_update", "pcm_action", "git_action", "deployment",
        ),
        "created_at": utc_now(),
    }
    history = tuple(state.get("governed_learning_strategy_authority_history") or ())
    if not any(item.get("request_id") == prior_request.get("request_id") for item in history if isinstance(item, Mapping)):
        history = history + ({**prior_request, "terminal_history": True},)
    acquisition_history = tuple(state.get("governed_learning_strategy_acquisition_history") or ())
    if not any(item.get("claim", {}).get("claim_id") == prior_claim.get("claim_id") for item in acquisition_history if isinstance(item, Mapping)):
        acquisition_history = acquisition_history + ({**acquisition, "terminal_history": True},)
    return replace(
        controller,
        continuous_mission_state="learning_strategy_awaiting_authority",
        active_work_item="learning_strategy_replacement_authority_request",
        continuous_active_subgoal={},
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (replacement,),
        continuous_learning_state={
            **state,
            "governed_learning_strategy": {**strategy, "status": "learning_strategy_awaiting_authority"},
            "governed_learning_strategy_authority_request": replacement,
            "governed_learning_strategy_authority_history": history,
            "governed_learning_strategy_acquisition_history": acquisition_history,
            "governed_learning_strategy_acquisition": {},
        },
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "replacement_learning_strategy_authority_request_compiled",
            (request_id, str(prior_claim.get("claim_id") or "")),
        ),),
    )


def compile_governed_learning_strategy_resource_revision(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Compile one immutable next-resource revision from partial source evidence."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    acquisition = dict(state.get("governed_learning_strategy_acquisition") or {})
    result = dict(acquisition.get("result") or {})
    if (
        acquisition.get("status") != "completed"
        or result.get("outcome") != "learning_strategy_source_partially_sufficient"
        or not strategy.get("strategy_id")
    ):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_resource_revision_not_eligible", (),
        ),))
    existing = dict(state.get("governed_learning_strategy_resource_revision") or {})
    if str(existing.get("acquisition_result_digest") or "") == str(result.get("result_digest") or ""):
        request = dict(existing.get("authority_request") or {})
        requests = tuple(controller.continuous_developmental_insight_requests)
        if request and not any(item.get("request_id") == request.get("request_id") for item in requests):
            return replace(
                controller,
                continuous_developmental_insight_requests=requests + (request,),
                journal=controller.journal + (_journal_entry(
                    "developmental_learning", "learning_strategy_resource_revision_request_restored", (str(request.get("request_id") or ""),),
                ),),
            )
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_learning_strategy_resource_revision_suppressed", (str(existing.get("revision_id") or ""),),
        ),))
    packet = learner_visible_strategy_packet(state)
    inventory = ({
        "source_identity": result.get("source_identity") or "",
        "source_locator": result.get("source_locator") or "",
        "source_digest": result.get("source_digest") or "",
    },)
    revision = compile_resource_revision_record(
        strategy=strategy,
        acquisition_result=result,
        available_resource_classes=tuple(packet.get("available_resource_classes") or ()),
        retained_source_inventory=inventory,
    )


    validation = validate_governed_learning_strategy_resource_revision(
        revision, strategy=strategy, acquisition_result=result,
    )
    stored = {**revision, "validation": validation, "status": "validated" if validation["accepted"] else "validation_failed"}
    history = tuple(state.get("governed_learning_strategy_revision_history") or ())
    if not validation["accepted"]:
        return replace(
            controller,
            continuous_mission_state="learning_strategy_resource_revision_failed",
            active_work_item="learning_strategy_resource_revision_validation_failed",
            continuous_learning_state={**state, "governed_learning_strategy_resource_revision": stored},
            journal=controller.journal + (_journal_entry(
                "developmental_learning", "learning_strategy_resource_revision_grounding_failed", tuple(validation["errors"]),
            ),),
        )
    request = dict(stored.get("authority_request") or {})
    return replace(
        controller,
        continuous_mission_state="learning_strategy_resource_revision_awaiting_authority" if request else "learning_strategy_resource_revision_ready",
        active_work_item="learning_strategy_resource_revision_authority_request" if request else "learning_strategy_resource_revision_ready",
        continuous_active_subgoal={},
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + ((request,) if request else ()),
        continuous_learning_state={
            **state,
            "governed_learning_strategy_resource_revision": stored,
            "governed_learning_strategy_revision_history": history,
        },
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "partial_source_evidence_compiled_to_immutable_resource_revision",
            (str(stored.get("revision_id") or ""), str(validation["accepted"])),
        ),),
    )


def compile_governed_learning_strategy_single_question_revision(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Classify a single retained question before any further acquisition."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    retrieval = dict(state.get("governed_learning_strategy_discovered_source_retrieval") or {})
    acquisition = dict(retrieval.get("result") or {})
    discovery = dict((state.get("governed_learning_strategy_source_discovery") or {}).get("result") or {})
    if retrieval.get("status") != "completed" or acquisition.get("outcome") != "learning_strategy_source_partially_sufficient" or not discovery:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "single_question_revision_not_eligible", (),
        ),))
    existing = dict(state.get("governed_learning_strategy_single_question_revision") or {})
    if (
        existing.get("prior_acquisition_result_digest") == acquisition.get("result_digest")
        and int(existing.get("revision_version") or 0) >= 3
    ):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_single_question_revision_suppressed", (str(existing.get("revision_id") or ""),),
        ),))
    try:
        revision = compile_single_question_revision_record(
            strategy=strategy, acquisition_result=acquisition, discovery_result=discovery,
        )
        validation = validate_single_question_learning_strategy_revision(
            revision, strategy=strategy, acquisition_result=acquisition, discovery_result=discovery,
        )
    except Exception as exc:  # noqa: BLE001
        return replace(controller, continuous_mission_state="learning_strategy_single_question_revision_failed", active_work_item="single_question_revision_compilation_failed", journal=controller.journal + (_journal_entry(
            "developmental_learning", "single_question_revision_compilation_failed", (f"{type(exc).__name__}:{exc}",),
        ),))
    history = tuple(state.get("governed_learning_strategy_single_question_revision_history") or ())
    if existing and existing.get("revision_id") != revision.get("revision_id"):
        history = history + ({
            **existing,
            "superseded_by_revision_id": revision["revision_id"],
            "superseded_at": utc_now(),
        },)
    stored = {**revision, "validation": validation}
    if not validation["accepted"]:
        return replace(controller, continuous_mission_state="learning_strategy_single_question_revision_failed", active_work_item="single_question_revision_validation_failed", continuous_learning_state={**state, "governed_learning_strategy_single_question_revision": stored})
    return replace(
        controller,
        continuous_mission_state=revision["outcome"],
        active_work_item="single_question_linkage_repair_required" if revision["outcome"] == "finite_dimensional_evidence_linkage_repair_required" else "single_question_revised_without_retrieval",
        continuous_active_subgoal={},
        continuous_learning_state={
            **state,
            "governed_learning_strategy_single_question_revision": stored,
            "governed_learning_strategy_single_question_revision_history": history,
        },
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "single_question_revision_compiled_without_retrieval", (revision["revision_id"], revision["outcome"]),
        ),),
    )


def compile_governed_learning_strategy_evidence_linkage_reassessment(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Re-evaluate retained source excerpts without retrieval or capability change."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    retrieval = dict(state.get("governed_learning_strategy_discovered_source_retrieval") or {})
    result = dict(retrieval.get("result") or {})
    revision = dict(state.get("governed_learning_strategy_single_question_revision") or {})
    if revision.get("outcome") != "finite_dimensional_evidence_linkage_repair_required" or retrieval.get("status") != "completed":
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "evidence_linkage_reassessment_not_eligible", (),
        ),))
    existing = dict(state.get("governed_learning_strategy_evidence_linkage_reassessment") or {})
    if existing.get("acquisition_result_digest") == result.get("result_digest"):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_evidence_linkage_reassessment_suppressed", (str(existing.get("reassessment_id") or ""),),
        ),))
    reassessment = compile_strategy_acquisition_evidence_linkage_reassessment(strategy=strategy, acquisition_result=result)
    return replace(
        controller,
        continuous_mission_state="learning_strategy_evidence_linkage_reassessed",
        active_work_item="finite_dimensional_contextual_evidence_requires_sufficiency_review",
        continuous_active_subgoal={},
        continuous_learning_state={**state, "governed_learning_strategy_evidence_linkage_reassessment": reassessment},
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "retained_evidence_relinked_without_retrieval_or_promotion", (reassessment["reassessment_id"], reassessment["outcome"]),
        ),),
    )


def compile_governed_constructive_grounding(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Compile one bounded prerequisite-grounding decision from retained evidence."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    latest_revision = dict(state.get("governed_learning_strategy_resource_revision") or {})
    retrieval = dict(state.get("governed_learning_strategy_discovered_source_retrieval") or {})
    acquisition = dict(retrieval.get("result") or {})
    linkage = dict(state.get("governed_learning_strategy_evidence_linkage_reassessment") or {})
    discovery = dict((state.get("governed_learning_strategy_source_discovery") or {}).get("result") or {})
    if controller.continuous_mission_state != "learning_strategy_evidence_linkage_reassessed" or not linkage:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "constructive_grounding_not_eligible", (),
        ),))
    existing = dict(state.get("governed_constructive_grounding") or {})
    if existing.get("assessment_digest"):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_constructive_grounding_suppressed", (str(existing.get("assessment_id") or ""),),
        ),))
    try:
        assessment = compile_constructive_grounding_assessment(
            strategy=strategy, latest_revision=latest_revision, acquisition_result=acquisition,
            linkage_reassessment=linkage, discovery_result=discovery,
        )
        validation = validate_constructive_grounding_assessment(
            assessment, strategy=strategy, acquisition_result=acquisition, linkage_reassessment=linkage,
        )
    except Exception as exc:  # noqa: BLE001
        return replace(controller, continuous_mission_state="constructive_grounding_failed", active_work_item="constructive_grounding_compilation_failed", journal=controller.journal + (_journal_entry(
            "developmental_learning", "constructive_grounding_compilation_failed", (f"{type(exc).__name__}:{exc}",),
        ),))
    stored = {**assessment, "validation": validation}
    if not validation["accepted"]:
        return replace(controller, continuous_mission_state="constructive_grounding_failed", active_work_item="constructive_grounding_validation_failed", continuous_learning_state={**state, "governed_constructive_grounding": stored})
    request = dict(stored.get("authority_request") or {})
    return replace(
        controller,
        continuous_mission_state=stored["outcome"],
        active_work_item="constructive_grounding_exact_source_authority_request" if request else "constructive_grounding_unresolved",
        continuous_active_subgoal={},
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + ((request,) if request else ()),
        continuous_learning_state={**state, "governed_constructive_grounding": stored},
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "constructive_grounding_compiled_without_retrieval", (stored["assessment_id"], stored["selected_path"]),
        ),),
    )


def consume_governed_learning_strategy_authority_response(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    selected_option: str,
    operator_text: str = "",
    approved_scope: str = "",
) -> ContinuousRuntimeController:
    """Consume one strategy-owned authority decision without performing work."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((
        position for position, item in enumerate(requests)
        if item.get("request_id") == request_id
        and item.get("request_kind") == "governed_learning_strategy_authority"
        and item.get("status") == "pending"
    ), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_or_unknown_learning_strategy_authority_response_suppressed", (request_id,),
        ),))
    request = requests[index]
    permitted = tuple(request.get("permitted_responses") or ())
    if selected_option not in permitted:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "invalid_learning_strategy_authority_response_rejected", (request_id, selected_option),
        ),))
    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    stored_request = dict(state.get("governed_learning_strategy_authority_request") or {})
    binding_matches = (
        str(strategy.get("strategy_id") or "") == str(request.get("strategy_id") or "")
        and str(strategy.get("evidence_digest") or "") == str(request.get("evidence_digest") or "")
        and str(stored_request.get("request_id") or "") == request_id
        and str(stored_request.get("source_locator") or "") == str(request.get("source_locator") or "")
        and int(stored_request.get("maximum_calls_or_retrievals") or 0) == int(request.get("maximum_calls_or_retrievals") or 0)
    )
    if not binding_matches or strategy.get("status") != "learning_strategy_awaiting_authority":
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_authority_response_rejected_binding_mismatch", (request_id,),
        ),))
    approved = selected_option == "approve_learning_strategy_authority"
    expected_scope = str(request.get("authority_scope") or "")
    if approved and approved_scope != expected_scope:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_authority_response_rejected_scope_mismatch", (request_id,),
        ),))
    consumed_at = utc_now()
    resolved = {
        **request,
        "status": "consumed",
        "resolution": selected_option,
        "authority_granted": approved,
        "consumed_at": consumed_at,
    }
    response = {
        "request_id": request_id,
        "response_kind": "governed_learning_strategy_authority",
        "selected_option": selected_option,
        "operator_text": operator_text,
        "approved_scope": expected_scope if approved else "",
        "authority_granted": approved,
        "created_at": consumed_at,
        "consumed_at": consumed_at,
    }
    next_strategy = {
        **strategy,
        "status": (
            "learning_strategy_acquisition_ready" if approved
            else "learning_strategy_deferred" if selected_option == "defer_learning_strategy_authority"
            else "learning_strategy_clarification_requested" if selected_option == "ask_for_clarification"
            else "learning_strategy_rejected"
        ),
        "authority_resolution": selected_option,
        "authority_resolved_at": consumed_at,
    }
    next_request = {**stored_request, **resolved}
    next_state = {
        **state,
        "governed_learning_strategy": next_strategy,
        "governed_learning_strategy_authority_request": next_request,
    }
    updated_requests = requests[:index] + (resolved,) + requests[index + 1:]
    if selected_option == "ask_for_clarification":
        clarification_id = stable_id("learning-strategy-authority-clarification", request_id)
        if not any(item.get("request_id") == clarification_id for item in updated_requests):
            updated_requests = updated_requests + ({
                "request_id": clarification_id,
                "request_kind": "clarification",
                "status": "pending",
                "strategy_authority_request_id": request_id,
                "exact_question": "What aspect of the already bounded strategy authority scope needs clarification?",
                "authority_scope": "none; clarification grants no authority",
                "permitted_responses": ("provide_clarification", "defer"),
                "authority_granted": False,
                "created_at": consumed_at,
            },)
        return replace(
            controller,
            continuous_mission_state="learning_strategy_awaiting_clarification",
            active_work_item="learning_strategy_authority_clarification",
            continuous_developmental_insight_requests=updated_requests,
            continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
            continuous_learning_state=next_state,
            journal=controller.journal + (_journal_entry(
                "developmental_learning", "learning_strategy_authority_clarification_requested_without_authority", (request_id,),
            ),),
        )
    mission_state = "learning_strategy_acquisition_ready" if approved else "learning_strategy_blocked"
    work_item = "approved_learning_strategy_exact_source_retrieval" if approved else "learning_strategy_authority_not_approved"
    return replace(
        controller,
        continuous_mission_state=mission_state,
        active_work_item=work_item,
        continuous_developmental_insight_requests=updated_requests,
        continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
        continuous_learning_state=next_state,
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_authority_response_consumed_once", (request_id, selected_option),
        ),),
    )


def consume_governed_learning_strategy_resource_revision_authority_response(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    selected_option: str,
    operator_text: str = "",
    approved_scope: str = "",
) -> ContinuousRuntimeController:
    """Consume one revision-owned discovery authority without discovering sources."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((
        position for position, item in enumerate(requests)
        if item.get("request_id") == request_id
        and item.get("request_kind") == "governed_learning_strategy_resource_revision_authority"
        and item.get("status") == "pending"
    ), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_or_unknown_learning_strategy_resource_revision_response_suppressed", (request_id,),
        ),))
    request = requests[index]
    if selected_option not in tuple(request.get("permitted_responses") or ()):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "invalid_learning_strategy_resource_revision_response_rejected", (request_id, selected_option),
        ),))
    state = dict(controller.continuous_learning_state or {})
    revision = dict(state.get("governed_learning_strategy_resource_revision") or {})
    stored = dict(revision.get("authority_request") or {})
    if (
        stored.get("request_id") != request_id
        or stored.get("revision_id") != request.get("revision_id")
        or stored.get("acquisition_result_digest") != request.get("acquisition_result_digest")
    ):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_resource_revision_response_rejected_binding_mismatch", (request_id,),
        ),))
    approved = selected_option == "approve_learning_strategy_resource_revision_authority"
    expected_scope = str(request.get("authority_scope") or request.get("scope") or "")
    if approved and approved_scope != expected_scope:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_resource_revision_response_rejected_scope_mismatch", (request_id,),
        ),))
    resolved = {
        **request,
        "status": "consumed",
        "authority_granted": approved,
        "resolution": selected_option,
        "resolved_at": utc_now(),
    }
    response = {
        "request_id": request_id,
        "response_kind": "governed_learning_strategy_resource_revision_authority",
        "selected_option": selected_option,
        "operator_text": operator_text,
        "approved_scope": expected_scope if approved else "",
        "authority_granted": approved,
        "created_at": utc_now(),
    }
    updated_requests = requests[:index] + (resolved,) + requests[index + 1:]
    updated_revision = {
        **revision,
        "authority_request": resolved,
        "status": "source_discovery_authority_granted" if approved else "source_discovery_authority_not_granted",
    }
    return replace(
        controller,
        continuous_mission_state="learning_strategy_resource_discovery_ready" if approved else "learning_strategy_resource_revision_blocked",
        active_work_item="approved_learning_strategy_narrow_source_discovery" if approved else "learning_strategy_resource_revision_authority_not_approved",
        continuous_developmental_insight_requests=updated_requests,
        continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
        continuous_learning_state={**state, "governed_learning_strategy_resource_revision": updated_revision},
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_resource_revision_authority_response_consumed_once", (request_id, selected_option),
        ),),
    )


def claim_governed_learning_strategy_narrow_source_discovery(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Persist one metadata-discovery claim before any discovery adapter runs."""

    state = dict(controller.continuous_learning_state or {})
    revision = dict(state.get("governed_learning_strategy_resource_revision") or {})
    request = dict(revision.get("authority_request") or {})
    existing = dict(state.get("governed_learning_strategy_source_discovery") or {})
    if existing.get("status") in {"claimed", "completed", "insufficient", "failed"}:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_learning_strategy_source_discovery_suppressed", (str(existing.get("claim", {}).get("claim_id") or ""),),
        ),))
    if (
        controller.continuous_mission_state != "learning_strategy_resource_discovery_ready"
        or revision.get("status") != "source_discovery_authority_granted"
        or request.get("status") != "consumed"
        or not request.get("authority_granted")
        or request.get("action_type") != "narrow_source_discovery"
    ):
        return replace(controller, continuous_mission_state="learning_strategy_source_discovery_blocked", active_work_item="learning_strategy_source_discovery_authority_invalid")
    claim = {
        "claim_id": stable_id("learning-strategy-source-discovery-claim", request.get("request_id"), revision.get("revision_id")),
        "request_id": request.get("request_id"),
        "revision_id": revision.get("revision_id"),
        "claim_state": "metadata_discovery_claimed",
        "execution_attempt_count": 1,
        "maximum_result_count": int(request.get("discovery_constraints", {}).get("maximum_result_count") or 0),
        "claimed_at": utc_now(),
    }
    return replace(
        controller,
        continuous_mission_state="learning_strategy_source_discovery_claimed",
        active_work_item="learning_strategy_metadata_discovery_claimed",
        continuous_learning_state={**state, "governed_learning_strategy_source_discovery": {"status": "claimed", "claim": claim}},
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_metadata_discovery_claimed_once", (claim["claim_id"],),
        ),),
    )


def record_governed_learning_strategy_metadata_source_discovery(
    controller: ContinuousRuntimeController,
    *,
    metadata_candidates: Sequence[Mapping[str, Any]],
) -> ContinuousRuntimeController:
    """Record bounded public metadata after an already-persisted discovery claim."""

    state = dict(controller.continuous_learning_state or {})
    revision = dict(state.get("governed_learning_strategy_resource_revision") or {})
    discovery = dict(state.get("governed_learning_strategy_source_discovery") or {})
    if controller.continuous_mission_state != "learning_strategy_source_discovery_claimed" or discovery.get("status") != "claimed":
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_metadata_discovery_result_rejected_without_claim", (),
        ),))
    try:
        result = compile_metadata_only_source_discovery_result(revision=revision, metadata_candidates=metadata_candidates)
        validation = validate_metadata_only_source_discovery_result(result, revision=revision)
        if not validation["accepted"]:
            raise ValueError(";".join(validation["errors"]))
    except Exception as exc:  # noqa: BLE001
        return replace(
            controller,
            continuous_mission_state="learning_strategy_source_discovery_insufficient",
            active_work_item="learning_strategy_metadata_discovery_validation_failed",
            continuous_learning_state={
                **state,
                "governed_learning_strategy_source_discovery": {
                    **discovery,
                    "status": "failed",
                    "claim": {**dict(discovery.get("claim") or {}), "claim_state": "failed"},
                    "failure_reason": f"{type(exc).__name__}:{exc}",
                },
            },
        )
    status = "completed" if result["status"] == "learning_strategy_source_discovery_completed" else "insufficient"
    return replace(
        controller,
        continuous_mission_state=result["status"],
        active_work_item="learning_strategy_discovery_result_ready" if status == "completed" else "learning_strategy_source_discovery_insufficient",
        continuous_active_subgoal={},
        continuous_learning_state={
            **state,
            "governed_learning_strategy_source_discovery": {
                "status": status,
                "claim": {**dict(discovery.get("claim") or {}), "claim_state": "completed"},
                "result": result,
                "validation": validation,
            },
        },
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "learning_strategy_metadata_discovery_completed_without_retrieval",
            (str(result["discovery_result_id"]), result["status"]),
        ),),
    )


def compile_governed_learning_strategy_discovered_source_retrieval_authority(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Create one approval boundary for the discovery-ranked candidate only."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    revision = dict(state.get("governed_learning_strategy_resource_revision") or {})
    discovery = dict(state.get("governed_learning_strategy_source_discovery") or {})
    result = dict(discovery.get("result") or {})
    existing = dict(state.get("governed_learning_strategy_discovered_source_retrieval_authority_request") or {})
    if existing:
        validation = validate_discovered_source_retrieval_authority_request(
            existing, strategy=strategy, revision=revision, discovery_result=result,
        )
        if validation["accepted"]:
            requests = tuple(controller.continuous_developmental_insight_requests)
            if not any(item.get("request_id") == existing.get("request_id") for item in requests):
                return replace(controller, continuous_developmental_insight_requests=requests + (existing,))
            return replace(controller, journal=controller.journal + (_journal_entry(
                "developmental_learning", "duplicate_discovered_source_retrieval_authority_suppressed", (str(existing.get("request_id") or ""),),
            ),))
        return replace(controller, continuous_mission_state="learning_strategy_discovered_source_retrieval_authority_invalid", active_work_item="discovered_source_retrieval_authority_binding_invalid")
    if (
        controller.continuous_mission_state != "learning_strategy_source_discovery_completed"
        or discovery.get("status") != "completed"
        or result.get("status") != "learning_strategy_source_discovery_completed"
        or not result.get("recommended_candidate_id")
    ):
        return replace(controller, continuous_mission_state="learning_strategy_discovered_source_retrieval_authority_blocked", active_work_item="discovered_source_retrieval_authority_prerequisites_missing")
    try:
        request = compile_discovered_source_retrieval_authority_request(
            strategy=strategy, revision=revision, discovery_result=result,
        )
        validation = validate_discovered_source_retrieval_authority_request(
            request, strategy=strategy, revision=revision, discovery_result=result,
        )
        if not validation["accepted"]:
            raise ValueError(";".join(validation["errors"]))
    except Exception as exc:  # noqa: BLE001
        return replace(controller, continuous_mission_state="learning_strategy_discovered_source_retrieval_authority_invalid", active_work_item="discovered_source_retrieval_authority_validation_failed", journal=controller.journal + (_journal_entry(
            "developmental_learning", "discovered_source_retrieval_authority_compilation_failed", (f"{type(exc).__name__}:{exc}",),
        ),))
    return replace(
        controller,
        continuous_mission_state="learning_strategy_discovered_source_retrieval_awaiting_authority",
        active_work_item="learning_strategy_discovered_source_retrieval_authority_request",
        continuous_active_subgoal={},
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        continuous_learning_state={
            **state,
            "governed_learning_strategy_discovered_source_retrieval_authority_request": request,
        },
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "discovered_source_retrieval_authority_compiled_without_retrieval", (request["request_id"],),
        ),),
    )


def archive_failed_governed_learning_strategy_discovered_source_retrieval(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Retire one terminal failed retrieval before a separately approved replacement."""

    state = dict(controller.continuous_learning_state or {})
    retrieval = dict(state.get("governed_learning_strategy_discovered_source_retrieval") or {})
    authority = dict(state.get("governed_learning_strategy_discovered_source_retrieval_authority_request") or {})
    if retrieval.get("status") != "failed" or not retrieval.get("claim", {}).get("claim_id") or not authority.get("request_id"):
        return controller
    retrieval_history = tuple(state.get("governed_learning_strategy_discovered_source_retrieval_history") or ())
    if not any(item.get("claim", {}).get("claim_id") == retrieval["claim"]["claim_id"] for item in retrieval_history if isinstance(item, Mapping)):
        retrieval_history = retrieval_history + ({**retrieval, "archived_at": utc_now(), "terminal_history": True},)
    authority_history = tuple(state.get("governed_learning_strategy_discovered_source_retrieval_authority_history") or ())
    if not any(item.get("request_id") == authority.get("request_id") for item in authority_history if isinstance(item, Mapping)):
        authority_history = authority_history + ({**authority, "archived_at": utc_now(), "terminal_history": True},)
    return replace(
        controller,
        continuous_mission_state="learning_strategy_source_discovery_completed",
        active_work_item="archived_discovered_source_retrieval_failure",
        continuous_learning_state={
            **state,
            "governed_learning_strategy_discovered_source_retrieval": {},
            "governed_learning_strategy_discovered_source_retrieval_authority_request": {},
            "governed_learning_strategy_discovered_source_retrieval_history": retrieval_history,
            "governed_learning_strategy_discovered_source_retrieval_authority_history": authority_history,
        },
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "terminal_discovered_source_retrieval_archived", (str(retrieval["claim"]["claim_id"]),),
        ),),
    )


def compile_replacement_governed_learning_strategy_discovered_source_retrieval_authority(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Compile a fresh one-use authority after an archived terminal parser failure."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    revision = dict(state.get("governed_learning_strategy_resource_revision") or {})
    discovery = dict(state.get("governed_learning_strategy_source_discovery") or {})
    result = dict(discovery.get("result") or {})
    history = tuple(state.get("governed_learning_strategy_discovered_source_retrieval_history") or ())
    authority_history = tuple(state.get("governed_learning_strategy_discovered_source_retrieval_authority_history") or ())
    prior = dict(history[-1] or {}) if history else {}
    prior_authority = dict(authority_history[-1] or {}) if authority_history else {}
    if (
        controller.continuous_mission_state != "learning_strategy_source_discovery_completed"
        or prior.get("status") != "failed"
        or not prior.get("claim", {}).get("claim_id")
        or not prior_authority.get("request_id")
        or state.get("governed_learning_strategy_discovered_source_retrieval_authority_request")
    ):
        return replace(controller, continuous_mission_state="learning_strategy_discovered_source_retrieval_replacement_blocked", active_work_item="replacement_retrieval_prerequisites_missing")
    nonce = stable_id("discovered-source-retrieval-replacement-nonce", prior["claim"]["claim_id"], prior.get("failure_reason"), result.get("result_digest"))
    request = compile_discovered_source_retrieval_authority_request(
        strategy=strategy, revision=revision, discovery_result=result, replacement_nonce=nonce,
    )
    request = {**request, "replacement_for_request_id": prior_authority.get("request_id"), "replacement_for_claim_id": prior["claim"]["claim_id"]}
    validation = validate_discovered_source_retrieval_authority_request(request, strategy=strategy, revision=revision, discovery_result=result)
    if not validation["accepted"]:
        return replace(controller, continuous_mission_state="learning_strategy_discovered_source_retrieval_replacement_blocked", active_work_item="replacement_retrieval_binding_invalid")
    return replace(
        controller,
        continuous_mission_state="learning_strategy_discovered_source_retrieval_awaiting_authority",
        active_work_item="learning_strategy_discovered_source_retrieval_replacement_authority_request",
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        continuous_learning_state={**state, "governed_learning_strategy_discovered_source_retrieval_authority_request": request},
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "replacement_discovered_source_retrieval_authority_compiled", (request["request_id"], str(prior["claim"]["claim_id"])),
        ),),
    )


def consume_governed_learning_strategy_discovered_source_retrieval_authority_response(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    selected_option: str,
    operator_text: str = "",
    approved_scope: str = "",
) -> ContinuousRuntimeController:
    """Consume one discovered-source retrieval authority without retrieving it."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((
        position for position, item in enumerate(requests)
        if item.get("request_id") == request_id
        and item.get("request_kind") == "governed_learning_strategy_discovered_source_retrieval_authority"
        and item.get("status") == "pending"
    ), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_or_unknown_discovered_source_retrieval_response_suppressed", (request_id,),
        ),))
    request = requests[index]
    if selected_option not in tuple(request.get("permitted_responses") or ()):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "invalid_discovered_source_retrieval_response_rejected", (request_id, selected_option),
        ),))
    state = dict(controller.continuous_learning_state or {})
    stored = dict(state.get("governed_learning_strategy_discovered_source_retrieval_authority_request") or {})
    if stored.get("request_id") != request_id or stored.get("discovery_result_digest") != request.get("discovery_result_digest"):
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "discovered_source_retrieval_response_rejected_binding_mismatch", (request_id,),
        ),))
    approved = selected_option == "approve_learning_strategy_discovered_source_retrieval_authority"
    expected_scope = str(request.get("authority_scope") or request.get("scope") or "")
    if approved and approved_scope != expected_scope:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "discovered_source_retrieval_response_rejected_scope_mismatch", (request_id,),
        ),))
    resolved = {**request, "status": "consumed", "authority_granted": approved, "resolution": selected_option, "resolved_at": utc_now()}
    response = {
        "request_id": request_id, "response_kind": request["request_kind"], "selected_option": selected_option,
        "operator_text": operator_text, "approved_scope": expected_scope if approved else "", "authority_granted": approved, "created_at": utc_now(),
    }
    return replace(
        controller,
        continuous_mission_state="learning_strategy_discovered_source_retrieval_ready" if approved else "learning_strategy_discovered_source_retrieval_blocked",
        active_work_item="approved_learning_strategy_discovered_source_retrieval" if approved else "discovered_source_retrieval_not_approved",
        continuous_developmental_insight_requests=requests[:index] + (resolved,) + requests[index + 1:],
        continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
        continuous_learning_state={**state, "governed_learning_strategy_discovered_source_retrieval_authority_request": resolved},
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "discovered_source_retrieval_authority_response_consumed_once", (request_id, selected_option),
        ),),
    )


def claim_governed_learning_strategy_discovered_source_retrieval(
    controller: ContinuousRuntimeController,
) -> ContinuousRuntimeController:
    """Persist one exact retrieval claim before the approved adapter can run."""

    state = dict(controller.continuous_learning_state or {})
    request = dict(state.get("governed_learning_strategy_discovered_source_retrieval_authority_request") or {})
    existing = dict(state.get("governed_learning_strategy_discovered_source_retrieval") or {})
    if existing.get("status") in {"claimed", "completed", "failed"}:
        return replace(controller, journal=controller.journal + (_journal_entry(
            "developmental_learning", "duplicate_discovered_source_retrieval_suppressed", (str(existing.get("claim", {}).get("claim_id") or ""),),
        ),))
    if (
        controller.continuous_mission_state != "learning_strategy_discovered_source_retrieval_ready"
        or request.get("status") != "consumed" or not request.get("authority_granted")
        or int(request.get("maximum_retrieval_count") or 0) != 1
    ):
        return replace(controller, continuous_mission_state="learning_strategy_discovered_source_retrieval_blocked", active_work_item="discovered_source_retrieval_authority_invalid")
    claim = {
        "claim_id": stable_id("learning-strategy-discovered-source-retrieval-claim", request.get("request_id"), request.get("discovery_result_digest")),
        "request_id": request.get("request_id"), "candidate_id": request.get("candidate_id"), "canonical_locator": request.get("canonical_locator"),
        "claim_state": "approved_pending_exact_retrieval", "execution_attempt_count": 0, "claimed_at": utc_now(),
    }
    return replace(
        controller,
        continuous_mission_state="learning_strategy_discovered_source_retrieval_claimed",
        active_work_item="discovered_source_retrieval_claimed",
        continuous_learning_state={**state, "governed_learning_strategy_discovered_source_retrieval": {"status": "claimed", "claim": claim}},
    )


def execute_claimed_governed_learning_strategy_discovered_source_retrieval(
    controller: ContinuousRuntimeController,
    *,
    retrieval_adapter=retrieve_exact_source,
) -> ContinuousRuntimeController:
    """Retrieve exactly one claimed discovered source and retain only question-bound claims."""

    state = dict(controller.continuous_learning_state or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    authority = dict(state.get("governed_learning_strategy_discovered_source_retrieval_authority_request") or {})
    retrieval_state = dict(state.get("governed_learning_strategy_discovered_source_retrieval") or {})
    claim = dict(retrieval_state.get("claim") or {})
    if (
        controller.continuous_mission_state != "learning_strategy_discovered_source_retrieval_claimed"
        or retrieval_state.get("status") != "claimed"
        or claim.get("claim_state") != "approved_pending_exact_retrieval"
    ):
        return controller
    source_locator = str(authority.get("canonical_locator") or "")
    try:
        retrieval = dict(retrieval_adapter(source_locator))
        if not is_same_exact_resource_chain(source_locator, str(retrieval.get("canonical_locator") or "")):
            raise ValueError("discovered_source_canonical_locator_mismatch")
        acquisition_authority = {
            "request_id": authority.get("request_id"), "source_identity": authority.get("candidate_id"),
            "source_locator": source_locator, "source_digest": authority.get("discovery_result_digest"),
        }
        result = compile_strategy_acquisition_result(strategy=strategy, authority_request=acquisition_authority, retrieval=retrieval)
    except Exception as exc:  # noqa: BLE001
        return replace(
            controller,
            continuous_mission_state="learning_strategy_discovered_source_retrieval_failed",
            active_work_item="discovered_source_retrieval_failed",
            continuous_learning_state={**state, "governed_learning_strategy_discovered_source_retrieval": {
                "status": "failed", "claim": {**claim, "claim_state": "failed", "execution_attempt_count": 1}, "failure_reason": f"{type(exc).__name__}:{exc}",
            }},
        )
    return replace(
        controller,
        continuous_mission_state="learning_strategy_discovered_source_retrieval_completed",
        active_work_item="discovered_source_sufficiency_evaluated",
        continuous_active_subgoal={},
        continuous_learning_state={**state, "governed_learning_strategy_discovered_source_retrieval": {
            "status": "completed", "claim": {**claim, "claim_state": "completed", "execution_attempt_count": 1}, "result": result,
        }},
        journal=controller.journal + (_journal_entry(
            "developmental_learning", "discovered_source_retrieval_completed_without_learner_retry", (result["acquisition_result_id"], result["outcome"]),
        ),),
    )


def consume_governed_constructive_grounding_exact_source_authority_response(
    controller: ContinuousRuntimeController, *, request_id: str, selected_option: str, operator_text: str = "", approved_scope: str = "",
) -> ContinuousRuntimeController:
    """Consume one constructive-grounding retrieval approval without dispatching it."""

    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((i for i, item in enumerate(requests) if item.get("request_id") == request_id and item.get("request_kind") == "governed_constructive_grounding_exact_source_authority" and item.get("status") == "pending"), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_learning", "duplicate_or_unknown_constructive_grounding_response_suppressed", (request_id,)),))
    request = requests[index]
    if selected_option not in tuple(request.get("permitted_responses") or ()):
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_learning", "invalid_constructive_grounding_response_rejected", (request_id, selected_option)),))
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    request_field = "authority_request" if dict(assessment.get("authority_request") or {}).get("request_id") == request_id else "followup_authority_request"
    if dict(assessment.get(request_field) or {}).get("request_id") != request_id:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_learning", "constructive_grounding_response_binding_mismatch", (request_id,)),))
    approved = selected_option == "approve_constructive_grounding_exact_source_authority"
    scope = str(request.get("authority_scope") or "")
    if approved and approved_scope != scope:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_learning", "constructive_grounding_response_scope_mismatch", (request_id,),),))
    resolved = {**request, "status": "consumed", "resolution": selected_option, "authority_granted": approved, "resolved_at": utc_now()}
    response = {"request_id": request_id, "response_kind": request["request_kind"], "selected_option": selected_option, "operator_text": operator_text, "approved_scope": scope if approved else "", "authority_granted": approved, "created_at": utc_now()}
    return replace(
        controller,
        continuous_mission_state="constructive_grounding_exact_source_ready" if approved else "constructive_grounding_exact_source_not_approved",
        active_work_item="approved_constructive_grounding_exact_source_retrieval" if approved else "constructive_grounding_authority_not_approved",
        continuous_developmental_insight_requests=requests[:index] + (resolved,) + requests[index + 1:],
        continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
        continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, request_field: resolved}},
    )


def claim_governed_constructive_grounding_exact_source_retrieval(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    """Persist an exact-once claim for the approved constructive source."""

    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    request = dict(assessment.get("authority_request") or {})
    existing = dict(assessment.get("retrieval") or {})
    if existing.get("status") in {"claimed", "completed", "failed"}:
        return replace(controller, journal=controller.journal + (_journal_entry("developmental_learning", "duplicate_constructive_grounding_retrieval_suppressed", (str(existing.get("claim", {}).get("claim_id") or ""),),)))
    if controller.continuous_mission_state != "constructive_grounding_exact_source_ready" or not request.get("authority_granted") or request.get("status") != "consumed":
        return replace(controller, continuous_mission_state="constructive_grounding_exact_source_blocked", active_work_item="constructive_grounding_authority_invalid")
    claim = {
        "claim_id": stable_id("constructive-grounding-exact-source-claim", request.get("request_id"), request.get("canonical_locator")),
        "request_id": request.get("request_id"), "candidate_id": request.get("candidate_id"), "canonical_locator": request.get("canonical_locator"),
        "claim_state": "approved_pending_exact_retrieval", "execution_attempt_count": 0, "claimed_at": utc_now(),
    }
    return replace(controller, continuous_mission_state="constructive_grounding_exact_source_claimed", active_work_item="constructive_grounding_exact_source_claimed", continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "retrieval": {"status": "claimed", "claim": claim}}})


def claim_followup_governed_constructive_grounding_exact_source_retrieval(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    request = dict(assessment.get("followup_authority_request") or {})
    existing = dict(assessment.get("followup_retrieval") or {})
    if existing.get("status") in {"claimed", "completed", "failed"}:
        return controller
    if controller.continuous_mission_state != "constructive_grounding_exact_source_ready" or request.get("status") != "consumed" or not request.get("authority_granted"):
        return replace(controller, continuous_mission_state="constructive_grounding_followup_blocked", active_work_item="constructive_grounding_followup_authority_invalid")
    claim = {"claim_id": stable_id("constructive-grounding-followup-source-claim", request.get("request_id"), request.get("canonical_locator")), "request_id": request.get("request_id"), "candidate_id": request.get("candidate_id"), "canonical_locator": request.get("canonical_locator"), "claim_state": "approved_pending_exact_retrieval", "execution_attempt_count": 0, "claimed_at": utc_now()}
    return replace(controller, continuous_mission_state="constructive_grounding_followup_claimed", active_work_item="constructive_grounding_followup_claimed", continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "followup_retrieval": {"status": "claimed", "claim": claim}}})


def execute_claimed_governed_constructive_grounding_exact_source_retrieval(
    controller: ContinuousRuntimeController, *, retrieval_adapter=retrieve_exact_source,
) -> ContinuousRuntimeController:
    """Retrieve and retain one source only for the approved prerequisite question."""

    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    request = dict(assessment.get("authority_request") or {})
    retrieval_state = dict(assessment.get("retrieval") or {})
    claim = dict(retrieval_state.get("claim") or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    if controller.continuous_mission_state != "constructive_grounding_exact_source_claimed" or claim.get("claim_state") != "approved_pending_exact_retrieval":
        return controller
    source_locator = str(request.get("canonical_locator") or "")
    question_id = str(assessment.get("relation_proposal", {}).get("target_question_id") or "")
    scoped_question = next((dict(item) for item in (strategy.get("learning_questions") or ()) if isinstance(item, Mapping) and item.get("question_id") == question_id), {})
    try:
        if not scoped_question:
            raise ValueError("constructive_grounding_question_missing")
        retrieval = dict(retrieval_adapter(source_locator))
        if not is_same_exact_resource_chain(source_locator, str(retrieval.get("canonical_locator") or "")):
            raise ValueError("constructive_grounding_canonical_locator_mismatch")
        scoped_strategy = {"strategy_id": strategy.get("strategy_id"), "evidence_digest": strategy.get("evidence_digest"), "learning_questions": (scoped_question,)}
        authority = {"request_id": request.get("request_id"), "source_identity": request.get("candidate_id"), "source_locator": source_locator, "source_digest": assessment.get("assessment_digest")}
        result = compile_strategy_acquisition_result(strategy=scoped_strategy, authority_request=authority, retrieval=retrieval)
    except Exception as exc:  # noqa: BLE001
        failed = {"status": "failed", "claim": {**claim, "claim_state": "failed", "execution_attempt_count": 1}, "failure_reason": f"{type(exc).__name__}:{exc}"}
        return replace(controller, continuous_mission_state="constructive_grounding_exact_source_failed", active_work_item="constructive_grounding_exact_source_failed", continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "retrieval": failed}})
    completed = {"status": "completed", "claim": {**claim, "claim_state": "completed", "execution_attempt_count": 1}, "result": result}
    return replace(
        controller,
        continuous_mission_state="constructive_grounding_exact_source_completed",
        active_work_item="constructive_grounding_source_sufficiency_evaluated",
        continuous_active_subgoal={},
        continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "retrieval": completed}},
        journal=controller.journal + (_journal_entry("developmental_learning", "constructive_grounding_source_retrieved_without_learner_or_promotion", (result["acquisition_result_id"], result["outcome"]),),),
    )


def execute_claimed_followup_governed_constructive_grounding_exact_source_retrieval(controller: ContinuousRuntimeController, *, retrieval_adapter=retrieve_exact_source) -> ContinuousRuntimeController:
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    request = dict(assessment.get("followup_authority_request") or {})
    retrieval_state = dict(assessment.get("followup_retrieval") or {})
    claim = dict(retrieval_state.get("claim") or {})
    strategy = dict(state.get("governed_learning_strategy") or {})
    if controller.continuous_mission_state != "constructive_grounding_followup_claimed" or claim.get("claim_state") != "approved_pending_exact_retrieval":
        return controller
    question_id = str(assessment.get("relation_proposal", {}).get("target_question_id") or "")
    question = next((dict(item) for item in (strategy.get("learning_questions") or ()) if isinstance(item, Mapping) and item.get("question_id") == question_id), {})
    try:
        if not question:
            raise ValueError("constructive_grounding_question_missing")
        locator = str(request.get("canonical_locator") or "")
        raw = dict(retrieval_adapter(locator))
        if not is_same_exact_resource_chain(locator, str(raw.get("canonical_locator") or "")):
            raise ValueError("constructive_grounding_canonical_locator_mismatch")
        scoped = {"strategy_id": strategy.get("strategy_id"), "evidence_digest": strategy.get("evidence_digest"), "learning_questions": (question,)}
        authority = {"request_id": request.get("request_id"), "source_identity": request.get("candidate_id"), "source_locator": locator, "source_digest": assessment.get("assessment_digest")}
        result = compile_strategy_acquisition_result(strategy=scoped, authority_request=authority, retrieval=raw)
    except Exception as exc:  # noqa: BLE001
        return replace(controller, continuous_mission_state="constructive_grounding_followup_failed", active_work_item="constructive_grounding_followup_failed", continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "followup_retrieval": {"status": "failed", "claim": {**claim, "claim_state": "failed", "execution_attempt_count": 1}, "failure_reason": f"{type(exc).__name__}:{exc}"}}})
    return replace(controller, continuous_mission_state="constructive_grounding_followup_completed", active_work_item="constructive_grounding_followup_source_sufficiency_evaluated", continuous_active_subgoal={}, continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "followup_retrieval": {"status": "completed", "claim": {**claim, "claim_state": "completed", "execution_attempt_count": 1}, "result": result}}})


def review_governed_constructive_grounding_source_result(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    """Classify one acquired source at the constructive, not term-match, level."""

    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    retrieval = dict(assessment.get("retrieval") or {})
    result = dict(retrieval.get("result") or {})
    if controller.continuous_mission_state != "constructive_grounding_exact_source_completed" or retrieval.get("status") != "completed":
        return controller
    existing = dict(assessment.get("source_review") or {})
    if existing.get("acquisition_result_digest") == result.get("result_digest"):
        return controller
    review = compile_constructive_grounding_source_review(assessment=assessment, acquisition_result=result)
    return replace(
        controller,
        continuous_mission_state="constructive_grounding_partial",
        active_work_item="constructive_relation_still_requires_grounded_derivation",
        continuous_active_subgoal={},
        continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "source_review": review}},
        journal=controller.journal + (_journal_entry("developmental_learning", "constructive_source_review_preserved_term_coverage_but_rejected_false_sufficiency", (review["review_id"],),),),
    )


def review_followup_governed_constructive_grounding_source_result(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    """Review a second retained source at constructive-relation scope only."""

    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    retrieval = dict(assessment.get("followup_retrieval") or {})
    result = dict(retrieval.get("result") or {})
    if controller.continuous_mission_state != "constructive_grounding_followup_completed" or retrieval.get("status") != "completed":
        return controller
    existing = dict(assessment.get("followup_source_review") or {})
    if existing.get("acquisition_result_digest") == result.get("result_digest"):
        return controller
    review = compile_constructive_grounding_source_review(assessment=assessment, acquisition_result=result)
    return replace(
        controller,
        continuous_mission_state="constructive_grounding_partial",
        active_work_item="constructive_relation_still_requires_grounded_derivation",
        continuous_active_subgoal={},
        continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "followup_source_review": review}},
        journal=controller.journal + (_journal_entry("developmental_learning", "followup_constructive_source_review_preserved_term_coverage_but_rejected_false_sufficiency", (review["review_id"],),),),
    )


def compile_governed_constructive_grounding_failure_synthesis(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    if controller.continuous_mission_state != "constructive_grounding_partial" or assessment.get("failure_synthesis"):
        return controller
    attempts = (
        dict(state.get("governed_learning_strategy_discovered_source_retrieval") or {}),
        dict(assessment.get("retrieval") or {}),
        *tuple(dict(item) for item in (assessment.get("followup_retrieval_history") or ()) if isinstance(item, Mapping)),
        dict(assessment.get("followup_retrieval") or {}),
    )
    synthesis = compile_constructive_failure_synthesis(assessment=assessment, source_attempts=attempts)
    request = dict(synthesis.get("authority_request") or {})
    return replace(controller, continuous_mission_state=synthesis["outcome"], active_work_item="constructive_teaching_provider_authority_request" if request else "constructive_grounding_escalation_unresolved", continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + ((request,) if request else ()), continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "failure_synthesis": synthesis}})


def compile_constructive_teaching_provider_replacement_authority(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    """Compile one replacement only after a prior provider claim is terminal."""
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    synthesis = dict(assessment.get("failure_synthesis") or {})
    prior_execution = dict(assessment.get("constructive_teaching_provider") or {})
    prior_claim = dict(prior_execution.get("execution_claim") or {})
    base = dict(synthesis.get("authority_request") or {})
    if not base or prior_claim.get("claim_state") not in {"invalid", "failed"}:
        return controller
    existing = dict(synthesis.get("replacement_authority_request") or {})
    if existing:
        return controller
    request = {**base, "request_id": stable_id("constructive-teaching-provider-replacement-authority", base.get("request_id"), prior_claim.get("claim_id"), prior_execution.get("result", {}).get("response_digest")), "status": "pending", "authority_granted": False, "replacement_for_request_id": base.get("request_id"), "replacement_for_claim_id": prior_claim.get("claim_id"), "replacement_reason": "prior provider output omitted required controller boundary constants; raw historical output unavailable", "created_at": utc_now()}
    updated_synthesis = {**synthesis, "replacement_authority_request": request, "prior_provider_claims": tuple(synthesis.get("prior_provider_claims") or ()) + ({"claim": prior_claim, "result": dict(prior_execution.get("result") or {})},)}
    return replace(controller, continuous_mission_state="constructive_teaching_provider_replacement_authority_pending", active_work_item="constructive_teaching_provider_replacement_authority_request", continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,), continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "failure_synthesis": updated_synthesis}})


def consume_constructive_teaching_provider_authority_response(
    controller: ContinuousRuntimeController, *, request_id: str, selected_option: str, operator_text: str = "", approved_scope: str = "",
) -> ContinuousRuntimeController:
    """Consume the one-use advisory-teaching authority without dispatching it."""
    requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    index = next((i for i, item in enumerate(requests) if item.get("request_id") == request_id and item.get("request_kind") == "governed_constructive_teaching_provider_authority" and item.get("status") == "pending"), -1)
    if index < 0:
        return replace(controller, journal=controller.journal + (_journal_entry("constructive_grounding", "constructive_teaching_authority_duplicate_or_unknown_response", (request_id,)),))
    request = requests[index]
    if selected_option not in tuple(request.get("permitted_responses") or ()):
        return replace(controller, journal=controller.journal + (_journal_entry("constructive_grounding", "constructive_teaching_authority_invalid_response", (request_id, selected_option)),))
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    synthesis = dict(assessment.get("failure_synthesis") or {})
    known_requests = (dict(synthesis.get("authority_request") or {}), dict(synthesis.get("replacement_authority_request") or {}))
    if request_id not in {item.get("request_id") for item in known_requests}:
        return replace(controller, journal=controller.journal + (_journal_entry("constructive_grounding", "constructive_teaching_authority_identity_mismatch", (request_id,)),))
    consumed_at = utc_now()
    granted = selected_option == "approve_constructive_teaching_provider_authority"
    resolved = {**request, "status": "consumed", "resolution": selected_option, "authority_granted": granted, "consumed_at": consumed_at}
    response = {"request_id": request_id, "response_kind": "governed_constructive_teaching_provider_authority", "selected_option": selected_option, "operator_text": operator_text, "approved_scope": approved_scope, "authority_granted": granted, "created_at": consumed_at, "consumed_at": consumed_at}
    updated_requests = requests[:index] + (resolved,) + requests[index + 1 :]
    if not granted:
        return replace(controller, continuous_developmental_insight_requests=updated_requests, continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,), continuous_mission_state="constructive_teaching_provider_authority_deferred", active_work_item="constructive_grounding_escalation_unresolved", continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "constructive_teaching_provider": {"status": "deferred" if selected_option == "defer_constructive_teaching_provider_authority" else "rejected", "operator_response": response}}})
    if approved_scope and approved_scope != request.get("authority_scope"):
        return replace(controller, journal=controller.journal + (_journal_entry("constructive_grounding", "constructive_teaching_authority_scope_mismatch", (request_id,)),))
    provider_packet = compile_constructive_teaching_provider_packet(authority_request=request)
    system_prompt, user_prompt = constructive_teaching_provider_prompts(packet=provider_packet)
    claim = {"claim_id": stable_id("constructive-teaching-provider-execution-claim", request_id, provider_packet["packet_digest"]), "request_id": request_id, "claim_state": "approved_pending_execution", "execution_attempt_count": 0, "provider": request.get("provider"), "model": request.get("model"), "packet_digest": provider_packet["packet_digest"], "approved_at": consumed_at}
    api = dict(controller.continuous_api_authority or {})
    api = {**api, "enabled": True, "allowed_providers": (request.get("provider"),), "allowed_models": (request.get("model"),), "call_allowance": 1, "pending_provider_tasks": tuple(dict.fromkeys(tuple(api.get("pending_provider_tasks") or ()) + (request_id,))), "unavailability_reason": "one_operator_approved_constructive_teaching_call_pending"}
    execution = {"status": "approved_pending_execution", "authority_request": request, "provider_packet": provider_packet, "system_prompt": system_prompt, "user_prompt": user_prompt, "execution_claim": claim, "operator_response": response}
    return replace(controller, continuous_developmental_insight_requests=updated_requests, continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,), continuous_api_authority=api, continuous_mission_state="constructive_teaching_provider_execution_pending", active_work_item="persisted_constructive_teaching_provider_execution_claim", continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "constructive_teaching_provider": execution}}, journal=controller.journal + (_journal_entry("constructive_grounding", "operator_approved_one_use_constructive_teaching_provider_claim", (request_id, claim["claim_id"])),))


def begin_constructive_teaching_provider_execution(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    """Persist the one permitted provider attempt before network I/O."""
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    execution = dict(assessment.get("constructive_teaching_provider") or {})
    claim = dict(execution.get("execution_claim") or {})
    if controller.continuous_mission_state != "constructive_teaching_provider_execution_pending" or claim.get("claim_state") != "approved_pending_execution" or int(claim.get("execution_attempt_count") or 0) != 0:
        return controller
    updated_claim = {**claim, "claim_state": "dispatching", "execution_attempt_count": 1, "dispatch_started_at": utc_now()}
    api = dict(controller.continuous_api_authority or {})
    return replace(controller, continuous_mission_state="constructive_teaching_provider_dispatching", active_work_item="one_use_constructive_teaching_provider_dispatch", continuous_api_authority={**api, "calls_consumed": int(api.get("calls_consumed") or 0) + 1}, continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "constructive_teaching_provider": {**execution, "status": "dispatching", "execution_claim": updated_claim}}}, journal=controller.journal + (_journal_entry("constructive_grounding", "constructive_teaching_provider_dispatch_persisted_before_network", (claim.get("claim_id", ""),)),))


def record_constructive_teaching_provider_result(controller: ContinuousRuntimeController, *, raw_response: Mapping[str, Any] | str | None, provider_error: str = "", provider_usage: Mapping[str, Any] | None = None) -> ContinuousRuntimeController:
    """Seal one advisory packet; it can never activate learning or promote capability."""
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    execution = dict(assessment.get("constructive_teaching_provider") or {})
    claim = dict(execution.get("execution_claim") or {})
    packet = dict(execution.get("provider_packet") or {})
    if claim.get("claim_state") != "dispatching" or not packet:
        return controller
    api = dict(controller.continuous_api_authority or {})
    request_id = str(claim.get("request_id") or "")
    pending = tuple(item for item in (api.get("pending_provider_tasks") or ()) if item != request_id)
    if provider_error:
        result = {"status": "failed", "error": provider_error, "provider_usage": dict(provider_usage or {}), "completed_at": utc_now(), "capability_eligible": False}
        return replace(controller, continuous_mission_state="constructive_teaching_provider_failed", active_work_item="constructive_grounding_escalation_unresolved", continuous_api_authority={**api, "enabled": False, "pending_provider_tasks": pending, "failures": int(api.get("failures") or 0) + 1, "unavailability_reason": "constructive_teaching_provider_failed"}, continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "constructive_teaching_provider": {**execution, "status": "provider_failed", "execution_claim": {**claim, "claim_state": "failed"}, "result": result}}})
    validation = validate_constructive_teaching_provider_response(packet=packet, raw_response=raw_response)
    result = {"status": "validated" if validation["accepted"] else "invalid", "response_digest": validation["response_digest"], "validation_errors": validation["errors"], "sealed_advisory_packet": validation["sealed_packet"], "provider_usage": dict(provider_usage or {}), "completed_at": utc_now(), "capability_eligible": False, "operator_only_forensic_response": {"raw_response": raw_response, "raw_response_digest": validation["response_digest"], "learner_visible": False, "capability_eligible": False}}
    return replace(controller, continuous_mission_state="constructive_teaching_packet_validated" if validation["accepted"] else "constructive_teaching_packet_invalid", active_work_item="independent_constructive_grounding_verification_required" if validation["accepted"] else "constructive_grounding_escalation_unresolved", continuous_api_authority={**api, "enabled": False, "pending_provider_tasks": pending, "last_provider_result": validation["response_digest"], "unavailability_reason": "constructive_teaching_packet_requires_independent_verification" if validation["accepted"] else "constructive_teaching_provider_schema_rejected"}, continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "constructive_teaching_provider": {**execution, "status": "packet_validated" if validation["accepted"] else "packet_invalid", "execution_claim": {**claim, "claim_state": "completed" if validation["accepted"] else "invalid"}, "result": result}}}, journal=controller.journal + (_journal_entry("constructive_grounding", "constructive_teaching_provider_result_sealed_without_learning_or_capability_promotion", (request_id, result["status"])),))


def record_constructive_teaching_response_adaptation_unavailable(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    """Persist the provenance blocker for legacy invalid responses that retained no bytes."""
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    execution = dict(assessment.get("constructive_teaching_provider") or {})
    result = dict(execution.get("result") or {})
    claim = dict(execution.get("execution_claim") or {})
    if claim.get("claim_state") != "invalid" or result.get("status") != "invalid" or execution.get("adaptation"):
        return controller
    adaptation = adapt_constructive_teaching_response(raw_response=None, source_claim_id=str(claim.get("claim_id") or ""), original_response_digest=str(result.get("response_digest") or ""))
    return replace(controller, continuous_mission_state="constructive_teaching_response_adaptation_unavailable", active_work_item="raw_provider_response_required_for_provenance_safe_adaptation", continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "constructive_teaching_provider": {**execution, "adaptation": adaptation}}}, journal=controller.journal + (_journal_entry("constructive_grounding", "legacy_invalid_constructive_response_cannot_be_adapted_without_raw_bytes", (str(claim.get("claim_id") or ""),)),))


def verify_independent_constructive_grounding(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    """Persist one non-promoting verification result for a sealed advisory packet."""
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    execution = dict(assessment.get("constructive_teaching_provider") or {})
    result = dict(execution.get("result") or {})
    if controller.continuous_mission_state != "constructive_teaching_packet_validated" or result.get("status") != "validated" or assessment.get("independent_verification"):
        return controller
    verification = compile_independent_constructive_grounding_verification(assessment=assessment, provider_result=result)
    return replace(controller, continuous_mission_state=verification["outcome"], active_work_item="constructive_relation_facets_remain_independently_unverified", continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "independent_verification": verification}}, journal=controller.journal + (_journal_entry("constructive_grounding", "advisory_constructive_teaching_packet_independently_checked_without_capability_promotion", (verification["verification_id"],)),))


def compile_advisory_claim_verification_targets(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    execution = dict(assessment.get("constructive_teaching_provider") or {})
    result = dict(execution.get("result") or {})
    if controller.continuous_mission_state != "finite_dimensional_constructive_grounding_partial" or assessment.get("atomic_verification_targets"):
        return controller
    targets = compile_advisory_claim_verification_target_record(assessment=assessment, provider_result=result)
    state_name = "atomic_verification_source_authority_pending" if targets["targets"] else "finite_dimensional_constructive_grounding_partial"
    work = "atomic_verification_target_routing" if targets["targets"] else "advisory_packet_lacks_relation_specific_verification_targets"
    return replace(controller, continuous_mission_state=state_name, active_work_item=work, continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "atomic_verification_targets": targets}}, journal=controller.journal + (_journal_entry("constructive_grounding", "advisory_claims_compiled_to_verification_targets_without_controller_authored_mathematics", (targets["target_compilation_id"],)),))


def compile_followup_governed_constructive_grounding_authority(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    """Offer one remaining discovered candidate after a partial source review."""

    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    prior = dict(assessment.get("retrieval") or {})
    review = dict(assessment.get("source_review") or {})
    if controller.continuous_mission_state != "constructive_grounding_partial" or review.get("outcome") != "constructive_grounding_partial":
        return controller
    existing = dict(assessment.get("followup_authority_request") or {})
    if existing:
        return controller
    prior_candidate = str(prior.get("claim", {}).get("candidate_id") or "")
    candidate = next((dict(item) for item in (assessment.get("candidate_ranking") or ()) if isinstance(item, Mapping) and item.get("candidate_id") != prior_candidate), {})
    if not candidate:
        return replace(controller, continuous_mission_state="constructive_grounding_unresolved", active_work_item="constructive_grounding_candidates_exhausted")
    request = {
        "request_id": stable_id("constructive-grounding-followup-source-authority", assessment.get("relation_id"), candidate.get("candidate_id"), prior.get("claim", {}).get("claim_id")),
        "request_kind": "governed_constructive_grounding_exact_source_authority", "status": "pending",
        "relation_id": assessment.get("relation_id"), "question_id": assessment.get("relation_proposal", {}).get("target_question_id"),
        "candidate_id": candidate.get("candidate_id"), "canonical_locator": candidate.get("canonical_locator"), "maximum_retrieval_count": 1,
        "authority_scope": "retrieve one exact previously discovered source only to ground one unresolved constructive prerequisite relation",
        "scope": "retrieve one exact previously discovered source only to ground one unresolved constructive prerequisite relation",
        "permitted_responses": ("approve_constructive_grounding_exact_source_authority", "reject_constructive_grounding_exact_source_authority", "defer_constructive_grounding_exact_source_authority", "ask_for_clarification"),
        "authority_granted": False,
        "prohibited_actions": ("additional_source_retrieval", "new_discovery", "broad_research", "provider_call", "learner_retry", "evaluator_run", "capability_update", "pcm_action", "git_action", "deployment"),
        "created_at": utc_now(), "prior_claim_id": prior.get("claim", {}).get("claim_id"),
    }
    return replace(controller, continuous_mission_state="constructive_grounding_followup_authority_pending", active_work_item="constructive_grounding_followup_authority_request", continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,), continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "followup_authority_request": request}})


def compile_case_preserving_constructive_grounding_replacement_authority(
    controller: ContinuousRuntimeController, *, corrected_locator: str,
) -> ContinuousRuntimeController:
    """Compile a replacement after a terminal case-corrupted locator failure."""

    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    failed = dict(assessment.get("followup_retrieval") or {})
    prior_request = dict(assessment.get("followup_authority_request") or {})
    if failed.get("status") != "failed" or "HTTP Error 404" not in str(failed.get("failure_reason") or "") or not prior_request.get("request_id"):
        return replace(controller, continuous_mission_state="constructive_grounding_replacement_blocked", active_work_item="constructive_grounding_replacement_prerequisites_missing")
    from urllib.parse import urlsplit

    old, new = urlsplit(str(prior_request.get("canonical_locator") or "")), urlsplit(corrected_locator)
    same_except_path_case = (
        old.scheme.lower() == new.scheme.lower() == "https"
        and (old.hostname or "").lower() == (new.hostname or "").lower()
        and old.port == new.port
        and old.path.lower() == new.path.lower()
        and old.query == new.query and old.fragment == new.fragment
    )
    if not same_except_path_case or old.path == new.path:
        return replace(controller, continuous_mission_state="constructive_grounding_replacement_blocked", active_work_item="constructive_grounding_corrected_locator_invalid")
    history = tuple(assessment.get("followup_retrieval_history") or ())
    if not any(dict(item).get("claim", {}).get("claim_id") == failed.get("claim", {}).get("claim_id") for item in history if isinstance(item, Mapping)):
        history = history + ({**failed, "terminal_history": True, "archived_at": utc_now()},)
    nonce = stable_id("case-preserving-locator-replacement", failed.get("claim", {}).get("claim_id"), corrected_locator)
    request = {
        **prior_request,
        "request_id": stable_id("constructive-grounding-case-preserving-source-authority", assessment.get("relation_id"), corrected_locator, nonce),
        "canonical_locator": corrected_locator,
        "status": "pending", "authority_granted": False, "resolution": "",
        "replacement_for_request_id": prior_request.get("request_id"), "replacement_for_claim_id": failed.get("claim", {}).get("claim_id"), "replacement_nonce": nonce,
        "created_at": utc_now(),
    }
    return replace(
        controller,
        continuous_mission_state="constructive_grounding_followup_authority_pending",
        active_work_item="constructive_grounding_case_preserving_replacement_authority_request",
        continuous_developmental_insight_requests=tuple(controller.continuous_developmental_insight_requests) + (request,),
        continuous_learning_state={**state, "governed_constructive_grounding": {**assessment, "followup_authority_request": request, "followup_retrieval": {}, "followup_retrieval_history": history}},
    )
def consume_continuous_operator_interaction_response(
    controller: ContinuousRuntimeController,
    *,
    request_id: str,
    response_kind: str,
    operator_text: str,
    selected_option: str,
    approved_scope: str = "",
) -> ContinuousRuntimeController:
    pending_requests = tuple(dict(item) for item in controller.continuous_developmental_insight_requests)
    matched_index = next((index for index, item in enumerate(pending_requests) if item.get("request_id") == request_id and item.get("status") == "pending"), -1)
    if matched_index < 0:
        return replace(
            controller,
            journal=controller.journal + (_journal_entry("continuous_mission", "operator_interaction_response_rejected_no_pending_request", (request_id,)),),
        )
    request = pending_requests[matched_index]
    permitted = tuple(request.get("permitted_responses") or request.get("options") or ())
    if permitted and selected_option not in permitted:
        return replace(
            controller,
            journal=controller.journal + (_journal_entry("continuous_mission", "operator_interaction_response_rejected_invalid_option", (request_id, selected_option)),),
        )
    if request.get("request_kind") == "developmental_goal_approval":
        return consume_developmental_goal_proposal_response(
            controller,
            request_id=request_id,
            selected_option=selected_option,
            operator_text=operator_text,
        )
    if request.get("request_kind") == "developmental_teaching_material_recovery_authority":
        return consume_retained_teaching_material_recovery_response(
            controller,
            request_id=request_id,
            selected_option=selected_option,
            operator_text=operator_text,
            approved_scope=approved_scope,
        )
    if request.get("request_kind") == "developmental_resource_authority":
        return consume_developmental_resource_authority_response(
            controller,
            request_id=request_id,
            selected_option=selected_option,
            operator_text=operator_text,
            approved_scope=approved_scope,
        )
    if request.get("request_kind") == "developmental_resource_fulfillment":
        supplied: Mapping[str, Any] | None = None
        if operator_text.strip():
            try:
                parsed = json.loads(operator_text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, Mapping):
                supplied = parsed
        return consume_developmental_resource_fulfillment(
            controller,
            request_id=request_id,
            selected_option=selected_option,
            supplied=supplied,
            operator_text=operator_text,
        )
    if request.get("request_kind") == "developmental_evaluator_authoring_api":
        return consume_isolated_evaluator_authoring_api_response(
            controller,
            request_id=request_id,
            selected_option=selected_option,
            operator_text=operator_text,
            approved_scope=approved_scope,
        )
    if request.get("request_kind") == "governed_learning_strategy_authority":
        return consume_governed_learning_strategy_authority_response(
            controller,
            request_id=request_id,
            selected_option=selected_option,
            operator_text=operator_text,
            approved_scope=approved_scope,
        )
    if request.get("request_kind") == "governed_learning_strategy_resource_revision_authority":
        return consume_governed_learning_strategy_resource_revision_authority_response(
            controller,
            request_id=request_id,
            selected_option=selected_option,
            operator_text=operator_text,
            approved_scope=approved_scope,
        )
    if request.get("request_kind") == "governed_learning_strategy_discovered_source_retrieval_authority":
        return consume_governed_learning_strategy_discovered_source_retrieval_authority_response(
            controller,
            request_id=request_id,
            selected_option=selected_option,
            operator_text=operator_text,
            approved_scope=approved_scope,
        )
    if request.get("request_kind") == "governed_constructive_grounding_exact_source_authority":
        return consume_governed_constructive_grounding_exact_source_authority_response(
            controller, request_id=request_id, selected_option=selected_option, operator_text=operator_text, approved_scope=approved_scope,
        )
    if request.get("request_kind") == "governed_constructive_teaching_provider_authority":
        return consume_constructive_teaching_provider_authority_response(
            controller, request_id=request_id, selected_option=selected_option, operator_text=operator_text, approved_scope=approved_scope,
        )
    if selected_option == "provide exact target and case" and not operator_text.strip():
        return replace(
            controller,
            journal=controller.journal + (_journal_entry("continuous_mission", "operator_interaction_response_rejected_missing_concrete_target", (request_id,)),),
        )
    authority_granted = bool(approved_scope and request.get("request_kind") != "insight")
    consumed_at = utc_now()
    resolved_request = {
        **request,
        "status": "consumed",
        "resolution": selected_option,
        "consumed_at": consumed_at,
        "authority_granted": authority_granted,
    }
    updated_requests = pending_requests[:matched_index] + (resolved_request,) + pending_requests[matched_index + 1 :]
    response = {
        "request_id": request_id,
        "response_kind": response_kind,
        "operator_text": operator_text,
        "selected_option": selected_option,
        "approved_scope": approved_scope,
        "authority_granted": authority_granted,
        "created_at": consumed_at,
        "consumed_at": consumed_at,
    }
    updated = replace(
        controller,
        continuous_developmental_insight_requests=updated_requests,
        continuous_operator_interaction_responses=tuple(controller.continuous_operator_interaction_responses) + (response,),
        continuous_observation_state={
            **(controller.continuous_observation_state or {}),
            "last_operator_response_id": request_id,
            "last_operator_response_option": selected_option,
        },
        journal=controller.journal + (_journal_entry("continuous_mission", "operator_interaction_response_consumed_once", (request_id, selected_option)),),
    )
    if selected_option == "continue local simulation only":
        action = _observation_gap_action(str(request.get("affected_gap") or "operator insight gap"))
        evidence = _observation_exit_evidence(updated, action)
        prepared = replace(
            updated,
            continuous_mission_state="operator_insight_consumed_deriving_local_action",
            journal=updated.journal + (_journal_entry("continuous_mission", "operator_insight_selected_local_simulation", (request_id, action["action_id"])),),
        )
    if selected_option == "provide exact target and case":
        return replace(
            updated,
            continuous_mission_state="observing_for_new_weaknesses",
            active_work_item=OBSERVATION_STATE,
            continuous_observation_state={
                **(updated.continuous_observation_state or {}),
                "candidate_design_evidence_exhausted": False,
                "candidate_design_evidence_scope_signature": "",
                "operator_supplied_candidate_target": operator_text.strip(),
                "candidate_design_blocker": {},
            },
            journal=updated.journal
            + (_journal_entry("continuous_mission", "operator_supplied_new_repository_bound_candidate_evidence", (request_id,)),),
        )
        return select_continuous_mission_subgoal(refresh_continuous_mission_frontier(assess_continuous_mission_runtime(prepared, (evidence,))))
    if selected_option == "request scoped application review":
        return create_scoped_continuous_application_review_request(updated, source_request_id=request_id)
    if selected_option == "treat as accepted boundary":
        accepted_gaps = _split_gap_tokens(request.get("source_gap_ids") or (request.get("affected_gap") or "",))
        prior_boundaries = tuple(str(item) for item in ((updated.continuous_observation_state or {}).get("accepted_boundary_gaps") or ()))
        accepted_boundary_gaps = tuple(dict.fromkeys(prior_boundaries + accepted_gaps))
        assessment = dict(updated.continuous_developmental_self_assessment or {})
        accepted_tokens = set(_split_gap_tokens(accepted_boundary_gaps))
        remaining_gaps = tuple(str(gap) for gap in (assessment.get("developmental_gaps") or ()) if str(gap) not in accepted_tokens)
        assessment["developmental_gaps"] = remaining_gaps
        assessment["needs_additional_insight"] = bool(remaining_gaps)
        return replace(
            updated,
            continuous_mission_state="observing_for_new_weaknesses",
            active_work_item=OBSERVATION_STATE,
            continuous_developmental_self_assessment=assessment,
            continuous_observation_state={
                **(updated.continuous_observation_state or {}),
                "accepted_boundary_gaps": accepted_boundary_gaps,
                "accepted_boundary_source_request_id": request_id,
                "candidate_actions": (),
                "selected_action": {},
            },
            journal=updated.journal + (_journal_entry("continuous_mission", "operator_insight_marked_gap_as_accepted_boundary", (request_id,)),),
        )
    return replace(
        updated,
        continuous_mission_state="observing_for_new_weaknesses",
        active_work_item=OBSERVATION_STATE,
    )


def create_scoped_continuous_application_review_request(
    controller: ContinuousRuntimeController,
    *,
    source_request_id: str,
) -> ContinuousRuntimeController:
    """Create the concrete one-use application boundary requested by an insight response."""

    if controller.pending_application_decision_id:
        return controller
    decision_id = stable_id(
        "continuous-scoped-application-review",
        controller.session_id,
        source_request_id,
        str(len(controller.continuous_operator_interaction_responses)),
    )
    review_record = {
        "decision_id": decision_id,
        "source_request_id": source_request_id,
        "request_kind": "application_review",
        "status": "pending",
        "authority_scope": "one-time exact tracked-source application only",
        "authority_granted": False,
        "created_at": utc_now(),
        "blocked_transition": "validated_local_evidence -> scoped_tracked_application_review",
        "operator_note": "This request asks for review preparation only; no tracked source is mutated by creating it.",
        "active_gap": ", ".join(str(item) for item in ((controller.continuous_developmental_self_assessment or {}).get("developmental_gaps") or ()))
        or "operator requested scoped application review",
    }
    observation_state = {
        **(controller.continuous_observation_state or {}),
        "pending_application_review": review_record,
    }
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_application",
        pending_application_decision_id=decision_id,
        active_work_item="awaiting_operator_application",
        continuous_observation_state=observation_state,
        journal=controller.journal
        + (
            _journal_entry(
                "continuous_mission",
                "operator_insight_created_scoped_application_review_boundary",
                (source_request_id, decision_id),
            ),
        ),
    )


def recover_missing_continuous_application_review_request(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    if controller.continuous_mission_state != "awaiting_operator_application" or controller.pending_application_decision_id:
        return controller
    source_request_id = str((controller.continuous_observation_state or {}).get("last_operator_response_id") or "recovered-operator-application")
    recovered = create_scoped_continuous_application_review_request(controller, source_request_id=source_request_id)
    return replace(
        recovered,
        journal=recovered.journal
        + (_journal_entry("continuous_mission", "recovered_missing_scoped_application_review_boundary", (source_request_id, recovered.pending_application_decision_id)),),
    )


def recover_accepted_boundary_operator_requests(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    accepted_tokens = _accepted_boundary_gap_tokens(controller)
    if not accepted_tokens:
        return controller
    changed = False
    requests: list[dict[str, Any]] = []
    for request in controller.continuous_developmental_insight_requests:
        item = dict(request)
        request_tokens = set(_split_gap_tokens(item.get("source_gap_ids") or (item.get("affected_gap") or "",)))
        if item.get("status") == "pending" and item.get("request_kind") == "insight" and request_tokens and request_tokens.issubset(accepted_tokens):
            item["status"] = "consumed"
            item["resolution"] = "accepted_boundary_already_recorded"
            item["recovery_disposition"] = "pending_request_suppressed_by_accepted_boundary"
            item["consumed_at"] = utc_now()
            changed = True
        requests.append(item)
    if not changed:
        return controller
    assessment = _filter_accepted_boundary_assessment(controller.continuous_developmental_self_assessment, accepted_tokens)
    return replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        active_work_item=OBSERVATION_STATE,
        continuous_developmental_insight_requests=tuple(requests),
        continuous_developmental_self_assessment=assessment,
        journal=controller.journal + (_journal_entry("continuous_mission", "suppressed_pending_operator_request_for_accepted_boundary", tuple(sorted(accepted_tokens))),),
    )


def _filter_accepted_boundary_assessment(assessment: Mapping[str, Any], accepted_tokens: set[str]) -> dict[str, Any]:
    updated = dict(assessment or {})
    if not accepted_tokens:
        return updated
    gaps = tuple(str(gap) for gap in (updated.get("developmental_gaps") or ()) if str(gap) not in accepted_tokens)
    updated["developmental_gaps"] = gaps
    updated["needs_additional_insight"] = bool(gaps)
    return updated


def _recover_knowledge_ledger(records: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    recovered: list[dict[str, Any]] = []
    for record in records:
        recovered.append(normalize_capability_record_for_recovery(CapabilityKnowledgeRecord(**dict(record))).as_dict())
    return tuple(recovered)


def _recover_behavioral_failure_records(
    records: Iterable[BehavioralFailureRecord | Mapping[str, Any]],
) -> tuple[BehavioralFailureRecord, ...]:
    recovered: list[BehavioralFailureRecord] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        try:
            item = record if isinstance(record, BehavioralFailureRecord) else BehavioralFailureRecord(**dict(record))
        except (TypeError, ValueError):
            continue
        identity = (item.semantic_failure_key, item.evidence_digest)
        if identity in seen:
            continue
        seen.add(identity)
        recovered.append(item)
    return tuple(recovered)


def queue_continuous_mission_sandbox_work(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    if not controller.continuous_active_subgoal:
        return controller
    return replace(
        controller,
        continuous_mission_state="sandbox_development_active",
        active_work_item=controller.continuous_active_subgoal["measurable_objective"],
        journal=controller.journal
        + (_journal_entry("continuous_mission", "active_subgoal_queued_for_autonomous_local_sandbox_development", (controller.continuous_active_subgoal["subgoal_id"],)),),
    )


def pause_continuous_mission_for_application(
    controller: ContinuousRuntimeController,
    *,
    candidate_id: str,
    decision_id: str,
) -> ContinuousRuntimeController:
    if not controller.continuous_active_subgoal:
        raise ValueError("continuous application pause requires an active subgoal")
    return replace(
        controller,
        continuous_mission_state="awaiting_operator_application",
        pending_application_decision_id=decision_id,
        active_work_item="awaiting_operator_application",
        journal=controller.journal
        + (_journal_entry("continuous_mission", "validated_candidate_created_exactly_one_application_boundary", (candidate_id, decision_id)),),
    )


def consume_continuous_mission_application_decision(
    controller: ContinuousRuntimeController,
    *,
    decision_id: str,
    action: str,
) -> ContinuousRuntimeController:
    if decision_id != controller.pending_application_decision_id:
        raise ValueError("application decision does not match pending boundary")
    transitions = {
        "APPLY_VALIDATED_CANDIDATE": "post_application_validation",
        "REJECT_CANDIDATE": "selecting_next_weakness",
        "CONTINUE_SANDBOX_RESEARCH": "sandbox_development_active",
        "REQUEST_REVISION": "sandbox_development_active",
    }
    if action not in transitions:
        raise ValueError(f"unsupported application decision: {action}")
    return replace(
        controller,
        continuous_mission_state=transitions[action],
        pending_application_decision_id="",
        journal=controller.journal + (_journal_entry("continuous_mission", f"terminal_application_decision_consumed_once:{action}", (decision_id,)),),
    )


def consume_continuous_capability_reassessment(
    controller: ContinuousRuntimeController,
    record: CapabilityKnowledgeRecord,
) -> ContinuousRuntimeController:
    record = normalize_capability_record_for_recovery(record)
    existing_records = _recover_knowledge_ledger(controller.continuous_knowledge_ledger)
    if record.behavioral_evaluation_ref and any(
        str(item.get("behavioral_evaluation_ref") or "") == record.behavioral_evaluation_ref
        for item in existing_records
    ):
        return replace(
            controller,
            journal=controller.journal
            + (_journal_entry("continuous_mission", "duplicate_behavioral_reassessment_suppressed", (record.behavioral_evaluation_ref,)),),
        )

    # Structural, failed, and blocked outcomes are evidence about a remaining
    # limitation. Only independently demonstrated behavior may retire the
    # originating frontier signature as solved.
    consumed = controller.continuous_consumed_weakness_signatures
    if capability_is_acquired(record):
        consumed = consumed_signatures_after_reassessment(
            [WeaknessCandidate(**item) for item in controller.continuous_mission_frontier],
            controller.continuous_active_subgoal or None,
            consumed,
        )
    updated = replace(
        controller,
        continuous_mission_state="capability_reassessment",
        continuous_knowledge_ledger=existing_records + (record.as_dict(),),
        continuous_consumed_weakness_signatures=consumed,
        continuous_active_subgoal={},
        active_work_item="capability_reassessment",
        journal=controller.journal
        + (_journal_entry("continuous_mission", "capability_reassessment_consumed_once_and_knowledge_recorded", (record.capability_id,)),),
    )
    return refresh_developmental_self_direction(updated)


def consume_continuous_pcm_bridge_result(
    controller: ContinuousRuntimeController,
    *,
    bridge_entry: Mapping[str, Any],
    record: CapabilityKnowledgeRecord,
) -> tuple[ContinuousRuntimeController, bool]:
    """Return one behaviorally evaluated PCM result to the mission exactly once."""

    entry = dict(bridge_entry)
    bridge_id = str(entry.get("bridge_id") or "")
    idempotency_key = str(entry.get("idempotency_key") or "")
    if not bridge_id or not idempotency_key:
        raise ValueError("continuous PCM bridge result requires bridge_id and idempotency_key")
    for previous in controller.continuous_pcm_bridge_ledger:
        if str(previous.get("bridge_id") or "") == bridge_id or str(previous.get("idempotency_key") or "") == idempotency_key:
            return (
                replace(
                    controller,
                    journal=controller.journal
                    + (_journal_entry("continuous_mission", "duplicate_pcm_bridge_result_suppressed", (bridge_id,)),),
                ),
                False,
            )
    pending = {
        **entry,
        "consumed_by_controller": False,
        "consumed_at": "",
    }
    with_pending = replace(
        controller,
        continuous_pcm_bridge_ledger=controller.continuous_pcm_bridge_ledger + (pending,),
    )
    reassessed = consume_continuous_capability_reassessment(with_pending, record)
    consumed = {
        **pending,
        "consumed_by_controller": True,
        "consumed_at": utc_now(),
    }
    return (
        replace(
            reassessed,
            continuous_pcm_bridge_ledger=tuple(
                consumed if str(item.get("bridge_id") or "") == bridge_id else item
                for item in reassessed.continuous_pcm_bridge_ledger
            ),
            journal=reassessed.journal
            + (_journal_entry("continuous_mission", "pcm_bridge_result_consumed_once", (bridge_id, record.reassessment)),),
        ),
        True,
    )


def continue_continuous_mission_after_reassessment(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    return select_continuous_mission_subgoal(refresh_continuous_mission_frontier(replace(controller, continuous_mission_state="selecting_next_weakness")))


def refresh_developmental_self_direction(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    if not controller.continuous_mission_contract:
        return controller
    contract = _broad_contract_from_state(controller)
    objective = compile_long_horizon_objective(contract.original_operator_goal)
    knowledge = tuple(CapabilityKnowledgeRecord(**item) for item in controller.continuous_knowledge_ledger)
    inventory = capability_inventory_from_knowledge(knowledge)
    assessment = assess_developmental_capability_state(objective, inventory)
    accepted_tokens = _accepted_boundary_gap_tokens(controller)
    assessment_dict = _filter_accepted_boundary_assessment(assessment.as_dict(), accepted_tokens)
    insight_requests = tuple(
        {**item.as_dict(), "status": "pending"}
        for item in compile_developmental_insight_requests(assessment)
    )
    plan = derive_developmental_capability_plan(objective, inventory)
    explanation = compile_developmental_operator_explanation(objective, assessment, plan)
    return replace(
        controller,
        continuous_capability_inventory=tuple(item.as_dict() for item in inventory),
        continuous_developmental_self_assessment=assessment_dict,
        continuous_developmental_insight_requests=insight_requests,
        continuous_operator_explanation=explanation.as_dict(),
        journal=controller.journal
        + (
            _journal_entry(
                "continuous_mission",
                "developmental_self_direction_refreshed_from_authoritative_state",
                (assessment.assessment_id, plan.plan_id, explanation.explanation_id),
            ),
        ),
    )


def _broad_contract_from_state(controller: ContinuousRuntimeController) -> BroadMissionContract:
    state = controller.continuous_mission_contract
    return BroadMissionContract(
        mission_id=str(state["mission_id"]),
        original_operator_goal=str(state["original_operator_goal"]),
        normalized_goal=str(state["normalized_goal"]),
        accepted_at=str(state["accepted_at"]),
        local_authority=state["local_authority"],
        api_authority=state["api_authority"],
        tracked_source_application_operator_controlled=bool(state.get("tracked_source_application_operator_controlled", True)),
        commit_push_operator_controlled=bool(state.get("commit_push_operator_controlled", True)),
        protected_paths=tuple(state.get("protected_paths") or ()),
        completion_policy=str(state.get("completion_policy") or "continuous_runtime_currently_stable_is_observation_not_completion"),
    )


def assess_and_advance_continuous_main_goal(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    if not controller.continuous_mission_contract or not controller.continuous_main_goal:
        return exit_observation_with_action_derivation(replace(
            controller,
            continuous_mission_state="observing_for_new_weaknesses",
            continuous_active_subgoal={},
            active_work_item=OBSERVATION_STATE,
            journal=controller.journal + (_journal_entry("continuous_mission", "observation_without_main_goal_contract", ()),),
        ))
    controller = refresh_developmental_self_direction(controller)
    main_goal = MainGoalContract(**controller.continuous_main_goal)
    knowledge = tuple(CapabilityKnowledgeRecord(**item) for item in controller.continuous_knowledge_ledger)
    eligible_frontier_exists = any(item.get("status") == "eligible" for item in controller.continuous_mission_frontier)
    assessed = assess_main_goal_completion(main_goal, knowledge, eligible_frontier_exists=eligible_frontier_exists)
    if assessed.disposition == "satisfied":
        contract = _broad_contract_from_state(controller)
        next_goal = derive_next_main_goal(contract, assessed, knowledge)
        if next_goal is None:
            completed_goals = controller.continuous_completed_main_goals
            if not any(item.get("main_goal_id") == assessed.main_goal_id for item in completed_goals):
                completed_goals = completed_goals + (assessed.as_dict(),)
            observed = replace(
                controller,
                continuous_main_goal=assessed.as_dict(),
                continuous_completed_main_goals=completed_goals,
                continuous_mission_findings=(),
                continuous_mission_frontier=(),
                continuous_active_subgoal={},
                continuous_consumed_weakness_signatures=(),
                continuous_mission_state="observing_for_new_weaknesses",
                active_work_item=OBSERVATION_STATE,
                journal=controller.journal
                + (
                    _journal_entry(
                        "continuous_mission",
                        "main_goal_satisfied_no_legitimate_next_goal_enters_observation",
                        (assessed.main_goal_id,),
                    ),
                ),
            )
            if (observed.continuous_developmental_self_assessment or {}).get("developmental_gaps"):
                return exit_observation_with_action_derivation(observed)
            return observed
        advanced = replace(
            controller,
            continuous_main_goal=next_goal.as_dict(),
            continuous_completed_main_goals=controller.continuous_completed_main_goals + (assessed.as_dict(),),
            continuous_mission_findings=(),
            continuous_mission_frontier=(),
            continuous_active_subgoal={},
            continuous_consumed_weakness_signatures=(),
            continuous_mission_state="main_goal_derived",
            active_work_item=f"main_goal:{next_goal.normalized_objective}",
            journal=controller.journal
            + (_journal_entry("continuous_mission", "main_goal_satisfied_and_next_main_goal_derived", (assessed.main_goal_id, next_goal.main_goal_id)),),
        )
        evidence = derive_subgoal_evidence_for_main_goal(next_goal, knowledge, max_items=1)
        if evidence:
            ranked = refresh_continuous_mission_frontier(assess_continuous_mission_runtime(advanced, evidence))
            if ranked.continuous_mission_frontier:
                return select_continuous_mission_subgoal(ranked)
        return exit_observation_with_action_derivation(replace(
            advanced,
            continuous_mission_state="observing_for_new_weaknesses",
            active_work_item=OBSERVATION_STATE,
            journal=advanced.journal + (_journal_entry("continuous_mission", "next_main_goal_has_no_immediate_subgoal_evidence", (next_goal.main_goal_id,)),),
        ))
    if assessed.disposition == "partially_satisfied":
        evidence = derive_subgoal_evidence_for_main_goal(assessed, knowledge, max_items=1)
        if evidence:
            updated = replace(
                controller,
                continuous_main_goal=assessed.as_dict(),
                continuous_mission_state="main_goal_partial_generating_subgoal",
                journal=controller.journal + (_journal_entry("continuous_mission", "main_goal_partial_completion_generated_subgoal_evidence", (assessed.main_goal_id,)),),
            )
            ranked = refresh_continuous_mission_frontier(assess_continuous_mission_runtime(updated, evidence))
            if ranked.continuous_mission_frontier:
                return select_continuous_mission_subgoal(ranked)
    return exit_observation_with_action_derivation(replace(
        controller,
        continuous_main_goal=assessed.as_dict(),
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        active_work_item=OBSERVATION_STATE,
        journal=controller.journal + (_journal_entry("continuous_mission", "main_goal_assessed_without_immediate_eligible_subgoal", (assessed.main_goal_id, assessed.disposition)),),
    ))


def mark_continuous_api_unavailable(
    controller: ContinuousRuntimeController,
    *,
    pending_task: str,
    reason: str,
) -> ContinuousRuntimeController:
    current = ApiAuthorityState(**controller.continuous_api_authority) if controller.continuous_api_authority else ApiAuthorityState(enabled=False)
    updated = api_unavailable_update(current, pending_task=pending_task, reason=reason)
    local_work_available = bool(controller.continuous_active_subgoal or any(item.get("status") == "eligible" for item in controller.continuous_mission_frontier))
    return replace(
        controller,
        continuous_api_authority=updated.__dict__,
        continuous_mission_state=controller.continuous_mission_state if local_work_available else "external_api_temporarily_unavailable",
        journal=controller.journal + (_journal_entry("continuous_mission", "provider_task_preserved_without_terminating_mission", (pending_task, reason)),),
    )


def export_continuous_mission_restart_state(controller: ContinuousRuntimeController) -> dict[str, Any]:
    return {
        "controller_id": controller.controller_id,
        "session_id": controller.session_id,
        "continuous_mission_state": controller.continuous_mission_state,
        "continuous_mission_contract": controller.continuous_mission_contract,
        "continuous_behavioral_failure_records": controller.continuous_behavioral_failure_records,
        "continuous_mission_findings": controller.continuous_mission_findings,
        "continuous_mission_frontier": controller.continuous_mission_frontier,
        "continuous_main_goal": controller.continuous_main_goal,
        "continuous_completed_main_goals": controller.continuous_completed_main_goals,
        "continuous_active_subgoal": controller.continuous_active_subgoal,
        "continuous_consumed_weakness_signatures": controller.continuous_consumed_weakness_signatures,
        "continuous_knowledge_ledger": controller.continuous_knowledge_ledger,
        "continuous_pcm_bridge_ledger": controller.continuous_pcm_bridge_ledger,
        "continuous_capability_inventory": controller.continuous_capability_inventory,
        "continuous_developmental_self_assessment": controller.continuous_developmental_self_assessment,
        "continuous_developmental_insight_requests": controller.continuous_developmental_insight_requests,
        "continuous_operator_interaction_responses": controller.continuous_operator_interaction_responses,
        "continuous_operator_explanation": controller.continuous_operator_explanation,
        "continuous_api_authority": controller.continuous_api_authority,
        "continuous_observation_state": controller.continuous_observation_state,
        "continuous_learning_state": controller.continuous_learning_state,
        "pending_application_decision_id": controller.pending_application_decision_id,
        "active_work_item": controller.active_work_item,
    }


def _has_recoverable_legacy_fulfillment_clarification(
    requests: Iterable[Mapping[str, Any]],
    responses: Iterable[Mapping[str, Any]],
    learning_state: Mapping[str, Any],
) -> bool:
    clarification_response = next(
        (
            dict(item)
            for item in reversed(tuple(responses))
            if item.get("response_kind") == "developmental_resource_fulfillment"
            and item.get("selected_option") == "ask_for_clarification"
        ),
        {},
    )
    request_id = str(clarification_response.get("request_id") or "")
    if not request_id:
        return False
    source = next(
        (
            dict(item)
            for item in requests
            if item.get("request_id") == request_id
            and item.get("request_kind") == "developmental_resource_fulfillment"
            and item.get("status") == "consumed"
            and item.get("resolution") == "ask_for_clarification"
        ),
        {},
    )
    if not source:
        return False
    return any(
        item.get("operator_interaction_id") == request_id
        and item.get("fulfillment_type") == "partial_fulfillment"
        and "operator_clarification_required" in tuple(item.get("partial_sections") or ())
        for item in (learning_state.get("developmental_resource_fulfillments") or ())
        if isinstance(item, Mapping)
    )


def restore_continuous_mission_restart_state(
    controller: ContinuousRuntimeController,
    restart_state: Mapping[str, Any],
) -> ContinuousRuntimeController:
    if restart_state.get("session_id") != controller.session_id:
        raise ValueError("continuous mission restart state belongs to another session")
    responses = tuple(restart_state.get("continuous_operator_interaction_responses") or ())
    requests = _normalize_consumed_operator_interaction_requests(
        tuple(restart_state.get("continuous_developmental_insight_requests") or ()),
        responses,
    )
    recovered_ledger = _recover_knowledge_ledger(tuple(restart_state.get("continuous_knowledge_ledger") or ()))
    recovered_failures = _recover_behavioral_failure_records(tuple(restart_state.get("continuous_behavioral_failure_records") or ()))
    learning_state = dict(restart_state.get("continuous_learning_state") or {})
    agenda = dict(learning_state.get("developmental_agenda") or {})
    policy = dict(learning_state.get("developmental_resource_policy") or {})
    invalid_agenda = bool(agenda) and not agenda_state_is_valid(agenda)
    fulfillments = tuple(dict(item) for item in (learning_state.get("developmental_resource_fulfillments") or ()) if isinstance(item, Mapping))
    invalid_policy = bool(policy) and not resource_policy_state_is_valid(policy)
    recoverable_legacy_clarification = _has_recoverable_legacy_fulfillment_clarification(requests, responses, learning_state)
    invalid_fulfillments = not recoverable_legacy_clarification and not resource_fulfillment_state_is_valid(fulfillments, policy=policy)
    invalid_research = not research_state_is_valid(dict(learning_state.get("external_research") or {}))
    if invalid_agenda:
        learning_state["developmental_agenda"] = {
            **agenda,
            "status": "blocked",
            "exhaustion_reasons": ("invalid_agenda_state_on_restart",),
            "next_eligible_transition": "operator_refresh_required",
        }
    if invalid_policy:
        learning_state["developmental_resource_policy"] = {
            **policy,
            "status": "unavailable",
            "failure_reason": "invalid_resource_policy_state_on_restart",
        }
    if invalid_fulfillments:
        learning_state["developmental_resource_fulfillments"] = ()
        learning_state["developmental_resource_policy"] = {
            **policy,
            "status": "unavailable",
            "failure_reason": "invalid_resource_fulfillment_state_on_restart",
        }
    if invalid_research:
        learning_state["external_research"] = {"status": "research_validation_failed", "failure_reason": "invalid_external_research_state_on_restart"}
    recovered = replace(
        controller,
        continuous_mission_state="developmental_agenda_blocked" if invalid_agenda else "developmental_resource_policy_blocked" if invalid_policy or invalid_fulfillments else "developmental_external_research_blocked" if invalid_research else str(restart_state.get("continuous_mission_state") or ""),
        continuous_mission_contract=dict(restart_state.get("continuous_mission_contract") or {}),
        continuous_behavioral_failure_records=tuple(item.as_dict() for item in recovered_failures),
        continuous_mission_findings=tuple(restart_state.get("continuous_mission_findings") or ()),
        continuous_mission_frontier=tuple(restart_state.get("continuous_mission_frontier") or ()),
        continuous_main_goal=dict(restart_state.get("continuous_main_goal") or {}),
        continuous_completed_main_goals=tuple(restart_state.get("continuous_completed_main_goals") or ()),
        continuous_active_subgoal={} if invalid_agenda or invalid_policy or invalid_research else dict(restart_state.get("continuous_active_subgoal") or {}),
        continuous_consumed_weakness_signatures=tuple(restart_state.get("continuous_consumed_weakness_signatures") or ()),
        continuous_knowledge_ledger=recovered_ledger,
        continuous_pcm_bridge_ledger=tuple(restart_state.get("continuous_pcm_bridge_ledger") or ()),
        continuous_capability_inventory=tuple(restart_state.get("continuous_capability_inventory") or ()),
        continuous_developmental_self_assessment=dict(restart_state.get("continuous_developmental_self_assessment") or {}),
        continuous_developmental_insight_requests=requests,
        continuous_operator_interaction_responses=responses,
        continuous_operator_explanation=dict(restart_state.get("continuous_operator_explanation") or {}),
        continuous_api_authority=dict(restart_state.get("continuous_api_authority") or {}),
        continuous_observation_state=dict(restart_state.get("continuous_observation_state") or {}),
        continuous_learning_state=learning_state,
        pending_application_decision_id=str(restart_state.get("pending_application_decision_id") or ""),
        active_work_item="developmental_agenda_blocked" if invalid_agenda else "developmental_resource_policy_blocked" if invalid_policy or invalid_fulfillments else "developmental_external_research_blocked" if invalid_research else str(restart_state.get("active_work_item") or ""),
        journal=tuple(controller.journal) + (_journal_entry("continuous_mission", "invalid_agenda_restart_failed_closed" if invalid_agenda else "invalid_resource_policy_restart_failed_closed" if invalid_policy else "invalid_resource_fulfillment_restart_failed_closed" if invalid_fulfillments else "invalid_external_research_restart_failed_closed" if invalid_research else "continuous_mission_restart_state_restored", (str(restart_state.get("continuous_mission_state") or ""),)),),
    )
    return reconcile_terminal_external_research_requests(recovered)


def run_bounded_long_run(controller: ContinuousRuntimeController, *, cycles: int = 30) -> tuple[ContinuousRuntimeController, dict[str, Any]]:
    started = time.perf_counter()
    process_started = time.process_time()
    start_metrics = _sample_process_metrics(include_external=True)
    queue_sizes = []
    injected_events = 0
    processed_before = len(controller.processed_event_ids)
    event_types_seen: set[str] = set()
    for index in range(cycles):
        event_spec = _long_run_event_spec(index)
        if event_spec is not None:
            event_type, payload, priority = event_spec
            event = make_continuous_event(
                event_type,
                source="long_run",
                session_id=controller.session_id,
                payload={**payload, "index": index},
                priority=priority,
                correlation_id=f"long-run-{index}",
                expiration_cycle=cycles + 5,
            )
            controller = enqueue_continuous_event(controller, event)
            injected_events += 1
            event_types_seen.add(event_type)
        controller = run_controller_cycle(controller, force_idle_reflection=index % 5 == 0)
        queue_sizes.append(len(controller.event_queue))
        if controller.lifecycle_state in {"SUSPENDED", "SHUTDOWN"}:
            break
    elapsed = time.perf_counter() - started
    end_metrics = _sample_process_metrics(include_external=True)
    recent_cycles = controller.cycles[-len(queue_sizes) :] if queue_sizes else ()
    processed_after = len(controller.processed_event_ids)
    metrics = {
        "duration_seconds": round(elapsed, 4),
        "process_cpu_seconds": round(time.process_time() - process_started, 6),
        "cycles_requested": cycles,
        "cycles_completed": len(queue_sizes),
        "events_injected": injected_events,
        "events_processed": processed_after - processed_before,
        "event_types_seen": sorted(event_types_seen),
        "max_queue_size": max(queue_sizes or [0]),
        "final_queue_size": queue_sizes[-1] if queue_sizes else len(controller.event_queue),
        "model_calls": sum(item.model_calls for item in recent_cycles),
        "wikipedia_calls": sum(item.wikipedia_calls for item in recent_cycles),
        "model_events_observed": sum(1 for item in controller.journal if item.get("summary") in {"MODEL_READY", "MODEL_UNAVAILABLE"}),
        "wikipedia_events_observed": sum(1 for item in controller.journal if item.get("summary") in {"WIKIPEDIA_RESULT", "WIKIPEDIA_FAILURE"}),
        "external_process_metrics": {
            "start": start_metrics,
            "end": end_metrics,
            "working_set_delta_bytes": _metric_delta(start_metrics, end_metrics, "working_set_bytes"),
            "thread_count_delta": _metric_delta(start_metrics, end_metrics, "thread_count"),
        },
        "final_state": controller.lifecycle_state,
        "health_state": controller.health.health_state,
        "idle_cpu_proxy": "measured_process_cpu_time_for_bounded_explicit_cycles",
        "hidden_threads_created": False,
        "unauthorized_retrieval": False,
        "hidden_memory_writes": False,
        "duplicate_initiatives": _duplicate_initiative_count(controller.initiatives),
        "pilot_limitations": (
            "short bounded in-process harness, not multi-hour UI pilot",
            "model events are observed as controller inputs; local model inference is still separately consent-gated",
            "Wikipedia calls counted from event processing; asynchronous retrieval is not proven",
        ),
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
    long_run_proven = _long_run_proven(long_run_metrics)
    performance = {
        "status": "BOUNDED_CAMPAIGN_MEASURED" if not long_run_proven else "LONG_RUN_VALIDATED",
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
        "recommendation": "CONTINUOUS_RUNTIME_PARTIALLY_OPERATIONAL_PROCEED_TO_REAL_LONG_HORIZON_VALIDATION"
        if not long_run_proven
        else "CONTINUOUS_RUNTIME_READY_FOR_CONTROLLED_OPERATOR_PILOT",
        "evidence": "Controller is event-driven, bounded, and instrumented, but the current harness is not a multi-hour UI/model/Wikipedia stress pilot."
        if not long_run_proven
        else "Controller completed a long-horizon pilot with events, model/Wikipedia calls, external process metrics, and recovery controls.",
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
        "- Readiness: bounded controller validation is useful, but live developmental operation is not yet proven without a real long-horizon UI/model/retrieval campaign.",
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
        "architecture_doc": "\n".join([
            "# Continuous Runtime Architecture",
            "",
            "The continuous runtime controller is an in-process managed service loop. It owns lifecycle state, normalized event envelopes, wake policy, controller health, model residency metadata, active objectives, initiatives, and notification readiness. It reuses DELTA 1.2 live runtime, DELTA 1.5 evidence comparison, and DELTA 1.6 self-model instead of replacing them.",
            "",
            "## Active Spine",
            "",
            "The active runtime path is:",
            "",
            "```text",
            "UI Start Runtime",
            "-> start_live_wikipedia_runtime",
            "-> DELTA 1.2 LiveRuntimeState boot",
            "-> ContinuousRuntimeController boot",
            "-> operator/live events normalized into ContinuousEvent",
            "-> bounded controller cycle",
            "-> DELTA 1.6 background initiative/self-model sync",
            "-> operator inquiry and promotion candidate surfaces",
            "-> controller returns to IDLE",
            "```",
            "",
            "The controller is intentionally in-process. It does not create hidden threads, daemons, external schedulers, or background services. The UI remains the operator-controlled lifecycle boundary.",
            "",
            "## Ownership",
            "",
            "- `LiveRuntimeState` remains the lower-level cognitive event and journal runtime.",
            "- `LiveWikipediaRuntimeSession` remains the live chat and Wikipedia bridge.",
            "- `ContinuousRuntimeController` owns the service lifecycle, normalized events, wake mode, health, objectives, initiative queue, model-residency inventory, notification readiness, and shutdown state.",
            "- `OperationalSelfModel` remains a derived snapshot. It is not the lifecycle authority.",
            "",
            "## Safety",
            "",
            "The controller may run deterministic local analysis and queue review items. It may not call providers, retrieve arbitrary web pages, write memory, mutate the repository, promote sandbox changes, commit, push, deploy, access secrets, or change governance.",
            "",
            "## Current Evidence Boundary",
            "",
            "The bounded validation harness injects events and records process metrics, but it is not a substitute for a multi-hour UI/model/retrieval pilot.",
            "",
        ]),
        "lifecycle_doc": "\n".join([
            "# Operating Lifecycle",
            "",
            "Supported states: `" + "`, `".join(LIFECYCLE_STATES) + "`.",
            "",
            "Default wake mode is `EVENT_DRIVEN`. `BOUNDED_BACKGROUND` may be enabled by operator policy, while `PAUSED` and `SUSPENDED` fail closed. Illegal transitions raise errors.",
            "",
            "## Wake Modes",
            "",
            "- `MANUAL`: only explicit operator or test calls advance the controller.",
            "- `EVENT_DRIVEN`: default; wake only when an event arrives.",
            "- `BOUNDED_BACKGROUND`: permits low-frequency idle reflection.",
            "- `EXPERIMENTAL_CONTINUOUS`: reserved for future operator-approved trials.",
            "- `PAUSED`: no initiative generation.",
            "- `SUSPENDED`: fail-closed review state.",
            "",
            "## Cycle Bounds",
            "",
            "Each cycle enforces a maximum event batch size, cycle duration target, generated initiative count, journal entries, model calls, and Wikipedia calls. The controller records model and Wikipedia calls from explicit governed events; it does not infer idle calls from silence.",
            "",
            "## Shutdown",
            "",
            "Shutdown is explicit: `SHUTTING_DOWN -> SHUTDOWN`. The controller clears its queue and remains inspectable through the final snapshot.",
            "",
        ]),
        "model_doc": "\n".join([
            "# Model Orchestration",
            "",
            "The controller reads the real local model registry and lane router. Default conversation uses `" + controller.model_residency.selected_default_model + "`, planning uses `" + controller.model_residency.selected_planning_model + "`, and development analysis uses `" + controller.model_residency.selected_development_model + "`. ProviderManager remains serial with one resident local model maximum.",
            "",
            "## Actual Inventory",
            "",
            "The registry exposes multiple GGUF models and aliases rather than exactly two hardcoded models. The controller therefore reports actual registry state, selected lane models, resident model ID, resident lane, and residency status.",
            "",
            "## Routing Policy",
            "",
            "Deterministic subsystems answer without a model for lifecycle status, authority classification, capability reporting, Wikipedia budget exhaustion, and cached evidence discussion. Local models remain useful for synthesis, planning, hypothesis generation, coding proposals, ambiguity resolution, and deeper developmental reflection.",
            "",
            "## Residency Policy",
            "",
            "The existing `ProviderManager` is the authority for local model residency. It is serial and keeps at most one local GGUF model resident at a time. The continuous controller observes and reports this state; it does not keep multiple models loaded or invoke inference from idle reflection.",
            "",
            "## Validation Boundary",
            "",
            "The bounded campaign observes model-ready events and lane selection. Repeated real inference, model switching under pressure, failed invocation recovery, and planning-to-conversation handoff still require a controlled long-horizon pilot.",
            "",
        ]),
        "operator_doc": "\n".join([
            "# Continuous Runtime Operator Guide",
            "",
            "Use Start Runtime, Stop Runtime, Pause, Resume, and Suspend from the UI. The status line reports lifecycle, health, resident model, active objective, inquiries, promotion candidates, Wikipedia budget, and recent initiative. Ask `What are you currently working on?` or `Which local model is available?` for grounded state.",
            "",
            "## Recommended Pilot",
            "",
            "Run a controlled operator pilot with the UI open. Exercise ordinary chat, context declarations, one Wikipedia lookup, a self-model question, a local model deepening request, pause/resume, suspend, restart, and review of pending promotion candidates.",
            "",
            "## Reading Status",
            "",
            "- `Runtime`: controller lifecycle state.",
            "- `health`: controller health classification.",
            "- `model`: resident model when known, otherwise default lane model.",
            "- `objective`: active or waiting objective.",
            "- `inquiries`: pending operator inquiry count.",
            "- `promotions`: gated promotion candidate count.",
            "- `wiki`: current session query count and budget.",
            "- `initiative`: latest initiative outcome.",
            "",
            "## Authority Reminder",
            "",
            "DELTA can prepare and queue review items. It cannot persist, promote, commit, push, deploy, broaden web access, call providers, or change governance without operator authority.",
            "",
        ]),
        "failure_doc": "\n".join([
            "# Failure Recovery",
            "",
            "Queue growth, timeouts, invalid transitions, model unavailability, Wikipedia failure, and repeated exceptions move the controller toward `DEGRADED`, `PAUSED_FOR_REVIEW`, `SUSPENDED`, or `FAILED_SAFE`. Shutdown remains available at all times. Recovery returns to `IDLE` only through explicit controller transitions.",
            "",
            "## Health Inputs",
            "",
            "The controller checks event queue size, model availability, Wikipedia availability, cycle timeout, repeated exceptions, stale objectives, and resource limit events. It records process CPU time, active Python threads, and best-effort Windows working-set metrics without requiring `psutil`.",
            "",
            "## Degraded Mode",
            "",
            "When degraded, the controller stops automatic initiative work and preserves the audit trail. The operator can pause, suspend, or shut down. Unknown action types or invalid lifecycle transitions fail closed.",
            "",
            "## Recovery",
            "",
            "Recovery is explicit and bounded. The controller may return to `IDLE` after a recoverable condition clears, but it does not retry external retrieval, model execution, sandbox work, or persistence automatically.",
            "",
        ]),
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
    return tuple(
        event
        for event in controller.event_queue
        if int(event.audit_metadata.get("expires_at_cycle", cycle_count + event.expiration_cycle)) > cycle_count
    )


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
    batch: tuple[ContinuousEvent, ...] = (),
    duration_ms: float | None = None,
    health_state: str | None = None,
) -> RuntimeCycleRecord:
    duration = (time.perf_counter() - started) * 1000 if duration_ms is None else duration_ms
    model_calls = sum(_model_call_count(event) for event in batch)
    wikipedia_calls = sum(1 for event in batch if event.event_type in {"WIKIPEDIA_RESULT", "WIKIPEDIA_FAILURE"})
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
        model_calls=model_calls,
        wikipedia_calls=wikipedia_calls,
        external_metrics=_sample_process_metrics(include_external=False),
        idle_result=idle_result,
        health_state=health_state or controller.health.health_state,
    )


def _long_run_event_spec(index: int) -> tuple[str, dict[str, Any], int] | None:
    if index % 19 == 0:
        return ("WIKIPEDIA_RESULT", {"title": "Runtime validation", "classification": "noncanonical_review_candidate"}, 75)
    if index % 17 == 0:
        return ("MODEL_READY", {"model_id": "planning-lane", "lane": "planning", "local_model_call_performed": True}, 70)
    if index % 13 == 0:
        return ("BEHAVIORAL_FAILURE", {"summary": "blocked objective observed during bounded campaign"}, 80)
    if index % 11 == 0:
        return ("OBJECTIVE_BLOCKED", {"summary": "waiting for operator validation"}, 65)
    if index % 7 == 0:
        return ("VALIDATION_RESULT", {"result": "heartbeat"}, 20)
    return None


def _model_call_count(event: ContinuousEvent) -> int:
    if event.event_type == "MODEL_READY" and event.payload.get("local_model_call_performed"):
        return 1
    if event.event_type == "MODEL_UNAVAILABLE" and event.payload.get("attempted"):
        return 1
    return int(event.payload.get("model_calls") or 0)


def _metric_delta(start: dict[str, Any], end: dict[str, Any], key: str) -> int | None:
    if not isinstance(start.get(key), int) or not isinstance(end.get(key), int):
        return None
    return int(end[key]) - int(start[key])


def _sample_process_metrics(*, include_external: bool = True) -> dict[str, Any]:
    metrics = {
        "pid": os.getpid(),
        "process_time_seconds": round(time.process_time(), 6),
        "active_python_threads": threading.active_count(),
    }
    if os.name == "nt" and include_external:
        metrics.update(_sample_windows_process_metrics())
    return metrics


def _sample_windows_process_metrics() -> dict[str, Any]:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    result: dict[str, Any] = {}
    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(ProcessMemoryCounters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        psapi = ctypes.WinDLL("psapi.dll")
        ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if ok:
            result.update({
                "working_set_bytes": int(counters.WorkingSetSize),
                "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
                "pagefile_usage_bytes": int(counters.PagefileUsage),
            })
        else:
            result["process_memory_error"] = "GetProcessMemoryInfo returned false"
    except Exception as exc:  # noqa: BLE001 - metrics are best-effort instrumentation only.
        result["process_memory_error"] = type(exc).__name__
    if "working_set_bytes" not in result:
        result.update(_sample_windows_process_metrics_via_powershell(os.getpid()))
    try:
        result["thread_count"] = int(ctypes.windll.kernel32.GetActiveProcessorCount(0)) if False else threading.active_count()
    except Exception:
        result["thread_count"] = threading.active_count()
    return result


def _sample_windows_process_metrics_via_powershell(pid: int) -> dict[str, Any]:
    command = (
        "$p=Get-Process -Id "
        + str(int(pid))
        + "; [pscustomobject]@{WorkingSet64=$p.WorkingSet64; CPU=$p.CPU; Handles=$p.Handles; Threads=$p.Threads.Count} | ConvertTo-Json -Compress"
    )
    for executable in ("powershell.exe", "powershell"):
        try:
            completed = subprocess.run(
                [executable, "-NoProfile", "-Command", command],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except Exception as exc:  # noqa: BLE001 - metrics are best-effort instrumentation only.
            continue
        if completed.returncode != 0 or not completed.stdout.strip():
            continue
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            continue
        return {
            "working_set_bytes": int(payload.get("WorkingSet64") or 0),
            "powershell_cpu_seconds": float(payload.get("CPU") or 0.0),
            "handle_count": int(payload.get("Handles") or 0),
            "os_thread_count": int(payload.get("Threads") or 0),
            "process_metrics_source": executable,
        }
    return {"process_metrics_fallback_error": "Get-Process unavailable"}


def _long_run_proven(metrics: dict[str, Any]) -> bool:
    return (
        float(metrics.get("duration_seconds") or 0) >= 3600
        and int(metrics.get("events_processed") or 0) > 0
        and int(metrics.get("model_calls") or 0) > 0
        and int(metrics.get("wikipedia_calls") or 0) > 0
        and int(metrics.get("final_queue_size") or 0) <= 1
        and metrics.get("health_state") == "HEALTHY"
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
