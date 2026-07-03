from __future__ import annotations

from orchestration.runtime.v16_review_ui_export_flow import (
    approval_export_text,
    build_review_ui_exports,
    defer_export_text,
    rejection_export_text,
    validate_review_ui_export_safe,
)
from orchestration.runtime.v16_review_ui_export_flow_report import write_review_ui_export_flow_report


def test_exports_are_exact():
    candidate_id = "candidate-1"
    assert approval_export_text(candidate_id) == "APPROVE_CANONICAL_MEMORY_WRITE\ncandidate_id=candidate-1\napproved_by=user\napproval_scope=single_memory_candidate_only"
    assert rejection_export_text(candidate_id) == "REJECT_MEMORY_CANDIDATE\ncandidate_id=candidate-1\nrejected_by=user\nrejection_scope=single_memory_candidate_only"
    assert defer_export_text(candidate_id) == "DEFER_MEMORY_CANDIDATE\ncandidate_id=candidate-1\ndeferred_by=user\ndefer_scope=single_memory_candidate_only"


def test_casual_approval_not_present():
    payload = build_review_ui_exports("candidate-1")
    text = "\n".join(item["export_text"] for item in payload["exports"]).lower()
    assert "yeah" not in text
    assert "looks good" not in text


def test_exports_do_not_mutate_or_call():
    payload = build_review_ui_exports("candidate-1")
    assert validate_review_ui_export_safe(payload)
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["provider_call_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation():
    data = write_review_ui_export_flow_report("candidate-1")
    assert data["export_safe"] is True
    assert data["final_recommendation"] == "PROCEED_MEMORY_CANDIDATE_EDIT_REJECT_DEFER_LOOP"
