from __future__ import annotations

from orchestration.runtime.v21_localhost_review_ui import (
    LocalhostReviewUIConfig,
    build_localhost_review_state,
    create_localhost_review_server,
    render_localhost_review_page,
    render_static_localhost_review_ui,
    validate_localhost_review_ui_safe,
)
from orchestration.runtime.v21_localhost_review_ui_report import write_localhost_review_ui_report


def test_localhost_server_binds_only_to_loopback():
    cfg = LocalhostReviewUIConfig()
    assert cfg.host == "127.0.0.1"
    assert cfg.external_binding_allowed is False


def test_non_loopback_rejected():
    try:
        create_localhost_review_server(LocalhostReviewUIConfig(host="0.0.0.0"))
    except ValueError as exc:
        assert "127.0.0.1" in str(exc)
    else:
        raise AssertionError("expected non-loopback binding rejection")


def test_ui_pages_render_offline_without_secret():
    html = render_localhost_review_page("/")
    assert "DELTA Localhost Review UI" in html
    assert "sk-" not in html


def test_approval_exports_exact():
    state = build_localhost_review_state(candidate_id="candidate-1")
    assert state["exports"]["approve"] == "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE\ncandidate_id=candidate-1\napproved_by=user\napproval_scope=single_memory_candidate_only"


def test_static_render_safe(tmp_path):
    payload = render_static_localhost_review_ui(tmp_path / "ui.html")
    assert validate_localhost_review_ui_safe(payload)


def test_no_mutation_flags():
    payload = render_static_localhost_review_ui()
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["provider_call_performed"] is False
    assert flags["scheduler_started"] is False


def test_report_generation():
    data = write_localhost_review_ui_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_GENERAL_MEMORY_TRIAL_EXPANSION"
