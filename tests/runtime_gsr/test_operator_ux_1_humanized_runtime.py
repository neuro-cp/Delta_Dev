from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.operator_ux import (
    compile_formal_operator_response,
    compile_operator_request_card,
    consume_formal_operator_response,
    goal_card_from_live_runtime_state,
    narration_from_live_runtime_state,
    normalize_operator_intent,
)

if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


class _DummyProviderManager:
    def __init__(self, keep_loaded: bool = True) -> None:
        self.keep_loaded = keep_loaded

    def warm(self, _model_id: str) -> None:
        return None


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "ProviderManager", _DummyProviderManager)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ROOT", tmp_path / "live-runtime-3")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ROOT", tmp_path / "live-runtime-4")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    root = tk.Tk()
    root.update()
    app = DELTA.DeltaApp(root)
    app.operator_ux_root = tmp_path / "operator-ux"
    root.update()
    return root, app


def _send(app: DELTA.DeltaApp, root: tk.Tk, message: str) -> None:
    app.chat_input.delete(0, tk.END)
    app.chat_input.insert(0, message)
    app._send_chat()
    root.update()


def _destroy(root: tk.Tk) -> None:
    try:
        root.destroy()
    except tk.TclError:
        pass


def _request() -> dict[str, object]:
    request = {
        "request_id": "req-1",
        "title": "I need your approval",
        "what_delta_wants": "Try one bounded step.",
        "why": "It unlocks the next task.",
        "files_or_resources": ("fixture.csv",),
        "may_change": "Only disposable artifacts.",
        "provider_or_network_use": "No provider calls.",
        "learning_attempts": 0,
        "if_declined": "The branch stays paused.",
    }
    card = compile_operator_request_card(request)
    return {**request, "artifact_digest": card["artifact_digest"]}


def test_operator_ux_intent_normalization_is_deterministic():
    for text in ("yes", "approve", "go ahead", "do it", "that's fine", "proceed"):
        assert normalize_operator_intent(text)["intent"] == "approve"
    for text in ("no", "decline", "deny", "don't do that", "stop", "not now"):
        assert normalize_operator_intent(text)["intent"] == "decline"
    for text in ("explain", "why", "I don't understand", "can you simplify that"):
        assert normalize_operator_intent(text)["intent"] == "explain"
    for text in ("pause", "wait", "hold on", "ask me later"):
        assert normalize_operator_intent(text)["intent"] == "pause"
    assert normalize_operator_intent("sounds interesting")["requires_clarification"] is True


def test_operator_ux_formal_response_consumes_exactly_once():
    request = _request()
    intent = normalize_operator_intent("approve")
    response = compile_formal_operator_response(request, intent, response_source="button:approve")
    consumed = consume_formal_operator_response(response)

    assert response["formal_disposition"] == "approved"
    assert consumed["consumed"] is True
    try:
        consume_formal_operator_response(consumed)
    except ValueError as exc:
        assert str(exc) == "operator_ux_response_already_consumed"
    else:
        raise AssertionError("consumed response was consumed twice")


def test_operator_ux_goal_and_narration_are_grounded_without_chain_of_thought():
    state = {
        "mission": {"mission_id": "mission-1", "objective": "Compare records"},
        "status": "terminal",
        "scheduler_cycles": 10,
        "work_items": (
            {"label": "csv_validation", "work_item_id": "csv"},
            {"label": "json_validation", "work_item_id": "json"},
            {"label": "cross_format_reconciliation", "work_item_id": "recon"},
            {"label": "dynamic_synthesis", "work_item_id": "synth"},
        ),
        "work_item_status": {
            "csv_validation": "completed",
            "json_validation": "completed",
            "cross_format_reconciliation": "completed",
            "dynamic_synthesis": "completed",
        },
    }
    card = goal_card_from_live_runtime_state(state)
    events = narration_from_live_runtime_state(state)

    assert card["state"] == "Completed"
    assert card["progress_completed"] == 4
    assert events
    assert all(event["chain_of_thought_exposed"] is False for event in events)
    assert all(event["mission_id"] == "mission-1" for event in events)


def test_operator_ux_tk_request_explain_approve_and_restart(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, root, "create operator ux demo goal")
        assert app.active_operator_ux_request is not None
        assert app.operator_ux_popup is not None
        request_id = app.active_operator_ux_request["request_id"]

        _send(app, root, "explain")
        assert app.active_operator_ux_request is not None
        assert not (app.operator_ux_root / "consumed_responses").exists()

        app.operator_ux_popup.destroy()
        root.update()
        assert app.active_operator_ux_request is not None

        _send(app, root, "sounds ok maybe")
        assert app.active_operator_ux_request is not None
        assert "I'm not sure whether you are approving" in app.chat_history.get("1.0", tk.END)

        _send(app, root, "approve")
        assert app.active_operator_ux_request is None
        consumed = tuple((app.operator_ux_root / "consumed_responses").glob("*.json"))
        assert len(consumed) == 1
        consumed_record = json.loads(consumed[0].read_text(encoding="utf-8"))
        assert consumed_record["request_id"] == request_id
    finally:
        _destroy(root)

    recovered_root, recovered = _app(monkeypatch, tmp_path)
    try:
        recovered.operator_ux_root = tmp_path / "operator-ux"
        recovered._refresh_operator_ux_views()
        assert recovered.active_operator_ux_request is None
        assert recovered.operator_ux_popup is None
        before = set(recovered.operator_ux_narration_events)
        recovered._refresh_operator_ux_views()
        after = set(recovered.operator_ux_narration_events)
        assert before == after
    finally:
        _destroy(recovered_root)


def test_operator_ux_top_level_tabs_and_rc_diagnostics_consolidated(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        tabs = [app.notebook.tab(tab_id, "text") for tab_id in app.notebook.tabs()]
        developer_tabs = [app.developer_notebook.tab(tab_id, "text") for tab_id in app.developer_notebook.tabs()]
        assert tabs == ["Conversation", "Goals", "Activity", "Evaluation", "Memory", "Settings", "Developer"]
        assert developer_tabs == ["RC3", "RC4", "RC5", "Diagnostics"]
        assert "RC3" not in tabs and "RC4" not in tabs and "RC5" not in tabs
    finally:
        _destroy(root)


def test_operator_ux_evaluation_behavior_remains_read_only(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        app._set_evaluation_review_items([
            {
                "title": "Review item",
                "status": "pending_operator_review",
                "boundary": "read only",
                "operator_action": "review",
                "details": {"x": 1},
            }
        ])
        first = next(iter(app.evaluation_snapshot))
        app.evaluation_items.selection_set(first)
        app._record_evaluation_disposition("accepted")
        assert app.evaluation_dispositions == []
        assert "display-only" in app.evaluation_status.get()
    finally:
        _destroy(root)
