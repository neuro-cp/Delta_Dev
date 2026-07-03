from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_replay import RUNTIME_V14E_INVARIANT_FLAGS, ReplayBatch


class SleepCycleIntent(str, Enum):
    AUDIT_ONLY = "audit_only"
    REVIEW_FEEDBACK = "review_feedback"
    REVIEW_REPLAY_CANDIDATES = "review_replay_candidates"
    PREPARE_CONSOLIDATION_CANDIDATES = "prepare_consolidation_candidates"


@dataclass(frozen=True)
class SleepCyclePlan:
    plan_id: str
    intent: SleepCycleIntent
    batch_ids: tuple[str, ...] = ()
    max_batches: int = 0
    scheduler_enabled: bool = False
    active_replay_enabled: bool = False
    provider_calls_enabled: bool = False
    canonical_write_enabled: bool = False
    training_enabled: bool = False
    pruning_enabled: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14E_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "intent": self.intent.value,
            "batch_ids": list(self.batch_ids),
            "max_batches": self.max_batches,
            "scheduler_enabled": self.scheduler_enabled,
            "active_replay_enabled": self.active_replay_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "canonical_write_enabled": self.canonical_write_enabled,
            "training_enabled": self.training_enabled,
            "pruning_enabled": self.pruning_enabled,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_sleep_cycle_plan(
    *,
    batches: tuple[ReplayBatch, ...] | list[ReplayBatch] = (),
    intent: SleepCycleIntent = SleepCycleIntent.AUDIT_ONLY,
    max_batches: int | None = None,
    notes: str = "",
) -> SleepCyclePlan:
    batch_ids = tuple(sorted(batch.batch_id for batch in batches))
    count = len(batch_ids) if max_batches is None else max(0, int(max_batches))
    return SleepCyclePlan(
        plan_id=_stable_id("sleep-cycle-plan", (intent.value, *batch_ids, str(count))),
        intent=intent,
        batch_ids=batch_ids,
        max_batches=count,
        notes=notes or "sleep cycle is a plan only; no scheduler, daemon, replay, or consolidation is started",
    )


def validate_sleep_cycle_plan_inert(plan: SleepCyclePlan) -> bool:
    return (
        plan.scheduler_enabled is False
        and plan.active_replay_enabled is False
        and plan.provider_calls_enabled is False
        and plan.canonical_write_enabled is False
        and plan.training_enabled is False
        and plan.pruning_enabled is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "|".join(part for part in parts if part)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else "empty"
    return f"{prefix}-{digest}"
