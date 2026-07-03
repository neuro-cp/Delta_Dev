from __future__ import annotations

from orchestration.runtime.v20_local_ux_consolidation import run_delta_ux_command, validate_local_ux_safe
from orchestration.runtime.v20_local_ux_consolidation_report import write_local_ux_consolidation_report


def test_status_works():
    payload = run_delta_ux_command("status")
    assert payload["output"]["result"]["output"]["model_b"] == "default_unchanged"
    assert validate_local_ux_safe(payload)


def test_ask_routes_local_known_answer():
    payload = run_delta_ux_command("ask", "What is HYB1?")
    assert payload["output"]["result"]["output"]["matched"] is True


def test_recall_preserves_candidate_context_label():
    payload = run_delta_ux_command("recall", "What does DELTA know about HYB1?")
    assert payload["output"]["result"]["output"]["trace"]["decision"]["candidate_context_only"] is True


def test_review_ui_static_pointer():
    payload = run_delta_ux_command("review-ui")
    assert payload["output"]["static_only"] is True
    assert payload["output"]["executes_write"] is False


def test_provider_dry_run_no_live_call():
    payload = run_delta_ux_command("provider-dry-run", "recent fact")
    assert payload["output"]["result"]["output"]["trace"]["decision"]["provider_call_performed"] is False


def test_safety_reports_disabled_systems():
    payload = run_delta_ux_command("safety")
    assert payload["output"]["hyb1"] == "dormant_env_gated"
    assert validate_local_ux_safe(payload)


def test_report_generation():
    data = write_local_ux_consolidation_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_GENERAL_MEMORY_TRIAL_DESIGN"
