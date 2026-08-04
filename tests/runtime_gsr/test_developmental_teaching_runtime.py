from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    classify_conversational_intent,
    compile_conversational_objective,
    handle_conversational_message,
    run_background_objective_cycle,
    save_runtime_state,
    start_or_restore_runtime,
)
from dataclasses import replace
from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel
from orchestration.runtime.developmental_teaching_runtime import (
    compile_endogenous_terminal_gap_followup,
    compile_teaching_plan,
    derive_teaching_pressures,
    is_teaching_instruction,
    load_teaching_controller,
    save_teaching_controller,
    start_teaching_controller,
    teaching_snapshot,
    update_teaching_state,
)
from orchestration.runtime.interactive_cognition import arbitrate_attention, build_workspace_snapshot
from orchestration.runtime.epistemic_answer_mode import bind_teaching_followup_question
from orchestration.runtime.provisional_semantic_consolidation import (
    ClaimVersion,
    ProvisionalSemanticGraphState,
    create_consolidation_cohort,
    load_graph,
)


NEUROANATOMY = "Today I want you to teach me basic neuroanatomy."
PHYSICS = "Teach me physics."


def test_explicit_teaching_phrases_are_goals_but_ordinary_questions_are_not():
    for message in (
        "Teach me neuroanatomy.",
        "Help me learn physics.",
        "Walk me through calculus.",
        "Today I want to learn neuroanatomy.",
        NEUROANATOMY,
    ):
        assert is_teaching_instruction(message) is True
        intent = classify_conversational_intent(message)
        assert intent.intent_type == "persistent_or_session_goal"
        assert intent.matched_signals == ("explicit_teaching_intent",)

    for message in ("What is 2 + 2?", "What does the amygdala do?", "How are you?"):
        assert is_teaching_instruction(message) is False
        assert classify_conversational_intent(message).intent_type == "ordinary_conversation"


def test_teaching_goal_reuses_knowledge_execution_and_renders_first_lesson(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    intent = classify_conversational_intent(NEUROANATOMY)
    objective = compile_conversational_objective(NEUROANATOMY, intent)

    result = handle_conversational_message(
        state,
        NEUROANATOMY,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    assert objective.provenance["execution_mode"] == "knowledge_acquisition"
    assert objective.provenance["teaching_plan"]["domain"] == "neuroscience"
    assert len(objective.provenance["knowledge_contract"]["material_requirements"]) == 6
    assert result.objective_created is True
    assert result.state.active_objective.objective_id == objective.objective_id
    assert "Let's begin with basic neuroanatomy." in result.reply
    assert "central nervous system" in result.reply.lower()
    assert not result.state.pending_chat_requests
    assert [turn.role for turn in result.state.conversation] == ["user", "assistant"]

    repeated = handle_conversational_message(
        result.state,
        NEUROANATOMY,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert repeated.objective_created is False
    assert repeated.state.active_objective.objective_id == objective.objective_id


def test_teaching_controller_persists_existing_controller_restart_export(tmp_path):
    plan = compile_teaching_plan(NEUROANATOMY)
    controller = start_teaching_controller(
        runtime_id="runtime-teaching-test",
        objective_id="objective-teaching-test",
        plan=plan,
    )
    updated = update_teaching_state(
        controller,
        teaching_cursor=2,
        stage="provisional_learning_pending_consolidation",
        retention_records=("claim-version-1",),
    )

    path = save_teaching_controller(tmp_path, updated, objective_id="objective-teaching-test")
    restored = load_teaching_controller(
        tmp_path,
        runtime_id="runtime-teaching-test",
        objective_id="objective-teaching-test",
    )

    assert path.parent == tmp_path / "developmental-teaching"
    assert restored is not None
    snapshot = teaching_snapshot(restored)
    assert snapshot["objective_id"] == "objective-teaching-test"
    assert snapshot["teaching_cursor"] == 2
    assert snapshot["stage"] == "provisional_learning_pending_consolidation"
    assert snapshot["retention_records"] == ("claim-version-1",)
    assert snapshot["plan"]["plan_id"] == plan["plan_id"]


def test_teaching_controller_is_read_only_attention_projection(tmp_path):
    state = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        NEUROANATOMY,
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state
    plan = state.active_objective.provenance["teaching_plan"]
    controller = start_teaching_controller(
        runtime_id=state.runtime_id,
        objective_id=state.active_objective.objective_id,
        plan=plan,
    )
    before = state.as_record()

    snapshot = build_workspace_snapshot(state, developmental_controller=teaching_snapshot(controller))
    thread = next(item for item in snapshot.threads if item.thread_kind == "developmental_objective")
    decision = arbitrate_attention(snapshot)

    assert state.as_record() == before
    assert thread.canonical_owner == "continuous_runtime_controller"
    assert thread.source_record_ids == (controller.controller_id, state.active_objective.objective_id)
    assert thread.inclusion_reason == "canonical_developmental_controller_projection"
    assert decision.selected_posture == "continue_active_goal"


def test_consolidation_pressure_waits_for_provisional_retention_decision():
    """Idle attention must not overtake the visible memory-approval boundary."""

    plan = compile_teaching_plan(NEUROANATOMY)
    pending = {
        "followup_id": "followup-amygdala",
        "claim_version_id": "claim-version-amygdala",
        "status": "provisional_ready_for_retention",
    }
    assert not derive_teaching_pressures(plan, followups=(pending,))

    retained = {**pending, "status": "retained_provisional"}
    pressures = derive_teaching_pressures(plan, followups=(retained,))
    assert len(pressures) == 1
    assert pressures[0]["pressure_type"] == "epistemic_debt"
    assert pressures[0]["recommended_action"] == "continue_consolidation_boundary"


def test_partial_terminal_gap_projects_one_source_bound_recovery_pressure():
    plan = compile_teaching_plan("Teach me introductory photography.")
    report = {
        "event": "knowledge_goal_terminal_report",
        "objective_id": "photography-objective",
        "status": "partially_completed",
        "stop_reason": "blocked_insufficient_evidence",
        "remaining_gaps": ("address Connections",),
        "at": "2026-08-04T01:22:51+00:00",
    }

    recovery = compile_endogenous_terminal_gap_followup(
        plan,
        objective_id="photography-objective",
        terminal_report=report,
    )
    pressures = derive_teaching_pressures(plan, terminal_reports=(report,))

    assert recovery["origin"] == "endogenous_terminal_gap_recovery"
    assert recovery["source_gap"] == "address Connections"
    assert recovery["lesson_title"] == "Connections"
    assert "introductory photography" in recovery["question"]
    assert len(pressures) == 1
    assert pressures[0]["pressure_type"] == "unresolved_curriculum_gap"
    assert pressures[0]["recommended_action"] == "perform_one_gap_recovery_study"
    assert pressures[0]["source_terminal_report_key"] == recovery["source_terminal_report_key"]
    assert not derive_teaching_pressures(plan, followups=(recovery,), terminal_reports=(report,))


def test_completed_or_gapless_terminal_reports_do_not_create_recovery_pressure():
    plan = compile_teaching_plan("Teach me introductory photography.")

    assert not derive_teaching_pressures(
        plan,
        terminal_reports=(
            {"objective_id": "photography-objective", "status": "completed", "remaining_gaps": ("address Connections",)},
            {"objective_id": "photography-objective", "status": "partially_completed", "remaining_gaps": ()},
        ),
    )


def test_physics_plan_preserves_qualitative_branch_and_calculus_prerequisite():
    plan = compile_teaching_plan(PHYSICS)
    objective = compile_conversational_objective(PHYSICS, classify_conversational_intent(PHYSICS))

    assert plan["domain"] == "physics"
    assert plan["curriculum"][0]["title"] == "Qualitative mechanics"
    assert plan["prerequisites"] == (
        {
            "topic": "introductory calculus",
            "needed_for": "mathematical mechanics and derivations",
            "safe_parallel_branch": "qualitative mechanics",
        },
    )
    assert objective.provenance["execution_mode"] == "knowledge_acquisition"


def _amygdala_runner(request, packet):
    response = dict(ScriptedSemanticModel()(request, packet))
    node = dict(packet.active_focus.get("active_frontier_node") or {})
    if "amygdala" in str(node.get("label") or "").lower():
        statement = (
            "The amygdala helps assign emotional salience to sensory information and supports threat-related learning "
            "because it coordinates signals with memory and autonomic response systems."
        )
        response.update(
            {
                "interpretation": statement,
                "hypothesis_statement": statement,
                "scope": str(node.get("label") or "What does the amygdala do?"),
                "raw_model_output": statement,
            }
        )
    return response


def test_teaching_followup_uses_existing_frontier_graph_and_retention_request(tmp_path):
    state = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        "Teach me neuroanatomy.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state

    studied = handle_conversational_message(
        state,
        "What does the amygdala do?",
        runtime_root=tmp_path,
        run_background_cycle=True,
        model_runner=_amygdala_runner,
    )
    followup = studied.state.active_objective.provenance["teaching_followups"][0]
    request = studied.state.pending_chat_requests[0]
    graph = load_graph(tmp_path)

    assert studied.intent.intent_type == "teaching_followup_question"
    assert studied.background_cycle_started is True
    assert followup["status"] == "provisional_ready_for_retention"
    assert followup["claim_version_id"]
    assert "emotional salience" in followup["interpretation"]
    assert followup["understanding_assessment"]["factual_status"] == "still_provisional_pending_consolidation"
    assert request.request_type == "teaching_provisional_retention"
    assert request.baseline_metrics["claim_version_id"] == followup["claim_version_id"]
    assert len(graph.claim_versions) == 1
    assert graph.claim_versions[0].epistemic_state == "pending_consolidation"
    assert len(graph.cohorts) == 1

    retained = handle_conversational_message(
        studied.state,
        "Yes.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    retained_followup = retained.state.active_objective.provenance["teaching_followups"][0]
    rebound_graph = load_graph(tmp_path)

    assert retained_followup["status"] == "retained_provisional"
    assert not retained.state.pending_chat_requests
    assert retained.state.resolved_chat_requests[-1].resolution_policy == "operator_approved_provisional_retention"
    assert "provisional material" in retained.reply
    assert bind_teaching_followup_question(
        "What does the amygdala do?",
        rebound_graph,
        retained.state.active_objective.provenance["teaching_followups"],
    ) == (followup["claim_version_id"],)

    repeated = handle_conversational_message(
        retained.state,
        "What does the amygdala do?",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert repeated.intent.intent_type == "ordinary_conversation"
    assert len(repeated.state.active_objective.provenance["teaching_followups"]) == 1


def test_teaching_followup_preserves_existing_frontier_retry_before_retention(tmp_path):
    attempts = {"amygdala": 0}

    def retrying_runner(request, packet):
        response = dict(ScriptedSemanticModel()(request, packet))
        node = dict(packet.active_focus.get("active_frontier_node") or {})
        if "amygdala" not in str(node.get("label") or "").lower():
            return response
        attempts["amygdala"] += 1
        statement = (
            "The amygdala processes emotional information and contributes to fear conditioning."
            if attempts["amygdala"] == 1
            else "The amygdala assigns emotional salience to sensory cues because it links their appraisal with memory and autonomic response systems, which supports threat-related learning."
        )
        return {
            **response,
            "interpretation": statement,
            "hypothesis_statement": statement,
            "scope": str(node.get("label") or "What does the amygdala do?"),
            "raw_model_output": statement,
        }

    created = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        "Teach me neuroanatomy.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    first = handle_conversational_message(
        created.state,
        "What does the amygdala do?",
        runtime_root=tmp_path,
        run_background_cycle=True,
        model_runner=retrying_runner,
    )
    first_followup = first.state.active_objective.provenance["teaching_followups"][0]

    assert first_followup["status"] == "study_retry_scheduled"
    assert first_followup["retry_count"] == 1
    assert first_followup["last_rejection_reasons"] == ("node_completion_missing_explanatory_relation",)
    assert not first.state.pending_chat_requests
    assert not any(item.get("event") == "teaching_followup_study_blocked" for item in first.state.objective_progress)

    second = run_background_objective_cycle(
        first.state,
        runtime_root=tmp_path,
        reason="teaching-followup-retry-proof",
        model_runner=retrying_runner,
    )
    second_followup = second.active_objective.provenance["teaching_followups"][0]

    assert attempts["amygdala"] == 2
    assert second_followup["status"] == "provisional_ready_for_retention"
    assert second_followup["retry_count"] == 1
    assert second_followup["claim_version_id"]
    assert any(item.request_type == "teaching_provisional_retention" for item in second.pending_chat_requests)
    assert sum(item.get("event") == "teaching_followup_study_retry_scheduled" for item in second.objective_progress) == 1


def test_teaching_followup_blocks_only_after_its_second_rejection(tmp_path):
    def always_incomplete_runner(request, packet):
        response = dict(ScriptedSemanticModel()(request, packet))
        node = dict(packet.active_focus.get("active_frontier_node") or {})
        if "amygdala" in str(node.get("label") or "").lower():
            statement = "The amygdala processes emotional information and contributes to fear conditioning."
            response.update({
                "interpretation": statement,
                "hypothesis_statement": statement,
                "scope": str(node.get("label") or "What does the amygdala do?"),
                "raw_model_output": statement,
            })
        return response

    created = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        "Teach me neuroanatomy.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    first = handle_conversational_message(
        created.state,
        "What does the amygdala do?",
        runtime_root=tmp_path,
        run_background_cycle=True,
        model_runner=always_incomplete_runner,
    )
    second = run_background_objective_cycle(
        first.state,
        runtime_root=tmp_path,
        reason="teaching-followup-terminal-rejection-proof",
        model_runner=always_incomplete_runner,
    )
    followup = second.active_objective.provenance["teaching_followups"][0]

    assert followup["status"] == "study_blocked"
    assert followup["retry_count"] == 2
    assert not second.pending_chat_requests
    assert sum(item.get("event") == "teaching_followup_study_retry_scheduled" for item in second.objective_progress) == 1
    assert sum(item.get("event") == "teaching_followup_study_blocked" for item in second.objective_progress) == 1


def test_physics_prerequisite_request_keeps_parent_active_and_starts_linked_branch(tmp_path):
    created = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        PHYSICS,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    request = created.state.pending_chat_requests[0]

    assert request.request_type == "teaching_prerequisite"
    assert "qualitative mechanics" in created.reply
    assert "introductory calculus" in request.prompt_text

    resolved = handle_conversational_message(
        created.state,
        "Yes.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    prerequisite = resolved.state.active_objective.provenance["teaching_prerequisites"][0]

    assert resolved.background_cycle_started is True
    assert resolved.state.active_objective.objective_id == created.state.active_objective.objective_id
    assert prerequisite["status"] == "queued"
    assert prerequisite["prerequisite_objective_id"]
    assert prerequisite["parent_objective_id"] == created.state.active_objective.objective_id


def test_physics_prerequisite_runs_one_linked_competence_check_without_replacing_parent(tmp_path):
    def physics_runner(request, packet):
        response = dict(ScriptedSemanticModel()(request, packet))
        node = dict(packet.active_focus.get("active_frontier_node") or {})
        label = str(node.get("label") or "")
        if "introductory calculus" in label.lower():
            statement = (
                "Introductory calculus uses derivatives to describe rates of change and integrals to accumulate change, "
                "because mathematical mechanics needs those tools to express changing motion."
            )
        else:
            statement = (
                f"{label} can be explained through one concrete relation because that relation connects the topic to a bounded next learning step."
            )
        response.update({
            "interpretation": statement,
            "hypothesis_statement": statement,
            "scope": label,
            "raw_model_output": statement,
        })
        return response

    created = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        PHYSICS,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    approved = handle_conversational_message(
        created.state,
        "Yes.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    parent_id = approved.state.active_objective.objective_id
    state = approved.state
    for cycle in range(1, 8):
        state = run_background_objective_cycle(
            state,
            runtime_root=tmp_path,
            reason=f"physics-prerequisite-proof-{cycle}",
            model_runner=physics_runner,
        )
        prerequisite = state.active_objective.provenance["teaching_prerequisites"][0]
        if prerequisite["status"] != "queued":
            break

    prerequisite = state.active_objective.provenance["teaching_prerequisites"][0]
    assert state.active_objective.objective_id == parent_id
    assert prerequisite["status"] == "competence_tested"
    assert prerequisite["competence_test_state"] == "tested_source_bound_explanation"
    assert prerequisite["derivation_branch_state"] == "resumed"
    assert prerequisite["parent_branch_resume_cursor"] == 3
    assert prerequisite["parent_branch_resume_lesson_title"] == "Mathematical mechanics"
    assert prerequisite["parent_branch_resume_event_id"]
    assert prerequisite["understanding_assessment"]["learning_states"]["tested"] is True
    assert sum(item.get("event") == "teaching_prerequisite_cleared" for item in state.objective_progress) == 1
    assert sum(item.get("event") == "teaching_parent_branch_resumed" for item in state.objective_progress) == 1

    save_runtime_state(tmp_path, state)
    restored = start_or_restore_runtime(tmp_path)
    restored_prerequisite = restored.active_objective.provenance["teaching_prerequisites"][0]
    assert restored.active_objective.objective_id == parent_id
    assert restored_prerequisite["prerequisite_id"] == prerequisite["prerequisite_id"]
    assert restored_prerequisite["derivation_branch_state"] == "resumed"
    assert restored_prerequisite["parent_branch_resume_event_id"] == prerequisite["parent_branch_resume_event_id"]


def test_physics_prerequisite_retries_missing_observable_before_competence_passes(tmp_path):
    """The prerequisite uses the normal frontier retry, not a second local-model path."""

    def physics_runner(request, packet):
        response = dict(ScriptedSemanticModel()(request, packet))
        node = dict(packet.active_focus.get("active_frontier_node") or {})
        label = str(node.get("label") or "")
        retry_attempt = int(packet.active_focus.get("retry_attempt") or 0)
        if "introductory calculus" in label.lower():
            statement = (
                "A derivative represents rate of change and an integral represents accumulation because mechanics "
                "uses them to connect changing velocity with displacement."
            )
            response.update({
                "interpretation": statement,
                "hypothesis_statement": statement,
                "scope": label,
                "raw_model_output": statement,
                "expected_observations": (
                    [] if retry_attempt == 0 else ["Acceleration is the derivative of velocity in a motion example."]
                ),
            })
        return response

    created = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        PHYSICS,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    state = handle_conversational_message(
        created.state,
        "Yes.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state

    for cycle in range(1, 16):
        state = run_background_objective_cycle(
            state,
            runtime_root=tmp_path,
            reason=f"physics-prerequisite-retry-{cycle}",
            model_runner=physics_runner,
        )
        prerequisite = state.active_objective.provenance["teaching_prerequisites"][0]
        if prerequisite["status"] == "competence_tested":
            break

    prerequisite = state.active_objective.provenance["teaching_prerequisites"][0]
    assert prerequisite["status"] == "competence_tested"
    assert prerequisite["retry_count"] == 1
    assert prerequisite["understanding_assessment"]["observable_application"] is True
    assert sum(item.get("event") == "teaching_prerequisite_retry_scheduled" for item in state.objective_progress) == 1
    assert sum(item.get("event") == "teaching_prerequisite_competence_checked" for item in state.objective_progress) == 1


def test_teaching_review_authority_uses_one_durable_request_without_external_review(tmp_path):
    created = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        NEUROANATOMY,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    objective = replace(
        created.state.active_objective,
        provenance={
            **created.state.active_objective.provenance,
            "teaching_consolidation_records": (
                {
                    "packet_id": "packet-teaching-review",
                    "cohort_id": "cohort-teaching-review",
                    "claim_version_ids": ("claim-version-teaching-review",),
                    "review_authorization_status": "awaiting_operator_confirmation",
                },
            ),
        },
    )
    request = ChatAddressableRequest(
        request_id="teaching-review-authority-request",
        request_type="teaching_consolidation_review_authority",
        objective_id=objective.objective_id,
        goal_label="basic neuroanatomy provisional review",
        prompt_text="May I prepare this bounded packet for governed review?",
        authority_impact="external_consolidation_review_requires_conversational_confirmation",
        accepted_response_types=("approved", "denied"),
        baseline_metrics={"packet_id": "packet-teaching-review"},
    )
    pending = replace(created.state, active_objective=objective, pending_chat_requests=(request,))

    resolved = handle_conversational_message(
        pending,
        "Yes.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    record = resolved.state.active_objective.provenance["teaching_consolidation_records"][0]
    assert resolved.state.resolved_chat_requests[-1].request_id == request.request_id
    assert resolved.state.resolved_chat_requests[-1].consumption_count == 1
    assert resolved.state.resolved_chat_requests[-1].resolution_policy == "operator_authorized_consolidation_review_preparation"
    assert record["review_authorization_status"] == "authorized_pending_external_review"
    assert record["review_status"] == "pending_external_review"
    assert record["review_authority_granted"] is True
    assert record["external_review_result_id"] == ""
    assert record["admission_id"] == ""
    assert "No external review has run yet" in resolved.reply

    save_runtime_state(tmp_path, resolved.state)
    restored = start_or_restore_runtime(tmp_path)
    restored_record = restored.active_objective.provenance["teaching_consolidation_records"][0]
    pressures = derive_teaching_pressures(
        restored.active_objective.provenance["teaching_plan"],
        consolidation_records=(restored_record,),
    )

    assert restored_record["review_status"] == "pending_external_review"
    assert not restored.pending_chat_requests
    assert restored.resolved_chat_requests[-1].request_id == request.request_id
    assert pressures == (
        {
            "pressure_type": "external_review_pending",
            "source_record_id": "packet-teaching-review",
            "reason": "A sealed teaching packet is awaiting the separately governed external review boundary.",
            "recommended_action": "await_external_review",
            "requires_operator": False,
            "priority": 0,
        },
    )


def test_existing_consolidation_cursor_is_reused_for_same_provisional_claim_set():
    graph = ProvisionalSemanticGraphState(
        graph_id="teaching-cohort-idempotence",
        claim_versions=(
            ClaimVersion(
                "claim-version-teaching-idempotence",
                "claim-teaching-idempotence",
                1,
                "A provisional teaching explanation remains pending review.",
                "pending_consolidation",
                (), (), (), (), "sha256:teaching-idempotence", "2026-08-03T00:00:00+00:00",
            ),
        ),
    )
    graph, first = create_consolidation_cohort(graph, trigger="conversational_teaching_followup")
    replayed, second = create_consolidation_cohort(graph, trigger="conversational_teaching_followup")

    assert first.cohort_id == second.cohort_id
    assert replayed.as_record() == graph.as_record()
    assert len(replayed.cohorts) == 1
