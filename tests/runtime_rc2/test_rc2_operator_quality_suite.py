from __future__ import annotations

from orchestration.runtime import rc2_operator_quality_suite as suite


def test_operator_quality_suite_builds_expected_categories():
    scenarios = suite.build_operator_quality_scenarios()

    suites = {scenario.suite for scenario in scenarios}
    assert "Conversational Continuity" in suites
    assert "Concept Browsing" in suites
    assert "Retrieval Quality" in suites
    assert "Short-Term Memory" in suites
    assert "Local Model Routing" in suites


def test_operator_quality_suite_is_report_only_and_safe():
    report = suite.run_operator_quality_suite()

    assert report["scenario_count"] >= 6
    assert report["turn_count"] >= 20
    assert report["safety"]["training_performed"] is False
    assert report["safety"]["canonical_write_performed"] is False
    assert report["safety"]["provider_calls_performed"] is False
    assert report["safety"]["autonomous_action_performed"] is False
    assert "topic_continuity" in report["metrics"]
    assert "followup_resolution" in report["metrics"]
    assert report["recommendation"]


def test_operator_quality_reports_write_expected_files(monkeypatch, tmp_path):
    reports = tmp_path / "reports"
    docs = tmp_path / "docs"
    monkeypatch.setattr(suite, "REPORTS", reports)
    monkeypatch.setattr(suite, "DOCS", docs)

    report = suite.write_operator_quality_reports()

    assert report["turn_count"] >= 20
    assert (reports / "RC2_OPERATOR_QUALITY_SUITE.json").exists()
    assert (reports / "RC2_OPERATOR_QUALITY_SUITE.md").exists()
    assert (docs / "continuation_rc2_operator_quality_suite.md").exists()
