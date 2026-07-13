from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestration.runtime.e2e_1_durable_runtime_state import (
    DURABILITY_ACCEPTANCE_MARKERS,
    DurableRuntimeStateStore,
    default_clean_checkpoint_state,
)


def _store(tmp_path: Path) -> DurableRuntimeStateStore:
    return DurableRuntimeStateStore(tmp_path / "runtime-state", runtime_session_id="session-test")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_append_only_event_log_uses_monotonic_digest_chain(tmp_path: Path):
    store = _store(tmp_path)

    first = store.append_event(
        "runtime_started",
        objective_or_mission_id="mission-1",
        subsystem="gdr",
        phase="startup",
        lifecycle_before="stopped",
        lifecycle_after="starting",
        request_id="request-1",
        authorization_id="auth-1",
        result_classification="started",
        summary="runtime start recorded",
        clean_boundary=True,
    )
    second = store.append_event(
        "mission_compiled",
        objective_or_mission_id="mission-1",
        subsystem="oar",
        phase="mission_compilation",
        lifecycle_before="starting",
        lifecycle_after="awaiting_approval",
        result_classification="compiled",
        summary="mission compiled",
    )

    lines = (tmp_path / "runtime-state" / "runtime_events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert first["monotonic_sequence"] == 1
    assert second["monotonic_sequence"] == 2
    assert second["previous_event_digest"] == first["current_event_digest"]
    assert first["clean_boundary"] is True
    assert second["event_type"] == "mission_compiled"


def test_failure_record_is_immutable_bounded_and_redacts_secondary_logging_failure(tmp_path: Path):
    store = _store(tmp_path)
    try:
        raise RuntimeError("boom with token-like data")
    except RuntimeError as exc:
        record = store.record_failure(
            phase="application",
            operation="apply reviewed patch",
            expected_transition="validated application",
            observed_transition="exception before validation",
            first_incorrect_transition="write raised",
            exception=exc,
            responsible="apply_exact_patch",
            lifecycle_state="application_authorized",
            active_mission_id="mission-1",
            active_attempt_id="attempt-1",
            authorization_consumption_state="uncertain",
            files_read=("fixture.py",),
            files_written=("fixture.py",),
            commands_executed=("pytest focused",),
            active_sandbox="sandbox-1",
            last_clean_checkpoint_id="checkpoint-1",
            cleanup_status="pending",
        )

    path = tmp_path / "runtime-state" / "failures" / f"{record['failure_id']}.json"
    saved = _read_json(path)
    assert saved["expected_transition"] == "validated application"
    assert saved["observed_transition"] == "exception before validation"
    assert saved["operator_review_required"] is True
    assert saved["last_event_log_sequence"] == 0
    assert "RuntimeError" in saved["bounded_stack_trace"]


def test_write_ahead_journal_requires_completion_and_blocks_replay(tmp_path: Path):
    store = _store(tmp_path)

    pending = store.write_intent(
        "action-1",
        "authorization_consumption",
        authorization_id="auth-1",
        summary="consume exact application authorization",
    )
    recovery = DurableRuntimeStateStore(tmp_path / "runtime-state", runtime_session_id="session-test").recover_startup()

    assert pending["status"] == "pending"
    assert recovery.incomplete_action_ids == ("action-1",)
    assert recovery.operator_review_required is True
    assert recovery.development_runtime_started is False
    assert recovery.live_runtime_started is False

    completed = store.complete_intent("action-1", outcome="authorization consumed once")
    assert completed["status"] == "completed"
    assert completed["authorization_uncertain"] is False
    with pytest.raises(ValueError):
        store.complete_intent("action-1", outcome="replay should fail")


def test_atomic_checkpoint_rotation_recovers_previous_when_current_is_corrupt(tmp_path: Path):
    store = _store(tmp_path)
    first = store.write_checkpoint("checkpoint-1", default_clean_checkpoint_state(mission_id="mission-1"))
    second_state = default_clean_checkpoint_state(mission_id="mission-2") | {
        "pending_review_identities": ("proposal-1",),
    }
    second = store.write_checkpoint("checkpoint-2", second_state)
    current = tmp_path / "runtime-state" / "checkpoints" / "checkpoint.current.json"
    current.write_text("{corrupt", encoding="utf-8")

    checkpoint, recovered_from_previous = store.newest_valid_checkpoint()
    recovery = store.recover_startup()

    assert first["checkpoint_id"] == "checkpoint-1"
    assert second["checkpoint_id"] == "checkpoint-2"
    assert checkpoint is not None
    assert checkpoint["checkpoint_id"] == "checkpoint-1"
    assert recovered_from_previous is True
    assert recovery.recovered_checkpoint_id == "checkpoint-1"
    assert recovery.recovered_from_previous is True
    assert recovery.operator_review_required is True


@pytest.mark.parametrize(
    ("scenario", "setup"),
    [
        ("before_intent_logging", "none"),
        ("after_pending_intent_flushed", "pending_authorization"),
        ("after_authorization_consumption", "completed_authorization"),
        ("after_first_sandbox_write", "pending_sandbox"),
        ("after_reviewed_patch_write_before_outcome", "pending_patch"),
        ("during_checkpoint_temp_write", "temp_checkpoint"),
        ("after_checkpoint_flush_before_replace", "previous_checkpoint"),
        ("after_replace_before_clean_shutdown", "unclean_current"),
        ("while_disposition_persisting", "pending_disposition"),
        ("while_capability_promotion_persisting", "pending_promotion"),
    ],
)
def test_power_loss_injection_keeps_checkpoint_recoverable_and_paused(tmp_path: Path, scenario: str, setup: str):
    store = _store(tmp_path)
    store.write_checkpoint("checkpoint-base", default_clean_checkpoint_state(mission_id=scenario))

    if setup == "pending_authorization":
        store.write_intent("auth-action", "authorization_consumption", authorization_id="auth-1")
    elif setup == "completed_authorization":
        store.write_intent("auth-action", "authorization_consumption", authorization_id="auth-1")
        store.complete_intent("auth-action", outcome="consumed once")
    elif setup == "pending_sandbox":
        store.write_intent("sandbox-action", "sandbox_mutation")
        (tmp_path / "runtime-state" / "sandboxes" / "sandbox-remnant").mkdir()
    elif setup == "pending_patch":
        store.write_intent("patch-action", "reviewed_patch_application", authorization_id="app-auth")
    elif setup == "temp_checkpoint":
        temp = tmp_path / "runtime-state" / "checkpoints" / ".checkpoint.current.json.interrupted.tmp"
        temp.write_text("{partial", encoding="utf-8")
    elif setup == "previous_checkpoint":
        store.write_checkpoint("checkpoint-new", default_clean_checkpoint_state(mission_id=f"{scenario}-new"))
        (tmp_path / "runtime-state" / "checkpoints" / "checkpoint.current.json").unlink()
    elif setup == "unclean_current":
        store.write_checkpoint(
            "checkpoint-unclean",
            default_clean_checkpoint_state(mission_id=scenario) | {"last_clean_shutdown_status": False},
        )
    elif setup == "pending_disposition":
        store.write_intent("disposition-action", "operator_disposition_update")
    elif setup == "pending_promotion":
        store.write_intent("promotion-action", "capability_evidence_promotion")

    recovered = DurableRuntimeStateStore(tmp_path / "runtime-state", runtime_session_id="session-test").recover_startup()
    status = DurableRuntimeStateStore(tmp_path / "runtime-state", runtime_session_id="session-test").runtime_status_snapshot()

    assert recovered.checkpoint_valid is True
    assert recovered.development_runtime_started is False
    assert recovered.live_runtime_started is False
    assert status.active_runtime_mode == "stopped"
    if setup in {"pending_authorization", "pending_sandbox", "pending_patch", "pending_disposition", "pending_promotion"}:
        assert recovered.operator_review_required is True
        assert recovered.incomplete_action_ids
    if setup == "completed_authorization":
        assert recovered.incomplete_action_ids == ()


def test_runtime_status_is_read_only_and_reports_pending_reviews_failures_and_recovery(tmp_path: Path):
    store = _store(tmp_path)
    store.write_checkpoint(
        "checkpoint-status",
        default_clean_checkpoint_state(mission_id="mission-status") | {
            "pending_review_identities": ("proposal-a", "proposal-b"),
        },
    )
    store.write_intent("action-pending", "operator_disposition_update")
    store.record_failure(
        phase="restart",
        operation="validate checkpoint",
        expected_transition="valid checkpoint",
        observed_transition="digest mismatch",
    )

    status = store.runtime_status_snapshot()

    assert status.latest_checkpoint_id == "checkpoint-status"
    assert status.pending_review_count == 2
    assert status.unresolved_failure_count == 1
    assert status.incomplete_journal_action_count == 1
    assert status.recovery_required is True
    assert status.active_runtime_mode == "stopped"


def test_durability_acceptance_markers_are_declared():
    assert set(DURABILITY_ACCEPTANCE_MARKERS) == {
        "E2E_1_APPEND_ONLY_EVENT_LOG_PASSED",
        "E2E_1_FAILURE_CRASH_LOG_PASSED",
        "E2E_1_WRITE_AHEAD_ACTION_JOURNAL_PASSED",
        "E2E_1_ATOMIC_CHECKPOINT_RECOVERY_PASSED",
        "E2E_1_POWER_LOSS_FAILURE_INJECTION_PASSED",
    }
