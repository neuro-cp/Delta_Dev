"""AUTONOMY-8 persistent multi-goal scheduler with one active execution slot."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_8_ROOT = Path(".tmp") / "autonomy-8-multi-goal-scheduler-v1"
MUTATION_AUTHORITY = {"tracked_source_mutation", "deployment", "credentials"}


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


def _load_goals(root: Path) -> list[dict[str, Any]]:
    return [record for path in sorted((root / "goals").glob("*.json")) if (record := _read_json(path))] if (root / "goals").exists() else []


def persist_goal(output_root: str | Path, *, condition_key: str, priority: int, state: str = "queued", authority_requirements: Sequence[str] = (), prerequisites: Sequence[str] = (), created_index: int = 0, cycle_family: str = "", supported_task_class: str = "") -> dict[str, Any]:
    goal = _digest_record({
        "schema": "autonomy_8_scheduled_goal_v1",
        "goal_id": stable_id("autonomy-8-goal", condition_key),
        "condition_key": condition_key,
        "cycle_family": cycle_family,
        "supported_task_class": supported_task_class,
        "priority": priority,
        "state": state,
        "authority_requirements": tuple(authority_requirements),
        "prerequisites": tuple(prerequisites),
        "created_index": created_index,
        "execution_started": False,
        "created_at": FIXED_TIMESTAMP,
    })
    path = Path(output_root) / "goals" / f"{goal['goal_id']}.json"
    existing = _read_json(path)
    return existing if existing else _write_json(path, goal)


def _eligible(goal: Mapping[str, Any], active_runner_exists: bool) -> tuple[bool, str]:
    state = str(goal.get("state") or "")
    if state in {"completed", "rejected", "superseded"}:
        return False, f"{state}_goals_are_terminal"
    if state in {"blocked", "paused", "deferred"}:
        return False, f"goal_{state}"
    if state == "duplicate":
        return False, "duplicate_equivalent_goal"
    if tuple(goal.get("prerequisites") or ()):
        return False, "missing_prerequisite_goal"
    if active_runner_exists:
        return False, "active_runner_already_owns_execution_slot"
    if MUTATION_AUTHORITY.intersection(set(tuple(goal.get("authority_requirements") or ()))):
        return False, "mutation_capable_goal_requires_separate_authority"
    return True, "eligible"


def run_scheduler(output_root: str | Path = AUTONOMY_8_ROOT, *, seed_goals: Sequence[Mapping[str, Any]] = (), mark_completed: str | None = None) -> dict[str, Any]:
    output_root = Path(output_root)
    if seed_goals:
        seen: set[str] = set()
        for index, goal in enumerate(seed_goals, start=1):
            key = str(goal["condition_key"])
            state = "duplicate" if key in seen else str(goal.get("state") or "queued")
            seen.add(key)
            persist_goal(output_root, condition_key=key, priority=int(goal.get("priority") or 0), state=state, authority_requirements=tuple(goal.get("authority_requirements") or ()), prerequisites=tuple(goal.get("prerequisites") or ()), created_index=index, cycle_family=str(goal.get("cycle_family") or ""), supported_task_class=str(goal.get("supported_task_class") or ""))
    if mark_completed:
        for goal in _load_goals(output_root):
            if goal.get("goal_id") == mark_completed or goal.get("condition_key") == mark_completed:
                goal["state"] = "completed"
                _write_json(output_root / "goals" / f"{goal['goal_id']}.json", goal)
    goals = _load_goals(output_root)
    existing_active = next((goal for goal in goals if goal.get("state") == "active"), {})
    active_runner_exists = bool(existing_active)
    decisions = []
    eligible_goals = []
    for goal in goals:
        eligible, reason = _eligible(goal, active_runner_exists)
        row = dict(goal)
        row["eligibility"] = "eligible" if eligible else "deferred"
        row["selection_reason"] = reason
        decisions.append(row)
        if eligible:
            eligible_goals.append(row)
    selected = dict(existing_active) if existing_active else (sorted(eligible_goals, key=lambda item: (-int(item.get("priority") or 0), int(item.get("created_index") or 0), str(item.get("goal_id"))))[0] if eligible_goals else {})
    if selected:
        for goal in goals:
            if goal.get("goal_id") == selected.get("goal_id"):
                goal["state"] = "active"
                goal["execution_started"] = False
                _write_json(output_root / "goals" / f"{goal['goal_id']}.json", goal)
                selected = goal
                break
    goals = _load_goals(output_root)
    snapshot = _digest_record({
        "schema": "autonomy_8_scheduler_record_v1",
        "scheduler_id": stable_id("autonomy-8-scheduler", tuple(goal.get("artifact_digest") for goal in goals)),
        "queue_snapshot": tuple(goals),
        "selected_goal": selected,
        "selection_reason": "highest_priority_eligible_goal" if selected else "no_eligible_goal",
        "deferred_goals": tuple(goal for goal in decisions if goal.get("eligibility") != "eligible"),
        "blocked_goals": tuple(goal for goal in goals if goal.get("state") == "blocked"),
        "fairness_age_values": {goal["goal_id"]: goal.get("created_index") for goal in goals},
        "priority_values": {goal["goal_id"]: goal.get("priority") for goal in goals},
        "dependency_values": {goal["goal_id"]: tuple(goal.get("prerequisites") or ()) for goal in goals},
        "authority_requirements": {goal["goal_id"]: tuple(goal.get("authority_requirements") or ()) for goal in goals},
        "active_runner_ownership": selected.get("goal_id", ""),
        "one_active_goal_maximum": sum(1 for goal in goals if goal.get("state") == "active") <= 1,
        "execution_started": False,
        "next_reevaluation_boundary": "operator_approval_or_active_goal_terminal",
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "scheduler_records" / f"{snapshot['scheduler_id']}.json", snapshot)
    return {"status": "AUTONOMY_8_MULTI_GOAL_SCHEDULER_PASSED", "scheduler": snapshot}
