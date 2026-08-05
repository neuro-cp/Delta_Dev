import time
import tkinter as tk


GOAL = (
    "Your new goal is to use the next source-bound semantic scenarios for bounded analysis. "
    "Preserve source evidence, assumptions, validation checks, limits, and safe next actions. "
    "Do not call a model, access a provider, take an external action, change source code, or restart. "
    "Wait for the scenarios."
)
OPERATIONS = (
    "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
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


def test_workbench_analysis_uses_normal_tk_conversation_observation_recall_and_restart(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import background_cycle_hold_reason
    from orchestration.runtime.provisional_semantic_consolidation import load_graph

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, GOAL)
        objective = app.conversational_runtime_state.active_objective
        assert objective is not None
        assert background_cycle_hold_reason(app.conversational_runtime_state) == "wait_for_operator_input"
        graph_before = load_graph(app.conversational_runtime_root)

        _send(app, OPERATIONS)

        objective = app.conversational_runtime_state.active_objective
        assert objective is not None
        frames = objective.provenance["semantic_problem_frames"]
        analyses = objective.provenance["evidence_bound_analyses"]
        assert len(frames) == 1
        assert len(analyses) == 1
        frame_id = frames[0]["frame_id"]
        analysis_id = analyses[0]["analysis_id"]
        assert analyses[0]["source_frame_id"] == frame_id
        assert analyses[0]["status"] == "provisional_analysis"
        assert not app.conversational_runtime_inference_in_flight
        assert not app.conversational_runtime_state.completed_cycle_keys
        assert not app.conversational_runtime_state.pending_chat_requests

        transcript = app.chat_history.get("1.0", tk.END).lower()
        observation = app.observation_stream.get("1.0", tk.END).lower()
        graph_after = load_graph(app.conversational_runtime_root)
        assert "bounded, source-bound analysis" in transcript
        assert "pump delivery" in transcript
        assert "not reviewed or admitted knowledge" in transcript
        assert "evidence-bound analysis" in observation
        assert analysis_id in observation
        assert frame_id in observation
        assert "semantic frame" in observation
        assert len(graph_after.experiences) == len(graph_before.experiences)
        assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
        assert not graph_after.packets
        assert not graph_after.reviews
        assert not graph_after.admissions

        _send(app, "What operational bottleneck did you identify?")
        recall = app.chat_history.get("1.0", tk.END).lower()
        assert "pump delivery" in recall
        assert "read-only source-bound analysis recall" in recall
        assert len(app.conversational_runtime_state.active_objective.provenance["evidence_bound_analyses"]) == 1

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
        assert len(objective.provenance["semantic_problem_frames"]) == 1
        assert len(objective.provenance["evidence_bound_analyses"]) == 1
        assert objective.provenance["semantic_problem_frames"][0]["frame_id"] == frame_id
        assert objective.provenance["evidence_bound_analyses"][0]["analysis_id"] == analysis_id
        assert background_cycle_hold_reason(restored.conversational_runtime_state) == "wait_for_operator_input"

        _send(restored, OPERATIONS)
        objective = restored.conversational_runtime_state.active_objective
        assert len(objective.provenance["semantic_problem_frames"]) == 1
        assert len(objective.provenance["evidence_bound_analyses"]) == 1
        assert sum(
            1
            for event in restored.conversational_runtime_state.objective_progress
            if event.get("event") == "evidence_bound_analysis_recorded"
            and event.get("analysis_id") == analysis_id
        ) == 1
    finally:
        root.destroy()
