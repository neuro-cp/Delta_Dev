import time
import tkinter as tk


GOAL = (
    "Your new goal is to analyze source-bound scenarios. When uncertainty or missing context materially blocks a refinement, "
    "ask me one useful clarification, bind my answer to the exact analysis, and append a provisional refinement. "
    "Do not call a model or provider, use a tool, take an external action, change source code, or restart. Wait for my scenarios."
)
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."


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
    app.root.update()


def _records(app, key):
    objective = app.conversational_runtime_state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def test_playable_question_answer_refinement_loop_uses_normal_tk_surfaces_and_restart(monkeypatch, tmp_path):
    from orchestration.runtime.provisional_semantic_consolidation import load_graph

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, GOAL)
        graph_before = load_graph(app.conversational_runtime_root)

        _send(app, OPERATIONS)

        frames = _records(app, "semantic_problem_frames")
        analyses = _records(app, "evidence_bound_analyses")
        candidates = _records(app, "operator_question_candidates")
        selections = _records(app, "operator_question_selections")
        pending = app.conversational_runtime_state.pending_chat_requests
        frame_id = frames[0]["frame_id"]
        analysis_id = analyses[0]["analysis_id"]
        candidate = next(item for item in candidates if item["status"] == "asked")
        request = pending[0]

        assert len(frames) == 1
        assert len(analyses) == 1
        assert len(candidates) == 4
        assert len(selections) == 4
        assert candidate["unknown_slot_id"] == "logistics.pump_delivery_eta"
        assert len(pending) == 1
        assert request.request_type == "evidence_bound_analysis_question"
        assert request.rendered_turn_id
        assert request.render_sequence > 0
        assert request.baseline_metrics["source_frame_id"] == frame_id
        assert request.baseline_metrics["source_analysis_id"] == analysis_id
        assert request.baseline_metrics["question_id"] == candidate["question_id"]

        transcript = app.chat_history.get("1.0", tk.END).lower()
        observation = app.observation_stream.get("1.0", tk.END).lower()
        assert "expected to arrive" in transcript
        assert "why one clarification matters" in transcript
        assert "safety boundary" in transcript
        assert "analysis question" in observation
        assert analysis_id in observation
        assert "delivery timing determines" in observation
        assert not app.conversational_runtime_inference_in_flight

        _send(app, "It is expected to arrive Friday afternoon.")

        answers = _records(app, "operator_question_answers")
        refinements = _records(app, "analysis_refinements")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        observation = app.observation_stream.get("1.0", tk.END).lower()
        assert len(answers) == 1
        assert len(refinements) == 1
        assert answers[0]["question_id"] == candidate["question_id"]
        assert refinements[0]["source_analysis_id"] == analysis_id
        assert refinements[0]["source_answer_id"] == answers[0]["answer_id"]
        assert not app.conversational_runtime_state.pending_chat_requests
        assert "appended your answer" in transcript
        assert "time-bounded" in transcript
        assert "analysis refinement" in observation
        assert refinements[0]["refinement_id"] in observation

        _send(app, "What changed after my answer?")
        _send(app, "What is still uncertain?")
        _send(app, "What is 2 + 2?")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        assert "read-only source-bound refinement recall" in transcript
        assert "4" in transcript.rsplit("you: what is 2 + 2?", 1)[-1]
        assert len(_records(app, "operator_question_answers")) == 1
        assert len(_records(app, "analysis_refinements")) == 1
        assert len(_records(app, "evidence_bound_analyses")) == 1

        graph_after = load_graph(app.conversational_runtime_root)
        assert len(graph_after.experiences) == len(graph_before.experiences)
        assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
        assert not graph_after.packets
        assert not graph_after.reviews
        assert not graph_after.admissions
        runtime_root = app.conversational_runtime_root
        ids = (frame_id, analysis_id, candidate["question_id"], answers[0]["answer_id"], refinements[0]["refinement_id"])
    finally:
        root.destroy()

    root, restored = _app(monkeypatch, tmp_path)
    try:
        assert restored.conversational_runtime_root == runtime_root
        restored_ids = (
            _records(restored, "semantic_problem_frames")[0]["frame_id"],
            _records(restored, "evidence_bound_analyses")[0]["analysis_id"],
            _records(restored, "operator_question_candidates")[0]["question_id"],
            _records(restored, "operator_question_answers")[0]["answer_id"],
            _records(restored, "analysis_refinements")[0]["refinement_id"],
        )
        assert restored_ids == ids
        assert not restored.conversational_runtime_state.pending_chat_requests

        _send(restored, "What did we analyze, what did you ask, and what did my answer change?")
        chain_recap = restored.chat_history.get("1.0", tk.END).lower()
        assert "recorded chain" in chain_recap
        assert "when is pump expected to arrive?" in chain_recap
        assert "it is expected to arrive friday afternoon." in chain_recap
        assert len(_records(restored, "operator_question_answers")) == 1
        assert len(_records(restored, "analysis_refinements")) == 1
    finally:
        root.destroy()
