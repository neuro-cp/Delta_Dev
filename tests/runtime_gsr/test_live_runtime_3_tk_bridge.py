from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.live_general_3_learning_mission import run_live_general_3_approved_learning_mission
from orchestration.runtime.live_runtime_3_interruption_resumption import run_live_runtime_3_bounded_unattended

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
    pid = 4343


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ROOT", tmp_path / "live-runtime-3")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    accepted = tmp_path / "accepted-general-3"
    if not (accepted / "terminal" / "terminal.json").exists():
        run_live_general_3_approved_learning_mission(root=accepted, reset=True)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ACCEPTED_ROOT", accepted)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ACCEPTED_ROOT", accepted)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ACCEPTED_ROOT", accepted)
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
    restart = json.loads((DELTA.LIVE_RUNTIME_3_ROOT / "restart_state.json").read_text(encoding="utf-8"))
    return restart["continuous_learning_state"]["live_runtime_1"]


def test_live_runtime_3_tk_interruption_reauthorization_and_terminal_recovery(monkeypatch, tmp_path):
    starts: list[str] = []

    def fake_start(*, runtime_root, authority_id=None, python_executable=None):
        starts.append(str(runtime_root))
        run_live_runtime_3_bounded_unattended(runtime_root=runtime_root, authority_id=authority_id)
        return _CompletedProcess()

    monkeypatch.setattr(DELTA, "start_live_runtime_3_process", fake_start)
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, root, "prepare live runtime 3 interruption mission")
        assert _state()["phase_history"] == ["mission_registered", "work_graph_registered"]

        _send(app, root, "authorize first bounded unattended live runtime 3")
        _send(app, root, "start bounded unattended live runtime 3")
        first = json.loads((DELTA.LIVE_RUNTIME_3_ROOT / "unattended_stop" / "stop.json").read_text(encoding="utf-8"))
        assert first["stop_reason"] == "cycle_limit"
        _destroy(root)
    finally:
        _destroy(root)

    recovery_root, recovered = _app(monkeypatch, tmp_path)
    try:
        recovered._load_live_runtime_3_state()
        interrupted = _state()
        assert recovered.live_runtime_3_controller is not None
        assert interrupted["work_item_status"]["csv_validation"] == "completed"
        assert interrupted["work_item_status"]["json_validation"] == "completed"
        assert len(interrupted["evaluation_item_ids"]) == 2

        _send(recovered, recovery_root, "authorize second bounded unattended live runtime 3")
        authority_files = sorted((DELTA.LIVE_RUNTIME_3_ROOT / "unattended_authority").glob("*.json"))
        assert len(authority_files) == 2
        _send(recovered, recovery_root, "start bounded unattended live runtime 3")
        final = _state()
        assert final["status"] == "terminal"
        assert len(final["evaluation_item_ids"]) == 4
        assert final["counts"]["csv_learner"] == 1
        assert final["counts"]["json_adapter"] == 1
        assert starts == [str(DELTA.LIVE_RUNTIME_3_ROOT), str(DELTA.LIVE_RUNTIME_3_ROOT)]
    finally:
        _destroy(recovery_root)

    final_root, final_app = _app(monkeypatch, tmp_path)
    try:
        final_app._load_live_runtime_3_state()
        before = tuple(sorted(path.relative_to(DELTA.LIVE_RUNTIME_3_ROOT).as_posix() for path in DELTA.LIVE_RUNTIME_3_ROOT.rglob("*.json")))
        _send(final_app, final_root, "live runtime 3 status")
        after = tuple(sorted(path.relative_to(DELTA.LIVE_RUNTIME_3_ROOT).as_posix() for path in DELTA.LIVE_RUNTIME_3_ROOT.rglob("*.json")))
        assert before == after
        assert len([item for item in final_app.evaluation_review_items if item["item_type"] == "live_runtime_3_evaluation"]) == 4
        assert "stopped terminal" in final_app.live_runtime_status.get()
        assert starts == [str(DELTA.LIVE_RUNTIME_3_ROOT), str(DELTA.LIVE_RUNTIME_3_ROOT)]
    finally:
        _destroy(final_root)
