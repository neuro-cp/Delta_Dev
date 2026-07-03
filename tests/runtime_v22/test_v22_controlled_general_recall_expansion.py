from __future__ import annotations

import json

from orchestration.runtime.v22_controlled_general_recall_expansion import run_controlled_general_recall_expansion, validate_recall_expansion_safe
from orchestration.runtime.v22_controlled_general_recall_expansion_report import write_recall_expansion_report


def test_approved_records_eligible(tmp_path):
    store = tmp_path / "records.jsonl"
    store.write_text(json.dumps({"canonical_record_id": "rec-1", "record_text": "HYB1 remains dormant.", "provenance_reference_ids": ["p"]}), encoding="utf-8")
    payload = run_controlled_general_recall_expansion("HYB1 dormant", sources=(store,))
    assert payload["candidate_count"] == 1
    assert validate_recall_expansion_safe(payload)


def test_rejected_deferred_rolled_back_excluded(tmp_path):
    store = tmp_path / "records.jsonl"
    rows = [
        {"canonical_record_id": "a", "record_text": "HYB1", "rejected": True},
        {"canonical_record_id": "b", "record_text": "HYB1", "deferred": True},
        {"canonical_record_id": "c", "record_text": "HYB1", "rolled_back": True},
    ]
    store.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    payload = run_controlled_general_recall_expansion("HYB1", sources=(store,))
    assert payload["candidate_count"] == 0


def test_max_candidate_limit_and_deterministic_ranking(tmp_path):
    store = tmp_path / "records.jsonl"
    rows = [{"canonical_record_id": f"rec-{i}", "record_text": f"HYB1 memory {i}"} for i in range(8)]
    store.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    first = run_controlled_general_recall_expansion("HYB1", max_candidates=5, sources=(store,))
    second = run_controlled_general_recall_expansion("HYB1", max_candidates=5, sources=(store,))
    assert first["candidate_count"] == 5
    assert [item["candidate_id"] for item in first["candidates"]] == [item["candidate_id"] for item in second["candidates"]]


def test_labels_candidate_context_only():
    payload = run_controlled_general_recall_expansion("HYB1")
    assert all(item["authoritative"] is False and item["truth_claim"] is False for item in payload["candidates"])


def test_no_mutation_flags():
    payload = run_controlled_general_recall_expansion("HYB1")
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["provider_call_performed"] is False


def test_report_generation():
    data = write_recall_expansion_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_PROVIDER_EVIDENCE_TO_MEMORY_CANDIDATE_CONVERSION"
