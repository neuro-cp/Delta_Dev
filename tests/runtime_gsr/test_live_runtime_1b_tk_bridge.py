from __future__ import annotations

import json
import tkinter as tk

import DELTA
from orchestration.runtime.live_general_3_learning_mission import run_live_general_3_approved_learning_mission


class _DummyProviderManager:
    def __init__(self, keep_loaded: bool = True) -> None:
        self.keep_loaded = keep_loaded

    def warm(self, _model_id: str) -> None:
        return None


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    accepted = tmp_path / "accepted-general-3"
    if not (accepted / "terminal" / "terminal.json").exists():
        run_live_general_3_approved_learning_mission(root=accepted, reset=True)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ACCEPTED_ROOT", accepted)
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


def _state(app: DELTA.DeltaApp) -> dict:
    assert app.live_runtime_1b_controller is not None, app.live_runtime_status.get()
    return dict(app.live_runtime_1b_controller.continuous_learning_state["live_runtime_1"])


def test_live_runtime_1b_tk_bridge_enters_advances_recovers_and_renders_evaluations(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, root, DELTA.LIVE_RUNTIME_1B_MISSION_TEXT)
        state = _state(app)
        assert app.live_runtime_1b_controller.continuous_mission_state == "live_runtime_1_attached"
        assert state["scheduler_cycles"] == 0
        assert app.evaluation_review_items == []

        for _ in range(2):
            _send(app, root, "advance live runtime 1b")
        root.destroy()

        restart_root, restarted = _app(monkeypatch, tmp_path)
        try:
            restarted_state = _state(restarted)
            assert tuple(restarted_state["phase_history"]) == ("mission_registered", "work_graph_registered")
            assert len(restarted_state["work_items"]) == 4
            assert tuple(restarted_state["evaluation_item_ids"]) == ()

            for _ in range(6):
                _send(restarted, restart_root, "advance live runtime 1b")
            branch_state = _state(restarted)
            assert branch_state["work_item_status"]["csv_validation"] == "completed"
            assert branch_state["work_item_status"]["json_validation"] == "completed"
            assert branch_state["counts"]["csv_learner"] == 1
            assert branch_state["counts"]["json_adapter"] == 1
            assert len(branch_state["evaluation_item_ids"]) == 2
            _destroy(restart_root)
        finally:
            _destroy(restart_root)

        terminal_root, terminal_app = _app(monkeypatch, tmp_path)
        try:
            for _ in range(2):
                _send(terminal_app, terminal_root, "advance live runtime 1b")
            terminal_state = _state(terminal_app)
            assert terminal_app.live_runtime_1b_controller.continuous_mission_state == "live_runtime_1_terminal"
            assert terminal_state["terminal"]["terminal_status"] == "LIVE_RUNTIME_1_SUSTAINED_ATTENDED_PASSED"
            assert len(terminal_state["evaluation_item_ids"]) == 4
            assert len([item for item in terminal_app.evaluation_review_items if item["item_type"] == "live_runtime_1b_evaluation"]) == 4
            assert "LIVE-RUNTIME-1B" in terminal_app.live_runtime_status.get()
            _destroy(terminal_root)
        finally:
            _destroy(terminal_root)

        replay_root, replay_app = _app(monkeypatch, tmp_path)
        try:
            before = tuple(sorted(path.relative_to(DELTA.LIVE_RUNTIME_1B_ROOT).as_posix() for path in DELTA.LIVE_RUNTIME_1B_ROOT.rglob("*.json")))
            _send(replay_app, replay_root, "advance live runtime 1b")
            after = tuple(sorted(path.relative_to(DELTA.LIVE_RUNTIME_1B_ROOT).as_posix() for path in DELTA.LIVE_RUNTIME_1B_ROOT.rglob("*.json")))
            replay_state = _state(replay_app)
            assert replay_state["counts"] == terminal_state["counts"]
            assert before == after
            assert replay_app.evaluation_status.get().startswith("GSR/OAR review surface")
            restart_payload = json.loads((DELTA.LIVE_RUNTIME_1B_ROOT / "restart_state.json").read_text(encoding="utf-8"))
            assert restart_payload["continuous_mission_state"] == "live_runtime_1_terminal"
        finally:
            _destroy(replay_root)
    finally:
        _destroy(root)


def test_live_runtime_1b_tk_bridge_suppresses_stale_non_runtime_review_items(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        app.evaluation_review_items = [{
            "item_type": "oar_mission_compilation",
            "title": "Stale OAR Mission Compilation",
            "status": "mission_approved",
            "details": {"request_id": "stale-request"},
        }]
        app._refresh_evaluation_snapshot()

        _send(app, root, DELTA.LIVE_RUNTIME_1B_MISSION_TEXT)

        assert app.evaluation_review_items == []
        assert all("Stale OAR" not in item["title"] for item in app.evaluation_snapshot.values())
    finally:
        _destroy(root)
