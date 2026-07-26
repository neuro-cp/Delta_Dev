from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_mixed_mission import acquire_mission_lock, compile_mixed_mission, run_mixed_mission, select_next_task, stale_authority_response
from tests.runtime_gsr.test_autonomy_13_task_scoped_activation import _competence_roots
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager


if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def test_a16_compiles_task_graph_and_routes_mixed_mission(tmp_path):
    roots = _competence_roots(tmp_path)
    result = run_mixed_mission(tmp_path / "mission", competence_roots=roots)
    restart = run_mixed_mission(tmp_path / "mission", competence_roots=roots, mode="restart")
    report = result["report"]
    by_key = {task["task_key"]: task for task in report["tasks"]}

    assert result["status"] == "AUTONOMY_16_PERSISTENT_MIXED_MISSION_ROUTING_PASSED"
    assert report["final_mission_disposition"] == "partially_completed"
    assert report["one_active_task_maximum"] is True
    assert by_key["direct_json"]["current_lifecycle_state"] == "completed"
    assert by_key["direct_reconciliation"]["current_lifecycle_state"] == "completed"
    assert by_key["composition"]["current_lifecycle_state"] == "completed"
    assert by_key["partial"]["current_lifecycle_state"] == "partially_completed"
    assert by_key["unsupported"]["current_lifecycle_state"] == "blocked_capability_gap"
    assert by_key["blocked_authority"]["current_lifecycle_state"] == "blocked_operator_authority"
    assert by_key["prohibited"]["current_lifecycle_state"] == "rejected_prohibited"
    assert by_key["ambiguous"]["current_lifecycle_state"] == "awaiting_clarification"
    assert by_key["duplicate_json"]["current_lifecycle_state"] == "deferred"
    assert by_key["independent_a"]["current_lifecycle_state"] == "completed"
    assert by_key["independent_b"]["current_lifecycle_state"] == "completed"
    assert restart["status"] == result["status"]
    assert restart["report"]["task_counts"] == report["task_counts"]


def test_a16_blocked_branch_does_not_freeze_independent_work(tmp_path):
    roots = _competence_roots(tmp_path)
    report = run_mixed_mission(tmp_path / "mission", competence_roots=roots)["report"]
    by_key = {task["task_key"]: task for task in report["tasks"]}
    assert by_key["blocked_authority"]["current_lifecycle_state"] == "blocked_operator_authority"
    assert by_key["independent_a"]["current_lifecycle_state"] == "completed"
    assert by_key["independent_b"]["current_lifecycle_state"] == "completed"


def test_a16_budget_pause_stop_duplicate_runner_and_stale_response(tmp_path):
    roots = _competence_roots(tmp_path)
    budget = run_mixed_mission(tmp_path / "budget", competence_roots=roots, budget_transitions=1)
    assert budget["status"] == "paused_budget"
    stopped = run_mixed_mission(tmp_path / "stopped", competence_roots=roots, mode="stop")
    replay = run_mixed_mission(tmp_path / "stopped", competence_roots=roots)
    assert stopped["status"] == "stopped_by_operator"
    assert replay["duplicate_suppressed"] is True
    mission = compile_mixed_mission(tmp_path / "lock", competence_roots=roots)
    first = acquire_mission_lock(tmp_path / "lock", mission)
    second = acquire_mission_lock(tmp_path / "lock", mission)
    assert first["acquired"] is True
    assert second["reason"] == "duplicate_active_runner"
    run_mixed_mission(tmp_path / "authority", competence_roots=roots, budget_transitions=0)
    tasks = list((tmp_path / "authority" / "authority_requests").glob("*.json"))
    assert tasks
    check = stale_authority_response(tmp_path / "authority", tasks[0].stem)
    assert check["accepted"] is False


def test_a16_dependency_waits_before_prerequisite(tmp_path):
    roots = _competence_roots(tmp_path)
    mission = compile_mixed_mission(tmp_path / "mission", competence_roots=roots)
    # Before classification/execution, the highest selected task is direct JSON; dependent reconciliation waits.
    from orchestration.runtime.autonomy_mixed_mission import _classify_tasks

    _classify_tasks(tmp_path / "mission", roots)
    selected = select_next_task(tmp_path / "mission")
    assert selected["task_key"] in {"direct_json", "blocked_authority", "prohibited"}


def test_tk_a16_mission_controls_and_chat_intents(monkeypatch, tmp_path):
    cycle_1, cycle_2 = _competence_roots(tmp_path)
    for source, target in (
        (cycle_1, tmp_path / ".tmp" / "autonomy-12r-final-cycle-1" / "a6_admission"),
        (cycle_2, tmp_path / ".tmp" / "autonomy-12r-final-cycle-2" / "a6_admission"),
    ):
        target.mkdir(parents=True, exist_ok=True)
        for path in (source / "accepted_competencies").glob("*.json"):
            destination = target / "accepted_competencies" / path.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(DELTA, "ProviderManager", _DummyProviderManager)
    monkeypatch.setattr(DELTA, "ROOT", tmp_path)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ROOT", tmp_path / "live-runtime-3")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ROOT", tmp_path / "live-runtime-4")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ACCEPTED_ROOT", tmp_path / "accepted")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    root = tk.Tk()
    root.update()
    app = DELTA.DeltaApp(root)
    try:
        app.operator_ux_root = tmp_path / "operator-ux"
        app._refresh_operator_ux_views()
        assert str(app.a16_control_buttons["start"]["state"]) == tk.NORMAL
        app.a16_control_buttons["start"].invoke()
        report = app._latest_autonomy_16_report()
        assert report["final_mission_disposition"] == "partially_completed"
        app.a16_control_buttons["current"].invoke()
        app.a16_control_buttons["blocked"].invoke()
        app.a16_control_buttons["evidence"].invoke()
        app.a16_control_buttons["limits"].invoke()
        app.a16_control_buttons["graph"].invoke()
        app.chat_input.delete(0, tk.END)
        app.chat_input.insert(0, "show mission limits")
        app._send_chat()
        assert str(app.a16_control_buttons["start"]["state"]) == tk.DISABLED
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
