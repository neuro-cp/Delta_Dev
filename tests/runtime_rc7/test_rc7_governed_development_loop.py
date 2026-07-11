from __future__ import annotations

import json

from orchestration.runtime.rc7_governed_development_loop import (
    benchmark_fixtures,
    build_cycle,
    build_history,
    build_operator_dashboard_snapshot,
    campaign_readiness_report,
    compare_behavior,
    development_loop_benchmark,
    developmental_corpus,
    operator_dashboard_report,
    render_operator_dashboard,
    safety_metadata,
    write_reports,
)


def test_rc7_safety_metadata_preserves_shadow_only_invariants():
    safety = safety_metadata()
    assert safety["automatic_code_modification_performed"] is False
    assert safety["automatic_approval_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["persistent_memory_write_performed"] is False
    assert safety["campaign_execution_performed"] is False


def test_development_cycle_contains_required_state_objects():
    cycle = build_cycle("summary_accounting")
    assert cycle.deficit.description == "summary accounting"
    assert cycle.hypothesis.deficit_id == cycle.deficit.deficit_id
    assert cycle.consultation.provider_call_performed is False
    assert cycle.proposal.operator_approval_required is True
    assert cycle.proposal.executable is False
    assert cycle.validation.passed is True
    assert cycle.comparison.recommendation == "RETAIN_AFTER_OPERATOR_REVIEW"
    assert cycle.disposition.decision == "accepted"


def test_comparative_evaluation_rejects_regressions():
    cycle = build_cycle("regression_case", validation_passed=False, regressions=("routing_regression",), decision="rejected")
    comparison = compare_behavior(
        cycle.proposal,
        old_behavior="old behavior worked",
        new_behavior="new behavior regressed",
        benefits=("narrow metric improved",),
        regressions=("routing_regression",),
        operator_workload_delta=0.1,
    )
    assert comparison.recommendation == "REJECT_OR_REVISE"


def test_campaign_fixtures_cover_long_horizon_cases():
    fixtures = benchmark_fixtures()
    expected = {
        "single_improvement",
        "multiple_improvements",
        "regression",
        "repeated_failure",
        "deferred_hypothesis",
        "rejected_proposal",
        "successful_campaign",
        "abandoned_campaign",
        "mixed_campaign",
        "interrupted_campaign",
        "resume_later",
        "campaign_completion",
        "campaign_cancellation",
    }
    assert expected.issubset(fixtures.keys())
    assert fixtures["repeated_failure"].health.stop_required is True
    assert fixtures["successful_campaign"].summary.recommendation == "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS"


def test_development_history_is_shadow_only_and_conversation_scoped_shape():
    campaign = benchmark_fixtures()["successful_campaign"]
    history = build_history(campaign.cycles)
    assert len(history) == len(campaign.cycles)
    assert all(record.disposition == "accepted" for record in history)
    assert all(record.outcome == "resolved" for record in history)


def test_developmental_corpus_contains_success_failure_consultation_and_recovery_patterns():
    corpus = developmental_corpus()
    patterns = {item.pattern for item in corpus}
    assert "successful_upgrade" in patterns
    assert "failed_upgrade" in patterns
    assert "bad_consultation" in patterns
    assert "rollback" in patterns
    assert "operator_disagreement" in patterns


def test_operator_dashboard_exposes_evidence_without_authority():
    snapshot = build_operator_dashboard_snapshot()
    rendered = render_operator_dashboard(snapshot)
    assert "Current campaign:" in rendered
    assert "Current hypothesis:" in rendered
    assert "Authority: observational dashboard only" in rendered
    assert snapshot["hidden_authority_exposed"] is False
    assert snapshot["safety"]["campaign_execution_performed"] is False


def test_rc7_benchmarks_and_reports_pass_and_are_json_serializable():
    foundation = development_loop_benchmark()
    readiness = campaign_readiness_report()
    dashboard = operator_dashboard_report()
    assert foundation["passed"] is True
    assert readiness["passed"] is True
    assert dashboard["passed"] is True
    json.dumps(foundation)
    json.dumps(readiness)
    json.dumps(dashboard)

    reports = write_reports()
    assert reports["RC7_DEVELOPMENT_LOOP_FOUNDATION"]["recommendation"] == "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS"
    json.dumps(reports)
