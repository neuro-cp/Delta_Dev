from orchestration.runtime.conversational_runtime_operation import (
    chat_feature_settings_schema,
    classify_conversational_intent,
    evaluate_conversational_runtime,
    handle_conversational_message,
    read_json,
    save_runtime_state,
    start_or_restore_runtime,
    stop_active_objective,
)


ENGLISH_GOAL = "Your goal today is to improve your English comprehension so we can communicate better."


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
