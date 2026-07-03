from __future__ import annotations

import json
import subprocess
import sys

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_explicit_canonical_memory_write_trial import (
    APPROVAL_APPROVED_BY,
    APPROVAL_HEADER,
    APPROVAL_SCOPE,
    ExplicitWriteTrialOutcome,
    build_explicit_canonical_write_approval,
    execute_explicit_canonical_memory_write_trial,
    validate_explicit_write_trial_safe,
)
from orchestration.runtime.v15_explicit_canonical_memory_write_trial_report import (
    build_explicit_canonical_memory_write_trial_report_data,
    build_v15i_approval_text,
    build_v15i_sample_memory_candidate,
    write_explicit_canonical_memory_write_trial_report,
)


def test_exact_approval_structure_is_required():
    candidate = build_v15i_sample_memory_candidate()
    approval = build_explicit_canonical_write_approval(candidate, build_v15i_approval_text(candidate["memory_candidate_id"]))
    assert approval.approval_present is True
    assert approval.approval_matches_required_structure is True
    assert approval.candidate_id_matches is True
    assert approval.bulk_approval is False


def test_casual_approval_does_not_write(tmp_path):
    candidate = build_v15i_sample_memory_candidate()
    for text in ("yes", "yeah", "that's right", "save it", "remember that", "looks good", "go ahead"):
        payload = execute_explicit_canonical_memory_write_trial(candidate, text, tmp_path / f"{text.replace(' ', '_')}.jsonl")
        assert payload["result"]["outcome"] == ExplicitWriteTrialOutcome.BLOCKED_APPROVAL_MISMATCH.value
        assert payload["result"]["record_written"] is False
        assert not (tmp_path / f"{text.replace(' ', '_')}.jsonl").exists()
        assert validate_explicit_write_trial_safe(payload)


def test_wrong_candidate_id_does_not_write(tmp_path):
    candidate = build_v15i_sample_memory_candidate()
    approval = "\n".join([APPROVAL_HEADER, "candidate_id=other-candidate", APPROVAL_APPROVED_BY, APPROVAL_SCOPE])
    payload = execute_explicit_canonical_memory_write_trial(candidate, approval, tmp_path / "wrong.jsonl")
    assert payload["approval"]["candidate_id_matches"] is False
    assert payload["result"]["record_written"] is False
    assert not (tmp_path / "wrong.jsonl").exists()


def test_exact_approval_writes_one_local_trial_record(tmp_path):
    candidate = build_v15i_sample_memory_candidate()
    store = tmp_path / "trial.jsonl"
    payload = execute_explicit_canonical_memory_write_trial(candidate, build_v15i_approval_text(candidate["memory_candidate_id"]), store)
    assert payload["result"]["outcome"] == ExplicitWriteTrialOutcome.WRITTEN.value
    assert payload["result"]["record_written"] is True
    assert store.exists()
    records = [json.loads(line) for line in store.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["canonical_record_id"] == payload["canonical_record"]["canonical_record_id"]
    assert payload["canonical_record"]["active_for_recall"] is False
    assert payload["canonical_record"]["general_memory_enabled"] is False
    assert validate_explicit_write_trial_safe(payload)


def test_exact_approval_is_idempotent_for_same_candidate(tmp_path):
    candidate = build_v15i_sample_memory_candidate()
    store = tmp_path / "trial.jsonl"
    approval = build_v15i_approval_text(candidate["memory_candidate_id"])
    execute_explicit_canonical_memory_write_trial(candidate, approval, store)
    execute_explicit_canonical_memory_write_trial(candidate, approval, store)
    assert len(store.read_text(encoding="utf-8").splitlines()) == 1


def test_no_provider_tool_action_training_recall_or_hyb1_activation(monkeypatch, tmp_path):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    candidate = build_v15i_sample_memory_candidate()
    payload = execute_explicit_canonical_memory_write_trial(candidate, build_v15i_approval_text(candidate["memory_candidate_id"]), tmp_path / "trial.jsonl")
    result = payload["result"]
    audit = payload["audit_metadata"]
    flags = payload["invariant_flags"]
    assert result["provider_calls_performed"] is False
    assert result["tool_calls_performed"] is False
    assert result["action_execution_performed"] is False
    assert result["training_triggered"] is False
    assert result["recall_still_inactive"] is True
    assert result["hyb1_default_activation_enabled"] is False
    assert result["model_b_default_changed"] is False
    assert audit["provider_calls_performed"] is False
    assert audit["tool_calls_performed"] is False
    assert audit["action_execution_performed"] is False
    assert audit["training_triggered"] is False
    assert audit["recall_mutated"] is False
    assert flags["runtime_recall_active"] is False
    assert flags["provider_calls_enabled"] is False
    assert flags["action_execution_enabled"] is False
    assert flags["training_enabled"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation_executes_one_trial_and_rejects_casual(tmp_path, monkeypatch):
    from orchestration.runtime import v15_explicit_canonical_memory_write_trial_report as report_module

    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "v15i.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "v15i.json")
    data = write_explicit_canonical_memory_write_trial_report(tmp_path / "trial.jsonl")
    assert data["success_safe"] is True
    assert data["success_payload"]["result"]["record_written"] is True
    assert data["casual_rejected"] is True
    assert report_module.REPORT_MD.exists()
    assert report_module.REPORT_JSON.exists()


def test_build_report_data_uses_expected_final_recommendation(tmp_path):
    data = build_explicit_canonical_memory_write_trial_report_data(tmp_path / "trial.jsonl")
    assert data["final_recommendation"] == "PROCEED_RECALL_BRIDGE_LIMITED_TRIAL_DESIGN"
    assert data["approval_format"].startswith(APPROVAL_HEADER)


def test_script_runs_with_exact_approval(tmp_path):
    candidate = build_v15i_sample_memory_candidate()
    approval = build_v15i_approval_text(candidate["memory_candidate_id"])
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/ask_delta_canonical_write_trial.py",
            "--question",
            "What is HYB1?",
            "--answer",
            "HYB1 is active.",
            "--feedback",
            "No, HYB1 is not active. It is dormant and env-gated. Model B remains default.",
            "--approval",
            approval,
            "--store-path",
            str(tmp_path / "trial.jsonl"),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    output = completed.stdout.lower()
    assert '"record_written": true' in output
    assert '"active_for_recall": false' in output
    assert '"training_triggered": false' in output
