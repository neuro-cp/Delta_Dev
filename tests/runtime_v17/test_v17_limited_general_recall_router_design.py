from __future__ import annotations

import json

from orchestration.runtime.v16_canonical_memory_rollback_trial import build_rollback_approval_text, execute_canonical_memory_rollback_trial
from orchestration.runtime.v17_limited_general_recall_router import route_limited_general_recall, validate_limited_general_recall_safe
from orchestration.runtime.v17_limited_general_recall_router_report import write_limited_general_recall_router_report


def test_approved_source_can_be_candidate(tmp_path):
    store = tmp_path / "records.jsonl"
    store.write_text(json.dumps({"canonical_record_id": "record-1", "record_text": "HYB1 remains dormant and Model B remains default."}) + "\n", encoding="utf-8")
    payload = route_limited_general_recall("HYB1 Model B", trial_store=store, rollback_marker_path=tmp_path / "markers.jsonl")
    assert payload["candidates"]
    assert validate_limited_general_recall_safe(payload)


def test_rolled_back_source_excluded(tmp_path):
    store = tmp_path / "records.jsonl"
    markers = tmp_path / "markers.jsonl"
    store.write_text(json.dumps({"canonical_record_id": "record-1", "record_text": "HYB1 remains dormant and Model B remains default."}) + "\n", encoding="utf-8")
    execute_canonical_memory_rollback_trial("record-1", build_rollback_approval_text("record-1"), dry_run=False, marker_path=markers)
    payload = route_limited_general_recall("HYB1 Model B", trial_store=store, rollback_marker_path=markers)
    assert all(item["source_reference"] != "record-1" for item in payload["candidates"])
    assert validate_limited_general_recall_safe(payload)


def test_evaluator_advisory_is_not_authority():
    payload = route_limited_general_recall("advisory evaluator")
    assert all(item["authoritative"] is False for item in payload["candidates"])
    assert validate_limited_general_recall_safe(payload)


def test_report_generation():
    data = write_limited_general_recall_router_report()
    assert data["router_safe"] is True
    assert data["final_recommendation"] == "PROCEED_LOCAL_MULTI_TURN_SESSION_STATE"
