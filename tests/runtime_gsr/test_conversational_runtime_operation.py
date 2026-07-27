from orchestration.runtime.conversational_runtime_operation import (
    apply_stop_or_redirect,
    chat_feature_settings_schema,
    classify_conversational_intent,
    decide_turn_relation,
    evaluate_conversational_runtime,
    handle_conversational_message,
    read_json,
    record_foreground_message_for_reconciliation,
    record_local_semantic_attempt,
    render_goal_review,
    request_provider_learning_packet,
    resolve_pending_chat_request,
    save_runtime_state,
    start_or_restore_runtime,
    stop_active_objective,
)


ENGLISH_GOAL = "Your goal today is to improve your English comprehension so we can communicate better."


def _with_local_insufficiency(state, tmp_path):
    updated, evaluation = record_local_semantic_attempt(
        state,
        runtime_root=tmp_path,
        target_gap="queued implied references across topic switches",
        local_model="qwen-test",
        local_prompt="Generate topic-switch counterexamples.",
        raw_response="One vague reference note only.",
    )
    assert evaluation["status"] == "locally_insufficient"
    return updated


def test_intent_classifier_distinguishes_chat_goal_correction_and_risk(tmp_path):
    state = start_or_restore_runtime(tmp_path)

    ordinary = classify_conversational_intent("How are you?")
    goal = classify_conversational_intent(ENGLISH_GOAL)
    risky = classify_conversational_intent("Modify your source code and push it.")
    created = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state
    correction = classify_conversational_intent(
        "No, that isn't what I meant.",
        active_objective=created.active_objective,
        recent_turns=created.conversation,
    )

    assert ordinary.intent_type == "ordinary_conversation"
    assert goal.intent_type == "persistent_or_session_goal"
    assert risky.intent_type == "authority_changing_or_risky_instruction"
    assert correction.intent_type == "direct_correction"
    assert "modify_source" in risky.authority_required
    assert "push" in risky.authority_required


def test_chat_feature_settings_schema_preserves_gpt_style_surface_and_authority():
    schema = chat_feature_settings_schema()

    assert schema["conversation"]["ordinary_chat_default"] is True
    assert schema["conversation"]["allow_natural_goals"] is True
    assert schema["interface"]["advanced_surface"] == "hidden_until_requested"
    assert schema["tools_and_actions"]["routine_local_cognition"] == "standing_bounded_authority"
    assert schema["tools_and_actions"]["tracked_source_mutation"] == "explicit_approval_required"


def test_natural_goal_compiles_objective_authority_and_starts_cycle(tmp_path):
    state = start_or_restore_runtime(tmp_path)

    result = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path)

    assert result.objective_created is True
    assert result.background_cycle_started is True
    assert result.state.active_objective is not None
    assert result.state.authority is not None
    assert result.state.active_objective.prohibited_actions == result.state.authority.prohibited_actions
    assert "tracked source mutation" in result.state.authority.prohibited_actions
    assert result.state.completed_cycle_keys
    assert "bounded session goal" in result.reply


def test_correction_creates_scoped_lesson_and_related_transfer_only(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path).state
    baseline = handle_conversational_message(
        state,
        "Explain this sentence.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    corrected = handle_conversational_message(
        baseline.state,
        "That was too verbose. Use shorter answers for this kind of explanation.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    related = handle_conversational_message(
        corrected.state,
        "Explain the style issue again.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    unrelated = handle_conversational_message(
        related.state,
        "What is angular momentum?",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    assert corrected.correction_attached is True
    assert corrected.state.corrections[0].target_turn_id
    assert corrected.state.accepted_lessons[0].authority_effect == "none"
    assert related.transfer_applied is True
    assert "Short version" in related.reply
    assert unrelated.transfer_applied is False


def test_question_about_meaning_is_not_a_correction_without_correction_signal(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state

    intent = classify_conversational_intent(
        "Explain what I mean by the thing before the current one.",
        active_objective=state.active_objective,
        recent_turns=state.conversation,
    )

    assert intent.intent_type == "ordinary_conversation"


def test_foreground_message_is_preserved_for_later_reconciliation(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state

    updated = record_foreground_message_for_reconciliation(
        state,
        "also compare that with how I use pronouns",
        runtime_root=tmp_path,
    )

    assert updated.conversation[-1].intent_type == "ordinary_conversation_queued"
    assert updated.conversation[-1].text == "also compare that with how I use pronouns"
    assert updated.objective_progress[-1]["event"] == "foreground_message_queued_for_reconciliation"


def test_stop_or_redirect_pauses_active_goal_without_source_authority(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state

    intent = classify_conversational_intent(
        "stop working on that and focus on topic switches instead",
        active_objective=state.active_objective,
        recent_turns=state.conversation,
    )
    updated = apply_stop_or_redirect(
        state,
        "stop working on that and focus on topic switches instead",
        runtime_root=tmp_path,
    )

    assert intent.intent_type == "stop_or_redirect"
    assert updated.lifecycle_state == "paused_operator"
    assert updated.objective_progress[-1]["event"] == "operator_stop_or_redirect"
    assert "tracked source mutation" in updated.active_objective.prohibited_actions


def test_risky_instruction_requests_authority_without_stopping_safe_goal(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path).state

    result = handle_conversational_message(
        state,
        "Use the internet and modify your source code.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    assert result.authority_request is not None
    assert result.state.active_objective is not None
    assert result.state.pending_material_authority
    assert result.state.pending_material_authority[0]["ordinary_work_can_continue"] is True
    assert "material authority boundary" in result.reply


def test_provider_request_is_chat_addressable_side_thread(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state

    blocked = request_provider_learning_packet(
        state,
        "Please request a provider learning packet for implied references.",
        runtime_root=tmp_path,
    )
    assert blocked.state.pending_chat_requests == ()
    assert "test local Qwen" in blocked.reply

    state = _with_local_insufficiency(blocked.state, tmp_path)
    result = request_provider_learning_packet(
        state,
        "Please request a provider learning packet for implied references.",
        runtime_root=tmp_path,
    )

    assert result.chat_request is not None
    assert result.state.pending_chat_requests[0].request_type == "provider_authority"
    assert result.state.pending_chat_requests[0].side_thread_effect == "does_not_replace_foreground_topic"
    assert "[Goal update · Language understanding]" in result.reply
    assert "Approve?" in result.reply


def test_natural_approval_binds_once_to_pending_provider_request(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state
    state = _with_local_insufficiency(state, tmp_path)
    state = request_provider_learning_packet(state, "Request a provider learning packet.", runtime_root=tmp_path).state

    approved = resolve_pending_chat_request(state, "Approve.", runtime_root=tmp_path)
    duplicate = resolve_pending_chat_request(approved.state, "Approve.", runtime_root=tmp_path)

    assert approved is not None
    assert approved.provider_authority is not None
    assert approved.provider_authority["max_calls"] == 1
    assert approved.provider_authority["status"] == "authorized_not_executed"
    assert len(approved.state.pending_chat_requests) == 0
    assert len(approved.state.resolved_chat_requests) == 1
    assert approved.state.resolved_chat_requests[0].consumption_count == 1
    assert duplicate is None
    assert len(approved.state.provider_authorities) == 1


def test_modified_provider_approval_preserves_budget_and_data_limits(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state
    state = _with_local_insufficiency(state, tmp_path)
    state = request_provider_learning_packet(state, "Request a provider learning packet.", runtime_root=tmp_path).state

    one_call = resolve_pending_chat_request(state, "Use only one call.", runtime_root=tmp_path)

    assert one_call.provider_authority["max_calls"] == 1
    assert one_call.provider_authority["max_spend_usd"] == 1.0
    assert one_call.state.resolved_chat_requests[0].resolution_policy == "modified_approval"

    state2 = start_or_restore_runtime(tmp_path / "synthetic")
    state2 = handle_conversational_message(state2, ENGLISH_GOAL, runtime_root=tmp_path / "synthetic", run_background_cycle=False).state
    state2 = _with_local_insufficiency(state2, tmp_path / "synthetic")
    state2 = request_provider_learning_packet(state2, "Request a provider learning packet.", runtime_root=tmp_path / "synthetic").state
    sanitized = resolve_pending_chat_request(state2, "Approve, but do not send my actual messages.", runtime_root=tmp_path / "synthetic")

    assert "actual operator messages" in sanitized.provider_authority["prohibited_data"]
    assert "sanitized operator-message summaries" not in sanitized.provider_authority["permitted_data"]


def test_denial_does_not_create_provider_authority(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state
    state = _with_local_insufficiency(state, tmp_path)
    state = request_provider_learning_packet(state, "Request a provider learning packet.", runtime_root=tmp_path).state

    denied = resolve_pending_chat_request(state, "No, continue locally.", runtime_root=tmp_path)

    assert denied.provider_authority is None
    assert denied.state.provider_authorities == ()
    assert denied.state.resolved_chat_requests[0].status == "denied"
    assert "continue the goal locally" in denied.reply


def test_unresolved_provider_request_survives_restart(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state
    state = _with_local_insufficiency(state, tmp_path)
    state = request_provider_learning_packet(state, "Request a provider learning packet.", runtime_root=tmp_path).state
    save_runtime_state(tmp_path, state)

    restored = start_or_restore_runtime(tmp_path)
    approved = resolve_pending_chat_request(restored, "Approve, but do not send my actual messages.", runtime_root=tmp_path)

    assert restored.pending_chat_requests[0].request_id == state.pending_chat_requests[0].request_id
    assert approved.provider_authority["request_id"] == state.pending_chat_requests[0].request_id
    assert len(approved.state.provider_authorities) == 1


def test_unrelated_factual_question_isolated_from_active_goal(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state
    state = handle_conversational_message(
        state,
        "No, when I say that thing from before, inspect the previous user message.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state

    result = handle_conversational_message(
        state,
        "What is angular momentum? Do not use my reference correction unless it actually matters.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    assert "rotational counterpart" in result.reply
    assert result.transfer_applied is False
    assert result.state.active_objective is not None
    decision = result.state.turn_relation_decisions[-1]
    assert decision.relation_class == "unrelated_foreground_topic"
    assert decision.lesson_ids_rejected
    assert "do not use" in decision.negative_instruction_tokens


def test_lesson_discussion_is_not_lesson_applicability(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state

    decision = decide_turn_relation(
        state,
        "Explain why the phrase previous message is ambiguous as a linguistic example.",
        turn_id="turn-test",
    )

    assert decision.foreground_topic == "linguistic_example_previous_message"
    assert decision.relation_class == "active_goal_related"
    assert decision.routing_decision != "foreground_answer_without_goal_lesson"


def test_completion_review_distinguishes_retained_lessons_from_authority(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path, run_background_cycle=False).state
    state = handle_conversational_message(
        state,
        "No, when I say that thing from before, inspect the previous user message.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state

    reviewed, text = render_goal_review(state, status="implementation_review_required")

    assert "[Goal review" in text
    assert "I retained:" in text
    assert "Provider use:" in text
    assert "implementation-review boundary" in text
    assert reviewed.goal_reviews


def test_restart_restores_without_duplicate_cycles_or_corrections(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path).state
    state = handle_conversational_message(
        state,
        "No, when I say communicate better here, I mean understand my corrections.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state
    save_runtime_state(tmp_path, state)

    restored = start_or_restore_runtime(tmp_path)

    assert restored.active_objective.objective_id == state.active_objective.objective_id
    assert restored.completed_cycle_keys == state.completed_cycle_keys
    assert restored.corrections[0].correction_id == state.corrections[0].correction_id
    assert len(restored.corrections) == 1
    assert read_json(tmp_path / "state.json")["active_objective"]["objective_id"] == state.active_objective.objective_id


def test_stop_active_objective_preserves_chat_runtime_without_new_authority(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path).state

    stopped = stop_active_objective(state)

    assert stopped.lifecycle_state == "stopped"
    assert stopped.active_objective.lifecycle_state == "stopped"
    assert stopped.authority.authority_effect == "routine_internal_only"


def test_evaluator_rejects_storage_only_and_accepts_correction_learning(tmp_path):
    empty = start_or_restore_runtime(tmp_path / "empty")
    assert evaluate_conversational_runtime(empty)["passed"] is False

    state = start_or_restore_runtime(tmp_path / "full")
    state = handle_conversational_message(state, ENGLISH_GOAL, runtime_root=tmp_path / "full").state
    state = handle_conversational_message(
        state,
        "No, that isn't what I meant. Interpret the local context first.",
        runtime_root=tmp_path / "full",
    ).state
    evaluation = evaluate_conversational_runtime(state)

    assert evaluation["passed"] is True
    assert evaluation["correction_count"] == 1
    assert evaluation["background_cycle_count"] >= 1
