from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_safety_closure import (
    RUNTIME_V14W_INVARIANT_FLAGS,
    V14ClosureOutcome,
    create_v14_capability_status,
    create_v14_closure_decision,
    create_v14_closure_report_entry,
    create_v14_phase_summary,
    create_v14_safety_invariant_snapshot,
    create_v14_test_suite_summary,
    validate_closure_report_only,
    V14CapabilityState,
)
from orchestration.runtime.v14_safety_closure_report import build_v14_safety_closure_report_data, write_v14_safety_closure_report


def test_closure_objects_are_deterministic_and_report_only():
    phase = create_v14_phase_summary(
        phase_id="V1.4W",
        phase_name="closure",
        capability_summary="report only",
        report_paths=("report.md",),
        status=V14CapabilityState.REPORT_ONLY,
    )
    duplicate = create_v14_phase_summary(
        phase_id="V1.4W",
        phase_name="closure",
        capability_summary="report only",
        report_paths=("report.md",),
        status=V14CapabilityState.REPORT_ONLY,
    )
    capability = create_v14_capability_status(capability_name="closure", state=V14CapabilityState.REPORT_ONLY)
    test_summary = create_v14_test_suite_summary(latest_count=285)
    entry = create_v14_closure_report_entry(phases=(phase,), capabilities=(capability,), test_summary=test_summary)
    snapshot = create_v14_safety_invariant_snapshot()
    decision = create_v14_closure_decision()
    assert phase.phase_id == duplicate.phase_id
    assert validate_closure_report_only(snapshot, decision, entry)


def test_closure_does_not_change_defaults_or_activate_hyb1(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V14W_INVARIANT_FLAGS["v14_closed"] is True
    assert RUNTIME_V14W_INVARIANT_FLAGS["hyb1_remains_dormant"] is True
    assert all(value is False for key, value in RUNTIME_V14W_INVARIANT_FLAGS.items() if key not in {"v14_closed", "hyb1_remains_dormant"})


def test_closure_decision_recommends_v15a_without_promotion():
    decision = create_v14_closure_decision()
    assert decision.outcome == V14ClosureOutcome.PROCEED_V15A
    assert decision.final_recommendation == "PROCEED_V15A_INTEGRATION_GATE_DESIGN"
    assert decision.applied is False
    assert decision.promoted_hyb1 is False
    assert decision.activated_runtime is False
    assert decision.changed_defaults is False


def test_report_data_summarizes_all_required_phases_and_inactive_systems():
    data = build_v14_safety_closure_report_data(latest_test_count=285)
    assert data["final_recommendation"] == "PROCEED_V15A_INTEGRATION_GATE_DESIGN"
    assert len(data["phase_summaries"]) >= 24
    assert data["safety_snapshot"]["model_b_default"] == "unchanged"
    assert data["safety_snapshot"]["hyb1_status"] == "dormant/env-gated"
    assert data["closure_decision"]["promoted_hyb1"] is False
    assert data["closure_decision"]["activated_runtime"] is False
    assert data["test_summary"]["last_verified_count"] == 285
    assert "live integration" in data["inactive_systems"]


def test_write_v14_safety_closure_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_safety_closure_report as report_module

    md_path = tmp_path / "closure.md"
    json_path = tmp_path / "closure.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)
    data = write_v14_safety_closure_report(latest_test_count=285)
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8").lower()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "report-only closure" in text
    assert "proceed to v1.5a" in text
