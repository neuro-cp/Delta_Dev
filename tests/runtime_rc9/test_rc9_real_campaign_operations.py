from __future__ import annotations

import json

from orchestration.runtime.rc9_real_campaign_operations import (
    EVIDENCE_CLASSES,
    SESSION_STATES,
    assess_continuation,
    build_campaign_dashboard,
    build_session,
    campaign_continuity_benchmark,
    campaign_trials,
    export_campaign_history,
    operator_campaign_readiness_report,
    real_campaign_foundation_report,
    safety_metadata,
    write_reports,
)


def test_rc9_session_model_supports_required_lifecycle_states():
    assert {"started", "paused", "resumed", "deferred", "cancelled", "abandoned", "superseded", "completed"}.issubset(SESSION_STATES)
    session = build_session("pause_resume", status="resumed", interruption_reason="operator_break")
    assert session.resume_token is not None
    assert session.interruption is not None
    assert session.state.status == "resumed"


def test_rc9_campaign_trials_cover_realistic_operator_cases():
    trials = campaign_trials()
    expected = {
        "accepted_hypothesis",
        "rejected_hypothesis",
        "deferred_hypothesis",
        "abandoned_campaign",
        "resumed_campaign",
        "changed_goal",
        "failed_implementation",
        "improvement_with_regression",
        "useful_external_advice",
        "unsafe_external_advice",
        "retrieval_blocked",
        "retrieval_useful",
        "operator_workload_overload",
    }
    assert expected.issubset(trials)
    assert trials["cancelled_campaign"].continuation.decision == "STOP_OPERATOR_CANCELLED"
    assert "operator_workload_excessive" in trials["operator_workload_overload"].continuation.reasons


def test_rc9_evidence_classes_are_visible_and_not_merged():
    session = build_session("provider_advice", evidence_class="PROVIDER_ADVISORY_EVIDENCE")
    assert session.evidence[0].evidence_class == "PROVIDER_ADVISORY_EVIDENCE"
    assert set(EVIDENCE_CLASSES).issuperset({session.evidence[0].evidence_class, "REAL_OPERATOR_EVIDENCE"})


def test_rc9_export_is_operator_controlled_and_report_only_by_default():
    session = build_session("export_case")
    default_export = export_campaign_history(session, operator_requested=False)
    explicit_export = export_campaign_history(session, operator_requested=True)
    assert default_export["export_performed"] is False
    assert explicit_export["export_performed"] is True
    assert explicit_export["automatic_canonical_write"] is False


def test_rc9_dashboard_exposes_campaign_workflow_without_authority():
    dashboard = build_campaign_dashboard(build_session("dashboard_case"))
    assert dashboard["implementation"] == "proposal_only"
    assert dashboard["authority"] == "operator_governed_shadow_or_report_only"
    assert dashboard["evidence_class"]


def test_rc9_reports_pass_and_are_json_serializable():
    foundation = real_campaign_foundation_report()
    continuity = campaign_continuity_benchmark()
    readiness = operator_campaign_readiness_report()
    assert foundation["passed"] is True
    assert continuity["passed"] is True
    assert readiness["recommendation"] == "RC9_READY_FOR_REAL_OPERATOR_DEVELOPMENTAL_CAMPAIGNS"
    assert readiness["real_operator_campaign_evidence"] == "not_yet_collected_by_fixtures"
    assert safety_metadata()["autonomous_campaign_started"] is False
    json.dumps(foundation)
    json.dumps(continuity)
    json.dumps(readiness)
    json.dumps(write_reports())
