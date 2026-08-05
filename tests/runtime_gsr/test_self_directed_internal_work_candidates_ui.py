import time
import tkinter as tk


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. When uncertainty blocks refinement, seek one clarification from me and "
    "bind the reply to the relevant analysis. When another unresolved detail remains, independently offer one safe internal continuation proposal "
    "that I can retain, postpone, dismiss, or answer. Do not call a model or provider, use a tool, take an external action, change source code, "
    "or restart. Wait for my scenarios."
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


def test_internal_continuation_uses_normal_tk_request_surface_and_preserves_foreground_chat(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, GOAL)
        _send(app, OPERATIONS)
        assert app.conversational_runtime_state.pending_chat_requests[0].request_type == "evidence_bound_analysis_question"

        _send(app, "The pump is due Friday afternoon.")

        candidates = _records(app, "internal_work_candidates")
        selections = _records(app, "internal_work_selections")
        refinements = _records(app, "analysis_refinements")
        pending = app.conversational_runtime_state.pending_chat_requests
        selected = next(item for item in candidates if item["status"] == "surfaced")
        request = pending[0]

        assert refinements
        assert selected["source_refinement_id"] == refinements[-1]["refinement_id"]
        assert selected["unresolved_slot_id"] == "logistics.invoice_payment_status"
        assert len(pending) == 1
        assert request.request_type == "internal_work_continuation"
        assert request.rendered_turn_id
        assert request.render_sequence > 0
        assert any(item["status"] == "surfaced" for item in selections)

        transcript = app.chat_history.get("1.0", tk.END).lower()
        observation = app.observation_stream.get("1.0", tk.END).lower()
        assert "one safe internal continuation is available" in transcript
        assert f"unresolved issue: {selected['unresolved_label'].lower()}" in transcript
        assert "internal continuation" in observation
        assert selected["source_analysis_id"] in observation
        assert not app.conversational_runtime_inference_in_flight

        _send(app, "What is 2 + 2?")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        assert "4" in transcript.rsplit("you: what is 2 + 2?", 1)[-1]
        assert len(app.conversational_runtime_state.pending_chat_requests) == 1
        assert app.conversational_runtime_state.pending_chat_requests[0].request_id == request.request_id
        assert not _records(app, "internal_work_dispositions")

        _send(app, "The invoice is disputed, so payment timing is not confirmed.")
        dispositions = _records(app, "internal_work_dispositions")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        observation = app.observation_stream.get("1.0", tk.END).lower()
        assert len(dispositions) == 1
        assert dispositions[0]["candidate_id"] == selected["internal_work_candidate_id"]
        assert dispositions[0]["status"] == "resolved_by_answer"
        assert not app.conversational_runtime_state.pending_chat_requests
        assert "provenance-only disposition" in transcript
        assert "no internal work started" in observation
        assert len(_records(app, "analysis_refinements")) == 1
        assert not app.conversational_runtime_inference_in_flight
        runtime_root = app.conversational_runtime_root
        ids = (
            selected["internal_work_candidate_id"],
            request.request_id,
            dispositions[0]["internal_work_disposition_id"],
        )
    finally:
        root.destroy()

    root, restored = _app(monkeypatch, tmp_path)
    try:
        restored_candidates = _records(restored, "internal_work_candidates")
        restored_dispositions = _records(restored, "internal_work_dispositions")
        restored_request = restored.conversational_runtime_state.resolved_chat_requests[-1]
        assert restored.conversational_runtime_root == runtime_root
        assert (
            next(item for item in restored_candidates if item["internal_work_candidate_id"] == ids[0])["internal_work_candidate_id"],
            restored_request.request_id,
            restored_dispositions[0]["internal_work_disposition_id"],
        ) == ids
        assert not restored.conversational_runtime_state.pending_chat_requests

        recall_prompt = "What internal continuation remains from that analysis?"
        from orchestration.runtime.conversational_runtime_operation import is_internal_work_recall_message

        assert is_internal_work_recall_message(restored.conversational_runtime_state, recall_prompt)
        _send(restored, recall_prompt)
        recap = restored.chat_history.get("1.0", tk.END).lower()
        assert "read-only provenance recall" in recap
        assert len(_records(restored, "internal_work_dispositions")) == 1
        assert len(_records(restored, "analysis_refinements")) == 1
    finally:
        root.destroy()
