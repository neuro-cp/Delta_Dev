import time
import tkinter as tk


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."


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


def test_evidence_permission_uses_tk_conversation_surface_and_restart_recall(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, GOAL)
        _send(app, FINANCE)
        assert app.conversational_runtime_state.pending_chat_requests[0].request_type == "evidence_bound_analysis_question"

        _send(app, "Assume losing more than 10% over six months is unacceptable.")
        evidence_requests = _records(app, "evidence_requests")
        pending = app.conversational_runtime_state.pending_chat_requests
        request = pending[0]

        assert len(evidence_requests) == 1
        assert evidence_requests[0]["status"] == "surfaced"
        assert request.request_type == "evidence_permission"
        assert request.rendered_turn_id
        assert request.render_sequence > 0
        transcript = app.chat_history.get("1.0", tk.END).lower()
        observation = app.observation_stream.get("1.0", tk.END).lower()
        assert "permission request only" in transcript
        assert "no evidence gathering has started" in transcript
        assert "evidence permission" in observation

        _send(app, "What is 2 + 2?")
        assert "4" in app.chat_history.get("1.0", tk.END).lower().rsplit("you: what is 2 + 2?", 1)[-1]
        assert app.conversational_runtime_state.pending_chat_requests[0].request_id == request.request_id
        assert not _records(app, "evidence_authorizations")

        _send(app, "No, keep it hypothetical.")
        authorizations = _records(app, "evidence_authorizations")
        assert len(authorizations) == 1
        assert authorizations[0]["status"] == "denied"
        assert not app.conversational_runtime_state.pending_chat_requests
        transcript = app.chat_history.get("1.0", tk.END).lower()
        observation = app.observation_stream.get("1.0", tk.END).lower()
        assert "decision: denied" in transcript
        assert "no evidence gathering" in transcript
        assert "evidence authorization" in observation
        runtime_root = app.conversational_runtime_root
        ids = (
            evidence_requests[0]["evidence_permission_request_id"],
            request.request_id,
            authorizations[0]["evidence_authorization_id"],
        )
    finally:
        root.destroy()

    root, restored = _app(monkeypatch, tmp_path)
    try:
        assert restored.conversational_runtime_root == runtime_root
        restored_request = _records(restored, "evidence_requests")[0]
        restored_authorization = _records(restored, "evidence_authorizations")[0]
        assert (
            restored_request["evidence_permission_request_id"],
            restored.conversational_runtime_state.resolved_chat_requests[-1].request_id,
            restored_authorization["evidence_authorization_id"],
        ) == ids

        _send(restored, "What was the evidence request and my decision?")
        recap = restored.chat_history.get("1.0", tk.END).lower()
        assert "read-only recall" in recap
        assert "denied" in recap
        assert len(_records(restored, "evidence_authorizations")) == 1
    finally:
        root.destroy()
