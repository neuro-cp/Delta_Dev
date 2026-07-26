from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_gap_detection import classify_requirement, fresh_requirement, run_gap_detection
from tests.runtime_gsr.test_autonomy_13_task_scoped_activation import _competence_roots
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager


if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def test_a15_classifies_required_pilots_and_suppresses_duplicate_gap(tmp_path):
    result = run_gap_detection(tmp_path / "a15", competence_roots=_competence_roots(tmp_path))
    restart = run_gap_detection(tmp_path / "a15", competence_roots=_competence_roots(tmp_path))
    by_kind = {item["kind"]: item["requirement"]["classification"] for item in result["report"]["records"]}

    assert result["status"] == "AUTONOMY_15_DYNAMIC_CAPABILITY_GAP_DETECTION_PASSED"
    assert restart["duplicate_suppressed"] is True
    assert by_kind["reconciliation"] == "fully_supported"
    assert by_kind["json"] == "fully_supported"
    assert by_kind["composition"] == "composition_supported"
    assert by_kind["partial"] == "partially_supported"
    assert by_kind["unsupported"] == "unsupported"
    assert by_kind["prohibited"] == "prohibited"
    assert by_kind["ambiguous"] == "ambiguous_requirements"
    assert by_kind["wrong_family"] == "partially_supported"
    assert result["report"]["duplicate_gap_suppressed"] is True
    assert result["report"]["unsupported_task_executions"] == 0


def test_a15_clause_matching_does_not_use_task_title_alone(tmp_path):
    roots = _competence_roots(tmp_path)
    competences_result = run_gap_detection(tmp_path / "a15", competence_roots=roots)
    competences = tuple(item["selection"]["selected_competence"] for item in competences_result["report"].get("records", ()) if item.get("selection"))
    # Use runtime-loaded competences via a normal run; wrong-family remains partial, not supported.
    result = run_gap_detection(tmp_path / "again", competence_roots=roots)
    wrong = next(item["requirement"] for item in result["report"]["records"] if item["kind"] == "wrong_family")
    assert wrong["classification"] == "partially_supported"
    assert "input_schema" in wrong["missing_clauses"] or "output_schema" in wrong["missing_clauses"]
    assert competences == ()


def test_a15_prohibited_and_ambiguous_do_not_create_goals(tmp_path):
    result = run_gap_detection(tmp_path / "a15", competence_roots=_competence_roots(tmp_path))
    prohibited = next(item for item in result["report"]["records"] if item["kind"] == "prohibited")
    ambiguous = next(item for item in result["report"]["records"] if item["kind"] == "ambiguous")
    unsupported = next(item for item in result["report"]["records"] if item["kind"] == "unsupported")

    assert prohibited["gap"] is None
    assert ambiguous["gap"] is None
    assert unsupported["gap"]["development_goal_created"] is False


def test_tk_a15_support_card_controls(monkeypatch, tmp_path):
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
        assert str(app.a15_control_buttons["classify"]["state"]) == tk.NORMAL
        app.a15_control_buttons["classify"].invoke()
        report = app._latest_autonomy_15_report()
        assert report["status"] == "AUTONOMY_15_DYNAMIC_CAPABILITY_GAP_DETECTION_PASSED"
        app.a15_control_buttons["missing"].invoke()
        app.a15_control_buttons["explain"].invoke()
        app.a15_control_buttons["evidence"].invoke()
        app.a15_control_buttons["clarify"].invoke()
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
