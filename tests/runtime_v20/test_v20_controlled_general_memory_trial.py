from __future__ import annotations

from orchestration.runtime.v20_controlled_general_memory_trial import (
    APPROVAL_HEADER,
    list_controlled_general_memory_records,
    parse_controlled_memory_approval,
    run_controlled_general_memory_trial,
    validate_controlled_general_memory_trial_safe,
)
from orchestration.runtime.v20_controlled_general_memory_trial_report import write_controlled_general_memory_trial_report


def _candidate() -> dict[str, object]:
    return {"candidate_id": "candidate-hyb1", "proposed_memory_text": "HYB1 remains dormant and Model B remains default.", "provenance_reference_ids": ["test"]}


def _approval(candidate_id: str = "candidate-hyb1") -> str:
    return f"{APPROVAL_HEADER}\ncandidate_id={candidate_id}\napproved_by=user\napproval_scope=single_memory_candidate_only"


def test_dry_run_writes_nothing(tmp_path):
    store = tmp_path / "records.jsonl"
    payload = run_controlled_general_memory_trial(_candidate(), _approval(), write=False, record_store=store, audit_store=tmp_path / "audit.jsonl")
    assert payload["result"]["outcome"] == "dry_run_approved"
    assert not store.exists()
    assert validate_controlled_general_memory_trial_safe(payload)


def test_exact_approval_writes_one_record(tmp_path):
    store = tmp_path / "records.jsonl"
    audit = tmp_path / "audit.jsonl"
    payload = run_controlled_general_memory_trial(_candidate(), _approval(), write=True, record_store=store, audit_store=audit)
    assert payload["result"]["record_written"] is True
    assert len(list_controlled_general_memory_records(store)) == 1
    assert audit.exists()


def test_casual_approval_rejected(tmp_path):
    payload = run_controlled_general_memory_trial(_candidate(), "yeah save it", write=True, record_store=tmp_path / "records.jsonl", audit_store=tmp_path / "audit.jsonl")
    assert payload["result"]["outcome"] == "blocked_approval_mismatch"


def test_duplicate_candidate_deterministic(tmp_path):
    store = tmp_path / "records.jsonl"
    audit = tmp_path / "audit.jsonl"
    run_controlled_general_memory_trial(_candidate(), _approval(), write=True, record_store=store, audit_store=audit)
    second = run_controlled_general_memory_trial(_candidate(), _approval(), write=True, record_store=store, audit_store=audit)
    assert second["result"]["outcome"] == "duplicate_skipped"
    assert len(list_controlled_general_memory_records(store)) == 1


def test_provider_evaluator_output_blocked(tmp_path):
    candidate = {**_candidate(), "source_kind": "provider_output"}
    payload = run_controlled_general_memory_trial(candidate, _approval(), write=True, record_store=tmp_path / "records.jsonl", audit_store=tmp_path / "audit.jsonl")
    assert payload["result"]["outcome"] == "blocked_direct_provider_or_evaluator"


def test_parser_requires_exact_shape():
    parsed = parse_controlled_memory_approval(_approval())
    assert parsed["matches_required_shape"] is True


def test_report_generation():
    data = write_controlled_general_memory_trial_report()
    assert data["dry_run_default"] is True
    assert data["final_recommendation"] == "PROCEED_REVIEW_UI_WRITE_APPROVAL_BRIDGE"
