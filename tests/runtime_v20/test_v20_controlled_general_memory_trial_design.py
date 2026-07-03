from __future__ import annotations

from orchestration.runtime.v20_controlled_general_memory_trial_design import (
    MemoryCandidateState,
    design_controlled_general_memory_trial,
    validate_controlled_general_memory_design_safe,
)
from orchestration.runtime.v20_controlled_general_memory_trial_design_report import write_controlled_general_memory_trial_design_report


def test_design_accepts_only_approved_candidate_for_future_trial():
    payload = design_controlled_general_memory_trial("candidate-1", MemoryCandidateState.APPROVED)
    assert payload["decision"]["eligible_for_future_trial"] is True
    assert validate_controlled_general_memory_design_safe(payload)


def test_design_excludes_rejected_deferred_rolled_back():
    for state in (MemoryCandidateState.REJECTED, MemoryCandidateState.DEFERRED, MemoryCandidateState.ROLLED_BACK):
        payload = design_controlled_general_memory_trial("candidate-1", state)
        assert payload["decision"]["eligible_for_future_trial"] is False


def test_provider_output_cannot_write_directly():
    payload = design_controlled_general_memory_trial("provider-output", MemoryCandidateState.APPROVED, source_kind="provider_output")
    assert payload["decision"]["eligible_for_future_trial"] is False


def test_design_does_not_write_or_activate_recall():
    payload = design_controlled_general_memory_trial("candidate-1", MemoryCandidateState.APPROVED)
    assert payload["decision"]["writes_memory_now"] is False
    assert payload["decision"]["activates_general_recall"] is False


def test_report_generation():
    data = write_controlled_general_memory_trial_design_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_GENERAL_MEMORY_TRIAL_EXPLICIT_APPROVAL_ONLY"
