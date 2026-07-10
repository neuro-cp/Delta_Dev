"""RC3-A deterministic goal lifecycle transitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orchestration.runtime.rc3_foundation_state import GoalFrame


VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "proposed": ("interpreted", "rejected"),
    "interpreted": ("awaiting_clarification", "confirmed", "rejected"),
    "awaiting_clarification": ("interpreted", "rejected"),
    "confirmed": ("active", "paused", "rejected"),
    "active": ("paused", "blocked", "completed", "abandoned", "superseded"),
    "paused": ("active", "abandoned", "superseded"),
    "blocked": ("active", "abandoned", "superseded"),
    "completed": (),
    "abandoned": (),
    "superseded": (),
    "rejected": (),
}


@dataclass(frozen=True)
class GoalTransitionResult:
    accepted: bool
    from_status: str
    to_status: str
    reason: str
    provenance: dict[str, Any]
    requires_operator_review: bool
    safety_blocked: bool = False


def evaluate_goal_transition(
    goal: GoalFrame,
    to_status: str,
    *,
    reason: str,
    completion_evidence: tuple[str, ...] = (),
) -> GoalTransitionResult:
    from_status = goal.status
    allowed = to_status in VALID_TRANSITIONS.get(from_status, ())
    safety_blocked = to_status == "active" and any(
        item in goal.prohibited_actions
        for item in ("do not execute", "do not execute plans", "do not interact with DELTA-75")
    ) and "execution" in reason.lower()
    if to_status == "completed" and not completion_evidence:
        return _result(False, from_status, to_status, "completion requires evidence", reason, True)
    if safety_blocked:
        return _result(False, from_status, to_status, "safety constraints prohibit activation for execution", reason, True, safety_blocked=True)
    if not allowed:
        return _result(False, from_status, to_status, "invalid lifecycle transition", reason, True)
    return _result(True, from_status, to_status, "transition accepted", reason, to_status in ("active", "completed", "superseded"))


def _result(
    accepted: bool,
    from_status: str,
    to_status: str,
    message: str,
    reason: str,
    requires_review: bool,
    *,
    safety_blocked: bool = False,
) -> GoalTransitionResult:
    return GoalTransitionResult(
        accepted=accepted,
        from_status=from_status,
        to_status=to_status,
        reason=message,
        provenance={"operator_or_runtime_reason": reason, "hidden_status_change": False},
        requires_operator_review=requires_review,
        safety_blocked=safety_blocked,
    )
