"""Narrow durable runtime evidence store for E2E-1 recovery validation.

This module is intentionally small and local-file based. It does not create a
database, start workers, execute commands, call providers, mutate source, or
authorize runtime actions. It only records bounded durable evidence that a
caller can inspect after process loss.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
from typing import Any, Mapping
from uuid import uuid4


SCHEMA_VERSION = "e2e_1_durability.v1"
MAX_EVENT_LOG_BYTES = 512_000
MAX_FAILURE_RECORDS = 50
MAX_TEXT_BYTES = 4096
MAX_STACK_BYTES = 8192
BACKUP_COUNT = 3

EVENT_CATEGORIES = (
    "runtime_started",
    "runtime_stopping",
    "runtime_stopped_cleanly",
    "runtime_recovered_unclean_shutdown",
    "mission_compiled",
    "mission_approved",
    "attempt_started",
    "attempt_completed",
    "attempt_failed",
    "proposal_created",
    "proposal_queued",
    "proposal_accepted",
    "proposal_declined",
    "proposal_revision_requested",
    "application_started",
    "application_completed",
    "application_failed",
    "rollback_required",
    "checkpoint_written",
    "checkpoint_recovered",
    "authorization_consumed",
    "authorization_replay_denied",
    "capability_promoted",
    "capability_activated",
    "capability_deactivated",
    "budget_exhausted",
    "stagnation_detected",
    "scope_violation",
    "integrity_failure",
    "unhandled_exception",
    "forced_termination_detected",
    "cleanup_failed",
)

CONSEQUENTIAL_ACTIONS = (
    "authorization_consumption",
    "sandbox_mutation",
    "reviewed_patch_application",
    "operator_disposition_update",
    "capability_evidence_promotion",
    "capability_activation",
    "checkpoint_replacement",
)

DURABILITY_ACCEPTANCE_MARKERS = (
    "E2E_1_APPEND_ONLY_EVENT_LOG_PASSED",
    "E2E_1_FAILURE_CRASH_LOG_PASSED",
    "E2E_1_WRITE_AHEAD_ACTION_JOURNAL_PASSED",
    "E2E_1_ATOMIC_CHECKPOINT_RECOVERY_PASSED",
    "E2E_1_POWER_LOSS_FAILURE_INJECTION_PASSED",
)

REDACTED_KEYS = {
    "api_key",
    "authorization",
    "authorization_header",
    "credential",
    "credentials",
    "password",
    "private_key",
    "secret",
    "token",
}


@dataclass(frozen=True)
class RuntimeRecoveryStatus:
    recovered_checkpoint_id: str | None
    recovered_from_previous: bool
    prior_shutdown_clean: bool
    event_log_valid: bool
    checkpoint_valid: bool
    incomplete_action_ids: tuple[str, ...]
    operator_review_required: bool
    development_runtime_started: bool = False
    live_runtime_started: bool = False
    recommendation: str = "review_required"


@dataclass(frozen=True)
class RuntimeStatusSnapshot:
    prior_shutdown_clean: bool
    latest_checkpoint_id: str | None
    current_event_sequence: int
    unresolved_failure_count: int
    incomplete_journal_action_count: int
    recovery_required: bool
    pending_review_count: int
    active_runtime_mode: str
    last_failure_summary: str | None


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _bounded_text(value: object, *, limit: int = MAX_TEXT_BYTES) -> str:
    text = str(value)
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return text
    return encoded[:limit].decode("utf-8", errors="ignore") + "...[truncated]"


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in REDACTED_KEYS:
                clean[key_text] = "[REDACTED]"
            else:
                clean[key_text] = _redact(item)
        return clean
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _bounded_text(value)
    return value


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(data: Mapping[str, Any] | str | bytes) -> str:
    if isinstance(data, Mapping):
        payload = _canonical_json(data).encode("utf-8")
    elif isinstance(data, str):
        payload = data.encode("utf-8")
    else:
        payload = data
    return hashlib.sha256(payload).hexdigest()


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _flush_file(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())


class DurableRuntimeStateStore:
    """Append-only evidence, action journal, and atomic checkpoint store."""

    def __init__(self, state_dir: str | Path, *, runtime_session_id: str | None = None) -> None:
        self.state_dir = Path(state_dir)
        self.runtime_session_id = runtime_session_id or f"session-{uuid4().hex}"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_safe_runtime_dir()
        for child in ("failures", "journal", "checkpoints", "sandboxes"):
            (self.state_dir / child).mkdir(exist_ok=True)
        self.event_log = self.state_dir / "runtime_events.jsonl"
        self._event_sequence, self._last_event_digest = self._load_event_cursor()

    def _ensure_safe_runtime_dir(self) -> None:
        resolved = self.state_dir.resolve()
        if self.state_dir.is_symlink():
            raise ValueError("runtime state directory must not be a symlink")
        for parent in (resolved, *resolved.parents):
            if parent.name.startswith("RC4_") and "reports" in {p.name for p in parent.parents}:
                raise ValueError("runtime state directory must not be under reports/RC4_*")

    def _safe_child(self, *parts: str) -> Path:
        path = self.state_dir.joinpath(*parts)
        resolved = path.resolve()
        if self.state_dir.resolve() not in (resolved, *resolved.parents):
            raise ValueError("runtime state path escaped state directory")
        if path.exists() and path.is_symlink():
            raise ValueError("runtime state file must not be a symlink")
        return path

    def _atomic_write_json(self, path: Path, payload: Mapping[str, Any]) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.is_symlink():
            raise ValueError("refusing to replace symlink runtime artifact")
        body = _canonical_json(payload) + "\n"
        payload_digest = _digest(body)
        tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
            _flush_file(handle)
        if tmp.stat().st_size != len(body.encode("utf-8")):
            tmp.unlink(missing_ok=True)
            raise IOError("durable write size verification failed")
        if _digest(tmp.read_bytes()) != payload_digest:
            tmp.unlink(missing_ok=True)
            raise IOError("durable write digest verification failed")
        os.replace(tmp, path)
        _fsync_directory(path.parent)
        if _digest(path.read_bytes()) != payload_digest:
            raise IOError("durable replacement digest verification failed")
        return payload_digest

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_event_cursor(self) -> tuple[int, str]:
        if not self.event_log.exists():
            return 0, "GENESIS"
        sequence = 0
        previous = "GENESIS"
        for line in self.event_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            expected = dict(event)
            current = expected.pop("current_event_digest", None)
            if event.get("previous_event_digest") != previous or _digest(expected) != current:
                raise ValueError("event log digest chain is invalid")
            previous = str(current)
            sequence = int(event["monotonic_sequence"])
        return sequence, previous

    def append_event(
        self,
        event_type: str,
        *,
        subsystem: str = "runtime",
        phase: str = "durability",
        lifecycle_before: str = "unknown",
        lifecycle_after: str = "unknown",
        objective_or_mission_id: str | None = None,
        request_id: str | None = None,
        authorization_id: str | None = None,
        attempt_id: str | None = None,
        proposal_id: str | None = None,
        disposition_id: str | None = None,
        application_id: str | None = None,
        capability_id: str | None = None,
        result_classification: str = "recorded",
        summary: str = "",
        error_category: str | None = None,
        clean_boundary: bool = False,
    ) -> dict[str, Any]:
        if event_type not in EVENT_CATEGORIES:
            raise ValueError(f"unsupported event category: {event_type}")
        self._rotate_event_log_if_needed()
        sequence = self._event_sequence + 1
        event_id = f"evt-{sequence:012d}-{uuid4().hex[:8]}"
        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id,
            "runtime_session_id": self.runtime_session_id,
            "objective_or_mission_id": objective_or_mission_id,
            "subsystem": subsystem,
            "phase": phase,
            "event_type": event_type,
            "utc_timestamp": _utc_timestamp(),
            "monotonic_sequence": sequence,
            "previous_event_digest": self._last_event_digest,
            "lifecycle_state_before": lifecycle_before,
            "lifecycle_state_after": lifecycle_after,
            "request_id": request_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "proposal_id": proposal_id,
            "disposition_id": disposition_id,
            "application_id": application_id,
            "capability_id": capability_id,
            "result_classification": result_classification,
            "summary": _bounded_text(summary),
            "error_category": error_category,
            "process_id": os.getpid(),
            "clean_boundary": clean_boundary,
        }
        event["current_event_digest"] = _digest(event)
        with self.event_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(event) + "\n")
            _flush_file(handle)
        self._event_sequence = sequence
        self._last_event_digest = str(event["current_event_digest"])
        return event

    def _rotate_event_log_if_needed(self) -> None:
        if self.event_log.exists() and self.event_log.stat().st_size > MAX_EVENT_LOG_BYTES:
            rotated = self.state_dir / "runtime_events.1.jsonl"
            if rotated.exists():
                rotated.unlink()
            os.replace(self.event_log, rotated)
            _fsync_directory(self.state_dir)
            self._event_sequence = 0
            self._last_event_digest = "GENESIS"

    def record_failure(
        self,
        *,
        phase: str,
        operation: str,
        expected_transition: str,
        observed_transition: str,
        exception: BaseException | None = None,
        first_incorrect_transition: str | None = None,
        responsible: str | None = None,
        lifecycle_state: str = "unknown",
        active_mission_id: str | None = None,
        active_attempt_id: str | None = None,
        authorization_consumption_state: str = "unknown",
        files_read: tuple[str, ...] = (),
        files_written: tuple[str, ...] = (),
        commands_executed: tuple[str, ...] = (),
        active_sandbox: str | None = None,
        last_clean_checkpoint_id: str | None = None,
        cleanup_status: str = "unknown",
        recovery_recommendation: str = "operator_review_required",
        operator_review_required: bool = True,
    ) -> dict[str, Any]:
        failure_id = f"failure-{uuid4().hex}"
        stack = ""
        exception_type = None
        exception_message = None
        if exception is not None:
            exception_type = type(exception).__name__
            exception_message = _bounded_text(exception)
            stack = _bounded_text("".join(traceback.format_exception(exception)), limit=MAX_STACK_BYTES)
        record = {
            "schema_version": SCHEMA_VERSION,
            "failure_id": failure_id,
            "runtime_session_id": self.runtime_session_id,
            "phase": phase,
            "exact_operation": operation,
            "expected_transition": expected_transition,
            "observed_transition": observed_transition,
            "first_incorrect_transition": first_incorrect_transition,
            "exception_type": exception_type,
            "bounded_exception_message": exception_message,
            "bounded_stack_trace": stack,
            "responsible_function_or_contract": responsible,
            "lifecycle_state": lifecycle_state,
            "active_mission_id": active_mission_id,
            "active_attempt_id": active_attempt_id,
            "authorization_consumption_state": authorization_consumption_state,
            "files_read": tuple(_bounded_text(item) for item in files_read),
            "files_written": tuple(_bounded_text(item) for item in files_written),
            "commands_executed": tuple(_bounded_text(item) for item in commands_executed),
            "active_sandbox": active_sandbox,
            "last_clean_checkpoint_id": last_clean_checkpoint_id,
            "last_event_log_sequence": self._event_sequence,
            "last_event_log_digest": self._last_event_digest,
            "cleanup_status": cleanup_status,
            "recovery_recommendation": recovery_recommendation,
            "operator_review_required": operator_review_required,
        }
        try:
            self._atomic_write_json(self._safe_child("failures", f"{failure_id}.json"), record)
            self._prune_failure_records()
            self.append_event(
                "unhandled_exception" if exception is not None else "integrity_failure",
                phase=phase,
                lifecycle_before=lifecycle_state,
                lifecycle_after=lifecycle_state,
                result_classification="failure_recorded",
                summary=f"{operation}: {observed_transition}",
                error_category=exception_type or "recorded_failure",
            )
        except Exception:
            # The original context is returned to the caller; a secondary logging
            # failure must not replace it.
            record["secondary_logging_failure"] = True
        return record

    def _prune_failure_records(self) -> None:
        records = sorted((self.state_dir / "failures").glob("failure-*.json"), key=lambda path: path.stat().st_mtime)
        for old in records[:-MAX_FAILURE_RECORDS]:
            old.unlink(missing_ok=True)

    def write_intent(
        self,
        action_id: str,
        action_type: str,
        *,
        authorization_id: str | None = None,
        summary: str = "",
        evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if action_type not in CONSEQUENTIAL_ACTIONS:
            raise ValueError(f"unsupported consequential action: {action_type}")
        record = {
            "schema_version": SCHEMA_VERSION,
            "action_id": action_id,
            "runtime_session_id": self.runtime_session_id,
            "action_type": action_type,
            "authorization_id": authorization_id,
            "status": "pending",
            "created_utc": _utc_timestamp(),
            "updated_utc": _utc_timestamp(),
            "summary": _bounded_text(summary),
            "evidence": _redact(dict(evidence or {})),
            "completed_utc": None,
            "failed_utc": None,
            "outcome": None,
            "authorization_uncertain": action_type == "authorization_consumption",
        }
        self._atomic_write_json(self._safe_child("journal", f"{action_id}.json"), record)
        return record

    def complete_intent(self, action_id: str, *, outcome: str = "completed") -> dict[str, Any]:
        path = self._safe_child("journal", f"{action_id}.json")
        record = self._read_json(path)
        if record.get("status") != "pending":
            raise ValueError("only pending journal actions can be completed")
        record.update(
            {
                "status": "completed",
                "updated_utc": _utc_timestamp(),
                "completed_utc": _utc_timestamp(),
                "outcome": _bounded_text(outcome),
                "authorization_uncertain": False,
            }
        )
        self._atomic_write_json(path, record)
        return record

    def fail_intent(self, action_id: str, *, outcome: str = "failed") -> dict[str, Any]:
        path = self._safe_child("journal", f"{action_id}.json")
        record = self._read_json(path)
        if record.get("status") != "pending":
            raise ValueError("only pending journal actions can fail")
        record.update(
            {
                "status": "failed",
                "updated_utc": _utc_timestamp(),
                "failed_utc": _utc_timestamp(),
                "outcome": _bounded_text(outcome),
            }
        )
        self._atomic_write_json(path, record)
        return record

    def incomplete_action_ids(self) -> tuple[str, ...]:
        ids: list[str] = []
        for path in sorted((self.state_dir / "journal").glob("*.json")):
            try:
                record = self._read_json(path)
            except Exception:
                ids.append(path.stem)
                continue
            if record.get("status") == "pending":
                ids.append(str(record["action_id"]))
        return tuple(ids)

    def write_checkpoint(self, checkpoint_id: str, clean_state: Mapping[str, Any]) -> dict[str, Any]:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "checkpoint_id": checkpoint_id,
            "runtime_session_id": self.runtime_session_id,
            "written_utc": _utc_timestamp(),
            "clean_boundary_state": _redact(dict(clean_state)),
            "runtime_session_identity": clean_state.get("runtime_session_identity", self.runtime_session_id),
            "original_mission_id": clean_state.get("original_mission_id"),
            "approved_objective_id": clean_state.get("approved_objective_id"),
            "current_lifecycle_state": clean_state.get("current_lifecycle_state", "stopped"),
            "completed_attempt_summaries": tuple(clean_state.get("completed_attempt_summaries", ())),
            "remaining_budgets": dict(clean_state.get("remaining_budgets", {})),
            "best_candidate_identity": clean_state.get("best_candidate_identity"),
            "pending_review_identities": tuple(clean_state.get("pending_review_identities", ())),
            "operator_dispositions": tuple(clean_state.get("operator_dispositions", ())),
            "authorization_consumption_summaries": tuple(clean_state.get("authorization_consumption_summaries", ())),
            "capability_evidence_tiers": dict(clean_state.get("capability_evidence_tiers", {})),
            "last_artifact_chain_digest": clean_state.get("last_artifact_chain_digest"),
            "event_log_sequence": self._event_sequence,
            "event_log_digest": self._last_event_digest,
            "last_clean_shutdown_status": bool(clean_state.get("last_clean_shutdown_status", False)),
            "payload_digest": "",
        }
        payload["payload_digest"] = _digest({key: value for key, value in payload.items() if key != "payload_digest"})
        self.write_intent(f"checkpoint-{checkpoint_id}", "checkpoint_replacement", summary=f"checkpoint {checkpoint_id}")
        self._rotate_checkpoints()
        digest = self._atomic_write_json(self._safe_child("checkpoints", "checkpoint.current.json"), payload)
        self.complete_intent(f"checkpoint-{checkpoint_id}", outcome=digest)
        self.append_event(
            "checkpoint_written",
            lifecycle_before=str(payload["current_lifecycle_state"]),
            lifecycle_after=str(payload["current_lifecycle_state"]),
            result_classification="checkpoint_written",
            summary=f"checkpoint {checkpoint_id}",
            clean_boundary=True,
        )
        return payload

    def _rotate_checkpoints(self) -> None:
        checkpoints = self.state_dir / "checkpoints"
        current = checkpoints / "checkpoint.current.json"
        previous = checkpoints / "checkpoint.previous.json"
        if previous.exists():
            for index in range(BACKUP_COUNT, 1, -1):
                older = checkpoints / f"checkpoint.backup.{index - 1}.json"
                newer = checkpoints / f"checkpoint.backup.{index}.json"
                if older.exists():
                    os.replace(older, newer)
            os.replace(previous, checkpoints / "checkpoint.backup.1.json")
        if current.exists():
            os.replace(current, previous)
        _fsync_directory(checkpoints)

    def _validated_checkpoint(self, path: Path) -> dict[str, Any] | None:
        if not path.exists() or path.is_symlink():
            return None
        try:
            payload = self._read_json(path)
        except Exception:
            return None
        expected = payload.get("payload_digest")
        actual = _digest({key: value for key, value in payload.items() if key != "payload_digest"})
        if expected != actual:
            return None
        return payload

    def newest_valid_checkpoint(self) -> tuple[dict[str, Any] | None, bool]:
        current = self._validated_checkpoint(self._safe_child("checkpoints", "checkpoint.current.json"))
        if current is not None:
            return current, False
        for name in ("checkpoint.previous.json", "checkpoint.backup.1.json", "checkpoint.backup.2.json", "checkpoint.backup.3.json"):
            fallback = self._validated_checkpoint(self._safe_child("checkpoints", name))
            if fallback is not None:
                return fallback, True
        return None, False

    def recover_startup(self) -> RuntimeRecoveryStatus:
        event_log_valid = True
        try:
            self._event_sequence, self._last_event_digest = self._load_event_cursor()
        except Exception:
            event_log_valid = False
        checkpoint, recovered_from_previous = self.newest_valid_checkpoint()
        incomplete = self.incomplete_action_ids()
        prior_clean = bool(checkpoint and checkpoint.get("last_clean_shutdown_status")) and not incomplete and event_log_valid
        operator_review_required = not prior_clean or bool(incomplete) or recovered_from_previous or not event_log_valid
        if not prior_clean:
            self.append_event(
                "runtime_recovered_unclean_shutdown",
                result_classification="recovery_requires_review" if operator_review_required else "recovered",
                summary="startup recovery inspected durable state",
                clean_boundary=False,
            )
        if recovered_from_previous and checkpoint is not None:
            self.append_event(
                "checkpoint_recovered",
                result_classification="fallback_checkpoint_recovered",
                summary=str(checkpoint.get("checkpoint_id")),
                clean_boundary=True,
            )
        return RuntimeRecoveryStatus(
            recovered_checkpoint_id=str(checkpoint["checkpoint_id"]) if checkpoint else None,
            recovered_from_previous=recovered_from_previous,
            prior_shutdown_clean=prior_clean,
            event_log_valid=event_log_valid,
            checkpoint_valid=checkpoint is not None,
            incomplete_action_ids=incomplete,
            operator_review_required=operator_review_required,
            recommendation="operator_review_required" if operator_review_required else "clean_start_allowed",
        )

    def runtime_status_snapshot(self) -> RuntimeStatusSnapshot:
        checkpoint, _ = self.newest_valid_checkpoint()
        failures = sorted((self.state_dir / "failures").glob("failure-*.json"))
        last_failure = None
        if failures:
            try:
                data = self._read_json(failures[-1])
                last_failure = str(data.get("exact_operation"))
            except Exception:
                last_failure = "unreadable failure record"
        incomplete = self.incomplete_action_ids()
        pending_reviews = 0
        if checkpoint:
            pending_reviews = len(tuple(checkpoint.get("pending_review_identities", ())))
        return RuntimeStatusSnapshot(
            prior_shutdown_clean=bool(checkpoint and checkpoint.get("last_clean_shutdown_status")) and not incomplete,
            latest_checkpoint_id=str(checkpoint["checkpoint_id"]) if checkpoint else None,
            current_event_sequence=self._event_sequence,
            unresolved_failure_count=len(failures),
            incomplete_journal_action_count=len(incomplete),
            recovery_required=bool(incomplete),
            pending_review_count=pending_reviews,
            active_runtime_mode="stopped",
            last_failure_summary=last_failure,
        )


def default_clean_checkpoint_state(*, mission_id: str = "mission-fixture") -> dict[str, Any]:
    return {
        "runtime_session_identity": "session-fixture",
        "original_mission_id": mission_id,
        "approved_objective_id": "objective-fixture",
        "current_lifecycle_state": "stopped",
        "completed_attempt_summaries": (),
        "remaining_budgets": {"attempts": 1},
        "best_candidate_identity": None,
        "pending_review_identities": (),
        "operator_dispositions": (),
        "authorization_consumption_summaries": (),
        "capability_evidence_tiers": {},
        "last_artifact_chain_digest": "artifact-fixture",
        "last_clean_shutdown_status": True,
    }
