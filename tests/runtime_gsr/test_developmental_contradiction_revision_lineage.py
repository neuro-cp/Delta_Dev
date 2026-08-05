from dataclasses import replace

from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.epistemic_answer_mode import (
    bind_teaching_followup_question,
    resolve_production_epistemic_answer,
)
from orchestration.runtime.provisional_semantic_consolidation import (
    ClaimVersion,
    ProvisionalSemanticGraphState,
    SemanticClaim,
    load_graph,
    save_graph,
)


PHOTOGRAPHY_GOAL = "Teach me introductory photography."
SOURCE_CLAIM_VERSION_ID = "semantic-claim-version-bd554ac4b3c84fd4"
CORRECTION = (
    "Actually, that Connections explanation is incomplete. It should distinguish composition, leading lines, "
    "and visual hierarchy instead of treating Connections as a generic idea."
)
REVISED_TEXT = (
    "Connections should distinguish composition, leading lines, and visual hierarchy instead of treating Connections as a generic idea"
)


def _connections_state(tmp_path):
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
        "question_tokens": ("connections", "photography"),
        "status": "provisional_ready_for_retention",
        "developmental_action_state": "completed_pending_retention",
        "claim_version_id": SOURCE_CLAIM_VERSION_ID,
        "operation_id": "operation-connections",
        "interpretation": "Connections is a generic introductory photography idea.",
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
    objective = replace(objective, provenance={**objective.provenance, "teaching_followups": (followup,)})
    return replace(state, lifecycle_state="paused_operator", active_objective=objective, pending_chat_requests=(request,))


def _save_connections_graph(tmp_path):
    graph = ProvisionalSemanticGraphState(
        graph_id="developmental-contradiction-lineage",
        claims=(SemanticClaim("semantic-claim-b7c7ec0f6c18053c", "photography-objective", "lesson-connections", "2026-08-04T00:00:00+00:00"),),
        claim_versions=(ClaimVersion(
            SOURCE_CLAIM_VERSION_ID,
            "semantic-claim-b7c7ec0f6c18053c",
            1,
            "Connections is a generic introductory photography idea.",
            "pending_consolidation",
            (), (), (), (), "sha256:connections-source", "2026-08-04T00:00:00+00:00",
        ),),
    )
    save_graph(tmp_path, graph)


def test_material_operator_correction_creates_append_only_source_bound_revision(tmp_path):
    _save_connections_graph(tmp_path)
    result = handle_conversational_message(
        _connections_state(tmp_path), CORRECTION, runtime_root=tmp_path, run_background_cycle=False,
    )

    followup = result.state.active_objective.provenance["teaching_followups"][0]
    graph = load_graph(tmp_path)
    original = next(item for item in graph.claim_versions if item.claim_version_id == SOURCE_CLAIM_VERSION_ID)
    revision = next(item for item in graph.claim_versions if item.claim_version_id == followup["claim_version_id"])

    assert result.intent.intent_type == "developmental_apply_source_correction"
    assert followup["status"] == "revision_pending_consolidation"
    assert followup["prior_claim_version_id"] == SOURCE_CLAIM_VERSION_ID
    assert followup["revision_claim_version_id"] == revision.claim_version_id
    assert followup["revision_consolidation_eligible"] is True
    assert original.exact_text == "Connections is a generic introductory photography idea."
    assert original.epistemic_state == "pending_consolidation"
    assert revision.claim_id == original.claim_id
    assert revision.version_index == 2
    assert revision.supersedes_version_id == original.claim_version_id
    assert revision.exact_text == REVISED_TEXT
    assert revision.epistemic_state == "pending_consolidation"
    assert any(item.edge_type == "supersedes" and item.source_ref == revision.claim_version_id and item.target_ref == original.claim_version_id for item in graph.edges)
    assert any(item.relation_type == "corrects" and item.source_ref == revision.claim_version_id and item.target_ref == original.claim_version_id for item in graph.relations)
    correction_experience = next(item for item in graph.experiences if item.experience_id in revision.source_experience_refs)
    assert correction_experience.source_class == "operator_statement"
    assert correction_experience.content == CORRECTION
    assert not graph.reviews
    assert not graph.admissions
    assert not graph.packets
    assert not result.state.pending_chat_requests
    assert result.state.resolved_chat_requests[0].resolution == "operator_source_correction_recorded"
    assert result.state.resolved_chat_requests[0].consumption_count == 1


def test_revision_answer_binding_prefers_corrected_pending_version_and_restart_is_idempotent(tmp_path):
    _save_connections_graph(tmp_path)
    updated = handle_conversational_message(
        _connections_state(tmp_path), CORRECTION, runtime_root=tmp_path, run_background_cycle=False,
    ).state
    followup = updated.active_objective.provenance["teaching_followups"][0]
    graph = load_graph(tmp_path)
    binding = bind_teaching_followup_question(
        "How do Connections fit into photography?", graph, (followup,),
    )
    resolution = resolve_production_epistemic_answer(graph, binding, question="How do Connections fit into photography?")
    original_resolution = resolve_production_epistemic_answer(graph, (SOURCE_CLAIM_VERSION_ID,), question=SOURCE_CLAIM_VERSION_ID)
    assert binding == (followup["claim_version_id"],)
    assert resolution.epistemic_mode == "pending_consolidation"
    assert REVISED_TEXT in resolution.provisional_content
    assert original_resolution.selected_revised_claim_version_id == followup["claim_version_id"]
    assert "revision_selected_over_original" in original_resolution.reason_codes

    restored = start_or_restore_runtime(tmp_path)
    repeated = handle_conversational_message(restored, CORRECTION, runtime_root=tmp_path, run_background_cycle=False)
    repeated_graph = load_graph(tmp_path)
    repeated_followup = repeated.state.active_objective.provenance["teaching_followups"][0]
    assert repeated_followup["claim_version_id"] == followup["claim_version_id"]
    assert repeated_followup["prior_claim_version_id"] == SOURCE_CLAIM_VERSION_ID
    assert len(repeated_graph.claim_versions) == 2
    assert len(repeated_graph.experiences) == 1
    assert len(repeated_graph.cohorts) == 1
    assert len(repeated_followup["operator_governance_history"]) == 1


def test_correction_does_not_start_study_or_change_ordinary_chat(tmp_path):
    _save_connections_graph(tmp_path)
    corrected = handle_conversational_message(
        _connections_state(tmp_path), CORRECTION, runtime_root=tmp_path, run_background_cycle=False,
    )
    ordinary = handle_conversational_message(
        corrected.state, "What is 2 + 2?", runtime_root=tmp_path, run_background_cycle=False,
    )
    graph = load_graph(tmp_path)

    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert not ordinary.state.pending_chat_requests
    assert not ordinary.state.completed_cycle_keys
    assert len(graph.claim_versions) == 2
    assert not graph.reviews
    assert not graph.admissions
