from __future__ import annotations

import json
import os
import sys
import tkinter as tk
import time
from pathlib import Path

import DELTA
from orchestration.runtime.live_general_3_learning_mission import run_live_general_3_approved_learning_mission

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
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ROOT", tmp_path / "live-runtime-3")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ROOT", tmp_path / "live-runtime-4")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    accepted = tmp_path / "accepted-general-3"
    if not (accepted / "terminal" / "terminal.json").exists():
        run_live_general_3_approved_learning_mission(root=accepted, reset=True)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ACCEPTED_ROOT", accepted)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ACCEPTED_ROOT", accepted)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ACCEPTED_ROOT", accepted)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ACCEPTED_ROOT", accepted)
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
    restart = json.loads((DELTA.LIVE_RUNTIME_4_ROOT / "restart_state.json").read_text(encoding="utf-8"))
    return restart["continuous_learning_state"]["live_runtime_1"]


def test_live_runtime_4_tk_crash_recovery_reauthorization_and_terminal_restart(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, root, "prepare live runtime 4 crash mission")
        assert _state()["phase_history"] == ["mission_registered", "work_graph_registered"]

        _send(app, root, "authorize first bounded unattended live runtime 4")
        _send(app, root, "start crash bounded unattended live runtime 4")
        process = app.live_runtime_4_process
        deadline = time.time() + 25
        while process and process.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        assert process is not None
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        assert process.returncode == 77
        _destroy(root)
    finally:
        _destroy(root)

    recovery_root, recovered = _app(monkeypatch, tmp_path)
    try:
        recovered._load_live_runtime_4_state()
        crash_stop = json.loads((DELTA.LIVE_RUNTIME_4_ROOT / "unattended_stop" / "stop.json").read_text(encoding="utf-8"))
        assert crash_stop["stop_reason"] == "runner_crash_recovered"
        assert "stopped runner_crash_recovered" in recovered.live_runtime_status.get()
        assert len(_state()["evaluation_item_ids"]) == 1

        _send(recovered, recovery_root, "authorize second bounded unattended live runtime 4")
        authority_files = sorted((DELTA.LIVE_RUNTIME_4_ROOT / "unattended_authority").glob("*.json"))
        assert len(authority_files) == 2
        _send(recovered, recovery_root, "start bounded unattended live runtime 4")
        process = recovered.live_runtime_4_process
        deadline = time.time() + 25
        while process and process.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        assert process is not None
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        assert process.returncode == 0
        recovered._load_live_runtime_4_state()
        final = _state()
        assert final["status"] == "terminal"
        assert len(final["evaluation_item_ids"]) == 4
        assert final["counts"]["provider_calls"] == 0
    finally:
        _destroy(recovery_root)

    final_root, final_app = _app(monkeypatch, tmp_path)
    try:
        final_app._load_live_runtime_4_state()
        before = tuple(sorted(path.relative_to(DELTA.LIVE_RUNTIME_4_ROOT).as_posix() for path in DELTA.LIVE_RUNTIME_4_ROOT.rglob("*.json")))
        _send(final_app, final_root, "live runtime 4 status")
        after = tuple(sorted(path.relative_to(DELTA.LIVE_RUNTIME_4_ROOT).as_posix() for path in DELTA.LIVE_RUNTIME_4_ROOT.rglob("*.json")))
        assert before == after
        assert "stopped terminal" in final_app.live_runtime_status.get()
    finally:
        _destroy(final_root)
