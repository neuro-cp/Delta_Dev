from orchestration.runtime.delta_1_0_operator_pilot import (
    create_evidence,
    create_pilot_session,
    detect_contradictions,
    evaluate_evidence,
    observe_interaction,
    permission_profile,
    record_disposition,
)


def test_pilot_session_records_metrics_without_authority():
    session = create_pilot_session("review a low-risk proposal", mode="REVIEW_WORKFLOW")
    assert session.permission_profile.execute is False
    session = observe_interaction(
        session,
        "inspect report",
        "identified missing rollback evidence",
        route="report_review",
        useful=True,
        governance_preserved=True,
    )
    session = record_disposition(session, "proposal-1", "REJECT", "too broad")
    assert session.metrics["turns"] == 1.0
    assert session.metrics["usefulness"] == 1.0
    assert session.metrics["governance"] == 1.0
    assert session.dispositions[0].disposition == "REJECT"


def test_permission_profiles_fail_closed_for_observation():
    profile = permission_profile("OBSERVATION_ONLY")
    assert profile.observe is True
    assert profile.advise is False
    assert profile.execute is False


def test_evidence_summary_requires_operator_and_recovery_evidence():
    records = (
        create_evidence("UNIT_TEST", "capability", "works", "pass", source="pytest"),
    )
    summary = evaluate_evidence("capability", records)
    assert summary.recommendation == "NEEDS_MORE_EVIDENCE"
    assert "real_operator_disposition" in summary.missing_evidence
    assert "rollback_or_recovery_evidence" in summary.missing_evidence


def test_contradictory_evidence_is_detected():
    records = (
        create_evidence("UNIT_TEST", "capability", "works", "pass", source="a"),
        create_evidence("BENCHMARK", "capability", "works", "fail", source="b"),
    )
    assert detect_contradictions(records)


def test_chain_of_thought_artifacts_are_rejected():
    session = create_pilot_session("reject hidden rationale")
    try:
        observe_interaction(session, "x", "chain of thought: hidden", route="bad", useful=False)
    except ValueError as exc:
        assert "chain-of-thought" in str(exc)
    else:
        raise AssertionError("expected chain-of-thought rejection")
