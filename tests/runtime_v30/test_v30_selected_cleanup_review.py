from orchestration.runtime.v30_selected_cleanup_review import build_cleanup_review


def test_v30_cleanup_review_is_report_only():
    data = build_cleanup_review()
    assert data["cleanup_performed"] is False
    assert "safe_cleanup_now" in data["cleanup_plan"]
    assert "risky_cleanup_later" in data["cleanup_plan"]
    assert data["safety_invariants"]["provider_call_performed"] is False
