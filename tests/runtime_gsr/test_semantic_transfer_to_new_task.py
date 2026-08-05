from dataclasses import replace

from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    handle_conversational_message,
    is_source_bound_semantic_analysis_message,
    is_source_bound_semantic_competence_measurement_message,
    is_source_bound_semantic_recall_message,
    is_source_bound_semantic_transfer_message,
    start_or_restore_runtime,
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
TRANSFER_PROMPT = (
    "Use what you revised about Connections, composition, leading lines, and visual hierarchy to organize a short "
    "explanation of how a dashboard screen should guide a user's attention."
)
ANALYSIS_PROMPT = (
    "Analyze this simple dashboard goal: \u201cA contractor wants to see overdue invoices, today's jobs, and urgent client "
    "messages on one screen.\u201d Use the learned visual-hierarchy/Connections concept to propose a layout and explain the reasoning."
)
COMPETENCE_PROMPT = (
    "Compare a baseline dashboard analysis with the revised source-bound dashboard analysis. Measure how the revised "
    "Connections concept changed the dashboard analysis and record the observed differences."
)
EFFECT_RECALL_PROMPT = "How did that affect the dashboard answer?"
DELTA_RECALL_PROMPT = "What changed from the baseline to the improved dashboard analysis?"
CHAIN_RECALL_PROMPT = "What did you revise, transfer, analyze, and measure?"


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
        graph_id="semantic-transfer-to-new-task",
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


def _corrected_state(tmp_path):
    _save_connections_graph(tmp_path)
    return handle_conversational_message(
        _connections_state(tmp_path),
        CORRECTION,
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state


def _transferred_state(tmp_path):
    return handle_conversational_message(
        _corrected_state(tmp_path),
        TRANSFER_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state


def _analyzed_state(tmp_path):
    return handle_conversational_message(
        _transferred_state(tmp_path),
        ANALYSIS_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state


def _measured_state(tmp_path):
    return handle_conversational_message(
        _analyzed_state(tmp_path),
        COMPETENCE_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state


def test_revised_teaching_claim_records_source_bound_dashboard_application_and_restart_is_idempotent(tmp_path):
    corrected = _corrected_state(tmp_path)
    before = load_graph(tmp_path)
    revised_followup = corrected.active_objective.provenance["teaching_followups"][0]
    revised_claim_version_id = revised_followup["claim_version_id"]

    assert is_source_bound_semantic_transfer_message(corrected, TRANSFER_PROMPT)
    result = handle_conversational_message(
        corrected,
        TRANSFER_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    application = result.state.active_objective.provenance["semantic_transfer_applications"][0]
    graph = load_graph(tmp_path)
    experience = next(item for item in graph.experiences if item.experience_id == application["graph_experience_id"])
    original = next(item for item in graph.claim_versions if item.claim_version_id == SOURCE_CLAIM_VERSION_ID)
    revision = next(item for item in graph.claim_versions if item.claim_version_id == revised_claim_version_id)

    assert result.intent.intent_type == "semantic_transfer_application"
    assert "composition" in result.reply.lower()
    assert "leading lines" in result.reply.lower()
    assert "visual hierarchy" in result.reply.lower()
    assert "dashboard" in result.reply.lower()
    assert "attention" in result.reply.lower()
    assert "provisional, source-bound application" in result.reply.lower()
    assert application["source_claim_version_id"] == revised_claim_version_id
    assert application["prior_claim_version_id"] == SOURCE_CLAIM_VERSION_ID
    assert application["source_lineage_ids"] == (SOURCE_CLAIM_VERSION_ID, revised_claim_version_id)
    assert application["status"] == "provisional_application_recorded"
    assert experience.source_class == "runtime_observation"
    assert experience.authority_class == "deterministic_source_bound_semantic_application"
    assert experience.metadata["record_kind"] == "source_bound_semantic_transfer_application"
    assert tuple(experience.metadata["source_claim_version_ids"]) == (revised_claim_version_id,)
    assert tuple(experience.metadata["source_lineage_ids"]) == (SOURCE_CLAIM_VERSION_ID, revised_claim_version_id)
    assert original.exact_text == "Connections is a generic introductory photography idea."
    assert revision.supersedes_version_id == SOURCE_CLAIM_VERSION_ID
    assert len(graph.claim_versions) == len(before.claim_versions)
    assert len(graph.experiences) == len(before.experiences) + 1
    assert not graph.packets
    assert not graph.reviews
    assert not graph.admissions
    assert not result.state.pending_chat_requests

    repeated = handle_conversational_message(
        result.state,
        TRANSFER_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    repeated_graph = load_graph(tmp_path)
    assert len(repeated.state.active_objective.provenance["semantic_transfer_applications"]) == 1
    assert len(repeated_graph.experiences) == len(graph.experiences)
    assert len(repeated_graph.claim_versions) == len(graph.claim_versions)
    assert sum(
        1
        for event in repeated.state.objective_progress
        if event.get("event") == "semantic_transfer_application_recorded"
    ) == 1

    restored = start_or_restore_runtime(tmp_path)
    after_restart = handle_conversational_message(
        restored,
        TRANSFER_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    restart_graph = load_graph(tmp_path)
    restarted_application = after_restart.state.active_objective.provenance["semantic_transfer_applications"][0]
    assert restarted_application["application_record_id"] == application["application_record_id"]
    assert restarted_application["graph_experience_id"] == application["graph_experience_id"]
    assert len(restart_graph.experiences) == len(graph.experiences)
    assert len(restart_graph.claim_versions) == len(graph.claim_versions)
    assert not restart_graph.packets
    assert not restart_graph.reviews
    assert not restart_graph.admissions


def test_unbound_dashboard_question_remains_ordinary_chat_without_transfer_trace(tmp_path):
    corrected = _corrected_state(tmp_path)
    graph_before = load_graph(tmp_path)
    prompt = "What should a dashboard show?"

    assert not is_source_bound_semantic_transfer_message(corrected, prompt)
    result = handle_conversational_message(
        corrected,
        prompt,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    graph_after = load_graph(tmp_path)

    assert result.intent.intent_type == "ordinary_conversation"
    assert "semantic_transfer_applications" not in result.state.active_objective.provenance
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not result.state.pending_chat_requests


def test_source_bound_transfer_compiles_one_multistep_dashboard_analysis_and_restart_is_idempotent(tmp_path):
    transferred = _transferred_state(tmp_path)
    source_application = transferred.active_objective.provenance["semantic_transfer_applications"][0]
    graph_before = load_graph(tmp_path)

    assert is_source_bound_semantic_analysis_message(transferred, ANALYSIS_PROMPT)
    result = handle_conversational_message(
        transferred,
        ANALYSIS_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    task = result.state.active_objective.provenance["semantic_analytical_tasks"][0]
    graph = load_graph(tmp_path)
    step_ids = tuple(item["step_id"] for item in task["substeps"])
    synthesis = task["final_synthesis"].lower()

    assert result.intent.intent_type == "semantic_multistep_analytical_task"
    assert task["record_kind"] == "source_bound_semantic_multistep_analysis"
    assert task["status"] == "provisional_analysis_recorded"
    assert task["source_semantic_ids"] == (SOURCE_CLAIM_VERSION_ID, source_application["source_claim_version_id"])
    assert task["source_transfer_application_id"] == source_application["application_record_id"]
    assert task["source_transfer_experience_id"] == source_application["graph_experience_id"]
    assert step_ids == (
        "identify_user_goal",
        "identify_information_priorities",
        "apply_revised_semantic_source",
        "propose_layout",
        "state_uncertainty_and_next_test",
    )
    assert all(item["status"] == "completed" for item in task["substeps"])
    assert "overdue invoices" in synthesis
    assert "financial or commitment risk" in synthesis
    assert "today's jobs" in synthesis
    assert "schedule or execution focus" in synthesis
    assert "urgent client messages" in synthesis
    assert "interruption or escalation" in synthesis
    assert "composition" in synthesis
    assert "leading lines" in synthesis
    assert "visual hierarchy" in synthesis
    assert "limitation" in synthesis
    assert len(graph.experiences) == len(graph_before.experiences)
    assert len(graph.claim_versions) == len(graph_before.claim_versions)
    assert not graph.packets
    assert not graph.reviews
    assert not graph.admissions
    assert not result.state.pending_chat_requests

    repeated = handle_conversational_message(
        result.state,
        ANALYSIS_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    repeated_graph = load_graph(tmp_path)
    assert len(repeated.state.active_objective.provenance["semantic_analytical_tasks"]) == 1
    assert len(repeated_graph.experiences) == len(graph.experiences)
    assert sum(
        1
        for event in repeated.state.objective_progress
        if event.get("event") == "semantic_multistep_analytical_task_recorded"
    ) == 1

    ordinary = handle_conversational_message(
        repeated.state,
        "What is 2 + 2?",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert len(ordinary.state.active_objective.provenance["semantic_analytical_tasks"]) == 1

    restored = start_or_restore_runtime(tmp_path)
    after_restart = handle_conversational_message(
        restored,
        ANALYSIS_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    restarted_task = after_restart.state.active_objective.provenance["semantic_analytical_tasks"][0]
    restart_graph = load_graph(tmp_path)
    assert restarted_task["analytical_task_id"] == task["analytical_task_id"]
    assert restarted_task["source_transfer_application_id"] == task["source_transfer_application_id"]
    assert len(after_restart.state.active_objective.provenance["semantic_analytical_tasks"]) == 1
    assert len(restart_graph.experiences) == len(graph.experiences)
    assert len(restart_graph.claim_versions) == len(graph.claim_versions)


def test_source_bound_analysis_records_task_local_competence_delta_and_restart_is_idempotent(tmp_path):
    analyzed = _analyzed_state(tmp_path)
    task = analyzed.active_objective.provenance["semantic_analytical_tasks"][0]
    graph_before = load_graph(tmp_path)

    assert is_source_bound_semantic_competence_measurement_message(analyzed, COMPETENCE_PROMPT)
    result = handle_conversational_message(
        analyzed,
        COMPETENCE_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    delta = result.state.active_objective.provenance["semantic_competence_deltas"][0]
    graph = load_graph(tmp_path)
    dimensions = {item["dimension_id"]: item for item in delta["measured_dimensions"]}

    assert result.intent.intent_type == "semantic_competence_delta_measurement"
    assert delta["record_kind"] == "source_bound_task_local_competence_delta"
    assert delta["competence_probe_id"] == delta["competence_delta_id"]
    assert delta["task_family"] == "source_bound_multistep_analysis"
    assert delta["baseline_result_id"] != delta["improved_result_id"]
    assert delta["improved_result_id"] == task["analytical_task_id"]
    assert delta["baseline_result"]["source_semantic_ids"] == ()
    assert "not an independently generated model answer" in delta["baseline_result"]["summary"].lower()
    assert delta["source_semantic_ids"] == task["source_semantic_ids"]
    assert delta["source_transfer_application_id"] == task["source_transfer_application_id"]
    assert delta["source_analytical_task_id"] == task["analytical_task_id"]
    assert dimensions["uses_source_semantic_lineage"]["baseline"] == "absent"
    assert dimensions["uses_source_semantic_lineage"]["improved"] == "present"
    assert dimensions["distinguishes_information_priority"]["improved"] == "present"
    assert dimensions["uses_visual_hierarchy"]["improved"] == "present"
    assert dimensions["maps_work_items_to_distinct_attention_roles"]["improved"] == "present"
    assert dimensions["states_uncertainty_or_next_test"]["improved"] == "present"
    assert len(delta["observed_delta"]) == len(delta["measured_dimensions"])
    assert delta["status"] == "task_local_observed_delta_recorded"
    assert "not a global competence score" in delta["limitations"].lower()
    assert "1.0" not in str(delta)
    assert not {"score", "metric", "candidate_metric", "global_intelligence_score"} & set(delta)
    assert "observed record differences" in result.reply.lower()
    assert len(graph.experiences) == len(graph_before.experiences)
    assert len(graph.claim_versions) == len(graph_before.claim_versions)
    assert not graph.packets
    assert not graph.reviews
    assert not graph.admissions
    assert not result.state.pending_chat_requests

    repeated = handle_conversational_message(
        result.state,
        COMPETENCE_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    repeated_graph = load_graph(tmp_path)
    assert len(repeated.state.active_objective.provenance["semantic_competence_deltas"]) == 1
    assert repeated.state.active_objective.provenance["semantic_competence_deltas"][0]["competence_delta_id"] == delta["competence_delta_id"]
    assert sum(
        1
        for event in repeated.state.objective_progress
        if event.get("event") == "semantic_competence_delta_recorded"
    ) == 1
    assert len(repeated_graph.experiences) == len(graph.experiences)
    assert len(repeated_graph.claim_versions) == len(graph.claim_versions)

    ordinary = handle_conversational_message(
        repeated.state,
        "What is 2 + 2?",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert len(ordinary.state.active_objective.provenance["semantic_competence_deltas"]) == 1

    restored = start_or_restore_runtime(tmp_path)
    after_restart = handle_conversational_message(
        restored,
        COMPETENCE_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    restarted_delta = after_restart.state.active_objective.provenance["semantic_competence_deltas"][0]
    restart_graph = load_graph(tmp_path)
    assert restarted_delta["competence_delta_id"] == delta["competence_delta_id"]
    assert restarted_delta["source_analytical_task_id"] == task["analytical_task_id"]
    assert len(after_restart.state.active_objective.provenance["semantic_competence_deltas"]) == 1
    assert len(restart_graph.experiences) == len(graph.experiences)
    assert len(restart_graph.claim_versions) == len(graph.claim_versions)
    assert not restart_graph.packets
    assert not restart_graph.reviews
    assert not restart_graph.admissions


def test_source_bound_semantic_recall_explains_application_delta_and_chain_without_side_effects(tmp_path):
    measured = _measured_state(tmp_path)
    objective = measured.active_objective
    assert objective is not None
    task = objective.provenance["semantic_analytical_tasks"][0]
    delta = objective.provenance["semantic_competence_deltas"][0]
    graph_before = load_graph(tmp_path)
    provenance_before = dict(objective.provenance)

    assert is_source_bound_semantic_recall_message(measured, EFFECT_RECALL_PROMPT)
    effect = handle_conversational_message(
        measured,
        EFFECT_RECALL_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert effect.intent.intent_type == "semantic_source_bound_recall"
    assert "revised connections record affected the dashboard analysis" in effect.reply.lower()
    assert "composition" in effect.reply.lower()
    assert "leading lines" in effect.reply.lower()
    assert "visual hierarchy" in effect.reply.lower()
    assert "financial or commitment risk" in effect.reply.lower()
    assert "provisional" in effect.reply.lower()

    assert is_source_bound_semantic_recall_message(effect.state, DELTA_RECALL_PROMPT)
    comparison = handle_conversational_message(
        effect.state,
        DELTA_RECALL_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert comparison.intent.intent_type == "semantic_source_bound_recall"
    assert "baseline-to-improved comparison is task-local" in comparison.reply.lower()
    assert "uses source semantic lineage" in comparison.reply.lower()
    assert "not a global competence claim" in comparison.reply.lower()

    assert is_source_bound_semantic_recall_message(comparison.state, CHAIN_RECALL_PROMPT)
    chain = handle_conversational_message(
        comparison.state,
        CHAIN_RECALL_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    graph_after = load_graph(tmp_path)
    assert chain.intent.intent_type == "semantic_source_bound_recall"
    assert "recorded applied-semantic chain" in chain.reply.lower()
    assert "revised: connections" in chain.reply.lower()
    assert "transferred:" in chain.reply.lower()
    assert "analyzed:" in chain.reply.lower()
    assert "measured:" in chain.reply.lower()
    assert chain.state.active_objective.provenance["semantic_transfer_applications"] == provenance_before["semantic_transfer_applications"]
    assert chain.state.active_objective.provenance["semantic_analytical_tasks"] == provenance_before["semantic_analytical_tasks"]
    assert chain.state.active_objective.provenance["semantic_competence_deltas"] == provenance_before["semantic_competence_deltas"]
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions
    assert not chain.state.pending_chat_requests

    ordinary = handle_conversational_message(
        chain.state,
        "What is 2 + 2?",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert ordinary.intent.intent_type == "ordinary_conversation"

    restored = start_or_restore_runtime(tmp_path)
    after_restart = handle_conversational_message(
        restored,
        CHAIN_RECALL_PROMPT,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    restart_graph = load_graph(tmp_path)
    assert after_restart.intent.intent_type == "semantic_source_bound_recall"
    assert after_restart.state.active_objective.provenance["semantic_analytical_tasks"][0]["analytical_task_id"] == task["analytical_task_id"]
    assert after_restart.state.active_objective.provenance["semantic_competence_deltas"][0]["competence_delta_id"] == delta["competence_delta_id"]
    assert len(after_restart.state.active_objective.provenance["semantic_transfer_applications"]) == 1
    assert len(after_restart.state.active_objective.provenance["semantic_analytical_tasks"]) == 1
    assert len(after_restart.state.active_objective.provenance["semantic_competence_deltas"]) == 1
    assert len(restart_graph.experiences) == len(graph_before.experiences)
    assert len(restart_graph.claim_versions) == len(graph_before.claim_versions)
    assert not restart_graph.packets
    assert not restart_graph.reviews
    assert not restart_graph.admissions


def test_unbound_competence_comparison_remains_ordinary_chat_without_delta_trace(tmp_path):
    corrected = _corrected_state(tmp_path)
    graph_before = load_graph(tmp_path)
    prompt = "Compare a baseline dashboard analysis with an improved dashboard analysis."

    assert not is_source_bound_semantic_competence_measurement_message(corrected, prompt)
    result = handle_conversational_message(
        corrected,
        prompt,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    graph_after = load_graph(tmp_path)

    assert result.intent.intent_type == "ordinary_conversation"
    assert "semantic_competence_deltas" not in result.state.active_objective.provenance
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not result.state.pending_chat_requests
