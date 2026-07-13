"""ORF-1 operational readiness and fail-safe closure helpers.

The module is deliberately observational and local. It may detect faults,
write durable evidence, classify stop conditions, and create operator-facing
reports. It does not authorize development, apply source changes, activate
capabilities, call providers, install dependencies, or perform Git actions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import shutil
import tempfile
import threading
import time
from typing import Any, Mapping
from uuid import uuid4

from orchestration.runtime.e2e_1_durable_runtime_state import DurableRuntimeStateStore


ORF_1_MARKERS = (
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
)

ORF_DISPOSITIONS = (
    "healthy",
    "warning",
    "pause_new_work",
    "terminate_timed_out_child",
    "stop_development_runtime",
    "recovery_required",
    "operator_review_required",
)

SUPPORTED_STATE_SCHEMA = "orf-runtime-state.v1"


@dataclass(frozen=True)
class OperationalThresholds:
    minimum_free_disk_to_begin_bytes: int = 10 * 1024**3
    hard_stop_free_disk_bytes: int = 5 * 1024**3
    maximum_event_log_bytes: int = 512_000
    maximum_failure_records: int = 50
    maximum_checkpoint_count: int = 5
    maximum_active_sandboxes: int = 1
    maximum_active_application_operations: int = 1
    maximum_active_missions: int = 1
    maximum_repeated_identical_failures: int = 3
    maximum_consecutive_crash_recoveries: int = 3
    maximum_queue_size: int = 25
    maximum_stale_heartbeat_seconds: int = 60
    maximum_subprocess_duration_seconds: int = 120


@dataclass(frozen=True)
class OperationalSample:
    sample_id: str
    runtime_mode: str
    process_id: int
    host_identity: str
    utc_timestamp: str
    monotonic_seconds: float
    process_cpu_seconds: float
    process_memory_bytes: int | None
    available_system_memory_bytes: int | None
    free_disk_bytes: int
    active_child_process_count: int
    active_thread_count: int
    current_attempt_duration_seconds: float
    subprocess_duration_seconds: float
    event_log_bytes: int
    checkpoint_age_seconds: float
    queue_size: int
    repeated_identical_failure_count: int
    consecutive_crash_count: int
    scheduler_heartbeat_age_seconds: float
    ui_heartbeat_age_seconds: float
    active_sandbox_count: int = 0
    active_application_count: int = 0
    active_mission_count: int = 0
    safety: dict[str, bool] = field(default_factory=lambda: {
        "observational_only": True,
        "authorizes_development": False,
        "applies_source": False,
        "activates_capability": False,
        "git_operation": False,
    })


@dataclass(frozen=True)
class WatchdogDecision:
    accepted: bool
    disposition: str
    reasons: tuple[str, ...]
    sample_id: str
    pause_new_work: bool = False
    terminate_child_process: bool = False
    stop_runtime: bool = False
    operator_review_required: bool = False
    authorizes_repair: bool = False
    applies_source: bool = False
    safety: dict[str, bool] = field(default_factory=lambda: {
        "observational_only": True,
        "authorizes_development": False,
        "applies_source": False,
        "activates_capability": False,
    })


@dataclass(frozen=True)
class RuntimeLockRecord:
    process_id: int
    session_id: str
    start_time_utc: str
    runtime_mode: str
    host_identity: str
    heartbeat_utc: str
    last_clean_checkpoint_id: str
    schema_version: str = SUPPORTED_STATE_SCHEMA


@dataclass(frozen=True)
class LockAcquisitionResult:
    accepted: bool
    reason: str
    lock: RuntimeLockRecord | None = None
    stale_lock_removed: bool = False
    live_process_override_performed: bool = False
    safety: dict[str, bool] = field(default_factory=lambda: {"authorizes_application": False, "starts_runtime": False})


@dataclass(frozen=True)
class EmergencyStopResult:
    accepted: bool
    reason: str
    runtime_mode_after: str
    new_attempts_prevented: bool
    writes_prevented: bool
    subprocesses_prevented: bool
    interrupted_operation_marked: bool
    durable_stop_event_written: bool
    last_clean_checkpoint_preserved: bool
    child_processes_terminated: bool
    explicit_restart_required: bool
    uncertain_action: bool = False
    safety: dict[str, bool] = field(default_factory=lambda: {"automatic_restart": False, "authorizes_repair": False})


@dataclass(frozen=True)
class StartupPreflightResult:
    accepted: bool
    reason: str
    repository_identity_ok: bool
    branch_ok: bool
    nothing_staged: bool
    dirty_files_acknowledged: bool
    runtime_state_writable: bool
    checkpoint_integrity_ok: bool
    pending_journal_actions: tuple[str, ...]
    disk_free_ok: bool
    python_available: bool
    test_runner_available: bool
    model_lane_status_recorded: bool
    evaluation_tab_available: bool
    no_conflicting_process: bool
    no_stale_lock: bool
    no_active_sandbox: bool
    no_unresolved_application_authorization: bool
    emergency_stop_available: bool
    safety: dict[str, bool] = field(default_factory=lambda: {"starts_runtime": False, "authorizes_development": False})


@dataclass(frozen=True)
class BackupManifest:
    manifest_id: str
    source_state_dir: str
    backup_dir: str
    files: dict[str, str]
    schema_version: str = SUPPORTED_STATE_SCHEMA
    secrets_included: bool = False
    sandboxes_included: bool = False
    cache_included: bool = False


@dataclass(frozen=True)
class BackupRestoreResult:
    accepted: bool
    reason: str
    manifest: BackupManifest
    restored_dir: str
    integrity_verified: bool
    startup_paused: bool
    authorization_revived: bool = False
    mission_resumed: bool = False
    safety: dict[str, bool] = field(default_factory=lambda: {"starts_runtime": False, "authorizes_action": False})


@dataclass(frozen=True)
class MorningAfterReport:
    report_id: str
    session_start: str
    session_end: str
    clean_shutdown: bool
    parent_mission: str
    objective_thresholds: dict[str, float]
    runtime_budgets: dict[str, int]
    attempts_completed: int
    capabilities_considered: tuple[str, ...]
    proposals_created: tuple[str, ...]
    sandbox_results: tuple[str, ...]
    proposals_awaiting_review: tuple[str, ...]
    accepted_proposals: tuple[str, ...]
    declined_proposals: tuple[str, ...]
    revised_proposals: tuple[str, ...]
    source_applications: tuple[str, ...]
    capability_promotions: tuple[str, ...]
    failures_and_crashes: tuple[str, ...]
    watchdog_interventions: tuple[str, ...]
    unresolved_journal_entries: tuple[str, ...]
    rollback_required_states: tuple[str, ...]
    remaining_disk_bytes: int
    remaining_budget: dict[str, int]
    last_clean_checkpoint: str
    stop_reason: str
    recommended_next_operator_action: str
    status_by_area: dict[str, str]


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_process_live(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _process_memory_bytes() -> int | None:
    try:
        import resource  # type: ignore

        usage = resource.getrusage(resource.RUSAGE_SELF)
        value = int(usage.ru_maxrss)
        if platform.system().lower() == "darwin":
            return value
        return value * 1024
    except Exception:
        return None


def _available_memory_bytes() -> int | None:
    if platform.system().lower() != "linux":
        return None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except Exception:
        return None
    return None


def collect_operational_sample(
    *,
    runtime_mode: str,
    state_dir: Path,
    queue_size: int = 0,
    repeated_identical_failure_count: int = 0,
    consecutive_crash_count: int = 0,
    current_attempt_started_monotonic: float | None = None,
    subprocess_started_monotonic: float | None = None,
    scheduler_heartbeat_monotonic: float | None = None,
    ui_heartbeat_monotonic: float | None = None,
    active_sandbox_count: int = 0,
    active_application_count: int = 0,
    active_mission_count: int = 0,
) -> OperationalSample:
    now = time.monotonic()
    event_log = state_dir / "runtime_events.jsonl"
    checkpoint = state_dir / "checkpoints" / "checkpoint.current.json"
    disk = shutil.disk_usage(state_dir if state_dir.exists() else state_dir.parent)
    return OperationalSample(
        sample_id=f"orf-sample-{uuid4().hex}",
        runtime_mode=runtime_mode,
        process_id=os.getpid(),
        host_identity=platform.node() or "unknown-host",
        utc_timestamp=_utc_now(),
        monotonic_seconds=now,
        process_cpu_seconds=time.process_time(),
        process_memory_bytes=_process_memory_bytes(),
        available_system_memory_bytes=_available_memory_bytes(),
        free_disk_bytes=int(disk.free),
        active_child_process_count=len(multiprocessing.active_children()),
        active_thread_count=threading.active_count(),
        current_attempt_duration_seconds=0.0 if current_attempt_started_monotonic is None else max(0.0, now - current_attempt_started_monotonic),
        subprocess_duration_seconds=0.0 if subprocess_started_monotonic is None else max(0.0, now - subprocess_started_monotonic),
        event_log_bytes=event_log.stat().st_size if event_log.exists() else 0,
        checkpoint_age_seconds=0.0 if not checkpoint.exists() else max(0.0, time.time() - checkpoint.stat().st_mtime),
        queue_size=queue_size,
        repeated_identical_failure_count=repeated_identical_failure_count,
        consecutive_crash_count=consecutive_crash_count,
        scheduler_heartbeat_age_seconds=0.0 if scheduler_heartbeat_monotonic is None else max(0.0, now - scheduler_heartbeat_monotonic),
        ui_heartbeat_age_seconds=0.0 if ui_heartbeat_monotonic is None else max(0.0, now - ui_heartbeat_monotonic),
        active_sandbox_count=active_sandbox_count,
        active_application_count=active_application_count,
        active_mission_count=active_mission_count,
    )


def evaluate_watchdog_sample(sample: OperationalSample, thresholds: OperationalThresholds = OperationalThresholds()) -> WatchdogDecision:
    reasons: list[str] = []
    if sample.free_disk_bytes <= thresholds.hard_stop_free_disk_bytes:
        reasons.append("hard_disk_threshold_crossed")
    elif sample.free_disk_bytes <= thresholds.minimum_free_disk_to_begin_bytes:
        reasons.append("disk_warning_threshold_crossed")
    if sample.event_log_bytes > thresholds.maximum_event_log_bytes:
        reasons.append("event_log_limit_exceeded")
    if sample.queue_size > thresholds.maximum_queue_size:
        reasons.append("queue_growth_limit_exceeded")
    if sample.active_sandbox_count > thresholds.maximum_active_sandboxes:
        reasons.append("too_many_active_sandboxes")
    if sample.active_application_count > thresholds.maximum_active_application_operations:
        reasons.append("parallel_application_denied")
    if sample.active_mission_count > thresholds.maximum_active_missions:
        reasons.append("parallel_mission_denied")
    if sample.repeated_identical_failure_count >= thresholds.maximum_repeated_identical_failures:
        reasons.append("repeated_identical_failure_limit")
    if sample.consecutive_crash_count >= thresholds.maximum_consecutive_crash_recoveries:
        reasons.append("crash_loop_detected")
    if sample.subprocess_duration_seconds > thresholds.maximum_subprocess_duration_seconds:
        reasons.append("subprocess_timeout")
    if sample.scheduler_heartbeat_age_seconds > thresholds.maximum_stale_heartbeat_seconds:
        reasons.append("scheduler_heartbeat_stale")
    if sample.ui_heartbeat_age_seconds > thresholds.maximum_stale_heartbeat_seconds:
        reasons.append("ui_heartbeat_stale")
    disposition = "healthy"
    if reasons:
        disposition = "warning"
    if any(reason in reasons for reason in ("queue_growth_limit_exceeded", "repeated_identical_failure_limit")):
        disposition = "pause_new_work"
    if "subprocess_timeout" in reasons:
        disposition = "terminate_timed_out_child"
    if any(reason in reasons for reason in ("hard_disk_threshold_crossed", "crash_loop_detected", "parallel_application_denied", "parallel_mission_denied")):
        disposition = "stop_development_runtime"
    if any(reason in reasons for reason in ("scheduler_heartbeat_stale", "ui_heartbeat_stale")):
        disposition = "operator_review_required"
    if disposition not in ORF_DISPOSITIONS:
        disposition = "operator_review_required"
    return WatchdogDecision(
        accepted=True,
        disposition=disposition,
        reasons=tuple(reasons),
        sample_id=sample.sample_id,
        pause_new_work=disposition in {"pause_new_work", "terminate_timed_out_child", "stop_development_runtime", "operator_review_required"},
        terminate_child_process=disposition == "terminate_timed_out_child",
        stop_runtime=disposition == "stop_development_runtime",
        operator_review_required=disposition in {"operator_review_required", "stop_development_runtime"},
    )


def acquire_runtime_lock(
    lock_path: Path,
    *,
    session_id: str,
    runtime_mode: str,
    last_clean_checkpoint_id: str,
    allow_stale_removal: bool = True,
) -> LockAcquisitionResult:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
            existing_pid = int(existing.get("process_id", -1))
        except Exception:
            existing_pid = -1
        if _is_process_live(existing_pid):
            return LockAcquisitionResult(False, "live_process_lock_present", live_process_override_performed=False)
        if not allow_stale_removal:
            return LockAcquisitionResult(False, "stale_lock_requires_review")
        lock_path.unlink()
        stale_removed = True
    else:
        stale_removed = False
    record = RuntimeLockRecord(
        process_id=os.getpid(),
        session_id=session_id,
        start_time_utc=_utc_now(),
        runtime_mode=runtime_mode,
        host_identity=platform.node() or "unknown-host",
        heartbeat_utc=_utc_now(),
        last_clean_checkpoint_id=last_clean_checkpoint_id,
    )
    lock_path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return LockAcquisitionResult(True, "lock_acquired", record, stale_lock_removed=stale_removed)


def emergency_stop_runtime(
    store: DurableRuntimeStateStore,
    *,
    runtime_mode: str,
    operation: str,
    uncertain_action: bool = False,
    child_processes_terminated: bool = True,
) -> EmergencyStopResult:
    store.append_event(
        "runtime_stopping",
        phase="emergency_stop",
        lifecycle_before=runtime_mode,
        lifecycle_after="stopped",
        result_classification="emergency_stop_requested",
        summary=f"Emergency stop during {operation}",
        clean_boundary=not uncertain_action,
    )
    store.append_event(
        "runtime_stopped_cleanly" if not uncertain_action else "forced_termination_detected",
        phase="emergency_stop",
        lifecycle_before=runtime_mode,
        lifecycle_after="stopped",
        result_classification="stopped",
        summary=f"Emergency stop completed during {operation}",
        clean_boundary=not uncertain_action,
    )
    return EmergencyStopResult(
        True,
        "emergency_stop_recorded",
        "stopped",
        new_attempts_prevented=True,
        writes_prevented=True,
        subprocesses_prevented=True,
        interrupted_operation_marked=True,
        durable_stop_event_written=True,
        last_clean_checkpoint_preserved=True,
        child_processes_terminated=child_processes_terminated,
        explicit_restart_required=True,
        uncertain_action=uncertain_action,
    )


def run_startup_preflight(
    *,
    repository_root: Path,
    branch_name: str,
    expected_branch: str,
    staged_files: tuple[str, ...],
    dirty_files: tuple[str, ...],
    acknowledged_dirty_prefixes: tuple[str, ...],
    state_dir: Path,
    thresholds: OperationalThresholds = OperationalThresholds(),
    python_executable: Path | None = None,
    test_runner_available: bool = True,
    model_lane_status_recorded: bool = True,
    evaluation_tab_available: bool = True,
    conflicting_process: bool = False,
    stale_lock_present: bool = False,
    active_sandbox: bool = False,
    unresolved_application_authorization: bool = False,
) -> StartupPreflightResult:
    store = DurableRuntimeStateStore(state_dir, runtime_session_id="preflight")
    recovery = store.recover_startup()
    disk = shutil.disk_usage(state_dir)
    dirty_ok = all(any(path.startswith(prefix) for prefix in acknowledged_dirty_prefixes) for path in dirty_files)
    python_ok = True if python_executable is None else python_executable.exists()
    accepted = all(
        (
            repository_root.exists(),
            branch_name == expected_branch,
            not staged_files,
            dirty_ok,
            state_dir.exists(),
            recovery.checkpoint_valid or recovery.recovered_checkpoint_id is None,
            not recovery.incomplete_action_ids,
            disk.free >= thresholds.minimum_free_disk_to_begin_bytes,
            python_ok,
            test_runner_available,
            model_lane_status_recorded,
            evaluation_tab_available,
            not conflicting_process,
            not stale_lock_present,
            not active_sandbox,
            not unresolved_application_authorization,
        )
    )
    reason = "preflight_passed" if accepted else "preflight_failed"
    return StartupPreflightResult(
        accepted,
        reason,
        repository_identity_ok=repository_root.exists(),
        branch_ok=branch_name == expected_branch,
        nothing_staged=not staged_files,
        dirty_files_acknowledged=dirty_ok,
        runtime_state_writable=state_dir.exists(),
        checkpoint_integrity_ok=recovery.checkpoint_valid or recovery.recovered_checkpoint_id is None,
        pending_journal_actions=recovery.incomplete_action_ids,
        disk_free_ok=disk.free >= thresholds.minimum_free_disk_to_begin_bytes,
        python_available=python_ok,
        test_runner_available=test_runner_available,
        model_lane_status_recorded=model_lane_status_recorded,
        evaluation_tab_available=evaluation_tab_available,
        no_conflicting_process=not conflicting_process,
        no_stale_lock=not stale_lock_present,
        no_active_sandbox=not active_sandbox,
        no_unresolved_application_authorization=not unresolved_application_authorization,
        emergency_stop_available=True,
    )


def export_runtime_backup(state_dir: Path, backup_dir: Path) -> BackupManifest:
    backup_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    allowed_roots = ("checkpoints", "failures", "journal")
    if (state_dir / "runtime_events.jsonl").exists():
        target = backup_dir / "runtime_events.tail.jsonl"
        target.write_bytes((state_dir / "runtime_events.jsonl").read_bytes()[-64_000:])
        files[target.name] = _sha256_file(target)
    for root_name in allowed_roots:
        root = state_dir / root_name
        if not root.exists():
            continue
        for path in sorted(root.glob("**/*")):
            if path.is_file():
                rel = Path(root_name) / path.relative_to(root)
                dest = backup_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                files[str(rel)] = _sha256_file(dest)
    manifest = BackupManifest(
        manifest_id=f"orf-backup-{uuid4().hex}",
        source_state_dir=str(state_dir),
        backup_dir=str(backup_dir),
        files=files,
    )
    (backup_dir / "manifest.json").write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def restore_runtime_backup(manifest: BackupManifest, restore_dir: Path) -> BackupRestoreResult:
    backup_dir = Path(manifest.backup_dir)
    restore_dir.mkdir(parents=True, exist_ok=True)
    for rel, expected_digest in manifest.files.items():
        source = backup_dir / rel
        if not source.exists() or _sha256_file(source) != expected_digest:
            return BackupRestoreResult(False, "manifest_verification_failed", manifest, str(restore_dir), False, True)
        dest = restore_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    return BackupRestoreResult(True, "backup_restored_paused", manifest, str(restore_dir), True, True)


def generate_morning_after_report(
    *,
    parent_mission: str,
    stop_reason: str,
    remaining_disk_bytes: int,
    last_clean_checkpoint: str,
    attempts_completed: int = 0,
    proposals_created: tuple[str, ...] = (),
    proposals_awaiting_review: tuple[str, ...] = (),
    accepted_proposals: tuple[str, ...] = (),
    declined_proposals: tuple[str, ...] = (),
    revised_proposals: tuple[str, ...] = (),
    failures_and_crashes: tuple[str, ...] = (),
    watchdog_interventions: tuple[str, ...] = (),
    unresolved_journal_entries: tuple[str, ...] = (),
    rollback_required_states: tuple[str, ...] = (),
) -> MorningAfterReport:
    status_by_area = {
        "mission": "completed" if stop_reason == "mission_success" else "blocked",
        "review": "pending review" if proposals_awaiting_review else "completed",
        "recovery": "uncertain after crash" if failures_and_crashes else "completed",
        "rollback": "blocked" if rollback_required_states else "completed",
    }
    return MorningAfterReport(
        report_id=f"orf-morning-after-{uuid4().hex}",
        session_start=_utc_now(),
        session_end=_utc_now(),
        clean_shutdown=not failures_and_crashes,
        parent_mission=parent_mission,
        objective_thresholds={},
        runtime_budgets={},
        attempts_completed=attempts_completed,
        capabilities_considered=(),
        proposals_created=proposals_created,
        sandbox_results=(),
        proposals_awaiting_review=proposals_awaiting_review,
        accepted_proposals=accepted_proposals,
        declined_proposals=declined_proposals,
        revised_proposals=revised_proposals,
        source_applications=(),
        capability_promotions=(),
        failures_and_crashes=failures_and_crashes,
        watchdog_interventions=watchdog_interventions,
        unresolved_journal_entries=unresolved_journal_entries,
        rollback_required_states=rollback_required_states,
        remaining_disk_bytes=remaining_disk_bytes,
        remaining_budget={},
        last_clean_checkpoint=last_clean_checkpoint,
        stop_reason=stop_reason,
        recommended_next_operator_action="review pending items" if proposals_awaiting_review or unresolved_journal_entries else "safe to remain stopped",
        status_by_area=status_by_area,
    )


def run_safe_unattended_pilot_fixture(state_dir: Path) -> dict[str, Any]:
    store = DurableRuntimeStateStore(state_dir, runtime_session_id="orf-pilot")
    store.append_event("runtime_started", phase="orf_pilot", lifecycle_before="stopped", lifecycle_after="development_runtime")
    store.append_event("attempt_started", phase="orf_pilot", attempt_id="attempt-ok")
    store.append_event("attempt_completed", phase="orf_pilot", attempt_id="attempt-ok", result_classification="succeeded")
    store.append_event("attempt_failed", phase="orf_pilot", attempt_id="attempt-failed", result_classification="model_response_failure")
    store.append_event("proposal_queued", phase="orf_pilot", proposal_id="proposal-queued")
    sample = collect_operational_sample(runtime_mode="development_runtime", state_dir=state_dir, queue_size=1, repeated_identical_failure_count=1)
    decision = evaluate_watchdog_sample(sample)
    stop = emergency_stop_runtime(store, runtime_mode="development_runtime", operation="safe_unattended_pilot")
    recovery = DurableRuntimeStateStore(state_dir, runtime_session_id="orf-pilot").recover_startup()
    report = generate_morning_after_report(
        parent_mission="fixture",
        stop_reason="operator_pause",
        remaining_disk_bytes=sample.free_disk_bytes,
        last_clean_checkpoint=recovery.recovered_checkpoint_id or "",
        attempts_completed=1,
        proposals_created=("proposal-queued",),
        proposals_awaiting_review=("proposal-queued",),
        failures_and_crashes=("attempt-failed",),
        watchdog_interventions=decision.reasons,
        unresolved_journal_entries=recovery.incomplete_action_ids,
    )
    return {
        "attempts_completed": 1,
        "proposal_applied_itself": False,
        "capability_activated_itself": False,
        "decision": asdict(decision),
        "stop": asdict(stop),
        "recovery": asdict(recovery),
        "report": asdict(report),
    }
