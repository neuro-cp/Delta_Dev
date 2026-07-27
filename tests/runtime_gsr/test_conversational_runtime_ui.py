import tkinter as tk
import time


ENGLISH_GOAL = "Your goal today is to improve your English comprehension so we can communicate better."


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


def test_natural_stop_redirect_pauses_active_goal(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "stop working on that and focus on topic switches instead")

        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        assert app.conversational_runtime_state.objective_progress[-1]["event"] == "operator_stop_or_redirect"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "paused the active goal" in transcript
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
