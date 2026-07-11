from __future__ import annotations

import json

from orchestration.runtime.rc10_specialist_cognition import (
    SPECIALIST_NAMES,
    build_specialist_profiles,
    detect_specialist_conflicts,
    render_recommendation,
    safety_metadata,
    select_specialists,
    specialist_foundation_report,
    specialist_portfolio_readiness_report,
    specialist_selection_benchmark,
    synthesize_portfolio,
    write_reports,
)


def test_rc10_profiles_are_complete_and_advisory_only():
    profiles = build_specialist_profiles()
    assert set(SPECIALIST_NAMES).issubset(profiles)
    assert all(profile.boundary.authority == "advisory_only" for profile in profiles.values())
    assert all(profile.boundary.operator_review_required for profile in profiles.values())
    assert all("commit" in profile.boundary.prohibited_authority for profile in profiles.values())


def test_rc10_selection_uses_task_need_without_invoking_every_specialist():
    selection = select_specialists("A credential redaction test failed and injection risk is unclear", risk="security")
    assert "security" in selection.selected
    assert "governance" in selection.selected
    assert len(selection.selected) < len(selection.considered)
    assert selection.context_mass <= 120


def test_rc10_operator_requested_specialist_gets_priority():
    selection = select_specialists("Review this design boundary", operator_requested=("user_experience",))
    assert "user_experience" in selection.selected


def test_rc10_recommendations_and_conflicts_remain_advisory():
    security = render_recommendation("security", "Make warning less confusing without reducing safety")
    ux = render_recommendation("user_experience", "Make warning less confusing without reducing safety")
    conflicts = detect_specialist_conflicts((security, ux))
    assert security.authority == "advisory_only"
    assert conflicts
    assert "majority vote" in conflicts[0].resolution_policy


def test_rc10_portfolio_synthesis_requires_operator_review():
    portfolio = synthesize_portfolio("Improve UI wording while preserving injection safety", risk="security")
    assert portfolio["authority"] == "advisory_only"
    assert portfolio["operator_review_required"] is True
    assert portfolio["recommendations"]


def test_rc10_reports_pass_and_are_json_serializable():
    foundation = specialist_foundation_report()
    selection = specialist_selection_benchmark()
    readiness = specialist_portfolio_readiness_report()
    assert foundation["passed"] is True
    assert selection["passed"] is True
    assert readiness["recommendation"] == "RC10_READY_FOR_GOVERNED_SPECIALIST_SHADOW_USE"
    assert safety_metadata()["specialist_authority_granted"] is False
    json.dumps(foundation)
    json.dumps(selection)
    json.dumps(readiness)
    json.dumps(write_reports())
