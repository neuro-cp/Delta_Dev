from __future__ import annotations

from pathlib import Path

from orchestration.runtime.v17_provider_evidence_review_ui import (
    EvidenceReviewSourceLabel,
    build_evidence_review_ui_input,
    render_evidence_review_html,
    validate_evidence_review_ui_safe,
    write_evidence_review_ui,
)
from orchestration.runtime.v17_provider_evidence_review_ui_report import write_provider_evidence_review_ui_report


def test_ui_generation_works_offline(tmp_path):
    data = write_evidence_review_ui(tmp_path / "evidence.html")
    assert Path(data["export"]["path"]).exists()
    assert data["report_entry"]["no_live_calls"] is True
    assert validate_evidence_review_ui_safe(data, Path(data["export"]["path"]).read_text(encoding="utf-8"))


def test_no_api_key_rendered():
    ui_input = build_evidence_review_ui_input()
    rendered = render_evidence_review_html(ui_input)
    assert "sk-" not in rendered
    assert "Evidence only / not authority" in rendered
    assert validate_evidence_review_ui_safe(ui_input.as_dict(), rendered)


def test_source_labels_are_non_authoritative():
    ui_input = build_evidence_review_ui_input()
    labels = {item.source_label for item in ui_input.items}
    assert EvidenceReviewSourceLabel.LOCAL_ANSWER in labels
    assert EvidenceReviewSourceLabel.RECALL_CANDIDATE in labels
    assert EvidenceReviewSourceLabel.PROVIDER_EVIDENCE in labels
    assert EvidenceReviewSourceLabel.SPECIALIST_EVIDENCE in labels
    assert EvidenceReviewSourceLabel.EVALUATOR_ADVISORY in labels
    assert all(item.authoritative is False for item in ui_input.items)


def test_no_mutation_training_scheduler_or_hyb1_change():
    data = write_evidence_review_ui()
    flags = data["safety_flags"]
    assert flags["provider_call_performed"] is False
    assert flags["specialist_call_performed"] is False
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["scheduler_enabled"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_provider_evidence_review_ui_report()
    assert data["final_recommendation"] == "PROCEED_LIMITED_GENERAL_RECALL_TRIAL"
    assert data["report_entry"]["all_items_non_authoritative"] is True
