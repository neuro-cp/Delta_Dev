from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_competence_maintenance import load_admission_inventory, resolve_effective_inventory, run_competence_maintenance
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager


if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def test_a21_creates_immutable_maintenance_inventory(tmp_path):
    result = run_competence_maintenance(tmp_path / "maintenance")
    restart = run_competence_maintenance(tmp_path / "maintenance")
    report = result["report"]
    assert result["status"] == "AUTONOMY_21_COMPETENCE_MAINTENANCE_PASSED"
    assert report["admissions_rewritten"] is False
    assert report["silent_deletion"] is False
    assert len(report["maintenance_events"]) >= 5
    assert restart["duplicate_suppressed"] is True


def test_a21_effective_state_resolution_preserves_precedence(tmp_path):
    result = run_competence_maintenance(tmp_path / "maintenance")
    states = {item["effective_state"] for item in result["after"]["effective_inventory"]}
    assert "narrowed" in states
    assert "revoked" in states
    assert "accepted_bounded_competence" not in states or len(states) >= 2


def test_a21_activation_and_composition_restrictions(tmp_path):
    report = run_competence_maintenance(tmp_path / "maintenance")["report"]
    activation = report["activation_restriction_audit"]
    composition = report["composition_restriction_audit"]
    assert activation["reevaluation_due_restricts_activation"] is True
    assert activation["suspended_blocks_activation"] is True
    assert activation["revoked_blocks_future_activation"] is True
    assert composition["suspended_or_revoked_blocks_dependent_composition"] is True
    assert composition["narrowed_composes_only_supported_clauses"] is True


def test_a21_no_authority_expansion_or_overwrite(tmp_path):
    report = run_competence_maintenance(tmp_path / "maintenance")["report"]
    assert report["authority_expansion"] is False
    for event in report["maintenance_events"]:
        assert event["authority_expansion"] is False
        assert event["operator_authority_requirement"] == "operator_review_required_for_restore_or_reactivation"


def test_a21_can_resolve_from_custom_admission_and_events():
    admissions = load_admission_inventory()
    event = {"competence_id": admissions[0]["competence_id"], "new_effective_state": "suspended", "maintenance_record_id": "event"}
    resolved = resolve_effective_inventory((admissions[0],), (event,))
    assert resolved[0]["effective_state"] == "suspended"
    assert resolved[0]["immutable_admission_preserved"] is True


def test_tk_a21_competence_health_controls(monkeypatch, tmp_path):
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
        app._refresh_operator_ux_views()
        for action in ("explain", "evidence", "tasks", "reevaluate", "suspend", "restore"):
            assert str(app.a21_control_buttons[action]["state"]) == tk.NORMAL
            app.a21_control_buttons[action].invoke()
        assert app._latest_autonomy_21_report()["status"] == "AUTONOMY_21_COMPETENCE_MAINTENANCE_PASSED"
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
