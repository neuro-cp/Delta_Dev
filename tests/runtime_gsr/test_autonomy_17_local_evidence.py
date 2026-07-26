from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_local_evidence import acquire_local_evidence, detect_stale_packet, select_real_gap, validate_source_path
from tests.runtime_gsr.test_autonomy_13_task_scoped_activation import _competence_roots
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager
from orchestration.runtime.autonomy_mixed_mission import run_mixed_mission


if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def _gap(tmp_path: Path):
    roots = _competence_roots(tmp_path)
    run_mixed_mission(tmp_path / "mission", competence_roots=roots)
    return select_real_gap(tmp_path / "mission" / "gaps")


def test_a17_acquires_packet_for_real_gap_and_restart_suppresses_duplicate(tmp_path):
    gap = _gap(tmp_path)
    result = acquire_local_evidence(tmp_path / "a17", gap=gap)
    restart = acquire_local_evidence(tmp_path / "a17", gap=gap)
    packet = result["packet"]
    assert result["status"] == "AUTONOMY_17_GOVERNED_LOCAL_EVIDENCE_ACQUISITION_PASSED"
    assert restart["duplicate_suppressed"] is True
    assert packet["target_gap_id"] == gap["gap_id"]
    assert packet["gap_resolved"] is False
    assert packet["development_execution_started"] is False
    assert packet["source_paths"]
    assert packet["excerpts"]
    assert packet["missing_evidence"]
    assert packet["contradictory_evidence"][0]["status"] == "insufficient_context"


def test_a17_path_security_counterfactuals(tmp_path):
    allowed = (Path(".").resolve(),)
    assert "path_traversal_rejected" in validate_source_path("orchestration/../DELTA.py", allowed)["reasons"]
    assert validate_source_path("DELTA-75/secret.txt", allowed)["allowed"] is False
    assert validate_source_path("reports/RC4_bad.json", allowed)["allowed"] is False
    assert validate_source_path(".env", allowed)["allowed"] is False
    assert validate_source_path("image.bin", allowed)["allowed"] is False
    outside = tmp_path / "outside"
    outside.mkdir()
    inside = tmp_path / "inside"
    inside.mkdir()
    target = outside / "x.txt"
    target.write_text("x", encoding="utf-8")
    link = inside / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        return
    assert "symlink_escape_rejected" in validate_source_path(link, (inside,))["reasons"]


def test_a17_stale_detection_on_source_change(tmp_path):
    gap = _gap(tmp_path)
    result = acquire_local_evidence(tmp_path / "a17", gap=gap)
    packet = result["packet"]
    source = Path(packet["canonical_paths"][0])
    original = source.read_text(encoding="utf-8")
    try:
        source.write_text(original + "\n# disposable stale probe\n", encoding="utf-8")
        stale = detect_stale_packet(packet)
        assert stale["stale"] is True
    finally:
        source.write_text(original, encoding="utf-8")


def test_a17_no_relevant_evidence_and_budget_limits(tmp_path):
    gap = _gap(tmp_path)
    result = acquire_local_evidence(tmp_path / "a17", gap=gap)
    assert result["packet"]["bytes_read"] <= 60000
    assert result["packet"]["file_count"] <= 6
    assert len(result["packet"]["excerpts"]) <= 8


def test_tk_a17_evidence_controls_and_chat_intents(monkeypatch, tmp_path):
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
    run_mixed_mission(tmp_path / ".tmp" / "autonomy-16-mixed-mission", competence_roots=(cycle_1, cycle_2))
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
        assert str(app.a17_control_buttons["acquire"]["state"]) == tk.NORMAL
        app.a17_control_buttons["acquire"].invoke()
        packet = app._latest_autonomy_17_packet()
        assert packet["acquisition_disposition"] == "evidence_sufficient_for_planning"
        assert packet["gap_resolved"] is False
        for action in ("explain", "sources", "contradictions", "missing", "limits", "revalidate"):
            app.a17_control_buttons[action].invoke()
        assert (app.operator_ux_root / "a17_evidence" / "stale_evidence_audit.json").exists()
        app.chat_input.delete(0, tk.END)
        app.chat_input.insert(0, "show evidence limits")
        app._send_chat()
        assert str(app.a17_control_buttons["acquire"]["state"]) == tk.DISABLED
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
