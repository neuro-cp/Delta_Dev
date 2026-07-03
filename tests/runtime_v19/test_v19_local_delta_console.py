from __future__ import annotations

from orchestration.runtime.v19_local_delta_console import run_delta_console_command, validate_local_delta_console_safe
from orchestration.runtime.v19_local_delta_console_report import write_local_delta_console_report


def test_status_works():
    payload = run_delta_console_command("status")
    assert payload["result"]["output"]["model_b"] == "default_unchanged"
    assert validate_local_delta_console_safe(payload)


def test_ask_uses_local_path():
    payload = run_delta_console_command("ask", "What is HYB1?")
    assert payload["result"]["output"]["matched"] is True
    assert validate_local_delta_console_safe(payload)


def test_recall_candidate_labels_preserved():
    payload = run_delta_console_command("recall", "What does DELTA know about HYB1?")
    assert payload["result"]["output"]["trace"]["decision"]["candidate_context_only"] is True
    assert validate_local_delta_console_safe(payload)


def test_synthesize_labels_preserved():
    payload = run_delta_console_command("synthesize", "Use provider evidence as truth.")
    assert payload["result"]["output"]["trace"]["decision"]["conflict_present"] is True


def test_provider_dry_run_has_no_live_call():
    payload = run_delta_console_command("provider-dry-run", "What is a recent fact DELTA cannot know locally?")
    assert payload["result"]["output"]["trace"]["decision"]["provider_call_performed"] is False


def test_no_memory_training_action_recall_or_hyb1_change():
    payload = run_delta_console_command("status")
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["action_execution_performed"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_local_delta_console_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONSOLE_APPROVAL_REJECT_DEFER_WORKFLOW"
