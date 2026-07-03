from __future__ import annotations

import json

from orchestration.runtime.v20_controlled_general_recall_trial import run_controlled_general_recall, validate_controlled_general_recall_safe
from orchestration.runtime.v20_controlled_general_recall_trial_report import write_controlled_general_recall_trial_report


def test_approved_records_are_candidate_context(tmp_path):
    store = tmp_path / "records.jsonl"
    store.write_text(json.dumps({"canonical_record_id": "rec-1", "record_text": "HYB1 remains dormant.", "provenance_reference_ids": ["p1"]}) + "\n", encoding="utf-8")
    payload = run_controlled_general_recall("HYB1 dormant", sources=(store,))
    assert payload["candidate_count"] == 1
    assert payload["candidates"][0]["authoritative"] is False
    assert validate_controlled_general_recall_safe(payload)


def test_rolled_back_rejected_deferred_excluded(tmp_path):
    store = tmp_path / "records.jsonl"
    rows = [
        {"canonical_record_id": "rec-1", "record_text": "HYB1 dormant", "rolled_back": True},
        {"canonical_record_id": "rec-2", "record_text": "HYB1 dormant", "rejected": True},
        {"canonical_record_id": "rec-3", "record_text": "HYB1 dormant", "deferred": True},
    ]
    store.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    payload = run_controlled_general_recall("HYB1", sources=(store,))
    assert payload["candidate_count"] == 0


def test_max_candidate_limit(tmp_path):
    store = tmp_path / "records.jsonl"
    rows = [{"canonical_record_id": f"rec-{i}", "record_text": f"HYB1 memory {i}"} for i in range(8)]
    store.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    payload = run_controlled_general_recall("HYB1", max_candidates=5, sources=(store,))
    assert payload["candidate_count"] == 5


def test_no_mutation_flags():
    payload = run_controlled_general_recall("HYB1")
    assert payload["invariant_flags"]["memory_write_performed"] is False
    assert payload["invariant_flags"]["recall_mutated"] is False
    assert payload["invariant_flags"]["provider_call_performed"] is False


def test_report_generation():
    data = write_controlled_general_recall_trial_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_PROVIDER_EVIDENCE_LIVE_TRIAL_REVIEW_BRIDGE"
