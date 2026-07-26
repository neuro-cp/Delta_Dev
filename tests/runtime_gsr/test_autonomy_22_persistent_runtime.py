from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_persistent_runtime import run_persistent_runtime
from tests.runtime_gsr.test_autonomy_13_task_scoped_activation import _competence_roots
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager


if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def _admission_roots(tmp_path: Path):
    cycle_1, cycle_2 = _competence_roots(tmp_path)
    return cycle_1, cycle_2


def test_a22_runs_integrated_terminal_persistent_runtime(tmp_path):
    roots = _admission_roots(tmp_path)
    result = run_persistent_runtime(tmp_path / "runtime", competence_roots=roots, admission_roots=roots)
    restart = run_persistent_runtime(tmp_path / "runtime", competence_roots=roots, admission_roots=roots, mode="restart")
    summary = result["summary"]
    assert result["status"] == "AUTONOMY_22_PERSISTENT_GOVERNED_DEVELOPMENT_RUNTIME_PASSED"
    assert result["final_disposition"] == "persistent_runtime_with_bounded_limitations"
    assert summary["one_active_task_maximum"] is True
    assert summary["one_active_development_goal_maximum"] is True
    assert summary["blocked_branch_does_not_freeze_independent_work"] is True
    assert summary["governance_kernel_contract"]["architecture_rule"] == "models_propose_and_interpret_code_constrains_executes_records_and_verifies"
    assert summary["trajectory_alignment"]["future_capabilities_should_be_specs_over_primitives"] is True
    assert restart["duplicate_suppressed"] is True


def test_a22_audits_checkpoint_narration_and_authority(tmp_path):
    roots = _admission_roots(tmp_path)
    run_persistent_runtime(tmp_path / "runtime", competence_roots=roots, admission_roots=roots)
    import json

    checkpoint = json.loads((tmp_path / "runtime" / "checkpoint_audit.json").read_text(encoding="utf-8"))
    narration = json.loads((tmp_path / "runtime" / "narration_audit.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "runtime" / "final_runtime_summary.json").read_text(encoding="utf-8"))
    assert checkpoint["prepared_not_applied_recovery"] is True
    assert checkpoint["duplicate_runner_rejection"] is True
    assert narration["all_events_bound"] is True
    assert narration["duplicate_narration"] is False
    assert summary["provider_calls"] == 0
    assert summary["network_calls"] == 0
    assert summary["primary_source_mutation"] is False


def test_a22_maintenance_changes_later_activation_eligibility(tmp_path):
    roots = _admission_roots(tmp_path)
    run_persistent_runtime(tmp_path / "runtime", competence_roots=roots, admission_roots=roots)
    import json

    activation = json.loads((tmp_path / "runtime" / "activation_audit.json").read_text(encoding="utf-8"))
    health = json.loads((tmp_path / "runtime" / "competence_health_audit.json").read_text(encoding="utf-8"))
    assert activation["suspended_competence_rejects"] is True
    assert health["revoked_blocks_future_activation"] is True


def test_a22_duplicate_runner_and_terminal_replay_suppression(tmp_path):
    roots = _admission_roots(tmp_path)
    duplicate = run_persistent_runtime(tmp_path / "runtime", competence_roots=roots, admission_roots=roots, mode="duplicate_runner")
    assert duplicate["status"] == "duplicate_runner_rejected"
    result = run_persistent_runtime(tmp_path / "runtime2", competence_roots=roots, admission_roots=roots)
    replay = run_persistent_runtime(tmp_path / "runtime2", competence_roots=roots, admission_roots=roots)
    assert result["status"] == replay["status"]
    assert replay["duplicate_suppressed"] is True


def test_tk_a22_visible_control_bindings(monkeypatch, tmp_path):
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
        app.a13_control_buttons["use"].invoke()
        app.a14_control_buttons["start"].invoke()
        app.a14_control_buttons["resume"].invoke()
        app.a16_control_buttons["pause"].invoke()
        app.a16_control_buttons["resume"].invoke()
        app.a16_control_buttons["stop"].invoke()
        app.operator_ux_root = tmp_path / "operator-ux-2"
        app._refresh_operator_ux_views()
        app.a16_control_buttons["start"].invoke()
        app.a16_control_buttons["current"].invoke()
        app.a16_control_buttons["blocked"].invoke()
        app.a16_control_buttons["evidence"].invoke()
        app.a16_control_buttons["limits"].invoke()
        app.a17_control_buttons["acquire"].invoke()
        app.a18_control_buttons["request"].invoke()
        app.a18_control_buttons["explain"].invoke()
        app.a21_control_buttons["explain"].invoke()
        assert app._latest_autonomy_18_report()["status"] == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
