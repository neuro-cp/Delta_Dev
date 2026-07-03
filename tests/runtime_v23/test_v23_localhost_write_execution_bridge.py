from pathlib import Path

from orchestration.runtime.v23_localhost_write_execution_bridge import run_localhost_write_execution_bridge, validate_localhost_write_execution_bridge_safe
from orchestration.runtime.v23_localhost_write_execution_bridge_report import APPROVAL, write_localhost_write_execution_bridge_report


def _candidate():
    return {"candidate_id": "memory-candidate-demo", "proposed_memory_text": "Model B remains default.", "provenance_reference_ids": ["p"]}


def test_dry_run_writes_nothing(tmp_path):
    payload = run_localhost_write_execution_bridge(_candidate(), APPROVAL, write=False, record_store=tmp_path / "records.jsonl", audit_store=tmp_path / "audit.jsonl")
    assert payload["decision"]["record_written"] is False
    assert not (tmp_path / "records.jsonl").exists()
    assert validate_localhost_write_execution_bridge_safe(payload)


def test_exact_approval_can_write_one_controlled_trial_record(tmp_path):
    payload = run_localhost_write_execution_bridge(_candidate(), APPROVAL, write=True, record_store=tmp_path / "records.jsonl", audit_store=tmp_path / "audit.jsonl")
    assert payload["decision"]["record_written"] is True
    assert (tmp_path / "records.jsonl").exists()
    assert (tmp_path / "audit.jsonl").exists()


def test_casual_and_bulk_approval_rejected(tmp_path):
    bulk = {**_candidate(), "bulk_candidate_ids": ["a", "b"]}
    assert run_localhost_write_execution_bridge(_candidate(), "yes", write=True, record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")["blocks"]
    assert "bulk_approval_blocked" in run_localhost_write_execution_bridge(bulk, APPROVAL, write=True, record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")["blocks"]


def test_ambiguous_and_misuse_candidates_blocked(tmp_path):
    assert "ambiguous_candidate_blocked" in run_localhost_write_execution_bridge({**_candidate(), "ambiguous": True}, APPROVAL, record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")["blocks"]
    assert "misuse_candidate_blocked" in run_localhost_write_execution_bridge({**_candidate(), "misuse": True}, APPROVAL, record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")["blocks"]


def test_report_generation():
    data = write_localhost_write_execution_bridge_report()
    assert data["all_safe"] is True

