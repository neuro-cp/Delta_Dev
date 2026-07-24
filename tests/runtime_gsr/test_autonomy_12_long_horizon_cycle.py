from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_goal_queue_planning import approve_plan_for_future_execution, compile_plan_proposal, normalize_plan_feedback
from orchestration.runtime.autonomy_long_horizon_cycle import run_long_horizon_cycle
from tests.runtime_gsr.test_autonomy_3_goal_queue_planning import _queued
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager

if sys.platform == "win32":
    tcl_root = Path(os.environ.get("TCL_LIBRARY", Path(sys.base_prefix) / "tcl" / "tcl8.6")).parent
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def test_a12_complete_cycle_artifacts_and_restart_exactness(tmp_path):
    result = run_long_horizon_cycle(output_root=tmp_path / "a12", a11_repair_report=tmp_path / "repair.json")
    restart = run_long_horizon_cycle(output_root=tmp_path / "a12", a11_repair_report=tmp_path / "repair.json")
    report = result["report"]

    assert result["status"] == "AUTONOMY_12_LONG_HORIZON_GOVERNED_CYCLE_PASSED"
    assert restart["duplicate_suppressed"] is True
    assert report["selected_goal"]["condition_key"] == "missing_or_unreliable_identifier_reconciliation"
    assert report["authority"]["provider_calls"] == 0
    assert report["authority"]["tracked_source_mutation"] is False
    assert report["evaluator"]["sealed_before_strategy"] is True
    assert report["revision"]["revision_count"] <= 1
    assert report["outcome_review"]["disposition"] == "candidate_for_competence_admission_review"
    assert report["competence_disposition"]["status"] == "accepted_bounded_competence"
    assert report["competence_disposition"]["activation_state"] == "admitted_inactive_pending_future_use"
    assert report["next_candidate"]["condition_key"] == "transfer_beyond_retained_fixture_families"
    assert report["next_candidate_executed"] is False
    assert report["provider_calls"] == 0
    assert report["network_calls"] == 0
    assert report["primary_tracked_source_mutation"] is False
    assert report["second_goal_execution"] is False
    assert len(tuple((tmp_path / "a12" / "final_reports").glob("*.json"))) == 1


def test_tk_a12_visible_controls_exercise_governed_handlers(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "ProviderManager", _DummyProviderManager)
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
        goal = _queued()
        plan = compile_plan_proposal(goal)
        approval = approve_plan_for_future_execution(plan, normalize_plan_feedback("looks good"))
        (app.operator_ux_root / "autonomy_3_plans").mkdir(parents=True, exist_ok=True)
        (app.operator_ux_root / "autonomy_3_plan_approvals").mkdir(parents=True, exist_ok=True)
        (app.operator_ux_root / "autonomy_3_plans" / f"{plan['plan_id']}.json").write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
        (app.operator_ux_root / "autonomy_3_plan_approvals" / f"{approval['approval_id']}.json").write_text(json.dumps(approval, sort_keys=True), encoding="utf-8")
        app._refresh_operator_ux_views()
        app.a4_control_buttons["start"].invoke()
        app.a4_control_buttons["evidence"].invoke()
        app.a5_control_buttons["review"].invoke()
        app.a6_control_buttons["review"].invoke()
        app.a6_control_buttons["admit"].invoke()
        assert tuple((app.operator_ux_root / "autonomy_6_competence_admission" / "accepted_competencies").glob("*.json"))
        assert app.a4_execution_status.get() == "A4: completed"
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
