from __future__ import annotations

from orchestration.runtime.v21_controlled_general_memory_expansion import (
    approval_text_for_candidate,
    check_expanded_memory_write_eligibility,
    list_expanded_memory_candidates,
    run_expanded_memory_write_trial,
    validate_memory_expansion_safe,
)
from orchestration.runtime.v21_controlled_general_memory_expansion_report import write_memory_expansion_report


def test_multiple_candidate_sources_listed():
    candidates = list_expanded_memory_candidates()
    assert len(candidates) >= 3
    assert {item["source_kind"] for item in candidates}


def test_exact_approval_required():
    eligibility = check_expanded_memory_write_eligibility("memory-candidate-demo", "yeah")
    assert eligibility["eligible"] is False
    assert "exact_approval_required" in eligibility["blocks"]


def test_approved_candidate_dry_run_safe():
    payload = run_expanded_memory_write_trial("memory-candidate-demo", approval_text_for_candidate("memory-candidate-demo"))
    assert payload["decision"]["outcome"] == "dry_run_approved"
    assert validate_memory_expansion_safe(payload)


def test_ambiguous_candidate_blocked():
    payload = run_expanded_memory_write_trial("ambiguous-candidate-demo", approval_text_for_candidate("ambiguous-candidate-demo"))
    assert payload["decision"]["outcome"] == "blocked"
    assert "ambiguity_sarcasm_or_misuse_flag" in payload["eligibility"]["blocks"]


def test_no_provider_training_action_recall_mutation():
    payload = run_expanded_memory_write_trial("memory-candidate-demo", approval_text_for_candidate("memory-candidate-demo"))
    flags = payload["invariant_flags"]
    assert flags["provider_call_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["action_execution_performed"] is False
    assert flags["recall_mutated"] is False


def test_report_generation():
    data = write_memory_expansion_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_PROVIDER_LIVE_TRIAL_USER_APPROVED"
