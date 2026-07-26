from __future__ import annotations

import copy
import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_advisory_assistance import (
    create_advisory_request,
    deterministic_advisory_output,
    request_bounded_advice,
    validate_advisory_output,
)
from orchestration.runtime.autonomy_governed_primitives import KERNEL_PRIMITIVES
from orchestration.runtime.autonomy_local_evidence import acquire_local_evidence, select_real_gap
from orchestration.runtime.autonomy_mixed_mission import run_mixed_mission
from tests.runtime_gsr.test_autonomy_13_task_scoped_activation import _competence_roots
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager


if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def _packet(tmp_path: Path) -> dict[str, object]:
    roots = _competence_roots(tmp_path)
    mission_root = tmp_path / "mission"
    run_mixed_mission(mission_root, competence_roots=roots)
    gap = select_real_gap(mission_root / "gaps")
    return acquire_local_evidence(tmp_path / "a17", gap=gap)["packet"]


def test_a18_request_binds_packet_and_accepts_grounded_advice(tmp_path):
    packet = _packet(tmp_path)
    result = request_bounded_advice(tmp_path / "a18", packet=packet)
    restart = request_bounded_advice(tmp_path / "a18", packet=packet)
    request = result["request"]
    output = result["advisory_output"]
    audit = result["grounding_audit"]
    assert result["status"] == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"
    assert request["a17_packet_digest"] == packet["artifact_digest"]
    assert request["advisory_mode"] == "recorded_advisory_packet"
    assert request["governance_kernel_contract"]["kernel_primitives"] == KERNEL_PRIMITIVES
    assert request["model_role"] == "interpret_and_propose_only"
    assert request["call_budget"] == request["token_budget"] == 0
    assert output["cognitive_role"] == "diagnosis_path_and_evaluator_proposal"
    assert output["deterministic_runtime_validated"] is True
    assert output["admits_competence"] is False
    assert output["grants_authority"] is False
    assert output["mutates_source"] is False
    assert audit["accepted"] is True
    assert audit["cognitive_proposal_contract"]["accepted"] is True
    assert restart["status"] == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP"
    assert restart["reason"] == "blocked_already_consumed"


def test_a18_grounding_rejects_bad_outputs(tmp_path):
    packet = _packet(tmp_path)
    request = create_advisory_request(packet, output_root=tmp_path / "a18")
    output = deterministic_advisory_output(request, packet)
    cases = []
    bad = copy.deepcopy(output)
    bad["referenced_existing_paths"] = ("orchestration/runtime/not_real.py",)
    cases.append(("invented_source_path_rejected", bad))
    bad = copy.deepcopy(output)
    bad["referenced_existing_paths"] = ("DELTA-75/secret.txt",)
    cases.append(("prohibited_path_rejected", bad))
    bad = copy.deepcopy(output)
    bad["modifies_evaluator_threshold"] = True
    cases.append(("modifies_evaluator_threshold_rejected", bad))
    bad = copy.deepcopy(output)
    bad["declares_success"] = True
    cases.append(("declares_success_rejected", bad))
    bad = copy.deepcopy(output)
    bad["requests_network"] = True
    cases.append(("requests_network_rejected", bad))
    bad = copy.deepcopy(output)
    bad["requests_provider"] = True
    cases.append(("requests_provider_rejected", bad))
    bad = copy.deepcopy(output)
    bad["schema"] = "wrong_schema"
    cases.append(("malformed_output_rejected", bad))
    bad = copy.deepcopy(output)
    bad["contradictions_acknowledged"] = False
    cases.append(("unacknowledged_contradiction_rejected", bad))
    bad = copy.deepcopy(output)
    bad["hidden_expected_outputs"] = ("case answer",)
    cases.append(("hidden_answer_use_rejected", bad))
    bad = copy.deepcopy(output)
    bad["mutates_source"] = True
    cases.append(("mutates_source_rejected", bad))
    for reason, payload in cases:
        audit = validate_advisory_output(payload, request, packet)
        assert reason in audit["reasons"]


def test_a18_duplicate_identity_and_no_external_authority(tmp_path):
    packet = _packet(tmp_path)
    request = create_advisory_request(packet, output_root=tmp_path / "a18")
    output = deterministic_advisory_output(request, packet)
    audit = validate_advisory_output(output, request, packet, seen_digests=(output["artifact_digest"],))
    assert "duplicate_advice_suppressed" in audit["reasons"]
    assert audit["provider_calls"] == 0
    assert audit["network_calls"] == 0
    assert audit["deployment"] is False
    assert audit["credentials"] is False
    assert audit["source_mutation"] is False


def test_a18_replay_requires_grounded_prior_report(tmp_path):
    output_root = tmp_path / "a18"
    output_root.mkdir()
    (output_root / "advisory_output.json").write_text('{"schema":"autonomy_18_advisory_output_v1","artifact_digest":"bad"}', encoding="utf-8")
    (output_root / "grounding_audit.json").write_text('{"accepted":false}', encoding="utf-8")
    (output_root / "report.json").write_text('{"status":"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_FAILED"}', encoding="utf-8")
    result = request_bounded_advice(output_root)
    assert result["status"] == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP"
    assert result["reason"] == "existing_advisory_not_grounded"


def test_a18_rejects_a19_work_and_keeps_advice_untrusted(tmp_path):
    packet = _packet(tmp_path)
    result = request_bounded_advice(tmp_path / "a18", packet=packet)
    report = result["report"]
    assert report["advisory_remains_untrusted"] is True
    assert report["a19_started"] is False
    assert "no competence admitted" in result["advisory_output"]["limitations"]


def test_tk_a18_advisory_controls_and_chat_intents(monkeypatch, tmp_path):
    cycle_1, cycle_2 = _competence_roots(tmp_path)
    run_mixed_mission(tmp_path / ".tmp" / "autonomy-16-mixed-mission", competence_roots=(cycle_1, cycle_2))
    packet = acquire_local_evidence(tmp_path / "operator-ux" / "a17_evidence", gap=select_real_gap(tmp_path / ".tmp" / "autonomy-16-mixed-mission" / "gaps"))["packet"]
    assert packet["development_execution_started"] is False
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
        assert str(app.a18_control_buttons["request"]["state"]) == tk.NORMAL
        app.a18_control_buttons["request"].invoke()
        assert app._latest_autonomy_18_report()["status"] == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"
        for action in ("explain", "grounding", "rejected", "limits", "keep", "reject"):
            app.a18_control_buttons[action].invoke()
        app.chat_input.delete(0, tk.END)
        app.chat_input.insert(0, "view advisory grounding")
        app._send_chat()
        assert str(app.a18_control_buttons["request"]["state"]) == tk.DISABLED
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
