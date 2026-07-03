from __future__ import annotations

from pathlib import Path

from orchestration.runtime.v18_review_ui_evidence_quality_iteration import build_quality_review_ui_input, render_quality_review_dashboard, validate_quality_review_ui_safe, write_quality_review_dashboard
from orchestration.runtime.v18_review_ui_evidence_quality_iteration_report import write_quality_review_ui_report


def test_dashboard_generates_offline(tmp_path):
    data = write_quality_review_dashboard(tmp_path / "quality.html")
    assert Path(data["report_entry"]["output_path"]).exists()
    assert data["report_entry"]["safe"] is True


def test_no_key_appears():
    ui_input = build_quality_review_ui_input()
    rendered = render_quality_review_dashboard(ui_input)
    assert "sk-" not in rendered
    assert "key redacted" in rendered.lower()
    assert validate_quality_review_ui_safe(ui_input.as_dict(), rendered)


def test_scorecards_and_blockers_displayed():
    ui_input = build_quality_review_ui_input()
    labels = [metric.label for metric in ui_input.metrics]
    assert "Evidence quality average" in labels
    assert "Promotion blockers" in labels
    assert ui_input.blockers


def test_provider_specialist_evaluator_labels_preserved():
    rendered = render_quality_review_dashboard(build_quality_review_ui_input()).lower()
    assert "provider answer != truth" in rendered
    assert "specialist answer != authority" in rendered
    assert "evidence score != promotion" in rendered


def test_no_mutation_or_runtime_change():
    data = write_quality_review_dashboard()
    flags = data["safety_flags"]
    assert flags["provider_call_performed"] is False
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["scheduler_enabled"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_quality_review_ui_report()
    assert data["final_recommendation"] == "PROCEED_MANUAL_PROVIDER_LIVE_TRIAL_GATE"
