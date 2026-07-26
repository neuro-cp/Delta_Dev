from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_capability_composition import (
    COMPOSITION_FAMILY,
    COMPOSITION_STATUS_INTEGRITY_STOP,
    COMPOSITION_STATUS_PASSED,
    create_composition_request,
    run_capability_composition,
    supported_composition_families,
)
from orchestration.runtime.autonomy_cycle_families import JSON_FAMILY, RECONCILIATION_FAMILY
from tests.runtime_gsr.test_autonomy_13_task_scoped_activation import _competence_roots
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager


if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def test_a14_supported_family_and_unsupported_family(tmp_path):
    families = supported_composition_families()
    assert families[0]["composition_family"] == COMPOSITION_FAMILY
    assert families[0]["ordered_stage_families"] == (JSON_FAMILY, RECONCILIATION_FAMILY)
    unsupported = create_composition_request(tmp_path / "bad", family="unsupported_third_competence")
    assert unsupported["status"] == "unsupported_composition_family"


def test_a14_valid_composition_pause_restart_and_terminal_replay(tmp_path):
    roots = _competence_roots(tmp_path)
    root = tmp_path / "a14"
    paused = run_capability_composition(root, competence_roots=roots, pause_after_stage_1=True)
    assert paused["status"] == "paused_operator"
    assert paused["composition_result"]["stage_1"]["semantic_execution_count"] == 1
    resumed = run_capability_composition(root, competence_roots=roots, resume=True)
    replay = run_capability_composition(root, competence_roots=roots)
    assert resumed["status"] == COMPOSITION_STATUS_PASSED
    assert replay["duplicate_suppressed"] is True
    result = resumed["composition_result"]
    assert result["stage_1"]["semantic_execution_count"] == 1
    assert result["stage_2"]["semantic_execution_count"] == 1
    assert result["stage_2"]["stage_2_input_digest"] == result["stage_1"]["validated_output_digest"]
    assert result["global_activation"] is False
    assert result["provider_calls"] == 0


def test_a14_stage_1_failures_block_stage_2(tmp_path):
    roots = _competence_roots(tmp_path)
    for scenario, reason in (
        ("malformed", "malformed_json"),
        ("unsupported_schema", "unsupported_schema_version"),
        ("missing_provenance", "missing_provenance"),
        ("ineligible_schema", "reconciliation_ineligible_output_schema"),
    ):
        result = run_capability_composition(tmp_path / scenario, competence_roots=roots, scenario=scenario)
        assert result["status"] == "stage_2_blocked"
        assert result["composition_result"]["stage_2"] is None
        assert result["composition_result"]["blocked_reason"] == reason


def test_a14_integrity_counterfactuals(tmp_path):
    roots = _competence_roots(tmp_path)
    assert run_capability_composition(tmp_path / "reverse", competence_roots=roots, reverse_order=True)["status"] == COMPOSITION_STATUS_INTEGRITY_STOP
    assert run_capability_composition(tmp_path / "tamper", competence_roots=roots, tamper_stage_1=True)["status"] == COMPOSITION_STATUS_INTEGRITY_STOP
    assert run_capability_composition(tmp_path / "eval", competence_roots=roots, mutate_evaluator=True)["status"] == COMPOSITION_STATUS_INTEGRITY_STOP


def test_a14_stop_and_stage_2_blockers_preserve_stage_1(tmp_path):
    roots = _competence_roots(tmp_path)
    stopped = run_capability_composition(tmp_path / "stop", competence_roots=roots, stop_after_stage_1=True)
    assert stopped["status"] == "stopped_by_operator"
    assert stopped["composition_result"]["stage_2"] is None
    replay = run_capability_composition(tmp_path / "stop", competence_roots=roots, resume=True)
    assert replay["duplicate_suppressed"] is True
    expired = run_capability_composition(tmp_path / "expired", competence_roots=roots, expire_stage_2=True)
    suspended = run_capability_composition(tmp_path / "suspended", competence_roots=roots, suspended_stage_2=True)
    assert expired["composition_result"]["blocked_reason"] == "activation_expired"
    assert suspended["composition_result"]["blocked_reason"] == "competence_suspended"


def test_tk_a14_composition_controls_and_chat_intents(monkeypatch, tmp_path):
    cycle_1, cycle_2 = _competence_roots(tmp_path)
    retained_1 = tmp_path / ".tmp" / "autonomy-12r-final-cycle-1" / "a6_admission"
    retained_2 = tmp_path / ".tmp" / "autonomy-12r-final-cycle-2" / "a6_admission"
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
        assert str(app.a14_control_buttons["start"]["state"]) == tk.NORMAL
        app.a14_control_buttons["start"].invoke()
        paused = app._latest_autonomy_14_result()
        assert paused["status"] == "paused_operator"
        assert str(app.a14_control_buttons["resume"]["state"]) == tk.NORMAL
        app.a14_control_buttons["evidence"].invoke()
        app.a14_control_buttons["provenance"].invoke()
        app.a14_control_buttons["limits"].invoke()
        app.a14_control_buttons["resume"].invoke()
        completed = app._latest_autonomy_14_result()
        assert completed["status"] == COMPOSITION_STATUS_PASSED
        app.chat_input.delete(0, tk.END)
        app.chat_input.insert(0, "show composition limits")
        app._send_chat()
        assert str(app.a14_control_buttons["start"]["state"]) == tk.DISABLED
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
