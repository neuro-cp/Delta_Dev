import tkinter as tk
import time


ENGLISH_GOAL = "Your goal today is to improve your English comprehension so we can communicate better."


def _app(monkeypatch, tmp_path):
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    monkeypatch.setattr(DELTA.DeltaApp, "_warm_default_model", lambda self: None)
    monkeypatch.setattr(DELTA.DeltaApp, "_conversational_cognitive_model_runner", lambda self: ScriptedSemanticModel())
    monkeypatch.setattr(DELTA, "CONVERSATIONAL_RUNTIME_ROOT", tmp_path / "conversational-runtime")
    root = tk.Tk()
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
