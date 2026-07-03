from __future__ import annotations

import json

from orchestration.runtime.v20_provider_live_review_bridge import build_provider_live_review_bridge, validate_provider_live_review_bridge_safe
from orchestration.runtime.v20_provider_live_review_bridge_report import write_provider_live_review_bridge_report


def test_no_provider_report_handled_safely(tmp_path):
    payload = build_provider_live_review_bridge(tmp_path / "missing.json")
    assert payload["provider_report_present"] is False
    assert validate_provider_live_review_bridge_safe(payload)


def test_provider_report_loaded_as_evidence_only(tmp_path):
    report = tmp_path / "provider.json"
    report.write_text(json.dumps({"phase": "provider trial", "summary": "sample"}), encoding="utf-8")
    payload = build_provider_live_review_bridge(report)
    assert payload["provider_evidence"]["evidence_only"] is True
    assert payload["provider_evidence"]["authoritative"] is False


def test_optional_evaluator_not_automatic():
    payload = build_provider_live_review_bridge()
    assert payload["invariant_flags"]["evaluator_cross_check_automatic"] is False


def test_no_mutation_or_live_call():
    payload = build_provider_live_review_bridge()
    flags = payload["invariant_flags"]
    assert flags["live_provider_call_performed"] is False
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False


def test_report_generation():
    data = write_provider_live_review_bridge_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_SCHEDULER_ACTIVATION_TRIAL_DESIGN_ONLY"
