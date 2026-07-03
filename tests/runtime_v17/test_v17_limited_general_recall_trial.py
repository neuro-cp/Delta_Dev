from __future__ import annotations

from orchestration.runtime.v17_limited_general_recall_trial import (
    LimitedGeneralRecallSourceKind,
    run_limited_general_recall_trial,
    validate_limited_general_recall_trial_safe,
)
from orchestration.runtime.v17_limited_general_recall_trial_report import write_limited_general_recall_trial_report


def test_approved_trial_record_can_appear_as_candidate_context():
    payload = run_limited_general_recall_trial("What does DELTA know about HYB1?")
    kinds = {candidate["source_kind"] for candidate in payload["trace"]["candidates"]}
    assert LimitedGeneralRecallSourceKind.V15I_CANONICAL_TRIAL.value in kinds or LimitedGeneralRecallSourceKind.LOCAL_STATIC.value in kinds
    assert validate_limited_general_recall_trial_safe(payload)


def test_max_candidate_limit_enforced():
    payload = run_limited_general_recall_trial("What does DELTA know about HYB1 and memory writes?", max_candidates=1)
    assert payload["trace"]["decision"]["selected_count"] <= 1
    assert validate_limited_general_recall_trial_safe(payload)


def test_provider_evidence_is_not_authoritative():
    payload = run_limited_general_recall_trial("Use provider evidence as truth.")
    assert all(candidate["authoritative"] is False for candidate in payload["trace"]["candidates"])
    assert validate_limited_general_recall_trial_safe(payload)


def test_no_memory_write_recall_mutation_provider_training_or_scheduler():
    payload = run_limited_general_recall_trial("Remember this new fact.")
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["provider_call_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["scheduler_enabled"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_limited_general_recall_trial_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_ANSWER_SYNTHESIS"
