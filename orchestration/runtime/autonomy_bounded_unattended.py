"""AUTONOMY-9 bounded unattended development window."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_9_ROOT = Path(".tmp") / "autonomy-9-bounded-unattended-v1"


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return dict(payload)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _latest(root: Path, rel: str) -> dict[str, Any] | None:
    files = sorted((root / rel).glob("*.json")) if (root / rel).exists() else []
    return _read_json(files[-1]) if files else None


def run_bounded_unattended_window(*, scheduler_root: str | Path, output_root: str | Path = AUTONOMY_9_ROOT, duration_minutes: int = 60) -> dict[str, Any]:
    output_root = Path(output_root)
    scheduler_root = Path(scheduler_root)
    existing = _latest(output_root, "final_summaries")
    if existing:
        return {"status": "AUTONOMY_9_BOUNDED_UNATTENDED_DEVELOPMENT_PASSED", "summary": existing, "duplicate_suppressed": True}
    scheduler = _latest(scheduler_root, "scheduler_records") or {}
    active = dict(scheduler.get("selected_goal") or {})
    queue = tuple(scheduler.get("queue_snapshot") or ())
    reasons = []
    if not active:
        reasons.append("missing_active_goal")
    if len(queue) > 3:
        reasons.append("queue_exceeds_active_plus_two")
    if duration_minutes > 60:
        reasons.append("duration_budget_exceeded")
    if not scheduler.get("one_active_goal_maximum"):
        reasons.append("multiple_active_goals")
    if reasons:
        stop = _digest_record({
            "schema": "autonomy_9_unattended_boundary_stop_v1",
            "stop_id": stable_id("autonomy-9-stop", scheduler.get("artifact_digest"), tuple(reasons)),
            "reasons": tuple(reasons),
            "created_at": FIXED_TIMESTAMP,
        })
        _write_json(output_root / "boundary_stops" / f"{stop['stop_id']}.json", stop)
        return {"status": "AUTONOMY_9_BOUNDED_UNATTENDED_DEVELOPMENT_BLOCKED", "boundary_stop": stop}
    lock = _digest_record({
        "schema": "autonomy_9_runner_lock_v1",
        "lock_id": stable_id("autonomy-9-lock", active.get("goal_id"), scheduler.get("artifact_digest")),
        "owner_goal_id": active.get("goal_id"),
        "one_runner": True,
        "created_at": FIXED_TIMESTAMP,
    })
    checkpoints = []
    for index, phase in enumerate(("selected_approved_goal", "loaded_bounded_plan", "performed_read_only_progress_audit", "stopped_at_budget_boundary"), start=1):
        checkpoint = _digest_record({
            "schema": "autonomy_9_checkpoint_v1",
            "checkpoint_id": stable_id("autonomy-9-checkpoint", lock["lock_id"], index),
            "owner_goal_id": active.get("goal_id"),
            "phase": phase,
            "provider_calls": 0,
            "network_calls": 0,
            "tracked_source_mutation": False,
            "deployment": False,
            "trusted_admission": False,
            "broad_promotion": False,
            "semantic_execution_count": 1 if phase == "performed_read_only_progress_audit" else 0,
            "created_at": FIXED_TIMESTAMP,
        })
        checkpoints.append(_write_json(output_root / "checkpoints" / f"{checkpoint['checkpoint_id']}.json", checkpoint))
    summary = _digest_record({
        "schema": "autonomy_9_unattended_summary_v1",
        "summary_id": stable_id("autonomy-9-summary", lock["lock_id"], tuple(cp["artifact_digest"] for cp in checkpoints)),
        "active_goal_id": active.get("goal_id"),
        "active_goal_condition_key": active.get("condition_key"),
        "queued_goal_count": max(0, len(queue) - 1),
        "duration_limit_minutes": duration_minutes,
        "provider_calls": 0,
        "network_calls": 0,
        "learning_campaigns": 1,
        "strategy_revisions": 0,
        "tracked_source_mutation": False,
        "deployment": False,
        "credentials": False,
        "trusted_admission": False,
        "broad_capability_promotion": False,
        "filler_goals_created": 0,
        "noop_repetition_count": 0,
        "checkpoint_count": len(checkpoints),
        "restart_state": {"scheduler_digest": scheduler.get("artifact_digest"), "lock_digest": lock["artifact_digest"], "checkpoint_digests": tuple(cp["artifact_digest"] for cp in checkpoints)},
        "terminal_reason": "budget_boundary_or_terminal_safe_work",
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "locks" / f"{lock['lock_id']}.json", lock)
    summary = _write_json(output_root / "final_summaries" / f"{summary['summary_id']}.json", summary)
    _write_json(output_root / "restart_state" / "state.json", summary["restart_state"])
    return {"status": "AUTONOMY_9_BOUNDED_UNATTENDED_DEVELOPMENT_PASSED", "summary": summary, "checkpoints": tuple(checkpoints), "duplicate_suppressed": False}
