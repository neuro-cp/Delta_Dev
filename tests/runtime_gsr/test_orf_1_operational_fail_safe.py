from __future__ import annotations

import json
import os
from pathlib import Path

from orchestration.runtime.e2e_1_durable_runtime_state import DurableRuntimeStateStore, default_clean_checkpoint_state
from orchestration.runtime import orf_1_operational_fail_safe as orf


def _state_dir(tmp_path: Path) -> Path:
    state = tmp_path / "runtime-state"
    store = DurableRuntimeStateStore(state, runtime_session_id="orf-test")
    store.write_checkpoint("checkpoint-orf", default_clean_checkpoint_state(mission_id="mission-orf"))
    return state


def test_orf_1a_startup_preflight_accepts_clean_controlled_state(tmp_path: Path):
    state = _state_dir(tmp_path)
    result = orf.run_startup_preflight(
        repository_root=tmp_path,
        branch_name="codex/delta-cognitive-core",
        expected_branch="codex/delta-cognitive-core",
        staged_files=(),
        dirty_files=("reports/RC4_X.md",),
        acknowledged_dirty_prefixes=("reports/RC4_",),
        state_dir=state,
        thresholds=orf.OperationalThresholds(minimum_free_disk_to_begin_bytes=1, hard_stop_free_disk_bytes=1),
    )

    assert result.accepted is True
    assert result.nothing_staged is True
    assert result.dirty_files_acknowledged is True
    assert result.emergency_stop_available is True
    assert result.safety["starts_runtime"] is False

    blocked = orf.run_startup_preflight(
        repository_root=tmp_path,
        branch_name="other",
        expected_branch="codex/delta-cognitive-core",
        staged_files=("x.py",),
        dirty_files=("unexpected.py",),
        acknowledged_dirty_prefixes=("reports/RC4_",),
        state_dir=state,
        thresholds=orf.OperationalThresholds(minimum_free_disk_to_begin_bytes=1, hard_stop_free_disk_bytes=1),
    )
    assert blocked.accepted is False
    assert blocked.branch_ok is False
    assert blocked.nothing_staged is False


def test_orf_1b_single_instance_lock_denies_live_process_and_recovers_stale(tmp_path: Path):
    live_lock = tmp_path / "live.lock"
    live_lock.write_text(json.dumps({"process_id": os.getpid()}), encoding="utf-8")
    live = orf.acquire_runtime_lock(live_lock, session_id="session", runtime_mode="development_runtime", last_clean_checkpoint_id="checkpoint")
    assert live.accepted is False
    assert live.reason == "live_process_lock_present"

    stale_lock = tmp_path / "stale.lock"
    stale_lock.write_text(json.dumps({"process_id": 99999999}), encoding="utf-8")
    stale = orf.acquire_runtime_lock(stale_lock, session_id="session", runtime_mode="development_runtime", last_clean_checkpoint_id="checkpoint")
    assert stale.accepted is True
    assert stale.stale_lock_removed is True
    assert stale.live_process_override_performed is False


def test_orf_1c_emergency_stop_records_events_and_requires_restart(tmp_path: Path):
    state = _state_dir(tmp_path)
    store = DurableRuntimeStateStore(state, runtime_session_id="orf-stop")
    result = orf.emergency_stop_runtime(store, runtime_mode="development_runtime", operation="sandbox_execution")

    assert result.accepted is True
    assert result.runtime_mode_after == "stopped"
    assert result.new_attempts_prevented is True
    assert result.writes_prevented is True
    assert result.subprocesses_prevented is True
    assert result.durable_stop_event_written is True
    assert result.explicit_restart_required is True
    assert "runtime_stopping" in (state / "runtime_events.jsonl").read_text(encoding="utf-8")


def test_orf_1d_1e_watchdog_detects_resource_and_heartbeat_faults(tmp_path: Path):
    state = _state_dir(tmp_path)
    sample = orf.collect_operational_sample(
        runtime_mode="development_runtime",
        state_dir=state,
        queue_size=99,
        repeated_identical_failure_count=3,
        consecutive_crash_count=0,
        scheduler_heartbeat_monotonic=0.0,
        ui_heartbeat_monotonic=0.0,
    )
    decision = orf.evaluate_watchdog_sample(
        sample,
        orf.OperationalThresholds(
            minimum_free_disk_to_begin_bytes=1,
            hard_stop_free_disk_bytes=1,
            maximum_queue_size=10,
            maximum_repeated_identical_failures=3,
            maximum_stale_heartbeat_seconds=1,
        ),
    )

    assert decision.accepted is True
    assert "queue_growth_limit_exceeded" in decision.reasons
    assert "repeated_identical_failure_limit" in decision.reasons
    assert decision.pause_new_work is True
    assert decision.authorizes_repair is False
    assert decision.applies_source is False

    timeout_sample = orf.OperationalSample(
        **{
            **sample.__dict__,
            "sample_id": "timeout-sample",
            "subprocess_duration_seconds": 500.0,
            "queue_size": 0,
            "repeated_identical_failure_count": 0,
            "scheduler_heartbeat_age_seconds": 0.0,
            "ui_heartbeat_age_seconds": 0.0,
        }
    )
    timeout = orf.evaluate_watchdog_sample(timeout_sample, orf.OperationalThresholds(maximum_subprocess_duration_seconds=1, minimum_free_disk_to_begin_bytes=1, hard_stop_free_disk_bytes=1))
    assert timeout.terminate_child_process is True


def test_orf_1f_model_provider_failures_pause_without_substitution(tmp_path: Path):
    state = _state_dir(tmp_path)
    store = DurableRuntimeStateStore(state, runtime_session_id="orf-model")
    failure = store.record_failure(
        phase="model_provider",
        operation="architecture synthesis",
        expected_transition="bounded model result",
        observed_transition="malformed output",
        first_incorrect_transition="model_result_parse_failed",
        responsible="provider_result_parser",
        recovery_recommendation="pause_mission_request_operator_review",
    )
    assert failure["operator_review_required"] is True
    assert failure["recovery_recommendation"] == "pause_mission_request_operator_review"


def test_orf_1g_1h_known_good_and_schema_compatibility_fail_closed(tmp_path: Path):
    state = _state_dir(tmp_path)
    store = DurableRuntimeStateStore(state, runtime_session_id="orf-schema")
    current = state / "checkpoints" / "checkpoint.current.json"
    data = json.loads(current.read_text(encoding="utf-8"))
    assert data["schema_version"] == "e2e_1_durability.v1"

    bad = dict(data)
    bad["schema_version"] = "future.v999"
    assert bad["schema_version"] != data["schema_version"]
    recovery = store.recover_startup()
    assert recovery.development_runtime_started is False
    assert recovery.live_runtime_started is False


def test_orf_1i_external_backup_restore_verifies_manifest_and_stays_paused(tmp_path: Path):
    state = _state_dir(tmp_path)
    store = DurableRuntimeStateStore(state, runtime_session_id="orf-backup")
    store.append_event("proposal_queued", phase="backup", proposal_id="proposal-backup")
    store.write_intent("auth-consume", "authorization_consumption", authorization_id="auth-backup")

    manifest = orf.export_runtime_backup(state, tmp_path / "backup")
    restored = orf.restore_runtime_backup(manifest, tmp_path / "restored")

    assert manifest.files
    assert manifest.secrets_included is False
    assert manifest.sandboxes_included is False
    assert restored.accepted is True
    assert restored.integrity_verified is True
    assert restored.startup_paused is True
    assert restored.authorization_revived is False
    assert restored.mission_resumed is False


def test_orf_1j_morning_after_report_distinguishes_pending_blocked_and_uncertain(tmp_path: Path):
    state = _state_dir(tmp_path)
    sample = orf.collect_operational_sample(runtime_mode="stopped", state_dir=state)
    report = orf.generate_morning_after_report(
        parent_mission="language mission",
        stop_reason="operator_pause",
        remaining_disk_bytes=sample.free_disk_bytes,
        last_clean_checkpoint="checkpoint-orf",
        attempts_completed=1,
        proposals_created=("proposal-1",),
        proposals_awaiting_review=("proposal-1",),
        failures_and_crashes=("model-timeout",),
        unresolved_journal_entries=("journal-1",),
    )

    assert report.status_by_area["review"] == "pending review"
    assert report.status_by_area["recovery"] == "uncertain after crash"
    assert report.recommended_next_operator_action == "review pending items"


def test_orf_1k_safe_unattended_pilot_remains_stopped_and_review_gated(tmp_path: Path):
    result = orf.run_safe_unattended_pilot_fixture(tmp_path / "runtime-state")

    assert result["attempts_completed"] == 1
    assert result["proposal_applied_itself"] is False
    assert result["capability_activated_itself"] is False
    assert result["stop"]["runtime_mode_after"] == "stopped"
    assert result["recovery"]["development_runtime_started"] is False
    assert result["recovery"]["live_runtime_started"] is False
    assert result["report"]["proposals_awaiting_review"] == ("proposal-queued",)


def test_orf_1_acceptance_markers_are_declared():
    assert set(orf.ORF_1_MARKERS) == {
        "ORF_1A_STARTUP_PREFLIGHT_ACCEPTED",
        "ORF_1B_SINGLE_INSTANCE_LOCK_CONTROL_ACCEPTED",
        "ORF_1C_EMERGENCY_STOP_ACCEPTED",
        "ORF_1D_WATCHDOG_HEARTBEAT_ACCEPTED",
        "ORF_1E_RESOURCE_EXHAUSTION_CONTROL_ACCEPTED",
        "ORF_1F_MODEL_PROVIDER_FAILURE_HANDLING_ACCEPTED",
        "ORF_1G_STARTUP_FAILURE_ROLLBACK_BOUNDARY_ACCEPTED",
        "ORF_1H_STATE_SCHEMA_COMPATIBILITY_ACCEPTED",
        "ORF_1I_EXTERNAL_BACKUP_RESTORE_ACCEPTED",
        "ORF_1J_MORNING_AFTER_REPORT_ACCEPTED",
        "ORF_1K_SAFE_UNATTENDED_PILOT_ACCEPTED",
    }
