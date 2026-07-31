import tkinter as tk
from dataclasses import replace
import time


ENGLISH_GOAL = "Your goal today is to improve your English comprehension so we can communicate better."
FOREGROUND_CAMPAIGN_GOAL = (
    "Your new goal is to improve how you distinguish between a new foreground question and a continuation "
    "of the previous topic. Study our normal conversation, identify the first recurring failure pattern, "
    "compare at least three bounded approaches, test them against unrelated-topic and follow-up cases, "
    "and notify me when you reach a meaningful milestone, become blocked, or finish with an adoption recommendation. "
    "Use local cognition and existing evidence first. Do not change source or restart without my explicit approval. "
    "Start working now."
)


def _app(monkeypatch, tmp_path):
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    monkeypatch.setattr(DELTA.DeltaApp, "_warm_default_model", lambda self: None)
    monkeypatch.setattr(DELTA.DeltaApp, "_conversational_cognitive_model_runner", lambda self: ScriptedSemanticModel())
    monkeypatch.setattr(DELTA, "CONVERSATIONAL_RUNTIME_ROOT", tmp_path / "conversational-runtime")
    last_error = None
    for _ in range(4):
        try:
            root = tk.Tk()
            break
        except tk.TclError as exc:
            last_error = exc
            time.sleep(0.1)
    else:
        raise last_error
    app = DELTA.DeltaApp(root)
    root.update()
    return root, app


def _send(app, text):
    app.chat_input.delete(0, tk.END)
    app.chat_input.insert(0, text)
    app._send_chat()


def _pump_until(root, predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        root.update()
        if predicate():
            return
        time.sleep(0.02)
    assert predicate()


def _add_local_insufficiency(app):
    from orchestration.runtime.conversational_runtime_operation import record_local_semantic_attempt

    app.conversational_runtime_state, evaluation = record_local_semantic_attempt(
        app.conversational_runtime_state,
        runtime_root=app.conversational_runtime_root,
        target_gap="queued implied references across topic switches",
        local_model="qwen-test",
        local_prompt="Generate topic-switch counterexamples.",
        raw_response="One vague reference note only.",
    )
    assert evaluation["status"] == "locally_insufficient"


def test_default_surface_is_simple_and_advanced_is_inspectable(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        tabs = [app.notebook.tab(tab_id, "text") for tab_id in app.notebook.tabs()]
        assert tabs == ["Conversation"]
        assert "Chat runtime: ready" in app.conversational_runtime_status.get()

        app._open_developer_diagnostics()
        tabs = [app.notebook.tab(tab_id, "text") for tab_id in app.notebook.tabs()]
        assert "Developer" in tabs
        assert "Goals" in tabs
        assert "Settings" in tabs
        assert app.developer_notebook.tab(app.advanced_tab, "text") == "Diagnostics"
    finally:
        root.destroy()


def test_chat_goal_correction_transfer_and_authority_boundary(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, "How are you?")
        assert app.conversational_runtime_state.active_objective is None

        _send(app, ENGLISH_GOAL)
        assert app.conversational_runtime_state.active_objective is not None
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "That was too verbose. Use shorter answers for this kind of explanation.")
        assert len(app.conversational_runtime_state.corrections) == 1
        assert len(app.conversational_runtime_state.accepted_lessons) == 1

        _send(app, "Explain the style issue again.")
        assert any(item.get("event") == "lesson_transfer_applied" for item in app.conversational_runtime_state.objective_progress)

        _send(app, "Modify your source code and push it.")
        assert app.conversational_runtime_state.pending_material_authority
        assert app.conversational_runtime_state.active_objective is not None
    finally:
        root.destroy()


def test_active_inference_shows_working_status_without_blocking_chat(monkeypatch, tmp_path):
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        original_cycle = DELTA.run_conversational_background_cycle

        def slow_cycle(*args, **kwargs):
            time.sleep(0.25)
            kwargs["model_runner"] = ScriptedSemanticModel()
            return original_cycle(*args, **kwargs)

        monkeypatch.setattr(DELTA, "run_conversational_background_cycle", slow_cycle)
        start = time.time()
        started = app._start_conversational_background_cycle("test_slow_inference")
        elapsed = time.time() - start
        assert started is True
        assert elapsed < 0.15
        assert "working" in app.conversational_runtime_status.get()
        assert app.conversational_runtime_state.active_objective is not None
        cycle_count = len(app.conversational_runtime_state.completed_cycle_keys)
        _pump_until(root, lambda: len(app.conversational_runtime_state.completed_cycle_keys) > cycle_count, timeout=4.0)
        assert "working" not in app.conversational_runtime_status.get()
    finally:
        root.destroy()


def test_mid_inference_keeps_foreground_turn_and_completes_the_worker_once(monkeypatch, tmp_path):
    """Exercise the actual Tk worker path while a foreground turn arrives."""
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        before_cycles = len(app.conversational_runtime_state.completed_cycle_keys)
        original_cycle = DELTA.run_conversational_background_cycle

        def slow_cycle(*args, **kwargs):
            time.sleep(0.25)
            kwargs["model_runner"] = ScriptedSemanticModel()
            return original_cycle(*args, **kwargs)

        monkeypatch.setattr(DELTA, "run_conversational_background_cycle", slow_cycle)
        assert app._start_conversational_background_cycle("mid_inference_foreground") is True
        assert app.conversational_runtime_inference_in_flight is True

        _send(app, "What color is the sky?")

        assert app.conversational_runtime_inference_in_flight is True
        assert any(turn.role == "user" and turn.text == "What color is the sky?" for turn in app.conversational_runtime_state.conversation)
        _pump_until(root, lambda: len(app.conversational_runtime_state.completed_cycle_keys) > before_cycles, timeout=4.0)
        assert sum(turn.role == "user" and turn.text == "What color is the sky?" for turn in app.conversational_runtime_state.conversation) == 1
        assert len(app.conversational_runtime_state.completed_cycle_keys) == before_cycles + 1
    finally:
        root.destroy()


def test_message_during_active_inference_is_acknowledged_and_preserved(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        app.conversational_runtime_inference_in_flight = True

        _send(app, "also compare that with how I use pronouns")

        assert app.conversational_runtime_state.conversation[-1].intent_type == "ordinary_conversation_queued"
        assert app.conversational_runtime_state.conversation[-1].text == "also compare that with how I use pronouns"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "Your message is queued" in transcript
    finally:
        root.destroy()


def test_goal_like_message_during_inference_is_queued_not_recompiled(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        app.conversational_runtime_inference_in_flight = True

        _send(app, "Your goal today is also to pay attention to topic switches.")

        assert app.conversational_runtime_state.active_objective.objective_id == objective_id
        assert app.conversational_runtime_state.conversation[-1].intent_type == "goal_or_priority_queued"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "possible goal or priority update" in transcript
    finally:
        root.destroy()


def test_provider_request_and_natural_approval_bind_inside_chat(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        _add_local_insufficiency(app)

        _send(app, "Please request a provider learning packet for implied references.")
        assert app.conversational_runtime_state.pending_chat_requests
        transcript = app.chat_history.get("1.0", tk.END)
        assert "[Goal update · Language understanding]" in transcript
        assert "Approve?" in transcript

        _send(app, "Approve, but do not send my actual messages.")
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert len(app.conversational_runtime_state.provider_authorities) == 1
        authority = app.conversational_runtime_state.provider_authorities[0]
        assert authority["status"] == "authorized_not_executed"
        assert "actual operator messages" in authority["prohibited_data"]
    finally:
        root.destroy()


def test_pending_authority_reply_resolves_while_inference_busy(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        _add_local_insufficiency(app)
        _send(app, "Please request a provider learning packet for implied references.")
        app.conversational_runtime_inference_in_flight = True

        _send(app, "Use only one call.")

        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert len(app.conversational_runtime_state.provider_authorities) == 1
        assert app.conversational_runtime_state.provider_authorities[0]["max_calls"] == 1
        assert app.conversational_runtime_state.conversation[-2].intent_type == "chat_request_resolution"
    finally:
        root.destroy()


def test_pending_authority_denial_uses_chat_without_popup(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        _add_local_insufficiency(app)
        _send(app, "Please request a provider learning packet for implied references.")

        _send(app, "No, continue locally.")

        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.provider_authorities == ()
        assert app.conversational_runtime_state.resolved_chat_requests[0].status == "denied"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "continue the goal locally" in transcript
    finally:
        root.destroy()


def test_goal_review_renders_in_chat(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "review the active goal")

        transcript = app.chat_history.get("1.0", tk.END)
        assert "[Goal review" in transcript
        assert "I retained:" in transcript
        assert "Provider use:" in transcript
        assert app.conversational_runtime_state.goal_reviews
    finally:
        root.destroy()


def test_campaign_goal_milestone_renders_inline_without_budget_review(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(
            root,
            lambda: any(
                item.get("event") == "capability_campaign_milestone_rendered"
                for item in app.conversational_runtime_state.objective_progress
            ),
            timeout=5.0,
        )

        transcript = app.chat_history.get("1.0", tk.END)
        assert "[Goal update - Foreground vs continuation routing]" in transcript
        assert "I found the first recurring failure pattern" in transcript
        assert "[Goal review Â· Language understanding]" not in transcript
        assert app.conversational_runtime_state.lifecycle_state == "running"
        assert len(app.conversational_runtime_state.completed_cycle_keys) < app.conversational_runtime_state.active_objective.cycle_budget
    finally:
        root.destroy()


def test_foreground_chat_answers_basic_questions_during_campaign_goal(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        _send(app, "okay while you're working on that tell me what color is the sky?")
        _send(app, "what color is the moon?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        assert "blue" in transcript
        assert "moon" in transcript
        assert "i understand. i will treat this as ordinary conversation" not in transcript
        assert app.conversational_runtime_state.active_objective is not None
    finally:
        root.destroy()


def test_negative_scope_with_new_color_question_does_not_reuse_prior_topic(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        _send(app, "What color is the Moon?")

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "Do not apply that rule to cooking questions. What color is the sky?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: do not apply that rule to cooking questions. what color is the sky?", 1)[-1]
        assert "blue" in latest
        assert "moon color appearance" not in latest
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert app.conversational_runtime_state.active_objective is not None
    finally:
        root.destroy()


def test_correction_and_unrelated_factual_question_commit_once(monkeypatch, tmp_path):
    import DELTA
    import orchestration.runtime.conversational_runtime_operation as operation

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        save_calls = []
        original_delta_save = DELTA.save_conversational_runtime_state

        def counted_save(root_path, state):
            save_calls.append((root_path, len(state.conversation)))
            return original_delta_save(root_path, state)

        monkeypatch.setattr(DELTA, "save_conversational_runtime_state", counted_save)
        monkeypatch.setattr(operation, "save_runtime_state", counted_save)
        render_calls = []
        original_append_chat = app._append_chat
        original_append_session = app._append_session
        session_calls = []

        def counted_append_chat(speaker, text):
            render_calls.append((speaker, text))
            return original_append_chat(speaker, text)

        def counted_append_session(role, content):
            session_calls.append((role, content))
            return original_append_session(role, content)

        app._append_chat = counted_append_chat
        app._append_session = counted_append_session
        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "That explanation was too long. Use shorter answers here. Also, what color is the sky?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: that explanation was too long. use shorter answers here. also, what color is the sky?", 1)[-1]
        assert "[goal update]" in latest
        assert "blue" in latest
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert app.conversational_runtime_state.conversation[-2].text == "That explanation was too long. Use shorter answers here. Also, what color is the sky?"
        assert app.conversational_runtime_state.conversation[-1].intent_type == "coordinated_composed_response"
        assert len(save_calls) == 1
        assert len([item for item in render_calls if item[0] == "DELTA"]) == 1
        assert len([item for item in session_calls if item[0] == "user"]) == 1
        assert len([item for item in session_calls if item[0] == "assistant"]) == 1
        assert app.last_coordinated_dispatch_audit["deferred_subordinate_save_count"] >= 1
        assert app.last_coordinated_dispatch_audit["final_persistence_owner"] == "dispatch_coordinator"
    finally:
        root.destroy()


def test_pause_and_factual_question_commit_once(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "Pause the active goal. Also, what color is water?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: pause the active goal. also, what color is water?", 1)[-1]
        assert "paused the active goal" in latest
        assert "water" in latest
        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_runtime_state_query_during_active_goal_commits_once(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "Are you currently paused or running, and are there pending requests?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: are you currently paused or running, and are there pending requests?", 1)[-1]
        assert "[runtime state]" in latest
        assert "active goal: yes" in latest
        assert "pending requests:" in latest
        assert "would you like me to ask" not in latest
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_runtime_state_query_reports_last_question_and_discarded_count(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        _send(app, "What color is the sky?")
        _send(app, "What is frobnicated glim energy?")
        _send(app, "No, leave it.")

        _send(app, "What was the last user question, and how many requests were discarded or expired?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: what was the last user question, and how many requests were discarded or expired?", 1)[-1]
        assert "[runtime state]" in latest
        assert "last user question: no, leave it." in latest
        assert "discarded or expired requests: 1" in latest
        assert "would you like me to ask" not in latest
    finally:
        root.destroy()


def test_visible_local_model_permission_yes_consumes_once(monkeypatch, tmp_path):
    import DELTA
    import orchestration.runtime.conversational_runtime_operation as operation

    original_route = DELTA.route_message

    def scripted_route(mode, message, *args, **kwargs):
        if kwargs.get("execute_local_model"):
            return {
                "mode": "Conversation",
                "route": "local_model_answer",
                "answer": "Here is the local-model expansion.",
                "confidence": "local_model_result",
                "confidence_score": 0.74,
                "selected_model_lane": {"lane": "everyday_conversation", "selected_model_id": "scripted-local-model"},
                "local_model_result": {"executed": True},
                "supporting_information_offer": None,
                "local_model_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        return original_route(mode, message, *args, **kwargs)

    monkeypatch.setattr(DELTA, "route_message", scripted_route)
    root, app = _app(monkeypatch, tmp_path)
    try:
        save_calls = []
        original_delta_save = DELTA.save_conversational_runtime_state

        def counted_save(root_path, state):
            save_calls.append((root_path, len(state.conversation), len(state.pending_chat_requests)))
            return original_delta_save(root_path, state)

        monkeypatch.setattr(DELTA, "save_conversational_runtime_state", counted_save)
        monkeypatch.setattr(operation, "save_runtime_state", counted_save)
        _send(app, "What is frobnicated glim energy?")
        assert len(app.conversational_runtime_state.pending_chat_requests) == 1
        assert app.conversational_runtime_state.pending_chat_requests[0].request_type == "local_model_execution"
        assert len(save_calls) == 1

        save_calls.clear()
        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "Yes, ask it.")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: yes, ask it.", 1)[-1]
        assert "local-model expansion" in latest
        assert "would you like me to ask" not in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert len(app.conversational_runtime_state.resolved_chat_requests) == 1
        assert app.conversational_runtime_state.resolved_chat_requests[0].consumption_count == 1
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert len(save_calls) == 1
        assert app.last_coordinated_dispatch_audit["final_persistence_owner"] == "dispatch_coordinator"
    finally:
        root.destroy()


def test_visible_local_model_permission_no_denies_once(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, "What is frobnicated glim energy?")
        assert len(app.conversational_runtime_state.pending_chat_requests) == 1

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "No, leave it.")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: no, leave it.", 1)[-1]
        assert "leave that unanswered" in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert len(app.conversational_runtime_state.resolved_chat_requests) == 1
        assert app.conversational_runtime_state.resolved_chat_requests[0].status == "denied"
        assert app.conversational_runtime_state.resolved_chat_requests[0].consumption_count == 1
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_two_pending_requests_clarify_and_consume_none(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        requests = (
            ChatAddressableRequest(
                request_id="request-provider",
                request_type="provider_authority",
                objective_id=objective_id,
                goal_label="Language understanding",
                prompt_text="Approve provider?",
                max_calls=1,
                max_spend_usd=1.0,
            ),
            ChatAddressableRequest(
                request_id="request-local-model",
                request_type="local_model_execution",
                objective_id=objective_id,
                goal_label="Local model permission",
                prompt_text="Ask local model?",
                max_calls=1,
            ),
        )
        app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=requests)
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Yes, go ahead.")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: yes, go ahead.", 1)[-1]
        assert "clarification needed" in latest
        assert tuple(item.request_id for item in app.conversational_runtime_state.pending_chat_requests) == ("request-provider", "request-local-model")
        assert app.conversational_runtime_state.resolved_chat_requests == ()
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_reference_clarification_create_resolve_and_expire(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import record_foreground_message_for_reconciliation

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        app.conversational_runtime_state = record_foreground_message_for_reconciliation(
            app.conversational_runtime_state,
            "Explain thermal expansion in bridges.",
            runtime_root=tmp_path / "conversational-runtime",
        )
        app.conversational_runtime_state = record_foreground_message_for_reconciliation(
            app.conversational_runtime_state,
            "Now explain angular momentum in skating.",
            runtime_root=tmp_path / "conversational-runtime",
        )

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "For the goal, compare that to the prior subject.")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: for the goal, compare that to the prior subject.", 1)[-1]
        assert "which prior subject" in latest
        assert app.conversational_runtime_state.pending_chat_requests[-1].request_type == "reference_clarification"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2

        _send(app, "I meant angular momentum.")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: i meant angular momentum.", 1)[-1]
        assert "bound that reference" in latest
        assert not any(item.request_type == "reference_clarification" for item in app.conversational_runtime_state.pending_chat_requests)
        assert app.conversational_runtime_state.resolved_chat_requests[-1].request_type == "reference_clarification"
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "resolved"

        app.conversational_runtime_state = replace(app.conversational_runtime_state, resolved_chat_requests=())
        _send(app, "For the goal, compare that to the prior subject.")
        assert app.conversational_runtime_state.pending_chat_requests[-1].request_type == "reference_clarification"
        _send(app, "What color is water?")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: what color is water?", 1)[-1]
        assert "water" in latest
        assert not any(item.request_type == "reference_clarification" for item in app.conversational_runtime_state.pending_chat_requests)
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "expired"
    finally:
        root.destroy()


def test_multi_obligation_correction_pause_and_factual_question(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "That was too verbose. Pause the active goal. Also, what color is the sky?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: that was too verbose. pause the active goal. also, what color is the sky?", 1)[-1]
        assert latest.count("[goal update]") >= 1
        assert "paused the active goal" in latest
        assert "blue" in latest
        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert app.last_coordinated_dispatch_audit["control_count"] == 2
        assert app.last_coordinated_dispatch_audit["final_persistence_owner"] == "dispatch_coordinator"
    finally:
        root.destroy()


def test_multi_obligation_approval_and_runtime_state_question(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        request = ChatAddressableRequest(
            request_id="provider-approval-runtime-state",
            request_type="provider_authority",
            objective_id=objective_id,
            goal_label="Provider authority",
            prompt_text="Approve provider?",
            max_calls=1,
            max_spend_usd=1.0,
        )
        app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(request,))
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Approve one call. Also, are you currently running or paused?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: approve one call. also, are you currently running or paused?", 1)[-1]
        assert "approved" in latest
        assert "[runtime state]" in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.provider_authorities
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_multi_obligation_adoption_and_runtime_state_commit_once(monkeypatch, tmp_path):
    import DELTA
    import orchestration.runtime.conversational_runtime_operation as operation
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        request = ChatAddressableRequest(
            request_id="adoption-runtime-state",
            request_type="capability_adoption_and_restart",
            objective_id=objective_id,
            goal_label="Semantic reconciliation",
            prompt_text="Adopt this capability?",
            capability_id="semantic_reconciliation",
            capability_version="test",
            capability_name="Semantic reconciliation",
            evidence_digest="test-evidence",
            restart_required=True,
        )
        app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(request,))
        save_calls = []
        original_delta_save = DELTA.save_conversational_runtime_state

        def counted_save(root_path, state):
            save_calls.append((root_path, len(state.conversation), len(state.pending_chat_requests), len(state.restart_records)))
            return original_delta_save(root_path, state)

        monkeypatch.setattr(DELTA, "save_conversational_runtime_state", counted_save)
        monkeypatch.setattr(operation, "save_runtime_state", counted_save)
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Yes, adopt it. Also, are you currently running or paused?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: yes, adopt it. also, are you currently running or paused?", 1)[-1]
        assert "recorded the adoption" in latest
        assert "[runtime state]" in latest
        assert "active goal: no" in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.resolved_chat_requests[-1].request_id == "adoption-runtime-state"
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "consumed"
        assert app.conversational_runtime_state.capability_registry[-1]["activation_state"] == "active"
        assert len(app.conversational_runtime_state.restart_records) == 1
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert len(save_calls) == 1
        assert app.last_coordinated_dispatch_audit["final_persistence_owner"] == "dispatch_coordinator"
        assert app.last_coordinated_dispatch_audit["render_owner"] == "dispatch_coordinator"
    finally:
        root.destroy()


def test_multi_obligation_denial_and_unrelated_factual_question(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        request = ChatAddressableRequest(
            request_id="provider-denial-foreground",
            request_type="provider_authority",
            objective_id=objective_id,
            goal_label="Provider authority",
            prompt_text="Approve provider?",
            max_calls=1,
            max_spend_usd=1.0,
        )
        app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(request,))
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "No, continue locally. Also, what color is the sky?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: no, continue locally. also, what color is the sky?", 1)[-1]
        assert "continue the goal locally" in latest
        assert "blue" in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "denied"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_multi_obligation_resume_and_queued_update_introspection(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import record_foreground_message_for_reconciliation

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        _send(app, "Pause the active goal.")
        app.conversational_runtime_state = record_foreground_message_for_reconciliation(
            app.conversational_runtime_state,
            "Your goal today is also to pay attention to topic switches.",
            runtime_root=tmp_path / "conversational-runtime",
            intent_type="goal_or_priority_queued",
        )
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Resume the active goal. Also, are there queued updates?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: resume the active goal. also, are there queued updates?", 1)[-1]
        assert "resumed the active goal" in latest
        assert "[runtime state]" in latest
        assert "queued turns: 1" in latest
        assert app.conversational_runtime_state.lifecycle_state == "running"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_multi_obligation_restart_continuation_and_last_question_query(monkeypatch, tmp_path):
    import DELTA
    import orchestration.runtime.conversational_runtime_operation as operation

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        _send(app, "What color is water?")
        app._start_conversational_background_cycle = lambda _reason: True
        save_calls = []
        original_delta_save = DELTA.save_conversational_runtime_state

        def counted_save(root_path, state):
            save_calls.append((root_path, len(state.conversation)))
            return original_delta_save(root_path, state)

        monkeypatch.setattr(DELTA, "save_conversational_runtime_state", counted_save)
        monkeypatch.setattr(operation, "save_runtime_state", counted_save)
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Restart after saving state. Then continue where you left off. Also, what was the last user question?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: restart after saving state. then continue where you left off. also, what was the last user question?", 1)[-1]
        assert "saved the current state" in latest
        assert "active goal remains running" in latest
        assert "last user question: what color is water?" in latest
        assert len(save_calls) == 1
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert app.last_coordinated_dispatch_audit["deferred_subordinate_save_count"] >= 1
    finally:
        root.destroy()


def test_natural_stop_redirect_pauses_active_goal(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "stop working on that and focus on topic switches instead")

        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        assert app.conversational_runtime_state.objective_progress[-1]["event"] == "operator_stop_or_redirect"
        assert app.conversational_runtime_state.conversation[-1].role == "assistant"
        assert app.conversational_runtime_state.conversation[-1].intent_type == "stop_or_redirect_acknowledgement"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "paused the active goal" in transcript
        assert "Chat runtime: paused goal" in app.conversational_runtime_status.get()
    finally:
        root.destroy()


def test_stale_background_result_does_not_overwrite_operator_pause(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        prior = app.conversational_runtime_state
        worker_state = app._merge_conversational_background_result(
            prior,
            prior,
        )
        assert worker_state.lifecycle_state == "running"

        _send(app, "stop working on that and focus on topic switches instead")
        paused = app.conversational_runtime_state
        merged = app._merge_conversational_background_result(prior, prior)

        assert paused.lifecycle_state == "paused_operator"
        assert merged.lifecycle_state == "paused_operator"
    finally:
        root.destroy()


def test_settings_renders_gpt_style_chat_schema(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        app._open_developer_diagnostics()
        text = app.chat_settings_detail.get("1.0", tk.END)
        assert '"conversation"' in text
        assert '"ordinary_chat_default": true' in text
        assert '"advanced_surface": "hidden_until_requested"' in text
        assert '"tracked_source_mutation": "explicit_approval_required"' in text
    finally:
        root.destroy()


def test_capability_adoption_restart_and_next_goal_handoff_in_chat(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "Review the semantic-reconciliation capability you developed. Tell me whether you recommend adopting it.")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "[Capability review" in transcript
        assert "Would you like me to adopt Approach A and restart the runtime?" in transcript
        assert app.conversational_runtime_state.pending_chat_requests[-1].request_type == "capability_adoption_and_restart"

        _send(app, "Yes. Adopt it, save state, and restart. Do not change anything else.")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "Restart complete." in transcript
        assert "Structured discourse reconciliation is active." in transcript
        assert "What goal should I work on next?" in transcript
        assert app.conversational_runtime_state.capability_registry[-1]["activation_state"] == "active"
        assert app.conversational_runtime_state.pending_chat_requests == ()

        _send(app, "Your new goal is to improve side-thread directional-question binding across delayed replies. Start with local cognition and existing evidence.")
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys), timeout=5.0)
        assert app.conversational_runtime_state.active_objective is not None
        assert "side-thread directional-question binding" in app.conversational_runtime_state.active_objective.interpreted_objective
        assert len(app.conversational_runtime_state.completed_cycle_keys) >= 1
        transcript = app.chat_history.get("1.0", tk.END)
        assert "Local cognition has started" in transcript

        _send(app, "What is kinetic energy?")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "kinetic energy" in transcript.lower()
        assert app.conversational_runtime_state.capability_registry[-1]["activation_state"] == "active"
    finally:
        root.destroy()


def test_chat_first_fourteen_step_tk_campaign(monkeypatch, tmp_path):
    """Run the closure sequence through the visible Tk chat widgets."""
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    root, app = _app(monkeypatch, tmp_path)
    try:
        # 1-2: ordinary foreground chat remains useful before and after a goal.
        _send(app, "What color is the sky?")
        assert "blue" in app.chat_history.get("1.0", tk.END).lower()
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        goal_id = app.conversational_runtime_state.active_objective.objective_id

        # 3-5: normal factual chat and a scoped correction coexist with the goal.
        _send(app, "What color is the Moon?")
        _send(app, "That was too verbose. Use shorter answers for this kind of explanation.")
        _send(app, "Explain the style issue again.")
        assert any(item.get("event") == "lesson_transfer_applied" for item in app.conversational_runtime_state.objective_progress)

        # 6-8: a negative scope blocks transfer, provider use remains governed,
        # and a natural denial consumes the exact pending request once.
        _send(app, "Do not apply that rule to cooking questions. What color is the sky?")
        _add_local_insufficiency(app)
        _send(app, "Please request a provider learning packet for implied references.")
        assert len(app.conversational_runtime_state.pending_chat_requests) == 1
        _send(app, "Do not use a provider. Also, what is kinetic energy?")
        assert not app.conversational_runtime_state.pending_chat_requests
        assert len(app.conversational_runtime_state.resolved_chat_requests) == 1

        # 9-11: a paused goal never captures foreground chat and resumes once.
        _send(app, "Pause the active goal.")
        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        _pump_until(root, lambda: not app.conversational_runtime_inference_in_flight, timeout=4.0)
        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        _send(app, "Why is the Moon gray?")
        _send(app, "Resume the active goal.")
        assert app.conversational_runtime_state.active_objective.objective_id == goal_id
        assert app.conversational_runtime_state.lifecycle_state == "running"

        # 12: the review is an inline chat event, not a mode switch.
        _send(app, "Review the active goal.")
        assert "goal review" in app.chat_history.get("1.0", tk.END).lower()

        # 13-14: a real worker remains alive while a goal-like update is
        # durably queued for later reconciliation.
        original_cycle = DELTA.run_conversational_background_cycle

        def slow_cycle(*args, **kwargs):
            time.sleep(0.25)
            kwargs["model_runner"] = ScriptedSemanticModel()
            return original_cycle(*args, **kwargs)

        monkeypatch.setattr(DELTA, "run_conversational_background_cycle", slow_cycle)
        before_cycles = len(app.conversational_runtime_state.completed_cycle_keys)
        assert app._start_conversational_background_cycle("fourteen_step_campaign") is True
        _send(app, "Your goal today is also to pay attention to topic switches.")
        assert app.conversational_runtime_state.active_objective.objective_id == goal_id
        assert app.conversational_runtime_state.conversation[-1].intent_type == "goal_or_priority_queued"
        _pump_until(root, lambda: len(app.conversational_runtime_state.completed_cycle_keys) > before_cycles, timeout=4.0)
        assert sum(turn.text == "Your goal today is also to pay attention to topic switches." for turn in app.conversational_runtime_state.conversation if turn.role == "user") == 1
        _send(app, "Please wait until the current reasoning step finishes, then tell me if the topic-switch update remained queued exactly once.")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: please wait until the current reasoning step finishes, then tell me if the topic-switch update remained queued exactly once.", 1)[-1]
        assert "queued exactly once" in latest
        assert "would you like me to ask a local reasoning model" not in latest
        assert sum(turn.text == "Your goal today is also to pay attention to topic switches." for turn in app.conversational_runtime_state.conversation if turn.role == "user") == 1
    finally:
        root.destroy()
