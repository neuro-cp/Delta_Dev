from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.live_general_3_learning_mission import run_live_general_3_approved_learning_mission
from orchestration.runtime.live_runtime_2_bounded_unattended import run_live_runtime_2_bounded_unattended

if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


class _DummyProviderManager:
    def __init__(self, keep_loaded: bool = True) -> None:
        self.keep_loaded = keep_loaded

    def warm(self, _model_id: str) -> None:
        return None


class _CompletedProcess:
    pid = 4242


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    accepted = tmp_path / "accepted-general-3"
    if not (accepted / "terminal" / "terminal.json").exists():
        run_live_general_3_approved_learning_mission(root=accepted, reset=True)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ACCEPTED_ROOT", accepted)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ACCEPTED_ROOT", accepted)
    monkeypatch.setattr(DELTA, "ProviderManager", _DummyProviderManager)
    root = tk.Tk()
    root.update()
    app = DELTA.DeltaApp(root)
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


def _state() -> dict:
    restart = json.loads((DELTA.LIVE_RUNTIME_2_ROOT / "restart_state.json").read_text(encoding="utf-8"))
    return restart["continuous_learning_state"]["live_runtime_1"]


def test_live_runtime_2_tk_explicit_unattended_start_and_recovery(monkeypatch, tmp_path):
    starts: list[str] = []

    def fake_start(*, runtime_root, python_executable=None):
        starts.append(str(runtime_root))
        run_live_runtime_2_bounded_unattended(runtime_root=runtime_root)
        return _CompletedProcess()

    monkeypatch.setattr(DELTA, "start_live_runtime_2_process", fake_start)
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, root, "prepare live runtime 2 unattended mission")
        state = _state()
        assert state["phase_history"] == ["mission_registered", "work_graph_registered"]
        assert len(state["work_items"]) == 4
        assert app.evaluation_review_items == []

        _send(app, root, "authorize bounded unattended live runtime 2")
        authority_files = tuple((DELTA.LIVE_RUNTIME_2_ROOT / "unattended_authority").glob("*.json"))
        assert len(authority_files) == 1

        _send(app, root, "start bounded unattended live runtime 2")
        assert starts == [str(DELTA.LIVE_RUNTIME_2_ROOT)]
        stop = json.loads((DELTA.LIVE_RUNTIME_2_ROOT / "unattended_stop" / "stop.json").read_text(encoding="utf-8"))
        assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PASSED"
        _destroy(root)
    finally:
        _destroy(root)

    restart_root, restarted = _app(monkeypatch, tmp_path)
    try:
        restarted._load_live_runtime_2_state()
        state = _state()
        assert restarted.live_runtime_2_controller is not None
        assert restarted.live_runtime_2_controller.continuous_mission_state == "live_runtime_1_terminal"
        assert len(state["evaluation_item_ids"]) == 4
        assert len([item for item in restarted.evaluation_review_items if item["item_type"] == "live_runtime_2_evaluation"]) == 4
        assert "stopped terminal" in restarted.live_runtime_status.get()
        before = tuple(sorted(path.relative_to(DELTA.LIVE_RUNTIME_2_ROOT).as_posix() for path in DELTA.LIVE_RUNTIME_2_ROOT.rglob("*.json")))
        _send(restarted, restart_root, "live runtime 2 status")
        after = tuple(sorted(path.relative_to(DELTA.LIVE_RUNTIME_2_ROOT).as_posix() for path in DELTA.LIVE_RUNTIME_2_ROOT.rglob("*.json")))
        assert before == after
        assert starts == [str(DELTA.LIVE_RUNTIME_2_ROOT)]
    finally:
        _destroy(restart_root)


def test_live_runtime_2_tk_does_not_start_without_authority(monkeypatch, tmp_path):
    starts: list[str] = []
    monkeypatch.setattr(DELTA, "start_live_runtime_2_process", lambda **kwargs: starts.append(str(kwargs["runtime_root"])))
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, root, "prepare live runtime 2 unattended mission")
        _send(app, root, "start bounded unattended live runtime 2")

        assert starts == []
        assert "authority record is missing" in app.session_history[-1]["content"]
    finally:
        _destroy(root)
