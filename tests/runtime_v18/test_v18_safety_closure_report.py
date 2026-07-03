from __future__ import annotations

from orchestration.runtime.v18_safety_closure_report import build_safety_closure_report, validate_safety_closure_report, write_safety_closure_report


def test_closure_report_contains_completed_phases():
    data = build_safety_closure_report()
    phases = [phase["phase"] for phase in data["completed_phases"]]
    assert phases == ["V1.7E", "V1.7F", "V1.7G", "V1.7H", "V1.8A", "V1.8B"]
    assert validate_safety_closure_report(data)


def test_pipeline_view_is_present():
    data = build_safety_closure_report()
    assert "PROVIDER / SPECIALIST EVIDENCE REVIEW UI" in data["pipeline_view"]
    assert "PROMOTION READINESS SCORECARD" in data["pipeline_view"]
    assert len(data["pipeline_view"]) >= 40


def test_safety_invariants_remain_false():
    data = build_safety_closure_report()
    assert all(value is False for value in data["safety_invariants"].values())


def test_report_generation():
    data = write_safety_closure_report()
    assert data["final_recommendation"] == "PROCEED_LOCAL_REVIEW_UI_ITERATION_OR_MANUAL_PROVIDER_LIVE_TRIAL"
    assert validate_safety_closure_report(data)
