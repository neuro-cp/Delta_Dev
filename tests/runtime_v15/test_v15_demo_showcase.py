from __future__ import annotations

import subprocess
import sys

from orchestration.runtime.v15_demo_showcase import (
    build_runtime_demo_showcase,
    format_runtime_demo_showcase,
    validate_runtime_demo_showcase_safe,
)
from orchestration.runtime.v15_demo_showcase_report import write_runtime_demo_showcase_report
from orchestration.runtime.v15_explicit_canonical_memory_write_trial import execute_explicit_canonical_memory_write_trial
from orchestration.runtime.v15_explicit_canonical_memory_write_trial_report import (
    build_v15i_approval_text,
    build_v15i_sample_memory_candidate,
)


def _seed_trial_store(tmp_path):
    candidate = build_v15i_sample_memory_candidate()
    store = tmp_path / "trial.jsonl"
    execute_explicit_canonical_memory_write_trial(candidate, build_v15i_approval_text(candidate["memory_candidate_id"]), store)
    return store


def test_showcase_is_safe_and_report_only(tmp_path):
    payload = build_runtime_demo_showcase(_seed_trial_store(tmp_path))
    assert payload["all_steps_safe"] is True
    assert validate_runtime_demo_showcase_safe(payload)
    assert payload["invariant_flags"]["demo_showcase_enabled"] is True
    assert payload["invariant_flags"]["report_only"] is True
    assert payload["invariant_flags"]["provider_calls_enabled"] is False
    assert payload["invariant_flags"]["training_enabled"] is False


def test_showcase_contains_expected_steps(tmp_path):
    payload = build_runtime_demo_showcase(_seed_trial_store(tmp_path))
    names = [step["step_name"] for step in payload["showcase_steps"]]
    assert names == ["local_answer", "feedback_candidate_preview", "limited_recall_candidate_context"]
    assert payload["final_recommendation"] == "PROCEED_VALIDATED_EXPERIENCE_LEARNING_LOOP"


def test_showcase_does_not_write_memory(tmp_path):
    store = _seed_trial_store(tmp_path)
    before = store.read_text(encoding="utf-8")
    payload = build_runtime_demo_showcase(store)
    after = store.read_text(encoding="utf-8")
    assert before == after
    assert all(step["memory_write_performed"] is False for step in payload["showcase_steps"])
    assert all(step["canonical_write_performed"] is False for step in payload["showcase_steps"])


def test_showcase_formatter_mentions_safety(tmp_path):
    text = format_runtime_demo_showcase(build_runtime_demo_showcase(_seed_trial_store(tmp_path)))
    assert "no provider calls" in text
    assert "final_recommendation: PROCEED_VALIDATED_EXPERIENCE_LEARNING_LOOP" in text


def test_showcase_report_generation(tmp_path, monkeypatch):
    from orchestration.runtime import v15_demo_showcase_report as report_module

    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "v15k.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "v15k.json")
    data = write_runtime_demo_showcase_report(_seed_trial_store(tmp_path))
    assert data["showcase_safe"] is True
    assert report_module.REPORT_MD.exists()
    assert report_module.REPORT_JSON.exists()


def test_showcase_script_runs(tmp_path):
    completed = subprocess.run(
        [sys.executable, "scripts/delta_runtime_showcase.py", "--store-path", str(_seed_trial_store(tmp_path))],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "DELTA Runtime V1.5K Demo Showcase" in completed.stdout
    assert "all_steps_safe: True" in completed.stdout
