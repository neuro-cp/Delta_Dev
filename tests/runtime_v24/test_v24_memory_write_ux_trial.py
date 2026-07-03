from orchestration.runtime.v24_memory_write_ux_trial import build_memory_write_approval, run_memory_write_ux_trial, validate_memory_write_ux_safe
from orchestration.runtime.v24_memory_write_ux_trial_report import write_memory_write_ux_report


def _candidate():
    return {"candidate_id": "memory-candidate-demo", "proposed_memory_text": "Model B remains default.", "provenance_reference_ids": ["p"]}


def test_ux_dry_run_writes_nothing(tmp_path):
    payload = run_memory_write_ux_trial(_candidate(), build_memory_write_approval("memory-candidate-demo"), write=False, record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")
    assert payload["decision"]["record_written"] is False
    assert not (tmp_path / "r.jsonl").exists()
    assert validate_memory_write_ux_safe(payload)


def test_exact_approval_can_write_one_fixture_record(tmp_path):
    payload = run_memory_write_ux_trial(_candidate(), build_memory_write_approval("memory-candidate-demo"), write=True, record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")
    assert payload["decision"]["record_written"] is True
    assert payload["decision"]["audit_created"] is True
    assert payload["decision"]["rollback_reference_created"] is True


def test_casual_bulk_and_ambiguous_rejected(tmp_path):
    assert run_memory_write_ux_trial(_candidate(), "yes", record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")["blocks"]
    assert "bulk_approval_blocked" in run_memory_write_ux_trial({**_candidate(), "bulk_candidate_ids": ["a"]}, build_memory_write_approval("memory-candidate-demo"), record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")["blocks"]
    assert "ambiguous_candidate_blocked" in run_memory_write_ux_trial({**_candidate(), "ambiguous": True}, build_memory_write_approval("memory-candidate-demo"), record_store=tmp_path / "r.jsonl", audit_store=tmp_path / "a.jsonl")["blocks"]


def test_no_hidden_write_or_hyb1_change():
    payload = run_memory_write_ux_trial(_candidate())
    flags = payload["invariant_flags"]
    assert flags["hidden_write_allowed"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation():
    data = write_memory_write_ux_report()
    assert data["all_safe"] is True

