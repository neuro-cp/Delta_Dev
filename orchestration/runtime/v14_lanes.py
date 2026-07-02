from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RuntimeLane(str, Enum):
    ACTIVATION = "activation"
    ATTENTION = "attention"
    REASONING = "reasoning"
    PLANNING = "planning"
    RESPONSE = "response"
    EXECUTION = "execution"


class LanePermission(str, Enum):
    VISIBLE = "visible"
    SELECTABLE = "selectable"
    CITABLE = "citable"
    PLANNING_SUPPORT = "planning_support"
    RESPONSE_SUPPORT = "response_support"
    EXECUTABLE = "executable"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class LanePolicy:
    lane: RuntimeLane
    permission: LanePermission
    reason: str
    confidence: float = 1.0
    reversible: bool = True

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "lane": self.lane.value,
            "permission": self.permission.value,
            "reason": self.reason,
            "confidence": self.normalized_confidence(),
            "reversible": self.reversible,
        }


@dataclass(frozen=True)
class ConceptLaneState:
    concept_id: str
    policies: tuple[LanePolicy, ...] = ()
    source: str = "runtime_v14_scaffold"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def policy_for(self, lane: RuntimeLane) -> LanePolicy | None:
        lane_policies = [policy for policy in self.policies if policy.lane == lane]
        if not lane_policies:
            return None
        return lane_policies[-1]

    def as_dict(self) -> dict[str, object]:
        return {
            "concept_id": self.concept_id,
            "policies": [policy.as_dict() for policy in self.policies],
            "source": self.source,
            "created_at": self.created_at,
        }


def allow_activation_only(concept_id: str, reason: str) -> ConceptLaneState:
    return ConceptLaneState(
        concept_id=concept_id,
        policies=(
            LanePolicy(RuntimeLane.ACTIVATION, LanePermission.VISIBLE, reason),
            LanePolicy(RuntimeLane.ATTENTION, LanePermission.BLOCKED, "activation-only concept is not attention selectable"),
            LanePolicy(RuntimeLane.REASONING, LanePermission.BLOCKED, "activation-only concept is not citable reasoning evidence"),
            LanePolicy(RuntimeLane.PLANNING, LanePermission.BLOCKED, "activation-only concept is not planning support"),
            LanePolicy(RuntimeLane.RESPONSE, LanePermission.BLOCKED, "activation-only concept is not response support"),
            LanePolicy(RuntimeLane.EXECUTION, LanePermission.BLOCKED, "runtime concepts are never executable"),
        ),
    )


def block_reasoning_lane(concept_id: str, reason: str) -> ConceptLaneState:
    return ConceptLaneState(
        concept_id=concept_id,
        policies=(
            LanePolicy(RuntimeLane.ACTIVATION, LanePermission.VISIBLE, "concept may remain visible for diagnostics"),
            LanePolicy(RuntimeLane.ATTENTION, LanePermission.SELECTABLE, "concept may be selected as context"),
            LanePolicy(RuntimeLane.REASONING, LanePermission.BLOCKED, reason),
            LanePolicy(RuntimeLane.PLANNING, LanePermission.PLANNING_SUPPORT, "concept may remain weak planning context"),
            LanePolicy(RuntimeLane.RESPONSE, LanePermission.BLOCKED, "blocked reasoning evidence is not response citable"),
            LanePolicy(RuntimeLane.EXECUTION, LanePermission.BLOCKED, "runtime concepts are never executable"),
        ),
    )


def block_planning_lane(concept_id: str, reason: str) -> ConceptLaneState:
    return ConceptLaneState(
        concept_id=concept_id,
        policies=(
            LanePolicy(RuntimeLane.ACTIVATION, LanePermission.VISIBLE, "concept may remain visible"),
            LanePolicy(RuntimeLane.ATTENTION, LanePermission.SELECTABLE, "concept may remain context selectable"),
            LanePolicy(RuntimeLane.REASONING, LanePermission.CITABLE, "concept may remain citable evidence"),
            LanePolicy(RuntimeLane.PLANNING, LanePermission.BLOCKED, reason),
            LanePolicy(RuntimeLane.RESPONSE, LanePermission.RESPONSE_SUPPORT, "concept may support response if reasoning citable"),
            LanePolicy(RuntimeLane.EXECUTION, LanePermission.BLOCKED, "runtime concepts are never executable"),
        ),
    )


def can_use_in_lane(
    state: ConceptLaneState,
    lane: RuntimeLane,
    required_permission: LanePermission | None = None,
) -> bool:
    policy = state.policy_for(lane)
    if policy is None:
        return False
    if policy.permission == LanePermission.BLOCKED:
        return False
    if required_permission is None:
        return True
    return policy.permission == required_permission


def can_use(state: ConceptLaneState, lane: RuntimeLane, permission: LanePermission | None = None) -> bool:
    return can_use_in_lane(state, lane, permission)
