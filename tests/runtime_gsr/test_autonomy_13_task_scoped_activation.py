from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_cycle_families import JSON_FAMILY, JSON_TASK_CLASS, RECONCILIATION_FAMILY
from orchestration.runtime.autonomy_long_horizon_cycle import run_long_horizon_cycle
from orchestration.runtime.autonomy_task_activation import (
    execute_task_activation,
    fresh_task_contract,
    issue_task_activation,
    run_task_scoped_activation,
    select_task_competence,
)
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager


if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def _competence_roots(tmp_path: Path) -> tuple[Path, Path]:
    cycle_1 = tmp_path / "cycle-1"
    cycle_2 = tmp_path / "cycle-2"
    assert run_long_horizon_cycle(output_root=cycle_1, cycle_family=RECONCILIATION_FAMILY)["status"] == "AUTONOMY_12_LONG_HORIZON_GOVERNED_CYCLE_PASSED"
    assert run_long_horizon_cycle(output_root=cycle_2, cycle_family=JSON_FAMILY)["status"] == "AUTONOMY_12_LONG_HORIZON_GOVERNED_CYCLE_PASSED"
    return cycle_1 / "a6_admission", cycle_2 / "a6_admission"


def test_a13_runs_two_fresh_task_scoped_pilots_without_global_activation(tmp_path):
    result = run_task_scoped_activation(tmp_path / "a13", competence_roots=_competence_roots(tmp_path))
    restart = run_task_scoped_activation(tmp_path / "a13", competence_roots=_competence_roots(tmp_path))

    assert result["status"] == "AUTONOMY_13_TASK_SCOPED_CAPABILITY_ACTIVATION_PASSED"
    assert restart["duplicate_suppressed"] is True
    assert result["report"]["global_activation"] is False
    assert {pilot["task"]["task_class"] for pilot in result["report"]["pilots"]} == {
        "bounded_cross_format_record_reconciliation",
        JSON_TASK_CLASS,
    }
    assert all(pilot["activation"]["activation_status"] == "activation_completed" for pilot in result["report"]["pilots"])
    assert all(pilot["execution_result"]["semantic_execution_count"] == 1 for pilot in result["report"]["pilots"])
    assert all(pilot["execution_result"]["evaluator_grades_actual_output"] for pilot in result["report"]["pilots"])
    assert all(pilot["wrong_competence_rejected"] for pilot in result["report"]["pilots"])
    assert all(pilot["unsupported_schema_rejected"] for pilot in result["report"]["pilots"])


def test_a13_rejects_wrong_competence_unsupported_schema_and_expired_activation(tmp_path):
    result = run_task_scoped_activation(tmp_path / "a13", competence_roots=_competence_roots(tmp_path))
    competences = tuple(pilot["selection"]["selected_competence"] for pilot in result["report"]["pilots"])

    task = fresh_task_contract(JSON_TASK_CLASS, task_nonce="bad-schema", input_schema="unsupported_schema")
    rejected = select_task_competence(task, competences)
    assert rejected["status"] == "rejected"
    assert "input_schema_exact" in rejected["scope_match"]["failed_clauses"]

    active_task = fresh_task_contract(JSON_TASK_CLASS, task_nonce="expired")
    selected = select_task_competence(active_task, competences)
    expired = issue_task_activation(tmp_path / "expired", active_task, selected, expires_at="2026-07-24T00:00:00+00:00")
    output = execute_task_activation(tmp_path / "expired", active_task, expired)
    assert expired["activation_status"] == "activation_expired"
    assert output["semantic_execution_count"] == 0


def test_a13_duplicate_active_execution_rejected(tmp_path):
    result = run_task_scoped_activation(tmp_path / "a13", competence_roots=_competence_roots(tmp_path))
    competences = tuple(pilot["selection"]["selected_competence"] for pilot in result["report"]["pilots"])
    task = fresh_task_contract("bounded_cross_format_record_reconciliation", task_nonce="duplicate-active")
    selected = select_task_competence(task, competences)

    first = issue_task_activation(tmp_path / "active", task, selected)
    second = issue_task_activation(tmp_path / "active", task, selected)

    assert first["activation_status"] == "activated_for_task"
    assert second["activation_status"] == "activation_rejected"
    assert second["reason"] == "duplicate_active_execution"


def test_tk_a13_visible_controls_are_task_scoped(monkeypatch, tmp_path):
    cycle_1, cycle_2 = _competence_roots(tmp_path)
    retained_1 = tmp_path / ".tmp" / "autonomy-12r-final-cycle-1" / "a6_admission"
    retained_2 = tmp_path / ".tmp" / "autonomy-12r-final-cycle-2" / "a6_admission"
    retained_1.parent.mkdir(parents=True, exist_ok=True)
    retained_2.parent.mkdir(parents=True, exist_ok=True)
    for source, target in ((cycle_1, retained_1), (cycle_2, retained_2)):
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
        assert str(app.a13_control_buttons["use"]["state"]) == tk.NORMAL
        app.a13_control_buttons["use"].invoke()
        app.a13_control_buttons["fit"].invoke()
        app.a13_control_buttons["cannot"].invoke()
        app.a13_control_buttons["scope"].invoke()
        app.a13_control_buttons["expires"].invoke()
        app.a13_control_buttons["evaluation"].invoke()
        app.a13_control_buttons["stop"].invoke()
        report = app._latest_autonomy_13_report()
        assert report["status"] == "AUTONOMY_13_TASK_SCOPED_CAPABILITY_ACTIVATION_PASSED"
        assert report["global_activation"] is False
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
