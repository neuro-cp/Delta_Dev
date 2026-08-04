from dataclasses import replace

from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    handle_conversational_message,
    is_developmental_governance_message,
    start_or_restore_runtime,
)
from orchestration.runtime.developmental_teaching_runtime import derive_teaching_pressures


PHOTOGRAPHY_GOAL = "Teach me introductory photography."


def _connections_retention_state(tmp_path):
    state = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        PHOTOGRAPHY_GOAL,
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state
    objective = state.active_objective
    assert objective is not None
    followup = {
        "followup_id": "followup-connections",
        "lesson_id": "lesson-connections",
        "lesson_title": "Connections",
        "source_gap": "address Connections",
        "question": "How do Connections fit into introductory photography?",
        "status": "provisional_ready_for_retention",
        "developmental_action_state": "completed_pending_retention",
        "claim_version_id": "claim-version-connections",
        "operation_id": "operation-connections",
        "interpretation": "Exposure controls connect aperture, shutter speed, and ISO.",
        "origin": "endogenous_terminal_gap_recovery",
    }
    request = ChatAddressableRequest(
        request_id="retention-connections",
        request_type="teaching_provisional_retention",
        objective_id=objective.objective_id,
        originating_goal_id=objective.objective_id,
        goal_label="Provisional teaching retention",
        prompt_text="Should I remember the provisional Connections explanation?",
        created_turn_id="connections-result-turn",
        rendered_turn_id="connections-retention-turn",
        created_sequence=5,
        render_sequence=6,
        accepted_response_types=("approved", "denied"),
        baseline_metrics={
            "followup_id": followup["followup_id"],
            "claim_version_id": followup["claim_version_id"],
        },
    )
    objective = replace(
        objective,
        provenance={
            **objective.provenance,
            "teaching_followups": (followup,),
        },
    )
    return replace(
        state,
        lifecycle_state="paused_operator",
        active_objective=objective,
        pending_chat_requests=(request,),
    )


def test_operator_deprioritization_binds_to_connections_and_consumes_retention_once(tmp_path):
    state = _connections_retention_state(tmp_path)
    message = "Actually, don't prioritize Connections right now. Keep it pending and continue the broader photography structure."

    result = handle_conversational_message(state, message, runtime_root=tmp_path, run_background_cycle=False)

    followup = result.state.active_objective.provenance["teaching_followups"][0]
    assert result.intent.intent_type == "developmental_deprioritize"
    assert followup["status"] == "retention_deferred"
    assert followup["developmental_action_state"] == "operator_deprioritized"
    assert followup["operator_suppressed"] is True
    assert followup["operator_resumption_posture"] == "parent_context_preferred"
    assert followup["claim_version_id"] == "claim-version-connections"
    assert not result.state.pending_chat_requests
    assert len(result.state.resolved_chat_requests) == 1
    resolved = result.state.resolved_chat_requests[0]
    assert resolved.request_id == "retention-connections"
    assert resolved.resolution == "operator_deprioritized"
    assert resolved.resolution_policy == "operator_deferred_provisional_retention"
    assert resolved.consumption_count == 1
    assert any(item.get("event") == "developmental_deprioritize_recorded" for item in result.state.objective_progress)
    assert result.state.lifecycle_state == "paused_budget"

    plan = result.state.active_objective.provenance["teaching_plan"]
    terminal = {
        "objective_id": result.state.active_objective.objective_id,
        "status": "partially_completed",
        "remaining_gaps": ("address Connections",),
    }
    assert not derive_teaching_pressures(plan, followups=(followup,), terminal_reports=(terminal,))

    restored = start_or_restore_runtime(tmp_path)
    restored_followup = restored.active_objective.provenance["teaching_followups"][0]
    assert restored_followup["operator_governance_latest_decision_id"] == followup["operator_governance_latest_decision_id"]
    assert len(restored.resolved_chat_requests) == 1
    repeated = handle_conversational_message(restored, message, runtime_root=tmp_path, run_background_cycle=False)
    repeated_followup = repeated.state.active_objective.provenance["teaching_followups"][0]
    assert len(repeated_followup["operator_governance_history"]) == 1


def test_operator_revision_preserves_provisional_claim_and_blocks_retention(tmp_path):
    state = _connections_retention_state(tmp_path)

    result = handle_conversational_message(
        state,
        "That Connections result is too vague. Mark it for revision before retaining it.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    followup = result.state.active_objective.provenance["teaching_followups"][0]
    assert result.intent.intent_type == "developmental_request_revision"
    assert followup["status"] == "revision_requested"
    assert followup["developmental_action_state"] == "operator_revision_requested"
    assert followup["operator_resumption_posture"] == "revision_required_before_retention"
    assert followup["claim_version_id"] == "claim-version-connections"
    assert followup["operator_governance_history"][0]["prior_status"] == "provisional_ready_for_retention"
    assert not result.state.pending_chat_requests
    resolved = result.state.resolved_chat_requests[0]
    assert resolved.status == "revision_requested"
    assert resolved.resolution == "operator_revision_requested"
    assert resolved.resolution_policy == "operator_revision_blocks_provisional_retention"
    assert resolved.consumption_count == 1

    restored = start_or_restore_runtime(tmp_path)
    restored_followup = restored.active_objective.provenance["teaching_followups"][0]
    assert restored_followup["claim_version_id"] == "claim-version-connections"
    assert restored_followup["status"] == "revision_requested"
    assert not restored.pending_chat_requests


def test_external_review_can_be_operator_deferred_without_provider_or_admission(tmp_path):
    state = _connections_retention_state(tmp_path)
    objective = state.active_objective
    assert objective is not None
    record = {
        "packet_id": "packet-connections",
        "cohort_id": "cohort-connections",
        "claim_version_ids": ("claim-version-connections",),
        "review_authorization_status": "authorized_pending_external_review",
        "review_status": "pending_external_review",
        "review_authority_granted": True,
        "external_review_result_id": "",
        "admission_id": "",
    }
    objective = replace(
        objective,
        provenance={
            **objective.provenance,
            "teaching_consolidation_records": (record,),
        },
    )
    state = replace(state, active_objective=objective, pending_chat_requests=())

    result = handle_conversational_message(
        state,
        "External review is not available right now. Keep it pending and stop surfacing it unless I ask.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    updated = result.state.active_objective.provenance["teaching_consolidation_records"][0]
    assert result.intent.intent_type == "developmental_defer_external_review"
    assert updated["review_status"] == "operator_deferred_external_review"
    assert updated["review_authority_granted"] is True
    assert updated["external_review_result_id"] == ""
    assert updated["admission_id"] == ""
    assert updated["operator_suppressed"] is True
    assert not derive_teaching_pressures(
        result.state.active_objective.provenance["teaching_plan"],
        consolidation_records=(updated,),
    )

    status = handle_conversational_message(
        result.state,
        "What did you change about the external review?",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert status.intent.intent_type == "developmental_governance_status"
    assert "operator deferred external review" in status.reply.lower()
    assert status.developmental_governance["source_kind"] == "consolidation_record"
    assert status.developmental_governance["source_record_id"] == "packet-connections"

    restored = start_or_restore_runtime(tmp_path)
    restored_record = restored.active_objective.provenance["teaching_consolidation_records"][0]
    assert restored_record["review_status"] == "operator_deferred_external_review"
    assert restored_record["external_review_result_id"] == ""
    assert restored_record["admission_id"] == ""


def test_governance_status_is_source_bound_and_ordinary_chat_remains_ordinary(tmp_path):
    state = _connections_retention_state(tmp_path)
    deferred = handle_conversational_message(
        state,
        "Actually, don't prioritize Connections right now. Keep it pending.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state

    status = handle_conversational_message(
        deferred,
        "What did you change about Connections?",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    ordinary = handle_conversational_message(
        status.state,
        "What is 2 + 2?",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    assert "retention deferred" in status.reply.lower()
    assert status.state.active_objective.provenance["teaching_followups"][0]["claim_version_id"] == "claim-version-connections"
    assert is_developmental_governance_message(status.state, "What is 2 + 2?") is False
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert not ordinary.state.pending_chat_requests
    assert ordinary.state.active_objective.provenance["teaching_followups"][0]["operator_suppressed"] is True
