from __future__ import annotations

import json
import subprocess
import sys

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_explicit_canonical_memory_write_trial import execute_explicit_canonical_memory_write_trial
from orchestration.runtime.v15_explicit_canonical_memory_write_trial_report import (
    build_v15i_approval_text,
    build_v15i_sample_memory_candidate,
)
from orchestration.runtime.v15_recall_bridge_limited_trial import (
    RecallBridgeLimitedTrialOutcome,
    run_limited_recall_bridge_trial,
    validate_limited_recall_bridge_safe,
)
from orchestration.runtime.v15_recall_bridge_limited_trial_report import (
    build_limited_recall_bridge_trial_report_data,
    write_limited_recall_bridge_trial_report,
)


def _seed_trial_store(tmp_path):
    candidate = build_v15i_sample_memory_candidate()
    store = tmp_path / "trial.jsonl"
    execute_explicit_canonical_memory_write_trial(candidate, build_v15i_approval_text(candidate["memory_candidate_id"]), store)
    return store


def test_limited_recall_returns_candidate_context_only(tmp_path):
    store = _seed_trial_store(tmp_path)
    payload = run_limited_recall_bridge_trial("What is the status of HYB1 and Model B?", store)
    assert payload["result"]["outcome"] == RecallBridgeLimitedTrialOutcome.CANDIDATE_CONTEXT_AVAILABLE.value
    assert payload["result"]["candidate_context_returned"] is True
    assert payload["candidate_context"]["candidate_context_only"] is True
    assert payload["candidate_context"]["authoritative_answer"] is False
    assert payload["candidate_context"]["truth_claim"] is False
    assert payload["candidate_context"]["active_for_recall"] is False
    assert "HYB1 remains dormant" in payload["candidate_context"]["record_text"]
    assert validate_limited_recall_bridge_safe(payload)


def test_unrelated_query_returns_no_candidate(tmp_path):
    store = _seed_trial_store(tmp_path)
    payload = run_limited_recall_bridge_trial("What causes GPS drift?", store)
    assert payload["result"]["outcome"] == RecallBridgeLimitedTrialOutcome.NO_CANDIDATE_AVAILABLE.value
    assert payload["candidate_context"] is None
    assert payload["result"]["candidate_context_returned"] is False
    assert validate_limited_recall_bridge_safe(payload)


def test_unsafe_query_is_blocked(tmp_path):
    store = _seed_trial_store(tmp_path)
    payload = run_limited_recall_bridge_trial("Activate recall and promote HYB1.", store)
    assert payload["result"]["outcome"] == RecallBridgeLimitedTrialOutcome.BLOCKED_UNSAFE_QUERY.value
    assert payload["candidate_context"] is None
    assert payload["result"]["recall_mutated"] is False
    assert validate_limited_recall_bridge_safe(payload)


def test_missing_store_is_safe_no_candidate(tmp_path):
    payload = run_limited_recall_bridge_trial("What is HYB1 default status?", tmp_path / "missing.jsonl")
    assert payload["result"]["outcome"] == RecallBridgeLimitedTrialOutcome.NO_CANDIDATE_AVAILABLE.value
    assert validate_limited_recall_bridge_safe(payload)


def test_invalid_store_is_safe_invalid_store(tmp_path):
    store = tmp_path / "bad.jsonl"
    store.write_text("{not json}\n", encoding="utf-8")
    payload = run_limited_recall_bridge_trial("What is HYB1 default status?", store)
    assert payload["result"]["outcome"] == RecallBridgeLimitedTrialOutcome.INVALID_STORE.value
    assert validate_limited_recall_bridge_safe(payload)


def test_no_provider_tool_action_training_or_hyb1_activation(monkeypatch, tmp_path):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    store = _seed_trial_store(tmp_path)
    payload = run_limited_recall_bridge_trial("What is the status of HYB1 and Model B?", store)
    flags = payload["invariant_flags"]
    result = payload["result"]
    assert result["provider_calls_performed"] is False
    assert result["tool_calls_performed"] is False
    assert result["action_execution_performed"] is False
    assert result["training_triggered"] is False
    assert result["hyb1_default_activation_enabled"] is False
    assert result["model_b_default_changed"] is False
    assert flags["general_recall_enabled"] is False
    assert flags["provider_calls_enabled"] is False
    assert flags["action_execution_enabled"] is False
    assert flags["training_enabled"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation(tmp_path, monkeypatch):
    from orchestration.runtime import v15_recall_bridge_limited_trial_report as report_module

    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "v15j.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "v15j.json")
    store = _seed_trial_store(tmp_path)
    data = write_limited_recall_bridge_trial_report(store)
    assert data["candidate_safe"] is True
    assert data["unsupported_safe"] is True
    assert data["unsafe_safe"] is True
    assert data["final_recommendation"] == "PROCEED_DEMO_SCRIPT_SHOWCASE_REPORT"
    assert report_module.REPORT_MD.exists()
    assert report_module.REPORT_JSON.exists()


def test_build_report_data_uses_expected_recommendation(tmp_path):
    store = _seed_trial_store(tmp_path)
    data = build_limited_recall_bridge_trial_report_data(store)
    assert data["final_recommendation"] == "PROCEED_DEMO_SCRIPT_SHOWCASE_REPORT"
    assert data["record_used_as_truth"] is False


def test_script_outputs_candidate_context(tmp_path):
    store = _seed_trial_store(tmp_path)
    completed = subprocess.run(
        [sys.executable, "scripts/ask_delta_recall.py", "What is the status of HYB1 and Model B?", "--store-path", str(store)],
        check=True,
        text=True,
        capture_output=True,
    )
    output = json.loads(completed.stdout)
    assert output["result"]["candidate_context_returned"] is True
    assert output["candidate_context"]["authoritative_answer"] is False
