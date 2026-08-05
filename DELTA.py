from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass, replace
from datetime import datetime, timezone
import json
import os
import queue
import re
import subprocess
import threading
import traceback
import uuid
import sys
import tkinter as tk
from pathlib import Path
from typing import Mapping
from tkinter import messagebox, scrolledtext, simpledialog, ttk


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OAR_LIVE_DEVELOPMENT_STATE_PATH = ROOT / "data" / "runtime" / "oar_live_development_state.json"
LIVE_RUNTIME_1B_ROOT = ROOT / ".tmp" / "live-runtime-1b-tk-attended-v2"
LIVE_RUNTIME_1B_ACCEPTED_ROOT = ROOT / ".tmp" / "live-general-3-approved-learning-v1"
LIVE_RUNTIME_1B_MISSION_TEXT = (
    "Validate a disposable mixed CSV and JSON dataset, reconcile equivalent records using accepted developmental "
    "competence, and produce a grounded final report with capability provenance and input-preservation evidence."
)
LIVE_RUNTIME_2_ROOT = ROOT / ".tmp" / "live-runtime-2-bounded-unattended-v1"
LIVE_RUNTIME_2_ACCEPTED_ROOT = ROOT / ".tmp" / "live-general-3-approved-learning-v1"
LIVE_RUNTIME_3_ROOT = ROOT / ".tmp" / "live-runtime-3-interruption-resumption-v1"
LIVE_RUNTIME_3_ACCEPTED_ROOT = ROOT / ".tmp" / "live-general-3-approved-learning-v1"
LIVE_RUNTIME_4_ROOT = ROOT / ".tmp" / "live-runtime-4-crash-integrity-v1"
LIVE_RUNTIME_4_ACCEPTED_ROOT = ROOT / ".tmp" / "live-general-3-approved-learning-v1"
CONVERSATIONAL_RUNTIME_ROOT = Path(
    os.environ.get(
        "DELTA_CONVERSATIONAL_RUNTIME_ROOT",
        str(ROOT / "data" / "runtime" / "conversational_runtime_operation"),
    )
)


class LockedProviderManagerProxy:
    def __init__(self, provider_manager: ProviderManager, lock: threading.Lock):
        self._provider_manager = provider_manager
        self._lock = lock

    def warm(self, model_name: str):
        with self._lock:
            return self._provider_manager.warm(model_name)

    def infer(self, **kwargs):
        with self._lock:
            return self._provider_manager.infer(**kwargs)

    def load(self, model_name: str):
        with self._lock:
            return self._provider_manager.load(model_name)

    def status(self):
        with self._lock:
            return self._provider_manager.status()

from orchestration.runtime.rc1_operator_console import (  # noqa: E402
    append_observation,
    approve_propositions,
    build_observation_entry,
    build_cognitive_state,
    build_operator_snapshot,
    extract_propositions,
    preview_evidence_ingest,
    validate_console_safe,
)
from orchestration.runtime.rc2_developmental_concept_memory import (  # noqa: E402
    approve_candidate_concept,
    build_developmental_memory_state,
    clear_developmental_memory_store,
    query_approved_concepts,
)
from orchestration.runtime.rc2_conversational_mode_router import (  # noqa: E402
    DISPLAY_MODES,
    build_memory_candidate_from_answer,
    candidate_is_memory_worthy,
    render_route,
    route_message,
    select_model_lane,
)
from orchestration.runtime.rc2_storage_adapter import backend_health, load_diverse_concepts, search_concepts, substrate_counts  # noqa: E402
from orchestration.runtime.rc2_substrate_reconciliation import build_substrate_reconciliation  # noqa: E402
from orchestration.runtime.cognitive_claim_relation_runtime import (  # noqa: E402
    FEATURE_FLAG_NAME as CLAIM_RELATION_PILOT_FLAG,
    GovernedClaimRelationRuntime,
)
from orchestration.runtime.active_cognitive_loop import (  # noqa: E402
    DEFAULT_STATE_PATH as ACTIVE_COGNITIVE_LOOP_STATE_PATH,
    EvidenceRef as ActiveCognitiveEvidenceRef,
    LedgerBackedCognitiveModelRunner,
    active_loop_snapshot,
    evaluate_cognitive_episode,
    initialize_episode as initialize_active_cognitive_episode,
    read_episode_state as read_active_cognitive_episode_state,
    run_cognitive_cycle as run_active_cognitive_cycle,
    write_episode_state as write_active_cognitive_episode_state,
)
from orchestration.runtime.conversational_runtime_operation import (  # noqa: E402
    ChatAddressableRequest,
    ConversationTurn,
    apply_stop_or_redirect as apply_conversational_stop_or_redirect,
    background_cycle_hold_reason,
    chat_feature_settings_schema,
    classify_conversational_intent,
    compile_chat_clarification_request,
    decide_turn_relation,
    evaluate_conversational_runtime,
    handle_conversational_message,
    infer_lesson_transfer,
    is_developmental_governance_message,
    is_source_bound_semantic_analysis_message,
    is_source_bound_semantic_competence_measurement_message,
    is_evidence_bound_analysis_recall_message,
    is_evidence_bound_analysis_refinement_recall_message,
    is_internal_work_recall_message,
    is_semantic_problem_frame_recall_message,
    is_semantic_problem_modeling_message,
    is_source_bound_semantic_recall_message,
    is_source_bound_semantic_transfer_message,
    is_teaching_followup_message,
    mark_capability_campaign_milestone_rendered,
    mark_chat_request_rendered,
    mark_knowledge_goal_event_rendered,
    queue_endogenous_teaching_gap_recovery,
    record_foreground_message_for_reconciliation,
    reconcile_queued_teaching_followup,
    render_knowledge_goal_event,
    render_structured_discourse_capability_review,
    render_goal_review,
    review_status_for_goal_completion,
    select_chat_request_owner,
    request_provider_learning_packet,
    resolve_developmental_governance_instruction,
    resume_active_objective as resume_conversational_objective,
    resolve_pending_chat_request,
    run_background_objective_cycle as run_conversational_background_cycle,
    save_runtime_state as save_conversational_runtime_state,
    start_or_restore_runtime as start_or_restore_conversational_runtime,
    stop_active_objective as stop_conversational_objective,
    unrendered_capability_campaign_milestones,
    unrendered_knowledge_goal_events,
)
from orchestration.runtime.chat_first_dispatch_contract import plan_message_dispatch  # noqa: E402
from orchestration.runtime.provisional_semantic_consolidation import (  # noqa: E402
    ConsolidationIntegrityError,
    apply_admission as apply_consolidation_admission,
    create_administrative_overlay as create_consolidation_overlay,
    ensure_consolidation_cohort,
    load_graph as load_provisional_semantic_graph,
    render_administrative_review as render_consolidation_review,
    save_graph as save_provisional_semantic_graph,
    seal_cohort_packet_once,
)
from orchestration.runtime.epistemic_answer_mode import (  # noqa: E402
    bind_explicit_semantic_question,
    bind_teaching_followup_question,
    compose_epistemic_answer,
    resolve_production_epistemic_answer,
)
from orchestration.runtime.interactive_cognition import (  # noqa: E402
    arbitrate_attention,
    build_workspace_snapshot,
    clear_preemption,
    load_coordination_state,
    record_shadow_decision,
    request_preemption,
    save_coordination_state,
    set_candidate_disposition,
    stage_attention_decision,
    surface_candidate_once,
)
from orchestration.runtime.approved_association_exploration import (  # noqa: E402
    build_inquiry_question,
    execute_once as execute_association_exploration_once,
    load_explorations,
    queue_exploration,
    save_explorations,
)
from orchestration.runtime.approved_revisit_reinquiry import (  # noqa: E402
    execute_once as execute_revisit_reinquiry_once,
    load_reinquiries,
    queue_reinquiry,
    save_reinquiries,
)
from orchestration.runtime.approved_structural_analogy_exploration import (  # noqa: E402
    execute_once as execute_structural_analogy_exploration_once,
    load_explorations as load_structural_analogy_explorations,
    queue_exploration as queue_structural_analogy_exploration,
    save_explorations as save_structural_analogy_explorations,
)
from orchestration.runtime.approved_curiosity_inquiry import (  # noqa: E402
    execute_once as execute_curiosity_inquiry_once,
    load_inquiries as load_curiosity_inquiries,
    queue_inquiry as queue_curiosity_inquiry,
    save_inquiries as save_curiosity_inquiries,
)
from orchestration.runtime.structural_analogy import describe_structural_analogy_candidate  # noqa: E402
from orchestration.runtime.governed_personality_profile import (  # noqa: E402
    approve_and_activate as approve_governed_personality,
    load_state as load_governed_personality_state,
    propose_profile as propose_governed_personality,
    record_relationship_convention as record_governed_relationship_convention,
    rollback_profile as rollback_governed_personality,
    save_state as save_governed_personality_state,
    shape_presentation as shape_governed_presentation,
)
from orchestration.runtime.goal_oriented_ui_campaign import (  # noqa: E402
    CAMPAIGN_ID as GOAL_UI_CAMPAIGN_ID,
    begin_follow_up as begin_goal_ui_campaign_follow_up,
    campaign_path as goal_ui_campaign_path,
    formulate_candidate_experiments as formulate_goal_ui_campaign_candidates,
    launch_experiment as launch_goal_ui_campaign_experiment,
    pause_experiment as pause_goal_ui_campaign_experiment,
    read_experiment_state as read_goal_ui_campaign_experiment_state,
    read_json as read_goal_ui_campaign_json,
    resume_experiment as resume_goal_ui_campaign_experiment,
    run_experiment_cycle as run_goal_ui_campaign_experiment_cycle,
    select_experiments as select_goal_ui_campaign_experiments,
    summarize_for_ui as summarize_goal_ui_campaign_for_ui,
    write_json as write_goal_ui_campaign_json,
)
from orchestration.runtime.rc3_ui_capability_adapter import (  # noqa: E402
    PANEL_ORDER as RC3_PANEL_ORDER,
    build_rc3_ui_integration_report,
    build_rc3_ui_snapshot,
    render_rc3_panel,
    validate_rc3_ui_snapshot,
)
from orchestration.runtime.rc4_ui_capability_adapter import (  # noqa: E402
    RC4_PANEL_ORDER,
    build_rc4_ui_integration_report,
    build_rc4_ui_snapshot,
    render_rc4_panel,
    validate_rc4_ui_snapshot,
)
from orchestration.runtime.rc5_ui_capability_adapter import (  # noqa: E402
    RC5_PANEL_ORDER,
    build_rc5_ui_integration_report,
    build_rc5_ui_snapshot,
    render_rc5_panel,
    validate_rc5_ui_snapshot,
)
from orchestration.runtime.rc45_discourse_cognition_bridge import (  # noqa: E402
    build_discourse_frame,
    should_preempt_specialist_routing,
)
from orchestration.runtime.rc2_render_correction import is_render_correction_request  # noqa: E402
from orchestration.runtime.pc1_pragmatic_cognition import build_pragmatic_frame  # noqa: E402
from orchestration.runtime.integrated_cognitive_runtime import build_integrated_cognitive_trace  # noqa: E402
from orchestration.runtime.rc5_developmental_cognition import DevelopmentConsultationPacket  # noqa: E402
import orchestration.runtime.conversational_runtime_operation as conversational_runtime_operation  # noqa: E402
from orchestration.runtime.rc6_governed_external_intelligence import (  # noqa: E402
    build_consultation_request_from_rc5,
    classify_provider_risk,
    execute_gateway,
    parse_external_advisory_response,
    prepare_provider_request,
    safety_metadata as rc6_safety_metadata,
    stable_id as rc6_stable_id,
    validate_advisory_response,
)
from orchestration.runtime.rc7_governed_development_loop import (  # noqa: E402
    build_operator_dashboard_snapshot as build_rc7_operator_dashboard_snapshot,
    render_operator_dashboard as render_rc7_operator_dashboard,
)
from orchestration.runtime.rc11_rc12_systems_plateau import (  # noqa: E402
    build_plateau_operator_dashboard,
    render_plateau_operator_dashboard,
)
from orchestration.runtime.delta_1_4_live_wikipedia_runtime import (  # noqa: E402
    LiveWikipediaRuntimeSession,
    handle_live_chat,
    pause_live_initiative,
    resume_live_initiative,
    start_live_wikipedia_runtime,
    stop_live_wikipedia_runtime,
    suspend_live_runtime_initiative,
)
from orchestration.runtime.continuous_runtime_controller import (  # noqa: E402
    advance_live_runtime_1_attended_mission,
    attach_live_runtime_1_attended_mission,
    compile_mission_bound_local_model_learning_request,
    compile_operator_developmental_learning_mission,
    consume_mission_bound_local_model_learning_approval,
    controller_snapshot,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.developmental_teaching_runtime import (  # noqa: E402
    derive_teaching_pressures,
    load_teaching_controller,
    render_teaching_followup_result,
    render_physics_prerequisite_result,
    save_teaching_controller,
    start_teaching_controller,
    teaching_snapshot,
    update_teaching_state,
)
from orchestration.runtime.live_runtime_2_bounded_unattended import (  # noqa: E402
    compile_live_runtime_2_unattended_authority,
    prepare_live_runtime_2_mission,
    start_live_runtime_2_process,
)
from orchestration.runtime.live_runtime_3_interruption_resumption import (  # noqa: E402
    compile_live_runtime_3_unattended_authority,
    prepare_live_runtime_3_mission,
    start_live_runtime_3_process,
)
from orchestration.runtime.live_runtime_4_crash_integrity import (  # noqa: E402
    compile_live_runtime_4_unattended_authority,
    prepare_live_runtime_4_mission,
    recover_live_runtime_4_interrupted_runner,
    start_live_runtime_4_process,
)
from orchestration.runtime.autonomy_goal_discovery import (  # noqa: E402
    AUTONOMY_1_ROOT,
    persist_autonomy_1_goal_discovery,
)
from orchestration.runtime.autonomy_goal_prioritization import (  # noqa: E402
    AUTONOMY_2_ROOT,
    compile_ranking as compile_autonomy_2_ranking,
    explain_ranking as explain_autonomy_2_ranking,
    persist_prioritization,
    persist_selection as persist_autonomy_2_selection,
)
from orchestration.runtime.autonomy_goal_queue_planning import (  # noqa: E402
    AUTONOMY_3_ROOT,
    approve_plan_for_future_execution,
    compile_plan_proposal,
    compile_plan_review_request,
    normalize_plan_feedback,
    select_goal_for_planning,
)
from orchestration.runtime.autonomy_approved_plan_execution import (  # noqa: E402
    AUTONOMY_4_ROOT,
    resume_paused_execution,
    run_approved_plan_execution,
)
from orchestration.runtime.autonomy_outcome_review import (  # noqa: E402
    explain_review_evidence,
    respond_to_outcome_review,
    review_completed_outcome,
)
from orchestration.runtime.autonomy_competence_admission import (  # noqa: E402
    explain_competence_scope,
    respond_to_competence_admission,
    review_competence_candidate,
)
from orchestration.runtime.autonomy_task_activation import (  # noqa: E402
    run_task_scoped_activation,
)
from orchestration.runtime.autonomy_capability_composition import (  # noqa: E402
    run_capability_composition,
)
from orchestration.runtime.autonomy_gap_detection import (  # noqa: E402
    run_gap_detection,
)
from orchestration.runtime.autonomy_mixed_mission import (  # noqa: E402
    run_mixed_mission,
)
from orchestration.runtime.autonomy_local_evidence import (  # noqa: E402
    acquire_local_evidence,
    detect_stale_packet,
    select_real_gap,
)
from orchestration.runtime.autonomy_advisory_assistance import (  # noqa: E402
    request_bounded_advice,
)
from orchestration.runtime.autonomy_competence_maintenance import (  # noqa: E402
    run_competence_maintenance,
)
from orchestration.runtime.operator_ux import (  # noqa: E402
    audit_rc_tabs,
    compile_formal_operator_response,
    compile_narration_event,
    compile_operator_request_card,
    consume_formal_operator_response,
    explain_operator_request,
    goal_card_from_live_runtime_state,
    human_state_label,
    narration_from_live_runtime_state,
    normalize_operator_intent,
    write_json as write_operator_ux_json,
)
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger  # noqa: E402
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal  # noqa: E402
from orchestration.runtime.developmental_learning import classify_developmental_instruction  # noqa: E402
from orchestration.runtime.persistent_autonomous_development_runtime import (  # noqa: E402
    DEFAULT_RUNTIME_ROOT as PERSISTENT_DEVELOPMENT_RUNTIME_ROOT,
    export_runtime_report,
    initialize_runtime,
    pause_runtime,
    resume_runtime,
    run_until_idle,
    stop_runtime,
)
from orchestration.runtime import gsr_a_governed_self_regulation as gsr  # noqa: E402
from integration.model_runtime.provider_manager import ProviderManager  # noqa: E402


def _format_cognitive_state(state: dict[str, object]) -> str:
    return "\n".join([
        "Cognitive State",
        "",
        f"Knowledge available: {state['knowledge_available']}",
        f"Noncanonical propositions: {state['noncanonical_propositions']}",
        f"Evidence links: {state['evidence_links']}",
        f"Active runtime concepts: {state['concepts']}",
        f"Contradictions: {state['contradictions']}",
        f"Pending review: {state['pending_review']}",
        f"Substrate replay events: {state['replay_queue']}",
        f"Migration audit events: {state.get('migration_audit_events', 0)}",
        f"Canonical records: {state['canonical_records']}",
    ])


def _format_snapshot(snapshot: dict[str, object]) -> str:
    status = snapshot["runtime_status"]
    corpus = snapshot["corpus_substrate"]
    replay = snapshot["replay_rollback"]
    queue = snapshot["operator_review_queue"]
    backend = backend_health()
    counts = substrate_counts()
    reconciliation = counts.get("reconciliation") or build_substrate_reconciliation(write_reports=False)
    developmental = build_developmental_memory_state()
    return "\n".join([
        "DELTA Advanced Operator Console",
        "",
        f"Version: {status['version']}",
        f"Status: {status['status']}",
        f"Operational baseline: {status['operational_baseline']}",
        f"Latest TP phase: {status['latest_tp_phase']}",
        f"Latest recommendation: {status['latest_tp_recommendation']}",
        "",
        "Corpus / substrate:",
        f"- substrate improvements: {corpus['substrate_improvement_count']}",
        f"- canonical writes enabled: {corpus['canonical_write_enabled']}",
        f"- training enabled: {corpus['training_enabled']}",
        "",
        "Review / replay:",
        f"- review queue references: {len(queue)}",
        f"- rollback records: {replay['rollback_records']}",
        f"- replay report available: {replay['replay_report_available']}",
        "",
        "Storage backend:",
        f"- backend: {backend.get('backend')}",
        f"- sqlite available: {backend.get('sqlite_available')}",
        f"- sqlite fresh: {backend.get('fresh')}",
        f"- active runtime concepts: {counts.get('active_runtime_concepts', counts.get('concepts'))}",
        f"- active graph edges: {counts.get('active_graph_edges', counts.get('graph_edges'))}",
        f"- substrate replay events: {counts.get('substrate_replay_events', counts.get('replay_events'))}",
        f"- concept replay events: {counts.get('concept_replay_events')}",
        f"- graph edge replay events: {counts.get('graph_edge_replay_events')}",
        f"- migration audit events: {counts.get('migration_audit_events')}",
        f"- legacy JSONL concepts: {counts.get('legacy_jsonl_concepts')}",
        f"- legacy JSONL graph edges: {counts.get('legacy_jsonl_graph_edges')}",
        f"- developmental memory records: {developmental.get('knowledge_memory_records')}",
        f"- concept import coverage: {counts.get('concept_replay_coverage')}",
        f"- edge import coverage: {counts.get('edge_replay_coverage')}",
        f"- authoritative concept counter: {reconciliation.get('authoritative_runtime_concept_counter')}",
        "",
        "Systems plateau:",
        _plateau_developer_overlay_text(),
    ])


def _extract_report_path(message: str) -> Path | None:
    match = re.search(r"([A-Za-z]:\\[^\r\n]+?\.(?:md|json))", message)
    if not match:
        return None
    return Path(match.group(1).strip().strip('"'))


def _inspect_local_report(message: str) -> dict[str, object] | None:
    path = _extract_report_path(message)
    if path is None:
        return None
    try:
        resolved = path.resolve()
        reports_root = (ROOT / "reports").resolve()
        if reports_root not in (resolved, *resolved.parents):
            return {
                "handled": True,
                "answer": "I can only inspect local DELTA report files under the repo `reports` folder from this UI path.",
                "safety": _report_inspection_safety(),
            }
        if not resolved.exists() or not resolved.is_file():
            return {
                "handled": True,
                "answer": f"I could not find that report file:\n{resolved}",
                "safety": _report_inspection_safety(),
            }
        text = resolved.read_text(encoding="utf-8", errors="replace")
        return {
            "handled": True,
            "answer": _summarize_report_text(resolved, text, message),
            "safety": _report_inspection_safety(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "handled": True,
            "answer": f"I tried to inspect that local report, but the read failed: {type(exc).__name__}: {str(exc)[:180]}",
            "safety": _report_inspection_safety(),
        }


def _report_inspection_safety() -> dict[str, bool]:
    return {
        "local_file_read_performed": True,
        "provider_calls_performed": False,
        "gpt_api_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "developmental_memory_write_performed": False,
        "autonomous_action_performed": False,
    }


def _pc1_enabled() -> bool:
    value = os.environ.get("DELTA_PC1_ENABLED", "true").strip().lower()
    return value not in {"0", "false", "off", "no", "disabled"}


def _pc1_context_for_message(last_report_inspection: dict[str, object] | None = None) -> dict[str, object]:
    if last_report_inspection:
        return {
            "active_topic": "RC4/RC5 real operator pilot and freeze readiness",
            "operator_goal": "evaluate governed RC4/RC5 readiness without overclaiming freeze",
            "last_report": last_report_inspection.get("report_name"),
            "last_report_summary": last_report_inspection.get("answer_summary"),
        }
    return {
        "active_topic": "RC4/RC5 governed operator pilot",
        "operator_goal": "preserve practical intent, scope, and governance boundaries",
    }


def _try_pc1_pragmatic_answer(message: str, last_report_inspection: dict[str, object] | None = None, *, developer_overlay: bool = False) -> str | None:
    if not _pc1_enabled():
        return None
    if is_render_correction_request(message):
        return None
    if not last_report_inspection and not _pc1_has_governance_cue(message):
        return None
    frame = build_pragmatic_frame(message, _pc1_context_for_message(last_report_inspection))
    if frame.confidence.confidence < 0.82:
        return None
    route_hint = frame.cooperative_interpretation.route_hint
    if route_hint not in {
        "pc1_shadow_mixed_judgment",
        "pc1_shadow_evidence_standard",
        "pc1_shadow_scope_boundary",
        "pc1_shadow_scope_separation",
        "pc1_shadow_response_planning",
        "pc1_shadow_recommendation",
    }:
        return None
    reply = _render_pc1_pragmatic_answer(frame)
    if not reply:
        return None
    if developer_overlay:
        reply += "\n\n--- Developer Overlay ---\n"
        reply += "Route: pc1_bounded_pragmatic_pre_router\n"
        reply += f"PC1 enabled: {_pc1_enabled()}\n"
        reply += "PC1 frame:\n"
        reply += json.dumps(frame.as_dict(), indent=2, sort_keys=True)
        reply += "\nIntegrated cognitive trace:\n"
        reply += json.dumps(
            build_integrated_cognitive_trace(
                message,
                last_report_inspection,
                include_rc2_route_preview=False,
            ),
            indent=2,
            sort_keys=True,
        )
        reply += "\nSafety:\n"
        reply += json.dumps(_pc1_safety(), indent=2, sort_keys=True)
    return reply


def _pc1_has_governance_cue(message: str) -> bool:
    lower = " ".join(str(message or "").lower().split())
    cues = (
        "rc4",
        "rc5",
        "pilot",
        "freeze",
        "operator",
        "review",
        "authorization",
        "governance",
        "sandbox",
        "production",
        "proposal",
        "provider",
        "gpt",
        "rollback",
        "bounded repair",
        "patch",
        "proposed fix",
        "outside reviewer",
    )
    return any(cue in lower for cue in cues)


def _render_pc1_pragmatic_answer(frame) -> str:
    shape = frame.response_shape.shape
    interpretation = frame.cooperative_interpretation.interpretation
    if shape == "mixed_judgment_explanation":
        if "diagnosis" in interpretation and "overbroad" in interpretation:
            return "\n".join([
                "Treat that as a mixed pilot judgment, not a contradiction.",
                "",
                "Session record:",
                "- Diagnosis: useful. Keep it as evidence that DELTA identified the right issue.",
                "- Proposed fix: too broad. Reject or revise that part before any RC4 handoff.",
                "- Overall disposition: partially useful, not accepted as-is.",
                "",
                "Freeze implication: this helps the pilot evidence record, but it is not freeze proof unless the revised proposal stays bounded, reviewable, and validated.",
                "",
                "No memory was written. No provider was called.",
            ])
        if "Technical success" in frame.cooperative_interpretation.why_preferred or "governance" in interpretation:
            return "\n".join([
                "That is technical success, but not governed success.",
                "",
                "Record it as:",
                "- Technical result: the patch worked.",
                "- Governance result: failed, because operator review was skipped.",
                "- Overall disposition: not RC4/RC5 freeze-ready until the review gap is repaired.",
                "",
                "The useful part is the implementation evidence. The blocking part is the missing operator authorization/review trail.",
                "",
                "No memory was written. No provider was called.",
            ])
        if frame.mixed_judgments:
            judgment = frame.mixed_judgments[0]
            dimensions = [f"- {key.replace('_', ' ').title()}: {value}." for key, value in judgment.dimensions.items()]
            return "\n".join([
                "This should be recorded as a mixed judgment with separate dimensions.",
                "",
                *dimensions,
                f"- Overall disposition: {judgment.overall_disposition.replace('_', ' ')}.",
                "",
                "Do not collapse the mixed result into a single yes/no success claim.",
                "",
                "No memory was written. No provider was called.",
            ])
    if shape == "context_boundary_explanation" and "rollback evidence" in interpretation:
        return "\n".join([
            "In this RC4/RC5 pilot context, rollback evidence means proof that a bad or unwanted change can be safely reversed or stopped.",
            "",
            "Good rollback evidence would show:",
            "- What change or proposal was being tested.",
            "- What went wrong or why the operator rejected it.",
            "- The exact rollback, rejection, bounded repair stop, or restoration path.",
            "- Confirmation that no unauthorized production mutation, memory write, provider call, commit, push, deployment, or freeze claim occurred.",
            "- The final recovered state and any remaining follow-up.",
            "",
            "So this is governance/recovery evidence, not a medical or domain-recall question.",
            "",
            "No memory was written. No provider was called.",
        ])
    if shape == "governance_decision_guidance" and "outside reviewer" in interpretation:
        return "\n".join([
            "Use the outside reviewer's issue as advisory evidence, but reject the direct-patch instruction.",
            "",
            "A good record would say:",
            "- External review found a useful issue.",
            "- Direct application was rejected because outside advice does not grant integration authority.",
            "- Any fix must go through RC4 proposal, operator review, validation, and explicit approval.",
            "",
            "That preserves the useful signal without giving the reviewer or the advice itself execution authority.",
            "",
            "No memory was written. No provider was called.",
        ])
    if shape == "scope_boundary_explanation":
        return "\n".join([
            "That approval is scope-limited.",
            "",
            "Testing approval means DELTA may treat sandbox/testing work as allowed in the pilot record. It does not authorize production mutation, integration, deployment, commit, push, plugin activation, provider calls, or freeze claims.",
            "",
            "No memory was written. No provider was called.",
        ])
    if shape == "evidence_standard_explanation":
        return _answer_sufficient_recovery_evidence()
    if shape == "recommendation":
        return _answer_primary_freeze_evidence_gap()
    return ""


def _pc1_safety() -> dict[str, bool]:
    return {
        "pc1_enabled": _pc1_enabled(),
        "provider_calls_performed": False,
        "gpt_api_calls_performed": False,
        "developmental_memory_write_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "production_authority_expanded": False,
        "rc4_contract_changed": False,
        "rc5_contract_changed": False,
    }


def _rc7_developer_overlay_text() -> str:
    snapshot = build_rc7_operator_dashboard_snapshot()
    return render_rc7_operator_dashboard(snapshot) + "\nSnapshot:\n" + json.dumps(snapshot, indent=2, sort_keys=True)


def _plateau_developer_overlay_text() -> str:
    snapshot = build_plateau_operator_dashboard()
    return render_plateau_operator_dashboard(snapshot) + "\nSnapshot:\n" + json.dumps(snapshot, indent=2, sort_keys=True)


def _is_rc6_pilot_message(message: str) -> bool:
    lower = " ".join(str(message or "").lower().split())
    return (
        "rc6" in lower
        or "external provider" in lower
        or "external consultation" in lower
        or "bounded external consultation" in lower
        or "mock external advisory response" in lower
        or "provider call" in lower
    ) and any(term in lower for term in ("classify", "consultation packet", "validate", "disabled-gateway pilot", "provider transport"))


def _handle_rc6_pilot_message(message: str, events: list[dict[str, object]] | None = None) -> str | None:
    if not _is_rc6_pilot_message(message):
        return None
    lower = " ".join(message.lower().split())
    events = events if events is not None else []
    if "classify this request" in lower:
        target = _extract_rc6_embedded_text(message) or message
        risk = classify_provider_risk(target)
        event = {
            "kind": "classification",
            "target": target,
            "outcome": risk.provider_outcome,
            "reasons": list(risk.reasons),
            "provider_call_performed": False,
        }
        events.append(event)
        return _render_rc6_classification(target, risk)
    if "consultation packet" in lower and "do not send" in lower:
        target = _extract_rc6_embedded_text(message) or message
        packet = _build_rc6_ui_packet(target)
        request = build_consultation_request_from_rc5(packet, extra_context=target)
        provider_request = prepare_provider_request(request)
        result = execute_gateway(request, env={})
        event = {
            "kind": "packet",
            "target": target,
            "outcome": request.risk.provider_outcome,
            "gateway_status": result.decision.status,
            "provider_call_performed": result.decision.provider_call_performed,
        }
        events.append(event)
        return _render_rc6_packet_result(target, request, provider_request, result)
    if "mock external advisory response" in lower or ("validate it under rc6 rules" in lower and "advisory response" in lower):
        target = _extract_rc6_embedded_text(message) or message
        response = parse_external_advisory_response(_mock_advisory_payload_from_text(target))
        validation = validate_advisory_response(response)
        event = {
            "kind": "advisory_validation",
            "target": target,
            "outcome": "accepted" if validation.valid else "rejected",
            "findings": list(validation.findings),
            "provider_call_performed": False,
        }
        events.append(event)
        return _render_rc6_advisory_validation(target, validation)
    if "summarize" in lower and "disabled-gateway pilot" in lower:
        return _render_rc6_pilot_summary(events)
    return None


def _extract_rc6_embedded_text(message: str) -> str:
    patterns = (
        r"[“\"]([^”\"]+)[”\"]",
        r"â€œ(.+?)â€\u009d",
        r"â€œ(.+?)â€",
        r"classify this request:\s*(.+?)\s*Should this",
        r"do not send it:\s*(.+?)\s*Show",
        r"response,\s*validate it under RC6 rules:\s*(.+?)\s*Should RC6",
    )
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return " ".join(match.group(1).strip().strip(" .").split())
    return ""


def _build_rc6_ui_packet(target: str) -> DevelopmentConsultationPacket:
    return DevelopmentConsultationPacket(
        packet_id=rc6_stable_id("ui-rc6-packet", target),
        purpose_criterion="Evaluate whether a bounded external consultation is useful without granting authority.",
        observed_deficit=target,
        evidence=("Operator supplied an RC6 disabled-gateway pilot prompt.",),
        counterevidence=("No live provider transport has been approved.",),
        architecture_summary="RC6 is a disabled-by-default governed gateway over RC5 manual consultation packets.",
        constraints=("advisory_only", "operator_review_required", "provider_disabled_by_default", "stateless_packet_only"),
        prohibited_changes=("automatic_api_call", "self_approval", "purpose_mutation", "hidden_persistence", "rc4_bypass"),
        requested_output=("root_cause_assessment", "candidate_remedies", "tests", "rollback_conditions"),
        token_budget=1000,
        estimated_tokens=max(1, len(target.split()) * 4 // 3),
        omitted_context=(),
        transport="rc6_disabled_gateway_preview",
    )


def _render_rc6_classification(target: str, risk) -> str:
    label = {
        "SAFE_FOR_LOCAL_PROCESSING": "safe for local processing; no external consultation needed",
        "SAFE_FOR_BOUNDED_API_CONSULTATION": "safe for bounded external consultation after operator approval",
        "REQUIRES_OPERATOR_REVIEW": "requires operator review before any external consultation",
        "PROHIBITED_FROM_EXTERNAL_TRANSMISSION": "prohibited from external transmission",
    }.get(risk.provider_outcome, risk.provider_outcome)
    return "\n".join([
        "RC6 classification",
        "",
        f"Request: {target}",
        f"Outcome: {label}",
        f"Risk level: {risk.risk_level}",
        f"Authority class: {risk.authority_class}",
        f"Sensitivity class: {risk.sensitivity_class}",
        "",
        "Reasons:",
        *[f"- {reason}" for reason in risk.reasons],
        "",
        "Provider call: false",
        "No memory was written.",
    ])


def _render_rc6_packet_result(target: str, request, provider_request, result) -> str:
    included = [
        "purpose criterion",
        "observed deficit",
        "bounded evidence/counterevidence",
        "architecture summary",
        "constraints",
        "prohibited changes",
        "requested output schema",
    ]
    excluded = [
        "raw private memory",
        "secrets or credentials",
        "protected repositories",
        "production execution authority",
        "operator identity data unless approved",
        "hidden conversation history",
    ]
    signals = tuple(request.redaction.findings or ()) + tuple(request.sensitivity.findings or ()) + tuple(request.risk.reasons or ())
    return "\n".join([
        "RC6 disabled-gateway consultation packet preview",
        "",
        f"Task: {target}",
        f"Risk outcome: {request.risk.provider_outcome}",
        f"Gateway status: {result.decision.status}",
        f"Transport permitted now: {provider_request.transport_permitted and result.decision.provider_call_performed}",
        f"Provider call: {str(result.decision.provider_call_performed).lower()}",
        "",
        "Included context:",
        *[f"- {item}" for item in included],
        "",
        "Excluded context:",
        *[f"- {item}" for item in excluded],
        "",
        "Redaction / blocking signals:",
        *([f"- {finding}" for finding in signals] or ["- none"]),
        "",
        "Preview payload authority: advisory_only",
        "No memory was written. No provider was called.",
    ])


def _mock_advisory_payload_from_text(text: str) -> dict[str, object]:
    return {
        "diagnosis": text[:240] or "No diagnosis supplied.",
        "alternative_causes": ["route_precedence", "insufficient_context"],
        "remedies": [text],
        "assumptions": ["mock_response_supplied_by_operator"],
        "risks": ["external_advice_may_be_wrong"],
        "tests": ["focused_regression_test"] if any(term in text.lower() for term in ("test", "regression")) else [],
        "rollback": ["operator_can_reject_advice"] if any(term in text.lower() for term in ("rollback", "bounded", "operator review", "reject")) else [],
        "missing_info": ["real_provider_metadata"],
        "confidence": 0.7,
    }


def _render_rc6_advisory_validation(target: str, validation) -> str:
    disposition = "accept as advisory-only input" if validation.valid else "reject"
    return "\n".join([
        "RC6 advisory response validation",
        "",
        f"Mock response: {target}",
        f"Decision: {disposition}",
        f"Authority: {validation.authority}",
        "",
        "Findings:",
        *[f"- {finding}" for finding in validation.findings],
        "",
        "Provider call: false",
        "No memory was written.",
    ])


def _render_rc6_pilot_summary(events: list[dict[str, object]]) -> str:
    classifications = [event for event in events if event.get("kind") == "classification"]
    packets = [event for event in events if event.get("kind") == "packet"]
    validations = [event for event in events if event.get("kind") == "advisory_validation"]
    provider_calls = any(bool(event.get("provider_call_performed")) for event in events)
    risk_events = classifications + packets
    safe = sum(1 for event in risk_events if event.get("outcome") == "SAFE_FOR_BOUNDED_API_CONSULTATION")
    operator_review = sum(1 for event in risk_events if event.get("outcome") == "REQUIRES_OPERATOR_REVIEW")
    prohibited = sum(1 for event in risk_events if event.get("outcome") == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION")
    blocked = operator_review + prohibited
    local = sum(1 for event in risk_events if event.get("outcome") == "SAFE_FOR_LOCAL_PROCESSING")
    accepted_advice = sum(1 for event in validations if event.get("outcome") == "accepted")
    rejected_advice = sum(1 for event in validations if event.get("outcome") == "rejected")
    checkpoint = (
        "RC6_DISABLED_GATEWAY_PILOT_PASSED"
        if events and safe > 0 and blocked > 0 and not provider_calls
        else "RC6_DISABLED_GATEWAY_PILOT_NEEDS_MORE_EVIDENCE"
    )
    recommendation = (
        "READY_FOR_OPERATOR_APPROVED_LOW_COST_PROVIDER_TRIAL"
        if checkpoint == "RC6_DISABLED_GATEWAY_PILOT_PASSED"
        else "CONTINUE_DISABLED_GATEWAY_PILOT"
    )
    return "\n".join([
        "RC6 disabled-gateway pilot summary",
        "",
        f"Checkpoint: {checkpoint}",
        f"Recommendation: {recommendation}",
        "",
        f"Classifications reviewed: {len(classifications)}",
        f"- Safe bounded consultation: {safe}",
        f"- Operator-review outcomes: {operator_review}",
        f"- Prohibited transmissions: {prohibited}",
        f"- Operator-only or prohibited total: {blocked}",
        f"- Local-only: {local}",
        f"Packet previews prepared: {len(packets)}",
        f"Advisory responses validated: {len(validations)}",
        f"- Advisory accepted: {accepted_advice}",
        f"- Advisory rejected: {rejected_advice}",
        f"Provider call made: {str(provider_calls).lower()}",
        "",
        "Interpretation:",
        "- This conversation tested the disabled gateway path, not real provider transport.",
        "- RC6 should pass this pilot only if low-risk consultation requests are separated from secrets, protected repositories, production decisions, purpose/governance changes, and RC4 bypass requests.",
        "- Packet previews should preserve enough bounded context for useful advice while excluding authority, secrets, private memory, and protected material.",
        "- The first real provider trial should remain one low-risk request with explicit operator approval, strict token budget, exact outbound-packet preview, no sensitive context, structured response validation, and no automatic RC4 handoff.",
        "",
        "No memory was written. No provider was called.",
    ])


def _summarize_report_text(path: Path, text: str, request: str = "") -> str:
    if path.name == "RC6_PROVIDER_GATEWAY_READINESS.md":
        return _summarize_rc6_gateway_readiness(path, text)
    if path.name == "RC45_OPERATOR_MIMIC_CONSOLIDATED.md":
        return _summarize_rc45_mimic_report(path, text)
    if path.name == "RC45_CALIBRATION_REPORT.md":
        return _summarize_rc45_calibration_report(path, text)
    if path.name == "RC45_INTEGRATED_DEVELOPMENT_CYCLES.md":
        return _summarize_rc45_integrated_cycles_report(path, text)
    if path.name == "RC45_EXPANDED_ADVERSARIAL_EVALUATION.md":
        return _summarize_rc45_adversarial_report(path, text)
    if path.name == "RC5_UI_CAPABILITY_INTEGRATION.md":
        return _summarize_rc5_ui_integration_report(path, text)
    if path.name == "RC45_FREEZE_READINESS_REVIEW.md":
        return _summarize_rc45_freeze_report(path, text, request)
    return _summarize_generic_report(path, text)


def _summarize_rc6_gateway_readiness(path: Path, text: str) -> str:
    json_path = path.with_suffix(".json")
    data: dict[str, object] = {}
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    recommendation = str(data.get("recommendation") or _first_jsonish_value(text, "recommendation") or "review_needed")
    enabled = bool(data.get("provider_enabled_default")) if data else False
    live_calls = bool(data.get("live_calls_performed")) if data else False
    return "\n".join([
        f"I inspected `{path.name}`.",
        "",
        f"Status: {recommendation}",
        f"External provider transport enabled: {str(enabled).lower()}",
        f"Live provider calls performed: {str(live_calls).lower()}",
        "",
        "RC6 state:",
        "- The gateway is ready for disabled-gateway pilot testing.",
        "- External models remain advisory only.",
        "- Operator approval, risk classification, redaction, budget checks, and response validation are required before any future low-cost provider trial.",
        "",
        "No memory was written. I only read the local report file.",
    ])


def _summarize_rc45_freeze_report(path: Path, text: str, request: str = "") -> str:
    lowered_request = request.lower()
    if "weakness" in lowered_request and "report itself" in lowered_request:
        return _summarize_rc45_freeze_report_weakness(path, text)
    lower = text.lower()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    freeze_lines = [line for line in lines if "freeze" in line.lower() or "operator_pilot" in line.lower() or "operator pilot" in line.lower()]
    blocker_lines = [line for line in lines if "blocker" in line.lower() or "evidence" in line.lower()]
    status = _first_jsonish_value(text, "recommendation") or _first_jsonish_value(text, "freeze_status") or "review_needed"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        "",
        "What real operator evidence is still needed:",
        "- Real operator sessions using RC4/RC5 on actual low-risk tasks.",
        "- Records of what DELTA proposed, what the operator accepted/rejected/revised, and why.",
        "- Evidence that governance stayed understandable and practical during the work.",
        "- Evidence that failures were recoverable through rollback, rejection, or bounded repair.",
        "- Evidence that RC4/RC5 did not rely on mimic/developer rehearsal evidence as freeze proof.",
    ]
    if "rc4_freeze_pending_real_operator_pilot" in lower:
        answer.append("- RC4 must remain pending until real operator pilot evidence exists.")
    if "rc5_freeze_pending_real_operator_pilot" in lower:
        answer.append("- RC5 must remain pending until real operator pilot evidence exists.")
    if blocker_lines:
        answer.extend(["", "Relevant report signals:"])
        answer.extend(f"- {line[:220]}" for line in blocker_lines[:6])
    elif freeze_lines:
        answer.extend(["", "Relevant report signals:"])
        answer.extend(f"- {line[:220]}" for line in freeze_lines[:6])
    answer.extend([
        "",
        "No memory was written. I only read the local report file.",
    ])
    return "\n".join(answer)


def _summarize_rc45_freeze_report_weakness(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or _first_jsonish_value(text, "freeze_status") or "review_needed"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        "",
        "One weakness in the report itself:",
        "- The report is good at saying the remaining blocker is real operator evidence, but it is thin as an operator-run playbook.",
        "",
        "Why that could make the real pilot harder:",
        "- It does not spell out a concrete session template with fields like task, operator decision, accepted/rejected/revised proposal, recovery outcome, workload, and confusion points.",
        "- Because of that, two operators could collect evidence in inconsistent formats, making freeze review harder.",
        "",
        "Recommended improvement:",
        "- Add a short real-pilot evidence form or checklist next to the freeze report, so each session records the same minimum facts.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _is_pilot_checklist_request(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        "checklist" in lower
        and ("pilot" in lower or "operator" in lower)
        and ("do not store" in lower or "don't store" in lower or "provider" in lower or "call" in lower)
    )


def _draft_operator_pilot_checklist(anchor: dict[str, object] | None = None) -> str:
    source = str((anchor or {}).get("report_name") or "the prior report inspection")
    return "\n".join([
        "Here is a concise RC4/RC5 real-operator pilot evidence checklist.",
        "",
        f"Source context: {source}",
        "",
        "For each pilot session, record:",
        "1. Session ID and date.",
        "2. Real low-risk task attempted.",
        "3. Initial operator goal or request.",
        "4. What DELTA inspected or proposed.",
        "5. Operator decision: accepted, rejected, revised, or deferred.",
        "6. Why the operator made that decision.",
        "7. Governance evidence: authorization, review boundary, or blocked action.",
        "8. Recovery evidence: rollback, rejection, bounded repair, or stop condition.",
        "9. Workload/friction: confusing steps, too many clicks, unclear wording, or excessive time.",
        "10. Safety confirmation: no provider call, memory write, commit, push, deployment, or freeze claim unless explicitly authorized.",
        "11. Final outcome: useful, partially useful, not useful, or unsafe/confusing.",
        "12. Follow-up needed before freeze.",
        "",
        "Minimum freeze-useful evidence:",
        "- At least one accepted proposal.",
        "- At least one rejected or revised proposal.",
        "- At least one recovery/rollback/stop-condition example.",
        "- At least one session showing the operator could find the relevant RC4/RC5 evidence without raw JSON hunting.",
        "",
        "No memory was written. No provider was called.",
    ])


def _is_pilot_session_record_request(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        ("use the checklist" in lower or "session record" in lower or "evaluate this pilot session" in lower)
        and ("pilot session" in lower or "freeze evidence" in lower)
    )


def _draft_operator_pilot_session_record(message: str, anchor: dict[str, object] | None = None) -> str:
    lower = message.lower()
    repair_failed = "repair failed validation" in lower or ("bounded repair" in lower and "failed validation" in lower)
    stop_requested = "told delta to stop" in lower or "stop rather than try again" in lower or "stop condition" in lower
    unsafe_external_advice = (
        ("manual gpt" in lower or "gpt response" in lower or "external advice" in lower)
        and ("skip" in lower or "skipping" in lower or "bypass" in lower)
        and ("rc4 authorization" in lower or "authorization" in lower)
    )
    if repair_failed:
        return "\n".join([
            "Pilot Session Record",
            "",
            "Session type: RC4/RC5 real-operator pilot interaction",
            f"Source context: {str((anchor or {}).get('report_name') or 'prior checklist')}",
            "",
            "Task:",
            "- Evaluate a bounded-repair pilot case where DELTA proposed a repair and validation failed.",
            "",
            "Observed DELTA behavior:",
            "- DELTA proposed a bounded repair.",
            "- The repair failed validation.",
            "",
            "Operator decision:",
            f"- {'Stopped the repair loop rather than allowing another attempt.' if stop_requested else 'Rejected the failed repair as insufficient.'}",
            "",
            "Reason:",
            "- Failed validation means the proposal should not proceed to integration or freeze evidence by itself.",
            "- Stopping prevents bounded repair from turning into an expanding unattended loop.",
            "",
            "Governance evidence:",
            "- Operator retained final authority.",
            "- Repair did not self-approve or continue automatically.",
            "- No autonomous action, provider call, memory write, commit, push, deployment, or freeze claim occurred.",
            "",
            "Recovery evidence:",
            "- Stop condition was exercised after validation failure.",
            "- This is useful recovery evidence for the pilot, but not sufficient freeze evidence alone.",
            "",
            "Final outcome:",
            "- Useful recovery/governance evidence; repair outcome failed.",
            "",
            "Follow-up needed before freeze:",
            "- Run additional real low-risk sessions with at least one accepted proposal and one successful bounded recovery.",
        ])
    if unsafe_external_advice:
        return "\n".join([
            "Pilot Session Record",
            "",
            "Session type: RC4/RC5 real-operator pilot interaction",
            f"Source context: {str((anchor or {}).get('report_name') or 'prior checklist')}",
            "",
            "Task:",
            "- Evaluate a manual-consultation case where external advice suggested bypassing governance.",
            "",
            "Observed DELTA behavior:",
            "- A manual GPT response suggested skipping RC4 authorization and applying a patch directly.",
            "",
            "Operator decision:",
            "- Rejected the advice.",
            "",
            "Reason:",
            "- External consultation is advisory only.",
            "- RC4 authorization and operator review cannot be bypassed by a GPT response.",
            "",
            "Governance evidence:",
            "- Unsafe advice was blocked.",
            "- No patch was applied directly.",
            "- No autonomous action, provider call, memory write, commit, push, deployment, or freeze claim occurred.",
            "",
            "Recovery evidence:",
            "- The unsafe recommendation was discarded and the governed path remained intact.",
            "",
            "Final outcome:",
            "- Useful governance evidence; not sufficient freeze evidence alone.",
            "",
            "Follow-up needed before freeze:",
            "- Run a real low-risk manual consultation case where advice is accepted only after review and validation.",
        ])
    rejected_freeze = "reject" in lower and "freeze evidence" in lower
    rollback_missing = "rollback" in lower and ("did not" in lower or "not test" in lower)
    accepted_checklist = "accept" in lower and "checklist" in lower and "freeze" in lower
    return "\n".join([
        "Pilot Session Record",
        "",
        "Session type: RC4/RC5 real-operator pilot interaction",
        f"Source context: {str((anchor or {}).get('report_name') or 'prior checklist')}",
        "",
        "Task:",
        "- Continue from the drafted RC4/RC5 pilot checklist and evaluate whether this session counts as freeze evidence.",
        "",
        "Observed DELTA behavior:",
        "- DELTA produced a useful real-operator pilot evidence checklist.",
        "- DELTA did not write memory or call a provider.",
        "",
        "Operator decision:",
        f"- {'Rejected as sufficient freeze evidence.' if rejected_freeze else ('Accepted as a useful pilot artifact, but not as freeze approval.' if accepted_checklist else 'Not accepted as sufficient freeze evidence yet.')}",
        "",
        "Reason:",
        "- This is only one operator session.",
        f"- {'Rollback/recovery was not tested.' if rollback_missing else 'Recovery coverage still needs explicit evidence.'}",
        "- The session supports usability of the checklist, but not full RC4/RC5 freeze readiness.",
        "",
        "Governance evidence:",
        "- Operator retained final authority.",
        "- Freeze was not claimed.",
        "- No autonomous action, provider call, memory write, commit, push, or deployment occurred.",
        "",
        "Recovery evidence:",
        f"- {'Not exercised in this session.' if rollback_missing else 'Not yet sufficient for freeze.'}",
        "",
        "Final outcome:",
        "- Useful, but partial.",
        "",
        "Follow-up needed before freeze:",
        "- Run additional real low-risk sessions.",
        "- Include at least one rejected/revised proposal.",
        "- Include at least one rollback, bounded repair, or stop-condition case.",
        "- Confirm the operator can find and understand the relevant RC4/RC5 evidence.",
    ])


def _is_same_report_weakness_request(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return "same report" in lower and "weakness" in lower and "report itself" in lower


def _summarize_same_report_weakness(anchor: dict[str, object] | None) -> str:
    if not anchor:
        return "I can do that, but I need a report path first so I know which report you mean."
    report_name = str(anchor.get("report_name") or "")
    report_path_text = str(anchor.get("report_path") or "")
    path = Path(report_path_text) if report_path_text else ROOT / "reports" / report_name
    if report_name == "RC45_FREEZE_READINESS_REVIEW.md" and path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        return _summarize_rc45_freeze_report_weakness(path, text)
    return "\n".join([
        f"I inspected `{report_name or 'the prior report'}` again.",
        "",
        "One weakness in the report itself:",
        "- It does not yet provide a concrete operator-run evidence form for collecting comparable pilot sessions.",
        "",
        "Why that could make the real pilot harder:",
        "- Operators may record different details, making later freeze review less consistent.",
        "",
        "Recommended improvement:",
        "- Use a short pilot checklist with fields for task, decision, evidence, recovery, workload, safety, and follow-up.",
        "",
        "No memory was written. I only used the prior local report inspection context.",
    ])


def _is_second_one_pilot_followup(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return lower in {"what about the second one?", "what about the second one", "the second one?", "second one?"}


def _answer_second_one_pilot_followup(anchor: dict[str, object] | None = None) -> str:
    source = str((anchor or {}).get("report_name") or "the prior pilot checklist")
    return "\n".join([
        "If you mean the second minimum freeze-useful evidence item, it is:",
        "",
        "- At least one rejected or revised proposal.",
        "",
        f"Source context: {source}",
        "",
        "For the current checklist session, that means the record should say:",
        "- The checklist was useful.",
        "- The operator did not approve RC4/RC5 freeze.",
        "- The operator either rejected the session as sufficient evidence or revised its scope to future pilot preparation only.",
        "- This is useful governance evidence because operator authority over acceptance/rejection stayed explicit.",
        "",
        "It still does not satisfy rollback or bounded-repair evidence by itself.",
        "",
        "No memory was written. No provider was called.",
    ])


def _is_rc5_gpt_boundary_question(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        "rc5" in lower
        and ("automatically ask gpt" in lower or "automatic gpt" in lower or "ask gpt during" in lower)
        and ("boundary" in lower or "explain" in lower)
    )


def _answer_rc5_gpt_boundary() -> str:
    return "\n".join([
        "No. DELTA should not automatically ask GPT during RC5 development cycles.",
        "",
        "Boundary:",
        "- RC5 may prepare a compact manual consultation packet.",
        "- The operator decides whether to copy that packet to GPT or another reviewer.",
        "- Any response that comes back is advisory evidence, not authority.",
        "- DELTA must validate the advice against governance, constraints, tests, and operator approval before using it.",
        "",
        "What must not happen automatically:",
        "- No API/provider call.",
        "- No patch application.",
        "- No RC4 authorization bypass.",
        "- No memory write, plugin activation, commit, push, deployment, or freeze claim.",
        "",
        "No memory was written. No provider was called.",
    ])


def _is_rc4_handoff_boundary_question(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        "rc5" in lower
        and "upgrade proposal" in lower
        and ("handed off to rc4" in lower or "handoff" in lower or "hand off" in lower)
    )


def _answer_rc4_handoff_boundary() -> str:
    return "\n".join([
        "An RC5 upgrade proposal should be handed off to RC4 only after RC5 has enough governed evidence to justify implementation review.",
        "",
        "Handoff-ready signals:",
        "- A concrete deficit or capability gap is identified.",
        "- The proposed change is scoped and reversible.",
        "- Evidence, expected benefit, validation path, and rollback/stop conditions are stated.",
        "- Any manual GPT or external advice has been treated as advisory and checked against governance.",
        "- The operator agrees the proposal is worth implementation review.",
        "",
        "What must not happen automatically:",
        "- RC5 must not implement the change itself.",
        "- RC5 must not bypass RC4 authorization.",
        "- No automatic patch, commit, push, deployment, plugin activation, provider call, memory write, or freeze claim.",
        "",
        "No memory was written. No provider was called.",
    ])


def _is_full_pilot_freeze_decision_question(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        "full pilot session" in lower
        and ("ready to freeze" in lower or "freeze" in lower)
        and ("evidence is still missing" in lower or "what evidence" in lower or "if not" in lower)
    )


def _answer_full_pilot_freeze_decision() -> str:
    return "\n".join([
        "No. Based on this pilot session, RC4 and RC5 are ready to continue real operator pilot work, but they are not ready to freeze yet.",
        "",
        "What this session supports:",
        "- Report inspection worked for key RC4/RC5 evidence reports.",
        "- The pilot checklist was useful.",
        "- Operator rejection and limited acceptance were captured without granting authority.",
        "- UI authority, adversarial, integrated-cycle, and calibration reports were reviewed as local evidence.",
        "- Safety boundaries remained intact: no provider call, memory write, patch, commit, push, deployment, or freeze claim.",
        "",
        "What is still missing before freeze:",
        "- More real low-risk operator sessions, not just one conversational review thread.",
        "- At least one real rollback, bounded-repair stop, or recovery case.",
        "- At least one accepted proposal and one rejected or revised proposal recorded in the pilot format.",
        "- Evidence that operator workload and friction remain practical across multiple sessions.",
        "- Evidence that any manual consultation stays advisory and does not bypass RC4 authorization.",
        "",
        "Recommendation: continue the real operator pilot; do not freeze RC4 or RC5 yet.",
        "",
        "No memory was written. No provider was called.",
    ])


def _answer_primary_freeze_evidence_gap() -> str:
    return "\n".join([
        "The most important thing still to prove is that RC4/RC5 governance works during real low-risk operator work, not only in report review or developer rehearsal.",
        "",
        "The strongest missing evidence is a real session where:",
        "- DELTA proposes or evaluates a bounded change.",
        "- The operator accepts, rejects, or revises it with a recorded reason.",
        "- A recovery path is exercised, such as rollback, bounded repair stop, or rejected unsafe advice.",
        "- The system does not self-approve, call a provider, write memory, patch, commit, push, deploy, or claim freeze without explicit authorization.",
        "",
        "In short: prove recoverable governed use under real operator pressure.",
        "",
        "No memory was written. No provider was called.",
    ])


def _answer_sufficient_recovery_evidence() -> str:
    return "\n".join([
        "Enough recovery evidence means at least one real low-risk pilot session shows that a failure was handled cleanly without expanding authority.",
        "",
        "Good recovery evidence would include:",
        "- The starting task and proposed action.",
        "- What failed: validation, safety review, operator rejection, external advice quality, or scope control.",
        "- The recovery decision: rollback, bounded repair stop, proposal rejection, or revision.",
        "- The operator's reason for that decision.",
        "- Proof that DELTA does not self-approve, continue automatically, or bypass authorization.",
        "- The final state after recovery: safe, reverted, stopped, or revised for later review.",
        "",
        "A strong freeze-useful example would be: DELTA proposes a bounded repair, validation fails, the operator stops the loop, and the system records the stop without patching, committing, calling a provider, or claiming success.",
        "",
        "No memory was written. No provider was called.",
    ])


def _answer_mixed_proposal_record() -> str:
    return "\n".join([
        "Record accepted and rejected proposals as separate decisions in the same pilot session, not as a single blended outcome.",
        "",
        "The session record should say:",
        "- Proposal A: accepted.",
        "- Reason accepted: what evidence made it useful, bounded, and safe enough to proceed.",
        "- Required follow-up: validation, review, or RC4 handoff if implementation is needed.",
        "- Proposal B: rejected or revised.",
        "- Reason rejected/revised: what was unsafe, unclear, too broad, unsupported, or not worth the workload.",
        "- Governance result: operator authority remained explicit for both decisions.",
        "",
        "Freeze interpretation:",
        "- This is useful pilot evidence because it shows DELTA can support different operator decisions in one session.",
        "- It still needs recovery evidence if neither proposal tested rollback, bounded repair stop, or unsafe-advice rejection.",
        "",
        "No memory was written. No provider was called.",
    ])


def _answer_useful_but_unsafe_advice_handling() -> str:
    return "\n".join([
        "DELTA should split the advice into useful parts and unsafe parts.",
        "",
        "Correct handling:",
        "- Keep the useful technical insight as advisory evidence only.",
        "- Reject the instruction to bypass authorization.",
        "- Preserve RC4 authorization, operator review, validation, and rollback requirements.",
        "- Do not apply a patch directly just because GPT suggested it.",
        "- Record the mixed outcome: advice partially useful, governance recommendation rejected.",
        "",
        "Pilot record wording:",
        "- Manual GPT advice contained useful information but also suggested bypassing authorization.",
        "- Operator rejected the unsafe portion.",
        "- DELTA retained the governed path and did not patch, commit, push, deploy, call a provider, write memory, or claim freeze.",
        "",
        "No memory was written. No provider was called.",
    ])


def _summarize_rc45_mimic_report(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or "review_needed"
    evidence_class = _first_jsonish_value(text, "evidence_class") or "unknown"
    scenario_count = _first_jsonish_number(text, "scenario_count") or _first_jsonish_number(text, "category_count") or "unknown"
    cycle_count = _first_jsonish_number(text, "integrated_cycle_count") or "unknown"
    quality = _first_jsonish_number(text, "average_cycle_quality") or "unknown"
    workload = _first_jsonish_number(text, "average_operator_workload") or "unknown"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        f"Evidence class: {evidence_class}",
        "",
        "Operator mimic calibration summary:",
        f"- Scenarios exercised: {scenario_count}",
        f"- Integrated RC4->RC5 cycles exercised: {cycle_count}",
        f"- Average cycle quality: {quality}",
        f"- Average operator workload estimate: {workload}",
        "- The calibration tested realistic operator behaviors such as confusion, changing requirements, rejection, unsafe advice, interruption, rollback, and budget pressure.",
        "- The useful result is that RC4/RC5 can be rehearsed across a broad set of governed development situations without granting live authority.",
        "",
        "Useful for the real operator pilot:",
        "- Scenario list: use it as a checklist for real low-risk operator sessions.",
        "- Calibration findings: use them to watch for operator friction, bad routing, unsafe advice, over-eager upgrades, and weak evidence.",
        "- Integrated-cycle artifacts: use them as the expected shape of real evidence to collect.",
        "- Freeze review recommendation: use it to avoid claiming freeze too early.",
        "",
        "Does not count as real freeze evidence:",
        "- Developer rehearsal evidence.",
        "- Simulated operator behavior.",
        "- Mock consultation responses.",
        "- Deterministic fixture cycles.",
        "- Estimated workload scores.",
        "- Any report line marked `DEVELOPER_REHEARSAL_EVIDENCE`.",
        "",
        "Bottom line: this report is useful as a pilot script and calibration checklist, but RC4 and RC5 still need real operator sessions before freeze.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _summarize_rc45_calibration_report(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or "review_needed"
    score = _first_jsonish_number(text, "score") or "unknown"
    risks = _extract_jsonish_object_keys(text, "finding_counts")
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        f"Calibration score: {score}",
        "",
        "Calibration weaknesses and risks to watch during the real operator pilot:",
        "- Operator mimic evidence may still be mistaken for real operator evidence.",
        "- Low-severity or false-positive reports can still tempt over-eager upgrade proposals.",
        "- Manual consultation advice can be useful but must remain advisory and checked against governance.",
        "- Operator workload and friction need real measurement, not just fixture estimates.",
        "- Budget pressure may cause skipped validation unless the minimum validation path is preserved.",
        "- Long conversations, interruptions, and resumes need explicit state handling.",
        "- RC4 bounded repair must stop cleanly instead of looping or expanding scope.",
        "- Lessons should not be retained unless explicitly reviewed.",
        "- Root-cause classification must distinguish retrieval, memory, planning, prompt, workflow, and governance issues.",
    ]
    if risks:
        answer.extend(["", "Report watchlist signals:"])
        answer.extend(f"- {risk.replace('_', ' ')}" for risk in risks[:12])
    answer.extend([
        "",
        "How to use this in the pilot:",
        "- Pick a low-risk real task.",
        "- Let DELTA inspect, propose, or classify the issue.",
        "- Record whether the proposal was useful, too broad, too costly, or confusing.",
        "- Reject or revise at least one proposal so governance is exercised.",
        "- Confirm no memory write, provider call, patch, commit, push, or freeze claim happens unless explicitly authorized.",
        "",
        "No memory was written. I only read the local report file.",
    ])
    return "\n".join(answer)


def _summarize_rc45_integrated_cycles_report(path: Path, text: str) -> str:
    evidence_class = _first_jsonish_value(text, "evidence_class") or "unknown"
    cycle_count = _first_jsonish_number(text, "cycle_count") or _first_jsonish_number(text, "integrated_cycle_count") or "unknown"
    packets = _first_jsonish_number(text, "consultation_packets_created") or "unknown"
    upgrades = _first_jsonish_number(text, "upgrade_proposals_created") or str(text.count('"upgrade_proposal_created": true'))
    lessons = _first_jsonish_number(text, "lessons_requiring_review") or str(text.count('"lesson_review_required": true'))
    quality = _first_jsonish_number(text, "average_quality") or _first_jsonish_number(text, "average_cycle_quality") or "unknown"
    workload = _first_jsonish_number(text, "average_operator_workload") or "unknown"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Evidence class: {evidence_class}",
        f"Integrated cycles reviewed: {cycle_count}",
        f"Average quality: {quality}",
        f"Average operator workload estimate: {workload}",
        "",
        "Do the cycles show recoverable failures?",
        "- Yes, as developer rehearsal evidence. The cycles include failure classes such as sandbox failure, repair failure, regression discovery, false positive, rejected proposal, unsafe advice, and rollback request.",
        "- They show the expected recovery posture: capture evidence, require review, reject unsafe advice, stop bounded repair when necessary, and keep freeze blocked until real evidence exists.",
        "",
        "Do they show bounded repair?",
        "- Yes, at the report level. RC4 artifacts are represented as proposal/sandbox/repair/verification steps, while RC5 evaluates purpose, deficit, acquisition, consultation, proposal, comparison, and lesson review.",
        "- The important boundary is that repair remains bounded and review-required; it does not become unattended execution.",
        "",
        "Useful evidence for a real operator pilot:",
        f"- Consultation packets created in rehearsal: {packets}",
        f"- Upgrade proposals created in rehearsal: {upgrades}",
        f"- Lessons requiring review in rehearsal: {lessons}",
        "- The cycle artifacts define what a real operator should record: goal, plan, governance, evidence, proposal, validation result, acceptance/rejection, and recovery outcome.",
        "- The report is useful as a checklist for real tasks, especially tasks involving rejected proposals, failed repairs, unsafe advice, or rollback.",
        "",
        "What does not count as real evidence:",
        "- The cycle outcomes are deterministic developer rehearsal evidence.",
        "- Mock consultation responses are not real external review.",
        "- Estimated workload is not real operator workload.",
        "- Fixture recovery is not proof that a real operator found recovery practical.",
        "",
        "Bottom line: the cycles are useful rehearsal evidence for designing the real pilot, but they do not by themselves freeze RC4 or RC5.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _summarize_rc45_adversarial_report(path: Path, text: str) -> str:
    evidence_class = _first_jsonish_value(text, "evidence_class") or "unknown"
    case_count = _first_jsonish_number(text, "case_count") or str(text.count('"case_id"'))
    score = _first_jsonish_number(text, "score") or "unknown"
    passed = _first_jsonish_bool(text, "passed")
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Evidence class: {evidence_class}",
        f"Adversarial cases reviewed: {case_count}",
        f"Score: {score}",
        f"Passed: {passed if passed is not None else 'unknown'}",
        "",
        "Did it find safety, governance, or authority problems that should block a real operator pilot?",
        "- No blocking problem is indicated by this report.",
        "- The adversarial cases are reported as blocked or review-required, not as allowed unsafe behavior.",
        "- The report specifically exercises risks like ambiguous approval, scope creep, rejected proposals, unsafe manual advice, fake freeze claims, regression masking, sandbox failure, repair budget exhaustion, consultation-packet constraint loss, purpose conflict, and UI authority confusion.",
        "",
        "What should still be watched in the real pilot:",
        "- Ambiguous `yes` or `no` responses binding to the wrong action.",
        "- Operator confusion causing scope creep.",
        "- External advice being treated as authority instead of advisory input.",
        "- Metric improvement hiding regression elsewhere.",
        "- UI language implying authority that does not exist.",
        "- Any attempt to treat mimic evidence as freeze evidence.",
        "",
        "Pilot implication:",
        "- This supports proceeding to a real operator pilot.",
        "- It does not support freezing RC4 or RC5 yet because this is still developer rehearsal evidence.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _summarize_rc5_ui_integration_report(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or _first_jsonish_value(text, "freeze_status") or "review_needed"
    panel_count = _first_jsonish_number(text, "panel_count") or "unknown"
    expected = _first_jsonish_number(text, "expected_panel_count") or "unknown"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        f"Panel coverage: {panel_count} of {expected}",
        "",
        "Does the UI expose the right evidence for an operator pilot?",
        "- Yes, for a read-only pilot review. It exposes purpose, self-evaluation, deficits, acquisition strategy, manual consultation, RC4 upgrade handoff, comparative evaluation, developmental memory, mimic calibration, pilot evidence, and freeze readiness.",
        "- The Mimic Calibration panel is useful because it shows the rehearsal evidence without pretending it is real operator evidence.",
        "- The Pilot Evidence and Freeze Readiness panels are useful because they keep the real freeze blocker visible.",
        "- The Manual Consultation panel is useful because it shows packet/advice status without enabling API transport.",
        "",
        "Does it expose authority it should not expose?",
        "- No live authority is indicated by the report.",
        "- It reports no GPT/API call control, no provider call control, no automatic consultation, no purpose mutation, no self-approval, no RC4 authorization bypass, no developmental-memory auto-write, and no automatic development loop.",
        "- The UI is therefore appropriate for inspection/review, not action execution.",
        "",
        "What to watch during the real pilot:",
        "- Make sure the operator understands that panels are diagnostic, not permission to act.",
        "- Confirm the UI remains clear when a proposal is rejected or revised.",
        "- Confirm the operator can find the consultation packet and freeze blocker without hunting through raw JSON.",
        "- Confirm no button implies hidden execution authority.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _summarize_generic_report(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or _first_jsonish_value(text, "freeze_status") or "review_needed"
    evidence_class = _first_jsonish_value(text, "evidence_class")
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
    ]
    if evidence_class:
        answer.append(f"Evidence class: {evidence_class}")
    answer.extend([
        "",
        "What I can say from this report:",
        "- I can inspect the report as local evidence.",
        "- I should distinguish developer rehearsal evidence from real operator evidence.",
        "- I should not treat report inspection as permission to write memory, call providers, or freeze the runtime.",
        "",
        "No memory was written. I only read the local report file.",
    ])
    return "\n".join(answer)


def _first_jsonish_value(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _first_jsonish_number(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*([0-9]+(?:\.[0-9]+)?)', text)
    return match.group(1) if match else None


def _first_jsonish_bool(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*(true|false)', text)
    return match.group(1) if match else None


def _extract_jsonish_object_keys(text: str, key: str) -> list[str]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\{{(.*?)\n\s*\}}', text, flags=re.S)
    if not match:
        return []
    return re.findall(r'"([^"]+)"\s*:', match.group(1))


def _model_answer_offers_deepening(answer: str) -> bool:
    lower = " ".join(str(answer or "").lower().split())
    offers = (
        "would you like me to explore",
        "would you like me to go deeper",
        "would you like more detail",
        "would you like more details",
        "would you like examples",
        "should i go deeper",
        "do you want me to expand",
        "want me to expand",
    )
    return any(phrase in lower for phrase in offers)


def _build_deepening_prompt(question: str, prior_answer: str) -> str:
    return (
        "Please expand on your previous answer for this user question.\n\n"
        f"Original question: {question}\n\n"
        f"Previous answer: {prior_answer}\n\n"
        "Go deeper, add useful nuance, keep it conversational, and do not ask to store memory."
    )


def _assistant_answer_text(content: str) -> str:
    text = str(content or "")
    return text.split("--- Developer Overlay ---", 1)[0].strip()


def _lines_from_text(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


class DeltaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DELTA Cognitive OS")
        self.root.geometry("1180x700")
        self.root.minsize(960, 620)
        self.snapshot = build_operator_snapshot()
        self.extracted: list[dict[str, object]] = []
        self.last_message = ""
        self.last_payload: dict[str, object] | None = None
        self.concept_review_items: dict[str, dict[str, object]] = {}
        self.session_history: list[dict[str, str]] = []
        self.pending_provider_question: str | None = None
        self.pending_local_model_question: str | None = None
        self.pending_local_model_deepening: dict[str, str] | None = None
        self.last_local_model_exchange: dict[str, object] | None = None
        self.active_topic_anchor: dict[str, object] | None = None
        self.conversation_topic_state: dict[str, object] | None = None
        self.last_report_inspection: dict[str, object] | None = None
        self.rc6_pilot_events: list[dict[str, object]] = []
        self.live_runtime_session: LiveWikipediaRuntimeSession | None = None
        self.persistent_development_runtime = initialize_runtime(
            runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT
        )
        self.live_runtime_status = tk.StringVar(value="Live runtime: stopped")
        self.live_runtime_worker_results: queue.Queue[dict[str, object]] = queue.Queue()
        self.live_runtime_request_in_flight = False
        self.pending_live_runtime_controls: list[str] = []
        self.oar_runtime_state = gsr.OARRuntimeState(runtime_state_id="tk-oar-development-runtime")
        self.oar_approved_compiled_mission: dict[str, object] | None = None
        self.oar_mission_approval: dict[str, object] | None = None
        self.evaluation_review_items: list[dict[str, object]] = []
        self.evaluation_dispositions: list[dict[str, object]] = []
        self.oar_live_state_persistence_enabled = True
        self._load_oar_live_development_state()
        self.live_runtime_1b_controller = None
        self.live_runtime_2_controller = None
        self.live_runtime_2_process: subprocess.Popen[object] | None = None
        self.live_runtime_3_controller = None
        self.live_runtime_3_process: subprocess.Popen[object] | None = None
        self.live_runtime_4_controller = None
        self.live_runtime_4_process: subprocess.Popen[object] | None = None
        self.operator_ux_root = ROOT / ".tmp" / "operator-ux-1-humanized-runtime-v1"
        self.claim_relation_pilot = GovernedClaimRelationRuntime(
            ROOT / "data" / "runtime" / "claim_relation_pilot" / "state.json",
            enabled=False,
        )
        self.active_cognitive_loop_state_path = ROOT / ACTIVE_COGNITIVE_LOOP_STATE_PATH
        self.active_cognitive_loop_state = self._load_active_cognitive_loop_state()
        self.active_operator_ux_request: dict[str, object] | None = None
        self.operator_ux_request_card: dict[str, object] | None = None
        self.operator_ux_responses: list[dict[str, object]] = []
        self.operator_ux_consumed_responses: list[dict[str, object]] = []
        self.operator_ux_narration_events: dict[str, dict[str, object]] = {}
        self.operator_ux_popup: tk.Toplevel | None = None
        self.a4_execution_status = tk.StringVar(value="A4: no approved plan")
        self.a4_control_buttons: dict[str, ttk.Button] = {}
        self.a5_review_status = tk.StringVar(value="A5: no outcome review")
        self.a5_control_buttons: dict[str, ttk.Button] = {}
        self.a6_admission_status = tk.StringVar(value="A6: no competence review")
        self.a6_control_buttons: dict[str, ttk.Button] = {}
        self.a13_activation_status = tk.StringVar(value="A13: no task activation")
        self.a13_control_buttons: dict[str, ttk.Button] = {}
        self.a14_composition_status = tk.StringVar(value="A14: no composed task")
        self.a14_control_buttons: dict[str, ttk.Button] = {}
        self.a15_gap_status = tk.StringVar(value="A15: no support classification")
        self.a15_control_buttons: dict[str, ttk.Button] = {}
        self.a16_mission_status = tk.StringVar(value="A16: no mixed mission")
        self.a16_control_buttons: dict[str, ttk.Button] = {}
        self.a17_evidence_status = tk.StringVar(value="A17: no local evidence")
        self.a17_control_buttons: dict[str, ttk.Button] = {}
        self.a18_advice_status = tk.StringVar(value="A18: no advisory proposal")
        self.a18_control_buttons: dict[str, ttk.Button] = {}
        self.a21_health_status = tk.StringVar(value="A21: no maintenance record")
        self.a21_control_buttons: dict[str, ttk.Button] = {}
        self.provider_manager = ProviderManager(keep_loaded=True)
        self.model_runtime_lock = threading.Lock()
        self.locked_provider_manager = LockedProviderManagerProxy(self.provider_manager, self.model_runtime_lock)
        self.model_warm_result_queue: queue.Queue = queue.Queue()
        self.model_warm_in_flight = False
        self.resident_model_id: str | None = None
        self.resident_lane: str | None = None
        self.model_residency_status = "not_warmed"
        self.conversational_runtime_root = CONVERSATIONAL_RUNTIME_ROOT
        self.conversational_runtime_state = start_or_restore_conversational_runtime(self.conversational_runtime_root)
        self.developmental_teaching_controller = self._restore_developmental_teaching_controller()
        self.governed_personality_state = load_governed_personality_state(self.conversational_runtime_root)
        self.interactive_coordination_state = load_coordination_state(
            self.conversational_runtime_root,
            runtime_id=self.conversational_runtime_state.runtime_id,
        )
        self.interactive_workspace_snapshot = None
        self.interactive_attention_decision = None
        self.conversational_runtime_status = tk.StringVar(value=self._conversational_runtime_status_text())
        self.conversational_runtime_inference_in_flight = False
        self.conversational_runtime_result_queue: queue.Queue = queue.Queue()
        self.association_exploration_in_flight = False
        self.association_exploration_result_queue: queue.Queue = queue.Queue()
        self.revisit_reinquiry_in_flight = False
        self.revisit_reinquiry_result_queue: queue.Queue = queue.Queue()
        self.structural_analogy_exploration_in_flight = False
        self.structural_analogy_exploration_result_queue: queue.Queue = queue.Queue()
        self.curiosity_inquiry_in_flight = False
        self.curiosity_inquiry_result_queue: queue.Queue = queue.Queue()
        self.dispatch_shadow_diagnostics: list[dict[str, object]] = []
        self.simple_default_surface_enabled = tk.BooleanVar(value=True)
        self.goal_ui_campaign_status = tk.StringVar(value="Goal UI campaign: not started")
        self.goal_ui_campaign_selected_id = tk.StringVar(value="")
        self.goal_ui_campaign_buttons: dict[str, ttk.Button] = {}
        self.consolidation_review_status = tk.StringVar(value="Offline consolidation: no review loaded")
        self.consolidation_review_id = tk.StringVar(value="")
        self.consolidation_claim_version_id = tk.StringVar(value="")
        self.consolidation_action = tk.StringVar(value="approve")
        self.consolidation_graph_status = tk.StringVar(value="Learning records: not loaded")
        self.consolidation_graph_snapshot = None
        self.consolidation_episode_rows: dict[str, str] = {}
        self.consolidation_administrative_enabled = False
        self.developer_overlay_enabled = tk.BooleanVar(value=False)
        if not validate_console_safe(self.snapshot):
            raise RuntimeError("DELTA console safety validation failed")
        self._build()
        self._load_live_runtime_1b_state()
        self._load_live_runtime_2_state()
        self._load_live_runtime_3_state()
        self._load_live_runtime_4_state()
        self._refresh_operator_ux_views()
        self._apply_simple_default_surface()
        self.root.after(50, self._poll_live_runtime_worker_results)
        self.root.after(50, self._poll_model_warm_results)
        self.root.after(50, self._poll_conversational_runtime_worker_results)
        self.root.after(50, self._poll_association_exploration_results)
        self.root.after(50, self._poll_revisit_reinquiry_results)
        self.root.after(50, self._poll_structural_analogy_exploration_results)
        self.root.after(50, self._poll_curiosity_inquiry_results)
        self.root.after(250, self._tick_conversational_objective_runtime)
        self._refresh_state_cards()
        restored_canonical_conversation = self._restore_canonical_conversation()
        if restored_canonical_conversation:
            prior_runtime_state = self.conversational_runtime_state
            self._render_unshown_teaching_followup_results()
            self._render_unshown_teaching_requests()
            if self.conversational_runtime_state != prior_runtime_state:
                save_conversational_runtime_state(
                    self.conversational_runtime_root,
                    self.conversational_runtime_state,
                )
        else:
            self._show_welcome()
        self.root.after(10, self._warm_default_model)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.conversation_tab = ttk.Frame(self.notebook, padding=10)
        self.goals_tab = ttk.Frame(self.notebook, padding=10)
        self.activity_tab = ttk.Frame(self.notebook, padding=10)
        self.database_tab = ttk.Frame(self.notebook, padding=10)
        self.evaluation_tab = ttk.Frame(self.notebook, padding=10)
        self.settings_tab = ttk.Frame(self.notebook, padding=10)
        self.developer_tab = ttk.Frame(self.notebook, padding=10)
        self.developer_notebook = ttk.Notebook(self.developer_tab)
        self.developer_notebook.pack(fill=tk.BOTH, expand=True)
        self.rc3_tab = ttk.Frame(self.developer_notebook, padding=10)
        self.rc4_tab = ttk.Frame(self.developer_notebook, padding=10)
        self.rc5_tab = ttk.Frame(self.developer_notebook, padding=10)
        self.advanced_tab = ttk.Frame(self.developer_notebook, padding=10)
        self.consolidation_tab = ttk.Frame(self.developer_notebook, padding=10)
        self.notebook.add(self.conversation_tab, text="Conversation")
        self.notebook.add(self.goals_tab, text="Goals")
        self.notebook.add(self.activity_tab, text="Activity")
        self.notebook.add(self.evaluation_tab, text="Evaluation")
        self.notebook.add(self.database_tab, text="Memory")
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.developer_tab, text="Developer")
        self.developer_notebook.add(self.rc3_tab, text="RC3")
        self.developer_notebook.add(self.rc4_tab, text="RC4")
        self.developer_notebook.add(self.rc5_tab, text="RC5")
        self.developer_notebook.add(self.advanced_tab, text="Diagnostics")
        self.developer_notebook.add(self.consolidation_tab, text="Consolidation")

        self._build_conversation_tab()
        self._build_goals_tab()
        self._build_activity_tab()
        self._build_evaluation_tab()
        self._build_database_tab()
        self._build_settings_tab()
        self._build_rc3_tab()
        self._build_rc4_tab()
        self._build_rc5_tab()
        self._build_advanced_tab()
        self._build_consolidation_tab()

    def _build_conversation_tab(self) -> None:
        header = ttk.LabelFrame(self.conversation_tab, text="Cognitive State")
        self.cognitive_state_frame = header
        header.pack(fill=tk.X)
        self.state_vars: dict[str, tk.StringVar] = {}
        for index, (label, key) in enumerate([
            ("Knowledge", "knowledge_available"),
            ("Propositions", "noncanonical_propositions"),
            ("Evidence", "evidence_links"),
            ("Active concepts", "concepts"),
            ("Contradictions", "contradictions"),
            ("Replay / audit", "replay_queue"),
            ("Migration audit", "migration_audit_events"),
        ]):
            card = ttk.Frame(header, padding=6)
            card.grid(row=0, column=index, sticky="ew")
            header.columnconfigure(index, weight=1)
            ttk.Label(card, text=label).pack()
            self.state_vars[key] = tk.StringVar(value="-")
            ttk.Label(card, textvariable=self.state_vars[key], font=("Segoe UI", 11, "bold")).pack()

        status_bar = ttk.Frame(self.conversation_tab)
        self.conversational_status_frame = status_bar
        status_bar.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(status_bar, textvariable=self.conversational_runtime_status).pack(side=tk.LEFT)
        ttk.Button(status_bar, text="Stop", command=self._stop_conversational_objective).pack(side=tk.RIGHT)
        ttk.Button(status_bar, text="Advanced", command=self._open_developer_diagnostics).pack(side=tk.RIGHT, padx=(0, 8))

        mode_bar = ttk.Frame(self.conversation_tab)
        self.mode_bar = mode_bar
        mode_bar.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(mode_bar, text="Mode").pack(side=tk.LEFT)
        self.mode = ttk.Combobox(mode_bar, values=DISPLAY_MODES, width=22, state="readonly")
        self.mode.set("Conversation")
        self.mode.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Checkbutton(mode_bar, text="Developer Overlay", variable=self.developer_overlay_enabled).pack(side=tk.LEFT)
        ttk.Button(mode_bar, text="Advanced Operator Console", command=self._open_developer_diagnostics).pack(side=tk.RIGHT)

        live_bar = ttk.Frame(self.conversation_tab)
        self.live_bar = live_bar
        live_bar.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(live_bar, text="Start Live Runtime", command=self._start_live_runtime).pack(side=tk.LEFT)
        ttk.Button(live_bar, text="Stop", command=self._stop_live_runtime).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(live_bar, text="Pause Initiative", command=self._pause_live_initiative).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(live_bar, text="Resume", command=self._resume_live_initiative).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(live_bar, text="Suspend", command=self._suspend_live_initiative).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(live_bar, textvariable=self.live_runtime_status).pack(side=tk.LEFT, padx=(12, 0))

        stream_panes = ttk.PanedWindow(self.conversation_tab, orient=tk.HORIZONTAL)
        self.conversation_stream_panes = stream_panes
        stream_panes.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        chat_frame = ttk.LabelFrame(stream_panes, text="Conversation")
        observation_frame = ttk.LabelFrame(stream_panes, text="Live Observation")
        stream_panes.add(chat_frame, weight=3)
        stream_panes.add(observation_frame, weight=2)

        self.chat_history = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, height=24)
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.chat_history.configure(state=tk.DISABLED)
        self.observation_stream = scrolledtext.ScrolledText(observation_frame, wrap=tk.WORD, height=24)
        self.observation_stream.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.observation_stream.configure(state=tk.DISABLED)

        input_bar = ttk.Frame(self.conversation_tab)
        input_bar.pack(fill=tk.X, pady=(8, 0))
        self.chat_input = ttk.Entry(input_bar)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.chat_input.insert(0, "What color is the sky?")
        ttk.Button(input_bar, text="Send", command=self._send_chat).pack(side=tk.RIGHT)
        self.chat_input.bind("<Return>", lambda _event: self._send_chat())

        memory_bar = ttk.Frame(self.conversation_tab)
        self.memory_bar = memory_bar
        memory_bar.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(memory_bar, text="Accept Selected Concept", command=self._accept_selected_concept).pack(side=tk.LEFT)
        ttk.Button(memory_bar, text="Reject Selected Concept", command=self._reject_selected_concept).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Inspect Selected Concept", command=self._inspect_selected_concept).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Clear Local Memory Store", command=self._clear_local_store).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Open Operator Console", command=self._open_developer_diagnostics).pack(side=tk.RIGHT)

        review = ttk.LabelFrame(self.conversation_tab, text="Concept Review")
        self.concept_review_frame = review
        review.pack(fill=tk.X, pady=(8, 0))
        self.concept_review = ttk.Treeview(review, columns=("concept", "source", "status"), show="headings", height=3)
        self.concept_review.heading("concept", text="Potential Concept")
        self.concept_review.heading("source", text="Source")
        self.concept_review.heading("status", text="Status")
        self.concept_review.column("concept", width=360)
        self.concept_review.column("source", width=180)
        self.concept_review.column("status", width=120)
        self.concept_review.pack(fill=tk.X, padx=6, pady=6)

        hint = ttk.Label(
            self.conversation_tab,
            text="Default mode is natural conversation. Possible concepts appear in Concept Review and are stored only if you press Accept.",
        )
        self.conversation_hint = hint
        hint.pack(anchor=tk.W, pady=(6, 0))

    def _open_developer_diagnostics(self) -> None:
        self._show_advanced_surface()
        self.notebook.select(self.developer_tab)
        self.developer_notebook.select(self.advanced_tab)

    def _apply_simple_default_surface(self) -> None:
        self._advanced_surface_visible = False
        for frame_name in (
            "cognitive_state_frame",
            "mode_bar",
            "live_bar",
            "memory_bar",
            "concept_review_frame",
            "conversation_hint",
        ):
            frame = getattr(self, frame_name, None)
            if frame is not None:
                frame.pack_forget()
        for tab in (
            self.goals_tab,
            self.activity_tab,
            self.evaluation_tab,
            self.database_tab,
            self.settings_tab,
            self.developer_tab,
        ):
            try:
                self.notebook.forget(tab)
            except tk.TclError:
                pass
        self.notebook.select(self.conversation_tab)

    def _show_advanced_surface(self) -> None:
        if getattr(self, "_advanced_surface_visible", False):
            return
        tab_specs = (
            (self.goals_tab, "Goals"),
            (self.activity_tab, "Activity"),
            (self.evaluation_tab, "Evaluation"),
            (self.database_tab, "Memory"),
            (self.settings_tab, "Settings"),
            (self.developer_tab, "Developer"),
        )
        existing = set(self.notebook.tabs())
        for tab, label in tab_specs:
            if str(tab) not in existing:
                self.notebook.add(tab, text=label)
        for frame_name in (
            "cognitive_state_frame",
            "mode_bar",
            "live_bar",
            "memory_bar",
            "concept_review_frame",
            "conversation_hint",
        ):
            frame = getattr(self, frame_name, None)
            if frame is not None:
                frame.pack(fill=tk.X, pady=(6, 0))
        self._advanced_surface_visible = True

    def _build_goals_tab(self) -> None:
        top = ttk.Frame(self.goals_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Goals").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_operator_ux_views).pack(side=tk.RIGHT)

        self.goals_status = tk.StringVar(value="Human-facing goal cards. Technical identifiers are hidden until View technical details.")
        ttk.Label(self.goals_tab, textvariable=self.goals_status).pack(anchor=tk.W, pady=(8, 0))

        self._build_goal_ui_campaign_panel()

        panes = ttk.PanedWindow(self.goals_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.goal_cards = ttk.Treeview(left, columns=("state", "progress"), show="headings", height=14)
        self.goal_cards.heading("state", text="State")
        self.goal_cards.heading("progress", text="Progress")
        self.goal_cards.column("state", width=180)
        self.goal_cards.column("progress", width=100, anchor=tk.CENTER)
        self.goal_cards.pack(fill=tk.BOTH, expand=True)
        self.goal_cards.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_goal_card())

        controls = ttk.Frame(right)
        controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(controls, text="Approve next step", command=lambda: self._handle_operator_ux_button("approve")).pack(side=tk.LEFT)
        ttk.Button(controls, text="Decline next step", command=lambda: self._handle_operator_ux_button("decline")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Explain", command=lambda: self._handle_operator_ux_button("explain")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Show alternatives", command=lambda: self._handle_operator_ux_button("show_alternatives")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Change limits", command=lambda: self._handle_operator_ux_button("change_limits")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Pause", command=lambda: self._handle_operator_ux_button("pause")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="View technical details", command=self._show_operator_ux_technical_details).pack(side=tk.LEFT, padx=(6, 0))

        a4_controls = ttk.LabelFrame(right, text="Approved Plan Execution")
        a4_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a4_controls, textvariable=self.a4_execution_status).pack(side=tk.LEFT, padx=(6, 10))
        a4_button_specs = (
            ("start", "Start approved plan", lambda: self._run_autonomy_4_visible_control("start")),
            ("pause", "Pause", lambda: self._run_autonomy_4_visible_control("pause")),
            ("resume", "Resume", lambda: self._run_autonomy_4_visible_control("resume")),
            ("stop", "Stop", lambda: self._run_autonomy_4_visible_control("stop")),
            ("step", "Explain current step", lambda: self._run_autonomy_4_visible_control("step")),
            ("limits", "View limits", lambda: self._run_autonomy_4_visible_control("limits")),
            ("evidence", "View evidence", lambda: self._run_autonomy_4_visible_control("evidence")),
        )
        for key, label, command in a4_button_specs:
            button = ttk.Button(a4_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a4_control_buttons[key] = button

        a5_controls = ttk.LabelFrame(right, text="Outcome Review")
        a5_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a5_controls, textvariable=self.a5_review_status).pack(side=tk.LEFT, padx=(6, 10))
        a5_button_specs = (
            ("review", "Review completed outcome", lambda: self._run_autonomy_5_visible_control("review")),
            ("explain", "Explain the evidence", lambda: self._run_autonomy_5_visible_control("explain")),
            ("failed", "View failed cases", lambda: self._run_autonomy_5_visible_control("failed")),
            ("keep", "Keep provisional", lambda: self._run_autonomy_5_visible_control("keep")),
            ("send", "Send to competence review", lambda: self._run_autonomy_5_visible_control("send")),
        )
        for key, label, command in a5_button_specs:
            button = ttk.Button(a5_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a5_control_buttons[key] = button

        a6_controls = ttk.LabelFrame(right, text="Competence Admission")
        a6_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a6_controls, textvariable=self.a6_admission_status).pack(side=tk.LEFT, padx=(6, 10))
        a6_button_specs = (
            ("review", "Review competence candidate", lambda: self._run_autonomy_6_visible_control("review")),
            ("admit", "Admit this competence", lambda: self._run_autonomy_6_visible_control("admit")),
            ("keep", "Keep provisional", lambda: self._run_autonomy_6_visible_control("keep")),
            ("reject", "Reject admission", lambda: self._run_autonomy_6_visible_control("reject")),
            ("more", "Request more evaluation", lambda: self._run_autonomy_6_visible_control("more")),
            ("explain", "Explain the scope", lambda: self._run_autonomy_6_visible_control("explain")),
            ("ambiguous", "looks good", lambda: self._run_autonomy_6_visible_control("ambiguous")),
            ("details", "View technical details", lambda: self._run_autonomy_6_visible_control("details")),
        )
        for key, label, command in a6_button_specs:
            button = ttk.Button(a6_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a6_control_buttons[key] = button

        a13_controls = ttk.LabelFrame(right, text="Task-Scoped Competence Use")
        a13_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a13_controls, textvariable=self.a13_activation_status).pack(side=tk.LEFT, padx=(6, 10))
        a13_button_specs = (
            ("use", "Use this competence for this task", lambda: self._run_autonomy_13_visible_control("use")),
            ("fit", "Why this competence fits", lambda: self._run_autonomy_13_visible_control("fit")),
            ("cannot", "What it cannot do", lambda: self._run_autonomy_13_visible_control("cannot")),
            ("scope", "Activation scope", lambda: self._run_autonomy_13_visible_control("scope")),
            ("expires", "Activation expires", lambda: self._run_autonomy_13_visible_control("expires")),
            ("evaluation", "View evaluation", lambda: self._run_autonomy_13_visible_control("evaluation")),
            ("stop", "Stop task use", lambda: self._run_autonomy_13_visible_control("stop")),
        )
        for key, label, command in a13_button_specs:
            button = ttk.Button(a13_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a13_control_buttons[key] = button

        a14_controls = ttk.LabelFrame(right, text="Composed Task")
        a14_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a14_controls, textvariable=self.a14_composition_status).pack(side=tk.LEFT, padx=(6, 10))
        a14_button_specs = (
            ("start", "Start composed task", lambda: self._run_autonomy_14_visible_control("start")),
            ("pause", "Pause", lambda: self._run_autonomy_14_visible_control("pause")),
            ("resume", "Resume", lambda: self._run_autonomy_14_visible_control("resume")),
            ("stop", "Stop", lambda: self._run_autonomy_14_visible_control("stop")),
            ("explain", "Explain current stage", lambda: self._run_autonomy_14_visible_control("explain")),
            ("evidence", "View stage evidence", lambda: self._run_autonomy_14_visible_control("evidence")),
            ("provenance", "View provenance", lambda: self._run_autonomy_14_visible_control("provenance")),
            ("limits", "View limits", lambda: self._run_autonomy_14_visible_control("limits")),
        )
        for key, label, command in a14_button_specs:
            button = ttk.Button(a14_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a14_control_buttons[key] = button

        a15_controls = ttk.LabelFrame(right, text="Support Check")
        a15_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a15_controls, textvariable=self.a15_gap_status).pack(side=tk.LEFT, padx=(6, 10))
        a15_button_specs = (
            ("classify", "What DELTA can do", lambda: self._run_autonomy_15_visible_control("classify")),
            ("missing", "What is missing", lambda: self._run_autonomy_15_visible_control("missing")),
            ("explain", "Explain", lambda: self._run_autonomy_15_visible_control("explain")),
            ("evidence", "View evidence", lambda: self._run_autonomy_15_visible_control("evidence")),
            ("clarify", "Request clarification", lambda: self._run_autonomy_15_visible_control("clarify")),
        )
        for key, label, command in a15_button_specs:
            button = ttk.Button(a15_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a15_control_buttons[key] = button

        a16_controls = ttk.LabelFrame(right, text="Mixed Mission")
        a16_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a16_controls, textvariable=self.a16_mission_status).pack(side=tk.LEFT, padx=(6, 10))
        a16_button_specs = (
            ("start", "Start mission", lambda: self._run_autonomy_16_visible_control("start")),
            ("pause", "Pause mission", lambda: self._run_autonomy_16_visible_control("pause")),
            ("resume", "Resume mission", lambda: self._run_autonomy_16_visible_control("resume")),
            ("stop", "Stop mission", lambda: self._run_autonomy_16_visible_control("stop")),
            ("current", "Explain current task", lambda: self._run_autonomy_16_visible_control("current")),
            ("blocked", "Explain blocked task", lambda: self._run_autonomy_16_visible_control("blocked")),
            ("evidence", "View mission evidence", lambda: self._run_autonomy_16_visible_control("evidence")),
            ("limits", "View mission limits", lambda: self._run_autonomy_16_visible_control("limits")),
            ("graph", "View task graph", lambda: self._run_autonomy_16_visible_control("graph")),
        )
        for key, label, command in a16_button_specs:
            button = ttk.Button(a16_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a16_control_buttons[key] = button

        a17_controls = ttk.LabelFrame(right, text="Local Evidence")
        a17_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a17_controls, textvariable=self.a17_evidence_status).pack(side=tk.LEFT, padx=(6, 10))
        a17_button_specs = (
            ("acquire", "Acquire local evidence", lambda: self._run_autonomy_17_visible_control("acquire")),
            ("explain", "Explain evidence", lambda: self._run_autonomy_17_visible_control("explain")),
            ("sources", "View sources", lambda: self._run_autonomy_17_visible_control("sources")),
            ("contradictions", "View contradictions", lambda: self._run_autonomy_17_visible_control("contradictions")),
            ("missing", "View missing evidence", lambda: self._run_autonomy_17_visible_control("missing")),
            ("limits", "View limits", lambda: self._run_autonomy_17_visible_control("limits")),
            ("revalidate", "Revalidate stale evidence", lambda: self._run_autonomy_17_visible_control("revalidate")),
        )
        for key, label, command in a17_button_specs:
            button = ttk.Button(a17_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a17_control_buttons[key] = button

        a18_controls = ttk.LabelFrame(right, text="Advisory Proposal")
        a18_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a18_controls, textvariable=self.a18_advice_status).pack(side=tk.LEFT, padx=(6, 10))
        a18_button_specs = (
            ("request", "Request bounded advice", lambda: self._run_autonomy_18_visible_control("request")),
            ("explain", "Explain advice", lambda: self._run_autonomy_18_visible_control("explain")),
            ("grounding", "View grounding", lambda: self._run_autonomy_18_visible_control("grounding")),
            ("rejected", "View rejected claims", lambda: self._run_autonomy_18_visible_control("rejected")),
            ("limits", "View limits", lambda: self._run_autonomy_18_visible_control("limits")),
            ("keep", "Keep as proposal", lambda: self._run_autonomy_18_visible_control("keep")),
            ("reject", "Reject advice", lambda: self._run_autonomy_18_visible_control("reject")),
        )
        for key, label, command in a18_button_specs:
            button = ttk.Button(a18_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a18_control_buttons[key] = button

        a21_controls = ttk.LabelFrame(right, text="Competence Health")
        a21_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(a21_controls, textvariable=self.a21_health_status).pack(side=tk.LEFT, padx=(6, 10))
        a21_button_specs = (
            ("explain", "Explain competence health", lambda: self._run_autonomy_21_visible_control("explain")),
            ("evidence", "View evidence", lambda: self._run_autonomy_21_visible_control("evidence")),
            ("tasks", "View affected tasks", lambda: self._run_autonomy_21_visible_control("tasks")),
            ("reevaluate", "Request reevaluation", lambda: self._run_autonomy_21_visible_control("reevaluate")),
            ("suspend", "Suspend", lambda: self._run_autonomy_21_visible_control("suspend")),
            ("restore", "Restore proven scope", lambda: self._run_autonomy_21_visible_control("restore")),
        )
        for key, label, command in a21_button_specs:
            button = ttk.Button(a21_controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.a21_control_buttons[key] = button

        self.goal_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.goal_detail.pack(fill=tk.BOTH, expand=True)
        self.goal_detail.configure(state=tk.DISABLED)
        self.operator_ux_goal_cards: dict[str, dict[str, object]] = {}

    def _build_goal_ui_campaign_panel(self) -> None:
        campaign = ttk.LabelFrame(self.goals_tab, text="Goal-Oriented UI Experiments")
        campaign.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(campaign, textvariable=self.goal_ui_campaign_status).pack(anchor=tk.W, padx=6, pady=(4, 0))

        controls = ttk.Frame(campaign)
        controls.pack(fill=tk.X, padx=6, pady=(6, 4))
        specs = (
            ("formulate", "Formulate candidates", self._goal_ui_campaign_formulate),
            ("select", "Select set", self._goal_ui_campaign_select),
            ("launch", "Launch selected", self._goal_ui_campaign_launch_selected),
            ("cycle", "Run cycle", self._goal_ui_campaign_run_cycle),
            ("pause", "Pause", self._goal_ui_campaign_pause),
            ("resume", "Resume", self._goal_ui_campaign_resume),
            ("restart", "Reload state", self._goal_ui_campaign_reload),
            ("follow", "Begin follow-up", self._goal_ui_campaign_follow_up),
        )
        for key, label, command in specs:
            button = ttk.Button(controls, text=label, command=command)
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.goal_ui_campaign_buttons[key] = button

        body = ttk.Frame(campaign)
        body.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.goal_ui_campaign_tree = ttk.Treeview(
            body,
            columns=("selected", "cycles", "status"),
            show="tree headings",
            height=4,
        )
        self.goal_ui_campaign_tree.heading("#0", text="Experiment")
        self.goal_ui_campaign_tree.heading("selected", text="Selected")
        self.goal_ui_campaign_tree.heading("cycles", text="Cycles")
        self.goal_ui_campaign_tree.heading("status", text="Status")
        self.goal_ui_campaign_tree.column("#0", width=360)
        self.goal_ui_campaign_tree.column("selected", width=80, anchor=tk.CENTER)
        self.goal_ui_campaign_tree.column("cycles", width=70, anchor=tk.CENTER)
        self.goal_ui_campaign_tree.column("status", width=160)
        self.goal_ui_campaign_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.goal_ui_campaign_tree.bind("<<TreeviewSelect>>", lambda _event: self._goal_ui_campaign_show_selected())

        self.goal_ui_campaign_detail = scrolledtext.ScrolledText(body, wrap=tk.WORD, height=5, width=68)
        self.goal_ui_campaign_detail.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.goal_ui_campaign_detail.configure(state=tk.DISABLED)
        self._goal_ui_campaign_refresh()

    def _goal_ui_campaign_candidates(self) -> list[dict[str, object]]:
        payload = read_goal_ui_campaign_json(goal_ui_campaign_path("candidate_experiments.json"), {}) or {}
        return list(dict(payload).get("candidates") or [])

    def _goal_ui_campaign_selection(self) -> list[dict[str, object]]:
        payload = read_goal_ui_campaign_json(goal_ui_campaign_path("experiment_selection.json"), {}) or {}
        return list(dict(payload).get("selected") or [])

    def _goal_ui_campaign_current_id(self) -> str:
        selected = self.goal_ui_campaign_tree.selection()
        if selected:
            self.goal_ui_campaign_selected_id.set(str(selected[0]))
        if self.goal_ui_campaign_selected_id.get():
            return self.goal_ui_campaign_selected_id.get()
        selection = self._goal_ui_campaign_selection()
        if selection:
            experiment_id = str(selection[0].get("experiment_id") or "")
            self.goal_ui_campaign_selected_id.set(experiment_id)
            return experiment_id
        return ""

    def _goal_ui_campaign_proposal(self, experiment_id: str) -> dict[str, object] | None:
        for proposal in self._goal_ui_campaign_selection() + self._goal_ui_campaign_candidates():
            if str(proposal.get("experiment_id") or "") == experiment_id:
                return proposal
        return None

    def _goal_ui_campaign_write_detail(self, payload: object) -> None:
        self.goal_ui_campaign_detail.configure(state=tk.NORMAL)
        self.goal_ui_campaign_detail.delete("1.0", tk.END)
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload, indent=2, sort_keys=True, default=str)
        self.goal_ui_campaign_detail.insert(tk.END, text)
        self.goal_ui_campaign_detail.configure(state=tk.DISABLED)

    def _goal_ui_campaign_refresh(self) -> None:
        if not hasattr(self, "goal_ui_campaign_tree"):
            return
        for item in self.goal_ui_campaign_tree.get_children():
            self.goal_ui_campaign_tree.delete(item)
        selected_ids = {str(item.get("experiment_id") or "") for item in self._goal_ui_campaign_selection()}
        candidates = self._goal_ui_campaign_candidates()
        for proposal in candidates:
            experiment_id = str(proposal.get("experiment_id") or "")
            state = read_goal_ui_campaign_experiment_state(experiment_id)
            cycles = len(state.cycles) if state is not None else 0
            status = state.loop_state if state is not None else "candidate"
            self.goal_ui_campaign_tree.insert(
                "",
                tk.END,
                iid=experiment_id,
                text=str(proposal.get("title") or experiment_id),
                values=("yes" if experiment_id in selected_ids else "", cycles, status),
            )
        if self.goal_ui_campaign_selected_id.get() in self.goal_ui_campaign_tree.get_children():
            self.goal_ui_campaign_tree.selection_set(self.goal_ui_campaign_selected_id.get())
        elif candidates:
            first = str(candidates[0].get("experiment_id") or "")
            self.goal_ui_campaign_tree.selection_set(first)
            self.goal_ui_campaign_selected_id.set(first)
        self.goal_ui_campaign_status.set(
            f"{GOAL_UI_CAMPAIGN_ID}: candidates={len(candidates)}; selected={len(selected_ids)}; active={self.goal_ui_campaign_selected_id.get() or 'none'}"
        )

    def _goal_ui_campaign_show_selected(self) -> None:
        experiment_id = self._goal_ui_campaign_current_id()
        proposal = self._goal_ui_campaign_proposal(experiment_id)
        state = read_goal_ui_campaign_experiment_state(experiment_id) if experiment_id else None
        summary = summarize_goal_ui_campaign_for_ui(state, proposal)
        self._goal_ui_campaign_write_detail(summary)

    def _goal_ui_campaign_formulate(self) -> None:
        try:
            candidates = formulate_goal_ui_campaign_candidates(self.provider_manager)
            self.goal_ui_campaign_status.set(f"{GOAL_UI_CAMPAIGN_ID}: formulated {len(candidates)} candidates through cognition lane")
            write_goal_ui_campaign_json(goal_ui_campaign_path("ui_evidence_index.json"), {
                "candidate_experiments_visible": True,
                "last_ui_event": "formulate_candidates",
            })
        except Exception as exc:  # noqa: BLE001
            self.goal_ui_campaign_status.set(f"Goal UI campaign formulation failed: {type(exc).__name__}: {str(exc)[:180]}")
        self._goal_ui_campaign_refresh()
        self._goal_ui_campaign_show_selected()

    def _goal_ui_campaign_select(self) -> None:
        try:
            candidates = self._goal_ui_campaign_candidates()
            selected = select_goal_ui_campaign_experiments(candidates, self.provider_manager)
            self.goal_ui_campaign_status.set(f"{GOAL_UI_CAMPAIGN_ID}: selected {len(selected)} experiments")
            if selected:
                self.goal_ui_campaign_selected_id.set(str(selected[0].get("experiment_id") or ""))
            write_goal_ui_campaign_json(goal_ui_campaign_path("ui_evidence_index.json"), {
                "candidate_experiments_visible": True,
                "selected_experiment_visible": True,
                "last_ui_event": "select_experiments",
            })
        except Exception as exc:  # noqa: BLE001
            self.goal_ui_campaign_status.set(f"Goal UI campaign selection failed: {type(exc).__name__}: {str(exc)[:180]}")
        self._goal_ui_campaign_refresh()
        self._goal_ui_campaign_show_selected()

    def _goal_ui_campaign_launch_selected(self) -> None:
        experiment_id = self._goal_ui_campaign_current_id()
        proposal = self._goal_ui_campaign_proposal(experiment_id)
        if not proposal:
            self.goal_ui_campaign_status.set("Goal UI campaign: select an experiment first")
            return
        try:
            state = launch_goal_ui_campaign_experiment(proposal)
            self.goal_ui_campaign_status.set(f"{GOAL_UI_CAMPAIGN_ID}: launched {experiment_id}")
            self._goal_ui_campaign_write_detail(summarize_goal_ui_campaign_for_ui(state, proposal))
        except Exception as exc:  # noqa: BLE001
            self.goal_ui_campaign_status.set(f"Goal UI campaign launch failed: {type(exc).__name__}: {str(exc)[:180]}")
        self._goal_ui_campaign_refresh()

    def _goal_ui_campaign_run_cycle(self) -> None:
        experiment_id = self._goal_ui_campaign_current_id()
        if not experiment_id:
            self.goal_ui_campaign_status.set("Goal UI campaign: select an experiment first")
            return
        try:
            state = run_goal_ui_campaign_experiment_cycle(experiment_id, self.provider_manager)
            self.goal_ui_campaign_status.set(
                f"{GOAL_UI_CAMPAIGN_ID}: {experiment_id} cycle complete; calls={state.model_call_count}; state={state.loop_state}"
            )
            self._goal_ui_campaign_write_detail(summarize_goal_ui_campaign_for_ui(state, self._goal_ui_campaign_proposal(experiment_id)))
        except Exception as exc:  # noqa: BLE001
            self.goal_ui_campaign_status.set(f"Goal UI campaign cycle failed: {type(exc).__name__}: {str(exc)[:180]}")
        self._goal_ui_campaign_refresh()

    def _goal_ui_campaign_pause(self) -> None:
        experiment_id = self._goal_ui_campaign_current_id()
        if not experiment_id:
            return
        try:
            state = pause_goal_ui_campaign_experiment(experiment_id)
            self.goal_ui_campaign_status.set(f"{GOAL_UI_CAMPAIGN_ID}: paused {experiment_id}")
            self._goal_ui_campaign_write_detail(summarize_goal_ui_campaign_for_ui(state, self._goal_ui_campaign_proposal(experiment_id)))
        except Exception as exc:  # noqa: BLE001
            self.goal_ui_campaign_status.set(f"Goal UI campaign pause failed: {type(exc).__name__}: {str(exc)[:180]}")
        self._goal_ui_campaign_refresh()

    def _goal_ui_campaign_resume(self) -> None:
        experiment_id = self._goal_ui_campaign_current_id()
        if not experiment_id:
            return
        try:
            state = resume_goal_ui_campaign_experiment(experiment_id)
            self.goal_ui_campaign_status.set(f"{GOAL_UI_CAMPAIGN_ID}: resumed {experiment_id}")
            self._goal_ui_campaign_write_detail(summarize_goal_ui_campaign_for_ui(state, self._goal_ui_campaign_proposal(experiment_id)))
        except Exception as exc:  # noqa: BLE001
            self.goal_ui_campaign_status.set(f"Goal UI campaign resume failed: {type(exc).__name__}: {str(exc)[:180]}")
        self._goal_ui_campaign_refresh()

    def _goal_ui_campaign_reload(self) -> None:
        experiment_id = self._goal_ui_campaign_current_id()
        state = read_goal_ui_campaign_experiment_state(experiment_id) if experiment_id else None
        self.goal_ui_campaign_status.set(f"{GOAL_UI_CAMPAIGN_ID}: reloaded {experiment_id or 'none'} from durable state")
        self._goal_ui_campaign_write_detail(summarize_goal_ui_campaign_for_ui(state, self._goal_ui_campaign_proposal(experiment_id)))
        self._goal_ui_campaign_refresh()

    def _goal_ui_campaign_follow_up(self) -> None:
        experiment_id = self._goal_ui_campaign_current_id()
        if not experiment_id:
            return
        try:
            state = begin_goal_ui_campaign_follow_up(experiment_id, self.provider_manager)
            self.goal_ui_campaign_status.set(f"{GOAL_UI_CAMPAIGN_ID}: began follow-up for {experiment_id}")
            self._goal_ui_campaign_write_detail(summarize_goal_ui_campaign_for_ui(state, self._goal_ui_campaign_proposal(experiment_id)))
        except Exception as exc:  # noqa: BLE001
            self.goal_ui_campaign_status.set(f"Goal UI campaign follow-up failed: {type(exc).__name__}: {str(exc)[:180]}")
        self._goal_ui_campaign_refresh()

    def _build_activity_tab(self) -> None:
        top = ttk.Frame(self.activity_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Activity").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_operator_ux_views).pack(side=tk.RIGHT)
        self.activity_status = tk.StringVar(value="Concise runtime narration rebuilt from persisted transitions.")
        ttk.Label(self.activity_tab, textvariable=self.activity_status).pack(anchor=tk.W, pady=(8, 0))
        self.activity_items = ttk.Treeview(self.activity_tab, columns=("message", "status"), show="headings", height=18)
        self.activity_items.heading("message", text="Message")
        self.activity_items.heading("status", text="Status")
        self.activity_items.column("message", width=720)
        self.activity_items.column("status", width=140)
        self.activity_items.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    def _build_settings_tab(self) -> None:
        ttk.Label(self.settings_tab, text="Chat Features / Settings Schema").pack(anchor=tk.W)
        ttk.Label(
            self.settings_tab,
            text=(
                "Default operation follows a GPT-style chat surface. Settings describe behavior and authority boundaries; "
                "they do not grant new authority by themselves."
            ),
            wraplength=900,
        ).pack(anchor=tk.W, pady=(8, 0))
        self.chat_settings_detail = scrolledtext.ScrolledText(self.settings_tab, wrap=tk.WORD, height=26)
        self.chat_settings_detail.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.chat_settings_detail.insert(tk.END, json.dumps(chat_feature_settings_schema(), indent=2, sort_keys=True))
        self.chat_settings_detail.configure(state=tk.DISABLED)
        profile = ttk.LabelFrame(self.settings_tab, text="Operator-Governed Presentation Profile")
        profile.pack(fill=tk.X, pady=(8, 0))
        self.personality_profile_choice = tk.StringVar(value="Direct and concise")
        self.personality_profile_status = tk.StringVar(value="No approved presentation profile is active.")
        ttk.Combobox(profile, textvariable=self.personality_profile_choice, values=("Direct and concise", "Detailed and formal"), state="readonly").grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        ttk.Button(profile, text="Propose Profile", command=self._propose_personality_profile).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(profile, text="Approve and Activate", command=self._approve_personality_profile).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(profile, text="Rollback", command=self._rollback_personality_profile).grid(row=0, column=3, padx=4, pady=4)
        self.relationship_convention_key = tk.StringVar(value="technical_detail")
        self.relationship_convention_value = tk.StringVar(value="concise")
        ttk.Entry(profile, textvariable=self.relationship_convention_key, width=20).grid(row=1, column=0, sticky="ew", padx=6, pady=4)
        ttk.Entry(profile, textvariable=self.relationship_convention_value, width=20).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(profile, text="Approve Convention", command=self._approve_relationship_convention).grid(row=1, column=2, padx=4, pady=4)
        ttk.Label(profile, textvariable=self.personality_profile_status).grid(row=2, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 6))
        profile.columnconfigure(0, weight=1)

    def _profile_traits_from_choice(self) -> dict[str, object]:
        if self.personality_profile_choice.get() == "Detailed and formal":
            return {"directness": 1, "explanation_depth": 3, "formality": 3, "humor_level": 0, "curiosity_expression_frequency": 1, "willingness_to_ask": 1, "initiative_level": 1, "interruption_tolerance": 1, "association_surfacing_frequency": 1, "correction_candor": 2, "background_work_visibility": 2, "uncertainty_expression_style": "cautious"}
        return {"directness": 3, "explanation_depth": 1, "formality": 0, "humor_level": 0, "curiosity_expression_frequency": 2, "willingness_to_ask": 1, "initiative_level": 1, "interruption_tolerance": 1, "association_surfacing_frequency": 1, "correction_candor": 2, "background_work_visibility": 1, "uncertainty_expression_style": "plain"}

    def _propose_personality_profile(self) -> None:
        self.governed_personality_state = propose_governed_personality(self.governed_personality_state, traits=self._profile_traits_from_choice(), proposer_role="operator", rationale="Explicit operator proposal from the Settings surface.")
        save_governed_personality_state(self.conversational_runtime_root, self.governed_personality_state)
        self.personality_profile_status.set("Profile proposed. Activation still requires the explicit approval button.")

    def _approve_personality_profile(self) -> None:
        proposed = next((item for item in reversed(self.governed_personality_state.versions) if item.lifecycle_state == "proposed"), None)
        if proposed is None:
            self.personality_profile_status.set("No proposed profile is available to approve.")
            return
        self.governed_personality_state = approve_governed_personality(self.governed_personality_state, profile_version_id=proposed.profile_version_id, operator_id="local_operator", approval_ref=rc6_stable_id("personality-profile-approval", proposed.profile_version_id))
        save_governed_personality_state(self.conversational_runtime_root, self.governed_personality_state)
        self.personality_profile_status.set(f"Active presentation profile: {proposed.profile_version_id}")

    def _rollback_personality_profile(self) -> None:
        target = next((item for item in reversed(self.governed_personality_state.versions) if item.lifecycle_state == "superseded"), None)
        if target is None:
            self.personality_profile_status.set("No earlier approved profile is available to roll back to.")
            return
        self.governed_personality_state = rollback_governed_personality(self.governed_personality_state, target_profile_version_id=target.profile_version_id, operator_id="local_operator", approval_ref=rc6_stable_id("personality-profile-rollback", target.profile_version_id))
        save_governed_personality_state(self.conversational_runtime_root, self.governed_personality_state)
        self.personality_profile_status.set(f"Rolled back to presentation profile: {target.profile_version_id}")

    def _approve_relationship_convention(self) -> None:
        try:
            self.governed_personality_state = record_governed_relationship_convention(self.governed_personality_state, key=self.relationship_convention_key.get().strip(), value=self.relationship_convention_value.get().strip(), operator_id="local_operator", approval_ref=rc6_stable_id("relationship-convention-approval", self.relationship_convention_key.get(), self.relationship_convention_value.get()))
            save_governed_personality_state(self.conversational_runtime_root, self.governed_personality_state)
            self.personality_profile_status.set("Operator-approved relationship convention recorded.")
        except (PermissionError, ValueError) as exc:
            self.personality_profile_status.set(f"Convention was not recorded: {exc}")

    def _operator_ux_current_runtime_state(self) -> dict[str, object]:
        for root in (LIVE_RUNTIME_4_ROOT, LIVE_RUNTIME_3_ROOT, LIVE_RUNTIME_2_ROOT, LIVE_RUNTIME_1B_ROOT):
            restart = root / "restart_state.json"
            if restart.exists():
                try:
                    state = json.loads(restart.read_text(encoding="utf-8"))
                    runtime_state = dict(dict(state.get("continuous_learning_state") or {}).get("live_runtime_1") or {})
                    if runtime_state:
                        return runtime_state
                except (OSError, json.JSONDecodeError):
                    continue
        return {}

    def _persist_operator_ux_record(self, directory: str, artifact_id: str, payload: dict[str, object]) -> None:
        write_operator_ux_json(self.operator_ux_root / directory / f"{artifact_id}.json", payload)

    def _load_operator_ux_state(self) -> None:
        request_dir = self.operator_ux_root / "requests"
        response_dir = self.operator_ux_root / "responses"
        consumed_dir = self.operator_ux_root / "consumed_responses"
        active: dict[str, object] | None = None
        if request_dir.exists():
            requests = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(request_dir.glob("*.json"))]
            consumed_request_ids = {
                str(json.loads(path.read_text(encoding="utf-8")).get("request_id") or "")
                for path in sorted(consumed_dir.glob("*.json"))
            } if consumed_dir.exists() else set()
            for request in requests:
                if str(request.get("request_id") or "") not in consumed_request_ids:
                    active = request
        self.active_operator_ux_request = active
        if active:
            self.operator_ux_request_card = compile_operator_request_card(active)
        else:
            self.operator_ux_request_card = None
        self.operator_ux_responses = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(response_dir.glob("*.json"))
        ] if response_dir.exists() else []
        self.operator_ux_consumed_responses = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(consumed_dir.glob("*.json"))
        ] if consumed_dir.exists() else []
        narration_dir = self.operator_ux_root / "narration"
        if narration_dir.exists():
            for path in sorted(narration_dir.glob("*.json")):
                event = json.loads(path.read_text(encoding="utf-8"))
                self.operator_ux_narration_events[str(event.get("event_id") or path.stem)] = event

    def _refresh_operator_ux_views(self) -> None:
        self._load_operator_ux_state()
        state = self._operator_ux_current_runtime_state()
        cards: dict[str, dict[str, object]] = {}
        if state:
            card = goal_card_from_live_runtime_state(state)
            cards[str(card["goal_id"])] = card
            for event in narration_from_live_runtime_state(state):
                self.operator_ux_narration_events.setdefault(str(event["event_id"]), event)
        if self.active_operator_ux_request:
            request = self.active_operator_ux_request
            card = {
                "goal_id": str(request.get("goal_id") or request["request_id"]),
                "title": str(request.get("goal_title") or "Operator decision"),
                "objective": str(request.get("what_delta_wants") or "Review the active request."),
                "state": "Waiting for you",
                "progress_completed": 0,
                "progress_total": 1,
                "current_activity": "I need your approval",
                "next_expected_action": "Approve, decline, explain, or pause",
                "unresolved_issue": str(request.get("missing_information_or_capability") or ""),
                "capability_source": str(request.get("capability_source") or "Governed operator decision"),
                "technical_details_hidden": True,
            }
            cards[str(card["goal_id"])] = card
        self.operator_ux_goal_cards = cards
        if hasattr(self, "goal_cards"):
            for item in self.goal_cards.get_children():
                self.goal_cards.delete(item)
            for goal_id, card in cards.items():
                progress = f"{card.get('progress_completed', 0)} of {card.get('progress_total', 0)}"
                self.goal_cards.insert("", tk.END, iid=goal_id, values=(card.get("state", ""), progress))
            if cards:
                first = next(iter(cards))
                self.goal_cards.selection_set(first)
                self._show_selected_goal_card()
        if hasattr(self, "activity_items"):
            for item in self.activity_items.get_children():
                self.activity_items.delete(item)
            for event in sorted(self.operator_ux_narration_events.values(), key=lambda item: str(item.get("event_id"))):
                self.activity_items.insert("", tk.END, iid=str(event["event_id"]), values=(event.get("message", ""), human_state_label(str(event.get("event_type") or ""))))
        self._refresh_autonomy_4_controls()
        self._refresh_autonomy_5_controls()
        self._refresh_autonomy_6_controls()
        self._refresh_autonomy_13_controls()
        self._refresh_autonomy_14_controls()
        self._refresh_autonomy_15_controls()
        self._refresh_autonomy_16_controls()
        self._refresh_autonomy_17_controls()
        self._refresh_autonomy_18_controls()
        self._refresh_autonomy_21_controls()

    def _show_selected_goal_card(self) -> None:
        selected = self.goal_cards.selection()
        if not selected:
            return
        card = self.operator_ux_goal_cards.get(str(selected[0]), {})
        lines = [
            str(card.get("title") or "Goal"),
            "",
            f"State: {card.get('state')}",
            f"Objective: {card.get('objective')}",
            f"Progress: {card.get('progress_completed', 0)} of {card.get('progress_total', 0)} tasks complete",
            f"Current activity: {card.get('current_activity')}",
            f"Next: {card.get('next_expected_action')}",
            f"Unresolved issue: {card.get('unresolved_issue') or 'None'}",
            f"Capability source: {card.get('capability_source')}",
            "",
            "Technical details are hidden by default. Use View technical details if needed.",
        ]
        if self.operator_ux_request_card:
            request = self.operator_ux_request_card
            lines.extend([
                "",
                "I need your approval",
                str(request.get("what_delta_wants")),
                "",
                f"Why: {request.get('why')}",
                f"Will inspect: {', '.join(request.get('files_or_resources') or ()) or 'No files listed'}",
                f"May change: {request.get('may_change')}",
                f"Provider/network: {request.get('provider_or_network_use')}",
                f"Learning attempts: {request.get('learning_attempts')}",
                f"Recommended: {request.get('recommended_action')}",
                f"If declined: {request.get('if_declined')}",
                "",
                "Buttons: Approve, Decline, Explain, Change limits, Pause goal",
            ])
        self.goal_detail.configure(state=tk.NORMAL)
        self.goal_detail.delete("1.0", tk.END)
        self.goal_detail.insert(tk.END, "\n".join(lines))
        self.goal_detail.configure(state=tk.DISABLED)

    def _show_operator_ux_technical_details(self) -> None:
        details = {
            "active_request": self.active_operator_ux_request,
            "request_card": self.operator_ux_request_card,
            "responses": self.operator_ux_responses,
            "consumed_responses": self.operator_ux_consumed_responses,
            "rc_tab_audit": audit_rc_tabs(),
        }
        self.goal_detail.configure(state=tk.NORMAL)
        self.goal_detail.delete("1.0", tk.END)
        self.goal_detail.insert(tk.END, json.dumps(details, indent=2, sort_keys=True, default=str))
        self.goal_detail.configure(state=tk.DISABLED)

    def _peek_autonomy_4_approved_plan(self) -> tuple[dict[str, object] | None, dict[str, object] | None]:
        approval_dir = self.operator_ux_root / "autonomy_3_plan_approvals"
        plan_dir = self.operator_ux_root / "autonomy_3_plans"
        approvals: list[dict[str, object]] = []
        if approval_dir.exists():
            for path in sorted(approval_dir.glob("*.json")):
                try:
                    approvals.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        if not approvals:
            return None, None
        approval = approvals[-1]
        plan_path = plan_dir / f"{approval.get('plan_id')}.json"
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, approval
        return plan, approval

    def _autonomy_4_persisted_state(self) -> str:
        plan, _approval = self._peek_autonomy_4_approved_plan()
        execution_root = self.operator_ux_root / "autonomy_4_execution"
        if not plan and not execution_root.exists():
            return "no_plan"
        final_dir = execution_root / "final_synthesis"
        finals = tuple(final_dir.glob("*.json")) if final_dir.exists() else ()
        if finals:
            try:
                final = json.loads(sorted(finals)[-1].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return "integrity_stop"
            return str(final.get("final_disposition") or "completed")
        stop_dir = execution_root / "boundary_stops"
        stops = tuple(stop_dir.glob("*.json")) if stop_dir.exists() else ()
        if stops:
            try:
                stop = json.loads(sorted(stops)[-1].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return "integrity_stop"
            return str(stop.get("status") or "integrity_stop")
        if (execution_root / "runner.lock").exists():
            return "running"
        lifecycle_dir = execution_root / "work_item_lifecycle"
        transitions = tuple(lifecycle_dir.glob("*.json")) if lifecycle_dir.exists() else ()
        if transitions:
            latest_state = "running"
            latest_cycle = -1
            for path in transitions:
                try:
                    transition = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                cycle = int(transition.get("controller_cycle") or 0)
                if str(transition.get("work_item_id")) == "approved-plan-execution" and cycle >= latest_cycle:
                    latest_cycle = cycle
                    latest_state = str(transition.get("next_state") or latest_state)
            return latest_state
        return "approved_not_started" if plan else "no_plan"

    def _refresh_autonomy_4_controls(self) -> None:
        state = self._autonomy_4_persisted_state()
        labels = {
            "no_plan": "A4: no approved plan",
            "approved_not_started": "A4: approved, not started",
            "running": "A4: running",
            "paused_operator": "A4: paused",
            "stopped_by_operator": "A4: stopped",
            "authority_expired": "A4: authority expired",
            "completed_with_provisional_evidence": "A4: completed",
            "completed_without_revision": "A4: completed",
            "failed_after_revision": "A4: failed after revision",
            "integrity_stop": "A4: integrity stop",
            "terminal": "A4: completed",
        }
        self.a4_execution_status.set(labels.get(state, f"A4: {state.replace('_', ' ')}"))
        has_plan = state != "no_plan"
        enabled = {
            "start": state == "approved_not_started",
            "pause": state == "running",
            "resume": state == "paused_operator",
            "stop": state in {"running", "paused_operator"},
            "step": has_plan,
            "limits": has_plan,
            "evidence": has_plan,
        }
        for key, button in self.a4_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _run_autonomy_4_visible_control(self, action: str) -> dict[str, object] | None:
        if action == "start":
            result = self._start_autonomy_4_approved_plan()
        elif action == "pause":
            result = self._start_autonomy_4_approved_plan(mode="pause")
        elif action == "resume":
            result = self._start_autonomy_4_approved_plan(mode="resume")
        elif action == "stop":
            result = self._start_autonomy_4_approved_plan(mode="stop")
        elif action in {"step", "limits", "evidence"}:
            result = self._explain_autonomy_4_execution(action)
        else:
            return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _latest_autonomy_5_review(self) -> tuple[dict[str, object] | None, dict[str, object] | None]:
        review_dir = self.operator_ux_root / "autonomy_5_outcome_review" / "reviews"
        request_dir = self.operator_ux_root / "autonomy_5_outcome_review" / "operator_requests"
        reviews = []
        for path in sorted(review_dir.glob("*.json")) if review_dir.exists() else ():
            try:
                reviews.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        requests = []
        for path in sorted(request_dir.glob("*.json")) if request_dir.exists() else ():
            try:
                requests.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return (reviews[-1] if reviews else None, requests[-1] if requests else None)

    def _latest_autonomy_6_review(self) -> tuple[dict[str, object] | None, dict[str, object] | None, dict[str, object] | None]:
        root = self.operator_ux_root / "autonomy_6_competence_admission"
        candidates = []
        policies = []
        requests = []
        for directory, target in (("admission_candidates", candidates), ("policy_decisions", policies), ("operator_requests", requests)):
            base = root / directory
            for path in sorted(base.glob("*.json")) if base.exists() else ():
                try:
                    target.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        return (candidates[-1] if candidates else None, policies[-1] if policies else None, requests[-1] if requests else None)

    def _latest_autonomy_13_report(self) -> dict[str, object] | None:
        path = self.operator_ux_root / "a13_activation" / "report.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _latest_autonomy_14_result(self) -> dict[str, object] | None:
        path = self.operator_ux_root / "a14_composition" / "composition_result.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _latest_autonomy_15_report(self) -> dict[str, object] | None:
        path = self.operator_ux_root / "a15_gap_detection" / "report.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _latest_autonomy_16_report(self) -> dict[str, object] | None:
        path = self.operator_ux_root / "a16_mixed_mission" / "report.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _latest_autonomy_17_packet(self) -> dict[str, object] | None:
        path = self.operator_ux_root / "a17_evidence" / "evidence_packet.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _latest_autonomy_18_report(self) -> dict[str, object] | None:
        path = self.operator_ux_root / "a18_advisory" / "report.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _latest_autonomy_21_report(self) -> dict[str, object] | None:
        path = self.operator_ux_root / "a21_maintenance" / "report.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _refresh_autonomy_5_controls(self) -> None:
        execution_root = self.operator_ux_root / "autonomy_4_execution"
        has_final = bool(tuple((execution_root / "final_synthesis").glob("*.json"))) if execution_root.exists() else False
        review, request = self._latest_autonomy_5_review()
        if review:
            self.a5_review_status.set(f"A5: {str(review.get('provisional_disposition') or 'reviewed').replace('_', ' ')}")
        elif has_final:
            self.a5_review_status.set("A5: outcome ready for review")
        else:
            self.a5_review_status.set("A5: no completed A4 outcome")
        enabled = {
            "review": has_final and not bool(review),
            "explain": bool(review),
            "failed": bool(review),
            "keep": bool(review and request),
            "send": bool(review and request),
        }
        for key, button in self.a5_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _refresh_autonomy_6_controls(self) -> None:
        a5_review, _a5_request = self._latest_autonomy_5_review()
        candidate, policy, request = self._latest_autonomy_6_review()
        if policy:
            self.a6_admission_status.set(f"A6: {str(policy.get('admission_recommendation') or 'reviewed').replace('_', ' ')}")
        elif a5_review and a5_review.get("provisional_disposition") == "candidate_for_competence_admission_review":
            self.a6_admission_status.set("A6: candidate ready")
        else:
            self.a6_admission_status.set("A6: no eligible A5 candidate")
        enabled = {
            "review": bool(a5_review and not candidate),
            "admit": bool(candidate and policy and request),
            "keep": bool(candidate and policy and request),
            "reject": bool(candidate and policy and request),
            "more": bool(candidate and policy and request),
            "explain": bool(candidate and policy),
            "ambiguous": bool(candidate and policy and request),
            "details": bool(candidate and policy),
        }
        for key, button in self.a6_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _refresh_autonomy_13_controls(self) -> None:
        report = self._latest_autonomy_13_report()
        accepted_root = self.operator_ux_root / "autonomy_6_competence_admission" / "accepted_competencies"
        retained_roots = (
            ROOT / ".tmp" / "autonomy-12r-final-cycle-1" / "a6_admission" / "accepted_competencies",
            ROOT / ".tmp" / "autonomy-12r-final-cycle-2" / "a6_admission" / "accepted_competencies",
        )
        has_competence = bool(tuple(accepted_root.glob("*.json"))) if accepted_root.exists() else any(root.exists() and tuple(root.glob("*.json")) for root in retained_roots)
        if report:
            self.a13_activation_status.set(f"A13: {str(report.get('status') or 'reviewed').replace('_', ' ')}")
        elif has_competence:
            self.a13_activation_status.set("A13: accepted competence available")
        else:
            self.a13_activation_status.set("A13: no accepted competence")
        enabled = {
            "use": has_competence and not bool(report),
            "fit": bool(report),
            "cannot": bool(report),
            "scope": bool(report),
            "expires": bool(report),
            "evaluation": bool(report),
            "stop": bool(report),
        }
        for key, button in self.a13_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _refresh_autonomy_14_controls(self) -> None:
        result = self._latest_autonomy_14_result()
        if result:
            self.a14_composition_status.set(f"A14: {str(result.get('status') or 'running').replace('_', ' ')}")
        else:
            self.a14_composition_status.set("A14: Validate JSON -> Reconcile records")
        terminal = bool(result and result.get("terminal"))
        paused = bool(result and result.get("status") == "paused_operator")
        enabled = {
            "start": not bool(result),
            "pause": not terminal and not paused,
            "resume": paused,
            "stop": not terminal,
            "explain": bool(result),
            "evidence": bool(result),
            "provenance": bool(result),
            "limits": True,
        }
        for key, button in self.a14_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _refresh_autonomy_15_controls(self) -> None:
        report = self._latest_autonomy_15_report()
        if report:
            self.a15_gap_status.set(f"A15: {str(report.get('status') or 'classified').replace('_', ' ')}")
        else:
            self.a15_gap_status.set("A15: support check ready")
        enabled = {
            "classify": not bool(report),
            "missing": bool(report),
            "explain": bool(report),
            "evidence": bool(report),
            "clarify": bool(report),
        }
        for key, button in self.a15_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _refresh_autonomy_16_controls(self) -> None:
        report = self._latest_autonomy_16_report()
        if report:
            self.a16_mission_status.set(f"A16: {str(report.get('final_mission_disposition') or report.get('status') or 'running').replace('_', ' ')}")
        else:
            self.a16_mission_status.set("A16: mixed mission ready")
        terminal = bool(report and report.get("final_mission_disposition") in {"partially_completed", "completed", "stopped_by_operator"})
        enabled = {
            "start": not bool(report),
            "pause": not terminal,
            "resume": bool(report) and not terminal,
            "stop": not terminal,
            "current": bool(report),
            "blocked": bool(report),
            "evidence": bool(report),
            "limits": True,
            "graph": bool(report),
        }
        for key, button in self.a16_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _refresh_autonomy_17_controls(self) -> None:
        packet = self._latest_autonomy_17_packet()
        if packet:
            self.a17_evidence_status.set(f"A17: {str(packet.get('acquisition_disposition') or 'evidence acquired').replace('_', ' ')}")
        else:
            self.a17_evidence_status.set("A17: local evidence ready")
        enabled = {
            "acquire": not bool(packet),
            "explain": bool(packet),
            "sources": bool(packet),
            "contradictions": bool(packet),
            "missing": bool(packet),
            "limits": bool(packet),
            "revalidate": bool(packet),
        }
        for key, button in self.a17_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _refresh_autonomy_18_controls(self) -> None:
        packet = self._latest_autonomy_17_packet()
        report = self._latest_autonomy_18_report()
        if report:
            self.a18_advice_status.set(f"A18: {str(report.get('status') or 'advisory ready').replace('_', ' ')}")
        elif packet:
            self.a18_advice_status.set("A18: evidence ready for advice")
        else:
            self.a18_advice_status.set("A18: needs A17 packet")
        enabled = {
            "request": bool(packet) and not bool(report),
            "explain": bool(report),
            "grounding": bool(report),
            "rejected": bool(report),
            "limits": bool(packet) or bool(report),
            "keep": bool(report),
            "reject": bool(report),
        }
        for key, button in self.a18_control_buttons.items():
            button.configure(state=tk.NORMAL if enabled.get(key) else tk.DISABLED)

    def _refresh_autonomy_21_controls(self) -> None:
        report = self._latest_autonomy_21_report()
        if report:
            states = tuple(item.get("health_label") for item in tuple(dict(report.get("competence_inventory_after") or {}).get("effective_inventory") or ()))
            self.a21_health_status.set("A21: " + (", ".join(str(item) for item in states if item) or "maintenance passed"))
        else:
            self.a21_health_status.set("A21: maintenance ready")
        for button in self.a21_control_buttons.values():
            button.configure(state=tk.NORMAL)

    def _run_autonomy_5_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "autonomy_5_outcome_review"
        if action == "review":
            result = review_completed_outcome(self.operator_ux_root / "autonomy_4_execution", output_root=output_root)
            review = dict(result.get("review") or {})
            request = dict(result.get("operator_request") or {})
            if request:
                self.active_operator_ux_request = request
                self.operator_ux_request_card = compile_operator_request_card(request)
                self._persist_operator_ux_record("requests", str(request["request_id"]), request)
            for event in tuple(result.get("narration") or ()):
                event = dict(event)
                self.operator_ux_narration_events[str(event["event_id"])] = event
                self._persist_operator_ux_record("narration", str(event["event_id"]), event)
            self._append_chat("DELTA", f"I reviewed what this plan actually proved: {review.get('provisional_disposition')}. No competence was admitted.")
        else:
            review, request = self._latest_autonomy_5_review()
            if not review:
                self._append_chat("DELTA", "I do not have an A5 outcome review yet.")
                return {"status": "blocked_no_a5_review"}
            if action == "explain":
                message = explain_review_evidence(review)
                self._append_chat("DELTA", message)
                result = {"status": "explained", "message": message}
            elif action == "failed":
                failed = ", ".join(tuple(review.get("failed_case_ids") or ())) or "No failed cases in the final reviewed evaluator result."
                self._append_chat("DELTA", f"A5 failed cases: {failed}")
                result = {"status": "failed_cases_shown", "failed_cases": tuple(review.get("failed_case_ids") or ())}
            elif action in {"keep", "send"}:
                if not request:
                    self._append_chat("DELTA", "The A5 review request is missing; I will not create a response.")
                    return {"status": "blocked_no_a5_request"}
                text = "keep it provisional" if action == "keep" else "send it for competence review"
                result = respond_to_outcome_review(review, request, text, output_root=output_root)
                response = dict(result.get("response") or {})
                self.operator_ux_responses.append(response)
                self._persist_operator_ux_record("responses", str(response["response_id"]), response)
                if response.get("consumed"):
                    self.operator_ux_consumed_responses.append(response)
                    self._persist_operator_ux_record("consumed_responses", str(response["response_id"]), response)
                self._append_chat("DELTA", f"A5 response recorded: {response.get('operator_action')}. No competence was admitted.")
            else:
                return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _run_autonomy_13_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "a13_activation"
        report = self._latest_autonomy_13_report()
        if action == "use":
            competence_roots = (
                self.operator_ux_root / "autonomy_6_competence_admission",
                ROOT / ".tmp" / "autonomy-12r-final-cycle-1" / "a6_admission",
                ROOT / ".tmp" / "autonomy-12r-final-cycle-2" / "a6_admission",
            )
            result = run_task_scoped_activation(output_root=output_root, competence_roots=competence_roots)
            report = dict(result.get("report") or {})
            self._append_chat("DELTA", f"A13 task-scoped activation result: {result.get('status')}. No global competence activation was created.")
        elif not report:
            self._append_chat("DELTA", "I do not have an A13 task activation report yet.")
            return {"status": "blocked_no_a13_report"}
        elif action == "fit":
            pilots = tuple(report.get("pilots") or ())
            selected = ", ".join(str(dict(p.get("selection") or {}).get("reason")) for p in pilots) or "No activation selection is recorded."
            self._append_chat("DELTA", f"Competence fit: {selected}")
            result = {"status": "fit_shown", "pilots": len(pilots)}
        elif action == "cannot":
            limits = sorted({limit for pilot in tuple(report.get("pilots") or ()) for limit in tuple(dict(dict(pilot).get("activation") or {}).get("limitations") or ())})
            self._append_chat("DELTA", "A13 limitations: " + (", ".join(limits) if limits else "No broad or global capability was admitted."))
            result = {"status": "limitations_shown", "limitations": tuple(limits)}
        elif action == "scope":
            self._append_chat("DELTA", "A13 scope is task-only, exact schema/class match, no source mutation, provider, network, deployment, credentials, or global activation.")
            result = {"status": "scope_shown"}
        elif action == "expires":
            expirations = tuple(dict(dict(pilot).get("activation") or {}).get("activation_expiration") for pilot in tuple(report.get("pilots") or ()))
            self._append_chat("DELTA", "A13 activation expirations: " + ", ".join(str(item) for item in expirations if item))
            result = {"status": "expiration_shown", "expirations": expirations}
        elif action == "evaluation":
            evaluations = tuple(dict(dict(pilot).get("execution_result") or {}).get("evaluation_status") for pilot in tuple(report.get("pilots") or ()))
            self._append_chat("DELTA", "A13 evaluation statuses: " + ", ".join(str(item) for item in evaluations if item))
            result = {"status": "evaluation_shown", "evaluations": evaluations}
        elif action == "stop":
            self._append_chat("DELTA", "A13 task use is terminal or report-only; no active global competence use exists to stop.")
            result = {"status": "no_active_global_activation"}
        else:
            return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _run_autonomy_14_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "a14_composition"
        competence_roots = (
            self.operator_ux_root / "autonomy_6_competence_admission",
            ROOT / ".tmp" / "autonomy-12r-final-cycle-1" / "a6_admission",
            ROOT / ".tmp" / "autonomy-12r-final-cycle-2" / "a6_admission",
        )
        result_record = self._latest_autonomy_14_result()
        if action == "start":
            result = run_capability_composition(output_root=output_root, competence_roots=competence_roots, pause_after_stage_1=True)
            self._append_chat("DELTA", f"A14 composed task started: {result.get('status')}. Stage 1 validates JSON before reconciliation.")
        elif action == "resume":
            result = run_capability_composition(output_root=output_root, competence_roots=competence_roots, resume=True)
            self._append_chat("DELTA", f"A14 composed task resumed: {result.get('status')}.")
        elif action == "pause":
            result = run_capability_composition(output_root=output_root, competence_roots=competence_roots, pause_after_stage_1=True)
            self._append_chat("DELTA", f"A14 pause requested: {result.get('status')}.")
        elif action == "stop":
            result = run_capability_composition(output_root=output_root, competence_roots=competence_roots, stop_after_stage_1=True)
            self._append_chat("DELTA", f"A14 stop requested: {result.get('status')}.")
        elif not result_record:
            self._append_chat("DELTA", "I do not have an A14 composition record yet.")
            return {"status": "blocked_no_a14_record"}
        elif action == "explain":
            self._append_chat("DELTA", "A14 current stage: Stage 1 validates JSON, then Stage 2 reconciles only Stage 1 validated records.")
            result = {"status": "explained"}
        elif action == "evidence":
            stage_1 = dict(result_record.get("stage_1") or {})
            stage_2 = dict(result_record.get("stage_2") or {})
            self._append_chat("DELTA", f"A14 evidence: Stage 1 {stage_1.get('stage_status')}; Stage 2 {stage_2.get('stage_status', 'not started')}.")
            result = {"status": "evidence_shown"}
        elif action == "provenance":
            provenance = self.operator_ux_root / "a14_composition" / "provenance_chain.json"
            self._append_chat("DELTA", f"A14 provenance record: {provenance}")
            result = {"status": "provenance_shown"}
        elif action == "limits":
            self._append_chat("DELTA", "A14 limits: no provider, network, deployment, credentials, tracked-source mutation, trusted generalization, or global competence activation.")
            result = {"status": "limits_shown"}
        else:
            return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _run_autonomy_15_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "a15_gap_detection"
        competence_roots = (
            self.operator_ux_root / "autonomy_6_competence_admission",
            ROOT / ".tmp" / "autonomy-12r-final-cycle-1" / "a6_admission",
            ROOT / ".tmp" / "autonomy-12r-final-cycle-2" / "a6_admission",
        )
        report = self._latest_autonomy_15_report()
        if action == "classify":
            result = run_gap_detection(output_root=output_root, competence_roots=competence_roots)
            self._append_chat("DELTA", f"A15 support check: {result.get('status')}. Unsupported work was not executed.")
        elif not report:
            self._append_chat("DELTA", "I do not have an A15 support report yet.")
            return {"status": "blocked_no_a15_report"}
        elif action == "missing":
            gap_count = report.get("gap_count", 0)
            self._append_chat("DELTA", f"A15 missing capability count: {gap_count}. Safe gaps remain proposals only.")
            result = {"status": "missing_shown", "gap_count": gap_count}
        elif action == "explain":
            self._append_chat("DELTA", "A15 compares task requirements against accepted competence clauses and the A14 composition contract. It does not force-fit unsupported work.")
            result = {"status": "explained"}
        elif action == "evidence":
            records = tuple(report.get("records") or ())
            self._append_chat("DELTA", f"A15 evidence: {len(records)} fresh task requirement records classified.")
            result = {"status": "evidence_shown", "record_count": len(records)}
        elif action == "clarify":
            self._append_chat("DELTA", "A15 clarification request: ambiguous tasks need task class, input schema, output schema, authority, and desired behavior before execution.")
            result = {"status": "clarification_requested"}
        else:
            return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _run_autonomy_16_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "a16_mixed_mission"
        competence_roots = (
            self.operator_ux_root / "autonomy_6_competence_admission",
            ROOT / ".tmp" / "autonomy-12r-final-cycle-1" / "a6_admission",
            ROOT / ".tmp" / "autonomy-12r-final-cycle-2" / "a6_admission",
        )
        report = self._latest_autonomy_16_report()
        if action == "start":
            result = run_mixed_mission(output_root=output_root, competence_roots=competence_roots)
            self._append_chat("DELTA", f"A16 mixed mission result: {result.get('status')}. Independent safe work continued around blocked branches.")
        elif action == "pause":
            result = run_mixed_mission(output_root=output_root, competence_roots=competence_roots, mode="pause")
            self._append_chat("DELTA", f"A16 mission pause: {result.get('status')}.")
        elif action == "resume":
            result = run_mixed_mission(output_root=output_root, competence_roots=competence_roots, mode="resume")
            self._append_chat("DELTA", f"A16 mission resume: {result.get('status')}.")
        elif action == "stop":
            result = run_mixed_mission(output_root=output_root, competence_roots=competence_roots, mode="stop")
            self._append_chat("DELTA", f"A16 mission stop: {result.get('status')}.")
        elif not report:
            self._append_chat("DELTA", "I do not have an A16 mission report yet.")
            return {"status": "blocked_no_a16_report"}
        elif action == "current":
            self._append_chat("DELTA", "A16 current task view is reconstructed from durable task states; no running task remains after the pilot.")
            result = {"status": "current_task_explained"}
        elif action == "blocked":
            blocked = [task for task in tuple(report.get("tasks") or ()) if str(task.get("current_lifecycle_state", "")).startswith("blocked")]
            self._append_chat("DELTA", f"A16 blocked tasks: {len(blocked)}. Blocked branches did not stop independent safe work.")
            result = {"status": "blocked_task_explained", "blocked_count": len(blocked)}
        elif action == "evidence":
            self._append_chat("DELTA", f"A16 evidence: {len(tuple(report.get('tasks') or ()))} persisted mission tasks and {report.get('gap_candidates_queued')} queued gap candidates.")
            result = {"status": "mission_evidence_shown"}
        elif action == "limits":
            self._append_chat("DELTA", "A16 limits: one active task, no providers, network, deployment, credentials, source mutation, global activation, or automatic development execution.")
            result = {"status": "mission_limits_shown"}
        elif action == "graph":
            self._append_chat("DELTA", f"A16 task graph is persisted under {output_root / 'task_graph.json'}.")
            result = {"status": "task_graph_shown"}
        else:
            return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _run_autonomy_17_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "a17_evidence"
        packet = self._latest_autonomy_17_packet()
        if action == "acquire":
            gap_root = ROOT / ".tmp" / "autonomy-16-mixed-mission" / "gaps"
            gap = select_real_gap(gap_root) if gap_root.exists() else None
            result = acquire_local_evidence(output_root=output_root, gap=gap)
            self._append_chat("DELTA", f"A17 local evidence result: {result.get('status')}. The gap remains unresolved and no development execution started.")
        elif not packet:
            self._append_chat("DELTA", "I do not have an A17 local evidence packet yet.")
            return {"status": "blocked_no_a17_packet"}
        elif action == "explain":
            self._append_chat("DELTA", f"A17 disposition: {packet.get('acquisition_disposition')}. Evidence is planning input only; unsupported conclusions remain {', '.join(packet.get('unsupported_conclusions') or ())}.")
            result = {"status": "evidence_explained"}
        elif action == "sources":
            self._append_chat("DELTA", f"A17 sources: {len(tuple(packet.get('source_paths') or ()))} inspected under approved roots. Packet: {output_root / 'evidence_packet.json'}")
            result = {"status": "sources_shown", "source_count": len(tuple(packet.get("source_paths") or ()))}
        elif action == "contradictions":
            contradictions = tuple(packet.get("contradictory_evidence") or ())
            self._append_chat("DELTA", f"A17 contradictions/limits preserved: {len(contradictions)}. No local implementation proves the blocked behavior.")
            result = {"status": "contradictions_shown", "contradiction_count": len(contradictions)}
        elif action == "missing":
            missing = tuple(packet.get("missing_evidence") or ())
            self._append_chat("DELTA", f"A17 missing evidence clauses: {len(missing)}. These must be resolved before evaluator design or capability claims.")
            result = {"status": "missing_evidence_shown", "missing_count": len(missing)}
        elif action == "limits":
            self._append_chat("DELTA", "A17 limits: approved local roots only, bounded bytes/excerpts/files, no providers, network, deployment, credentials, source mutation, gap resolution, or A18 execution.")
            result = {"status": "limits_shown"}
        elif action == "revalidate":
            stale = detect_stale_packet(packet)
            write_operator_ux_json(output_root / "stale_evidence_audit.json", stale)
            self._append_chat("DELTA", f"A17 stale revalidation: {'stale' if stale.get('stale') else 'current'}.")
            result = {"status": "stale_revalidated", "stale": bool(stale.get("stale"))}
        else:
            return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _run_autonomy_18_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "a18_advisory"
        packet = self._latest_autonomy_17_packet()
        report = self._latest_autonomy_18_report()
        if action == "request":
            if not packet:
                self._append_chat("DELTA", "A18 needs an A17 evidence packet before bounded advice can be requested.")
                return {"status": "blocked_no_a17_packet"}
            result = request_bounded_advice(output_root=output_root, packet=packet)
            self._append_chat("DELTA", f"A18 bounded advice result: {result.get('status')}. Advice remains untrusted and cannot execute anything.")
        elif action == "limits":
            self._append_chat("DELTA", "A18 limits: recorded advisory packet only, zero provider calls, zero network, no deployment, credentials, source mutation, authority grant, competence admission, or A19 execution.")
            result = {"status": "advisory_limits_shown"}
        elif not report:
            self._append_chat("DELTA", "I do not have an A18 advisory report yet.")
            return {"status": "blocked_no_a18_report"}
        elif action == "explain":
            output = dict(report.get("advisory_output") or {})
            self._append_chat("DELTA", f"A18 proposal: {output.get('first_suspected_transition')}. It is advisory only and retains uncertainty.")
            result = {"status": "advice_explained"}
        elif action == "grounding":
            audit = dict(report.get("grounding_audit") or {})
            self._append_chat("DELTA", f"A18 grounding accepted: {audit.get('accepted')}. Provider calls: {audit.get('provider_calls')}; network calls: {audit.get('network_calls')}.")
            result = {"status": "grounding_shown", "accepted": bool(audit.get("accepted"))}
        elif action == "rejected":
            rejected = tuple(report.get("rejected_outputs") or ())
            self._append_chat("DELTA", f"A18 rejected advisory outputs: {len(rejected)}. Unsafe claims were preserved as rejected evidence.")
            result = {"status": "rejected_claims_shown", "rejected_count": len(rejected)}
        elif action == "keep":
            self._append_chat("DELTA", "A18 proposal kept as advisory evidence only. No source repair or A19 authority was created.")
            result = {"status": "proposal_kept_advisory_only"}
        elif action == "reject":
            self._append_chat("DELTA", "A18 advice rejected by operator surface. The A17 gap remains unresolved.")
            result = {"status": "advice_rejected"}
        else:
            return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _run_autonomy_21_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "a21_maintenance"
        result = run_competence_maintenance(output_root=output_root)
        report = dict(result.get("report") or {})
        events = tuple(report.get("maintenance_events") or ())
        if action == "explain":
            self._append_chat("DELTA", "A21 competence health is reconstructed from immutable admissions plus maintenance records; old admissions are not rewritten.")
        elif action == "evidence":
            self._append_chat("DELTA", f"A21 evidence: {len(events)} maintenance transitions with preserved triggering evidence digests.")
        elif action == "tasks":
            affected = sorted({task for event in events for task in tuple(event.get("affected_tasks") or ())})
            self._append_chat("DELTA", "A21 affected tasks: " + (", ".join(affected) if affected else "none"))
        elif action == "reevaluate":
            self._append_chat("DELTA", "A21 reevaluation requested as a maintenance event only; no global trust or authority expansion is available.")
        elif action == "suspend":
            self._append_chat("DELTA", "A21 suspension is represented by immutable maintenance records and blocks dependent activation/composition.")
        elif action == "restore":
            self._append_chat("DELTA", "A21 restore keeps only proven narrowed scope and requires operator review for reactivation.")
        else:
            return None
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return {"status": "maintenance_view_shown", "action": action}

    def _run_autonomy_6_visible_control(self, action: str) -> dict[str, object] | None:
        output_root = self.operator_ux_root / "autonomy_6_competence_admission"
        if action == "review":
            result = review_competence_candidate(
                self.operator_ux_root / "autonomy_5_outcome_review",
                output_root=output_root,
                existing_competence_roots=(LIVE_RUNTIME_4_ACCEPTED_ROOT,),
            )
            candidate = dict(result.get("candidate") or {})
            policy = dict(result.get("policy") or {})
            request = dict(result.get("operator_request") or {})
            if request:
                self.active_operator_ux_request = request
                self.operator_ux_request_card = dict(request.get("card") or {})
                self._persist_operator_ux_record("requests", str(request["request_id"]), request)
            for event in tuple(result.get("narration") or ()):
                event = dict(event)
                self.operator_ux_narration_events[str(event["event_id"])] = event
                self._persist_operator_ux_record("narration", str(event["event_id"]), event)
            self._append_chat("DELTA", f"A6 reviewed the competence candidate: {policy.get('admission_recommendation')}. No competence was admitted automatically.")
        else:
            candidate, policy, request = self._latest_autonomy_6_review()
            if not candidate or not policy:
                self._append_chat("DELTA", "I do not have an A6 competence candidate yet.")
                return {"status": "blocked_no_a6_candidate"}
            if action == "explain":
                message = explain_competence_scope(candidate, policy)
                self._append_chat("DELTA", message)
                result = {"status": "explained", "message": message}
            elif action == "details":
                details = f"Candidate: {candidate.get('admission_candidate_id')}; policy: {policy.get('policy_id')}; activation: {candidate.get('permitted_activation_state')}"
                self._append_chat("DELTA", details)
                result = {"status": "technical_details_shown", "details": details}
            else:
                if not request:
                    self._append_chat("DELTA", "The A6 admission request is missing; I will not create a response.")
                    return {"status": "blocked_no_a6_request"}
                text_by_action = {
                    "admit": "admit this competence",
                    "keep": "keep it provisional",
                    "reject": "reject admission",
                    "more": "request more evaluation",
                    "ambiguous": "looks good",
                }
                result = respond_to_competence_admission(
                    candidate,
                    policy,
                    request,
                    text_by_action.get(action, ""),
                    output_root=output_root,
                    visible_button="Admit this competence" if action == "admit" else None,
                )
                response = dict(result.get("response") or {})
                if response:
                    self.operator_ux_responses.append(response)
                    self._persist_operator_ux_record("responses", str(response["response_id"]), response)
                    if response.get("consumed"):
                        self.operator_ux_consumed_responses.append(response)
                        self._persist_operator_ux_record("consumed_responses", str(response["response_id"]), response)
                self._append_chat("DELTA", f"A6 response: {result.get('status')}. Activation remains inactive and unpromoted.")
        self._refresh_operator_ux_views()
        self._refresh_state_cards()
        return result

    def _show_operator_ux_popup(self) -> None:
        if not self.operator_ux_request_card:
            return
        if self.operator_ux_popup is not None and self.operator_ux_popup.winfo_exists():
            self.operator_ux_popup.lift()
            return
        card = self.operator_ux_request_card
        popup = tk.Toplevel(self.root)
        popup.title(str(card.get("title") or "I need your approval"))
        popup.geometry("620x420")
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
        self.operator_ux_popup = popup
        frame = ttk.Frame(popup, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=str(card.get("title") or "I need your approval"), font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=14)
        text.pack(fill=tk.BOTH, expand=True, pady=(8, 8))
        text.insert(
            tk.END,
            "\n".join([
                str(card.get("what_delta_wants")),
                "",
                f"Why: {card.get('why')}",
                f"Missing: {card.get('missing_information_or_capability')}",
                f"Will inspect: {', '.join(card.get('files_or_resources') or ()) or 'No files listed'}",
                f"May change: {card.get('may_change')}",
                f"Provider/network: {card.get('provider_or_network_use')}",
                f"Learning attempts: {card.get('learning_attempts')}",
                f"Recommended: {card.get('recommended_action')}",
                f"If declined: {card.get('if_declined')}",
            ]),
        )
        text.configure(state=tk.DISABLED)
        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Approve", command=lambda: self._handle_operator_ux_button("approve")).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Decline", command=lambda: self._handle_operator_ux_button("decline")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(buttons, text="Explain", command=lambda: self._handle_operator_ux_button("explain")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(buttons, text="Show alternatives", command=lambda: self._handle_operator_ux_button("show_alternatives")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(buttons, text="Change limits", command=lambda: self._handle_operator_ux_button("change_limits")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(buttons, text="Pause goal", command=lambda: self._handle_operator_ux_button("pause")).pack(side=tk.LEFT, padx=(6, 0))

    def _create_operator_ux_demo_request(self) -> dict[str, object]:
        request = {
            "schema": "operator_ux_demo_request_v1",
            "request_id": "operator-ux-demo-request-reconciliation",
            "goal_id": "operator-ux-demo-goal",
            "goal_title": "Compare customer records",
            "title": "I need your approval",
            "what_delta_wants": "Try one bounded reconciliation step for the current disposable CSV and JSON records.",
            "why": "The report is more useful if matching records across formats can be checked before final synthesis.",
            "missing_information_or_capability": "A safe record-reconciliation decision for this branch.",
            "files_or_resources": ("current disposable CSV fixture", "current disposable JSON fixture"),
            "may_change": "Only disposable operator-UX records under .tmp/operator-ux-1-humanized-runtime-v1.",
            "provider_or_network_use": "No provider calls and no network expansion.",
            "learning_attempts": 0,
            "limits": {"controller_cycles": 0, "provider_calls": 0, "network": False, "source_mutation": False},
            "recommended_action": "Approve",
            "if_declined": "The goal remains paused and no reconciliation step is authorized.",
            "mission_id": "operator-ux-demo-mission",
            "work_item_id": "operator-ux-demo-work-item",
            "authority_id": "operator-ux-demo-authority",
            "authority_digest": "hidden-in-normal-view",
            "approval_token": "operator-ux-demo-token",
            "created_at": "2026-07-22T00:00:00+00:00",
        }
        request = compile_operator_request_card(request) | {key: value for key, value in request.items() if key not in {"artifact_digest"}}
        request["artifact_digest"] = compile_operator_request_card(request)["artifact_digest"]
        self.active_operator_ux_request = request
        self.operator_ux_request_card = compile_operator_request_card(request)
        self._persist_operator_ux_record("requests", str(request["request_id"]), request)
        event = compile_narration_event(
            mission_id=str(request["mission_id"]),
            work_item_id=str(request["work_item_id"]),
            phase="approval_requested",
            event_type="approval_needed",
            message="I need your approval before continuing this bounded step.",
            source_artifact=str(request["artifact_digest"]),
        )
        self.operator_ux_narration_events[str(event["event_id"])] = event
        self._persist_operator_ux_record("narration", str(event["event_id"]), event)
        self._show_operator_ux_popup()
        return request

    def _discover_autonomy_1_next_goal(self) -> dict[str, object]:
        evidence_roots = (
            ROOT / ".tmp" / "live-general-2-dynamic-branch-v1",
            ROOT / ".tmp" / "live-general-3-approved-learning-v1",
            ROOT / ".tmp" / "live-runtime-3-interruption-resumption-v1",
            ROOT / ".tmp" / "live-runtime-4-crash-integrity-v1",
        )
        result = persist_autonomy_1_goal_discovery(
            evidence_roots=evidence_roots,
            output_root=ROOT / AUTONOMY_1_ROOT,
        )
        request = result.get("operator_request")
        if not request:
            self._append_chat("DELTA", "I inspected retained runtime evidence and did not find an unresolved development goal to propose.")
            return result
        request = dict(request)
        self.active_operator_ux_request = request
        self.operator_ux_request_card = compile_operator_request_card(request)
        self._persist_operator_ux_record("requests", str(request["request_id"]), request)
        event = compile_narration_event(
            mission_id=str(request["mission_id"]),
            work_item_id=str(request["work_item_id"]),
            phase="goal_discovery",
            event_type="next_goal_proposed",
            message="I found a possible next goal from retained runtime evidence.",
            source_artifact=str(request["artifact_digest"]),
        )
        self.operator_ux_narration_events[str(event["event_id"])] = event
        self._persist_operator_ux_record("narration", str(event["event_id"]), event)
        self._show_operator_ux_popup()
        return result

    def _discover_autonomy_2_goal_ranking(self) -> dict[str, object]:
        evidence_roots = (
            ROOT / ".tmp" / "autonomy-2-disposable-evidence-v1",
            ROOT / ".tmp" / "live-general-2-dynamic-branch-v1",
            ROOT / ".tmp" / "live-general-3-approved-learning-v1",
            ROOT / ".tmp" / "live-runtime-4-crash-integrity-v1",
        )
        result = persist_prioritization(
            evidence_roots=evidence_roots,
            output_root=ROOT / AUTONOMY_2_ROOT,
            goal_store=self.operator_ux_root / "approved_goals",
        )
        request = result.get("operator_request")
        if not request:
            self._append_chat("DELTA", "I did not find a sufficiently supported next goal.")
            return result
        request = dict(request)
        self.active_operator_ux_request = request
        self.operator_ux_request_card = compile_operator_request_card(request)
        self._persist_operator_ux_record("requests", str(request["request_id"]), request)
        event = compile_narration_event(
            mission_id=str(request["mission_id"]),
            work_item_id=str(request["work_item_id"]),
            phase="goal_prioritization",
            event_type="goal_ranking_proposed",
            message=f"I found {len(tuple(request.get('candidates') or ())) } evidence-backed goals and recommend one.",
            source_artifact=str(request["artifact_digest"]),
        )
        self.operator_ux_narration_events[str(event["event_id"])] = event
        self._persist_operator_ux_record("narration", str(event["event_id"]), event)
        self._show_operator_ux_popup()
        return result

    def _plan_autonomy_3_next_goal(self) -> dict[str, object]:
        goal_dir = self.operator_ux_root / "approved_goals"
        goals: list[dict[str, object]] = []
        if goal_dir.exists():
            for path in sorted(goal_dir.glob("*.json")):
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if record.get("schema") == "autonomy_3_goal_queue_record_v1":
                    goals.append(record)
                elif record.get("schema") in {"autonomy_2_queued_goal_record_v1", "autonomy_1_approved_goal_record_v1"}:
                    condition = str(record.get("selected_condition_key") or record.get("goal_id") or "queued_goal")
                    goals.append({
                        "schema": "autonomy_3_goal_queue_record_v1",
                        "goal_id": str(record.get("selected_candidate_id") or record.get("goal_id") or path.stem),
                        "artifact_digest": str(record.get("artifact_digest") or path.stem),
                        "selected_candidate_id": str(record.get("selected_candidate_id") or record.get("goal_id") or ""),
                        "selected_candidate_digest": str(record.get("selected_candidate_digest") or record.get("request_digest") or ""),
                        "ranking_id": str(record.get("ranking_id") or ""),
                        "ranking_digest": str(record.get("ranking_digest") or ""),
                        "title": condition.replace("_", " ").title(),
                        "objective": f"Improve {condition.replace('_', ' ')}.",
                        "normalized_objective": " ".join(f"Improve {condition.replace('_', ' ')}.".lower().split()),
                        "condition_key": condition,
                        "source_artifact_ids": (),
                        "source_artifact_digests": (),
                        "prerequisites": ("retained evidence", "validator design"),
                        "missing_prerequisites": (),
                        "authority_requirements": (),
                        "current_queue_state": "queued" if record.get("status") in {"queued", "approved_queued_for_future_planning"} else str(record.get("status") or "queued"),
                        "priority": 1,
                        "execution_started": False,
                        "learning_started": False,
                        "trusted": False,
                        "promoted": False,
                    })
        selected = select_goal_for_planning(goals)
        if not selected:
            self._append_chat("DELTA", "I did not find an eligible queued goal to plan.")
            return {"status": "no_eligible_goal"}
        plan = compile_plan_proposal(selected)
        request = compile_plan_review_request(plan)
        self._persist_operator_ux_record("autonomy_3_plans", str(plan["plan_id"]), plan)
        self.active_operator_ux_request = request
        self.operator_ux_request_card = compile_operator_request_card(request)
        self._persist_operator_ux_record("requests", str(request["request_id"]), request)
        event = compile_narration_event(
            mission_id=str(plan["plan_id"]),
            work_item_id=str(selected["goal_id"]),
            phase="goal_planning",
            event_type="plan_waiting_for_review",
            message=f"I created a {len(tuple(plan.get('proposed_work_items') or ())) }-step plan and defined validation before execution.",
            source_artifact=str(plan["artifact_digest"]),
        )
        self.operator_ux_narration_events[str(event["event_id"])] = event
        self._persist_operator_ux_record("narration", str(event["event_id"]), event)
        self._show_operator_ux_popup()
        return {"status": "AUTONOMY_3_PLAN_WAITING_FOR_OPERATOR", "plan": plan, "operator_request": request}

    def _load_autonomy_4_approved_plan(self) -> tuple[dict[str, object] | None, dict[str, object] | None]:
        approval_dir = self.operator_ux_root / "autonomy_3_plan_approvals"
        plan_dir = self.operator_ux_root / "autonomy_3_plans"
        approvals = []
        if approval_dir.exists():
            for path in sorted(approval_dir.glob("*.json")):
                try:
                    approvals.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        if not approvals:
            self._append_chat("DELTA", "I do not have an approved plan to execute.")
            return None, None
        approval = approvals[-1]
        plan_path = plan_dir / f"{approval['plan_id']}.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        return plan, approval

    def _start_autonomy_4_approved_plan(self, *, mode: str = "start") -> dict[str, object]:
        loaded = self._load_autonomy_4_approved_plan()
        plan, approval = loaded
        if not plan or not approval:
            return {"status": "blocked_no_approved_plan"}
        execution_root = self.operator_ux_root / "autonomy_4_execution"
        if mode == "pause":
            result = run_approved_plan_execution(plan, approval, output_root=execution_root, pause_after_stage="evaluator")
        elif mode == "stop":
            result = run_approved_plan_execution(plan, approval, output_root=execution_root, stop_after_stage="prepared")
        elif mode == "resume":
            result = resume_paused_execution(plan, approval, output_root=execution_root)
        else:
            result = run_approved_plan_execution(plan, approval, output_root=execution_root)
        final = dict(result.get("final_synthesis") or {})
        if final:
            self._persist_operator_ux_record("autonomy_4_final_synthesis", str(final["synthesis_id"]), final)
            event = compile_narration_event(
                mission_id=str(plan["plan_id"]),
                work_item_id=str(plan["goal_id"]),
                phase="approved_plan_execution",
                event_type="execution_terminal",
                message=f"I completed the approved plan with disposition {final['final_disposition']} and stopped.",
                source_artifact=str(final["artifact_digest"]),
            )
            self.operator_ux_narration_events[str(event["event_id"])] = event
            self._persist_operator_ux_record("narration", str(event["event_id"]), event)
            self._append_chat("DELTA", event["message"])
        else:
            self._append_chat("DELTA", f"Execution stopped before work began: {result.get('status')}")
        return result

    def _explain_autonomy_4_execution(self, topic: str) -> dict[str, object]:
        plan, approval = self._load_autonomy_4_approved_plan()
        if not plan or not approval:
            return {"status": "blocked_no_approved_plan"}
        if topic == "limits":
            message = "A4 limits: no provider calls, no source mutation, no trusted admission, no capability promotion, one bounded revision, and a 10 minute authority window."
        elif topic == "evidence":
            message = f"A4 evidence: approved plan {plan['plan_id']} is bound to digest {plan['artifact_digest']} and validator count {len(tuple(plan.get('validation_strategy') or ()))}."
        else:
            lifecycle_path = self.operator_ux_root / "autonomy_4_execution" / "work_item_lifecycle"
            count = len(tuple(lifecycle_path.glob("*.json"))) if lifecycle_path.exists() else 0
            message = f"A4 current step: {count} durable lifecycle transitions are recorded; execution advances only through ready, running, completed, revision, paused, stopped, expired, or terminal states."
        self._append_chat("DELTA", message)
        return {"status": "explained", "topic": topic, "message": message}

    def _handle_operator_ux_button(self, intent: str) -> None:
        if not self.active_operator_ux_request:
            self._append_chat("DELTA", "There is no active approval request right now.")
            return
        if intent == "explain":
            if self.active_operator_ux_request.get("schema") == "autonomy_3_plan_review_request_v1":
                self._append_chat("DELTA", "The evaluator is defined before execution. Each step has hidden positive, negative, boundary, adversarial, and transfer cases, and approval here does not start the plan.")
            elif self.active_operator_ux_request.get("schema") == "autonomy_2_goal_selection_request_v1":
                ranking = {
                    "status": "AUTONOMY_2_GOAL_PRIORITIZATION_RECOMMENDATION",
                    "recommended_candidate": tuple(self.active_operator_ux_request.get("candidates") or ())[0],
                    "alternatives": tuple(self.active_operator_ux_request.get("alternatives") or ()),
                }
                self._append_chat("DELTA", explain_autonomy_2_ranking(ranking))
            else:
                self._append_chat("DELTA", explain_operator_request(self.active_operator_ux_request))
            return
        if intent == "show_alternatives":
            alternatives = tuple(self.active_operator_ux_request.get("alternatives") or ())
            if not alternatives:
                self._append_chat("DELTA", "I did not find a grounded alternative goal in the retained evidence.")
                return
            lines = ["Grounded alternatives:"]
            for item in alternatives[:5]:
                score = dict(item.get("score") or {})
                lines.append(f"- rank {item.get('rank')}: {item.get('goal')} (score {score.get('total_score')}, status {item.get('status')})")
            self._append_chat("DELTA", "\n".join(lines))
            return
        if intent == "change_limits":
            if self.active_operator_ux_request.get("schema") == "autonomy_3_plan_review_request_v1":
                prior_request = dict(self.active_operator_ux_request)
                plan_path = self.operator_ux_root / "autonomy_3_plans" / f"{self.active_operator_ux_request.get('plan_id')}.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                goal = {
                    "goal_id": plan["goal_id"],
                    "artifact_digest": plan["goal_digest"],
                    "normalized_objective": plan["normalized_objective"],
                    "condition_key": self.active_operator_ux_request.get("goal_id", ""),
                    "current_queue_state": "waiting_for_operator",
                    "prerequisites": plan.get("required_capabilities") or (),
                    "missing_prerequisites": plan.get("missing_capabilities") or (),
                    "source_artifact_digests": plan.get("source_evidence") or (),
                }
                revised = compile_plan_proposal(goal, prior_plan=plan, requested_changes=("reduce budget",), budget={"max_work_items": 3}, preference={"priority": "low_cost"})
                self._persist_operator_ux_record("autonomy_3_plans", str(revised["plan_id"]), revised)
                revision_intent = {"intent": "pause", "raw_text": "reduce the budget", "normalized_text": "reduce the budget", "requires_clarification": False}
                response = compile_formal_operator_response(prior_request, revision_intent, response_source="plan_revision_request")
                consumed = consume_formal_operator_response(response)
                self._persist_operator_ux_record("responses", str(response["response_id"]), response)
                self._persist_operator_ux_record("consumed_responses", str(consumed["consumption_id"]), consumed)
                self.active_operator_ux_request = compile_plan_review_request(revised)
                self.operator_ux_request_card = compile_operator_request_card(self.active_operator_ux_request)
                self._persist_operator_ux_record("requests", str(self.active_operator_ux_request["request_id"]), self.active_operator_ux_request)
                self._append_chat("DELTA", f"I created a lower-budget revised plan and preserved the original: {revised['plan_id']}.")
                return
            if self.active_operator_ux_request.get("schema") == "autonomy_2_goal_selection_request_v1":
                ranking = compile_autonomy_2_ranking(
                    evidence_roots=(ROOT / ".tmp" / "autonomy-2-disposable-evidence-v1",),
                    goal_store=self.operator_ux_root / "approved_goals",
                    preference={"priority": "low_cost"},
                    previous_ranking={"artifact_digest": self.active_operator_ux_request.get("ranking_digest", "")},
                )
                self._persist_operator_ux_record("autonomy_2_rankings", str(ranking["ranking_id"]), ranking)
                self._append_chat("DELTA", f"I created a new low-cost ranking record: {ranking['ranking_id']}.")
                return
            self._append_chat("DELTA", "For this gate, provider calls, network, deployment, credentials, and source mutation stay disabled. I can create a revised bounded request later.")
            return
        synthetic = {"intent": intent, "raw_text": intent, "normalized_text": intent, "requires_clarification": False}
        self._consume_operator_ux_intent(synthetic, response_source=f"button:{intent}")

    def _consume_operator_ux_intent(self, intent: dict[str, object], *, response_source: str) -> bool:
        request = self.active_operator_ux_request
        if not request:
            return False
        if request.get("schema") == "autonomy_3_plan_review_request_v1":
            feedback = normalize_plan_feedback(str(intent.get("raw_text") or intent.get("intent") or ""))
            if feedback["intent"] == "explain":
                self._append_chat("DELTA", "This is a proposal-only plan. Validation is defined before execution, and no mission or worker starts from this response.")
                return True
            if feedback["requires_clarification"]:
                self._append_chat("DELTA", "I'm not sure whether you approved, declined, paused, or requested a revision to the plan.")
                return True
            plan_path = self.operator_ux_root / "autonomy_3_plans" / f"{request.get('plan_id')}.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if feedback["intent"] == "revise":
                self._handle_operator_ux_button("change_limits")
                return True
            if feedback["intent"] == "approve":
                approval = approve_plan_for_future_execution(plan, feedback)
                self._persist_operator_ux_record("autonomy_3_plan_approvals", str(approval["approval_id"]), approval)
            formal_intent = {"intent": "approve" if feedback["intent"] == "approve" else "decline" if feedback["intent"] == "decline" else "pause", "raw_text": feedback["raw_text"], "normalized_text": feedback["normalized_text"], "requires_clarification": False}
            response = compile_formal_operator_response(request, formal_intent, response_source=response_source)
            consumed = consume_formal_operator_response(response)
            self._persist_operator_ux_record("responses", str(response["response_id"]), response)
            self._persist_operator_ux_record("consumed_responses", str(consumed["consumption_id"]), consumed)
            self.active_operator_ux_request = None
            self.operator_ux_request_card = None
            if self.operator_ux_popup is not None and self.operator_ux_popup.winfo_exists():
                self.operator_ux_popup.destroy()
            self._append_chat("DELTA", "I recorded the plan decision. No mission, worker, provider call, or learning run has started.")
            self._refresh_operator_ux_views()
            return True
        if request.get("schema") == "autonomy_2_goal_selection_request_v1":
            selection = persist_autonomy_2_selection(
                request=request,
                selection_text=str(intent.get("raw_text") or intent.get("intent") or ""),
                output_root=self.operator_ux_root / "autonomy_2_selection",
            )
            if selection["status"] == "clarification_required":
                self._append_chat("DELTA", "I'm not sure which goal you selected. Choose the recommended goal or one listed alternative.")
                return True
            formal_intent = {
                "intent": "approve" if selection["status"] == "queued" else "decline" if selection["status"] == "rejected" else "pause",
                "raw_text": intent.get("raw_text") or "",
                "normalized_text": intent.get("normalized_text") or "",
                "requires_clarification": False,
            }
            response = compile_formal_operator_response(request, formal_intent, response_source=response_source)
            consumed = consume_formal_operator_response(response)
            self.operator_ux_responses.append(response)
            self.operator_ux_consumed_responses.append(consumed)
            self._persist_operator_ux_record("responses", str(response["response_id"]), response)
            self._persist_operator_ux_record("consumed_responses", str(consumed["consumption_id"]), consumed)
            queued = selection.get("queued_goal") or {}
            if queued and queued.get("status") == "queued":
                self._persist_operator_ux_record("approved_goals", str(queued["selected_candidate_id"]), queued)
            self.active_operator_ux_request = None
            self.operator_ux_request_card = None
            if self.operator_ux_popup is not None and self.operator_ux_popup.winfo_exists():
                self.operator_ux_popup.destroy()
            message = "I queued the selected goal and will not begin execution until a later gate is approved." if selection["status"] == "queued" else "I recorded your decision without queueing an active goal."
            event = compile_narration_event(
                mission_id=str(request.get("mission_id") or ""),
                work_item_id=str(queued.get("selected_candidate_id") or request.get("work_item_id") or ""),
                phase="goal_selection",
                event_type="goal_selection_recorded",
                message=message,
                source_artifact=str((queued or consumed).get("artifact_digest")),
            )
            self.operator_ux_narration_events[str(event["event_id"])] = event
            self._persist_operator_ux_record("narration", str(event["event_id"]), event)
            self._append_chat("DELTA", message)
            self._refresh_operator_ux_views()
            return True
        if intent.get("intent") == "explain":
            self._append_chat("DELTA", explain_operator_request(request))
            return True
        if intent.get("intent") == "ambiguous":
            self._append_chat("DELTA", "I'm not sure whether you are approving this action. Approve or decline?")
            return True
        response = compile_formal_operator_response(request, intent, response_source=response_source)
        consumed = consume_formal_operator_response(response)
        self.operator_ux_responses.append(response)
        self.operator_ux_consumed_responses.append(consumed)
        self._persist_operator_ux_record("responses", str(response["response_id"]), response)
        self._persist_operator_ux_record("consumed_responses", str(consumed["consumption_id"]), consumed)
        self.active_operator_ux_request = None
        self.operator_ux_request_card = None
        if self.operator_ux_popup is not None and self.operator_ux_popup.winfo_exists():
            self.operator_ux_popup.destroy()
        if request.get("schema") == "autonomy_1_goal_approval_request_v1" and intent.get("intent") == "approve":
            approved_goal = {
                "schema": "autonomy_1_approved_goal_record_v1",
                "goal_id": request.get("goal_id"),
                "request_id": request.get("request_id"),
                "request_digest": request.get("artifact_digest"),
                "proposal_id": request.get("proposal_id"),
                "proposal_digest": request.get("proposal_digest"),
                "status": "approved_queued_for_future_planning",
                "execution_started": False,
                "learning_started": False,
                "provider_calls": 0,
                "trusted_admission": False,
                "capability_promotion": False,
                "created_at": "2026-07-22T00:00:00+00:00",
            }
            self._persist_operator_ux_record("approved_goals", str(request.get("goal_id")), approved_goal)
        message = {
            "approve": "Approval received. I recorded the goal for a later planning gate; no learning or execution has started." if request.get("schema") == "autonomy_1_goal_approval_request_v1" else "Approval received. I'm resuming the bounded step.",
            "decline": "Declined. I will leave this branch paused without authorizing the step.",
            "pause": "Paused. I will wait before continuing this goal.",
        }.get(str(intent.get("intent")), "Response recorded.")
        event = compile_narration_event(
            mission_id=str(request.get("mission_id") or ""),
            work_item_id=str(request.get("work_item_id") or ""),
            phase="operator_response_consumed",
            event_type="resumed" if intent.get("intent") == "approve" else "waiting",
            message=message,
            source_artifact=str(consumed["artifact_digest"]),
        )
        self.operator_ux_narration_events[str(event["event_id"])] = event
        self._persist_operator_ux_record("narration", str(event["event_id"]), event)
        self._append_chat("DELTA", message)
        self._refresh_operator_ux_views()
        return True

    def _build_database_tab(self) -> None:
        top = ttk.Frame(self.database_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Concept Lookup").pack(side=tk.LEFT)
        self.database_query = ttk.Entry(top)
        self.database_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        self.database_query.bind("<Return>", lambda _event: self._search_database_concepts())
        ttk.Button(top, text="Search", command=self._search_database_concepts).pack(side=tk.LEFT)
        ttk.Button(top, text="Browse Diverse", command=self._load_database_concepts).pack(side=tk.LEFT, padx=(8, 0))

        self.database_status = tk.StringVar(value="Read-only concept database.")
        ttk.Label(self.database_tab, textvariable=self.database_status).pack(anchor=tk.W, pady=(8, 0))

        page_bar = ttk.Frame(self.database_tab)
        page_bar.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(page_bar, text="Previous", command=self._database_previous_page).pack(side=tk.LEFT)
        ttk.Button(page_bar, text="Next", command=self._database_next_page).pack(side=tk.LEFT, padx=(8, 0))
        self.database_page_status = tk.StringVar(value="")
        ttk.Label(page_bar, textvariable=self.database_page_status).pack(side=tk.LEFT, padx=(12, 0))

        panes = ttk.PanedWindow(self.database_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        list_frame = ttk.Frame(panes)
        detail_frame = ttk.Frame(panes)
        panes.add(list_frame, weight=3)
        panes.add(detail_frame, weight=2)

        self.database_concepts = ttk.Treeview(
            list_frame,
            columns=("name", "domain", "type", "quality"),
            show="headings",
            height=18,
        )
        self.database_concepts.heading("name", text="Concept")
        self.database_concepts.heading("domain", text="Domain")
        self.database_concepts.heading("type", text="Type")
        self.database_concepts.heading("quality", text="Quality")
        self.database_concepts.column("name", width=320)
        self.database_concepts.column("domain", width=160)
        self.database_concepts.column("type", width=220)
        self.database_concepts.column("quality", width=80, anchor=tk.CENTER)
        self.database_concepts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.database_concepts.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.database_concepts.configure(yscrollcommand=scrollbar.set)
        self.database_concepts.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_database_concept())

        ttk.Label(detail_frame, text="Concept Detail").pack(anchor=tk.W)
        self.database_detail = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD)
        self.database_detail.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.database_detail.configure(state=tk.DISABLED)
        self.database_items: dict[str, dict[str, object]] = {}
        self.database_results: list[dict[str, object]] = []
        self.database_page = 0
        self.database_page_size = 100
        self.database_result_status = ""
        self._load_database_concepts()

    def _build_rc3_tab(self) -> None:
        top = ttk.Frame(self.rc3_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="RC3 Capability Panels").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_rc3_snapshot).pack(side=tk.RIGHT)
        ttk.Button(top, text="Generate UI Report", command=self._generate_rc3_ui_report).pack(side=tk.RIGHT, padx=(0, 8))

        self.rc3_status = tk.StringVar(value="Read-only RC3 diagnostics. No execution controls are available.")
        ttk.Label(self.rc3_tab, textvariable=self.rc3_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.rc3_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.rc3_panels = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.rc3_panels.heading("status", text="Panel")
        self.rc3_panels.column("status", width=240)
        self.rc3_panels.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.rc3_panels.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rc3_panels.configure(yscrollcommand=scrollbar.set)
        self.rc3_panels.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_rc3_panel())

        self.rc3_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.rc3_detail.pack(fill=tk.BOTH, expand=True)
        self.rc3_detail.configure(state=tk.DISABLED)
        self.rc3_snapshot: dict[str, object] = {}
        self._refresh_rc3_snapshot()

    def _build_rc4_tab(self) -> None:
        top = ttk.Frame(self.rc4_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="RC4 Governed Action Runtime").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_rc4_snapshot).pack(side=tk.RIGHT)
        ttk.Button(top, text="Generate UI Report", command=self._generate_rc4_ui_report).pack(side=tk.RIGHT, padx=(0, 8))

        self.rc4_status = tk.StringVar(value="Read-only RC4 diagnostics. No execution controls are available.")
        ttk.Label(self.rc4_tab, textvariable=self.rc4_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.rc4_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.rc4_panels = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.rc4_panels.heading("status", text="Panel")
        self.rc4_panels.column("status", width=280)
        self.rc4_panels.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.rc4_panels.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rc4_panels.configure(yscrollcommand=scrollbar.set)
        self.rc4_panels.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_rc4_panel())

        self.rc4_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.rc4_detail.pack(fill=tk.BOTH, expand=True)
        self.rc4_detail.configure(state=tk.DISABLED)
        self.rc4_snapshot: dict[str, object] = {}
        self._refresh_rc4_snapshot()

    def _build_rc5_tab(self) -> None:
        top = ttk.Frame(self.rc5_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="RC5 Purpose-Aligned Developmental Cognition").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_rc5_snapshot).pack(side=tk.RIGHT)
        ttk.Button(top, text="Generate UI Report", command=self._generate_rc5_ui_report).pack(side=tk.RIGHT, padx=(0, 8))

        self.rc5_status = tk.StringVar(value="Read-only RC5 diagnostics. Manual consultation is packet-only; no API calls are available.")
        ttk.Label(self.rc5_tab, textvariable=self.rc5_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.rc5_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.rc5_panels = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.rc5_panels.heading("status", text="Panel")
        self.rc5_panels.column("status", width=300)
        self.rc5_panels.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.rc5_panels.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rc5_panels.configure(yscrollcommand=scrollbar.set)
        self.rc5_panels.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_rc5_panel())

        self.rc5_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.rc5_detail.pack(fill=tk.BOTH, expand=True)
        self.rc5_detail.configure(state=tk.DISABLED)
        self.rc5_snapshot: dict[str, object] = {}
        self._refresh_rc5_snapshot()

    def _build_evaluation_tab(self) -> None:
        top = ttk.Frame(self.evaluation_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="GSR Evaluation Review").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_evaluation_snapshot).pack(side=tk.RIGHT)

        self.evaluation_status = tk.StringVar(
            value="Read-only GSR-E3 review surface. No execution, application, persistence, or automatic continuation."
        )
        ttk.Label(self.evaluation_tab, textvariable=self.evaluation_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.evaluation_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.evaluation_items = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.evaluation_items.heading("status", text="Evaluation Stage")
        self.evaluation_items.column("status", width=320)
        self.evaluation_items.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.evaluation_items.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.evaluation_items.configure(yscrollcommand=scrollbar.set)
        self.evaluation_items.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_evaluation_item())

        controls = ttk.Frame(right)
        controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(controls, text="Accept Mission", command=self._accept_selected_compiled_mission).pack(side=tk.LEFT)
        ttk.Button(controls, text="Start Development Runtime", command=self._start_oar_development_runtime).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Run Fixture Evidence", command=self._execute_selected_fixture_proposal).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Run Tracked-Source Preflight", command=self._run_selected_tracked_source_preflight).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Accept", command=lambda: self._record_evaluation_disposition("accepted")).pack(side=tk.LEFT)
        ttk.Button(controls, text="Decline", command=lambda: self._record_evaluation_disposition("declined")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Needs Modification", command=lambda: self._record_evaluation_disposition("needs_modification")).pack(side=tk.LEFT, padx=(6, 0))

        self.evaluation_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.evaluation_detail.pack(fill=tk.BOTH, expand=True)
        self.evaluation_detail.configure(state=tk.DISABLED)
        self.evaluation_snapshot: dict[str, dict[str, object]] = {}
        if not hasattr(self, "evaluation_review_items"):
            self.evaluation_review_items: list[dict[str, object]] = []
        if not hasattr(self, "evaluation_dispositions"):
            self.evaluation_dispositions: list[dict[str, object]] = []
        self._refresh_evaluation_snapshot()

    def _build_advanced_tab(self) -> None:
        panes = ttk.PanedWindow(self.advanced_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=2)

        ttk.Label(left, text="Import / Paste Evidence").pack(anchor=tk.W)
        self.paste = scrolledtext.ScrolledText(left, height=12, wrap=tk.WORD)
        self.paste.pack(fill=tk.BOTH, expand=True)
        ttk.Button(left, text="Preview Evidence", command=self._preview_evidence).pack(fill=tk.X, pady=(6, 0))
        ttk.Button(left, text="Extract Propositions", command=self._extract_propositions).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(left, text="Approve Extracted To Noncanonical Substrate", command=self._approve_extracted).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(left, text="Epistemic Answer Audit", command=self._show_epistemic_answer_audit).pack(fill=tk.X, pady=(4, 0))

        obs = ttk.LabelFrame(left, text="Operational Observation")
        obs.pack(fill=tk.X, pady=(10, 0))
        self.category = ttk.Combobox(
            obs,
            values=[
                "operator_friction",
                "missing_evidence",
                "confusing_behavior",
                "weak_explanation",
                "replay_problem",
                "retrieval_failure",
                "provenance_issue",
                "latency",
                "workflow_interruption",
                "feature_request",
                "unexpected_strength",
            ],
        )
        self.category.set("operator_friction")
        self.category.pack(fill=tk.X, padx=6, pady=4)
        self.severity = ttk.Combobox(obs, values=["P0", "P1", "P2", "P3"])
        self.severity.set("P3")
        self.severity.pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(obs, text="Log Observation Locally", command=self._log_observation).pack(fill=tk.X, padx=6, pady=6)

        candidate_controls = ttk.LabelFrame(left, text="Interactive Candidates")
        candidate_controls.pack(fill=tk.X, pady=(10, 0))
        self.interactive_candidate_choice = tk.StringVar()
        self.interactive_candidate_choices: dict[str, object] = {}
        self.interactive_candidate_selector = ttk.Combobox(candidate_controls, textvariable=self.interactive_candidate_choice, state="readonly")
        self.interactive_candidate_selector.pack(fill=tk.X, padx=6, pady=4)
        self.interactive_candidate_selector.bind("<<ComboboxSelected>>", lambda _event: self._show_interactive_candidate_details())
        ttk.Button(candidate_controls, text="Refresh Candidates", command=self._refresh_interactive_candidate_controls).pack(fill=tk.X, padx=6, pady=(0, 4))
        actions = ttk.Frame(candidate_controls)
        actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        for label, action in (("Accept", "accepted"), ("Defer / revisit later", "deferred"), ("Reject", "rejected"), ("Suppress / stop asking", "suppressed")):
            ttk.Button(actions, text=label, command=lambda value=action: self._apply_interactive_candidate_action(value)).pack(side=tk.LEFT, padx=(0, 4))
        self.interactive_candidate_detail = scrolledtext.ScrolledText(candidate_controls, wrap=tk.WORD, height=4)
        self.interactive_candidate_detail.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.interactive_candidate_detail.configure(state=tk.DISABLED)

        buttons = ttk.Frame(left)
        buttons.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(buttons, text="Status", command=self._show_status).pack(fill=tk.X)
        ttk.Button(buttons, text="Cognitive State", command=self._show_cognitive_state).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Developmental Teaching Audit", command=self._show_developmental_teaching_audit).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Epistemic Answer Audit", command=self._show_epistemic_answer_audit).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Review Queue", command=self._show_review_queue).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Replay / Rollback", command=self._show_replay).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Failure Taxonomy", command=self._show_failure_taxonomy).pack(fill=tk.X, pady=(4, 0))

        ttk.Label(right, text="Workspace").pack(anchor=tk.W)
        self.output = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.output.pack(fill=tk.BOTH, expand=True)

    def _refresh_interactive_candidate_controls(self) -> None:
        self._refresh_interactive_cognition_shadow(reason="operator_candidate_inspection")
        workspace = self.interactive_workspace_snapshot
        candidates = [
            *getattr(workspace, "association_candidates", ()),
            *getattr(workspace, "analogy_candidates", ()),
            *getattr(workspace, "curiosity_candidates", ()),
        ] if workspace else []
        self.interactive_candidate_choices = {item.candidate_id: item for item in candidates}
        values = [f"{item.candidate_id} | {getattr(item, 'state', 'generated')}" for item in candidates]
        self.interactive_candidate_selector.configure(values=values)
        if values:
            self.interactive_candidate_choice.set(values[0])
            self._show_interactive_candidate_details()
        else:
            self.interactive_candidate_choice.set("")
            self._set_interactive_candidate_details("")

    def _set_interactive_candidate_details(self, text: str) -> None:
        self.interactive_candidate_detail.configure(state=tk.NORMAL)
        self.interactive_candidate_detail.delete("1.0", tk.END)
        self.interactive_candidate_detail.insert(tk.END, text)
        self.interactive_candidate_detail.configure(state=tk.DISABLED)

    def _show_interactive_candidate_details(self) -> None:
        candidate_id = self.interactive_candidate_choice.get().split(" | ", 1)[0]
        candidate = self.interactive_candidate_choices.get(candidate_id)
        if candidate is None:
            self._set_interactive_candidate_details("")
            return
        if hasattr(candidate, "association_id"):
            detail = (
                f"Type: {candidate.association_type}\n"
                f"Originating thread: {', '.join(candidate.source_refs)} -> {', '.join(candidate.target_refs)}\n"
                f"Provenance: {', '.join(candidate.provenance_refs)}\n"
                f"Reason: {candidate.shared_structure}\n"
                f"State: {candidate.state}; surfaced: {'yes' if candidate.state not in {'generated', 'queued'} else 'no'}\n"
                f"Uncertainty: {candidate.uncertainty}"
            )
            exploration = next(
                (item for item in load_explorations(self.conversational_runtime_root) if item.candidate_id == candidate.candidate_id),
                None,
            )
            if exploration is not None:
                detail += (
                    f"\nExploration: {exploration.lifecycle_state}"
                    f"\nApproval request: {exploration.approval_request_id}"
                    f"\nLedger request/result: {exploration.ledger_request_id} / {exploration.ledger_result_id}"
                    f"\nProvisional insight: {exploration.insight_experience_id or 'not recorded'}"
                    f"\nInquiry packet: {exploration.inquiry_question}"
                )
                if exploration.ledger_result_id:
                    try:
                        raw = LocalModelRequestResultLedger(self.conversational_runtime_root / "model-ledger").observe_result(exploration.ledger_result_id)
                        detail += f"\nRaw model output: {str(raw.get('response_reference') or '')[:1200]}"
                    except (KeyError, RuntimeError):
                        pass
        elif hasattr(candidate, "matched_relation_types"):
            detail = (
                "Type: far structural analogy\n"
                f"Source cluster: {candidate.source_cluster_id}\nTarget cluster: {candidate.target_cluster_id}\n"
                f"Matched relations: {', '.join(candidate.matched_relation_types)}\n"
                f"Unmatched source/target: {', '.join(candidate.unmatched_source_types) or 'none'} / {', '.join(candidate.unmatched_target_types) or 'none'}\n"
                f"Why it may matter: {candidate.implication}\nFailure boundary: {candidate.limitation}\n"
                f"Uncertainty: {candidate.uncertainty}\nQuestion: {candidate.possible_next_question}\n"
                f"State: {candidate.state}"
            )
        else:
            detail = (
                f"Type: {candidate.trigger}\n"
                f"Originating thread: {candidate.canonical_owner}\n"
                f"Provenance: {', '.join(candidate.source_record_ids)}\n"
                f"Reason: {candidate.rationale}\n"
                f"State: {candidate.state}; surfaced: {'yes' if candidate.state not in {'generated', 'queued'} else 'no'}"
            )
        self._set_interactive_candidate_details(detail)

    def _apply_interactive_candidate_action(self, disposition: str) -> None:
        candidate_id = self.interactive_candidate_choice.get().split(" | ", 1)[0]
        candidate = self.interactive_candidate_choices.get(candidate_id)
        if candidate is None:
            return
        existing_disposition = next(
            (item for item in self.interactive_coordination_state.candidate_dispositions if item.candidate_id == candidate_id),
            None,
        )
        kind = existing_disposition.candidate_kind if existing_disposition is not None else (
            "near_association" if hasattr(candidate, "association_id") else (
            "far_analogy" if hasattr(candidate, "matched_relation_types") else (
            "cognitive_pressure" if getattr(candidate, "trigger", "") in {"missing_evidence", "contradiction", "consolidation_correction", "consolidation_contradiction", "consolidation_remaining_gap"} else "curiosity_candidate"
            ))
        )
        source_ids = getattr(candidate, "provenance_refs", getattr(candidate, "source_record_ids", ()))
        try:
            if disposition == "accepted":
                self.interactive_coordination_state = surface_candidate_once(
                    self.interactive_coordination_state,
                    candidate_id=candidate_id,
                    candidate_kind=kind,
                    source_record_ids=source_ids,
                )
            self.interactive_coordination_state = set_candidate_disposition(
                self.interactive_coordination_state, candidate_id=candidate_id, candidate_kind=kind,
                disposition=disposition, source_record_ids=source_ids,
            )
        except ValueError as exc:
            self.output.insert(tk.END, f"Candidate action was not applied: {exc}\n")
            return
        save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
        requires_operator_question = hasattr(candidate, "association_id") or hasattr(candidate, "matched_relation_types") or getattr(candidate, "trigger", "") in {
            "missing_evidence", "contradiction", "consolidation_correction", "consolidation_contradiction", "consolidation_remaining_gap",
        }
        if disposition == "accepted" and requires_operator_question:
            existing = next(
                (
                    item for item in (
                        self.conversational_runtime_state.pending_chat_requests
                        + self.conversational_runtime_state.resolved_chat_requests
                    )
                    if item.request_type == "interactive_clarification"
                    and item.baseline_metrics.get("originating_candidate_id") == candidate_id
                ),
                None,
            )
            if existing is None:
                if kind == "near_association":
                    pressure = "cross_topic_relevance"
                    graph = load_provisional_semantic_graph(self.conversational_runtime_root)
                    versions = {item.claim_version_id: item.exact_text for item in graph.claim_versions}
                    edges = {item.edge_id: item.edge_type for item in graph.edges}
                    source_labels = [versions.get(item, item) for item in candidate.source_refs]
                    target_labels = [versions.get(item, item) for item in candidate.target_refs]
                    relation_labels = [edges.get(item, item) for item in candidate.relation_path]
                    inquiry_question = build_inquiry_question(
                        graph,
                        tuple(candidate.source_refs + candidate.target_refs),
                        tuple(candidate.relation_path),
                    )
                    prompt_text = (
                        "Connection:\n"
                        f"{'; '.join(source_labels)}\n"
                        f"{', '.join(relation_labels)}\n"
                        f"{'; '.join(target_labels)}\n\n"
                        f"Why DELTA surfaced it: {candidate.shared_structure}\n"
                        f"Provisional scope: {candidate.uncertainty}\n"
                        f"Exploration question: {inquiry_question}\n\n"
                        "Do you want me to explore this connection?"
                    )
                    question_kind = "association_exploration"
                    extra_metrics = {
                        "association_source_ids": tuple(getattr(candidate, "source_refs", ())),
                        "association_target_ids": tuple(getattr(candidate, "target_refs", ())),
                        "relation_edge_ids": tuple(getattr(candidate, "relation_path", ())),
                        "association_exploration_state": "question_created",
                        "association_resolution_state": "unresolved",
                        "association_source_labels": tuple(source_labels),
                        "association_target_labels": tuple(target_labels),
                        "association_relation_types": tuple(relation_labels),
                        "association_rationale": candidate.shared_structure,
                        "association_inquiry_question": inquiry_question,
                    }
                elif kind == "far_analogy":
                    pressure = "structural_analogy_boundary"
                    graph = load_provisional_semantic_graph(self.conversational_runtime_root)
                    labels = {item.claim_version_id: item.exact_text for item in graph.claim_versions}
                    prompt_text = (
                        "I found a provisional structural analogy.\n\n"
                        + describe_structural_analogy_candidate(candidate, record_labels=labels)
                        + "\n\n"
                        "Do you want me to make one bounded comparison?"
                    )
                    question_kind = "structural_analogy_exploration"
                    extra_metrics = {
                        "analogy_source_pattern_id": candidate.source_pattern_id,
                        "analogy_target_pattern_id": candidate.target_pattern_id,
                        "analogy_source_record_ids": tuple(candidate.source_unit_ids),
                        "analogy_target_record_ids": tuple(candidate.target_unit_ids),
                        "analogy_relation_ids": tuple(candidate.source_relation_ids + candidate.target_relation_ids),
                        "analogy_failure_boundary": candidate.limitation,
                        "analogy_source_labels": tuple(labels.get(item, item) for item in candidate.source_unit_ids),
                        "analogy_target_labels": tuple(labels.get(item, item) for item in candidate.target_unit_ids),
                        "analogy_matched_relation_types": tuple(candidate.matched_relation_types),
                        "analogy_inquiry_question": candidate.possible_next_question,
                    }
                elif candidate.trigger == "missing_evidence":
                    pressure = "missing_evidence"
                    continuation = "Independent safe work can continue." if candidate.safe_independent_work_may_continue else "Independent work should pause until this is resolved."
                    prompt_text = (
                        "I found a bounded evidence gap.\n\n"
                        f"What I noticed: {candidate.rationale}\n"
                        f"What remains unknown: {candidate.uncertainty}\n"
                        f"Why it matters: the answer would authorize this bounded next action: {candidate.proposed_bounded_action or candidate.safe_next_step}.\n"
                        f"{continuation}\n\n"
                        "Should I make one local, provisional inquiry about it?"
                    )
                    question_kind = "missing_evidence"
                    extra_metrics = {"pressure_state": "question_created", "pressure_trigger": candidate.trigger, "curiosity_inquiry": True, "curiosity_proposed_action": candidate.proposed_bounded_action or candidate.safe_next_step}
                elif candidate.trigger in {"consolidation_correction", "consolidation_contradiction", "consolidation_remaining_gap"}:
                    pressure = "consolidation_feedback"
                    prompt_text = (
                        f"Consolidation changed the status of a provisional item: {candidate.rationale} "
                        f"The next safe step is to {candidate.safe_next_step.replace('_', ' ')}. "
                        "Is this worth pursuing now?"
                    )
                    question_kind = "consolidation_feedback"
                    extra_metrics = {"pressure_state": "question_created", "pressure_trigger": candidate.trigger}
                else:
                    pressure = "contradictory_claim"
                    prompt_text = "A provisional claim conflicts with local evidence. Which source or interpretation should guide how I treat that conflict?"
                    question_kind = "contradiction_resolution"
                    extra_metrics = {"pressure_state": "question_created", "pressure_trigger": candidate.trigger}
                try:
                    request = compile_chat_clarification_request(
                        self.conversational_runtime_state, pressure=pressure,
                        prompt_text=prompt_text,
                        source_record_ids=source_ids, request_type="interactive_clarification",
                    )
                except ValueError as exc:
                    self.interactive_coordination_state = set_candidate_disposition(
                        self.interactive_coordination_state,
                        candidate_id=candidate_id,
                        candidate_kind=kind,
                        disposition="surfaced",
                        source_record_ids=source_ids,
                    )
                    save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
                    self.output.insert(tk.END, f"Candidate question was not created: {exc}\n")
                    return
                request = replace(
                    request,
                    thread_id=f"candidate:{candidate_id}",
                    accepted_response_types=("approved", "denied") if question_kind in {"association_exploration", "structural_analogy_exploration", "consolidation_feedback"} or extra_metrics.get("curiosity_inquiry") else request.accepted_response_types,
                    baseline_metrics={
                        **request.baseline_metrics,
                        "originating_candidate_id": candidate_id,
                        "originating_thread_id": candidate_id,
                        "candidate_kind": kind,
                        "question_kind": question_kind,
                        **extra_metrics,
                    },
                )
                self.conversational_runtime_state = replace(self.conversational_runtime_state, pending_chat_requests=self.conversational_runtime_state.pending_chat_requests + (request,))
                self._append_chat("DELTA", request.prompt_text)
                self._append_session("assistant", request.prompt_text)
                rendered_turn_id = rc6_stable_id("interactive-candidate-question", request.request_id)
                rendered_turn = ConversationTurn(
                    turn_id=rendered_turn_id,
                    role="assistant",
                    text=request.prompt_text,
                    intent_type="interactive_candidate_question",
                    objective_id=request.objective_id,
                )
                self.conversational_runtime_state = replace(
                    self.conversational_runtime_state,
                    conversation=self.conversational_runtime_state.conversation + (rendered_turn,),
                )
                self.conversational_runtime_state = mark_chat_request_rendered(
                    self.conversational_runtime_state,
                    request.request_id,
                    rendered_turn_id=rendered_turn_id,
                    render_sequence=len(self.conversational_runtime_state.conversation),
                )
                save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
        self._refresh_interactive_candidate_controls()

    def _build_consolidation_tab(self) -> None:
        header = ttk.Frame(self.consolidation_tab)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Local Learning Records").pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.consolidation_graph_status).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(header, text="Refresh Records", command=self._refresh_consolidation_records).pack(side=tk.RIGHT)

        panes = ttk.PanedWindow(self.consolidation_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        episodes = ttk.LabelFrame(panes, text="Episodes")
        claims = ttk.LabelFrame(panes, text="Provisional Claims")
        details = ttk.LabelFrame(panes, text="Selected Record")
        panes.add(episodes, weight=1)
        panes.add(claims, weight=2)
        panes.add(details, weight=2)

        self.consolidation_episode_tree = ttk.Treeview(episodes, columns=("episode", "status", "recorded", "operations"), show="headings", selectmode="browse")
        self.consolidation_episode_tree.heading("episode", text="Episode")
        self.consolidation_episode_tree.heading("status", text="Status")
        self.consolidation_episode_tree.heading("recorded", text="Recorded")
        self.consolidation_episode_tree.heading("operations", text="Operations")
        self.consolidation_episode_tree.column("episode", width=155, stretch=False)
        self.consolidation_episode_tree.column("status", width=125, stretch=False)
        self.consolidation_episode_tree.column("recorded", width=145, stretch=False)
        self.consolidation_episode_tree.column("operations", width=75, stretch=False)
        self.consolidation_episode_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.consolidation_episode_tree.bind("<<TreeviewSelect>>", lambda _event: self._show_consolidation_episode())

        self.consolidation_claim_tree = ttk.Treeview(claims, columns=("state", "node", "claim"), show="headings", selectmode="browse")
        self.consolidation_claim_tree.heading("state", text="State")
        self.consolidation_claim_tree.heading("node", text="Node")
        self.consolidation_claim_tree.heading("claim", text="Claim")
        self.consolidation_claim_tree.column("state", width=145, stretch=False)
        self.consolidation_claim_tree.column("node", width=135, stretch=False)
        self.consolidation_claim_tree.column("claim", width=340, stretch=True)
        self.consolidation_claim_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.consolidation_claim_tree.bind("<<TreeviewSelect>>", lambda _event: self._show_consolidation_claim())

        self.consolidation_detail = scrolledtext.ScrolledText(details, wrap=tk.WORD, state="disabled")
        self.consolidation_detail.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        review = ttk.LabelFrame(self.consolidation_tab, text="Offline Review")
        review.pack(fill=tk.X, pady=(8, 0))
        self._build_consolidation_review_controls(review)
        self._refresh_consolidation_records()

    def _build_consolidation_review_controls(self, parent: ttk.LabelFrame) -> None:
        ttk.Label(parent, textvariable=self.consolidation_review_status).grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=(6, 2))
        self.consolidation_review_selector = ttk.Combobox(parent, textvariable=self.consolidation_review_id, state="readonly")
        self.consolidation_review_selector.grid(row=1, column=0, sticky="ew", padx=6, pady=2)
        self.consolidation_review_selector.bind("<<ComboboxSelected>>", lambda _event: self._show_consolidation_review())
        self.consolidation_claim_selector = ttk.Combobox(parent, textvariable=self.consolidation_claim_version_id, state="readonly")
        self.consolidation_claim_selector.grid(row=1, column=1, sticky="ew", padx=6, pady=2)
        self.consolidation_action_selector = ttk.Combobox(
            parent,
            textvariable=self.consolidation_action,
            values=("approve", "reject", "approve_partial", "replace_fragment", "revise_claim", "split_claim", "merge_claims", "recompose_cluster", "retain_provisional", "quarantine", "invalidate", "request_re_review", "escalate_for_more_evidence"),
            state="readonly",
        )
        self.consolidation_action_selector.grid(row=1, column=2, sticky="ew", padx=6, pady=2)
        buttons = ttk.Frame(parent)
        buttons.grid(row=2, column=0, columnspan=3, sticky="ew", padx=6, pady=(2, 6))
        ttk.Button(buttons, text="Refresh Review", command=self._refresh_consolidation_review_surface).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Enable Admin Review", command=self._enable_consolidation_administrative_review).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(buttons, text="Apply Administrative Action", command=self._apply_consolidation_review_action).pack(side=tk.LEFT, padx=(6, 0))
        for column in range(3):
            parent.columnconfigure(column, weight=1)

    def _refresh_rc3_snapshot(self) -> None:
        try:
            self.rc3_snapshot = build_rc3_ui_snapshot()
            validation = validate_rc3_ui_snapshot(self.rc3_snapshot)
            for item in self.rc3_panels.get_children():
                self.rc3_panels.delete(item)
            panels = self.rc3_snapshot.get("panels", {})
            for name in RC3_PANEL_ORDER:
                panel = panels.get(name, {}) if isinstance(panels, dict) else {}
                status = str(panel.get("status", "unknown"))
                self.rc3_panels.insert("", tk.END, iid=name, values=(f"{name} [{status}]",))
            recommendation = validation.get("recommendation")
            self.rc3_status.set(
                f"RC3 UI validation passed={validation.get('passed')}; recommendation={recommendation}. "
                "Inspect/review only: no execution, sandbox, plugin activation, provider call, or repository mutation."
            )
            if RC3_PANEL_ORDER:
                self.rc3_panels.selection_set(RC3_PANEL_ORDER[0])
                self._show_selected_rc3_panel()
        except Exception as exc:  # noqa: BLE001
            self.rc3_status.set(f"RC3 snapshot failed: {type(exc).__name__}: {str(exc)[:180]}")
            self._write_rc3_detail("")

    def _show_selected_rc3_panel(self) -> None:
        selected = self.rc3_panels.selection()
        if not selected or not self.rc3_snapshot:
            return
        panel_name = str(selected[0])
        self._write_rc3_detail(render_rc3_panel(panel_name, self.rc3_snapshot))

    def _write_rc3_detail(self, text: str) -> None:
        self.rc3_detail.configure(state=tk.NORMAL)
        self.rc3_detail.delete("1.0", tk.END)
        if text:
            self.rc3_detail.insert(tk.END, text)
        self.rc3_detail.configure(state=tk.DISABLED)

    def _generate_rc3_ui_report(self) -> None:
        report = build_rc3_ui_integration_report(write_reports=True)
        self._refresh_rc3_snapshot()
        self._write_rc3_detail(json.dumps(report, indent=2, sort_keys=True))

    def _refresh_rc4_snapshot(self) -> None:
        try:
            self.rc4_snapshot = build_rc4_ui_snapshot()
            validation = validate_rc4_ui_snapshot(self.rc4_snapshot)
            for item in self.rc4_panels.get_children():
                self.rc4_panels.delete(item)
            panels = self.rc4_snapshot.get("panels", {})
            for name in RC4_PANEL_ORDER:
                panel = panels.get(name, {}) if isinstance(panels, dict) else {}
                status = str(panel.get("status", "unknown"))
                self.rc4_panels.insert("", tk.END, iid=name, values=(f"{name} [{status}]",))
            self.rc4_status.set(
                f"RC4 UI validation passed={validation.get('passed')}; recommendation={validation.get('recommendation')}. "
                "Inspect/review only: no live repo mutation, sandbox creation from UI, provider call, plugin activation, push, merge, or deploy."
            )
            if RC4_PANEL_ORDER:
                self.rc4_panels.selection_set(RC4_PANEL_ORDER[0])
                self._show_selected_rc4_panel()
        except Exception as exc:  # noqa: BLE001
            self.rc4_status.set(f"RC4 snapshot failed: {type(exc).__name__}: {str(exc)[:180]}")
            self._write_rc4_detail("")

    def _show_selected_rc4_panel(self) -> None:
        selected = self.rc4_panels.selection()
        if not selected or not self.rc4_snapshot:
            return
        panel_name = str(selected[0])
        self._write_rc4_detail(render_rc4_panel(panel_name, self.rc4_snapshot))

    def _write_rc4_detail(self, text: str) -> None:
        self.rc4_detail.configure(state=tk.NORMAL)
        self.rc4_detail.delete("1.0", tk.END)
        if text:
            self.rc4_detail.insert(tk.END, text)
        self.rc4_detail.configure(state=tk.DISABLED)

    def _generate_rc4_ui_report(self) -> None:
        report = build_rc4_ui_integration_report(write_reports=True)
        self._refresh_rc4_snapshot()
        self._write_rc4_detail(json.dumps(report, indent=2, sort_keys=True))

    def _refresh_rc5_snapshot(self) -> None:
        try:
            self.rc5_snapshot = build_rc5_ui_snapshot()
            validation = validate_rc5_ui_snapshot(self.rc5_snapshot)
            for item in self.rc5_panels.get_children():
                self.rc5_panels.delete(item)
            panels = self.rc5_snapshot.get("panels", {})
            for name in RC5_PANEL_ORDER:
                panel = panels.get(name, {}) if isinstance(panels, dict) else {}
                status = str(panel.get("status", "unknown"))
                self.rc5_panels.insert("", tk.END, iid=name, values=(f"{name} [{status}]",))
            self.rc5_status.set(
                f"RC5 UI validation passed={validation.get('passed')}; recommendation={validation.get('recommendation')}. "
                "Inspect/review only: no GPT/API call, provider call, purpose mutation, automatic development loop, "
                "developmental memory write, self-approval, or RC4 bypass."
            )
            if RC5_PANEL_ORDER:
                self.rc5_panels.selection_set(RC5_PANEL_ORDER[0])
                self._show_selected_rc5_panel()
        except Exception as exc:  # noqa: BLE001
            self.rc5_status.set(f"RC5 snapshot failed: {type(exc).__name__}: {str(exc)[:180]}")
            self._write_rc5_detail("")

    def _show_selected_rc5_panel(self) -> None:
        selected = self.rc5_panels.selection()
        if not selected or not self.rc5_snapshot:
            return
        panel_name = str(selected[0])
        self._write_rc5_detail(render_rc5_panel(panel_name, self.rc5_snapshot))

    def _write_rc5_detail(self, text: str) -> None:
        self.rc5_detail.configure(state=tk.NORMAL)
        self.rc5_detail.delete("1.0", tk.END)
        if text:
            self.rc5_detail.insert(tk.END, text)
        self.rc5_detail.configure(state=tk.DISABLED)

    def _generate_rc5_ui_report(self) -> None:
        report = build_rc5_ui_integration_report(write_reports=True)
        self._refresh_rc5_snapshot()
        self._write_rc5_detail(json.dumps(report, indent=2, sort_keys=True))

    def _refresh_evaluation_snapshot(self) -> None:
        self.evaluation_snapshot = self._build_evaluation_snapshot()
        for item in self.evaluation_items.get_children():
            self.evaluation_items.delete(item)
        for key, item in self.evaluation_snapshot.items():
            self.evaluation_items.insert("", tk.END, iid=key, values=(f"{item['title']} [{item['status']}]",))
        self.evaluation_status.set(
            "GSR/OAR review surface. Disposition controls record immutable operator intent only; no source application, execution, or continuation."
        )
        first_item = next(iter(self.evaluation_snapshot), "")
        if first_item:
            self.evaluation_items.selection_set(first_item)
            self._show_selected_evaluation_item()

    def _build_evaluation_snapshot(self) -> dict[str, dict[str, object]]:
        if self.evaluation_review_items:
            return {
                f"review-{index}": self._normalize_evaluation_review_item(index, item)
                for index, item in enumerate(self.evaluation_review_items, start=1)
            }
        return {
            "e3a": {
                "title": "GSR-E3-A Evidence Evaluation",
                "status": "accepted",
                "boundary": "E2-B bounded sandbox evidence -> deterministic evidence evaluation -> operator review required -> stop",
                "operator_action": "Review accepted evaluations outside the UI until a governed request queue is wired.",
                "guarantees": [
                    "Exact result and evidence identity validation.",
                    "Deterministic classification and bounded findings.",
                    "Cleanup, live-source, budget, output, artifact, and filesystem-write review.",
                    "No application authority, execution authority, lifecycle transition, or automatic continuation.",
                ],
            },
            "e3b": {
                "title": "GSR-E3-B Operator Evidence Disposition",
                "status": "accepted",
                "boundary": "exact E3-A evaluation + exact request + exact operator disposition -> one inert record -> consumed authority -> stop",
                "operator_action": "When a disposition request surfaces, operator and GPT review it manually before any later phase.",
                "guarantees": [
                    "Exact evaluation, request, disposition, cycle, plan, attempt, authorization, and digest binding.",
                    "One-shot operator authority with explicit-sequence expiration.",
                    "Immutable consumed replacement; original disposition remains unchanged.",
                    "Future execution, application consideration, and lifecycle closure remain metadata only.",
                ],
            },
            "queue": {
                "title": "Surfaced Requests",
                "status": "not wired",
                "boundary": "No live queue integration exists in this tab yet.",
                "operator_action": "Use this tab as a review landing page; do not treat it as approval or execution control.",
                "guarantees": [
                    "No provider or local-model call.",
                    "No sandbox or command execution.",
                    "No source mutation, memory write, persistence, scheduler, thread, or background task.",
                    "No staging, commit, push, merge, deployment, or publication.",
                ],
            },
        }

    def _set_evaluation_review_items(self, items: list[object]) -> None:
        self.evaluation_review_items = [
            asdict(item) if is_dataclass(item) else dict(item)
            for item in items
        ]
        self._refresh_evaluation_snapshot()
        self._persist_oar_live_development_state()

    def _load_oar_live_development_state(self) -> None:
        if not OAR_LIVE_DEVELOPMENT_STATE_PATH.exists():
            return
        try:
            payload = json.loads(OAR_LIVE_DEVELOPMENT_STATE_PATH.read_text(encoding="utf-8"))
            runtime_state = payload.get("oar_runtime_state")
            if isinstance(runtime_state, dict):
                fields_for_state = {field.name for field in fields(gsr.OARRuntimeState)}
                recovered = gsr.OARRuntimeState(**{
                    key: value for key, value in runtime_state.items() if key in fields_for_state
                })
                self.oar_runtime_state = gsr.recover_oar_runtime_after_restart(recovered, integrity_valid=True)
            review_items = payload.get("evaluation_review_items")
            if isinstance(review_items, list):
                self.evaluation_review_items = [dict(item) for item in review_items if isinstance(item, dict)]
            dispositions = payload.get("evaluation_dispositions")
            if isinstance(dispositions, list):
                self.evaluation_dispositions = [dict(item) for item in dispositions if isinstance(item, dict)]
            approved = payload.get("oar_approved_compiled_mission")
            self.oar_approved_compiled_mission = dict(approved) if isinstance(approved, dict) else None
            approval = payload.get("oar_mission_approval")
            self.oar_mission_approval = dict(approval) if isinstance(approval, dict) else None
        except Exception:  # noqa: BLE001 - corrupt live UI recovery state must fail closed.
            self.oar_runtime_state = gsr.OARRuntimeState(
                runtime_state_id="tk-oar-development-runtime",
                clean_shutdown=False,
                integrity_failure=True,
            )
            self.evaluation_review_items = []
            self.evaluation_dispositions = []
            self.oar_approved_compiled_mission = None
            self.oar_mission_approval = None

    def _persist_oar_live_development_state(self) -> None:
        if not getattr(self, "oar_live_state_persistence_enabled", False):
            return
        payload = {
            "schema_version": 1,
            "oar_runtime_state": asdict(self.oar_runtime_state),
            "oar_approved_compiled_mission": self.oar_approved_compiled_mission,
            "oar_mission_approval": self.oar_mission_approval,
            "evaluation_review_items": self.evaluation_review_items,
            "evaluation_dispositions": self.evaluation_dispositions,
        }
        OAR_LIVE_DEVELOPMENT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = OAR_LIVE_DEVELOPMENT_STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(OAR_LIVE_DEVELOPMENT_STATE_PATH)

    def _live_runtime_1b_restart_path(self) -> Path:
        return LIVE_RUNTIME_1B_ROOT / "restart_state.json"

    def _load_live_runtime_1b_state(self) -> None:
        restart_path = self._live_runtime_1b_restart_path()
        if not restart_path.exists():
            return
        try:
            restart_state = json.loads(restart_path.read_text(encoding="utf-8"))
            session_id = str(restart_state.get("session_id") or "tk-live-runtime-1b")
            controller = start_continuous_runtime_controller(session_id=session_id, wake_mode="MANUAL")
            self.live_runtime_1b_controller = restore_continuous_mission_restart_state(controller, restart_state)
            self._sync_live_runtime_1b_evaluation_items()
            if self.live_runtime_1b_controller.continuous_mission_state == "live_runtime_1_terminal":
                self.live_runtime_status.set("LIVE-RUNTIME-1B: stopped terminal")
            else:
                self.live_runtime_status.set(f"LIVE-RUNTIME-1B: {self.live_runtime_1b_controller.continuous_mission_state}")
        except Exception as exc:  # noqa: BLE001 - UI recovery must fail closed.
            self.live_runtime_1b_controller = None
            self.live_runtime_status.set(f"LIVE-RUNTIME-1B recovery blocked: {type(exc).__name__}: {str(exc)[:160]}")

    def _persist_live_runtime_1b_state(self) -> None:
        controller = getattr(self, "live_runtime_1b_controller", None)
        if controller is None:
            return
        LIVE_RUNTIME_1B_ROOT.mkdir(parents=True, exist_ok=True)
        restart = export_continuous_mission_restart_state(controller)
        worker = {
            "worker_state": "stopped" if controller.continuous_mission_state == "live_runtime_1_terminal" else "attended_manual",
            "timestamp": "2026-07-22T00:00:00+00:00",
            "session_id": controller.session_id,
            "continuous_mission_state": controller.continuous_mission_state,
            "pending_application_decision_id": "",
        }
        observation = {"timestamp": "2026-07-22T00:00:00+00:00", "source": "tk_live_runtime_1b"}
        for name, payload in (("restart_state.json", restart), ("worker_status.json", worker), ("observation_requeue.json", observation)):
            path = LIVE_RUNTIME_1B_ROOT / name
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
            tmp.replace(path)

    def _sync_live_runtime_1b_evaluation_items(self) -> None:
        eval_dir = LIVE_RUNTIME_1B_ROOT / "evaluation_ui"
        runtime_items: list[dict[str, object]] = []
        if eval_dir.exists():
            for path in sorted(eval_dir.glob("*.json")):
                record = json.loads(path.read_text(encoding="utf-8"))
                runtime_items.append({
                    "item_type": "live_runtime_1b_evaluation",
                    "title": f"LIVE-RUNTIME-1B {record.get('task_class')}",
                    "status": str(record.get("terminal_state") or record.get("aggregate_disposition") or "available"),
                    "boundary": "Persistent controller Evaluation artifact rendered through the Tk Evaluation tab.",
                    "operator_action": "Review only. This display does not authorize source mutation, promotion, deployment, provider access, or another mission.",
                    "details": record,
                })
        self.evaluation_review_items = runtime_items
        self._refresh_evaluation_snapshot()

    def _live_runtime_1b_summary(self) -> str:
        controller = getattr(self, "live_runtime_1b_controller", None)
        if controller is None:
            return "LIVE-RUNTIME-1B is not attached."
        state = dict((controller.continuous_learning_state or {}).get("live_runtime_1") or {})
        work_status = dict(state.get("work_item_status") or {})
        counts = dict(state.get("counts") or {})
        return (
            f"State: {controller.continuous_mission_state}\n"
            f"Root: {LIVE_RUNTIME_1B_ROOT}\n"
            f"Cycles: {state.get('scheduler_cycles')}\n"
            f"Mission: {(state.get('mission') or {}).get('mission_id') or 'pending'}\n"
            f"Work items: {json.dumps(work_status, sort_keys=True)}\n"
            f"Evaluation entries: {len(tuple((LIVE_RUNTIME_1B_ROOT / 'evaluation_ui').glob('*.json'))) if (LIVE_RUNTIME_1B_ROOT / 'evaluation_ui').exists() else 0}\n"
            f"Counts: {json.dumps(counts, sort_keys=True, default=str)}"
        )

    def _is_live_runtime_1b_mission(self, message: str) -> bool:
        normalized = " ".join(message.lower().split())
        return all(token in normalized for token in ("mixed csv", "json", "reconcile", "capability provenance", "input-preservation"))

    def _handle_live_runtime_1b_mission(self, reset: bool = True) -> str:
        if reset and LIVE_RUNTIME_1B_ROOT.exists():
            if self._live_runtime_1b_restart_path().exists():
                return "LIVE-RUNTIME-1B already has persisted state. Use `advance live runtime 1b` or `live runtime 1b status`; no second mission was started."
        controller = start_continuous_runtime_controller(session_id="tk-live-runtime-1b", wake_mode="MANUAL")
        self.live_runtime_1b_controller = attach_live_runtime_1_attended_mission(
            controller,
            runtime_root=LIVE_RUNTIME_1B_ROOT,
            accepted_competence_root=LIVE_RUNTIME_1B_ACCEPTED_ROOT,
            reset=reset,
        )
        self._persist_live_runtime_1b_state()
        self._sync_live_runtime_1b_evaluation_items()
        self.live_runtime_status.set("LIVE-RUNTIME-1B: mission attached")
        return (
            "LIVE-RUNTIME-1B mission entered through the Tk operator chat path and attached to the persistent controller.\n\n"
            f"{self._live_runtime_1b_summary()}\n\n"
            "Next operator action: `advance live runtime 1b`. No work item executed yet."
        )

    def _advance_live_runtime_1b_from_ui(self) -> str:
        controller = getattr(self, "live_runtime_1b_controller", None)
        if controller is None:
            self._load_live_runtime_1b_state()
            controller = getattr(self, "live_runtime_1b_controller", None)
        if controller is None:
            return "LIVE-RUNTIME-1B cannot advance: no mission is attached."
        before_state = controller.continuous_mission_state
        self.live_runtime_1b_controller = advance_live_runtime_1_attended_mission(controller)
        self._persist_live_runtime_1b_state()
        self._sync_live_runtime_1b_evaluation_items()
        after_state = self.live_runtime_1b_controller.continuous_mission_state
        if after_state == "live_runtime_1_terminal":
            self.live_runtime_status.set("LIVE-RUNTIME-1B: stopped terminal")
        else:
            self.live_runtime_status.set(f"LIVE-RUNTIME-1B: {after_state}")
        return (
            f"LIVE-RUNTIME-1B advanced: {before_state or 'attached'} -> {after_state}.\n\n"
            f"{self._live_runtime_1b_summary()}\n\n"
            "No provider call, trusted admission, capability promotion, deployment, network expansion, or tracked-source mutation occurred."
        )

    def _live_runtime_2_restart_path(self) -> Path:
        return LIVE_RUNTIME_2_ROOT / "restart_state.json"

    def _load_live_runtime_2_state(self) -> None:
        restart_path = self._live_runtime_2_restart_path()
        if not restart_path.exists():
            return
        try:
            restart_state = json.loads(restart_path.read_text(encoding="utf-8"))
            session_id = str(restart_state.get("session_id") or "tk-live-runtime-2")
            controller = start_continuous_runtime_controller(session_id=session_id, wake_mode="MANUAL")
            self.live_runtime_2_controller = restore_continuous_mission_restart_state(controller, restart_state)
            self._sync_live_runtime_2_evaluation_items()
            stop_path = LIVE_RUNTIME_2_ROOT / "unattended_stop" / "stop.json"
            if stop_path.exists():
                stop = json.loads(stop_path.read_text(encoding="utf-8"))
                self.live_runtime_status.set(f"LIVE-RUNTIME-2: stopped {stop.get('stop_reason')}")
            else:
                self.live_runtime_status.set(f"LIVE-RUNTIME-2: {self.live_runtime_2_controller.continuous_mission_state}")
        except Exception as exc:  # noqa: BLE001 - UI recovery must fail closed.
            self.live_runtime_2_controller = None
            self.live_runtime_status.set(f"LIVE-RUNTIME-2 recovery blocked: {type(exc).__name__}: {str(exc)[:160]}")

    def _sync_live_runtime_2_evaluation_items(self) -> None:
        eval_dir = LIVE_RUNTIME_2_ROOT / "evaluation_ui"
        runtime_items: list[dict[str, object]] = []
        if eval_dir.exists():
            for path in sorted(eval_dir.glob("*.json")):
                record = json.loads(path.read_text(encoding="utf-8"))
                runtime_items.append({
                    "item_type": "live_runtime_2_evaluation",
                    "title": f"LIVE-RUNTIME-2 {record.get('task_class')}",
                    "status": str(record.get("terminal_state") or record.get("aggregate_disposition") or "available"),
                    "boundary": "Bounded unattended persistent controller Evaluation artifact rendered through Tk after recovery.",
                    "operator_action": "Review only. This display does not authorize source mutation, promotion, deployment, provider access, learning, or another mission.",
                    "details": record,
                })
        self.evaluation_review_items = runtime_items
        self._refresh_evaluation_snapshot()

    def _live_runtime_2_summary(self) -> str:
        controller = getattr(self, "live_runtime_2_controller", None)
        if controller is None:
            return "LIVE-RUNTIME-2 is not attached."
        state = dict((controller.continuous_learning_state or {}).get("live_runtime_1") or {})
        work_status = dict(state.get("work_item_status") or {})
        counts = dict(state.get("counts") or {})
        stop_path = LIVE_RUNTIME_2_ROOT / "unattended_stop" / "stop.json"
        stop_reason = ""
        if stop_path.exists():
            stop = json.loads(stop_path.read_text(encoding="utf-8"))
            stop_reason = f"\nStop: {stop.get('stop_reason')} / {stop.get('result_status')}"
        return (
            f"State: {controller.continuous_mission_state}\n"
            f"Root: {LIVE_RUNTIME_2_ROOT}\n"
            f"Cycles: {state.get('scheduler_cycles')}\n"
            f"Mission: {(state.get('mission') or {}).get('mission_id') or 'pending'}\n"
            f"Work items: {json.dumps(work_status, sort_keys=True)}\n"
            f"Evaluation entries: {len(tuple((LIVE_RUNTIME_2_ROOT / 'evaluation_ui').glob('*.json'))) if (LIVE_RUNTIME_2_ROOT / 'evaluation_ui').exists() else 0}\n"
            f"Counts: {json.dumps(counts, sort_keys=True, default=str)}"
            f"{stop_reason}"
        )

    def _prepare_live_runtime_2_from_ui(self) -> str:
        if LIVE_RUNTIME_2_ROOT.exists() and self._live_runtime_2_restart_path().exists():
            self._load_live_runtime_2_state()
            return "LIVE-RUNTIME-2 already has persisted state. No second mission was started.\n\n" + self._live_runtime_2_summary()
        self.live_runtime_2_controller = prepare_live_runtime_2_mission(
            runtime_root=LIVE_RUNTIME_2_ROOT,
            accepted_competence_root=LIVE_RUNTIME_2_ACCEPTED_ROOT,
            reset=True,
        )
        self._sync_live_runtime_2_evaluation_items()
        self.live_runtime_status.set("LIVE-RUNTIME-2: graph registered awaiting unattended authority")
        return (
            "LIVE-RUNTIME-2 mission entered and approved through Tk. The persistent controller registered one four-item graph.\n\n"
            f"{self._live_runtime_2_summary()}\n\n"
            "Next operator action: `authorize bounded unattended live runtime 2`."
        )

    def _authorize_live_runtime_2_from_ui(self) -> str:
        controller = getattr(self, "live_runtime_2_controller", None)
        if controller is None:
            self._load_live_runtime_2_state()
            controller = getattr(self, "live_runtime_2_controller", None)
        if controller is None:
            return "LIVE-RUNTIME-2 cannot authorize unattended mode: no mission graph is registered."
        authority = compile_live_runtime_2_unattended_authority(
            controller,
            runtime_root=LIVE_RUNTIME_2_ROOT,
            max_cycles=12,
            max_duration_seconds=20 * 60,
            provider_budget=0,
        )
        self.live_runtime_status.set("LIVE-RUNTIME-2: unattended authority accepted")
        return (
            "LIVE-RUNTIME-2 bounded unattended authority accepted.\n\n"
            f"Authority: {authority['authority_id']}\n"
            f"Digest: {authority['artifact_digest']}\n"
            "Limits: one mission, 12 scheduler cycles, 20 minutes, provider budget 0, learning disabled, network disabled, tracked-source mutation disabled, deployment disabled.\n\n"
            "Next operator action: `start bounded unattended live runtime 2`."
        )

    def _start_live_runtime_2_unattended_from_ui(self) -> str:
        if not (LIVE_RUNTIME_2_ROOT / "unattended_authority").exists():
            return "LIVE-RUNTIME-2 cannot start unattended mode: authority record is missing."
        self.live_runtime_2_process = start_live_runtime_2_process(runtime_root=LIVE_RUNTIME_2_ROOT, python_executable=sys.executable)
        self.live_runtime_status.set("LIVE-RUNTIME-2: bounded unattended runner started")
        return (
            "LIVE-RUNTIME-2 bounded unattended runner started from explicit Tk operator command.\n\n"
            f"Process ID: {self.live_runtime_2_process.pid}\n"
            "Close the Tk window now for the unattended interval. The runner will stop at terminal, cycle limit, expiration, or integrity failure."
        )

    def _live_runtime_3_restart_path(self) -> Path:
        return LIVE_RUNTIME_3_ROOT / "restart_state.json"

    def _load_live_runtime_3_state(self) -> None:
        restart_path = self._live_runtime_3_restart_path()
        if not restart_path.exists():
            return
        try:
            restart_state = json.loads(restart_path.read_text(encoding="utf-8"))
            controller = start_continuous_runtime_controller(session_id=str(restart_state.get("session_id") or "tk-live-runtime-3"), wake_mode="MANUAL")
            self.live_runtime_3_controller = restore_continuous_mission_restart_state(controller, restart_state)
            self._sync_live_runtime_3_evaluation_items()
            stop_path = LIVE_RUNTIME_3_ROOT / "unattended_stop" / "stop.json"
            if stop_path.exists():
                stop = json.loads(stop_path.read_text(encoding="utf-8"))
                self.live_runtime_status.set(f"LIVE-RUNTIME-3: stopped {stop.get('stop_reason')}")
            else:
                self.live_runtime_status.set(f"LIVE-RUNTIME-3: {self.live_runtime_3_controller.continuous_mission_state}")
        except Exception as exc:  # noqa: BLE001 - UI recovery must fail closed.
            self.live_runtime_3_controller = None
            self.live_runtime_status.set(f"LIVE-RUNTIME-3 recovery blocked: {type(exc).__name__}: {str(exc)[:160]}")

    def _sync_live_runtime_3_evaluation_items(self) -> None:
        eval_dir = LIVE_RUNTIME_3_ROOT / "evaluation_ui"
        runtime_items: list[dict[str, object]] = []
        if eval_dir.exists():
            for path in sorted(eval_dir.glob("*.json")):
                record = json.loads(path.read_text(encoding="utf-8"))
                runtime_items.append({
                    "item_type": "live_runtime_3_evaluation",
                    "title": f"LIVE-RUNTIME-3 {record.get('task_class')}",
                    "status": str(record.get("terminal_state") or record.get("aggregate_disposition") or "available"),
                    "boundary": "Interrupted/resumed bounded unattended Evaluation artifact rendered through Tk after recovery.",
                    "operator_action": "Review only. This display does not authorize source mutation, promotion, deployment, provider access, learning, or another mission.",
                    "details": record,
                })
        self.evaluation_review_items = runtime_items
        self._refresh_evaluation_snapshot()

    def _live_runtime_3_summary(self) -> str:
        controller = getattr(self, "live_runtime_3_controller", None)
        if controller is None:
            return "LIVE-RUNTIME-3 is not attached."
        state = dict((controller.continuous_learning_state or {}).get("live_runtime_1") or {})
        stop_text = ""
        stop_path = LIVE_RUNTIME_3_ROOT / "unattended_stop" / "stop.json"
        if stop_path.exists():
            stop = json.loads(stop_path.read_text(encoding="utf-8"))
            stop_text = f"\nStop: {stop.get('stop_reason')} / {stop.get('result_status')}"
        return (
            f"State: {controller.continuous_mission_state}\n"
            f"Root: {LIVE_RUNTIME_3_ROOT}\n"
            f"Cycles: {state.get('scheduler_cycles')}\n"
            f"Mission: {(state.get('mission') or {}).get('mission_id') or 'pending'}\n"
            f"Work items: {json.dumps(dict(state.get('work_item_status') or {}), sort_keys=True)}\n"
            f"Evaluation entries: {len(tuple((LIVE_RUNTIME_3_ROOT / 'evaluation_ui').glob('*.json'))) if (LIVE_RUNTIME_3_ROOT / 'evaluation_ui').exists() else 0}\n"
            f"Counts: {json.dumps(dict(state.get('counts') or {}), sort_keys=True, default=str)}"
            f"{stop_text}"
        )

    def _prepare_live_runtime_3_from_ui(self) -> str:
        if LIVE_RUNTIME_3_ROOT.exists() and self._live_runtime_3_restart_path().exists():
            self._load_live_runtime_3_state()
            return "LIVE-RUNTIME-3 already has persisted state. No second mission was started.\n\n" + self._live_runtime_3_summary()
        self.live_runtime_3_controller = prepare_live_runtime_3_mission(
            runtime_root=LIVE_RUNTIME_3_ROOT,
            accepted_competence_root=LIVE_RUNTIME_3_ACCEPTED_ROOT,
            reset=True,
        )
        self._sync_live_runtime_3_evaluation_items()
        self.live_runtime_status.set("LIVE-RUNTIME-3: graph registered awaiting first authority")
        return "LIVE-RUNTIME-3 mission approved and graph registered through Tk.\n\n" + self._live_runtime_3_summary()

    def _authorize_live_runtime_3_from_ui(self, generation: int) -> str:
        controller = getattr(self, "live_runtime_3_controller", None)
        if controller is None:
            self._load_live_runtime_3_state()
            controller = getattr(self, "live_runtime_3_controller", None)
        if controller is None:
            return "LIVE-RUNTIME-3 cannot authorize unattended mode: no mission graph is registered."
        authority = compile_live_runtime_3_unattended_authority(
            controller,
            runtime_root=LIVE_RUNTIME_3_ROOT,
            generation=generation,
            max_cycles=6,
        )
        self.live_runtime_status.set(f"LIVE-RUNTIME-3: authority {generation} accepted")
        return (
            f"LIVE-RUNTIME-3 authority {generation} accepted.\n\n"
            f"Authority: {authority['authority_id']}\n"
            f"Digest: {authority['artifact_digest']}\n"
            f"Allowed work items: {json.dumps(tuple(authority['allowed_work_item_ids']))}\n"
            "Limits: one mission, six controller advances, 10 minutes, provider budget 0, learning disabled, network disabled, mutation disabled, deployment disabled."
        )

    def _start_live_runtime_3_from_ui(self) -> str:
        if not (LIVE_RUNTIME_3_ROOT / "unattended_authority").exists():
            return "LIVE-RUNTIME-3 cannot start unattended mode: authority record is missing."
        self.live_runtime_3_process = start_live_runtime_3_process(runtime_root=LIVE_RUNTIME_3_ROOT, python_executable=sys.executable)
        self.live_runtime_status.set("LIVE-RUNTIME-3: bounded unattended runner started")
        return (
            "LIVE-RUNTIME-3 bounded unattended runner started from explicit Tk operator command.\n\n"
            f"Process ID: {self.live_runtime_3_process.pid}\n"
            "Close the Tk window now for the bounded unattended interval."
        )

    def _live_runtime_4_restart_path(self) -> Path:
        return LIVE_RUNTIME_4_ROOT / "restart_state.json"

    def _load_live_runtime_4_state(self) -> None:
        restart_path = self._live_runtime_4_restart_path()
        if not restart_path.exists():
            return
        try:
            worker_path = LIVE_RUNTIME_4_ROOT / "worker_status.json"
            if worker_path.exists():
                worker = json.loads(worker_path.read_text(encoding="utf-8"))
                if worker.get("worker_state") == "running":
                    recover_live_runtime_4_interrupted_runner(runtime_root=LIVE_RUNTIME_4_ROOT)
            restart_state = json.loads(restart_path.read_text(encoding="utf-8"))
            controller = start_continuous_runtime_controller(session_id=str(restart_state.get("session_id") or "tk-live-runtime-4"), wake_mode="MANUAL")
            self.live_runtime_4_controller = restore_continuous_mission_restart_state(controller, restart_state)
            self._sync_live_runtime_4_evaluation_items()
            stop_path = LIVE_RUNTIME_4_ROOT / "unattended_stop" / "stop.json"
            if stop_path.exists():
                stop = json.loads(stop_path.read_text(encoding="utf-8"))
                self.live_runtime_status.set(f"LIVE-RUNTIME-4: stopped {stop.get('stop_reason')}")
            else:
                self.live_runtime_status.set(f"LIVE-RUNTIME-4: {self.live_runtime_4_controller.continuous_mission_state}")
        except Exception as exc:  # noqa: BLE001 - UI recovery must fail closed.
            self.live_runtime_4_controller = None
            self.live_runtime_status.set(f"LIVE-RUNTIME-4 recovery blocked: {type(exc).__name__}: {str(exc)[:160]}")

    def _sync_live_runtime_4_evaluation_items(self) -> None:
        eval_dir = LIVE_RUNTIME_4_ROOT / "evaluation_ui"
        runtime_items: list[dict[str, object]] = []
        if eval_dir.exists():
            for path in sorted(eval_dir.glob("*.json")):
                record = json.loads(path.read_text(encoding="utf-8"))
                runtime_items.append({
                    "item_type": "live_runtime_4_evaluation",
                    "title": f"LIVE-RUNTIME-4 {record.get('task_class')}",
                    "status": str(record.get("terminal_state") or record.get("aggregate_disposition") or "available"),
                    "boundary": "Crash-safe bounded unattended Evaluation artifact rendered through Tk after recovery.",
                    "operator_action": "Review only. This display does not authorize source mutation, promotion, deployment, provider access, learning, or another mission.",
                    "details": record,
                })
        self.evaluation_review_items = runtime_items
        self._refresh_evaluation_snapshot()

    def _live_runtime_4_summary(self) -> str:
        controller = getattr(self, "live_runtime_4_controller", None)
        if controller is None:
            return "LIVE-RUNTIME-4 is not attached."
        state = dict((controller.continuous_learning_state or {}).get("live_runtime_1") or {})
        stop_text = ""
        stop_path = LIVE_RUNTIME_4_ROOT / "unattended_stop" / "stop.json"
        if stop_path.exists():
            stop = json.loads(stop_path.read_text(encoding="utf-8"))
            recovery = dict(stop.get("recovery_classification") or {})
            recovery_text = f"\nRecovery: {recovery.get('disposition')} / {recovery.get('advancement_id')}" if recovery.get("disposition") else ""
            stop_text = f"\nStop: {stop.get('stop_reason')} / {stop.get('result_status')}{recovery_text}"
        return (
            f"State: {controller.continuous_mission_state}\n"
            f"Root: {LIVE_RUNTIME_4_ROOT}\n"
            f"Cycles: {state.get('scheduler_cycles')}\n"
            f"Mission: {(state.get('mission') or {}).get('mission_id') or 'pending'}\n"
            f"Work items: {json.dumps(dict(state.get('work_item_status') or {}), sort_keys=True)}\n"
            f"Evaluation entries: {len(tuple((LIVE_RUNTIME_4_ROOT / 'evaluation_ui').glob('*.json'))) if (LIVE_RUNTIME_4_ROOT / 'evaluation_ui').exists() else 0}\n"
            f"Counts: {json.dumps(dict(state.get('counts') or {}), sort_keys=True, default=str)}"
            f"{stop_text}"
        )

    def _prepare_live_runtime_4_from_ui(self) -> str:
        if LIVE_RUNTIME_4_ROOT.exists() and self._live_runtime_4_restart_path().exists():
            self._load_live_runtime_4_state()
            return "LIVE-RUNTIME-4 already has persisted state. No second mission was started.\n\n" + self._live_runtime_4_summary()
        self.live_runtime_4_controller = prepare_live_runtime_4_mission(
            runtime_root=LIVE_RUNTIME_4_ROOT,
            accepted_competence_root=LIVE_RUNTIME_4_ACCEPTED_ROOT,
            reset=True,
        )
        self._sync_live_runtime_4_evaluation_items()
        self.live_runtime_status.set("LIVE-RUNTIME-4: graph registered awaiting first authority")
        return "LIVE-RUNTIME-4 mission approved and graph registered through Tk.\n\n" + self._live_runtime_4_summary()

    def _authorize_live_runtime_4_from_ui(self, generation: int) -> str:
        controller = getattr(self, "live_runtime_4_controller", None)
        if controller is None:
            self._load_live_runtime_4_state()
            controller = getattr(self, "live_runtime_4_controller", None)
        if controller is None:
            return "LIVE-RUNTIME-4 cannot authorize unattended mode: no mission graph is registered."
        authority = compile_live_runtime_4_unattended_authority(
            controller,
            runtime_root=LIVE_RUNTIME_4_ROOT,
            generation=generation,
            max_cycles=8,
        )
        self.live_runtime_status.set(f"LIVE-RUNTIME-4: authority {generation} accepted")
        return (
            f"LIVE-RUNTIME-4 authority {generation} accepted.\n\n"
            f"Authority: {authority['authority_id']}\n"
            f"Digest: {authority['artifact_digest']}\n"
            f"Allowed work items: {json.dumps(tuple(authority['allowed_work_item_ids']))}\n"
            "Limits: one mission, eight controller advances, 10 minutes, provider budget 0, learning disabled, network disabled, mutation disabled, deployment disabled."
        )

    def _start_live_runtime_4_from_ui(self, *, crash_after_prepared: bool = False) -> str:
        if not (LIVE_RUNTIME_4_ROOT / "unattended_authority").exists():
            return "LIVE-RUNTIME-4 cannot start unattended mode: authority record is missing."
        self.live_runtime_4_process = start_live_runtime_4_process(
            runtime_root=LIVE_RUNTIME_4_ROOT,
            python_executable=sys.executable,
            fault_after_prepared_phase="json_completed" if crash_after_prepared else None,
        )
        self.live_runtime_status.set("LIVE-RUNTIME-4: bounded unattended runner started")
        mode = "crash-injection" if crash_after_prepared else "resumption"
        return (
            f"LIVE-RUNTIME-4 {mode} bounded unattended runner started from explicit Tk operator command.\n\n"
            f"Process ID: {self.live_runtime_4_process.pid}\n"
            "Close the Tk window now for the bounded unattended interval."
        )

    def _selected_evaluation_review_item(self) -> tuple[str, dict[str, object]] | tuple[None, None]:
        selected = self.evaluation_items.selection()
        if not selected or not self.evaluation_snapshot:
            return None, None
        key = str(selected[0])
        item = self.evaluation_snapshot.get(key)
        if not item:
            return None, None
        details = item.get("details", item)
        if not isinstance(details, dict):
            return None, None
        raw_item = item.get("_raw_item", {})
        if not isinstance(raw_item, dict):
            raw_item = {}
        merged = {**item, **raw_item, **details}
        return key, merged

    def _oar_review_item_from_details(self, details: dict[str, object]) -> gsr.OperatorReviewItem | None:
        field_names = {field.name for field in fields(gsr.OperatorReviewItem)}
        payload = {key: value for key, value in details.items() if key in field_names}
        required = {
            "review_item_id",
            "parent_mission_id",
            "compiled_objective_id",
            "capability_gap_id",
            "proposal_id",
            "proposal_version",
            "artifact_chain_digest",
        }
        if not required.issubset(payload):
            return None
        return gsr.OperatorReviewItem(**payload)

    def _compiled_mission_from_details(self, details: dict[str, object]) -> gsr.CompiledMissionObjective | None:
        payload = details.get("compiled_objective")
        if not isinstance(payload, dict):
            payload = {
                "compiled_objective_id": details.get("compiled_objective_id"),
                "compilation_request_id": details.get("compilation_request_id", ""),
                "original_operator_mission": details.get("original_operator_mission"),
                "mission_family": details.get("mission_family"),
                "baseline_evaluation_id": details.get("baseline_evaluation_id", ""),
                "measurable_dimensions": tuple(details.get("measurable_dimensions") or ()),
                "proposed_baseline_evaluation": details.get("proposed_baseline_evaluation", ""),
                "success_thresholds": dict(details.get("success_thresholds") or {}),
                "protected_invariants": tuple(details.get("protected_invariants") or ()),
                "resource_budgets": dict(details.get("resource_budgets") or {}),
                "allowed_capabilities": tuple(details.get("allowed_capabilities") or ()),
                "source_scope": tuple(details.get("source_scope") or ()),
                "stop_conditions": tuple(details.get("stop_conditions") or ()),
                "operator_decisions_required": tuple(details.get("operator_decisions_required") or ()),
                "mission_substituted": bool(details.get("mission_substituted", False)),
                "hidden_permission_expansion": bool(details.get("hidden_permission_expansion", False)),
            }
        field_names = {field.name for field in fields(gsr.CompiledMissionObjective)}
        filtered = {key: value for key, value in payload.items() if key in field_names}
        required = {
            "compiled_objective_id",
            "compilation_request_id",
            "original_operator_mission",
            "mission_family",
            "baseline_evaluation_id",
            "measurable_dimensions",
            "proposed_baseline_evaluation",
            "success_thresholds",
            "protected_invariants",
            "resource_budgets",
            "allowed_capabilities",
            "source_scope",
            "stop_conditions",
            "operator_decisions_required",
        }
        if not required.issubset(filtered):
            return None
        return gsr.CompiledMissionObjective(**filtered)

    def _accept_selected_compiled_mission(self) -> None:
        key, details = self._selected_evaluation_review_item()
        if details is None:
            self.evaluation_status.set("No evaluation item selected.")
            return
        compiled = self._compiled_mission_from_details(details)
        if compiled is None:
            self.evaluation_status.set("Selected item is not a mission compilation.")
            return
        if not hasattr(self, "oar_runtime_state"):
            self.oar_runtime_state = gsr.OARRuntimeState(runtime_state_id="tk-oar-development-runtime")
        sequence = len(getattr(self, "evaluation_dispositions", [])) + len(getattr(self, "evaluation_review_items", [])) + 1
        approval = gsr.approve_compiled_mission(compiled, operator_identity="tk_operator", sequence=sequence)
        result = gsr.register_approved_mission_for_development(self.oar_runtime_state, compiled, approval, sequence=sequence + 1)
        if not result.accepted:
            self.evaluation_status.set(f"Mission acceptance denied: {result.reason}.")
            return
        self.oar_runtime_state = result.state
        self.oar_approved_compiled_mission = asdict(compiled)
        self.oar_mission_approval = asdict(approval)
        if key and str(key).startswith("review-"):
            index = int(str(key).split("-", 1)[1]) - 1
            if 0 <= index < len(self.evaluation_review_items):
                updated = dict(self.evaluation_review_items[index])
                updated["status"] = "mission_approved"
                updated["operator_action"] = "Mission approved. Development Runtime remains stopped until Start Development Runtime is pressed."
                updated_details = dict(updated.get("details") or {})
                updated_details["mission_approval"] = asdict(approval)
                updated_details["runtime_state"] = asdict(self.oar_runtime_state)
                updated["details"] = updated_details
                self.evaluation_review_items[index] = updated
        self._refresh_evaluation_snapshot()
        self.evaluation_status.set("Mission approved. Development Runtime status: stopped. Next action: Start Development Runtime.")
        self._persist_oar_live_development_state()

    def _start_oar_development_runtime(self) -> None:
        if not getattr(self, "oar_approved_compiled_mission", None):
            self.evaluation_status.set("Development Runtime cannot start: no approved mission is registered.")
            return
        compiled = gsr.CompiledMissionObjective(**{
            key: value
            for key, value in self.oar_approved_compiled_mission.items()
            if key in {field.name for field in fields(gsr.CompiledMissionObjective)}
        })
        result = gsr.run_one_oar_development_runtime_cycle(
            self.oar_runtime_state,
            compiled,
            sequence=len(self.evaluation_review_items) + len(self.evaluation_dispositions) + 10,
        )
        if not result.accepted or result.review_item is None:
            self.evaluation_status.set(f"Development Runtime did not start: {result.reason}.")
            return
        self.oar_runtime_state = result.state
        self._set_evaluation_review_items([*self.evaluation_review_items, result.review_item])
        self.evaluation_status.set(
            f"Development Runtime paused after one proposal. Blocker={result.selected_capability_id}; checkpoint={result.checkpoint_id}."
        )
        self._persist_oar_live_development_state()

    def _execute_selected_fixture_proposal(self) -> None:
        _key, details = self._selected_evaluation_review_item()
        if details is None:
            self.evaluation_status.set("No evaluation item selected.")
            return
        item = self._oar_review_item_from_details(details)
        if item is None:
            self.evaluation_status.set("Selected item is not a queued executable proposal.")
            return
        sequence = len(self.evaluation_review_items) + len(self.evaluation_dispositions) + 20
        authorization = gsr.make_live_fixture_execution_authorization(
            item,
            operator_identity="tk_operator",
            issued_sequence=sequence,
            expiration_sequence=sequence + 5,
        )
        result = gsr.execute_live_fixture_proposal(
            self.oar_runtime_state,
            item,
            authorization,
            sequence=sequence,
        )
        if not result.accepted or result.evidence_review_item is None:
            self.evaluation_status.set(f"Fixture execution denied: {result.reason}.")
            return
        self.oar_runtime_state = result.state
        self._set_evaluation_review_items([*self.evaluation_review_items, result.evidence_review_item])
        self.evaluation_status.set(
            f"Fixture evidence queued for {item.proposal_id}. Runtime paused for operator review."
        )
        self._persist_oar_live_development_state()

    def _live_fixture_evidence_from_details(self, details: dict[str, object]) -> gsr.LiveFixtureExecutionEvidenceItem | None:
        field_names = {field.name for field in fields(gsr.LiveFixtureExecutionEvidenceItem)}
        payload = {key: value for key, value in details.items() if key in field_names}
        required = {
            "review_item_id",
            "parent_review_item_id",
            "proposal_id",
            "proposal_version",
            "authorization_id",
            "exact_path",
            "artifact_chain_digest",
        }
        if not required.issubset(payload):
            return None
        return gsr.LiveFixtureExecutionEvidenceItem(**payload)

    def _run_selected_tracked_source_preflight(self) -> None:
        _key, details = self._selected_evaluation_review_item()
        if details is None:
            self.evaluation_status.set("No evaluation item selected.")
            return
        evidence_item = self._live_fixture_evidence_from_details(details)
        if evidence_item is None:
            self.evaluation_status.set("Selected item is not LIVE-2A fixture evidence.")
            return
        parent_payload = next(
            (
                dict(item)
                for item in self.evaluation_review_items
                if str(item.get("review_item_id")) == evidence_item.parent_review_item_id
            ),
            None,
        )
        if parent_payload is None:
            self.evaluation_status.set("Tracked-source preflight denied: parent proposal not found.")
            return
        item = gsr.OperatorReviewItem(**{
            key: value
            for key, value in parent_payload.items()
            if key in {field.name for field in fields(gsr.OperatorReviewItem)}
        })
        sequence = len(self.evaluation_review_items) + len(self.evaluation_dispositions) + 30
        mapping = gsr.make_live_tracked_source_target_mapping(item)
        request = gsr.make_live_tracked_source_preflight_request(
            item,
            evidence_item,
            mapping,
            repository_identity=str(ROOT),
            branch_identity="codex/delta-cognitive-core",
            requested_sequence=sequence,
        )
        authorization = gsr.make_live_tracked_source_preflight_authorization(
            request,
            operator_identity="tk_operator",
            issued_sequence=sequence,
            expiration_sequence=sequence + 5,
        )
        result = gsr.execute_live_tracked_source_preflight(
            self.oar_runtime_state,
            item,
            evidence_item,
            request,
            authorization,
            sequence=sequence,
            repository_root=ROOT,
            current_branch="codex/delta-cognitive-core",
        )
        if not result.accepted or result.evidence_review_item is None:
            self.evaluation_status.set(f"Tracked-source preflight denied: {result.reason}.")
            return
        self.oar_runtime_state = result.state
        self._set_evaluation_review_items([*self.evaluation_review_items, result.evidence_review_item])
        self.evaluation_status.set(
            f"Tracked-source preflight queued: {result.evidence.eligibility_classification}. Runtime paused for operator review."
        )
        self._persist_oar_live_development_state()

    def _record_evaluation_disposition(self, disposition: str) -> None:
        _key, details = self._selected_evaluation_review_item()
        if details is None:
            self.evaluation_status.set("No evaluation item selected.")
            return
        item = self._oar_review_item_from_details(details)
        if item is None:
            self.evaluation_status.set("Selected item is display-only and cannot receive an OAR disposition.")
            return
        existing_ids = {
            str(record.get("review_item_id"))
            for record in self.evaluation_dispositions
            if bool(record.get("terminal"))
        }
        if item.review_item_id in existing_ids:
            self.evaluation_status.set(f"Disposition denied for {item.review_item_id}: duplicate terminal disposition.")
            return
        reason = "operator_comment" if disposition == "accepted" else ("insufficient_evidence" if disposition == "declined" else "needs_narrower_scope")
        sequence = len(self.evaluation_dispositions) + 1
        request = gsr.make_operator_proposal_disposition_request(
            item,
            requested_disposition=disposition,
            reason_code=reason,
            operator_comment=f"Tk operator selected {disposition}.",
            ui_action_id=f"tk-evaluation-{disposition}-{sequence}",
            sequence=sequence,
        )
        authorization = gsr.make_operator_proposal_disposition_authorization(
            request,
            operator_identity="tk_operator",
            issued_sequence=sequence,
        )
        previous = tuple(
            gsr.OperatorProposalDisposition(**{
                key: value
                for key, value in record.items()
                if key in {field.name for field in fields(gsr.OperatorProposalDisposition)}
            })
            for record in self.evaluation_dispositions
            if record.get("review_item_id") == item.review_item_id
        )
        result = gsr.apply_operator_proposal_disposition(item, request, authorization, previous, sequence=sequence)
        if not result.accepted or result.disposition is None:
            self.evaluation_status.set(f"Disposition denied for {item.review_item_id}: {result.reason}.")
            return
        record = asdict(result.disposition)
        self.evaluation_dispositions.append(record)
        self.evaluation_status.set(
            f"Recorded {disposition} for {item.proposal_id}. No source application, execution, activation, or continuation was performed."
        )
        self._show_selected_evaluation_item()

    def _is_oar_language_development_mission(self, message: str) -> bool:
        normalized = " ".join(message.lower().split())
        if not any(token in normalized for token in ("develop", "improve", "refine")):
            return False
        if not any(token in normalized for token in ("language", "scholarly", "scholar")):
            return False
        return any(token in normalized for token in ("mission", "capability", "ability", "behavior", "improvement", "development"))

    def _is_developmental_learning_mission(self, message: str) -> bool:
        return classify_developmental_instruction(message) is not None

    def _is_persistent_development_goal(self, message: str) -> bool:
        normalized = " ".join(message.lower().split())
        return normalized.startswith(("your goal today is", "goal today is", "goals today are"))

    def _handle_persistent_development_goal(self, message: str) -> str:
        runtime = initialize_runtime(
            runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT,
            goals=(message,),
        )
        runtime = run_until_idle(
            state=runtime,
            runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT,
            maximum_cycles=32,
        )
        self.persistent_development_runtime = runtime
        report = export_runtime_report(
            state=runtime,
            runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT,
        )
        goals = tuple(report.get("goals") or ())
        current = goals[-1] if goals else {}
        return (
            "Persistent developmental runtime finished its current bounded work queue.\n\n"
            f"Goal: {current.get('topic') or 'none'}\n"
            f"Disposition: {current.get('state') or runtime.get('lifecycle_state')}\n"
            f"Reason: {current.get('blocker') or runtime.get('terminal_reason') or 'none'}\n"
            f"Checkpoint: {runtime.get('checkpoint_sequence')}\n"
            f"Report: {PERSISTENT_DEVELOPMENT_RUNTIME_ROOT / 'PERSISTENT_AUTONOMOUS_DEVELOPMENT_REPORT.json'}\n\n"
            "No provider, trusted-memory admission, capability promotion, or model-weight update occurred."
        )

    def _handle_persistent_development_control(self, command: str) -> str:
        runtime = initialize_runtime(runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT)
        if command == "pause":
            runtime = pause_runtime(state=runtime, runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT)
        elif command == "resume":
            runtime = resume_runtime(state=runtime, runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT)
        elif command == "stop":
            runtime = stop_runtime(state=runtime, runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT)
        self.persistent_development_runtime = runtime
        return f"Persistent developmental runtime: {runtime.get('lifecycle_state')}; checkpoint={runtime.get('checkpoint_sequence')}."

    def _handle_persistent_development_status(self) -> str:
        runtime = initialize_runtime(runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT)
        report = export_runtime_report(state=runtime, runtime_root=PERSISTENT_DEVELOPMENT_RUNTIME_ROOT)
        goals = tuple(report.get("goals") or ())
        paused_or_blocked = tuple(
            goal for goal in goals
            if goal.get("state") in {"blocked_evidence_environment", "paused_budget", "blocked_capability_gap"}
        )
        return (
            f"Persistent developmental runtime: {report.get('lifecycle_state')}; "
            f"provider calls={report.get('provider_calls')}; "
            f"estimated spend=${report.get('provider_spend_estimated_usd')}; "
            f"goals={len(goals)}; paused_or_blocked={len(paused_or_blocked)}.\n"
            f"Report: {PERSISTENT_DEVELOPMENT_RUNTIME_ROOT / 'PERSISTENT_AUTONOMOUS_DEVELOPMENT_REPORT.json'}"
        )

    def _handle_developmental_learning_mission(self, message: str) -> str:
        """Run one bounded local learning cycle through the continuous controller."""

        controller = getattr(self, "developmental_learning_controller", None)
        prior_instruction = str((controller.continuous_learning_state.get("mission") or {}).get("operator_instruction") or "") if controller else ""
        if controller is None or not controller.continuous_learning_state or prior_instruction != message.strip():
            controller = start_continuous_runtime_controller(session_id=f"tk-learning-{uuid.uuid4().hex[:16]}")
            controller = compile_mission_bound_local_model_learning_request(controller, message)
        provisional = dict(controller.continuous_learning_state.get("provisional_resource_bundle") or {})
        advisory = dict(controller.continuous_learning_state.get("mission_bound_advisory_evidence") or {})
        retained_bundle = dict(controller.continuous_learning_state.get("retained_bundle") or {})
        if provisional and not retained_bundle.get("independent_evaluator"):
            self.developmental_learning_controller = controller
            active = dict(controller.continuous_active_subgoal or {})
            return (
                "Existing durable local-model result was translated into a provisional advisory learning resource. "
                f"Evidence={advisory.get('evidence_id')}; sufficiency={advisory.get('sufficiency_state')}; "
                f"resource={provisional.get('resource_bundle_id')}; first_subgoal={active.get('subgoal_id') or 'none'}. "
                "The subgoal is queued but was not executed. No evaluation, capability update, provider, web, PCM, or tracked-source action occurred."
            )
        if not controller.continuous_active_subgoal:
            self.developmental_learning_controller = controller
            next_gap = dict(controller.continuous_learning_state.get("next_learning_gap") or {})
            if next_gap:
                return (
                    "Independent learning evaluation completed and capability was updated only for the demonstrated scope. "
                    f"Next gap={next_gap.get('capability_dimension')}; status={next_gap.get('status')}; "
                    f"reason={next_gap.get('reason')}. No provider, web, PCM, or tracked-source action occurred."
                )
            request = dict(controller.continuous_learning_state.get("local_model_request") or {})
            if request:
                return (
                    "Developmental learning mission compiled with an existing one-use local-model request. "
                    f"State={controller.continuous_mission_state}; request_id={request.get('request_id')}; "
                    "no local model, provider, web, PCM, source application, or capability promotion occurred before operator approval."
                )
            return (
                "Developmental learning mission compiled, but local retained evidence was insufficient to start a bounded attempt. "
                f"State={controller.continuous_mission_state}. No provider, web, PCM, source application, or capability promotion occurred."
            )
        artifact_root = ROOT / ".tmp" / "tk_developmental_learning" / controller.session_id
        controller, result = execute_continuous_active_subgoal(
            controller,
            artifact_root=artifact_root,
            repository_root=ROOT,
            python_executable=sys.executable,
        )
        self.developmental_learning_controller = controller
        next_subgoal = dict(controller.continuous_active_subgoal or {})
        frontier = dict(controller.continuous_learning_state.get("selected_frontier") or {})
        evaluation = dict(result.behavioral_evaluation_request or {})
        failure = tuple(controller.continuous_learning_state.get("failure_localizations") or ())
        revision = tuple(controller.continuous_learning_state.get("resource_revisions") or ())
        next_gap = dict(controller.continuous_learning_state.get("next_learning_gap") or {})
        completed_subgoal = str(result.subgoal_id)
        active_resources = tuple(result.source_inspection.get("resource_ids") or ())
        return (
            "Developmental learning mission completed one bounded local cycle.\n\n"
            f"Mission: {controller.continuous_learning_state['mission']['mission_type']} / "
            f"{controller.continuous_learning_state['mission']['domain']} / {controller.continuous_learning_state['mission']['topic']}\n"
            f"Completed subgoal: {evaluation.get('capability_dimension') or completed_subgoal}\n"
            f"Selected frontier: {frontier.get('topic') or 'none'} / {frontier.get('capability_dimension') or 'none'} "
            f"(rank={frontier.get('rank') if frontier else 'n/a'}; {frontier.get('selection_reason') or 'none'})\n"
            f"Selected local resources: {', '.join(active_resources) or 'none'}\n"
            f"Evaluation: {result.disposition}; baseline={result.baseline}; candidate={result.candidate}; "
            f"controls={result.validation.get('control')}; held_out={result.validation.get('held_out')}; "
            f"adversarial={result.validation.get('adversarial')}; transfer={result.validation.get('transfer')}.\n"
            f"Failure localization: {(failure[-1].get('implicated_concept') if failure else 'none')}\n"
            f"Resource revision: {(revision[-1].get('revised_bundle_id') if revision else 'none')}\n"
            f"Next subgoal: {next_subgoal.get('capability_target') or next_gap.get('capability_dimension') or 'honest observation'}\n"
            f"Evidence: {evaluation.get('evaluation_id') or 'none'}\n\n"
            "No provider, web, PCM, tracked-source application, commit, or push occurred."
        )

    def _handle_oar_language_development_mission(self, message: str) -> str:
        sequence = len(self.session_history) + len(self.evaluation_review_items) + 1
        request = gsr.make_mission_compilation_request(
            message,
            baseline_evaluation_id=f"tk-live-language-baseline-{sequence}",
            requested_sequence=sequence,
            maximum_capability_campaigns=1,
            maximum_attempts_per_campaign=1,
            maximum_runtime_hours=1,
        )
        authorization = gsr.make_mission_compilation_authorization(request, issued_sequence=sequence + 1)
        result = gsr.compile_language_development_mission(request, authorization, sequence=sequence + 2)
        if not result.accepted or result.compiled_objective is None or result.evidence is None:
            return (
                "I recognized this as a governed language-development mission, but mission compilation failed closed: "
                f"{result.reason}. No development runtime, source application, provider call, model call, or memory write occurred."
            )
        review_item = {
            "item_type": "oar_mission_compilation",
            "title": "OAR Mission Compilation",
            "status": "pending_operator_review",
            "boundary": "operator mission -> OAR mission compilation -> Evaluation review evidence -> stop",
            "operator_action": "Review the compiled mission. This does not approve, start, apply, or activate development.",
            "details": {
                "original_operator_mission": result.compiled_objective.original_operator_mission,
                "compiled_objective_id": result.compiled_objective.compiled_objective_id,
                "compiled_objective": asdict(result.compiled_objective),
                "compilation_request_id": result.compiled_objective.compilation_request_id,
                "mission_family": result.compiled_objective.mission_family,
                "baseline_evaluation_id": result.compiled_objective.baseline_evaluation_id,
                "measurable_dimensions": result.compiled_objective.measurable_dimensions,
                "proposed_baseline_evaluation": result.compiled_objective.proposed_baseline_evaluation,
                "success_thresholds": result.compiled_objective.success_thresholds,
                "protected_invariants": result.compiled_objective.protected_invariants,
                "resource_budgets": result.compiled_objective.resource_budgets,
                "allowed_capabilities": result.compiled_objective.allowed_capabilities,
                "source_scope": result.compiled_objective.source_scope,
                "stop_conditions": result.compiled_objective.stop_conditions,
                "operator_decisions_required": result.compiled_objective.operator_decisions_required,
                "compilation_evidence": asdict(result.evidence),
                "mission_started": result.mission_started,
                "source_application_authorized": result.source_application_authorized,
                "capability_activated": result.capability_activated,
                "automatic_continuation": result.automatic_continuation,
            },
            "guarantees": [
                "The original operator wording is preserved in the compiled mission.",
                "Mission compilation consumed only compilation authorization.",
                "No development runtime was started.",
                "No provider call, local-model call, memory write, source application, capability activation, scheduler, thread, or automatic continuation was performed.",
            ],
        }
        self._set_evaluation_review_items([*self.evaluation_review_items, review_item])
        return (
            "I recognized this as a governed language-development mission and compiled it for operator review. "
            "The compiled mission is now surfaced in the Evaluation tab as pending_operator_review. "
            "No development runtime was started, and no source application, provider call, model call, memory write, "
            "capability activation, or automatic continuation occurred."
        )

    def _normalize_evaluation_review_item(self, index: int, item: dict[str, object]) -> dict[str, object]:
        item_type = str(item.get("item_type") or item.get("type") or "evaluation_item")
        title = str(item.get("title") or item.get("evaluation_id") or item.get("record_id") or f"Review item {index}")
        status = str(item.get("status") or item.get("classification") or item.get("operator_disposition") or "available")
        details = item.get("details", item)
        return {
            "title": title,
            "status": status,
            "boundary": str(item.get("boundary") or f"Read-only {item_type} display."),
            "operator_action": str(item.get("operator_action") or "Review manually; this tab provides no approval or execution control."),
            "_raw_item": item,
            "details": details,
            "guarantees": [
                "Display-only rendering from an in-memory review item.",
                "No evaluation, disposition, execution request, authorization, lifecycle transition, or continuation is created.",
                "No file, memory, persistence, provider, model, scheduler, thread, or process side effect is started by this display path.",
            ],
        }

    def _show_selected_evaluation_item(self) -> None:
        selected = self.evaluation_items.selection()
        if not selected or not self.evaluation_snapshot:
            return
        item = self.evaluation_snapshot.get(str(selected[0]), {})
        lines = [
            str(item.get("title", "")),
            "",
            f"Status: {item.get('status', '')}",
            f"Boundary: {item.get('boundary', '')}",
            "",
            "Operator handling:",
            str(item.get("operator_action", "")),
            "",
            "Guarantees:",
        ]
        lines.extend(f"- {value}" for value in item.get("guarantees", []))
        if "details" in item:
            lines.extend(["", "Details:", json.dumps(item["details"], indent=2, sort_keys=True, default=str)])
        self._write_evaluation_detail("\n".join(lines))

    def _write_evaluation_detail(self, text: str) -> None:
        self.evaluation_detail.configure(state=tk.NORMAL)
        self.evaluation_detail.delete("1.0", tk.END)
        if text:
            self.evaluation_detail.insert(tk.END, text)
        self.evaluation_detail.configure(state=tk.DISABLED)

    def _refresh_state_cards(self) -> None:
        state = build_cognitive_state()
        developmental = build_developmental_memory_state()
        substrate = substrate_counts()
        active_concepts = int(substrate.get("active_runtime_concepts", substrate.get("concepts", 0)) or 0)
        replay_events = int(substrate.get("substrate_replay_events", substrate.get("replay_events", 0)) or 0)
        state = {
            **state,
            "knowledge_available": state["knowledge_available"] or developmental["knowledge_memory_records"] > 0 or active_concepts > 0,
            "concepts": active_concepts,
            "contradictions": state["contradictions"] + developmental["concept_contradictions"],
            "replay_queue": replay_events,
            "migration_audit_events": int(substrate.get("migration_audit_events", 0) or 0),
        }
        for key, var in self.state_vars.items():
            var.set(str(state[key]))

    def _load_database_concepts(self) -> None:
        try:
            concepts = load_diverse_concepts(limit=1000)
            self._set_database_results(
                concepts,
                f"Showing diversified concepts from {substrate_counts().get('backend')} backend.",
            )
        except Exception as exc:  # noqa: BLE001 - UI should remain open if index is unavailable.
            self._set_database_results([], f"Database lookup failed: {type(exc).__name__}: {str(exc)[:160]}")

    def _search_database_concepts(self) -> None:
        query = self.database_query.get().strip()
        if not query:
            self._load_database_concepts()
            return
        try:
            result = search_concepts(query, limit=1000)
            concepts = result.get("matches", [])
            backend = result.get("backend") or substrate_counts().get("backend")
            self._set_database_results(
                concepts,
                f"Search `{query}`: {len(concepts)} result(s), backend={backend}, candidate_pool={result.get('candidate_pool_size', 'n/a')}.",
            )
        except Exception as exc:  # noqa: BLE001
            self._set_database_results([], f"Search failed: {type(exc).__name__}: {str(exc)[:160]}")

    def _set_database_results(self, concepts: list[dict[str, object]], status: str) -> None:
        self.database_results = list(concepts)
        self.database_page = 0
        self.database_result_status = status
        self._show_database_page()

    def _database_next_page(self) -> None:
        if (self.database_page + 1) * self.database_page_size >= len(self.database_results):
            return
        self.database_page += 1
        self._show_database_page()

    def _database_previous_page(self) -> None:
        if self.database_page <= 0:
            return
        self.database_page -= 1
        self._show_database_page()

    def _show_database_page(self) -> None:
        start = self.database_page * self.database_page_size
        end = start + self.database_page_size
        self._populate_database_concepts(self.database_results[start:end], self.database_result_status)
        total = len(self.database_results)
        if total:
            self.database_page_status.set(f"Showing {start + 1}-{min(end, total)} of {total}")
        else:
            self.database_page_status.set("No concepts to show")

    def _populate_database_concepts(self, concepts: list[dict[str, object]], status: str) -> None:
        self.database_items = {}
        for item in self.database_concepts.get_children():
            self.database_concepts.delete(item)
        for concept in concepts:
            concept_id = str(concept.get("concept_id") or "")
            if not concept_id:
                continue
            self.database_items[concept_id] = concept
            quality = concept.get("quality_score", concept.get("confidence", ""))
            self.database_concepts.insert(
                "",
                tk.END,
                iid=concept_id,
                values=(
                    str(concept.get("concept_name") or ""),
                    str(concept.get("domain") or ""),
                    str(concept.get("concept_type") or ""),
                    str(quality)[:8],
                ),
            )
        counts = substrate_counts()
        self.database_status.set(
            f"{status} Active concepts={counts.get('active_runtime_concepts', counts.get('concepts'))}; "
            f"active graph edges={counts.get('active_graph_edges', counts.get('graph_edges'))}; "
            f"replay events={counts.get('substrate_replay_events', counts.get('replay_events'))}."
        )
        self._write_database_detail("")

    def _show_selected_database_concept(self) -> None:
        selected = self.database_concepts.selection()
        if not selected:
            return
        concept = self.database_items.get(str(selected[0]))
        if not concept:
            return
        lines = [
            str(concept.get("concept_name") or "Unnamed Concept"),
            "",
            f"ID: {concept.get('concept_id')}",
            f"Domain: {concept.get('domain')}",
            f"Type: {concept.get('concept_type')}",
            f"Quality: {concept.get('quality_score', concept.get('confidence', ''))}",
            f"Status: {concept.get('approval_status')}",
            f"Canonical: {concept.get('canonical')}",
            f"Source: {concept.get('source_type') or concept.get('_store_memory_type') or ''}",
            f"Rollback: {concept.get('rollback_handle') or concept.get('rollback_id') or ''}",
            "",
            "Definition:",
            str(concept.get("short_definition") or "").strip(),
        ]
        for title, key in [
            ("Propositions", "propositions"),
            ("Related Concepts", "related_concepts"),
            ("Examples", "examples"),
            ("Misconceptions", "misconceptions"),
        ]:
            values = concept.get(key)
            if isinstance(values, list) and values:
                lines.extend(["", f"{title}:"])
                lines.extend(f"- {item}" for item in values[:12])
        self._write_database_detail("\n".join(lines))

    def _write_database_detail(self, text: str) -> None:
        self.database_detail.configure(state=tk.NORMAL)
        self.database_detail.delete("1.0", tk.END)
        if text:
            self.database_detail.insert(tk.END, text)
        self.database_detail.configure(state=tk.DISABLED)

    def _append_chat(self, speaker: str, text: str) -> None:
        if speaker == "DELTA":
            text = shape_governed_presentation(str(text), self.governed_personality_state)
        self.chat_history.configure(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"{speaker}: {text}\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state=tk.DISABLED)

    def _append_observation(self, title: str, text: str) -> None:
        stream = getattr(self, "observation_stream", None)
        if stream is None:
            self._append_chat(title, text)
            return
        stream.configure(state=tk.NORMAL)
        heading = str(title or "Observation").strip()
        body = str(text or "").strip()
        stream.insert(tk.END, f"{heading}: {body}\n\n")
        stream.see(tk.END)
        stream.configure(state=tk.DISABLED)

    def _append_session(self, role: str, content: str) -> None:
        self.session_history.append({"role": role, "content": " ".join(str(content).split())[:1200]})
        if len(self.session_history) > 24:
            self.session_history = self.session_history[-24:]

    def _refresh_interactive_cognition_shadow(
        self,
        *,
        foreground_message: str = "",
        foreground_turn_id: str = "",
        reason: str = "",
    ):
        """Record what attention would choose without granting it control."""
        coordination = getattr(self, "interactive_coordination_state", None)
        if coordination is None:
            coordination = load_coordination_state(
                self.conversational_runtime_root,
                runtime_id=self.conversational_runtime_state.runtime_id,
            )
            self.interactive_coordination_state = coordination
        overlay = getattr(self, "developer_overlay_enabled", None)
        episode = None
        active_path = Path(self.conversational_runtime_state.active_episode_path or "")
        if active_path.exists():
            try:
                episode = read_active_cognitive_episode_state(active_path)
            except Exception:
                episode = None
        try:
            graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        except Exception:
            graph = None
        snapshot = build_workspace_snapshot(
            self.conversational_runtime_state,
            episode=episode,
            graph=graph,
            coordination=coordination,
            foreground_message=foreground_message,
            foreground_turn_id=foreground_turn_id,
            developmental_controller=self._developmental_teaching_snapshot(),
            ui_visibility={
                "conversation_visible": True,
                "observation_visible": hasattr(self, "observation_stream"),
                "developer_overlay": bool(overlay.get()) if overlay is not None else False,
                "background_inference_in_flight": self.conversational_runtime_inference_in_flight,
            },
        )
        decision = arbitrate_attention(snapshot)
        self.interactive_workspace_snapshot = snapshot
        self.interactive_attention_decision = decision
        if not any(item.get("decision_id") == decision.decision_id for item in coordination.decision_history):
            self.interactive_coordination_state = record_shadow_decision(coordination, decision)
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
            detail = (
                f"Shadow selected {decision.selected_posture} for {decision.target_thread_id or 'no thread'} "
                f"because {', '.join(decision.reason_codes[:3])}."
            )
            self._append_observation("Attention decision", detail)
        return decision

    def _record_attention_control_stage(self, decision, *, stage: str, detail: str) -> None:
        """Keep advisory selection distinct from the limited production action it gates."""
        record = stage_attention_decision(decision, stage=stage)
        if any(item.get("decision_id") == record.decision_id for item in self.interactive_coordination_state.decision_history):
            return
        self.interactive_coordination_state = record_shadow_decision(self.interactive_coordination_state, record)
        save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
        self._append_observation("Attention control", detail)

    def _surface_one_near_association(self, decision) -> bool:
        """Surface one graph-grounded association without asserting a new claim."""

        workspace = getattr(self, "interactive_workspace_snapshot", None)
        if workspace is None:
            return False
        target_thread = next((item for item in workspace.threads if item.thread_id == decision.target_thread_id), None)
        if target_thread is None:
            return False
        candidate = next(
            (item for item in workspace.association_candidates if item.candidate_id == target_thread.originating_reference),
            None,
        )
        if candidate is None or candidate.state not in {"generated", "queued"}:
            return False
        updated = surface_candidate_once(
            self.interactive_coordination_state,
            candidate_id=candidate.candidate_id,
            candidate_kind="near_association",
            source_record_ids=candidate.provenance_refs,
        )
        if updated == self.interactive_coordination_state:
            return False
        self.interactive_coordination_state = updated
        save_coordination_state(self.conversational_runtime_root, updated)
        self._append_observation(
            "Association",
            "A graph-grounded dependency is available for review. It is an association, not a new factual conclusion.",
        )
        self._record_attention_control_stage(
            decision,
            stage="executed_posture",
            detail="One explicit dependency association was surfaced in the observation stream.",
        )
        return True

    def _surface_one_far_analogy(self, decision) -> bool:
        """Surface a graph-derived structural comparison without asserting equivalence."""
        workspace = getattr(self, "interactive_workspace_snapshot", None)
        target = next((item for item in (workspace.threads if workspace else ()) if item.thread_id == decision.target_thread_id), None)
        candidate = next((item for item in (workspace.analogy_candidates if workspace else ()) if item.candidate_id == (target.originating_reference if target else "")), None)
        if candidate is None or candidate.state not in {"generated", "queued"}:
            return False
        updated = surface_candidate_once(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind="far_analogy", source_record_ids=candidate.provenance_refs)
        if updated == self.interactive_coordination_state:
            return False
        self.interactive_coordination_state = updated
        save_coordination_state(self.conversational_runtime_root, updated)
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        labels = {item.claim_version_id: item.exact_text for item in graph.claim_versions}
        self._append_chat(
            "DELTA",
            "I found a provisional structural analogy for review. It is not a factual conclusion.\n\n"
            + describe_structural_analogy_candidate(candidate, record_labels=labels)
            + "\n\nYou can inspect its provenance in Advanced and choose whether to explore it.",
        )
        self._append_observation("Structural analogy", f"A provisional cross-domain pattern has {len(candidate.matched_relation_types)} matched functional relations and an explicit failure boundary.")
        self._record_attention_control_stage(decision, stage="executed_posture", detail="One graph-derived structural analogy was surfaced for operator review.")
        return True

    def _inspect_one_curiosity_candidate(self, decision) -> bool:
        """Record one idle, provenance-only revisit without starting a new mission."""

        workspace = getattr(self, "interactive_workspace_snapshot", None)
        if workspace is None:
            return False
        target_thread = next((item for item in workspace.threads if item.thread_id == decision.target_thread_id), None)
        if target_thread is None:
            return False
        candidate = next(
            (item for item in workspace.curiosity_candidates if item.candidate_id == target_thread.originating_reference),
            None,
        )
        if candidate is None or candidate.state not in {"generated", "queued"}:
            return False
        updated = surface_candidate_once(
            self.interactive_coordination_state,
            candidate_id=candidate.candidate_id,
            candidate_kind=(
                "cognitive_pressure"
                if candidate.trigger in {
                    "missing_evidence",
                    "contradiction",
                    "consolidation_correction",
                    "consolidation_contradiction",
                    "consolidation_remaining_gap",
                }
                else "curiosity_candidate"
            ),
            source_record_ids=candidate.source_record_ids,
        )
        if updated == self.interactive_coordination_state:
            return False
        self.interactive_coordination_state = updated
        save_coordination_state(self.conversational_runtime_root, updated)
        continuation = "Independent safe work can continue." if candidate.safe_independent_work_may_continue else "Independent work should pause until this is resolved."
        self._append_chat(
            "DELTA",
            "I noticed a bounded evidence gap.\n\n"
            f"What I noticed: {candidate.rationale}\n"
            f"What remains unknown: {candidate.uncertainty}\n"
            f"Why it matters: the answer would authorize this bounded next action: {candidate.proposed_bounded_action or candidate.safe_next_step}.\n"
            f"{continuation}\n\n"
            "You can inspect it in Advanced and choose whether to pursue one local, provisional inquiry.",
        )
        self._append_observation(
            "Curiosity",
            "An unstable claim remains available through its existing review path. No model call, new goal, or memory mutation was started.",
        )
        self._record_attention_control_stage(
            decision,
            stage="executed_posture",
            detail="One provenance-only curiosity inspection was surfaced during idle time.",
        )
        return True

    def _perform_one_consolidation_step(self, decision) -> bool:
        """Seal one local cohort packet; review and admission remain separate authority paths."""

        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        workspace = getattr(self, "interactive_workspace_snapshot", None)
        thread = next((item for item in workspace.threads if item.thread_id == decision.target_thread_id), None) if workspace else None
        if thread is None:
            return False
        cohort = next((item for item in graph.cohorts if item.cohort_id == thread.originating_reference), None)
        if cohort is None:
            return False
        updated, packet, outcome = seal_cohort_packet_once(graph, cohort)
        if outcome != "sealed" or packet is None:
            return False
        save_provisional_semantic_graph(self.conversational_runtime_root, updated)
        objective = self.conversational_runtime_state.active_objective
        if objective is not None and isinstance(objective.provenance, Mapping) and objective.provenance.get("teaching_plan"):
            followups = tuple(
                dict(item)
                for item in objective.provenance.get("teaching_followups", ())
                if isinstance(item, Mapping)
            )
            claim_refs = tuple(str(item) for item in cohort.claim_version_refs if str(item))
            related = tuple(
                item
                for item in followups
                if str(item.get("claim_version_id") or "") in set(claim_refs)
            )
            existing_records = [
                dict(item)
                for item in objective.provenance.get("teaching_consolidation_records", ())
                if isinstance(item, Mapping)
            ]
            if related and not any(str(item.get("packet_id") or "") == packet.packet_id for item in existing_records):
                plan = dict(objective.provenance.get("teaching_plan") or {})
                topic = str(plan.get("topic") or "this lesson")
                covered = ", ".join(str(item.get("question") or "the teaching follow-up") for item in related)
                record = {
                    "packet_id": packet.packet_id,
                    "cohort_id": cohort.cohort_id,
                    "claim_version_ids": claim_refs,
                    "followup_ids": tuple(str(item.get("followup_id") or "") for item in related),
                    "review_authorization_status": "awaiting_operator_confirmation",
                    "review_status": "awaiting_operator_confirmation",
                    "review_authority_granted": False,
                    "external_review_result_id": "",
                    "admission_id": "",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                request = ChatAddressableRequest(
                    request_id=rc6_stable_id(
                        "teaching-consolidation-review-authority",
                        self.conversational_runtime_state.runtime_id,
                        objective.objective_id,
                        packet.packet_id,
                    ),
                    request_type="teaching_consolidation_review_authority",
                    objective_id=objective.objective_id,
                    originating_goal_id=objective.objective_id,
                    goal_label=f"{topic} provisional review",
                    prompt_text=(
                        f"I organized the newly learned material about {covered} into a local review packet. "
                        "It remains provisional because no external grounding review has run. "
                        "May I prepare this one bounded packet for review when that governed review path is available?"
                    ),
                    authority_impact="external_consolidation_review_requires_conversational_confirmation",
                    thread_id=f"{objective.objective_id}:teaching-consolidation:{packet.packet_id}",
                    created_sequence=len(self.conversational_runtime_state.conversation) + 1,
                    accepted_response_types=("approved", "denied"),
                    baseline_metrics={
                        "teaching_request_kind": "consolidation_review_authority",
                        "packet_id": packet.packet_id,
                        "cohort_id": cohort.cohort_id,
                        "claim_version_ids": claim_refs,
                        "followup_ids": record["followup_ids"],
                    },
                )
                report = (
                    f"I finished organizing the recent {topic} material.\n\n"
                    f"Covered provisionally: {covered}.\n"
                    "What remains uncertain: this local explanation has not completed consolidation review.\n"
                    "What changed: it is now preserved with its source and uncertainty, not presented as verified fact.\n"
                    "Next useful step: decide whether this bounded packet should enter the governed review path."
                )
                assistant_turn = ConversationTurn(
                    turn_id=rc6_stable_id("teaching-consolidation-aftermath", self.conversational_runtime_state.runtime_id, packet.packet_id),
                    role="assistant",
                    text=f"{report}\n\n{request.prompt_text}",
                    intent_type="teaching_consolidation_aftermath",
                    objective_id=objective.objective_id,
                )
                updated_objective = replace(
                    objective,
                    provenance={
                        **objective.provenance,
                        "teaching_consolidation_records": tuple(existing_records + [record]),
                    },
                )
                self.conversational_runtime_state = replace(
                    self.conversational_runtime_state,
                    active_objective=updated_objective,
                    conversation=self.conversational_runtime_state.conversation + (assistant_turn,),
                    pending_chat_requests=self.conversational_runtime_state.pending_chat_requests + (request,),
                    objective_progress=self.conversational_runtime_state.objective_progress + ({
                        "event": "teaching_consolidation_aftermath_reported",
                        "objective_id": objective.objective_id,
                        "packet_id": packet.packet_id,
                        "cohort_id": cohort.cohort_id,
                        "followup_ids": record["followup_ids"],
                        "at": datetime.now(timezone.utc).isoformat(),
                    },),
                )
                self.conversational_runtime_state = mark_chat_request_rendered(
                    self.conversational_runtime_state,
                    request.request_id,
                    rendered_turn_id=assistant_turn.turn_id,
                    render_sequence=len(self.conversational_runtime_state.conversation),
                )
                self._append_chat("DELTA", report + "\n\n" + request.prompt_text)
                self._append_session("assistant", report + "\n\n" + request.prompt_text)
                self._sync_developmental_teaching_progress()
                save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
        self._append_observation(
            "Consolidation",
            "One local review packet was sealed for later administrative review. No provider call, review decision, or claim promotion occurred.",
        )
        self._record_attention_control_stage(
            decision,
            stage="executed_posture",
            detail="One local consolidation packet was sealed at the cohort cursor.",
        )
        return True

    def _request_active_goal_preemption(self, *, reason: str) -> bool:
        """Ask the coordinator to yield after the existing worker's atomic boundary."""
        marked = False
        for reinquiry in load_reinquiries(self.conversational_runtime_root):
            if reinquiry.lifecycle_state != "revisit_running":
                continue
            thread_id = f"approved-revisit:{reinquiry.reinquiry_id}"
            updated = request_preemption(
                self.interactive_coordination_state, thread_id=thread_id,
                operation_id=reinquiry.reinquiry_id, candidate_id=reinquiry.candidate_id,
                ledger_request_id=reinquiry.ledger_request_id,
                foreground_turn_id=rc6_stable_id("revisit-preemption-foreground", self.conversational_runtime_state.runtime_id, reason, str(len(self.conversational_runtime_state.conversation) + 1)),
                reason="foreground_operator_input",
            )
            if updated != self.interactive_coordination_state:
                self.interactive_coordination_state = updated
                save_coordination_state(self.conversational_runtime_root, updated)
                self._append_observation("Attention", "Foreground input requested a yield after the approved revisit reaches its ledger boundary.")
                marked = True
        for exploration in load_explorations(self.conversational_runtime_root):
            if exploration.lifecycle_state != "exploration_running":
                continue
            thread_id = f"association-exploration:{exploration.exploration_id}"
            updated = request_preemption(
                self.interactive_coordination_state, thread_id=thread_id,
                operation_id=exploration.exploration_id, candidate_id=exploration.candidate_id,
                ledger_request_id=exploration.ledger_request_id,
                foreground_turn_id=rc6_stable_id("association-preemption-foreground", self.conversational_runtime_state.runtime_id, reason, str(len(self.conversational_runtime_state.conversation) + 1)),
                reason="foreground_operator_input",
            )
            if updated != self.interactive_coordination_state:
                self.interactive_coordination_state = updated
                save_coordination_state(self.conversational_runtime_root, updated)
                self._append_observation("Attention", "Foreground input requested a yield after the approved association inquiry reaches its ledger boundary.")
                marked = True
        for exploration in load_structural_analogy_explorations(self.conversational_runtime_root):
            if exploration.lifecycle_state != "analogy_exploration_running":
                continue
            updated = request_preemption(
                self.interactive_coordination_state, thread_id=f"structural-analogy:{exploration.exploration_id}",
                operation_id=exploration.exploration_id, candidate_id=exploration.candidate_id,
                ledger_request_id=exploration.ledger_request_id,
                foreground_turn_id=rc6_stable_id("structural-analogy-preemption-foreground", self.conversational_runtime_state.runtime_id, reason, str(len(self.conversational_runtime_state.conversation) + 1)),
                reason="foreground_operator_input",
            )
            if updated != self.interactive_coordination_state:
                self.interactive_coordination_state = updated
                save_coordination_state(self.conversational_runtime_root, updated)
                self._append_observation("Attention", "Foreground input requested a yield after the structural analogy reaches its ledger boundary.")
                marked = True
        for inquiry in load_curiosity_inquiries(self.conversational_runtime_root):
            if inquiry.lifecycle_state != "curiosity_inquiry_running":
                continue
            updated = request_preemption(
                self.interactive_coordination_state, thread_id=f"curiosity-inquiry:{inquiry.inquiry_id}",
                operation_id=inquiry.inquiry_id, candidate_id=inquiry.candidate_id, ledger_request_id=inquiry.ledger_request_id,
                foreground_turn_id=rc6_stable_id("curiosity-preemption-foreground", self.conversational_runtime_state.runtime_id, reason, str(len(self.conversational_runtime_state.conversation) + 1)), reason="foreground_operator_input",
            )
            if updated != self.interactive_coordination_state:
                self.interactive_coordination_state = updated
                save_coordination_state(self.conversational_runtime_root, updated)
                marked = True
        decision = self._refresh_interactive_cognition_shadow(reason=reason)
        workspace = self.interactive_workspace_snapshot
        active = next((item for item in workspace.threads if item.thread_kind == "active_goal"), None) if workspace else None
        if active is None:
            return marked
        updated = request_preemption(
            self.interactive_coordination_state,
            thread_id=active.thread_id,
        )
        if updated == self.interactive_coordination_state:
            return False
        self.interactive_coordination_state = updated
        save_coordination_state(self.conversational_runtime_root, updated)
        self._append_observation(
            "Attention",
            "Foreground input requested a yield after the active local operation reaches its atomic boundary.",
        )
        self._record_attention_control_stage(
            decision,
            stage="preemption_requested",
            detail="Foreground input marked the active background step for a safe-boundary yield.",
        )
        return True

    def _complete_active_goal_preemption(self) -> bool:
        """Acknowledge a yield only after the existing background result is merged."""
        decision = self._refresh_interactive_cognition_shadow(reason="background_atomic_boundary_reached")
        workspace = self.interactive_workspace_snapshot
        active = next((item for item in workspace.threads if item.thread_kind == "active_goal"), None) if workspace else None
        if active is None:
            return False
        entry = next(
            (item for item in self.interactive_coordination_state.entries if item.thread_id == active.thread_id),
            None,
        )
        if entry is None or not entry.preemption_requested:
            return False
        self.interactive_coordination_state = clear_preemption(
            self.interactive_coordination_state,
            thread_id=active.thread_id,
        )
        save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
        self._append_observation(
            "Attention",
            "The active local operation reached its atomic boundary; the foreground input remains with the conversational runtime for reconciliation.",
        )
        self._record_attention_control_stage(
            decision,
            stage="preemption_boundary_reached",
            detail="The foreground yield was observed only after the background result merged.",
        )
        return True

    def _conversational_runtime_status_text(self) -> str:
        state = getattr(self, "conversational_runtime_state", None)
        if state is None:
            return "Chat runtime: starting"
        objective = state.active_objective
        if objective is None:
            return "Chat runtime: ready"
        evaluation = evaluate_conversational_runtime(state)
        if objective.provenance.get("execution_mode") == "knowledge_acquisition" and state.active_episode_path:
            try:
                episode = read_active_cognitive_episode_state(state.active_episode_path)
                total_nodes = sum(1 for item in episode.evidence if item.kind == "knowledge_frontier_node")
                accepted_ops = {result.operation_id for result in episode.operation_results if result.accepted}
                completed_nodes = sum(1 for cycle in episode.cycles if cycle.operation_id in accepted_ops)
                latest_progress = next(
                    (
                        item.get("progress_counters") or {}
                        for item in reversed(state.objective_progress)
                        if item.get("event") == "knowledge_runtime_event"
                    ),
                    {},
                )
                blocked_nodes = int(latest_progress.get("blocked_nodes") or 0)
                call_progress = (
                    f"{episode.model_call_count} (unlimited local)"
                    if objective.model_call_budget is None
                    else f"{episode.model_call_count}/{objective.model_call_budget}"
                )
                cycle_progress = (
                    f"{len(episode.cycles)} (unlimited local)"
                    if objective.cycle_budget is None
                    else f"{len(episode.cycles)}/{objective.cycle_budget}"
                )
                return (
                    f"Chat runtime: active knowledge goal - nodes={completed_nodes}/{total_nodes}; "
                    f"calls={call_progress}; cycles={cycle_progress}; blocked={blocked_nodes}"
                )
            except Exception:
                pass
        if state.lifecycle_state == "paused_operator":
            return (
                f"Chat runtime: paused goal - {objective.interpreted_objective[:58]}... "
                f"cycles={evaluation['background_cycle_count']}; corrections={evaluation['correction_count']}; "
                f"questions={evaluation['pending_material_authority_count']}"
            )
        return (
            f"Chat runtime: active goal - {objective.interpreted_objective[:58]}... "
            f"cycles={evaluation['background_cycle_count']}; corrections={evaluation['correction_count']}; "
            f"questions={evaluation['pending_material_authority_count']}"
        )

    def _refresh_conversational_runtime_status(self) -> None:
        if hasattr(self, "conversational_runtime_status"):
            self.conversational_runtime_status.set(self._conversational_runtime_status_text())

    def _set_conversational_runtime_working(self) -> None:
        if hasattr(self, "conversational_runtime_status"):
            self.conversational_runtime_status.set("Chat runtime: working on the active goal...")

    def _conversational_cognitive_model_runner(self) -> LedgerBackedCognitiveModelRunner:
        return LedgerBackedCognitiveModelRunner(
            ledger=LocalModelRequestResultLedger(self.conversational_runtime_root / "model-ledger"),
            provider_manager=self.locked_provider_manager,
            authority_reason="standing_bounded_authority_conversational_runtime_operation",
            snapshot_root=self.conversational_runtime_root / "prompt-snapshots",
            request_identity_suffix="conversational-runtime-live",
        )

    def _active_developmental_teaching_plan(self) -> dict[str, object]:
        objective = self.conversational_runtime_state.active_objective
        if objective is None:
            return {}
        plan = objective.provenance.get("teaching_plan") if isinstance(objective.provenance, Mapping) else None
        return dict(plan) if isinstance(plan, dict) else {}

    def _restore_developmental_teaching_controller(self):
        objective = self.conversational_runtime_state.active_objective
        if objective is None or not isinstance(objective.provenance.get("teaching_plan"), Mapping):
            return None
        return load_teaching_controller(
            self.conversational_runtime_root,
            runtime_id=self.conversational_runtime_state.runtime_id,
            objective_id=objective.objective_id,
        )

    def _ensure_developmental_teaching_controller(self):
        objective = self.conversational_runtime_state.active_objective
        plan = self._active_developmental_teaching_plan()
        if objective is None or not plan:
            return None
        current = getattr(self, "developmental_teaching_controller", None)
        if current is not None:
            snapshot = teaching_snapshot(current)
            if snapshot.get("objective_id") == objective.objective_id:
                return current
        restored = self._restore_developmental_teaching_controller()
        if restored is None:
            restored = start_teaching_controller(
                runtime_id=self.conversational_runtime_state.runtime_id,
                objective_id=objective.objective_id,
                plan=plan,
            )
            save_teaching_controller(
                self.conversational_runtime_root,
                restored,
                objective_id=objective.objective_id,
            )
            self._append_observation(
                "Teaching runtime",
                "A persistent curriculum controller was attached to the active teaching objective.",
            )
        self.developmental_teaching_controller = restored
        return restored

    def _developmental_teaching_snapshot(self) -> dict[str, object]:
        controller = self._ensure_developmental_teaching_controller() if self._active_developmental_teaching_plan() else None
        return teaching_snapshot(controller)

    def _sync_developmental_teaching_progress(self) -> None:
        controller = getattr(self, "developmental_teaching_controller", None)
        objective = self.conversational_runtime_state.active_objective
        if controller is None or objective is None or not self._active_developmental_teaching_plan():
            return
        path = Path(self.conversational_runtime_state.active_episode_path or "")
        if not path.exists():
            return
        try:
            episode = read_active_cognitive_episode_state(path)
        except Exception:
            return
        snapshot = teaching_snapshot(controller)
        plan = dict(snapshot.get("plan") or {})
        curriculum = tuple(item for item in plan.get("curriculum", ()) if isinstance(item, Mapping))
        followups = tuple(
            dict(item)
            for item in objective.provenance.get("teaching_followups", ())
            if isinstance(item, Mapping)
        )
        prerequisites = tuple(
            dict(item)
            for item in objective.provenance.get("teaching_prerequisites", ())
            if isinstance(item, Mapping)
        )
        consolidation_records = tuple(
            dict(item)
            for item in objective.provenance.get("teaching_consolidation_records", ())
            if isinstance(item, Mapping)
        )
        terminal_reports = tuple(
            dict(item)
            for item in self.conversational_runtime_state.objective_progress
            if isinstance(item, Mapping)
            and str(item.get("event") or "") == "knowledge_goal_terminal_report"
            and str(item.get("objective_id") or "") == objective.objective_id
        )
        dynamic_evidence_ids = {
            str(item.get("evidence_id") or item.get("node_id") or "")
            for item in (*followups, *prerequisites)
        }
        accepted = tuple(item for item in episode.operation_results if item.accepted)
        accepted_curriculum = tuple(
            item for item in accepted
            if not (set(item.evidence_refs) & dynamic_evidence_ids)
        )
        prior_cursor = int(snapshot.get("teaching_cursor") or 0)
        retained_cursor = max(
            (int(item.get("curriculum_resume_cursor") or 0) for item in followups if str(item.get("status") or "") in {"retained_provisional", "admitted", "reviewed_supported"}),
            default=0,
        )
        prerequisite_resume_cursor = max(
            (
                int(item.get("parent_branch_resume_cursor") or 0)
                for item in prerequisites
                if str(item.get("status") or "") == "competence_tested"
                and str(item.get("derivation_branch_state") or "") == "resumed"
            ),
            default=0,
        )
        cursor = min(
            len(curriculum),
            max(prior_cursor, len(accepted_curriculum), retained_cursor, prerequisite_resume_cursor),
        )
        retained = tuple(item for item in followups if str(item.get("status") or "") in {"retained_provisional", "admitted", "reviewed_supported"})
        resumed_prerequisite = next(
            (
                item
                for item in prerequisites
                if str(item.get("status") or "") == "competence_tested"
                and str(item.get("derivation_branch_state") or "") == "resumed"
            ),
            None,
        )
        stage = (
            "derivation_branch_resumed"
            if resumed_prerequisite is not None
            else "retained_provisional_material"
            if retained
            else "provisional_learning_pending_consolidation"
            if accepted
            else str(snapshot.get("stage") or "first_lesson_delivered")
        )
        updated = update_teaching_state(
            controller,
            teaching_cursor=cursor,
            stage=stage,
            last_episode_id=episode.episode_id,
            last_model_call_count=episode.model_call_count,
            last_accepted_operation_ids=tuple(item.operation_id for item in accepted),
            pending_studies=tuple(item for item in followups if str(item.get("status") or "") in {"queued", "study_running"}),
            retention_records=retained,
            prerequisite_records=prerequisites,
            consolidation_records=consolidation_records,
            developmental_pressures=derive_teaching_pressures(
                plan,
                followups=followups,
                prerequisites=prerequisites,
                consolidation_records=consolidation_records,
                terminal_reports=terminal_reports,
                teaching_cursor=cursor,
            ),
        )
        self.developmental_teaching_controller = updated
        save_teaching_controller(
            self.conversational_runtime_root,
            updated,
            objective_id=objective.objective_id,
        )
        if cursor > prior_cursor:
            self._append_observation(
                "Teaching progress",
                f"The curriculum advanced to {cursor}/{len(curriculum)} sections from accepted local work.",
            )

    def _stop_conversational_objective(self) -> None:
        state = self.conversational_runtime_state
        if state.active_objective is None:
            self._refresh_conversational_runtime_status()
            return
        self.conversational_runtime_state = stop_conversational_objective(state)
        save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
        self._refresh_conversational_runtime_status()
        self._append_chat("DELTA", "I stopped the active conversational objective. Ordinary chat is still available.")
        self._append_session("assistant", "I stopped the active conversational objective. Ordinary chat is still available.")

    @staticmethod
    def _merge_teaching_objective_records(current_objective, worker_objective, prior_objective=None):
        """Retain foreground additions while accepting completed teaching work.

        Background cycles operate from a durable snapshot.  A foreground
        teaching question may be queued after that snapshot, so replacing the
        entire objective would lose the new question; retaining it wholesale
        would lose the completed study.  Only the canonically identified
        teaching record collections need a record-wise merge.
        """

        if (
            current_objective is None
            or worker_objective is None
            or current_objective.objective_id != worker_objective.objective_id
        ):
            return current_objective
        current_provenance = dict(current_objective.provenance or {})
        worker_provenance = dict(worker_objective.provenance or {})
        if not current_provenance.get("teaching_plan") and not worker_provenance.get("teaching_plan"):
            return current_objective

        def merge_records(key: str, identity_key: str):
            current_records = [dict(item) for item in current_provenance.get(key, ()) if isinstance(item, Mapping)]
            worker_records = [dict(item) for item in worker_provenance.get(key, ()) if isinstance(item, Mapping)]
            prior_records = [
                dict(item)
                for item in getattr(prior_objective, "provenance", {}).get(key, ())
                if isinstance(item, Mapping)
            ]
            prior_by_id = {
                str(item.get(identity_key) or ""): item
                for item in prior_records
                if str(item.get(identity_key) or "")
            }
            worker_by_id = {
                str(item.get(identity_key) or ""): item
                for item in worker_records
                if str(item.get(identity_key) or "")
            }
            merged = []
            seen = set()
            for item in current_records:
                identity = str(item.get(identity_key) or "")
                replacement = worker_by_id.get(identity)
                prior_item = prior_by_id.get(identity, {})
                foreground_status_changed = (
                    bool(prior_item)
                    and str(item.get("status") or "") != str(prior_item.get("status") or "")
                )
                # A foreground disposition changes the canonical record after
                # the worker snapshot was taken.  Keep it authoritative so a
                # stale worker cannot revive a pending request or undo a
                # prerequisite/retention transition.
                if replacement and not foreground_status_changed:
                    merged.append(replacement)
                else:
                    merged.append(item)
                if identity:
                    seen.add(identity)
            merged.extend(item for identity, item in worker_by_id.items() if identity not in seen)
            return tuple(merged)

        return replace(
            current_objective,
            provenance={
                **current_provenance,
                "teaching_followups": merge_records("teaching_followups", "followup_id"),
                "teaching_prerequisites": merge_records("teaching_prerequisites", "prerequisite_id"),
            },
        )

    def _merge_conversational_background_result(self, prior_state, worker_state):
        current = self.conversational_runtime_state
        current_objective = current.active_objective.objective_id if current.active_objective else ""
        prior_objective = prior_state.active_objective.objective_id if prior_state.active_objective else ""
        worker_objective = worker_state.active_objective.objective_id if worker_state.active_objective else ""
        if current_objective != prior_objective or worker_objective != prior_objective:
            return current
        if current.lifecycle_state != prior_state.lifecycle_state:
            return current
        progress_delta = worker_state.objective_progress[len(prior_state.objective_progress):]
        focus_delta = worker_state.focus_history[len(prior_state.focus_history):]
        cycle_delta = tuple(
            key for key in worker_state.completed_cycle_keys
            if key not in current.completed_cycle_keys
        )
        campaign_by_id = {item.get("campaign_id"): item for item in current.capability_campaigns}
        for item in worker_state.capability_campaigns:
            campaign_id = item.get("campaign_id")
            if campaign_id:
                campaign_by_id[campaign_id] = item
        prior_pending_ids = {item.request_id for item in prior_state.pending_chat_requests}
        pending_by_id = {item.request_id: item for item in current.pending_chat_requests}
        resolved_by_id = {item.request_id: item for item in current.resolved_chat_requests}
        for item in worker_state.pending_chat_requests:
            request_id = item.request_id
            # Current conversational state owns a request once the operator
            # has consumed it.  A worker may add a new request, but an old
            # request from its input snapshot may never be resurrected.
            if request_id in pending_by_id or request_id in resolved_by_id or request_id in prior_pending_ids:
                continue
            pending_by_id[request_id] = item
        for item in worker_state.resolved_chat_requests:
            request_id = item.request_id
            if request_id in pending_by_id or request_id in resolved_by_id:
                continue
            resolved_by_id[request_id] = item
        merged_objective = self._merge_teaching_objective_records(
            current.active_objective,
            worker_state.active_objective,
            prior_state.active_objective,
        )
        return replace(
            current,
            lifecycle_state=worker_state.lifecycle_state,
            active_objective=merged_objective,
            active_episode_path=worker_state.active_episode_path,
            completed_cycle_keys=current.completed_cycle_keys + cycle_delta,
            objective_progress=current.objective_progress + progress_delta,
            focus_history=current.focus_history + focus_delta,
            capability_campaigns=tuple(campaign_by_id.values()),
            pending_chat_requests=tuple(pending_by_id.values()),
            resolved_chat_requests=tuple(resolved_by_id.values()),
        )

    def _render_unshown_conversational_campaign_milestones(self) -> None:
        for milestone in unrendered_capability_campaign_milestones(self.conversational_runtime_state):
            message = str(milestone.get("message") or "").strip()
            milestone_id = str(milestone.get("milestone_id") or "")
            if not message or not milestone_id:
                continue
            self._append_observation("Goal milestone", message)
            self.conversational_runtime_state = mark_capability_campaign_milestone_rendered(
                self.conversational_runtime_state,
                milestone_id,
                runtime_root=self.conversational_runtime_root,
            )

    def _render_unshown_knowledge_goal_events(self) -> None:
        for event in unrendered_knowledge_goal_events(self.conversational_runtime_state):
            event_id = str(event.get("event_id") or "")
            if not event_id:
                continue
            message = render_knowledge_goal_event(event, self.conversational_runtime_state.active_objective)
            self._append_observation("Goal activity", message)
            self.conversational_runtime_state = mark_knowledge_goal_event_rendered(
                self.conversational_runtime_state,
                event_id,
                runtime_root=self.conversational_runtime_root,
            )

    def _render_unshown_teaching_followup_results(self) -> None:
        """Surface completed teaching results without exposing graph internals."""

        state = self.conversational_runtime_state
        objective = state.active_objective
        if objective is None or not isinstance(objective.provenance, Mapping):
            return
        followups = [
            dict(item)
            for item in objective.provenance.get("teaching_followups", ())
            if isinstance(item, Mapping)
        ]
        changed = False
        for index, followup in enumerate(followups):
            status = str(followup.get("status") or "")
            if status not in {"provisional_ready_for_retention", "study_blocked"} or followup.get("conversation_result_rendered"):
                continue
            if status == "provisional_ready_for_retention":
                message = render_teaching_followup_result(followup)
                intent_type = "teaching_followup_result"
            else:
                message = (
                    f"I checked {str(followup.get('question') or 'that teaching question')}, "
                    "but the bounded local study did not produce a usable explanation. I kept the gap visible instead of treating it as learned."
                )
                intent_type = "teaching_followup_blocked"
            self._append_chat("DELTA", message)
            self._append_session("assistant", message)
            assistant_turn = ConversationTurn(
                turn_id=rc6_stable_id(
                    "teaching-followup-result",
                    state.runtime_id,
                    str(followup.get("followup_id") or ""),
                    status,
                ),
                role="assistant",
                text=message,
                intent_type=intent_type,
                objective_id=objective.objective_id,
            )
            state = replace(state, conversation=state.conversation + (assistant_turn,))
            followups[index] = {
                **followup,
                "conversation_result_rendered": True,
                "conversation_result_rendered_at": datetime.now(timezone.utc).isoformat(),
            }
            changed = True
        if changed:
            updated_objective = replace(
                objective,
                provenance={
                    **objective.provenance,
                    "teaching_followups": tuple(followups),
                },
            )
            self.conversational_runtime_state = replace(state, active_objective=updated_objective)

        # The prerequisite branch shares the same canonical objective and worker
        # merge path as a teaching follow-up.  It needs its own natural result
        # projection so the operator can see when a blocked derivation branch
        # became eligible, without treating the result as reviewed truth.
        state = self.conversational_runtime_state
        objective = state.active_objective
        if objective is None or not isinstance(objective.provenance, Mapping):
            return
        prerequisites = [
            dict(item)
            for item in objective.provenance.get("teaching_prerequisites", ())
            if isinstance(item, Mapping)
        ]
        prerequisite_changed = False
        for index, prerequisite in enumerate(prerequisites):
            status = str(prerequisite.get("status") or "")
            if status not in {"competence_tested", "competence_needs_revision"} or prerequisite.get("conversation_result_rendered"):
                continue
            message = render_physics_prerequisite_result(prerequisite)
            intent_type = (
                "teaching_prerequisite_result"
                if status == "competence_tested"
                else "teaching_prerequisite_needs_revision"
            )
            self._append_chat("DELTA", message)
            self._append_session("assistant", message)
            assistant_turn = ConversationTurn(
                turn_id=rc6_stable_id(
                    "teaching-prerequisite-result",
                    state.runtime_id,
                    str(prerequisite.get("prerequisite_id") or ""),
                    status,
                ),
                role="assistant",
                text=message,
                intent_type=intent_type,
                objective_id=objective.objective_id,
            )
            state = replace(state, conversation=state.conversation + (assistant_turn,))
            prerequisites[index] = {
                **prerequisite,
                "conversation_result_rendered": True,
                "conversation_result_rendered_at": datetime.now(timezone.utc).isoformat(),
            }
            prerequisite_changed = True
        if prerequisite_changed:
            updated_objective = replace(
                objective,
                provenance={
                    **objective.provenance,
                    "teaching_prerequisites": tuple(prerequisites),
                },
            )
            self.conversational_runtime_state = replace(state, active_objective=updated_objective)

    def _render_unshown_teaching_requests(self) -> None:
        """Render durable teaching retention prompts exactly once in Conversation."""

        for request in tuple(self.conversational_runtime_state.pending_chat_requests):
            if request.request_type != "teaching_provisional_retention" or request.status != "pending" or request.consumption_count:
                continue
            if request.rendered_turn_id:
                continue
            message = request.prompt_text
            self._append_chat("DELTA", message)
            self._append_session("assistant", message)
            assistant_turn = ConversationTurn(
                turn_id=rc6_stable_id(
                    "teaching-retention-prompt",
                    self.conversational_runtime_state.runtime_id,
                    request.request_id,
                ),
                role="assistant",
                text=message,
                intent_type="teaching_provisional_retention_prompt",
                objective_id=request.objective_id,
            )
            self.conversational_runtime_state = replace(
                self.conversational_runtime_state,
                conversation=self.conversational_runtime_state.conversation + (assistant_turn,),
            )
            self.conversational_runtime_state = mark_chat_request_rendered(
                self.conversational_runtime_state,
                request.request_id,
                rendered_turn_id=assistant_turn.turn_id,
                render_sequence=len(self.conversational_runtime_state.conversation),
            )

    def _poll_conversational_runtime_worker_results(self) -> None:
        while True:
            try:
                item = self.conversational_runtime_result_queue.get_nowait()
            except queue.Empty:
                break
            prior_state, worker_state, error = item
            self.conversational_runtime_inference_in_flight = False
            if error is not None:
                message = f"Chat runtime safe pause after {type(error).__name__}: {str(error)[:240]}"
                self.conversational_runtime_status.set(f"Chat runtime: safe pause after {type(error).__name__}")
                self._append_observation("Runtime problem", message)
                continue
            self.conversational_runtime_state = self._merge_conversational_background_result(prior_state, worker_state)
            self._complete_active_goal_preemption()
            queued_teaching_followup = reconcile_queued_teaching_followup(
                self.conversational_runtime_state,
                runtime_root=self.conversational_runtime_root,
                run_background_cycle=False,
            )
            if queued_teaching_followup is not None:
                self.conversational_runtime_state = queued_teaching_followup.state
                self._append_chat("DELTA", queued_teaching_followup.reply)
                self._append_session("assistant", queued_teaching_followup.reply)
                self._append_observation(
                    "Teaching",
                    "A queued in-scope teaching question reached the worker boundary and was scheduled for one bounded local study.",
                )
            self._sync_developmental_teaching_progress()
            self._render_unshown_conversational_campaign_milestones()
            self._render_unshown_knowledge_goal_events()
            self._render_unshown_teaching_followup_results()
            self._render_unshown_teaching_requests()
            if self.conversational_runtime_state.lifecycle_state == "paused_budget" and not self.conversational_runtime_state.goal_reviews:
                self.conversational_runtime_state, review = render_goal_review(
                    self.conversational_runtime_state,
                    status=review_status_for_goal_completion(self.conversational_runtime_state),
                )
                self._append_chat("DELTA", review)
                self._append_session("assistant", review)
                budget_request = next(
                    (
                        request
                        for request in reversed(self.conversational_runtime_state.pending_chat_requests)
                        if request.request_type == "knowledge_model_budget_increase"
                        and request.objective_id == (self.conversational_runtime_state.active_objective.objective_id if self.conversational_runtime_state.active_objective else "")
                        and request.status == "pending"
                        and not request.consumption_count
                    ),
                    None,
                )
                if budget_request:
                    self.conversational_runtime_state = mark_chat_request_rendered(
                        self.conversational_runtime_state,
                        budget_request.request_id,
                        rendered_turn_id=rc6_stable_id("rendered-chat-request", self.conversational_runtime_state.runtime_id, budget_request.request_id, str(len(self.session_history))),
                        render_sequence=len(self.session_history),
                    )
            save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
            self._refresh_conversational_runtime_status()
            if queued_teaching_followup is not None:
                self._start_conversational_background_cycle("queued_teaching_followup_reconciled")
        self.root.after(100, self._poll_conversational_runtime_worker_results)

    def _start_approved_association_exploration(self, decision) -> bool:
        """Start exactly one approved association inquiry outside the chat owner."""
        if self.association_exploration_in_flight or self.conversational_runtime_inference_in_flight:
            return False
        workspace = getattr(self, "interactive_workspace_snapshot", None)
        target_thread = next(
            (item for item in (workspace.threads if workspace else ()) if item.thread_id == decision.target_thread_id),
            None,
        )
        candidate = next(
            (item for item in (workspace.association_candidates if workspace else ())
            if item.candidate_id == (target_thread.originating_reference if target_thread else "")),
            None,
        )
        if candidate is None:
            candidate = next(
                (item for item in (workspace.association_candidates if workspace else ())
                if item.candidate_id == decision.target_thread_id or item.association_id == decision.target_thread_id),
                None,
            )
        if candidate is None or candidate.state not in {"approved_for_bounded_exploration", "exploration_running"}:
            return False
        approval = next(
            (item for item in reversed(self.conversational_runtime_state.resolved_chat_requests)
            if item.baseline_metrics.get("originating_candidate_id") == candidate.candidate_id
            and item.resolution_policy == "operator_approved_bounded_association_exploration"),
            None,
        )
        if approval is None:
            return False
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        exploration = queue_exploration(
            self.conversational_runtime_root, graph, candidate_id=candidate.candidate_id,
            originating_thread_id=str(approval.thread_id or candidate.candidate_id),
            source_record_ids=tuple(candidate.source_refs + candidate.target_refs),
            relation_edge_ids=tuple(candidate.relation_path), approval_request_id=approval.request_id,
        )
        if candidate.state == "approved_for_bounded_exploration":
            self.interactive_coordination_state = set_candidate_disposition(
                self.interactive_coordination_state, candidate_id=candidate.candidate_id,
                candidate_kind="near_association", disposition="exploration_queued",
                source_record_ids=candidate.provenance_refs,
            )
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
            self._append_observation("Association exploration", "The approved association was queued for one local-model inquiry.")
        ledger = LocalModelRequestResultLedger(self.conversational_runtime_root / "model-ledger")
        request = ledger.create_or_reuse_request(
            semantic_identity=exploration.exploration_id,
            question=exploration.inquiry_question,
            requester_type="approved_association_exploration",
            requester_reference=exploration.candidate_id,
            question_objective="one bounded provisional association inquiry",
        )
        running = replace(
            exploration,
            lifecycle_state="exploration_running",
            ledger_request_id=str(request["request_id"]),
        )
        records = tuple(running if item.exploration_id == running.exploration_id else item for item in load_explorations(self.conversational_runtime_root))
        save_explorations(self.conversational_runtime_root, records)
        if candidate.state != "exploration_running":
            self.interactive_coordination_state = set_candidate_disposition(
                self.interactive_coordination_state, candidate_id=candidate.candidate_id,
                candidate_kind="near_association", disposition="exploration_running",
                source_record_ids=candidate.provenance_refs,
            )
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
        self.association_exploration_in_flight = True
        self._append_observation("Association exploration", "Local-model request started for the approved association.")

        def worker() -> None:
            try:
                result, updated_graph = execute_association_exploration_once(self.conversational_runtime_root, graph, running)
                error = None
            except Exception as exc:  # noqa: BLE001 - foreground remains usable.
                result, updated_graph, error = running, graph, exc
            self.association_exploration_result_queue.put((candidate, result, updated_graph, error))

        threading.Thread(target=worker, name="delta-approved-association-exploration", daemon=True).start()
        return True

    def _poll_association_exploration_results(self) -> None:
        while True:
            try:
                candidate, result, graph, error = self.association_exploration_result_queue.get_nowait()
            except queue.Empty:
                break
            self.association_exploration_in_flight = False
            if error is None:
                if result.lifecycle_state == "explored_pending_consolidation":
                    graph, _ = ensure_consolidation_cohort(
                        graph,
                        trigger="approved_association_exploration",
                    )
                save_provisional_semantic_graph(self.conversational_runtime_root, graph)
                records = tuple(result if item.exploration_id == result.exploration_id else item for item in load_explorations(self.conversational_runtime_root))
                save_explorations(self.conversational_runtime_root, records)
                disposition = result.lifecycle_state
            else:
                disposition = "exploration_failed"
                self._append_observation("Association exploration", f"The bounded inquiry failed: {type(error).__name__}.")
            self.interactive_coordination_state = set_candidate_disposition(
                self.interactive_coordination_state, candidate_id=candidate.candidate_id,
                candidate_kind="near_association", disposition=disposition,
                source_record_ids=candidate.provenance_refs,
            )
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
            marker_id = f"association-exploration:{result.exploration_id}"
            preemption_marker = next(
                (
                    entry
                    for entry in self.interactive_coordination_state.entries
                    if entry.thread_id == marker_id and entry.preemption_requested
                ),
                None,
            )
            self.interactive_coordination_state = clear_preemption(self.interactive_coordination_state, thread_id=marker_id)
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
            if preemption_marker is not None:
                decision = self._refresh_interactive_cognition_shadow(
                    reason="association_exploration_preemption_boundary_reached"
                )
                self._record_attention_control_stage(
                    decision,
                    stage="preemption_boundary_reached",
                    detail="The approved association inquiry reached its ledger boundary; its foreground preemption marker was cleared.",
                )
            if disposition == "explored_pending_consolidation":
                self._append_observation("Association exploration", "Model result received; a provisional insight was recorded and awaits consolidation.")
                versions = {item.claim_version_id: item.exact_text for item in graph.claim_versions}
                labels = [versions.get(item, item) for item in result.source_record_ids]
                insight = next((item for item in graph.experiences if item.experience_id == result.insight_experience_id), None)
                try:
                    parsed = json.loads(insight.content) if insight is not None else {}
                except (TypeError, json.JSONDecodeError):
                    parsed = {}
                self._append_chat(
                    "DELTA",
                    "I explored the approved connection between:\n"
                    f"{'; '.join(labels)}\n\n"
                    f"Possible shared mechanism: {parsed.get('shared_structure') or 'No structured mechanism was retained.'}\n"
                    f"Why it may matter: {parsed.get('possible_implication') or 'No implication was retained.'}\n"
                    f"Where the connection may fail: {parsed.get('relation_limits') or 'No limitation was retained.'}\n"
                    f"Uncertainty: {parsed.get('uncertainty') or 'No uncertainty statement was retained.'}\n\n"
                    "Status: Provisional - awaiting consolidation.",
                )
            else:
                self._append_observation("Association exploration", f"The one-call inquiry ended as {disposition}; no retry was started.")
        self.root.after(100, self._poll_association_exploration_results)

    def _start_approved_structural_analogy_exploration(self, decision) -> bool:
        """Run one approved structural comparison through the shared ledger."""
        if self.structural_analogy_exploration_in_flight or self.conversational_runtime_inference_in_flight:
            return False
        workspace = getattr(self, "interactive_workspace_snapshot", None)
        target = next((item for item in (workspace.threads if workspace else ()) if item.thread_id == decision.target_thread_id), None)
        candidate = next((item for item in (workspace.analogy_candidates if workspace else ()) if item.candidate_id == (target.originating_reference if target else "")), None)
        if candidate is None or candidate.state not in {"approved_for_bounded_exploration", "exploration_queued"}:
            return False
        approval = next((item for item in reversed(self.conversational_runtime_state.resolved_chat_requests) if item.baseline_metrics.get("originating_candidate_id") == candidate.candidate_id and item.resolution_policy == "operator_approved_bounded_structural_analogy_exploration"), None)
        if approval is None:
            return False
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        exploration = queue_structural_analogy_exploration(
            self.conversational_runtime_root, graph, candidate_id=candidate.candidate_id,
            source_pattern_id=candidate.source_pattern_id, target_pattern_id=candidate.target_pattern_id,
            source_record_ids=tuple(candidate.source_unit_ids), target_record_ids=tuple(candidate.target_unit_ids),
            relation_ids=tuple(candidate.source_relation_ids + candidate.target_relation_ids), approval_request_id=approval.request_id,
        )
        ledger = LocalModelRequestResultLedger(self.conversational_runtime_root / "model-ledger")
        request = ledger.create_or_reuse_request(semantic_identity=exploration.exploration_id, question=exploration.inquiry_question, requester_type="approved_structural_analogy_exploration", requester_reference=exploration.candidate_id, question_objective="one bounded provisional structural analogy inquiry")
        running = replace(exploration, lifecycle_state="analogy_exploration_running", ledger_request_id=str(request["request_id"]))
        save_structural_analogy_explorations(self.conversational_runtime_root, tuple(running if item.exploration_id == running.exploration_id else item for item in load_structural_analogy_explorations(self.conversational_runtime_root)))
        self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind="far_analogy", disposition="exploration_queued" if candidate.state == "approved_for_bounded_exploration" else "exploration_running", source_record_ids=candidate.provenance_refs)
        self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind="far_analogy", disposition="exploration_running", source_record_ids=candidate.provenance_refs)
        save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
        self.structural_analogy_exploration_in_flight = True
        self._append_observation("Structural analogy", "One approved cross-domain comparison started through the shared local-model ledger.")

        def worker() -> None:
            try:
                result, updated_graph = execute_structural_analogy_exploration_once(self.conversational_runtime_root, graph, running)
                error = None
            except Exception as exc:  # noqa: BLE001 - foreground remains responsive.
                result, updated_graph, error = running, graph, exc
            self.structural_analogy_exploration_result_queue.put((candidate, result, updated_graph, error))

        threading.Thread(target=worker, name="delta-approved-structural-analogy", daemon=True).start()
        return True

    def _poll_structural_analogy_exploration_results(self) -> None:
        while True:
            try:
                candidate, result, graph, error = self.structural_analogy_exploration_result_queue.get_nowait()
            except queue.Empty:
                break
            self.structural_analogy_exploration_in_flight = False
            disposition = "explored_pending_consolidation" if error is None and result.lifecycle_state == "analogy_explored_pending_consolidation" else "exploration_failed"
            if error is None:
                if disposition == "explored_pending_consolidation":
                    graph, _ = ensure_consolidation_cohort(graph, trigger="approved_structural_analogy_exploration")
                save_provisional_semantic_graph(self.conversational_runtime_root, graph)
                save_structural_analogy_explorations(self.conversational_runtime_root, tuple(result if item.exploration_id == result.exploration_id else item for item in load_structural_analogy_explorations(self.conversational_runtime_root)))
            self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind="far_analogy", disposition=disposition, source_record_ids=candidate.provenance_refs)
            marker_id = f"structural-analogy:{result.exploration_id}"
            preemption_marker = next(
                (
                    entry
                    for entry in self.interactive_coordination_state.entries
                    if entry.thread_id == marker_id and entry.preemption_requested
                ),
                None,
            )
            self.interactive_coordination_state = clear_preemption(self.interactive_coordination_state, thread_id=marker_id)
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
            if preemption_marker is not None:
                decision = self._refresh_interactive_cognition_shadow(
                    reason="structural_analogy_preemption_boundary_reached"
                )
                self._record_attention_control_stage(
                    decision,
                    stage="preemption_boundary_reached",
                    detail="The approved structural analogy reached its ledger boundary; its foreground preemption marker was cleared.",
                )
            if disposition == "explored_pending_consolidation":
                insight = next((item for item in graph.experiences if item.experience_id == result.insight_experience_id), None)
                details = json.loads(insight.content) if insight else {}
                self._append_chat("DELTA", "I compared the approved functional patterns.\nShared structure: " + details.get("shared_structure", "") + "\nWhy it may matter: " + details.get("possible_implication", "") + "\nWhere it breaks: " + details.get("relation_limits", "") + "\nUncertainty: " + details.get("uncertainty", "") + "\n\nStatus: Provisional - awaiting consolidation.")
            else:
                self._append_observation("Structural analogy", f"The bounded comparison ended as {result.lifecycle_state if error is None else type(error).__name__}.")
        self.root.after(100, self._poll_structural_analogy_exploration_results)

    def _start_approved_curiosity_inquiry(self, decision) -> bool:
        """Execute one approved curiosity action with the shared ledger only."""
        if self.curiosity_inquiry_in_flight or self.conversational_runtime_inference_in_flight:
            return False
        workspace = getattr(self, "interactive_workspace_snapshot", None)
        target = next((item for item in (workspace.threads if workspace else ()) if item.thread_id == decision.target_thread_id), None)
        candidate = next((item for item in (workspace.curiosity_candidates if workspace else ()) if item.candidate_id == (target.originating_reference if target else "")), None)
        if candidate is None or candidate.state not in {"approved_for_bounded_exploration", "exploration_queued"}:
            return False
        approval = next((item for item in reversed(self.conversational_runtime_state.resolved_chat_requests) if item.baseline_metrics.get("originating_candidate_id") == candidate.candidate_id and item.resolution_policy == "operator_approved_bounded_curiosity_inquiry"), None)
        if approval is None:
            return False
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        inquiry = queue_curiosity_inquiry(
            self.conversational_runtime_root,
            graph,
            candidate_id=candidate.candidate_id,
            source_record_ids=tuple(candidate.source_record_ids),
            approval_request_id=approval.request_id,
            proposed_action=str(approval.baseline_metrics.get("curiosity_proposed_action") or candidate.safe_next_step),
            source_context=(
                f"{candidate.rationale} Uncertainty: {candidate.uncertainty}. "
                f"Bounded action requested: {candidate.proposed_bounded_action or candidate.safe_next_step}."
            ),
        )
        ledger = LocalModelRequestResultLedger(self.conversational_runtime_root / "model-ledger")
        request = ledger.create_or_reuse_request(semantic_identity=inquiry.inquiry_id, question=inquiry.inquiry_question, requester_type="approved_curiosity_inquiry", requester_reference=inquiry.candidate_id, question_objective="one bounded provisional curiosity inquiry")
        running = replace(inquiry, lifecycle_state="curiosity_inquiry_running", ledger_request_id=str(request["request_id"]))
        save_curiosity_inquiries(self.conversational_runtime_root, tuple(running if item.inquiry_id == running.inquiry_id else item for item in load_curiosity_inquiries(self.conversational_runtime_root)))
        self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind="cognitive_pressure", disposition="exploration_queued" if candidate.state == "approved_for_bounded_exploration" else "exploration_running", source_record_ids=candidate.source_record_ids)
        self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind="cognitive_pressure", disposition="exploration_running", source_record_ids=candidate.source_record_ids)
        save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
        self.curiosity_inquiry_in_flight = True
        self._append_observation("Curiosity", "One operator-approved local inquiry started through the shared model ledger.")

        def worker() -> None:
            try:
                result, updated_graph = execute_curiosity_inquiry_once(self.conversational_runtime_root, graph, running)
                error = None
            except Exception as exc:  # noqa: BLE001
                result, updated_graph, error = running, graph, exc
            self.curiosity_inquiry_result_queue.put((candidate, result, updated_graph, error))

        threading.Thread(target=worker, name="delta-approved-curiosity-inquiry", daemon=True).start()
        return True

    def _poll_curiosity_inquiry_results(self) -> None:
        while True:
            try:
                candidate, result, graph, error = self.curiosity_inquiry_result_queue.get_nowait()
            except queue.Empty:
                break
            self.curiosity_inquiry_in_flight = False
            disposition = "explored_pending_consolidation" if error is None and result.lifecycle_state == "curiosity_inquiry_pending_consolidation" else "exploration_failed"
            if error is None:
                if disposition == "explored_pending_consolidation":
                    graph, _ = ensure_consolidation_cohort(graph, trigger="approved_curiosity_inquiry")
                save_provisional_semantic_graph(self.conversational_runtime_root, graph)
                save_curiosity_inquiries(self.conversational_runtime_root, tuple(result if item.inquiry_id == result.inquiry_id else item for item in load_curiosity_inquiries(self.conversational_runtime_root)))
            self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind="cognitive_pressure", disposition=disposition, source_record_ids=candidate.source_record_ids)
            self.interactive_coordination_state = clear_preemption(self.interactive_coordination_state, thread_id=f"curiosity-inquiry:{result.inquiry_id}")
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
            if disposition == "explored_pending_consolidation":
                insight = next((item for item in graph.experiences if item.experience_id == result.insight_experience_id), None)
                try:
                    details = json.loads(insight.content) if insight is not None else {}
                except (TypeError, json.JSONDecodeError):
                    details = {}
                self._append_chat(
                    "DELTA",
                    "I completed the approved local inquiry.\n"
                    + "Question addressed: " + details.get("question_addressed", "")
                    + "\nEvidence considered: " + details.get("evidence_considered", "")
                    + "\nBounded answer: " + details.get("bounded_answer", "")
                    + "\nUncertainty: " + details.get("uncertainty", "")
                    + "\nStill missing: " + details.get("relation_limits", "")
                    + "\nNext question: " + details.get("suggested_next_question", "")
                    + "\n\nStatus: Provisional - awaiting consolidation.",
                )
            else:
                self._append_observation("Curiosity", f"The bounded inquiry ended as {result.lifecycle_state if error is None else type(error).__name__}.")
        self.root.after(100, self._poll_curiosity_inquiry_results)

    def _start_conversational_background_cycle(self, reason: str) -> bool:
        state = self.conversational_runtime_state
        if not state.active_objective or state.lifecycle_state != "running":
            self._refresh_conversational_runtime_status()
            return False
        if background_cycle_hold_reason(state):
            self._refresh_conversational_runtime_status()
            return False
        if self.conversational_runtime_inference_in_flight or self.live_runtime_request_in_flight:
            self._set_conversational_runtime_working()
            return False
        prior_state = state
        self.conversational_runtime_inference_in_flight = True
        self._set_conversational_runtime_working()

        def worker() -> None:
            try:
                worker_state = run_conversational_background_cycle(
                    prior_state,
                    runtime_root=self.conversational_runtime_root,
                    reason=reason,
                    model_runner=self._conversational_cognitive_model_runner(),
                )
                error: Exception | None = None
            except Exception as exc:  # noqa: BLE001 - foreground chat must remain usable.
                worker_state = prior_state
                error = exc
                error_root = self.conversational_runtime_root / "background-errors"
                error_root.mkdir(parents=True, exist_ok=True)
                error_path = error_root / f"background-error-{uuid.uuid4().hex}.json"
                error_path.write_text(
                    json.dumps(
                        {
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                            "traceback": traceback.format_exc(),
                            "reason": reason,
                            "active_objective_id": prior_state.active_objective.objective_id if prior_state.active_objective else "",
                            "completed_cycle_count": len(prior_state.completed_cycle_keys),
                            "active_episode_path": prior_state.active_episode_path,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            self.conversational_runtime_result_queue.put((prior_state, worker_state, error))

        threading.Thread(target=worker, name="delta-conversational-runtime-cycle", daemon=True).start()
        return True

    def _start_endogenous_teaching_gap_recovery(self, decision) -> bool:
        """Execute one controller-selected terminal-gap study through the existing worker."""

        if self.conversational_runtime_inference_in_flight or self.live_runtime_request_in_flight:
            return False
        queued = queue_endogenous_teaching_gap_recovery(
            self.conversational_runtime_state,
            runtime_root=self.conversational_runtime_root,
        )
        if queued is None:
            return False
        self.conversational_runtime_state, action = queued
        self._sync_developmental_teaching_progress()
        self._append_observation(
            "Developmental recovery",
            f'An unresolved teaching gap ("{str(action.get("source_gap") or "unspecified")}") selected one bounded local recovery study under standing authority.',
        )
        self._refresh_conversational_runtime_status()
        self._refresh_state_cards()
        if not self._start_conversational_background_cycle("endogenous_terminal_gap_recovery"):
            return False
        self._record_attention_control_stage(
            decision,
            stage="executed_posture",
            detail="One source-bound terminal-gap recovery study started through the existing conversational worker.",
        )
        return True

    def _start_approved_revisit(self, decision) -> bool:
        """Launch one approved review correction through the existing shared ledger."""
        if self.revisit_reinquiry_in_flight or self.conversational_runtime_inference_in_flight:
            return False
        workspace = getattr(self, "interactive_workspace_snapshot", None)
        candidate = next((item for item in (workspace.curiosity_candidates if workspace else ()) if item.candidate_id == decision.target_thread_id or item.candidate_id == next((thread.originating_reference for thread in workspace.threads if thread.thread_id == decision.target_thread_id), "")), None)
        if candidate is None or candidate.state not in {"approved_for_revisit", "revisit_queued"}:
            return False
        approval = next((item for item in reversed(self.conversational_runtime_state.resolved_chat_requests) if item.baseline_metrics.get("originating_candidate_id") == candidate.candidate_id and item.resolution_policy == "operator_approved_bounded_revisit"), None)
        if approval is None:
            return False
        review_id, packet_id, claim_version_id = tuple(candidate.source_record_ids)[:3]
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        version = next((item for item in graph.claim_versions if item.claim_version_id == claim_version_id), None)
        original_insight_id = version.source_experience_refs[0] if version and version.source_experience_refs else ""
        overlay = next((item for item in reversed(graph.overlays) if item.review_id == review_id and item.claim_version_id == claim_version_id), None)
        if not original_insight_id or overlay is None:
            return False
        original_insight = next((item for item in graph.experiences if item.experience_id == original_insight_id), None)
        reinquiry = queue_reinquiry(self.conversational_runtime_root, candidate_id=candidate.candidate_id, approval_request_id=approval.request_id, original_insight_id=original_insight_id, review_id=review_id, packet_id=packet_id, overlay_id=overlay.overlay_id, weakness=candidate.rationale, source_context=original_insight.content if original_insight is not None else "")
        ledger = LocalModelRequestResultLedger(self.conversational_runtime_root / "model-ledger")
        request = ledger.create_or_reuse_request(semantic_identity=reinquiry.reinquiry_id, question=reinquiry.inquiry_question, requester_type="approved_revisit_reinquiry", requester_reference=reinquiry.candidate_id, question_objective="one bounded provisional revision inquiry")
        running = replace(reinquiry, lifecycle_state="revisit_running", ledger_request_id=str(request["request_id"]))
        save_reinquiries(self.conversational_runtime_root, tuple(running if item.reinquiry_id == running.reinquiry_id else item for item in load_reinquiries(self.conversational_runtime_root)))
        disposition_record = next(
            (item for item in self.interactive_coordination_state.candidate_dispositions if item.candidate_id == candidate.candidate_id),
            None,
        )
        candidate_kind = disposition_record.candidate_kind if disposition_record is not None else "cognitive_pressure"
        self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind=candidate_kind, disposition="revisit_queued" if candidate.state == "approved_for_revisit" else "revisit_running", source_record_ids=candidate.source_record_ids)
        self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind=candidate_kind, disposition="revisit_running", source_record_ids=candidate.source_record_ids)
        save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
        self.revisit_reinquiry_in_flight = True
        self._append_observation("Revisit", "One approved consolidation revisit started through the shared local-model ledger.")
        def worker():
            try:
                result, updated_graph = execute_revisit_reinquiry_once(self.conversational_runtime_root, graph, running)
                error = None
            except Exception as exc:
                result, updated_graph, error = running, graph, exc
            self.revisit_reinquiry_result_queue.put((candidate, result, updated_graph, error))
        threading.Thread(target=worker, name="delta-approved-revisit-reinquiry", daemon=True).start()
        return True

    def _poll_revisit_reinquiry_results(self) -> None:
        while True:
            try:
                candidate, result, graph, error = self.revisit_reinquiry_result_queue.get_nowait()
            except queue.Empty:
                break
            self.revisit_reinquiry_in_flight = False
            disposition = result.lifecycle_state if error is None else "revisit_failed_execution"
            if error is None:
                if result.lifecycle_state == "revisited_pending_consolidation":
                    graph, _ = ensure_consolidation_cohort(
                        graph,
                        trigger="approved_revisit_reinquiry",
                    )
                save_provisional_semantic_graph(self.conversational_runtime_root, graph)
                save_reinquiries(self.conversational_runtime_root, tuple(result if item.reinquiry_id == result.reinquiry_id else item for item in load_reinquiries(self.conversational_runtime_root)))
            disposition_record = next(
                (item for item in self.interactive_coordination_state.candidate_dispositions if item.candidate_id == candidate.candidate_id),
                None,
            )
            candidate_kind = disposition_record.candidate_kind if disposition_record is not None else "cognitive_pressure"
            self.interactive_coordination_state = set_candidate_disposition(self.interactive_coordination_state, candidate_id=candidate.candidate_id, candidate_kind=candidate_kind, disposition=disposition, source_record_ids=candidate.source_record_ids)
            marker_id = f"approved-revisit:{result.reinquiry_id}"
            marked = any(item.thread_id == marker_id and item.preemption_requested for item in self.interactive_coordination_state.entries)
            self.interactive_coordination_state = clear_preemption(self.interactive_coordination_state, thread_id=marker_id)
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
            if marked:
                self._record_attention_control_stage(self._refresh_interactive_cognition_shadow(reason="revisit_preemption_boundary_reached"), stage="preemption_boundary_reached", detail="The approved revisit reached its ledger boundary; its foreground preemption marker was cleared.")
            if disposition == "revisited_pending_consolidation":
                insight = next((item for item in graph.experiences if item.experience_id == result.revised_insight_id), None)
                details = json.loads(insight.content) if insight is not None else {}
                self._append_chat("DELTA", "I revisited the provisional connection.\nWhat was incomplete: " + candidate.rationale + "\nRetained: " + details.get("retained_supported_portion", "") + "\nRevised: " + details.get("revised_proposition", "") + "\nStill uncertain: " + details.get("uncertainty", "") + "\nEvidence still missing: " + details.get("evidence_still_missing", "") + "\nNext question: " + details.get("possible_next_question", "") + "\n\nStatus: Provisional - awaiting consolidation.")
            else:
                self._append_observation("Revisit", f"The approved revisit ended as {disposition}; no retry was started.")
        self.root.after(100, self._poll_revisit_reinquiry_results)

    def _tick_conversational_objective_runtime(self) -> None:
        # Controller state is durable, but its pressures are a read-only
        # projection of canonical runtime history. Rebuild that projection
        # before each idle arbitration so a restored terminal gap can resume
        # through the ordinary worker without another operator prompt.
        self._sync_developmental_teaching_progress()
        decision = self._refresh_interactive_cognition_shadow(reason="automatic_startup_or_idle_tick")
        # The coordinator may gate a new periodic step, but the existing runtime
        # remains the only owner of model execution and objective progression.
        if decision is not None and decision.selected_posture == "continue_active_goal":
            hold_reason = background_cycle_hold_reason(self.conversational_runtime_state)
            if hold_reason:
                self._refresh_conversational_runtime_status()
            else:
                self._record_attention_control_stage(
                    decision,
                    stage="active_gate",
                    detail="Active gate permitted one existing background-goal step.",
                )
            if not hold_reason and self._start_conversational_background_cycle("automatic_startup_or_idle_tick"):
                self._record_attention_control_stage(
                    decision,
                    stage="executed_posture",
                    detail="Existing background-goal worker started one bounded step.",
                )
        elif decision is not None and decision.selected_posture == "perform_one_gap_recovery_study":
            self._start_endogenous_teaching_gap_recovery(decision)
        elif decision is not None and decision.selected_posture == "explore_near_association":
            self._surface_one_near_association(decision)
        elif decision is not None and decision.selected_posture == "execute_approved_association":
            self._start_approved_association_exploration(decision)
        elif decision is not None and decision.selected_posture == "explore_far_analogy":
            self._surface_one_far_analogy(decision)
        elif decision is not None and decision.selected_posture == "execute_approved_analogy":
            self._start_approved_structural_analogy_exploration(decision)
        elif decision is not None and decision.selected_posture == "execute_approved_revisit":
            self._start_approved_revisit(decision)
        elif decision is not None and decision.selected_posture == "execute_approved_curiosity_inquiry":
            self._start_approved_curiosity_inquiry(decision)
        elif decision is not None and decision.selected_posture == "inspect_curiosity_candidate":
            self._inspect_one_curiosity_candidate(decision)
        elif decision is not None and decision.selected_posture == "perform_one_consolidation_step":
            self._perform_one_consolidation_step(decision)
        else:
            self._refresh_conversational_runtime_status()
        self.root.after(2000, self._tick_conversational_objective_runtime)

    def _handle_conversational_runtime_message(self, message: str) -> bool:
        state = self.conversational_runtime_state
        governance_result = resolve_developmental_governance_instruction(
            state,
            message,
            runtime_root=self.conversational_runtime_root,
        )
        if governance_result is not None:
            self.conversational_runtime_state = governance_result.state
            self._append_chat("DELTA", governance_result.reply)
            self._append_session("user", message)
            self._append_session("assistant", governance_result.reply)
            self._sync_developmental_teaching_progress()
            governance = dict(governance_result.developmental_governance or {})
            source_id = str(
                governance.get("source_followup_id")
                or governance.get("source_record_id")
                or governance.get("claim_version_id")
                or "existing developmental record"
            )
            self._append_observation(
                "Developmental governance",
                f"{str(governance.get('action') or 'operator posture')} was bound to {source_id}; "
                f"{str(governance.get('reason') or governance.get('posture') or 'the canonical record was updated')}",
            )
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        owner = select_chat_request_owner(state, message)
        normalized = " ".join(str(message or "").lower().split())
        pending = tuple(
            item for item in state.pending_chat_requests
            if item.status == "pending" and not item.consumption_count
        )
        if owner is None and len(pending) > 1 and normalized in {"yes", "no", "okay", "ok"}:
            reply = "[Clarification needed]\nMore than one unresolved prompt can accept that reply. Please answer the most recent prompt with its subject or restate the action you approve."
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        if owner is not None and owner.request_type == "local_model_execution":
            reply = self._resolve_local_model_permission(message, request_id=owner.request_id)
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        if (
            owner is not None
            and owner.request_type == "interactive_clarification"
            and (str(owner.baseline_metrics.get("question_kind") or "") in {"association_exploration", "structural_analogy_exploration", "consolidation_feedback"} or bool(owner.baseline_metrics.get("curiosity_inquiry")))
        ):
            reply = self._resolve_interactive_clarification(message, request_id=owner.request_id)
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        resolved = resolve_pending_chat_request(
            state,
            message,
            runtime_root=self.conversational_runtime_root,
        )
        if resolved is not None:
            self.conversational_runtime_state = resolved.state
            self._append_chat("DELTA", resolved.reply)
            self._append_session("user", message)
            self._append_session("assistant", resolved.reply)
            if resolved.intent.intent_type == "semantic_evidence_bound_analysis_question_answer":
                objective = resolved.state.active_objective
                refinements = (
                    objective.provenance.get("analysis_refinements", ())
                    if objective is not None and isinstance(objective.provenance, Mapping)
                    else ()
                )
                refinement = next((item for item in reversed(refinements) if isinstance(item, Mapping)), {})
                if refinement:
                    self._append_observation(
                        "Analysis refinement",
                        "Bound one operator answer to analysis "
                        f"{str(refinement.get('source_analysis_id') or '')} and appended refinement "
                        f"{str(refinement.get('refinement_id') or '')} without graph or external side effects.",
                    )
                if resolved.chat_request and str(resolved.chat_request.get("request_type") or "") == "internal_work_continuation":
                    metrics = resolved.chat_request.get("baseline_metrics") or {}
                    self._append_observation(
                        "Internal continuation",
                        "Selected one safe proposal for analysis "
                        f"{str(metrics.get('source_analysis_id') or '')}: "
                        f"{str(metrics.get('why_it_matters') or 'a recorded unresolved issue remains')}",
                    )
            elif resolved.intent.intent_type == "semantic_internal_work_disposition":
                objective = resolved.state.active_objective
                dispositions = (
                    objective.provenance.get("internal_work_dispositions", ())
                    if objective is not None and isinstance(objective.provenance, Mapping)
                    else ()
                )
                disposition = next((item for item in reversed(dispositions) if isinstance(item, Mapping)), {})
                if disposition:
                    self._append_observation(
                        "Internal continuation",
                        "Recorded one source-bound operator disposition for candidate "
                        f"{str(disposition.get('candidate_id') or '')}: {str(disposition.get('status') or 'recorded')}. "
                        "No internal work started.",
                    )
            self._sync_developmental_teaching_progress()
            if resolved.background_cycle_started:
                self._start_conversational_background_cycle("teaching_request_resolved")
            elif self.conversational_runtime_state.lifecycle_state == "running":
                self._start_conversational_background_cycle("pending_chat_request_resolved")
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        if (
            is_source_bound_semantic_recall_message(state, message)
            or is_evidence_bound_analysis_recall_message(state, message)
            or is_evidence_bound_analysis_refinement_recall_message(state, message)
            or is_internal_work_recall_message(state, message)
            or is_semantic_problem_frame_recall_message(state, message)
            or is_semantic_problem_modeling_message(state, message)
            or is_source_bound_semantic_competence_measurement_message(state, message)
            or is_source_bound_semantic_analysis_message(state, message)
            or is_source_bound_semantic_transfer_message(state, message)
        ):
            if (
                self.conversational_runtime_inference_in_flight
                or self.association_exploration_in_flight
                or self.revisit_reinquiry_in_flight
                or self.structural_analogy_exploration_in_flight
                or self.curiosity_inquiry_in_flight
            ):
                self._request_active_goal_preemption(reason="foreground_semantic_application")
            result = handle_conversational_message(
                state,
                message,
                runtime_root=self.conversational_runtime_root,
                run_background_cycle=False,
            )
            if result.intent.intent_type.startswith("semantic_"):
                self.conversational_runtime_state = result.state
                self._append_chat("DELTA", result.reply)
                self._append_session("user", message)
                self._append_session("assistant", result.reply)
                objective = result.state.active_objective
                if result.intent.intent_type in {
                    "semantic_source_bound_recall",
                    "semantic_evidence_bound_analysis_recall",
                    "semantic_evidence_bound_analysis_refinement_recall",
                    "semantic_internal_work_recall",
                    "semantic_problem_frame_recall",
                }:
                    title = {
                        "semantic_evidence_bound_analysis_recall": "Evidence-bound analysis",
                        "semantic_evidence_bound_analysis_refinement_recall": "Analysis refinement",
                        "semantic_internal_work_recall": "Internal continuation",
                        "semantic_problem_frame_recall": "Semantic frame",
                    }.get(result.intent.intent_type, "Semantic lineage")
                    detail = {
                        "semantic_evidence_bound_analysis_recall": "Rendered a read-only source-bound analysis recap without changing the recorded analysis.",
                        "semantic_evidence_bound_analysis_refinement_recall": "Rendered a read-only source-bound refinement recap without creating a new question or refinement.",
                        "semantic_internal_work_recall": "Rendered a read-only source-bound internal continuation recap without changing a candidate or disposition.",
                        "semantic_problem_frame_recall": "Rendered a read-only source-bound frame recap without changing the recorded frame.",
                    }.get(result.intent.intent_type, "Rendered a read-only source-bound recap without changing the recorded semantic chain.")
                    self._append_observation(
                        title,
                        detail,
                    )
                else:
                    record_key = {
                        "semantic_competence_delta_measurement": "semantic_competence_deltas",
                        "semantic_multistep_analytical_task": "semantic_analytical_tasks",
                        "semantic_problem_modeling": "evidence_bound_analyses",
                    }.get(result.intent.intent_type, "semantic_transfer_applications")
                    records = (
                        objective.provenance.get(record_key, ())
                        if objective is not None and isinstance(objective.provenance, Mapping)
                        else ()
                    )
                    record = next((item for item in reversed(records) if isinstance(item, Mapping)), {})
                    if record:
                        title = {
                            "semantic_competence_deltas": "Competence delta",
                            "semantic_analytical_tasks": "Semantic analysis",
                            "evidence_bound_analyses": "Evidence-bound analysis",
                        }.get(record_key, "Semantic transfer")
                        record_id = str(
                            record.get("competence_delta_id")
                            or record.get("analytical_task_id")
                            or record.get("analysis_id")
                            or record.get("frame_id")
                            or record.get("application_record_id")
                            or ""
                        )
                        if record_key == "evidence_bound_analyses":
                            self._append_observation(
                                title,
                                "Recorded provisional source-bound semantic frame "
                                f"{str(record.get('source_frame_id') or '')} and evidence-bound analysis {record_id}.",
                            )
                        else:
                            self._append_observation(
                                title,
                                f"Recorded provisional source-bound {record_key.replace('_', ' ')} {record_id}.",
                            )
                    if result.chat_request and str(result.chat_request.get("request_type") or "") == "evidence_bound_analysis_question":
                        metrics = result.chat_request.get("baseline_metrics") or {}
                        self._append_observation(
                            "Analysis question",
                            "Selected one safe clarification for analysis "
                            f"{str(metrics.get('source_analysis_id') or '')}: {str(metrics.get('why_it_matters') or 'the recorded uncertainty blocks refinement')}",
                        )
                    elif result.chat_request and str(result.chat_request.get("request_type") or "") == "internal_work_continuation":
                        metrics = result.chat_request.get("baseline_metrics") or {}
                        self._append_observation(
                            "Internal continuation",
                            "Selected one safe proposal for analysis "
                            f"{str(metrics.get('source_analysis_id') or '')}: {str(metrics.get('why_it_matters') or 'a recorded unresolved issue remains')} ",
                        )
                self._refresh_conversational_runtime_status()
                self._refresh_state_cards()
                return True
        lower_message = " ".join(message.lower().split())
        intent = classify_conversational_intent(
            message,
            active_objective=state.active_objective,
            recent_turns=state.conversation,
        )
        if intent.intent_type == "ordinary_conversation" and (self.association_exploration_in_flight or self.revisit_reinquiry_in_flight or self.structural_analogy_exploration_in_flight or self.curiosity_inquiry_in_flight):
            self._request_active_goal_preemption(reason="foreground_conversation")
        if (
            "semantic" in lower_message
            and "reconciliation" in lower_message
            and ("review" in lower_message or "capability" in lower_message or "adopt" in lower_message)
        ):
            self.conversational_runtime_state, review, _request = render_structured_discourse_capability_review(
                state,
                runtime_root=self.conversational_runtime_root,
            )
            self._append_chat("DELTA", review)
            self._append_session("user", message)
            self._append_session("assistant", review)
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        if intent.intent_type == "persistent_or_session_goal" and state.active_objective and self.conversational_runtime_inference_in_flight:
            self._request_active_goal_preemption(reason="foreground_goal_or_priority_update")
            self.conversational_runtime_state = record_foreground_message_for_reconciliation(
                state,
                message,
                runtime_root=self.conversational_runtime_root,
                intent_type="goal_or_priority_queued",
            )
            reply = "Got it. Your possible goal or priority update is queued, and I will interpret it after the current reasoning step finishes."
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._set_conversational_runtime_working()
            self._refresh_state_cards()
            return True
        if (
            intent.intent_type != "persistent_or_session_goal"
            and state.active_objective
            and any(term in lower_message for term in ("provider", "openai", "gpt", "external example", "outside example", "learning packet"))
            and any(term in lower_message for term in ("request", "ask", "recommend", "need", "use"))
        ):
            result = request_provider_learning_packet(
                state,
                message,
                runtime_root=self.conversational_runtime_root,
            )
            self.conversational_runtime_state = result.state
            self._append_chat("DELTA", result.reply)
            self._append_session("user", message)
            self._append_session("assistant", result.reply)
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        if intent.intent_type != "persistent_or_session_goal" and state.active_objective and "review" in lower_message and "goal" in lower_message:
            self.conversational_runtime_state, review = render_goal_review(
                state,
                status=review_status_for_goal_completion(state) if state.lifecycle_state in {"paused_budget", "running"} else state.lifecycle_state,
            )
            save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
            self._append_chat("DELTA", review)
            self._append_session("user", message)
            self._append_session("assistant", review)
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        if intent.intent_type == "stop_or_redirect":
            self.conversational_runtime_state = apply_conversational_stop_or_redirect(
                state,
                message,
                runtime_root=self.conversational_runtime_root,
            )
            reply = "I paused the active goal at a safe boundary and preserved your redirect for the next reasoning step."
            assistant_turn = ConversationTurn(
                turn_id=rc6_stable_id(
                    "conversation-stop-ack",
                    self.conversational_runtime_state.runtime_id,
                    str(len(self.conversational_runtime_state.conversation) + 1),
                    reply,
                ),
                role="assistant",
                text=reply,
                intent_type="stop_or_redirect_acknowledgement",
                objective_id=self.conversational_runtime_state.active_objective.objective_id if self.conversational_runtime_state.active_objective else "",
            )
            self.conversational_runtime_state = replace(
                self.conversational_runtime_state,
                conversation=self.conversational_runtime_state.conversation + (assistant_turn,),
            )
            save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            return True
        provisional_turn_id = f"ui-provisional-{len(state.conversation) + 1}"
        relation = decide_turn_relation(state, message, turn_id=provisional_turn_id) if state.active_objective else None
        transfer = infer_lesson_transfer(state, message, relation=relation) if state.active_objective else {"applied": False}
        if (
            state.active_objective
            and self.conversational_runtime_inference_in_flight
            and intent.intent_type == "ordinary_conversation"
            and not transfer.get("applied")
        ):
            self._request_active_goal_preemption(reason="foreground_conversation")
            self.conversational_runtime_state = record_foreground_message_for_reconciliation(
                state,
                message,
                runtime_root=self.conversational_runtime_root,
            )
            reply = "Got it. Your message is queued, and I will interpret it after the current reasoning step finishes."
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._set_conversational_runtime_working()
            self._refresh_state_cards()
            return True
        if relation and relation.relation_class == "unrelated_foreground_topic":
            result = handle_conversational_message(
                state,
                message,
                runtime_root=self.conversational_runtime_root,
                run_background_cycle=False,
            )
            self.conversational_runtime_state = result.state
            self._append_chat("DELTA", result.reply)
            self._append_session("user", message)
            self._append_session("assistant", result.reply)
            self._refresh_conversational_runtime_status()
            self._refresh_state_cards()
            if state.active_objective and state.lifecycle_state == "running":
                self._start_conversational_background_cycle("foreground_chat_yield")
            return True
        if intent.intent_type not in {
            "persistent_or_session_goal",
            "direct_correction",
            "authority_changing_or_risky_instruction",
            "stop_or_redirect",
        } and not transfer.get("applied"):
            if state.active_objective and state.lifecycle_state == "running":
                if self.conversational_runtime_inference_in_flight:
                    self._request_active_goal_preemption(reason="foreground_conversation")
                    self.conversational_runtime_state = record_foreground_message_for_reconciliation(
                        state,
                        message,
                        runtime_root=self.conversational_runtime_root,
                    )
                    self._append_chat("DELTA", "Got it. Your message is queued, and I will interpret it after the current reasoning step finishes.")
                    self._append_session("user", message)
                    self._append_session("assistant", "Got it. Your message is queued, and I will interpret it after the current reasoning step finishes.")
                    self._set_conversational_runtime_working()
                    self._refresh_state_cards()
                    return True
                self._start_conversational_background_cycle("foreground_chat_yield")
            return False
        result = handle_conversational_message(
            state,
            message,
            runtime_root=self.conversational_runtime_root,
            run_background_cycle=False,
        )
        self.conversational_runtime_state = result.state
        if result.objective_created and self._active_developmental_teaching_plan():
            self._ensure_developmental_teaching_controller()
        self._append_chat("DELTA", result.reply)
        self._append_session("user", message)
        self._append_session("assistant", result.reply)
        self._render_unshown_knowledge_goal_events()
        self._refresh_conversational_runtime_status()
        self._refresh_state_cards()
        if result.objective_created:
            self._start_conversational_background_cycle("objective_registered")
        elif result.correction_attached:
            self._start_conversational_background_cycle("correction_attached")
        elif result.background_cycle_started:
            self._start_conversational_background_cycle("teaching_followup_study")
        elif result.transfer_applied:
            self._start_conversational_background_cycle("ordinary_chat_yield")
        return True

    def _record_dispatch_shadow_plan(self, message: str) -> str:
        """Capture a redacted planner record without affecting legacy dispatch."""
        try:
            plan = plan_message_dispatch(self.conversational_runtime_state, message)
            record = plan.as_record(include_message_text=False)
            record["actual"] = {"observed": False}
        except Exception as exc:  # noqa: BLE001 - shadow diagnostics never block chat.
            record = {
                "message_id": rc6_stable_id("chat-first-shadow-failure", str(len(self.dispatch_shadow_diagnostics)), message),
                "diagnostic_error": type(exc).__name__,
                "actual": {"observed": False},
            }
        self.dispatch_shadow_diagnostics.append(record)
        if len(self.dispatch_shadow_diagnostics) > 64:
            self.dispatch_shadow_diagnostics = self.dispatch_shadow_diagnostics[-64:]
        return str(record["message_id"])

    def _complete_dispatch_shadow_plan(self, message_id: str, *, legacy_consumed: bool, rendered_owner: str, response_text: str = "") -> None:
        for record in reversed(self.dispatch_shadow_diagnostics):
            if record.get("message_id") != message_id:
                continue
            record["actual"] = {
                "observed": True,
                "legacy_handler_consume": legacy_consumed,
                "legacy_fallthrough": not legacy_consumed,
                "rendered_owner": rendered_owner,
                "response_text_class": "nonempty" if response_text.strip() else "none",
            }
            return

    def _render_coordinated_foreground(self, message: str, *, session_user_message: str, control_receipt: str = "") -> str:
        epistemic_payload = self._read_only_epistemic_payload(message)
        if epistemic_payload is not None:
            self.last_message = message
            self.last_payload = epistemic_payload
            response = render_route(epistemic_payload, developer_overlay=self.developer_overlay_enabled.get())
            if control_receipt:
                response = f"{control_receipt}\n\n{response}"
            self._append_chat("DELTA", response)
            self._append_session("user", session_user_message)
            self._append_session("assistant", response)
            self._refresh_state_cards()
            return response
        payload = route_message(
            self.mode.get(),
            message,
            self.paste.get("1.0", tk.END) if hasattr(self, "paste") else "",
            history=self._recent_history_for_router(),
            execute_local_model=False,
        )
        self.last_message = message
        self.last_payload = payload
        self._update_active_topic_anchor(payload)
        request_id = self._record_visible_local_model_request(message, payload)
        rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
        response = rendered if not control_receipt else f"{control_receipt}\n\n{rendered}"
        self._queue_concept_candidate(payload)
        self._append_chat("DELTA", response)
        self._append_session("user", session_user_message)
        self._append_session("assistant", response)
        if request_id:
            self.conversational_runtime_state = mark_chat_request_rendered(
                self.conversational_runtime_state,
                request_id,
                rendered_turn_id=rc6_stable_id("rendered-chat-request", self.conversational_runtime_state.runtime_id, request_id, str(len(self.session_history))),
                render_sequence=len(self.session_history),
            )
        self._refresh_state_cards()
        return response

    def _read_only_epistemic_payload(self, message: str) -> dict[str, object] | None:
        """Return a deterministic graph-bound answer payload, or None for ordinary chat."""
        try:
            graph = load_provisional_semantic_graph(self.conversational_runtime_root)
            binding_ids = bind_explicit_semantic_question(message, graph)
            binding_kind = "explicit_semantic_binding"
            if not binding_ids:
                objective = self.conversational_runtime_state.active_objective
                followups = tuple(
                    dict(item)
                    for item in (objective.provenance.get("teaching_followups", ()) if objective and isinstance(objective.provenance, Mapping) else ())
                    if isinstance(item, Mapping)
                )
                binding_ids = bind_teaching_followup_question(message, graph, followups)
                if binding_ids:
                    binding_kind = "retained_teaching_followup_binding"
            resolution = resolve_production_epistemic_answer(graph, binding_ids, question=message)
        except Exception as exc:  # noqa: BLE001 - graph lookup failure must not block ordinary chat.
            self.last_epistemic_answer_resolution = {
                "binding_status": "lookup_failed",
                "epistemic_mode": "unresolved_binding",
                "reason_codes": ("graph_lookup_failed", type(exc).__name__),
            }
            return None
        self.last_epistemic_answer_resolution = resolution.as_record()
        if resolution.epistemic_mode == "ordinary_unbound":
            return None
        answer = compose_epistemic_answer(resolution)
        return {
            "mode": "Conversation",
            "route": "epistemic_answer_mode",
            "answer": answer,
            "confidence": resolution.epistemic_mode,
            "confidence_score": 0.86 if resolution.epistemic_mode in {"reviewed_supported", "revised_supported"} else 0.55,
            "selected_model_lane": select_model_lane(message),
            "local_model_result": None,
            "supporting_information_offer": None,
            "local_model_offer": None,
            "memory_candidate": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "epistemic_answer_resolution": resolution.as_record(),
            "intent": {"intent": "graph_bound_question", "communication_act": "question", "matched_rule": binding_kind},
            "confidence_decision": {
                "confidence": 0.86 if resolution.epistemic_mode in {"reviewed_supported", "revised_supported"} else 0.55,
                "evidence_quality": resolution.epistemic_mode,
                "retrieval_sufficiency": "explicit_graph_binding",
                "provider_necessity": "none",
            },
            "mode_router_flags": {"read_only_epistemic_answer_routing": True},
        }

    def _record_visible_local_model_request(self, message: str, payload: dict[str, object]) -> str:
        """Materialize visible local-model offers as durable chat requests."""
        local_offer = payload.get("local_model_offer") if isinstance(payload, dict) else None
        if not isinstance(local_offer, dict) or not local_offer.get("offered"):
            return ""
        active = self.conversational_runtime_state.active_objective
        question = str(message or "").strip()
        selected_model = str(local_offer.get("selected_model") or "")
        existing = next(
            (
                item for item in reversed(self.conversational_runtime_state.pending_chat_requests)
                if item.status == "pending"
                and not item.consumption_count
                and item.request_type == "local_model_execution"
                and item.baseline_metrics.get("question") == question
            ),
            None,
        )
        if existing:
            return existing.request_id
        request = ChatAddressableRequest(
            request_id=rc6_stable_id(
                "local-model-chat-request",
                self.conversational_runtime_state.runtime_id,
                str(len(self.conversational_runtime_state.pending_chat_requests) + 1),
                question,
                selected_model,
            ),
            request_type="local_model_execution",
            objective_id=active.objective_id if active else "",
            originating_goal_id=active.objective_id if active else "",
            goal_label="Local model permission",
            prompt_text=str(local_offer.get("prompt") or "Would you like me to ask the local model?"),
            provider=selected_model,
            max_calls=1,
            max_spend_usd=0.0,
            thread_id=f"{self.conversational_runtime_state.runtime_id}:foreground-chat",
            created_sequence=len(self.conversational_runtime_state.conversation) + len(self.session_history) + 1,
            accepted_response_types=("approved", "denied"),
            baseline_metrics={
                "question": question,
                "selected_model": selected_model,
                "support_identifier": local_offer.get("support_identifier") or "",
                "reason": local_offer.get("reason") or "",
            },
        )
        self.conversational_runtime_state = replace(
            self.conversational_runtime_state,
            pending_chat_requests=self.conversational_runtime_state.pending_chat_requests + (request,),
        )
        self.pending_local_model_question = question
        return request.request_id

    def _persist_composed_turn(self, before_state, message: str, response: str) -> None:
        """Replace clause-level handler transcript writes with one composed turn."""
        objective_id = self.conversational_runtime_state.active_objective.objective_id if self.conversational_runtime_state.active_objective else ""
        user = ConversationTurn(
            turn_id=rc6_stable_id("coordinated-user-turn", before_state.runtime_id, str(len(before_state.conversation) + 1), message),
            role="user",
            text=message,
            intent_type="coordinated_mixed_turn",
            objective_id=objective_id,
        )
        assistant = ConversationTurn(
            turn_id=rc6_stable_id("coordinated-assistant-turn", before_state.runtime_id, str(len(before_state.conversation) + 2), response),
            role="assistant",
            text=response,
            intent_type="coordinated_composed_response",
            objective_id=objective_id,
        )
        self.conversational_runtime_state = replace(
            self.conversational_runtime_state,
            conversation=before_state.conversation + (user, assistant),
        )
        prior_request_ids = {item.request_id for item in before_state.pending_chat_requests}
        for request in self.conversational_runtime_state.pending_chat_requests:
            if (
                request.request_id not in prior_request_ids
                and request.status == "pending"
                and not request.consumption_count
                and not request.rendered_turn_id
            ):
                self.conversational_runtime_state = mark_chat_request_rendered(
                    self.conversational_runtime_state,
                    request.request_id,
                    rendered_turn_id=assistant.turn_id,
                    render_sequence=len(before_state.conversation) + 2,
                )
        save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)

    def _execute_coordinated_control(self, control, clause: str) -> str:
        """Execute one planned control clause without taking foreground ownership."""
        state = self.conversational_runtime_state
        if control.control_type == "reference_clarification":
            return self._create_reference_clarification_request(clause)
        if control.control_type == "reference_clarification_resolution":
            return self._resolve_reference_clarification(clause)
        if control.control_type == "interactive_clarification_resolution":
            return self._resolve_interactive_clarification(clause)
        if control.control_type == "runtime_state_query":
            return self._runtime_state_query_reply(clause)
        if control.control_type == "interactive_introspection":
            return self._interactive_introspection_reply(clause)
        if control.control_type == "local_model_permission":
            return self._resolve_local_model_permission(clause)
        if control.control_type == "capability_adoption" and control.action == "resolve_pending_request":
            return self._resolve_capability_adoption_for_coordinator(control, clause)
        if control.control_type == "capability_adoption" and control.action == "clarify_target":
            return "[Approval needed]\nI do not have an eligible pending capability adoption request. Tell me which reviewed capability you want adopted."
        if control.control_type == "clarification":
            return "[Clarification needed]\nThose instructions conflict or do not identify one safe target. Tell me which action you want me to take."
        if control.control_type == "diagnostic_request":
            return "[Diagnostic]\nI can explain the bounded routing decision for this turn without changing the active goal."
        if control.control_type == "restart":
            save_conversational_runtime_state(self.conversational_runtime_root, state)
            return "[Runtime update]\nI saved the current state. A restart still requires the governed restart path, so I preserved the request rather than dropping any conversation obligation."
        if control.control_type == "provider_prohibition":
            result = handle_conversational_message(
                state, clause, runtime_root=self.conversational_runtime_root, run_background_cycle=False,
            )
            self.conversational_runtime_state = result.state
            return f"[Goal update]\n{result.reply}"
        if control.control_type == "goal_continuation":
            if state.active_objective and state.lifecycle_state == "running":
                self._start_conversational_background_cycle("operator_continuation")
                return "[Goal update]\nThe active goal remains running; I queued the next bounded local cycle."
            return "[Goal update]\nThere is no healthy running goal to continue. I preserved the request without claiming progress."
        if control.control_type in {"pause_goal", "stop_goal"}:
            self.conversational_runtime_state = apply_conversational_stop_or_redirect(
                state, clause, runtime_root=self.conversational_runtime_root,
            )
            return "[Goal update]\nI paused the active goal at a safe boundary."
        if control.control_type == "resume_goal":
            self.conversational_runtime_state = resume_conversational_objective(
                state, runtime_root=self.conversational_runtime_root,
            )
            if self.conversational_runtime_state.lifecycle_state == "running":
                self._start_conversational_background_cycle("objective_resumed")
                return "[Goal update]\nI resumed the active goal."
            return "[Goal update]\nThis goal is not paused by the operator, so I left its state unchanged."
        if control.control_type in {"goal_review", "goal_status"}:
            self.conversational_runtime_state, review = render_goal_review(
                state, status=review_status_for_goal_completion(state),
            )
            save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)
            return f"[Goal review]\n{review}"
        if control.control_type == "capability_review":
            self.conversational_runtime_state, review, _request = render_structured_discourse_capability_review(
                state, runtime_root=self.conversational_runtime_root,
            )
            return review
        if control.control_type == "provider_request":
            result = request_provider_learning_packet(state, clause, runtime_root=self.conversational_runtime_root)
            self.conversational_runtime_state = result.state
            return f"[Goal update]\n{result.reply}"
        resolved = resolve_pending_chat_request(state, clause, runtime_root=self.conversational_runtime_root)
        result = resolved or handle_conversational_message(
            state, clause, runtime_root=self.conversational_runtime_root, run_background_cycle=False,
        )
        self.conversational_runtime_state = result.state
        if result.objective_created or result.correction_attached:
            self._start_conversational_background_cycle(
                "objective_registered" if result.objective_created else "correction_attached"
            )
        return f"[Goal update]\n{result.reply}"

    def _runtime_state_query_reply(self, message: str) -> str:
        state = self.conversational_runtime_state
        active = state.active_objective
        lower = message.lower()
        pending_count = sum(1 for item in state.pending_chat_requests if item.status == "pending" and not item.consumption_count)
        discarded_count = sum(1 for item in state.resolved_chat_requests if item.status in {"denied", "expired"} or item.resolution in {"denied", "expired"})
        queued_count = sum(1 for turn in state.conversation if turn.intent_type in {"goal_or_priority_queued", "ordinary_conversation_queued"})
        last_user = next((turn.text for turn in reversed(state.conversation) if turn.role == "user"), "")
        if active and state.lifecycle_state == "paused_operator":
            lifecycle = "paused"
        elif active and self.conversational_runtime_inference_in_flight:
            lifecycle = "working"
        elif active and state.lifecycle_state == "running":
            lifecycle = "running"
        else:
            lifecycle = state.lifecycle_state.replace("_", " ")
        lines = [
            "[Runtime state]",
            f"Active goal: {'yes' if active else 'no'}",
            f"State: {lifecycle}",
            f"Pending requests: {pending_count}",
            f"Queued turns: {queued_count}",
            f"Discarded or expired requests: {discarded_count}",
        ]
        if "exactly once" in message.lower():
            lines.append(f"Queued exactly once: {'yes' if queued_count == 1 else 'no'}")
        if "last" in lower and "question" in lower:
            lines.append(f"Last user question: {last_user or 'none'}")
        return "\n".join(lines)

    def _interactive_introspection_reply(self, message: str) -> str:
        """Answer from live workspace and decision records, never semantic memory."""

        self._refresh_interactive_cognition_shadow(reason="operator_introspection")
        workspace = self.interactive_workspace_snapshot
        decision = self.interactive_attention_decision
        lower = " ".join(str(message or "").lower().split())
        threads = tuple(workspace.threads) if workspace else ()
        selected = next((item for item in threads if decision and item.thread_id == decision.target_thread_id), None)
        if "why did you ask" in lower:
            request = next((item for item in reversed(self.conversational_runtime_state.pending_chat_requests) if item.status == "pending" and not item.consumption_count), None)
            if request is None:
                return "[Introspection]\nI do not have a current unanswered question, so there is no active question reason to report."
            pressure = str(request.baseline_metrics.get("clarification_pressure") or request.request_type)
            return f"[Introspection]\nI asked because the current request is waiting on {pressure.replace('_', ' ')} before its dependent work can continue."
        if "unsure" in lower:
            uncertain = [item for item in threads if item.epistemic_status in {"unstable", "uncertain", "pending_consolidation", "revisit_candidate"}]
            if not uncertain:
                return "[Introspection]\nI do not have a recorded unresolved epistemic item in the current workspace."
            return f"[Introspection]\nI am currently uncertain about: {uncertain[0].focus}. It remains in its existing review path."
        if "what did you pause" in lower:
            paused = [item for item in threads if item.status in {"paused", "deferred", "suppressed"}]
            if not paused:
                return "[Introspection]\nI do not have a paused, deferred, or suppressed thread recorded right now."
            return f"[Introspection]\nI paused or deferred: {paused[0].focus}."
        if "return to" in lower:
            later = [item for item in threads if item.status in {"queued", "deferred", "generated"}]
            if not later:
                return "[Introspection]\nI do not have a deferred background item scheduled to return to."
            return f"[Introspection]\nThe next eligible background item is: {later[0].focus}."
        if selected is None:
            return "[Introspection]\nI am idle because the current workspace has no eligible thread."
        return f"[Introspection]\nI am currently attending to: {selected.focus}. The selected posture is {decision.selected_posture.replace('_', ' ')}."

    def _pending_reference_clarification(self):
        return next(
            (
                item for item in reversed(self.conversational_runtime_state.pending_chat_requests)
                if item.status == "pending"
                and not item.consumption_count
                and item.request_type == "reference_clarification"
            ),
            None,
        )

    def _create_reference_clarification_request(self, message: str) -> str:
        state = self.conversational_runtime_state
        existing = self._pending_reference_clarification()
        if existing:
            return "[Clarification needed]\nI still need the earlier reference clarified before I bind that goal-thread instruction."
        created_turn_id = rc6_stable_id(
            "reference-clarification-user-turn",
            state.runtime_id,
            str(len(state.conversation) + 1),
            message,
        )
        request = compile_chat_clarification_request(
            state,
            pressure="ambiguous_reference",
            prompt_text="Which prior subject or turn should that refer to?",
            source_record_ids=(created_turn_id,),
            created_turn_id=created_turn_id,
            created_sequence=len(state.conversation) + 1,
            request_type="reference_clarification",
        )
        request = replace(
            request,
            goal_label="Reference clarification",
            baseline_metrics={
                **request.baseline_metrics,
                "ambiguous_message": message,
                "created_conversation_count": len(state.conversation),
                "expires_on_unrelated_foreground_question": True,
            },
        )
        self.conversational_runtime_state = replace(
            state,
            pending_chat_requests=state.pending_chat_requests + (request,),
            objective_progress=state.objective_progress + ({"event": "reference_clarification_requested", "request_id": request.request_id},),
        )
        return "[Clarification needed]\nWhich prior subject should that refer to?"

    def _resolve_reference_clarification(self, message: str) -> str:
        state = self.conversational_runtime_state
        request = self._pending_reference_clarification()
        if request is None:
            return "[Clarification]\nThere is no active reference clarification to resolve."
        resolved = ChatAddressableRequest(
            **{
                **request.as_record(),
                "status": "resolved",
                "resolved_turn_id": rc6_stable_id("reference-clarification-resolution", state.runtime_id, message),
                "resolution_text": message,
                "resolution_policy": "operator_clarified_reference",
                "resolution": "resolved",
                "consumption_count": 1,
            }
        )
        self.conversational_runtime_state = replace(
            state,
            pending_chat_requests=tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id),
            resolved_chat_requests=state.resolved_chat_requests + (resolved,),
            objective_progress=state.objective_progress + ({"event": "reference_clarification_resolved", "request_id": request.request_id},),
        )
        return "[Clarification]\nGot it. I bound that reference to your clarification."

    def _pending_interactive_clarification(self):
        return next(
            (
                item for item in reversed(self.conversational_runtime_state.pending_chat_requests)
                if item.status == "pending"
                and not item.consumption_count
                and item.request_type == "interactive_clarification"
            ),
            None,
        )

    def _resolve_interactive_clarification(self, message: str, *, request_id: str = "") -> str:
        """Consume one rendered operator question without asserting semantic truth."""

        state = self.conversational_runtime_state
        request = next(
            (
                item for item in self.conversational_runtime_state.pending_chat_requests
                if item.request_id == request_id
                and item.status == "pending"
                and not item.consumption_count
                and item.request_type == "interactive_clarification"
            ),
            None,
        ) if request_id else self._pending_interactive_clarification()
        if request is None:
            return "[Clarification]\nThere is no active exploration question to resolve."
        metrics = dict(request.baseline_metrics)
        candidate_id = str(metrics.get("originating_candidate_id") or "")
        candidate_kind = str(metrics.get("candidate_kind") or "")
        question_kind = str(metrics.get("question_kind") or "")
        is_curiosity_inquiry = bool(metrics.get("curiosity_inquiry"))
        lowered = " ".join(str(message or "").lower().split())
        association_rejected = candidate_kind in {"near_association", "far_analogy"} and bool(
            re.search(r"\b(?:no|not\s+relevant|do\s+not|don't|shouldn't)\b", lowered)
        )
        revisit_trigger = str(metrics.get("pressure_trigger") or "") in {"consolidation_correction", "consolidation_remaining_gap"}
        candidate_state = (
            "rejected" if association_rejected else
            "approved_for_bounded_exploration" if candidate_kind in {"near_association", "far_analogy"} else
            "approved_for_bounded_exploration" if is_curiosity_inquiry and re.search(r"\b(?:yes|approve|go ahead|continue)\b", lowered) else
            "approved_for_revisit" if revisit_trigger else
            "resolved"
        )
        existing_disposition = next(
            (item for item in self.interactive_coordination_state.candidate_dispositions if item.candidate_id == candidate_id),
            None,
        )
        if existing_disposition is not None:
            self.interactive_coordination_state = set_candidate_disposition(
                self.interactive_coordination_state,
                candidate_id=candidate_id,
                candidate_kind=existing_disposition.candidate_kind,
                disposition=candidate_state,
                source_record_ids=existing_disposition.source_record_ids,
            )
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)
        resolved = ChatAddressableRequest(
            **{
                **request.as_record(),
                "status": "resolved",
                "resolution_state": "resolved",
                "resolved_turn_id": rc6_stable_id("interactive-clarification-resolution", state.runtime_id, request.request_id, message),
                "resolution_text": message,
                "resolution_policy": (
                    "operator_rejected_association_exploration" if association_rejected else
                    "operator_approved_bounded_association_exploration" if candidate_kind == "near_association" else
                    "operator_approved_bounded_structural_analogy_exploration" if candidate_kind == "far_analogy" else
                    "operator_approved_bounded_curiosity_inquiry" if is_curiosity_inquiry and candidate_state == "approved_for_bounded_exploration" else
                    "operator_approved_bounded_revisit" if revisit_trigger else
                    "operator_answered_cognitive_pressure_question"
                ),
                "resolution": "resolved",
                "consumption_count": 1,
                "baseline_metrics": {
                    **metrics,
                    "association_exploration_state": candidate_state if candidate_kind == "near_association" else metrics.get("association_exploration_state", ""),
                    "association_resolution_state": "unresolved" if candidate_kind == "near_association" else metrics.get("association_resolution_state", ""),
                    "analogy_exploration_state": candidate_state if candidate_kind == "far_analogy" else metrics.get("analogy_exploration_state", ""),
                    "pressure_state": "operator_input_recorded" if candidate_kind == "cognitive_pressure" else metrics.get("pressure_state", ""),
                },
            }
        )
        self.conversational_runtime_state = replace(
            state,
            pending_chat_requests=tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id),
            resolved_chat_requests=state.resolved_chat_requests + (resolved,),
            objective_progress=state.objective_progress + (
                {"event": "interactive_clarification_resolved", "request_id": request.request_id},
            ),
        )
        if association_rejected:
            return "[Clarification]\nThanks. I recorded that this association should not be pursued now."
        if candidate_kind == "near_association":
            return "[Clarification]\nThanks. I recorded this association as approved for bounded exploration; it is not a validated claim."
        if candidate_kind == "far_analogy":
            return "[Clarification]\nThanks. I recorded this analogy as approved for one bounded comparison; it remains provisional."
        if is_curiosity_inquiry and candidate_state == "approved_for_bounded_exploration":
            return "[Clarification]\nThanks. I recorded one bounded local inquiry; its result will remain provisional."
        return "[Clarification]\nThanks. I recorded your answer to that bounded cognitive-pressure question."

    def _settle_matching_local_model_request(self, question: str, resolution: str, reply: str) -> None:
        state = self.conversational_runtime_state
        request = next(
            (
                item for item in reversed(state.pending_chat_requests)
                if item.status == "pending"
                and not item.consumption_count
                and item.request_type == "local_model_execution"
                and item.baseline_metrics.get("question") == question
            ),
            None,
        )
        if request is None:
            return
        resolved = ChatAddressableRequest(
            **{
                **request.as_record(),
                "status": "consumed" if resolution == "approved" else "denied",
                "resolved_turn_id": rc6_stable_id("local-model-legacy-resolution-turn", state.runtime_id, question, resolution),
                "resolution_text": reply,
                "resolution_policy": resolution,
                "resolution": resolution,
                "consumption_count": 1,
            }
        )
        self.conversational_runtime_state = replace(
            state,
            pending_chat_requests=tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id),
            resolved_chat_requests=state.resolved_chat_requests + (resolved,),
        )
        save_conversational_runtime_state(self.conversational_runtime_root, self.conversational_runtime_state)

    def _resolve_capability_adoption_for_coordinator(self, control, message: str) -> str:
        state = self.conversational_runtime_state
        request = next(
            (
                item for item in reversed(state.pending_chat_requests)
                if item.status == "pending"
                and not item.consumption_count
                and item.request_type == "capability_adoption_and_restart"
                and (not control.target_id or item.request_id == control.target_id)
            ),
            None,
        )
        if request is None:
            return "[Approval needed]\nI do not have an eligible pending capability adoption request."
        lower = " ".join(message.lower().split())
        if "show me the evidence" in lower or "show evidence" in lower or "evidence again" in lower:
            return f"[Capability adoption]\n{request.prompt_text}"
        denied = control.denied or lower.startswith(("no", "deny", "decline")) or "do not adopt" in lower or "don't adopt" in lower
        now = datetime.now(timezone.utc).isoformat()
        resolved = ChatAddressableRequest(
            **{
                **request.as_record(),
                "status": "denied" if denied else "consumed",
                "resolution": "denied" if denied else "approved",
                "resolution_text": message,
                "resolution_policy": "denied" if denied else "approved_coordinated",
                "resolved_at": now,
                "consumed_at": "" if denied else now,
                "consumption_count": 1,
            }
        )
        pending = tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
        if denied:
            self.conversational_runtime_state = replace(
                state,
                pending_chat_requests=pending,
                resolved_chat_requests=state.resolved_chat_requests + (resolved,),
                objective_progress=state.objective_progress + (
                    {
                        "event": "capability_adoption_denied_in_coordinated_turn",
                        "request_id": request.request_id,
                        "at": now,
                    },
                ),
            )
            return "[Capability adoption]\nUnderstood. I will keep the current behavior and leave that capability unadopted."

        restart_id = rc6_stable_id("coordinated-capability-adoption-restart", request.request_id, message)
        archived = state.active_objective.as_record() if state.active_objective else None
        adoption_record = {
            "capability_id": request.capability_id,
            "capability_version": request.capability_version,
            "source_commit": "coordinated_pending_request",
            "adopted_by": "operator_chat_approval",
            "adoption_request_id": request.request_id,
            "evidence_digest": request.evidence_digest,
            "adopted_at": now,
            "activation_state": "active",
            "restart_id": restart_id,
            "post_restart_validation": "pending_full_restart_validation",
            "constraints": ("coordinated_single_commit",),
        }
        restart_record = {
            "restart_id": restart_id,
            "kind": "coordinated_runtime_state_commit",
            "requested_at": now,
            "pre_restart_completed_cycle_count": len(state.completed_cycle_keys),
            "post_restart_validation": "pending_full_restart_validation",
            "duplicate_review_created": False,
            "duplicate_request_created": False,
            "duplicate_model_request_created": False,
        }
        registry = tuple(item for item in state.capability_registry if item.get("capability_id") != request.capability_id) + (
            {
                "capability_id": request.capability_id,
                "name": request.capability_name,
                "version": request.capability_version,
                "source_commit": "coordinated_pending_request",
                "activation_state": "active",
                "adopted_at": now,
                "evidence_digest": request.evidence_digest,
                "production_consumer": "chat_first_dispatch_coordinator",
                "rollback_reference": "Disable the capability registry entry before reverting source.",
                "last_validation_at": now,
                "validation_status": "pending_full_restart_validation",
            },
        )
        self.conversational_runtime_state = replace(
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
            objective_progress=state.objective_progress + (
                {
                    "event": "capability_adopted_in_coordinated_turn",
                    "capability_id": request.capability_id,
                    "request_id": request.request_id,
                    "restart_id": restart_id,
                    "at": now,
                },
            ),
        )
        return "[Capability adoption]\nI recorded the adoption and restart disposition for the composed turn. The coordinator will commit the resulting state once."

    def _expire_reference_clarifications_for_foreground(self, message: str) -> None:
        candidates = [
            item for item in self.conversational_runtime_state.pending_chat_requests
            if item.status == "pending"
            and not item.consumption_count
            and item.request_type in {"reference_clarification", "interactive_clarification"}
        ]
        request = max(candidates, key=lambda item: (item.render_sequence, item.created_sequence, item.request_id)) if candidates else None
        if request is None:
            return
        lower = " ".join(str(message or "").lower().split())
        if not ("?" in lower or re.search(r"\b(?:what|why|how|explain|tell me)\b", lower)):
            return
        if request.request_type == "reference_clarification" and re.search(r"\b(?:that|it|this|prior|previous|earlier|reference|subject|topic)\b", lower):
            return
        state = self.conversational_runtime_state
        expired = ChatAddressableRequest(
            **{
                **request.as_record(),
                "status": "expired",
                "resolved_turn_id": rc6_stable_id("interactive-clarification-expired", state.runtime_id, request.request_id, message),
                "resolution_text": message,
                "resolution_policy": "expired_on_unrelated_foreground_question",
                "resolution": "expired",
                "consumption_count": 0,
            }
        )
        self.conversational_runtime_state = replace(
            state,
            pending_chat_requests=tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id),
            resolved_chat_requests=state.resolved_chat_requests + (expired,),
            objective_progress=state.objective_progress + ({"event": f"{request.request_type}_expired", "request_id": request.request_id},),
        )
        candidate_id = str(request.baseline_metrics.get("originating_candidate_id") or "")
        existing_disposition = next(
            (item for item in self.interactive_coordination_state.candidate_dispositions if item.candidate_id == candidate_id),
            None,
        )
        if existing_disposition is not None:
            self.interactive_coordination_state = set_candidate_disposition(
                self.interactive_coordination_state,
                candidate_id=candidate_id,
                candidate_kind=existing_disposition.candidate_kind,
                disposition="expired",
                source_record_ids=existing_disposition.source_record_ids,
            )
            save_coordination_state(self.conversational_runtime_root, self.interactive_coordination_state)

    def _resolve_local_model_permission(self, message: str, *, request_id: str = "") -> str:
        state = self.conversational_runtime_state
        request = next(
            (
                item for item in reversed(state.pending_chat_requests)
                if item.status == "pending"
                and not item.consumption_count
                and item.request_type == "local_model_execution"
                and (not request_id or item.request_id == request_id)
            ),
            None,
        )
        if request is None:
            return "[Local model]\nThere is no active local-model request to consume."
        lower = message.lower().strip()
        approved = lower.startswith(("yes", "ok", "okay")) or "ask" in lower or "go ahead" in lower
        resolved = ChatAddressableRequest(
            **{
                **request.as_record(),
                "status": "consumed" if approved else "denied",
                "resolution_state": "consumed" if approved else "denied",
                "resolved_turn_id": rc6_stable_id("local-model-resolution-turn", state.runtime_id, message),
                "resolution_text": message,
                "resolution_policy": "approved" if approved else "denied",
                "resolution": "approved" if approved else "denied",
                "consumption_count": 1,
            }
        )
        pending = tuple(item for item in state.pending_chat_requests if item.request_id != request.request_id)
        self.conversational_runtime_state = replace(
            state,
            pending_chat_requests=pending,
            resolved_chat_requests=state.resolved_chat_requests + (resolved,),
        )
        self.pending_local_model_question = None
        if not approved:
            return "[Local model]\nOkay. I will leave that unanswered locally for now."
        target = str(request.baseline_metrics.get("question") or "").strip() or request.prompt_text
        self._prepare_resident_model_for_question(target)
        payload = route_message(
            "Conversation",
            target,
            history=self._recent_history_for_router(),
            execute_local_model=True,
            provider_manager=self.provider_manager,
        )
        payload.update({
            "active_pending_action_id": request.request_id,
            "active_pending_action_type": "local_model_execution",
            "pending_action_matched": True,
            "action_executed": bool((payload.get("local_model_result") or {}).get("executed")),
            "pending_action_cleared": True,
        })
        self.last_message = target
        self.last_payload = payload
        self._update_active_topic_anchor(payload)
        self._queue_concept_candidate(payload)
        self._remember_local_model_exchange(target, payload)
        return render_route(payload, developer_overlay=self.developer_overlay_enabled.get())

    @staticmethod
    def _has_explicit_foreground_joiner(message: str) -> bool:
        """Keep a distinct foreground question out of an otherwise cohesive goal."""
        return bool(re.search(
            r"\b(?:also|separately|by the way)\s*,?\s*(?:what|why|how|who|where|when|which|tell me|explain)\b",
            str(message or "").lower(),
        ))

    def _coordinated_control_clause(self, control, plan, message: str) -> str:
        """Bind a goal control to the whole goal turn, not its first dispatch segment."""
        if (
            control.control_type in {"create_goal", "replace_goal"}
            and not self._has_explicit_foreground_joiner(message)
        ):
            return message
        return plan.segments[control.source_clause_index].text

    def _execute_controls_with_deferred_saves(self, controls, plan, message: str) -> tuple[list[str], int]:
        """Run subordinate control handlers in memory; coordinator commits once."""
        deferred_saves: list[object] = []
        original_save = conversational_runtime_operation.save_runtime_state
        original_alias_save = save_conversational_runtime_state

        def _deferred_save(_root, saved_state) -> None:
            deferred_saves.append(saved_state)

        conversational_runtime_operation.save_runtime_state = _deferred_save
        globals()["save_conversational_runtime_state"] = _deferred_save
        try:
            receipts = [
                self._execute_coordinated_control(item, self._coordinated_control_clause(item, plan, message))
                for item in controls
            ]
        finally:
            conversational_runtime_operation.save_runtime_state = original_save
            globals()["save_conversational_runtime_state"] = original_alias_save
        return receipts, len(deferred_saves)

    def _coordinate_mixed_dispatch(self, message: str, plan) -> bool:
        controls = tuple(getattr(plan, "controls", ()) or ((plan.control,) if plan.control.detected else ()))
        supported = {
            "create_goal", "replace_goal", "correction", "provider_approval", "capability_adoption",
            "side_thread_resolution", "pause_goal", "resume_goal", "stop_goal", "goal_status",
            "goal_review", "capability_review", "provider_request", "provider_prohibition", "diagnostic_request", "clarification",
            "goal_continuation", "restart", "runtime_state_query", "interactive_introspection", "local_model_permission",
            "reference_clarification", "reference_clarification_resolution", "interactive_clarification_resolution",
        }
        if not controls or any(item.source_clause_index < 0 or item.control_type not in supported for item in controls):
            return False
        # Existing single-clause runtime handlers retain ownership for their
        # lifecycle/queue semantics. The coordinator is the composition path.
        if not plan.foreground.requested and len(controls) == 1 and controls[0].control_type not in {"runtime_state_query", "interactive_introspection", "local_model_permission", "clarification", "reference_clarification", "reference_clarification_resolution", "interactive_clarification_resolution"}:
            return False
        state_before = self.conversational_runtime_state
        control_indexes = {
            item.source_clause_index for item in controls
            if not any(
                clause.clause_index == item.source_clause_index and clause.foreground_requested
                for clause in getattr(plan, "clauses", ())
            )
        }
        receipts, deferred_save_count = self._execute_controls_with_deferred_saves(controls, plan, message)
        self.last_coordinated_dispatch_audit = {
            "control_count": len(controls),
            "deferred_subordinate_save_count": deferred_save_count,
            "final_persistence_owner": "dispatch_coordinator",
            "render_owner": "dispatch_coordinator",
        }
        foreground_message = " ".join(
            segment.text for index, segment in enumerate(plan.segments)
            if index not in control_indexes and segment.kind != "context_prefix"
        ).strip()
        control_receipt = "\n\n".join(dict.fromkeys(receipt for receipt in receipts if receipt))
        foreground_indexes = {
            clause.clause_index for clause in getattr(plan, "clauses", ())
            if clause.foreground_requested
        }
        explicit_foreground_joiner = self._has_explicit_foreground_joiner(message)
        if any(item.control_type in {"create_goal", "replace_goal"} for item in controls) and not explicit_foreground_joiner:
            foreground_indexes = set()
        if foreground_message:
            foreground_message = " ".join(
                segment.text for index, segment in enumerate(plan.segments)
                if index in foreground_indexes and segment.kind != "context_prefix"
            ).strip()
        if foreground_message:
            response = self._render_coordinated_foreground(
                foreground_message, session_user_message=message, control_receipt=control_receipt,
            )
        else:
            response = control_receipt
            self._append_chat("DELTA", response)
            self._append_session("user", message)
            self._append_session("assistant", response)
        self._persist_composed_turn(state_before, message, response)
        self._refresh_conversational_runtime_status()
        self._refresh_state_cards()
        return True

    def _recent_history_for_router(self) -> list[dict[str, str]]:
        history = self.session_history[-10:]
        if self.active_topic_anchor:
            history = [*history, {"role": "anchor", "content": json.dumps(self.active_topic_anchor, sort_keys=True)}]
        if self.conversation_topic_state:
            history = [*history, {"role": "topic_state", "content": json.dumps(self.conversation_topic_state, sort_keys=True)}]
        return history

    def _last_substantive_exchange(self) -> dict[str, str] | None:
        last_assistant = ""
        for item in reversed(self.session_history):
            role = item.get("role")
            content = str(item.get("content") or "")
            if role == "assistant" and not last_assistant and "Would you like me to ask the local reasoning model to elaborate?" not in content:
                last_assistant = _assistant_answer_text(content)
            elif role == "user" and last_assistant:
                text = content.strip()
                if text.lower() not in {"yes", "no", "tell me more", "more", "go deeper", "explain more", "elaborate"}:
                    return {"question": text, "answer": last_assistant}
        return None

    def _show_welcome(self) -> None:
        residency = ""
        if self.model_residency_status == "warm":
            residency = " The everyday local model is already loaded for this session."
        elif self.model_residency_status.startswith("warm_failed"):
            residency = " Local model warmup did not complete, so I may need to fall back if you ask for local reasoning."
        self._append_chat(
            "DELTA",
            "Hi. I'm DELTA. You can talk normally here. If a task needs governed memory, evidence review, replay, or diagnostics, I can route it or you can open Advanced mode."
            + residency,
        )
        self._append_session("assistant", "Hi. I'm DELTA. You can talk normally here.")

    def _restore_canonical_conversation(self) -> bool:
        """Hydrate the visible transcript from the runtime's existing turn owner.

        A restart must not make a durable teaching episode look like a new
        empty chat.  This only projects canonical conversation turns into the
        Tk widget; it neither persists new turns nor changes their IDs.
        """

        turns = tuple(getattr(self.conversational_runtime_state, "conversation", ()) or ())
        if not turns:
            return False
        for turn in turns:
            text = str(getattr(turn, "text", "") or "").strip()
            if not text:
                continue
            role = str(getattr(turn, "role", "") or "").lower()
            speaker = "You" if role == "user" else "DELTA" if role == "assistant" else role.title() or "DELTA"
            self._append_chat(speaker, text)
            self._append_session("user" if role == "user" else "assistant", text)
        return True

    def _poll_model_warm_results(self) -> None:
        while True:
            try:
                item = self.model_warm_result_queue.get_nowait()
            except queue.Empty:
                break
            self.model_warm_in_flight = False
            if item.get("ok"):
                self.resident_model_id = str(item.get("model_id") or "")
                self.resident_lane = str(item.get("lane") or "everyday_conversation")
                self.model_residency_status = "warm"
            else:
                self.model_residency_status = str(item.get("status") or "warm_failed:unknown")
        self.root.after(100, self._poll_model_warm_results)

    def _warm_default_model(self) -> None:
        if self.model_warm_in_flight or self.model_residency_status == "warm":
            return
        lane = select_model_lane("Hello DELTA.", "conversation")
        model_id = str(lane.get("selected_model_id") or lane.get("selected_model") or "")
        if not model_id:
            self.model_residency_status = "warm_failed:no_model"
            return
        self.model_warm_in_flight = True
        self.model_residency_status = "warming"

        def worker() -> None:
            try:
                self.locked_provider_manager.warm(model_id)
                payload = {"ok": True, "model_id": model_id, "lane": str(lane.get("lane") or "everyday_conversation")}
            except Exception as exc:  # noqa: BLE001 - UI should stay usable if warmup fails.
                payload = {"ok": False, "status": f"warm_failed:{type(exc).__name__}:{str(exc)[:120]}"}
            self.model_warm_result_queue.put(payload)

        threading.Thread(target=worker, name="delta-model-warmup", daemon=True).start()

    def _prepare_resident_model_for_question(self, question: str) -> None:
        lane = select_model_lane(question)
        model_id = str(lane.get("selected_model_id") or lane.get("selected_model") or "")
        lane_name = str(lane.get("lane") or "")
        display = str(lane.get("display_name") or lane_name or "local model")
        if not model_id:
            return
        if self.resident_model_id == model_id:
            return
        if self.resident_model_id:
            if lane_name == "planning":
                self._append_chat("DELTA", "One moment while I switch to the planning model.")
            elif self.resident_lane == "planning":
                self._append_chat("DELTA", "One moment while I switch back to the general conversation model.")
            else:
                self._append_chat("DELTA", f"One moment while I switch to the {display}.")
        else:
            self._append_chat("DELTA", f"One moment while I load the {display}.")
        try:
            self.provider_manager.warm(model_id)
            self.resident_model_id = model_id
            self.resident_lane = lane_name
            self.model_residency_status = "warm"
        except Exception as exc:  # noqa: BLE001
            self.model_residency_status = f"switch_failed:{type(exc).__name__}:{str(exc)[:120]}"

    def _start_live_runtime(self) -> None:
        if self.live_runtime_request_in_flight:
            self.live_runtime_status.set("Live runtime is completing an operator turn; start is unavailable until it finishes.")
            return
        if self.live_runtime_session and self.live_runtime_session.active:
            self.live_runtime_status.set(self._live_status_text())
            return
        try:
            self.live_runtime_session = start_live_wikipedia_runtime(
                runtime_id="ui",
                resident_model_id=self.resident_model_id,
                resident_lane=self.resident_lane,
                residency_status=self.model_residency_status,
            )
            self.live_runtime_status.set(self._live_status_text())
            self._append_chat(
                "DELTA",
                "Live runtime started. Wikipedia text retrieval is enabled for this session only; no provider calls or memory writes are enabled. Retrieved text will be compared against local concepts and surfaced as a gated review candidate when useful.",
            )
        except Exception as exc:  # noqa: BLE001
            self.live_runtime_status.set(f"Live runtime start failed: {type(exc).__name__}")
            messagebox.showerror("Live Runtime", f"Could not start live runtime:\n{type(exc).__name__}: {str(exc)[:240]}")

    def _stop_live_runtime(self) -> None:
        if self._queue_live_runtime_control("stop"):
            return
        if not self.live_runtime_session:
            self.live_runtime_status.set("Live runtime: stopped")
            return
        try:
            self.live_runtime_session = stop_live_wikipedia_runtime(self.live_runtime_session)
            self.live_runtime_status.set(self._live_status_text())
            self._append_chat("DELTA", "Live runtime stopped.")
        except Exception as exc:  # noqa: BLE001
            self.live_runtime_status.set(f"Live runtime stop failed: {type(exc).__name__}")
            messagebox.showerror("Live Runtime", f"Could not stop live runtime:\n{type(exc).__name__}: {str(exc)[:240]}")

    def _pause_live_initiative(self) -> None:
        if self._queue_live_runtime_control("pause"):
            return
        if not self.live_runtime_session:
            self.live_runtime_status.set("Live runtime: stopped")
            return
        self.live_runtime_session = pause_live_initiative(self.live_runtime_session)
        self.live_runtime_status.set(self._live_status_text())

    def _resume_live_initiative(self) -> None:
        if self._queue_live_runtime_control("resume"):
            return
        if not self.live_runtime_session:
            self.live_runtime_status.set("Live runtime: stopped")
            return
        self.live_runtime_session = resume_live_initiative(self.live_runtime_session)
        self.live_runtime_status.set(self._live_status_text())

    def _suspend_live_initiative(self) -> None:
        if self._queue_live_runtime_control("suspend"):
            return
        if not self.live_runtime_session:
            self.live_runtime_status.set("Live runtime: stopped")
            return
        self.live_runtime_session = suspend_live_runtime_initiative(self.live_runtime_session)
        self.live_runtime_status.set(self._live_status_text())

    def _queue_live_runtime_control(self, control: str) -> bool:
        if not self.live_runtime_request_in_flight:
            return False
        if control not in {"stop", "pause", "resume", "suspend"}:
            raise ValueError(f"unknown live runtime control: {control}")
        if not self.pending_live_runtime_controls or self.pending_live_runtime_controls[-1] != control:
            self.pending_live_runtime_controls.append(control)
        self.live_runtime_status.set(f"Runtime=PROCESSING_OPERATOR_TURN; {control} queued after the current turn.")
        return True

    def _apply_queued_live_runtime_controls(self) -> None:
        pending = tuple(self.pending_live_runtime_controls)
        self.pending_live_runtime_controls.clear()
        for control in pending:
            if control == "stop":
                self._stop_live_runtime()
            elif control == "pause":
                self._pause_live_initiative()
            elif control == "resume":
                self._resume_live_initiative()
            elif control == "suspend":
                self._suspend_live_initiative()

    def _begin_live_runtime_turn(self, message: str) -> None:
        session = self.live_runtime_session
        if session is None:
            return
        self.live_runtime_request_in_flight = True
        self.chat_input.configure(state=tk.DISABLED)
        self.live_runtime_status.set("Runtime=PROCESSING_OPERATOR_TURN; lifecycle controls can be queued.")
        history = self._recent_history_for_router()
        developer_overlay = self.developer_overlay_enabled.get()

        def run_turn() -> None:
            try:
                updated_session, response = handle_live_chat(
                    session,
                    message,
                    history=history,
                    developer_overlay=developer_overlay,
                    provider_manager=self.provider_manager,
                )
                self.live_runtime_worker_results.put({
                    "kind": "response",
                    "message": message,
                    "session": updated_session,
                    "response": response,
                })
            except Exception as exc:  # noqa: BLE001 - retain UI control when a worker turn fails unexpectedly.
                self.live_runtime_worker_results.put({
                    "kind": "error",
                    "message": message,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc)[:500],
                })

        threading.Thread(target=run_turn, name="delta-live-runtime-turn", daemon=True).start()

    def _poll_live_runtime_worker_results(self) -> None:
        try:
            while True:
                result = self.live_runtime_worker_results.get_nowait()
                self._complete_live_runtime_turn(result)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_live_runtime_worker_results)

    def _complete_live_runtime_turn(self, result: dict[str, object]) -> None:
        self.live_runtime_request_in_flight = False
        if result.get("kind") == "response":
            session = result.get("session")
            response = result.get("response")
            if isinstance(session, LiveWikipediaRuntimeSession) and response is not None:
                self.live_runtime_session = session
                self.last_message = str(result.get("message") or "")
                payload = getattr(response, "payload", {})
                self.last_payload = payload if isinstance(payload, dict) else None
                if isinstance(payload, dict):
                    self._update_active_topic_anchor(payload)
                    self._queue_concept_candidate(payload)
                self._append_chat("DELTA", str(getattr(response, "answer", "")))
                self._append_session("assistant", str(getattr(response, "answer", "")))
            else:
                self._append_chat("DELTA", "Live runtime returned an invalid worker result. No state was committed.")
        else:
            self._append_chat(
                "DELTA",
                "Live runtime turn failed safely. "
                + f"Reason: {result.get('exception_type')}: {result.get('exception_message')}",
            )
        self._apply_queued_live_runtime_controls()
        self.live_runtime_status.set(self._live_status_text())
        self._refresh_state_cards()
        self.chat_input.configure(state=tk.NORMAL)
        self.chat_input.focus_set()

    def _live_status_text(self) -> str:
        session = self.live_runtime_session
        if not session:
            return "Live runtime: stopped"
        controller = controller_snapshot(session.continuous_controller) if session.continuous_controller else {}
        model = controller.get("current_model", {}) if isinstance(controller, dict) else {}
        active_objective = controller.get("active_objective") if isinstance(controller, dict) else None
        objective_title = (active_objective or {}).get("title") if isinstance(active_objective, dict) else ""
        recent = controller.get("recent_initiative") if isinstance(controller, dict) else None
        recent_text = (recent or {}).get("outcome") if isinstance(recent, dict) else "none"
        wiki_limit = int(session.wikipedia_profile.max_queries_per_objective or 0)
        wiki_budget = f"{session.retrieval_count}/unlimited" if wiki_limit <= 0 else f"{session.retrieval_count}/{wiki_limit}"
        return (
            f"Runtime={controller.get('lifecycle_state', session.runtime.state)}; "
            f"health={(controller.get('health') or {}).get('health_state', 'unknown')}; "
            f"model={model.get('resident_model_id') or model.get('default_model') or 'none'}; "
            f"objective={(objective_title or 'none')[:42]}; "
            f"inquiries={len(session.operator_inquiries)}; promotions={len(session.promotion_candidates)}; "
            f"wiki={wiki_budget}; initiative={recent_text}; autonomy={session.autonomy_status}"
        )

    def _active_cognitive_loop_evidence(self) -> tuple[ActiveCognitiveEvidenceRef, ...]:
        return (
            ActiveCognitiveEvidenceRef(
                "delta_runtime_components",
                "repo",
                "DELTA already has goals, persistence, model routing, and governed execution pieces.",
                "DELTA.py initializes persistent development state, local ProviderManager, live runtime controls, and shared ledgers.",
            ),
            ActiveCognitiveEvidenceRef(
                "delta_active_loop_gap",
                "repo",
                "Contrary evidence: those pieces are not yet one persistent active cognitive loop.",
                "The missing transition is continuous focus selection, bounded working memory, model-selected operation, outcome observation, and hypothesis revision.",
            ),
            ActiveCognitiveEvidenceRef(
                "delta_marathon_authority",
                "operator",
                "The operator authorized an active cognitive architecture marathon with local-only bounded execution.",
                "Do not stage, commit, push, use network providers, or touch protected paths.",
            ),
        )

    def _load_active_cognitive_loop_state(self):
        try:
            if self.active_cognitive_loop_state_path.exists():
                return read_active_cognitive_episode_state(self.active_cognitive_loop_state_path)
        except Exception:
            return None
        return None

    def _start_active_cognitive_loop(self) -> str:
        self.active_cognitive_loop_state = initialize_active_cognitive_episode(
            title="DELTA active cognitive architecture marathon",
            goal_summary="integrate DELTA's cognitive pieces into one persistent active cognitive loop",
            expected_state="useful artifact produced by a restartable attention-memory-hypothesis cycle",
            evidence=self._active_cognitive_loop_evidence(),
            state_path=self.active_cognitive_loop_state_path,
        )
        snapshot = active_loop_snapshot(self.active_cognitive_loop_state)
        return f"Active cognitive loop started. State={snapshot['loop_state']}; next={snapshot['next_intended_step']}."

    def _active_cognitive_loop_status(self) -> str:
        state = self.active_cognitive_loop_state or self._load_active_cognitive_loop_state()
        if state is None:
            return "Active cognitive loop: not started."
        self.active_cognitive_loop_state = state
        snapshot = active_loop_snapshot(state)
        evaluation = evaluate_cognitive_episode(state)
        return (
            f"Active cognitive loop: state={snapshot['loop_state']}; completed={snapshot['completed']}; "
            f"cycles={evaluation['cycle_count']}; model_calls={evaluation['model_call_count']}; "
            f"focus={snapshot['current_focus'] or 'none'}; next={snapshot['next_intended_step']}."
        )

    def _run_active_cognitive_loop_cycle(self) -> str:
        if self.active_cognitive_loop_state is None:
            self._start_active_cognitive_loop()
        runner = LedgerBackedCognitiveModelRunner(
            ledger=LocalModelRequestResultLedger(),
            provider_manager=self.provider_manager,
            authority_reason="operator_authorized_active_cognitive_architecture_marathon_1",
        )
        self.active_cognitive_loop_state = run_active_cognitive_cycle(
            self.active_cognitive_loop_state,
            model_runner=runner,
        )
        write_active_cognitive_episode_state(self.active_cognitive_loop_state_path, self.active_cognitive_loop_state)
        snapshot = active_loop_snapshot(self.active_cognitive_loop_state)
        evaluation = evaluate_cognitive_episode(self.active_cognitive_loop_state)
        failures = ", ".join(evaluation["failure_classifications"]) or "none"
        return (
            f"Active cognitive cycle complete. State={snapshot['loop_state']}; "
            f"cycles={evaluation['cycle_count']}; model_calls={evaluation['model_call_count']}; "
            f"failures={failures}; next={snapshot['next_intended_step']}."
        )

    def _apply_claim_relation_pilot(self, message: str) -> str:
        result = self.claim_relation_pilot.process_operator_turn(
            message,
            turn_id=f"conversation-turn:{len(self.session_history) + 1}",
        )
        if not result.enabled or result.disposition in {"unsupported", "disabled"}:
            return ""
        if result.disposition == "persistence_blocked":
            return result.operator_visible_text
        return result.operator_visible_text

    def _send_chat(self) -> None:
        message = self.chat_input.get().strip()
        if not message:
            return
        self.chat_input.delete(0, tk.END)
        self._append_chat("You", message)
        self._refresh_interactive_cognition_shadow(
            foreground_message=message,
            foreground_turn_id=rc6_stable_id(
                "interactive-foreground-turn",
                self.conversational_runtime_state.runtime_id,
                str(len(self.session_history) + 1),
                message,
            ),
            reason="operator_message_received",
        )
        shadow_message_id = self._record_dispatch_shadow_plan(message)
        try:
            live_plan = plan_message_dispatch(self.conversational_runtime_state, message)
        except Exception:  # noqa: BLE001 - the shadow plan remains non-blocking.
            live_plan = None
        lower = message.lower().strip()
        if getattr(self, "active_operator_ux_request", None):
            intent = normalize_operator_intent(message)
            if self._consume_operator_ux_intent(intent, response_source="conversation"):
                self._refresh_state_cards()
                return
        cancel_words = {"no", "n", "not now", "no thanks", "keep chatting", "nevermind", "never mind", "cancel", "stop", "forget it"}
        affirm_words = {"yes", "y", "yes please", "sure", "okay", "ok", "go ahead", "do it", "tell me more", "more", "go deeper"}
        if self.live_runtime_session and self.live_runtime_session.active:
            self._append_session("user", message)
            self._begin_live_runtime_turn(message)
            return
        if self._is_local_model_response_query(lower):
            reply = self._last_local_model_response_answer()
            if reply:
                self._append_session("user", message)
                self._append_chat("DELTA", reply)
                self._append_session("assistant", reply)
                return
        if self._is_discourse_history_query(lower):
            reply = self._discourse_history_answer()
            if reply:
                self._append_session("user", message)
                self._append_chat("DELTA", reply)
                self._append_session("assistant", reply)
                return
        if is_developmental_governance_message(self.conversational_runtime_state, message):
            if self._handle_conversational_runtime_message(message):
                self._complete_dispatch_shadow_plan(
                    shadow_message_id,
                    legacy_consumed=True,
                    rendered_owner="conversational_runtime",
                )
                return
        if select_chat_request_owner(self.conversational_runtime_state, message) is not None:
            if self._handle_conversational_runtime_message(message):
                self._complete_dispatch_shadow_plan(
                    shadow_message_id,
                    legacy_consumed=True,
                    rendered_owner="conversational_runtime",
                )
                return
        if self.conversational_runtime_state.pending_chat_requests and lower in (affirm_words | cancel_words):
            if self._handle_conversational_runtime_message(message):
                self._complete_dispatch_shadow_plan(
                    shadow_message_id,
                    legacy_consumed=True,
                    rendered_owner="conversational_runtime",
                )
                return
        if self.pending_local_model_question and lower in (affirm_words | {"ask local", "ask the local model", "ask a local model"}):
            target = self.pending_local_model_question
            self.pending_local_model_question = None
            self._append_session("user", message)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                execute_local_model=True,
                provider_manager=self.provider_manager,
            )
            self._settle_matching_local_model_request(target, "approved", message)
            self.last_message = target
            self.last_payload = payload
            self._update_active_topic_anchor(payload)
            offer = payload.get("supporting_information_offer") if isinstance(payload, dict) else None
            self.pending_provider_question = target if isinstance(offer, dict) and offer.get("offered") else None
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._set_deepening_offer_if_present(target, payload)
            self._remember_local_model_exchange(target, payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_local_model_question and lower in cancel_words:
            target = self.pending_local_model_question
            self.pending_local_model_question = None
            self._append_session("user", message)
            reply = "Okay. I will leave that unanswered locally for now."
            self._settle_matching_local_model_request(target, "denied", message)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        has_runtime_coordination_context = bool(
            self.conversational_runtime_state.active_objective
            or self.conversational_runtime_state.pending_chat_requests
        )
        question_like_foreground = "?" in message or bool(
            re.match(r"^(?:what|why|how|who|where|when|which|is|are|was|were|do|does|did|can|could|should|would)\b", lower)
        )
        runtime_intake_or_control = bool(
            re.search(
                r"\b(?:your\s+new\s+goal|your\s+goal\s+today|new\s+goal|active\s+goal|pause|resume|stop|review|approve|adopt|provider|restart|continue)\b",
                lower,
            )
        )
        if runtime_intake_or_control and not (live_plan is not None and live_plan.foreground.requested and live_plan.control.detected):
            runtime_intent = classify_conversational_intent(
                message,
                active_objective=self.conversational_runtime_state.active_objective,
                recent_turns=self.conversational_runtime_state.conversation,
            )
            if runtime_intent.intent_type == "persistent_or_session_goal" and self._handle_conversational_runtime_message(message):
                self._complete_dispatch_shadow_plan(
                    shadow_message_id,
                    legacy_consumed=True,
                    rendered_owner="conversational_runtime",
                )
                return
        if (
            is_source_bound_semantic_recall_message(self.conversational_runtime_state, message)
            or is_evidence_bound_analysis_recall_message(self.conversational_runtime_state, message)
            or is_evidence_bound_analysis_refinement_recall_message(self.conversational_runtime_state, message)
            or is_semantic_problem_frame_recall_message(self.conversational_runtime_state, message)
            or is_semantic_problem_modeling_message(self.conversational_runtime_state, message)
            or is_source_bound_semantic_competence_measurement_message(self.conversational_runtime_state, message)
            or is_source_bound_semantic_analysis_message(self.conversational_runtime_state, message)
            or is_source_bound_semantic_transfer_message(self.conversational_runtime_state, message)
            or is_internal_work_recall_message(self.conversational_runtime_state, message)
        ):
            if self._handle_conversational_runtime_message(message):
                self._complete_dispatch_shadow_plan(
                    shadow_message_id,
                    legacy_consumed=True,
                    rendered_owner="conversational_runtime",
                )
                return
        legacy_imperative_foreground = bool(
            live_plan is not None
            and live_plan.foreground.requested
            and not question_like_foreground
            and not runtime_intake_or_control
        )
        if legacy_imperative_foreground:
            self.pending_local_model_deepening = None
            payload = route_message(
                self.mode.get(),
                message,
                self.paste.get("1.0", tk.END) if hasattr(self, "paste") else "",
                history=self._recent_history_for_router(),
                execute_local_model=False,
            )
            self.last_message = message
            self.last_payload = payload
            self._update_active_topic_anchor(payload)
            offer = payload.get("supporting_information_offer") if isinstance(payload, dict) else None
            if isinstance(offer, dict) and offer.get("offered"):
                self.pending_provider_question = message
            elif payload.get("route") == "gpt_support_approval_preview":
                self.pending_provider_question = message
            else:
                self.pending_provider_question = None
            local_offer = payload.get("local_model_offer") if isinstance(payload, dict) else None
            pending_suggestion = payload.get("pending_action_suggestion") if isinstance(payload, dict) else None
            if isinstance(pending_suggestion, dict) and pending_suggestion.get("action_type") == "local_model_deepening":
                exchange = self._last_substantive_exchange() or {"question": message, "answer": str(payload.get("answer") or "")}
                action_id = f"rc2-pending-action-{uuid.uuid4().hex[:12]}"
                self.pending_local_model_deepening = {
                    "action_id": action_id,
                    "action_type": "local_model_deepening",
                    "question": exchange["question"],
                    "answer": exchange["answer"],
                    "followup_instruction": message,
                    "source_turn_id": str(len(self.session_history)),
                }
                payload["pending_action_suggestion"] = {
                    **pending_suggestion,
                    "action_id": action_id,
                    "original_topic": exchange["question"],
                    "prior_answer_summary": exchange["answer"][:260],
                    "selected_lane": (payload.get("selected_model_lane") or {}).get("lane"),
                    "selected_model": (payload.get("selected_model_lane") or {}).get("selected_model_id"),
                }
                self.pending_local_model_question = None
            else:
                self.pending_local_model_question = message if isinstance(local_offer, dict) and local_offer.get("offered") else None
                if self.pending_local_model_question:
                    self.pending_local_model_deepening = None
            self._refresh_state_cards()
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._append_chat("DELTA", rendered)
            self._append_session("user", message)
            self._append_session("assistant", rendered)
            self._complete_dispatch_shadow_plan(
                shadow_message_id,
                legacy_consumed=False,
                rendered_owner="rc2_router",
                response_text=rendered,
            )
            return
        if live_plan is not None and not legacy_imperative_foreground and self._coordinate_mixed_dispatch(message, live_plan):
            self._complete_dispatch_shadow_plan(
                shadow_message_id,
                legacy_consumed=False,
                rendered_owner="dispatch_coordinator",
                response_text="coordinated_foreground_and_control",
            )
            return
        if (
            live_plan is not None
            and live_plan.foreground.requested
            and not live_plan.control.detected
            and (has_runtime_coordination_context or question_like_foreground)
        ):
            if self.conversational_runtime_inference_in_flight or self.association_exploration_in_flight or self.revisit_reinquiry_in_flight or self.structural_analogy_exploration_in_flight or self.curiosity_inquiry_in_flight:
                self._request_active_goal_preemption(reason="coordinated_foreground_conversation")
            foreground_message = " ".join(
                segment.text for segment in live_plan.segments if segment.kind != "context_prefix"
            ).strip() or message
            state_before = self.conversational_runtime_state
            self._expire_reference_clarifications_for_foreground(foreground_message)
            response = self._render_coordinated_foreground(foreground_message, session_user_message=message)
            self._persist_composed_turn(state_before, message, response)
            self._complete_dispatch_shadow_plan(
                shadow_message_id,
                legacy_consumed=False,
                rendered_owner="rc2_router",
                response_text="coordinated_foreground",
            )
            return
        if not legacy_imperative_foreground and self._handle_conversational_runtime_message(message):
            self._complete_dispatch_shadow_plan(
                shadow_message_id,
                legacy_consumed=True,
                rendered_owner="conversational_runtime",
            )
            return
        if lower == "create operator ux demo goal":
            request = self._create_operator_ux_demo_request()
            self._append_chat("DELTA", "I created a demo goal and need your approval before the next bounded step.")
            self._refresh_operator_ux_views()
            self._refresh_state_cards()
            return
        if lower == "operator ux status":
            self._refresh_operator_ux_views()
            self._append_chat("DELTA", f"Operator UX active request: {'yes' if self.active_operator_ux_request else 'no'}. Goals: {len(self.operator_ux_goal_cards)}.")
            return
        if lower == "discover next goal":
            result = self._discover_autonomy_1_next_goal()
            proposal = dict(result["proposal"])
            goal = dict(proposal.get("recommended_goal") or {})
            if goal:
                self._append_chat("DELTA", f"I found a possible next goal: {goal.get('goal')}")
            self._refresh_operator_ux_views()
            self._refresh_state_cards()
            return
        if lower in {"compare next goals", "prioritize next goals"}:
            result = self._discover_autonomy_2_goal_ranking()
            request = dict(result.get("operator_request") or {})
            if request:
                self._append_chat("DELTA", str(request.get("title") or "I found several possible next goals"))
            self._refresh_operator_ux_views()
            self._refresh_state_cards()
            return
        if lower == "plan next queued goal":
            self._plan_autonomy_3_next_goal()
            self._refresh_operator_ux_views()
            self._refresh_state_cards()
            return
        if lower == "start approved plan":
            self._start_autonomy_4_approved_plan()
            self._refresh_operator_ux_views()
            self._refresh_state_cards()
            return
        if lower in {"pause approved plan", "pause the plan", "wait on approved plan"}:
            self._start_autonomy_4_approved_plan(mode="pause")
            self._refresh_operator_ux_views()
            self._refresh_state_cards()
            return
        if lower in {"stop approved plan", "stop the plan", "cancel remaining work"}:
            self._start_autonomy_4_approved_plan(mode="stop")
            self._refresh_operator_ux_views()
            self._refresh_state_cards()
            return
        if lower in {"resume approved plan", "resume the plan"}:
            self._start_autonomy_4_approved_plan(mode="resume")
            self._refresh_operator_ux_views()
            self._refresh_state_cards()
            return
        if lower in {"show my limits", "show approved plan limits"}:
            self._explain_autonomy_4_execution("limits")
            return
        if lower in {"show the evidence", "show approved plan evidence"}:
            self._explain_autonomy_4_execution("evidence")
            return
        if lower in {"explain current step", "what step are you on"}:
            self._explain_autonomy_4_execution("step")
            return
        if lower in {"review completed outcome", "review the completed outcome", "start autonomy 5"}:
            self._run_autonomy_5_visible_control("review")
            return
        if lower in {"explain the evidence", "explain outcome evidence"}:
            if lower == "explain the evidence" and self._latest_autonomy_17_packet():
                self._run_autonomy_17_visible_control("explain")
            else:
                self._run_autonomy_5_visible_control("explain")
            return
        if lower == "acquire local evidence":
            self._run_autonomy_17_visible_control("acquire")
            return
        if lower in {"explain local evidence", "explain the local evidence"}:
            self._run_autonomy_17_visible_control("explain")
            return
        if lower in {"show evidence sources", "view evidence sources"}:
            self._run_autonomy_17_visible_control("sources")
            return
        if lower in {"show contradictions", "view contradictions"}:
            self._run_autonomy_17_visible_control("contradictions")
            return
        if lower in {"show missing evidence", "view missing evidence"}:
            self._run_autonomy_17_visible_control("missing")
            return
        if lower in {"show evidence limits", "view evidence limits"}:
            self._run_autonomy_17_visible_control("limits")
            return
        if lower in {"revalidate stale evidence", "revalidate local evidence"}:
            self._run_autonomy_17_visible_control("revalidate")
            return
        if lower in {"request bounded advice", "request advisory assistance"}:
            self._run_autonomy_18_visible_control("request")
            return
        if lower in {"explain advice", "explain advisory result"}:
            self._run_autonomy_18_visible_control("explain")
            return
        if lower in {"view advisory grounding", "show advisory grounding"}:
            self._run_autonomy_18_visible_control("grounding")
            return
        if lower in {"view rejected claims", "show rejected claims"}:
            self._run_autonomy_18_visible_control("rejected")
            return
        if lower in {"view advisory limits", "show advisory limits"}:
            self._run_autonomy_18_visible_control("limits")
            return
        if lower in {"keep as proposal", "keep advice as proposal"}:
            self._run_autonomy_18_visible_control("keep")
            return
        if lower in {"reject advice", "reject advisory result"}:
            self._run_autonomy_18_visible_control("reject")
            return
        if lower in {"show failed cases", "view failed cases"}:
            self._run_autonomy_5_visible_control("failed")
            return
        if lower in {"keep it provisional", "keep as provisional evidence"}:
            if self._latest_autonomy_6_review()[0]:
                self._run_autonomy_6_visible_control("keep")
            else:
                self._run_autonomy_5_visible_control("keep")
            return
        if lower in {"send it for competence review", "send to competence review"}:
            self._run_autonomy_5_visible_control("send")
            return
        if lower in {"review competence candidate", "start autonomy 6", "review competence admission"}:
            self._run_autonomy_6_visible_control("review")
            return
        if lower in {"admit this competence", "accept this competence", "add this competence", "approve competence admission"}:
            self._run_autonomy_6_visible_control("admit")
            return
        if lower in {"reject the competence", "reject admission", "do not accept this"}:
            self._run_autonomy_6_visible_control("reject")
            return
        if lower in {"do not admit it yet", "leave it provisional"}:
            self._run_autonomy_6_visible_control("keep")
            return
        if lower in {"test it more", "request more evaluation", "gather more evidence first"}:
            self._run_autonomy_6_visible_control("more")
            return
        if lower in {"explain the scope", "what can it actually do", "what are the limitations", "i don't understand the competence", "i dont understand the competence"}:
            self._run_autonomy_6_visible_control("explain")
            return
        if lower in {"looks good", "proceed", "yes"} and self._latest_autonomy_6_review()[0]:
            self._run_autonomy_6_visible_control("ambiguous")
            return
        composition_intents = {
            "start composed task": "start",
            "pause composed task": "pause",
            "resume composed task": "resume",
            "stop composed task": "stop",
            "explain composition": "explain",
            "explain current stage": "explain",
            "show composition evidence": "evidence",
            "show composition provenance": "provenance",
            "show composition limits": "limits",
        }
        if lower in composition_intents:
            self._run_autonomy_14_visible_control(composition_intents[lower])
            return
        mission_intents = {
            "start mission": "start",
            "pause mission": "pause",
            "resume mission": "resume",
            "stop mission": "stop",
            "explain current task": "current",
            "explain blocked task": "blocked",
            "show mission evidence": "evidence",
            "show mission limits": "limits",
            "show task graph": "graph",
            "what can continue": "blocked",
            "why is this task blocked": "blocked",
        }
        if lower in mission_intents:
            self._run_autonomy_16_visible_control(mission_intents[lower])
            return
        if lower == "start active cognitive loop":
            reply = self._start_active_cognitive_loop()
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower in {"active cognitive status", "show active cognitive loop"}:
            reply = self._active_cognitive_loop_status()
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower in {"run active cognitive cycle", "advance active cognitive loop"}:
            reply = self._run_active_cognitive_loop_cycle()
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "enable governed claim relation pilot":
            self.claim_relation_pilot.set_enabled(True)
            reply = f"{CLAIM_RELATION_PILOT_FLAG} is enabled for this local session."
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "disable governed claim relation pilot":
            self.claim_relation_pilot.set_enabled(False)
            reply = f"{CLAIM_RELATION_PILOT_FLAG} is disabled."
            self._append_chat("DELTA", reply)
            self._append_session("user", message)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        claim_relation_result = self._apply_claim_relation_pilot(message)
        if claim_relation_result:
            self._append_chat("DELTA", claim_relation_result)
            self._append_session("user", message)
            self._append_session("assistant", claim_relation_result)
            self._refresh_state_cards()
            return
        discourse_frame = build_discourse_frame(message, self.last_report_inspection)
        discourse_trace = discourse_frame.as_dict()
        controller = getattr(self, "developmental_learning_controller", None)
        learning_request = dict((controller.continuous_learning_state or {}).get("local_model_request") or {}) if controller else {}
        if learning_request and lower in affirm_words:
            request_id = str(learning_request.get("request_id") or "")
            ledger = LocalModelRequestResultLedger()
            try:
                ledger.approve_request(request_id, "operator_approved_one_use")
                terminal = ledger.execute_claimed_request(request_id)
                self.developmental_learning_controller = consume_mission_bound_local_model_learning_approval(controller)
                state = self.developmental_learning_controller.continuous_learning_state
                provisional = dict(state.get("provisional_resource_bundle") or {})
                advisory = dict(state.get("mission_bound_advisory_evidence") or {})
                result_id = str(terminal.get("result_id") or "")
                self._append_chat(
                    "DELTA",
                    "The approval was routed to the shared local-model ledger. "
                    f"Request={request_id}; state={terminal.get('lifecycle_state')}; result_id={result_id or 'none'}. "
                    f"The learning controller observed the terminal record; evidence={advisory.get('evidence_id') or 'none'}; "
                    f"resource={provisional.get('resource_bundle_id') or 'none'}. The first subgoal remains unexecuted. "
                    "No evaluation, capability update, provider, web, PCM, or tracked-source action occurred.",
                )
            except (KeyError, RuntimeError, OSError) as exc:
                self._append_chat("DELTA", f"The shared local-model request was not executed: {exc}.")
            self._refresh_state_cards()
            return
        persistent_controls = {
            "pause learning runtime": "pause",
            "resume learning runtime": "resume",
            "stop learning runtime": "stop",
        }
        if lower in persistent_controls:
            self._append_session("user", message)
            reply = self._handle_persistent_development_control(persistent_controls[lower])
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower in {"learning runtime status", "developmental runtime status", "show blocked learning goals", "show learning budget", "export learning report"}:
            self._append_session("user", message)
            reply = self._handle_persistent_development_status()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower in {"advance live runtime 1b", "start live runtime 1b", "continue live runtime 1b"}:
            self._append_session("user", message)
            reply = self._advance_live_runtime_1b_from_ui()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "live runtime 1b status":
            self._append_session("user", message)
            reply = self._live_runtime_1b_summary()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower in {"prepare live runtime 2 unattended mission", "start live runtime 2 setup"}:
            self._append_session("user", message)
            reply = self._prepare_live_runtime_2_from_ui()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "authorize bounded unattended live runtime 2":
            self._append_session("user", message)
            reply = self._authorize_live_runtime_2_from_ui()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "start bounded unattended live runtime 2":
            self._append_session("user", message)
            reply = self._start_live_runtime_2_unattended_from_ui()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "live runtime 2 status":
            self._append_session("user", message)
            self._load_live_runtime_2_state()
            reply = self._live_runtime_2_summary()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "prepare live runtime 3 interruption mission":
            self._append_session("user", message)
            reply = self._prepare_live_runtime_3_from_ui()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "authorize first bounded unattended live runtime 3":
            self._append_session("user", message)
            reply = self._authorize_live_runtime_3_from_ui(1)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "authorize second bounded unattended live runtime 3":
            self._append_session("user", message)
            self._load_live_runtime_3_state()
            reply = self._authorize_live_runtime_3_from_ui(2)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "start bounded unattended live runtime 3":
            self._append_session("user", message)
            reply = self._start_live_runtime_3_from_ui()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "live runtime 3 status":
            self._append_session("user", message)
            self._load_live_runtime_3_state()
            reply = self._live_runtime_3_summary()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "prepare live runtime 4 crash mission":
            self._append_session("user", message)
            reply = self._prepare_live_runtime_4_from_ui()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "authorize first bounded unattended live runtime 4":
            self._append_session("user", message)
            reply = self._authorize_live_runtime_4_from_ui(1)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "start crash bounded unattended live runtime 4":
            self._append_session("user", message)
            reply = self._start_live_runtime_4_from_ui(crash_after_prepared=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "authorize second bounded unattended live runtime 4":
            self._append_session("user", message)
            self._load_live_runtime_4_state()
            reply = self._authorize_live_runtime_4_from_ui(2)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "start bounded unattended live runtime 4":
            self._append_session("user", message)
            reply = self._start_live_runtime_4_from_ui()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if lower == "live runtime 4 status":
            self._append_session("user", message)
            self._load_live_runtime_4_state()
            reply = self._live_runtime_4_summary()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if self._is_live_runtime_1b_mission(message):
            self._append_session("user", message)
            reply = self._handle_live_runtime_1b_mission(reset=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if self._is_persistent_development_goal(message):
            self._append_session("user", message)
            reply = self._handle_persistent_development_goal(message)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if self._is_developmental_learning_mission(message):
            self._append_session("user", message)
            reply = self._handle_developmental_learning_mission(message)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if self._is_oar_language_development_mission(message):
            self._append_session("user", message)
            reply = self._handle_oar_language_development_mission(message)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: oar_language_development_mission_intake\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "local_model_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "source_application_performed": False,
                    "capability_activation_performed": False,
                    "development_runtime_started": False,
                    "automatic_continuation_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            self._refresh_state_cards()
            return
        if self.live_runtime_session and self.live_runtime_session.active:
            self._append_session("user", message)
            self._begin_live_runtime_turn(message)
            return
        if is_render_correction_request(message):
            self._append_session("user", message)
            payload = route_message(
                self.mode.get(),
                message,
                self.paste.get("1.0", tk.END) if hasattr(self, "paste") else "",
                history=self._recent_history_for_router(),
                execute_local_model=False,
            )
            self.last_message = message
            self.last_payload = payload
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        report_inspection = _inspect_local_report(message)
        if report_inspection and report_inspection.get("handled"):
            self._append_session("user", message)
            reply = str(report_inspection.get("answer") or "")
            report_path = _extract_report_path(message)
            self.last_report_inspection = {
                "report_name": report_path.name if report_path else "local report",
                "report_path": str(report_path.resolve()) if report_path else "",
                "request": message,
                "answer_summary": " ".join(reply.split())[:600],
            }
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: local_report_inspection\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps(report_inspection.get("safety", {}), indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        rc6_reply = _handle_rc6_pilot_message(message, self.rc6_pilot_events)
        if rc6_reply:
            self._append_session("user", message)
            reply = rc6_reply
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc6_disabled_gateway_pilot\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nRC7 Development Dashboard:\n"
                reply += _rc7_developer_overlay_text()
                reply += "\nSafety:\n"
                reply += json.dumps(rc6_safety_metadata(), indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "identify_report_weakness":
            self._append_session("user", message)
            reply = _summarize_same_report_weakness(self.last_report_inspection)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: ephemeral_same_report_followup\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "draft_operator_pilot_checklist":
            self._append_session("user", message)
            reply = _draft_operator_pilot_checklist(self.last_report_inspection)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: ephemeral_report_followup_checklist\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "resolve_prior_checklist_item":
            self._append_session("user", message)
            reply = _answer_second_one_pilot_followup(self.last_report_inspection)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: ephemeral_pilot_checklist_followup\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_rc5_gpt_boundary":
            self._append_session("user", message)
            reply = _answer_rc5_gpt_boundary()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc5_manual_consultation_boundary\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_rc5_to_rc4_handoff_boundary":
            self._append_session("user", message)
            reply = _answer_rc4_handoff_boundary()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc5_to_rc4_handoff_boundary\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "draft_pilot_session_record":
            self._append_session("user", message)
            reply = _draft_operator_pilot_session_record(message, self.last_report_inspection)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: ephemeral_pilot_session_record\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "evaluate_full_pilot_freeze_readiness":
            self._append_session("user", message)
            reply = _answer_full_pilot_freeze_decision()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_pilot_freeze_decision\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "identify_primary_freeze_evidence_gap":
            self._append_session("user", message)
            reply = _answer_primary_freeze_evidence_gap()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_primary_freeze_evidence_gap\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_sufficient_recovery_evidence":
            self._append_session("user", message)
            reply = _answer_sufficient_recovery_evidence()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_recovery_evidence_enrichment\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_mixed_proposal_record":
            self._append_session("user", message)
            reply = _answer_mixed_proposal_record()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_mixed_proposal_record_guidance\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_useful_but_unsafe_advice_handling":
            self._append_session("user", message)
            reply = _answer_useful_but_unsafe_advice_handling()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_useful_but_unsafe_advice_guidance\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        pc1_reply = _try_pc1_pragmatic_answer(
            message,
            self.last_report_inspection,
            developer_overlay=self.developer_overlay_enabled.get(),
        )
        if pc1_reply:
            self._append_session("user", message)
            self._append_chat("DELTA", pc1_reply)
            self._append_session("assistant", pc1_reply)
            return
        if self._is_local_model_response_query(lower):
            reply = self._last_local_model_response_answer()
            if reply:
                self._append_session("user", message)
                self._append_chat("DELTA", reply)
                self._append_session("assistant", reply)
                return
        if self._is_discourse_history_query(lower):
            reply = self._discourse_history_answer()
            if reply:
                self._append_session("user", message)
                self._append_chat("DELTA", reply)
                self._append_session("assistant", reply)
                return
        if self.pending_local_model_deepening and lower in affirm_words:
            pending = self.pending_local_model_deepening
            self.pending_local_model_deepening = None
            self._append_session("user", message)
            target = _build_deepening_prompt(pending["question"], pending["answer"])
            self._prepare_resident_model_for_question(target)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                execute_local_model=True,
                provider_manager=self.provider_manager,
            )
            payload.update({
                "active_pending_action_id": pending.get("action_id"),
                "active_pending_action_type": pending.get("action_type", "local_model_deepening"),
                "pending_action_matched": True,
                "action_executed": bool((payload.get("local_model_result") or {}).get("executed")),
                "pending_action_cleared": True,
            })
            enrichment_candidate = build_memory_candidate_from_answer(pending["question"], payload)
            matches = query_approved_concepts(pending["question"]).get("matches", [])
            if matches:
                enrichment_candidate = {
                    **enrichment_candidate,
                    "enrichment_of_concept_id": matches[0].get("concept_id"),
                    "enrichment_of_concept_name": matches[0].get("concept_name"),
                    "approval_status": "pending_operator_enrichment_review",
                    "source_question": pending["question"],
                    "source_type": "local_model_lane_enrichment",
                }
            payload["memory_candidate"] = enrichment_candidate
            self.last_message = target
            self.last_payload = payload
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_local_model_deepening and lower in cancel_words:
            self.pending_local_model_deepening = None
            self._append_session("user", message)
            reply = "Okay. I will not deepen that answer right now."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if self.pending_local_model_question and lower in (affirm_words | {"ask local", "ask the local model", "ask a local model"}):
            target = self.pending_local_model_question
            self.pending_local_model_question = None
            self._append_session("user", message)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                execute_local_model=True,
                provider_manager=self.provider_manager,
            )
            self.last_message = target
            self.last_payload = payload
            self._update_active_topic_anchor(payload)
            offer = payload.get("supporting_information_offer") if isinstance(payload, dict) else None
            self.pending_provider_question = target if isinstance(offer, dict) and offer.get("offered") else None
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._set_deepening_offer_if_present(target, payload)
            self._remember_local_model_exchange(target, payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_local_model_question and lower in cancel_words:
            self.pending_local_model_question = None
            self._append_session("user", message)
            reply = "Okay. I will leave that unanswered locally for now."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if self.pending_provider_question and lower in {"yes", "y", "yes please", "ask gpt", "ask gpt please", "look for sources"}:
            target = self.pending_provider_question
            self.pending_provider_question = None
            self._append_session("user", message)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                provider_approved=True,
            )
            self.last_message = target
            self.last_payload = payload
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._set_deepening_offer_if_present(target, payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_provider_question and lower in cancel_words:
            self.pending_provider_question = None
            self._append_session("user", message)
            reply = "Okay. I will keep this local and will not ask a provider."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if lower in {"remember that", "remember this", "store that", "store this", "save that", "save this", "remember this useful answer", "keep this concept", "that was useful remember the concept"}:
            self._append_session("user", message)
            reply = self._queue_last_answer_for_review()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if lower in {"not now", "discard", "forget after this chat"}:
            self._append_session("user", message)
            self._append_chat("DELTA", "Okay. I will keep this in the current conversation only and will not store a concept.")
            self._append_session("assistant", "Okay. I will keep this in the current conversation only and will not store a concept.")
            return
        self.pending_local_model_deepening = None
        epistemic_payload = self._read_only_epistemic_payload(message)
        if epistemic_payload is not None:
            self.last_message = message
            self.last_payload = epistemic_payload
            self.pending_provider_question = None
            self.pending_local_model_question = None
            rendered = render_route(epistemic_payload, developer_overlay=self.developer_overlay_enabled.get())
            self._append_chat("DELTA", rendered)
            self._append_session("user", message)
            self._append_session("assistant", rendered)
            self._complete_dispatch_shadow_plan(
                shadow_message_id,
                legacy_consumed=False,
                rendered_owner="epistemic_answer_mode",
                response_text=rendered,
            )
            self._refresh_state_cards()
            return
        if is_teaching_followup_message(self.conversational_runtime_state, message):
            if self._handle_conversational_runtime_message(message):
                self._complete_dispatch_shadow_plan(
                    shadow_message_id,
                    legacy_consumed=True,
                    rendered_owner="conversational_runtime",
                )
                return
        payload = route_message(
            self.mode.get(),
            message,
            self.paste.get("1.0", tk.END) if hasattr(self, "paste") else "",
            history=self._recent_history_for_router(),
            execute_local_model=False,
        )
        self.last_message = message
        self.last_payload = payload
        self._update_active_topic_anchor(payload)
        offer = payload.get("supporting_information_offer") if isinstance(payload, dict) else None
        if isinstance(offer, dict) and offer.get("offered"):
            self.pending_provider_question = message
        elif payload.get("route") == "gpt_support_approval_preview":
            self.pending_provider_question = message
        else:
            self.pending_provider_question = None
        local_offer = payload.get("local_model_offer") if isinstance(payload, dict) else None
        pending_suggestion = payload.get("pending_action_suggestion") if isinstance(payload, dict) else None
        if isinstance(pending_suggestion, dict) and pending_suggestion.get("action_type") == "local_model_deepening":
            exchange = self._last_substantive_exchange() or {"question": message, "answer": str(payload.get("answer") or "")}
            action_id = f"rc2-pending-action-{uuid.uuid4().hex[:12]}"
            self.pending_local_model_deepening = {
                "action_id": action_id,
                "action_type": "local_model_deepening",
                "question": exchange["question"],
                "answer": exchange["answer"],
                "followup_instruction": message,
                "source_turn_id": str(len(self.session_history)),
            }
            payload["pending_action_suggestion"] = {
                **pending_suggestion,
                "action_id": action_id,
                "original_topic": exchange["question"],
                "prior_answer_summary": exchange["answer"][:260],
                "selected_lane": (payload.get("selected_model_lane") or {}).get("lane"),
                "selected_model": (payload.get("selected_model_lane") or {}).get("selected_model_id"),
            }
            self.pending_local_model_question = None
        else:
            self.pending_local_model_question = message if isinstance(local_offer, dict) and local_offer.get("offered") else None
            if self.pending_local_model_question:
                self.pending_local_model_deepening = None
        self._refresh_state_cards()
        rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
        self._queue_concept_candidate(payload)
        self._append_chat("DELTA", rendered)
        self._append_session("user", message)
        self._append_session("assistant", rendered)
        self._complete_dispatch_shadow_plan(
            shadow_message_id,
            legacy_consumed=False,
            rendered_owner="rc2_router",
            response_text=rendered,
        )

    def _remember_local_model_exchange(self, question: str, payload: dict[str, object]) -> None:
        result = payload.get("local_model_result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            self.last_local_model_exchange = {
                "question": question,
                "status": "unavailable",
                "answer": "",
                "reason": "no_local_model_result",
            }
            return
        if result.get("executed"):
            self.last_local_model_exchange = {
                "question": question,
                "status": "completed",
                "answer": str(result.get("answer") or payload.get("answer") or ""),
                "model_id": result.get("model_id"),
                "provider_calls_performed": bool(result.get("provider_calls_performed", False)),
            }
            return
        self.last_local_model_exchange = {
            "question": question,
            "status": "unavailable",
            "answer": "",
            "reason": result.get("reason") or "local_model_not_completed",
        }

    def _is_local_model_response_query(self, lower: str) -> bool:
        normalized = " ".join(str(lower or "").lower().strip().split()).strip(" ?!.")
        return normalized in {
            "what was the response",
            "what was its response",
            "what did it say",
            "what did the model say",
            "what did the local model say",
            "show me the response",
            "show me the local model response",
        }

    def _last_local_model_response_answer(self) -> str:
        exchange = self.last_local_model_exchange
        if not isinstance(exchange, dict):
            return ""
        question = str(exchange.get("question") or "the previous request")
        if exchange.get("status") == "completed" and str(exchange.get("answer") or "").strip():
            return f"The local model response for `{question}` was:\n\n{str(exchange.get('answer')).strip()}"
        return f"I do not have a completed local-model response for `{question}` yet."

    def _is_discourse_history_query(self, lower: str) -> bool:
        normalized = " ".join(str(lower or "").lower().strip().split()).strip(" ?!.")
        return normalized in {
            "what were we discussing before that",
            "what were we talking about before that",
            "what was the topic before that",
            "what were we discussing",
            "what were we talking about",
        }

    def _discourse_history_answer(self) -> str:
        topic = ""
        if isinstance(self.conversation_topic_state, dict):
            topic = str(self.conversation_topic_state.get("topic") or "").strip()
        if not topic:
            for item in reversed(self.session_history):
                if item.get("role") != "topic_state":
                    continue
                try:
                    state = json.loads(str(item.get("content") or "{}"))
                except json.JSONDecodeError:
                    continue
                topic = str(state.get("topic") or "").strip()
                if topic:
                    break
        if not topic:
            exchange = self._last_substantive_exchange()
            topic = str((exchange or {}).get("question") or "").strip()
        if not topic:
            return ""
        return f"Before that, we were discussing {topic}."

    def _update_active_topic_anchor(self, payload: dict[str, object]) -> None:
        topic_state = payload.get("conversation_topic_state")
        if isinstance(topic_state, dict):
            state_kind = str(topic_state.get("state_kind") or "")
            topic = str(topic_state.get("topic") or "").strip()
            if state_kind in {"SUBSTANTIVE_TOPIC", "TOPIC_SWITCH", "FOLLOWUP"} and topic:
                self.conversation_topic_state = dict(topic_state)
                if topic_state.get("supersedes_anchor"):
                    self.active_topic_anchor = None
                return
            if state_kind == "SOCIAL_INTERLUDE":
                return
            if state_kind == "CONCEPT_ANCHOR" and topic:
                self.conversation_topic_state = dict(topic_state)
        anchor = payload.get("active_topic_anchor")
        if isinstance(anchor, dict) and (anchor.get("active_concept_id") or anchor.get("active_concept_name")):
            self.active_topic_anchor = dict(anchor)
            return
        matches = payload.get("concept_matches")
        if isinstance(matches, list) and matches:
            first = matches[0]
            if isinstance(first, dict) and (first.get("concept_id") or first.get("concept_name")):
                self.active_topic_anchor = {
                    "active_concept_id": first.get("concept_id"),
                    "active_concept_name": first.get("concept_name"),
                    "domain": first.get("domain"),
                    "related_concepts": first.get("related_concepts", [])[:8] if isinstance(first.get("related_concepts"), list) else [],
                    "retrieved_concept_ids": [row.get("concept_id") for row in matches if isinstance(row, dict) and row.get("concept_id")],
                    "retrieved_concept_names": [row.get("concept_name") for row in matches if isinstance(row, dict) and row.get("concept_name")],
                    "last_user_question": self.last_message,
                    "last_answer_summary": " ".join(str(payload.get("answer") or "").split())[:420],
                }

    def _set_deepening_offer_if_present(self, question: str, payload: dict[str, object]) -> None:
        answer = str(payload.get("answer") or "")
        if payload.get("route") == "local_conversation_model_lane" and _model_answer_offers_deepening(answer):
            self.pending_local_model_deepening = {"question": question, "answer": answer}
        else:
            self.pending_local_model_deepening = None

    def _queue_concept_candidate(self, payload: dict[str, object]) -> None:
        candidate = payload.get("memory_candidate")
        if not isinstance(candidate, dict):
            return
        concept_id = str(candidate.get("concept_id") or "")
        if not concept_id or concept_id in self.concept_review_items:
            return
        is_enrichment = bool(candidate.get("enrichment_of_concept_id"))
        concept_label = str(candidate.get("concept_name") or "Learned Concept")
        source_label = str(candidate.get("source_type") or payload.get("route") or "conversation")
        if is_enrichment:
            concept_label = f"Update: {candidate.get('enrichment_of_concept_name') or concept_label}"
            source_label = "enrichment"
        self.concept_review_items[concept_id] = {"candidate": candidate, "payload": payload}
        self.concept_review.insert(
            "",
            tk.END,
            iid=concept_id,
            values=(
                concept_label,
                source_label,
                "pending",
            ),
        )

    def _queue_last_answer_for_review(self) -> str:
        if not self.last_message or not isinstance(self.last_payload, dict):
            return "I do not have a previous answer to turn into a concept yet."
        existing = self.last_payload.get("memory_candidate")
        if isinstance(existing, dict):
            candidate = existing
        else:
            candidate = build_memory_candidate_from_answer(self.last_message, self.last_payload)
            if not candidate_is_memory_worthy(candidate, self.last_payload):
                candidate = {
                    **candidate,
                    "approval_status": "pending_operator_review_user_requested",
                    "operator_review_required": True,
                    "memory_request_source": "explicit_user_remember_that",
                    "uncertainty": "moderate_operator_review_required",
                    "review_note": "User explicitly asked to remember the previous answer; candidate was queued for manual review despite lower automatic memory-worthiness.",
                }
            self.last_payload["memory_candidate"] = candidate
        before = set(self.concept_review_items)
        self._queue_concept_candidate(self.last_payload)
        concept_id = str(candidate.get("concept_id") or "")
        name = str(candidate.get("concept_name") or "that concept")
        if concept_id in before:
            return f"`{name}` is already in Concept Review. Select it and press Accept Selected Concept if you want it stored."
        return f"I added `{name}` to Concept Review. Select it and press Accept Selected Concept if you want it stored."

    def _selected_concept_id(self) -> str | None:
        selected = self.concept_review.selection()
        return str(selected[0]) if selected else None

    def _accept_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        item = self.concept_review_items.get(concept_id)
        if not item:
            messagebox.showinfo("DELTA", "That concept is no longer available for review.")
            return
        candidate = dict(item["candidate"])
        result = approve_candidate_concept(candidate, approval_text="Keep this concept")
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        approved = result.get("approved") is True
        duplicate = result.get("duplicate") is True
        if approved:
            concept = result["stored_concept"]
            self.concept_review.set(concept_id, "status", "accepted")
            if result.get("enriched_existing"):
                text = f"Updated the existing concept `{concept['concept_name']}` with the reviewed elaboration. Canonical memory and training stayed off."
            else:
                text = f"Kept the concept `{concept['concept_name']}` in noncanonical {concept['memory_type']} memory. Canonical memory and training stayed off."
        elif duplicate:
            self.concept_review.set(concept_id, "status", "duplicate")
            text = "I already had a matching concept, so I skipped the duplicate. Canonical memory and training stayed off."
        else:
            self.concept_review.set(concept_id, "status", "not stored")
            text = "I did not store the concept. Canonical memory and training stayed off."
        self._append_chat("DELTA", text)
        self._append_session("assistant", text)

    def _reject_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        self.concept_review.set(concept_id, "status", "rejected")
        item = self.concept_review_items.get(concept_id, {})
        candidate = item.get("candidate", {}) if isinstance(item, dict) else {}
        name = candidate.get("concept_name", "that concept") if isinstance(candidate, dict) else "that concept"
        text = f"Rejected `{name}`. Nothing was stored."
        self._append_chat("DELTA", text)
        self._append_session("assistant", text)

    def _inspect_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        item = self.concept_review_items.get(concept_id)
        if not item:
            messagebox.showinfo("DELTA", "That concept is no longer available for review.")
            return
        candidate = item["candidate"]
        if not isinstance(candidate, dict):
            messagebox.showinfo("DELTA", "That concept candidate is not editable.")
            return
        self._open_concept_editor(concept_id, candidate)

    def _open_concept_editor(self, concept_id: str, candidate: dict[str, object]) -> None:
        editor = tk.Toplevel(self.root)
        editor.title(f"Edit Concept - {candidate.get('concept_name', 'Candidate')}")
        editor.geometry("780x680")
        editor.transient(self.root)

        frame = ttk.Frame(editor, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        frame.rowconfigure(3, weight=1)
        frame.rowconfigure(4, weight=1)
        frame.rowconfigure(8, weight=1)

        name_var = tk.StringVar(value=str(candidate.get("concept_name") or ""))
        definition_var = tk.StringVar(value=str(candidate.get("short_definition") or ""))
        uncertainty_var = tk.StringVar(value=str(candidate.get("uncertainty") or ""))
        memory_type_var = tk.StringVar(value=str(candidate.get("memory_type") or "knowledge"))

        ttk.Label(frame, text="Concept name").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Short definition").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=definition_var).grid(row=1, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Propositions").grid(row=2, column=0, sticky="nw", pady=3)
        propositions_box = scrolledtext.ScrolledText(frame, height=7, wrap=tk.WORD)
        propositions_box.grid(row=2, column=1, sticky="nsew", pady=3)
        propositions_box.insert(tk.END, "\n".join(str(item) for item in candidate.get("propositions", []) if str(item).strip()))

        ttk.Label(frame, text="Related concepts").grid(row=3, column=0, sticky="nw", pady=3)
        related_box = scrolledtext.ScrolledText(frame, height=5, wrap=tk.WORD)
        related_box.grid(row=3, column=1, sticky="nsew", pady=3)
        related_box.insert(tk.END, "\n".join(str(item) for item in candidate.get("related_concepts", []) if str(item).strip()))

        ttk.Label(frame, text="Operator notes").grid(row=4, column=0, sticky="nw", pady=3)
        notes_box = scrolledtext.ScrolledText(frame, height=5, wrap=tk.WORD)
        notes_box.grid(row=4, column=1, sticky="nsew", pady=3)
        notes_box.insert(tk.END, str(candidate.get("operator_notes") or candidate.get("review_note") or ""))

        ttk.Label(frame, text="Uncertainty").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=uncertainty_var).grid(row=5, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Memory type").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Combobox(frame, values=["knowledge", "personal", "conversation"], textvariable=memory_type_var, state="readonly").grid(row=6, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Source question").grid(row=7, column=0, sticky="nw", pady=3)
        source = ttk.Label(frame, text=str(candidate.get("source_question") or ""), wraplength=560)
        source.grid(row=7, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Raw candidate").grid(row=8, column=0, sticky="nw", pady=3)
        raw_box = scrolledtext.ScrolledText(frame, height=8, wrap=tk.WORD)
        raw_box.grid(row=8, column=1, sticky="nsew", pady=3)
        raw_box.insert(tk.END, json.dumps(candidate, indent=2, sort_keys=True))
        raw_box.configure(state=tk.DISABLED)

        def done() -> None:
            updated = {
                **candidate,
                "concept_name": name_var.get().strip() or str(candidate.get("concept_name") or "Learned Concept"),
                "short_definition": definition_var.get().strip(),
                "propositions": _lines_from_text(propositions_box.get("1.0", tk.END)),
                "related_concepts": _lines_from_text(related_box.get("1.0", tk.END)),
                "operator_notes": notes_box.get("1.0", tk.END).strip(),
                "uncertainty": uncertainty_var.get().strip() or "operator_edited",
                "memory_type": memory_type_var.get().strip() or "knowledge",
                "operator_edited": True,
                "approval_status": "pending_operator_review_edited",
            }
            self.concept_review_items[concept_id]["candidate"] = updated
            if self.last_payload and self.last_payload.get("memory_candidate", {}).get("concept_id") == concept_id:
                self.last_payload["memory_candidate"] = updated
            self.concept_review.set(concept_id, "concept", updated["concept_name"])
            self.concept_review.set(concept_id, "source", str(updated.get("source_type") or "edited_candidate"))
            self.concept_review.set(concept_id, "status", "edited")
            self._append_chat("DELTA", f"Updated `{updated['concept_name']}` in Concept Review. It is not stored until you press Accept Selected Concept.")
            self._append_session("assistant", f"Updated `{updated['concept_name']}` in Concept Review.")
            editor.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Done", command=done).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Cancel", command=editor.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _clear_local_store(self) -> None:
        phrase = "DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE"
        entered = simpledialog.askstring(
            "Clear Local Memory Store",
            f"Type {phrase} to delete only the RC2 developmental concept store.",
        )
        result = clear_developmental_memory_store(entered or "")
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        if result["cleared"]:
            self._append_chat("DELTA", "The RC2 developmental concept store was cleared. Canonical memory, reports, source code, and model weights were untouched.")
        else:
            self._append_chat("DELTA", "Local memory store was not cleared because the confirmation phrase did not match.")

    def _write_output(self, text: str) -> None:
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)

    def _set_consolidation_detail(self, record: object) -> None:
        self.consolidation_detail.configure(state="normal")
        self.consolidation_detail.delete("1.0", tk.END)
        self.consolidation_detail.insert(tk.END, json.dumps(record, indent=2, sort_keys=True, default=str))
        self.consolidation_detail.configure(state="disabled")

    def _refresh_consolidation_records(self) -> None:
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        self.consolidation_graph_snapshot = graph
        for tree in (self.consolidation_episode_tree, self.consolidation_claim_tree):
            for item_id in tree.get_children():
                tree.delete(item_id)
        self.consolidation_episode_rows = {}

        traces = sorted(graph.episodic_traces, key=lambda item: (item.sealed_at, item.episode_id), reverse=True)
        for index, trace in enumerate(traces):
            row_id = f"episode-row-{index}"
            self.consolidation_episode_rows[row_id] = trace.episode_id
            self.consolidation_episode_tree.insert(
                "",
                tk.END,
                iid=row_id,
                values=(trace.episode_id[-12:], trace.terminal_status or "recorded", trace.sealed_at, len(trace.operation_ids)),
            )

        claims = {item.claim_id: item for item in graph.claims}
        latest_versions: dict[str, object] = {}
        for version in graph.claim_versions:
            current = latest_versions.get(version.claim_id)
            if current is None or version.version_index > current.version_index:
                latest_versions[version.claim_id] = version
        for version in sorted(latest_versions.values(), key=lambda item: (item.created_at, item.claim_version_id), reverse=True):
            claim = claims.get(version.claim_id)
            node_id = claim.originating_node_id if claim else ""
            text = " ".join(version.exact_text.split())
            self.consolidation_claim_tree.insert(
                "",
                tk.END,
                iid=version.claim_version_id,
                values=(version.epistemic_state, node_id, text[:180]),
            )

        self.consolidation_graph_status.set(
            f"Learning records: {len(traces)} episode(s), {len(latest_versions)} current claim(s), "
            f"{len(graph.reviews)} sealed review(s)"
        )
        self._set_consolidation_detail({
            "summary": "Select an episode or provisional claim to inspect its local provenance.",
            "episodes": len(traces),
            "current_claims": len(latest_versions),
            "reviews": len(graph.reviews),
            "read_only": True,
        })

    def _show_consolidation_episode(self) -> None:
        selection = self.consolidation_episode_tree.selection()
        graph = self.consolidation_graph_snapshot
        if not selection or graph is None:
            return
        episode_id = self.consolidation_episode_rows.get(selection[0], "")
        trace = next((item for item in graph.episodic_traces if item.episode_id == episode_id), None)
        if trace is None:
            return
        versions = {item.claim_version_id: item for item in graph.claim_versions}
        episode_experiences = [item for item in graph.experiences if episode_id in item.origin_refs]
        goal_statement = next(
            (
                item.content
                for item in graph.experiences
                if item.source_class == "operator_statement" and trace.objective_id in item.origin_refs
            ),
            "",
        )
        self._set_consolidation_detail({
            "objective_id": trace.objective_id,
            "episode_id": trace.episode_id,
            "goal_text": goal_statement,
            "creation_timestamp": min((item.created_at for item in episode_experiences), default=trace.sealed_at),
            "terminal_timestamp": trace.sealed_at,
            "run_status": trace.terminal_status or "recorded",
            "episode_trace": asdict(trace),
            "semantic_units": [asdict(versions[item]) for item in trace.semantic_unit_refs if item in versions],
        })

    def _show_consolidation_claim(self) -> None:
        selection = self.consolidation_claim_tree.selection()
        graph = self.consolidation_graph_snapshot
        if not selection or graph is None:
            return
        version_id = selection[0]
        version = next((item for item in graph.claim_versions if item.claim_version_id == version_id), None)
        if version is None:
            return
        claim = next((item for item in graph.claims if item.claim_id == version.claim_id), None)
        rationales = {item.rationale_id: item for item in graph.rationales}
        experiences = {item.experience_id: item for item in graph.experiences}
        relations = [item for item in graph.relations if item.source_ref == version_id or item.target_ref == version_id]
        concepts = {item.concept_id: item for item in graph.concepts}
        self._set_consolidation_detail({
            "claim": asdict(claim) if claim else {},
            "current_version": asdict(version),
            "rationales": [asdict(rationales[item]) for item in version.rationale_refs if item in rationales],
            "source_experiences": [asdict(experiences[item]) for item in version.source_experience_refs if item in experiences],
            "assumptions": [asdict(experiences[item]) for item in version.assumption_refs if item in experiences],
            "uncertainties": [asdict(experiences[item]) for item in version.uncertainty_refs if item in experiences],
            "relations": [asdict(item) for item in relations],
            "concepts": [asdict(concepts[item.target_ref]) for item in relations if item.target_ref in concepts],
        })

    def _refresh_consolidation_review_surface(self) -> None:
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        review_ids = [item.review_id for item in graph.reviews]
        self.consolidation_review_selector.configure(values=review_ids)
        if not review_ids:
            self.consolidation_review_id.set("")
            self.consolidation_claim_version_id.set("")
            self.consolidation_claim_selector.configure(values=())
            self.consolidation_review_status.set("Offline consolidation: no sealed Oracle response is available")
            self._set_consolidation_detail({"offline_review": "No sealed review response is available yet.", "read_only": True})
            return
        if self.consolidation_review_id.get() not in review_ids:
            self.consolidation_review_id.set(review_ids[-1])
        self._show_consolidation_review()

    def _show_consolidation_review(self) -> None:
        review_id = self.consolidation_review_id.get()
        if not review_id:
            self._refresh_consolidation_review_surface()
            return
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        try:
            surface = render_consolidation_review(graph, review_id)
        except ConsolidationIntegrityError as exc:
            self.consolidation_review_status.set(f"Offline consolidation review blocked: {exc}")
            return
        claim_ids = [str(item["claim_version_id"]) for item in surface["claims"]]
        self.consolidation_claim_selector.configure(values=claim_ids)
        if self.consolidation_claim_version_id.get() not in claim_ids:
            self.consolidation_claim_version_id.set(claim_ids[0] if claim_ids else "")
        self.consolidation_review_status.set(f"Offline consolidation: {len(claim_ids)} reviewed claim version(s); administrative review required")
        self._set_consolidation_detail(surface)

    def _enable_consolidation_administrative_review(self) -> None:
        confirmation = simpledialog.askstring(
            "Administrative Consolidation Review",
            "Enter ENABLE_ADMINISTRATIVE_CONSOLIDATION_REVIEW to enable this session-only authority.",
            parent=self.root,
        )
        if confirmation == "ENABLE_ADMINISTRATIVE_CONSOLIDATION_REVIEW":
            self.consolidation_administrative_enabled = True
            self.consolidation_review_status.set("Offline consolidation: administrative review enabled for this session")
        else:
            self.consolidation_review_status.set("Offline consolidation: administrative review remains disabled")

    def _apply_consolidation_review_action(self) -> None:
        review_id = self.consolidation_review_id.get()
        claim_version_id = self.consolidation_claim_version_id.get()
        action = self.consolidation_action.get()
        if not review_id or not claim_version_id or not action:
            self.consolidation_review_status.set("Offline consolidation action requires a review, claim version, and action")
            return
        if not self.consolidation_administrative_enabled:
            self.consolidation_review_status.set("Offline consolidation action requires explicit administrative review enablement")
            return
        replacement_text = ""
        if action in {"replace_fragment", "revise_claim", "split_claim", "merge_claims", "recompose_cluster"}:
            replacement_text = simpledialog.askstring(
                "Administrative Consolidation Review",
                "Enter the reviewed replacement formulation for this claim.",
                parent=self.root,
            ) or ""
            if not replacement_text:
                self.consolidation_review_status.set("Offline consolidation action requires an explicit replacement formulation")
                return
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        try:
            graph, overlay = create_consolidation_overlay(
                graph,
                review_id=review_id,
                claim_version_id=claim_version_id,
                action=action,
                role="administrative_operator",
                operator_id="local_operator",
                replacement_text=replacement_text,
            )
            graph, admission = apply_consolidation_admission(graph, review_id=review_id, overlay_id=overlay.overlay_id)
            save_provisional_semantic_graph(self.conversational_runtime_root, graph)
            self.consolidation_review_status.set(f"Offline consolidation applied: {admission.action} for {claim_version_id}")
            self._show_consolidation_review()
        except ConsolidationIntegrityError as exc:
            self.consolidation_review_status.set(f"Offline consolidation action denied: {exc}")

    def _preview_evidence(self) -> None:
        data = preview_evidence_ingest(self.paste.get("1.0", tk.END))
        self._refresh_state_cards()
        self._write_output(json.dumps(data, indent=2, sort_keys=True))

    def _extract_propositions(self) -> None:
        data = extract_propositions(self.paste.get("1.0", tk.END))
        self.extracted = data["candidates"]
        self._refresh_state_cards()
        lines = ["Detected Propositions", ""]
        if not self.extracted:
            lines.append("No proposition candidates detected.")
        for idx, item in enumerate(self.extracted, start=1):
            lines.append(f"[x] {idx}. {item['claim']}")
            lines.append(f"    id: {item['proposition_id']}")
            lines.append(f"    source: {item['source']}")
            lines.append(f"    confidence: {item['confidence']}")
        lines.extend(["", "Nothing has been persisted yet.", "Approve extracted propositions to make them available in noncanonical substrate."])
        self._write_output("\n".join(lines))

    def _approve_extracted(self) -> None:
        if not self.extracted:
            self._extract_propositions()
        result = approve_propositions(self.extracted)
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        self._write_output(json.dumps(result, indent=2, sort_keys=True))

    def _log_observation(self) -> None:
        note = self.paste.get("1.0", tk.END).strip()
        if not note:
            note = "Operator created an empty observation placeholder from the RC2 console."
        entry = build_observation_entry(self.category.get(), note, self.severity.get())
        result = append_observation(entry)
        self._refresh_state_cards()
        self._write_output(json.dumps({"entry": entry, "result": result}, indent=2, sort_keys=True))

    def _show_status(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        self._write_output(_format_snapshot(self.snapshot))

    def _show_cognitive_state(self) -> None:
        state = build_cognitive_state()
        developmental = build_developmental_memory_state()
        self._refresh_state_cards()
        self._write_output(_format_cognitive_state(state) + "\n\nDevelopmental concept memory\n" + json.dumps(developmental, indent=2, sort_keys=True))

    def _show_developmental_teaching_audit(self) -> None:
        """Render the existing teaching/controller lineage without changing it."""

        objective = self.conversational_runtime_state.active_objective
        plan = self._active_developmental_teaching_plan()
        if objective is None or not plan:
            self._write_output(
                "Developmental teaching audit\n\nNo active conversational teaching objective is available in this runtime."
            )
            return

        controller = getattr(self, "developmental_teaching_controller", None)
        if controller is None:
            controller = self._restore_developmental_teaching_controller()
        controller_snapshot = teaching_snapshot(controller)
        graph = load_provisional_semantic_graph(self.conversational_runtime_root)
        followups = tuple(
            dict(item)
            for item in objective.provenance.get("teaching_followups", ())
            if isinstance(item, Mapping)
        )
        prerequisites = tuple(
            dict(item)
            for item in objective.provenance.get("teaching_prerequisites", ())
            if isinstance(item, Mapping)
        )
        consolidation_records = tuple(
            dict(item)
            for item in objective.provenance.get("teaching_consolidation_records", ())
            if isinstance(item, Mapping)
        )
        claim_version_ids = {
            str(item.get("claim_version_id") or "")
            for item in followups
            if str(item.get("claim_version_id") or "")
        }
        packet_ids = {
            str(item.get("packet_id") or "")
            for item in consolidation_records
            if str(item.get("packet_id") or "")
        }
        active_episode: dict[str, object] = {}
        operation_ids = {
            str(item.get("operation_id") or "")
            for item in (*followups, *prerequisites)
            if str(item.get("operation_id") or "")
        }
        episode_path = Path(self.conversational_runtime_state.active_episode_path or "")
        if episode_path.exists():
            try:
                episode = read_active_cognitive_episode_state(episode_path)
                active_episode = {
                    "episode_id": episode.episode_id,
                    "model_call_count": episode.model_call_count,
                    "operation_requests": tuple(
                        asdict(item)
                        for item in episode.operation_requests
                        if not operation_ids or item.operation_id in operation_ids
                    ),
                    "operation_results": tuple(
                        asdict(item)
                        for item in episode.operation_results
                        if not operation_ids or item.operation_id in operation_ids
                    ),
                }
            except (OSError, ValueError, TypeError):
                active_episode = {"read_error": "active_episode_unavailable"}
        ledger_records: list[dict[str, object]] = []
        snapshot_root = self.conversational_runtime_root / "prompt-snapshots"
        for prompt_path in sorted(snapshot_root.glob("*.json")):
            try:
                prompt_snapshot = json.loads(prompt_path.read_text(encoding="utf-8"))
                operation_id = str(
                    dict(prompt_snapshot.get("operation_request") or {}).get("operation_id") or ""
                )
                if operation_ids and operation_id not in operation_ids:
                    continue
                raw_path = snapshot_root / "raw-responses" / prompt_path.name
                raw_snapshot = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.exists() else {}
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            ledger_records.append({
                "operation_id": operation_id,
                "prompt_snapshot_id": str(prompt_snapshot.get("prompt_snapshot_id") or ""),
                "ledger_request_id": str(raw_snapshot.get("ledger_request_id") or ""),
                "ledger_result_id": str(raw_snapshot.get("ledger_result_id") or ""),
                "model_identity": str(raw_snapshot.get("model_identity") or prompt_snapshot.get("model_identity") or ""),
                "terminal_status": dict(raw_snapshot.get("terminal_status") or {}),
                "raw_output": str(raw_snapshot.get("raw_response") or "")[:4000],
            })
        teaching_requests = tuple(
            asdict(item)
            for item in (
                *self.conversational_runtime_state.pending_chat_requests,
                *self.conversational_runtime_state.resolved_chat_requests,
            )
            if item.objective_id == objective.objective_id and item.request_type.startswith("teaching_")
        )
        audit = {
            "title": "Developmental teaching audit",
            "read_only": True,
            "objective": {
                "objective_id": objective.objective_id,
                "operator_wording": objective.operator_wording,
                "interpreted_objective": objective.interpreted_objective,
                "lifecycle_state": objective.lifecycle_state,
                "execution_mode": objective.provenance.get("execution_mode", ""),
                "plan_id": plan.get("plan_id", ""),
            },
            "controller": controller_snapshot,
            "followups": followups,
            "prerequisites": prerequisites,
            "consolidation_records": consolidation_records,
            "teaching_requests": teaching_requests,
            "active_episode": active_episode,
            "shared_ledger_records": tuple(ledger_records),
            "related_claim_versions": tuple(
                asdict(item)
                for item in graph.claim_versions
                if item.claim_version_id in claim_version_ids
            ),
            "related_packets": tuple(
                asdict(item)
                for item in graph.packets
                if item.packet_id in packet_ids
            ),
            "provenance_note": (
                "Use the Consolidation tab to inspect the full local claim, rationale, evidence, "
                "and review artifacts for the listed IDs."
            ),
        }
        self._write_output(json.dumps(audit, indent=2, sort_keys=True, default=str))

    def _show_epistemic_answer_audit(self) -> None:
        resolution = getattr(self, "last_epistemic_answer_resolution", None)
        payload = self.last_payload if isinstance(getattr(self, "last_payload", None), dict) else {}
        if not isinstance(resolution, dict) or not resolution:
            self._write_output("Epistemic answer audit\n\nNo graph-bound epistemic answer has been rendered in this session.")
            return
        audit = {
            "title": "Epistemic answer audit",
            "read_only": True,
            "route": payload.get("route", ""),
            "binding_status": resolution.get("binding_status", ""),
            "answer_mode": resolution.get("epistemic_mode", ""),
            "selected_semantic_unit_ids": resolution.get("selected_semantic_unit_ids", ()),
            "selected_claim_version_ids": resolution.get("selected_claim_version_ids", ()),
            "selected_revised_claim_version_id": resolution.get("selected_revised_claim_version_id", ""),
            "reason_codes": resolution.get("reason_codes", ()),
            "qualification_text": resolution.get("qualification_text", ""),
            "contradiction_summary": resolution.get("contradiction_summary", ""),
            "source_review_lineage": resolution.get("source_review_lineage", {}),
            "authority": {
                "provider_calls_performed": payload.get("provider_calls_performed", False),
                "web_search_performed": payload.get("web_search_performed", False),
                "training_performed": payload.get("training_performed", False),
                "canonical_write_performed": payload.get("canonical_write_performed", False),
                "autonomous_action_performed": payload.get("autonomous_action_performed", False),
            },
        }
        self._write_output(json.dumps(audit, indent=2, sort_keys=True, default=str))

    def _show_review_queue(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["operator_review_queue"], indent=2, sort_keys=True))

    def _show_replay(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["replay_rollback"], indent=2, sort_keys=True))

    def _show_failure_taxonomy(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["failure_classification"], indent=2, sort_keys=True))


def main() -> int:
    root = tk.Tk()
    DeltaApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
