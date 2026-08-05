import time
import tkinter as tk


GOAL = (
    "Your new goal is to review a source-bound operations scenario. "
    "Keep its interpretation provisional, do not change source code, and do not restart."
)
CONSTRAINED_GOAL = (
    "Your new goal is to interpret the next few source-bound semantic scenarios as provisional semantic frames. "
    "Preserve the source, assumptions, uncertainty, safety limits, and validation checks. "
    "Do not call a model, access a provider, take an external action, change source code, or restart. "
    "Wait for the scenarios."
)
OPERATIONS_NOTE = (
    "Read this operations note: Invoice #A17 is 14 days overdue. "
    "Crew North cannot start the drainage job until the pump is delivered."
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


def test_semantic_problem_frame_uses_the_normal_tk_foreground_and_observation_paths(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import (
        handle_conversational_message,
        save_runtime_state,
    )
    from orchestration.runtime.provisional_semantic_consolidation import load_graph

    root, app = _app(monkeypatch, tmp_path)
    try:
        created = handle_conversational_message(
            app.conversational_runtime_state,
            GOAL,
            runtime_root=app.conversational_runtime_root,
            run_background_cycle=False,
        ).state
        app.conversational_runtime_state = created
        save_runtime_state(app.conversational_runtime_root, created)
        graph_before = load_graph(app.conversational_runtime_root)

        _send(app, OPERATIONS_NOTE)

        objective = app.conversational_runtime_state.active_objective
        assert objective is not None
        frames = objective.provenance["semantic_problem_frames"]
        frame = frames[0]
        frame_id = frame["frame_id"]
        transcript = app.chat_history.get("1.0", tk.END).lower()
        observation = app.observation_stream.get("1.0", tk.END).lower()
        graph_after = load_graph(app.conversational_runtime_root)

        assert len(frames) == 1
        assert frame["semantic_input_frame"]["domain_guess"] == "operations_logistics_receivables"
        assert "overdue invoice" in transcript
        assert "source-bound and provisional" in transcript
        assert "semantic frame" in observation
        assert frame_id in observation
        assert len(graph_after.experiences) == len(graph_before.experiences)
        assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
        assert not graph_after.packets
        assert not graph_after.reviews
        assert not graph_after.admissions
        assert not app.conversational_runtime_state.pending_chat_requests
        assert app.dispatch_shadow_diagnostics[-1]["actual"]["rendered_owner"] == "conversational_runtime"

        _send(app, "What did you perceive in the operations note?")
        recall = app.chat_history.get("1.0", tk.END).lower()
        assert "overdue receivable" in recall
        assert "read-only recall" in recall
        assert len(app.conversational_runtime_state.active_objective.provenance["semantic_problem_frames"]) == 1

        _send(app, "What is 2 + 2?")
        assert "4" in app.chat_history.get("1.0", tk.END).rsplit("You: What is 2 + 2?", 1)[-1]
        runtime_root = app.conversational_runtime_root
    finally:
        root.destroy()

    root, restored = _app(monkeypatch, tmp_path)
    try:
        assert restored.conversational_runtime_root == runtime_root
        objective = restored.conversational_runtime_state.active_objective
        assert objective is not None
        frames = objective.provenance["semantic_problem_frames"]
        assert len(frames) == 1
        assert frames[0]["frame_id"] == frame_id

        _send(restored, OPERATIONS_NOTE)
        frames = restored.conversational_runtime_state.active_objective.provenance["semantic_problem_frames"]
        assert len(frames) == 1
        assert frames[0]["frame_id"] == frame_id
        assert sum(
            1
            for event in restored.conversational_runtime_state.objective_progress
            if event.get("event") == "semantic_problem_frame_recorded"
            and event.get("frame_id") == frame_id
        ) == 1
    finally:
        root.destroy()


def test_normal_tk_goal_honors_wait_constraints_while_foreground_frames_and_chat_remain_available(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import background_cycle_hold_reason

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, CONSTRAINED_GOAL)
        root.update()

        objective = app.conversational_runtime_state.active_objective
        assert objective is not None
        assert background_cycle_hold_reason(app.conversational_runtime_state) == "wait_for_operator_input"
        assert objective.provenance["execution_constraints"]["no_local_model"] is True
        assert not app.conversational_runtime_inference_in_flight
        assert not app.conversational_runtime_state.completed_cycle_keys
        assert not any(
            item.get("event") == "background_cycle"
            for item in app.conversational_runtime_state.objective_progress
        )
        assert "waiting for your next input" in app.chat_history.get("1.0", tk.END).lower()

        app._tick_conversational_objective_runtime()
        assert not app.conversational_runtime_inference_in_flight
        assert not any(
            item.get("decision_stage") == "active_gate"
            for item in app.interactive_coordination_state.decision_history
        )

        _send(app, OPERATIONS_NOTE)
        objective = app.conversational_runtime_state.active_objective
        assert objective is not None
        assert len(objective.provenance["semantic_problem_frames"]) == 1
        assert not app.conversational_runtime_inference_in_flight
        assert not app.conversational_runtime_state.completed_cycle_keys

        _send(app, "What is 2 + 2?")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "4" in transcript.rsplit("You: What is 2 + 2?", 1)[-1]
        assert not app.conversational_runtime_state.pending_chat_requests
        assert background_cycle_hold_reason(app.conversational_runtime_state) == "wait_for_operator_input"
    finally:
        root.destroy()
