from __future__ import annotations

from orchestration.runtime.v20_controlled_general_memory_trial import parse_controlled_memory_approval
from orchestration.runtime.v20_review_ui_write_approval_bridge import build_review_ui_exports, generate_review_ui_write_approval_bridge, validate_review_ui_bridge_safe
from orchestration.runtime.v20_review_ui_write_approval_bridge_report import write_review_ui_write_approval_bridge_report


def test_export_generates_exact_approval_text():
    exports = build_review_ui_exports("candidate-1")
    assert exports["approve"] == "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE\ncandidate_id=candidate-1\napproved_by=user\napproval_scope=single_memory_candidate_only"
    assert parse_controlled_memory_approval(exports["approve"])["matches_required_shape"] is True


def test_export_generates_reject_and_defer():
    exports = build_review_ui_exports("candidate-1")
    assert "REJECT_MEMORY_CANDIDATE" in exports["reject"]
    assert "DEFER_MEMORY_CANDIDATE" in exports["defer"]


def test_ui_generation_does_not_write_memory():
    payload = generate_review_ui_write_approval_bridge("memory-candidate-demo")
    assert validate_review_ui_bridge_safe(payload)
    assert payload["invariant_flags"]["memory_write_performed"] is False


def test_casual_approval_not_accepted():
    assert parse_controlled_memory_approval("looks good")["matches_required_shape"] is False


def test_report_generation():
    data = write_review_ui_write_approval_bridge_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_GENERAL_RECALL_TRIAL"
