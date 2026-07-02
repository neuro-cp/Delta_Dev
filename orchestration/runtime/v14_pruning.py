from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_lanes import ConceptLaneState, LanePermission, LanePolicy, RuntimeLane


class PruningFailureType(str, Enum):
    SAME_TOPIC_NOISE = "same_topic_noise"
    WRONG_RELATION_USAGE = "wrong_relation_usage"
    WRONG_EVIDENCE_ROLE = "wrong_evidence_role"
    GENERIC_ANCHOR_DOMINANCE = "generic_anchor_dominance"
    CENTRALITY_BIAS = "centrality_bias"
    CONFIDENCE_PROMOTION_ERROR = "confidence_promotion_error"
    PLANNING_DRIFT = "planning_drift"
    REASONING_DRIFT = "reasoning_drift"
    RESPONSE_DRIFT = "response_drift"
    FALSE_OR_CORRUPT_CONCEPT = "false_or_corrupt_concept"
    BENCHMARK_ARTIFACT = "benchmark_artifact"


class CorrectiveAction(str, Enum):
    DAMPEN = "dampen"
    LANE_BLOCK = "lane_block"
    REQUIRE_CONTEXT = "require_context"
    QUARANTINE = "quarantine"
    REVIEW_REQUIRED = "review_required"
    NO_ACTION = "no_action"


@dataclass(frozen=True)
class PruningRecord:
    concept_id: str
    failure_context_hash: str
    failure_type: PruningFailureType
    affected_lane: RuntimeLane
    corrective_action: CorrectiveAction
    evidence_snapshot: dict[str, object] = field(default_factory=dict)
    confidence: float = 0.0
    decay_rule: str = "none"
    reversal_condition: str = "manual_review_or_counterevidence"
    source_report: str = "runtime_v14_scaffold"
    human_review_required: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "concept_id": self.concept_id,
            "failure_context_hash": self.failure_context_hash,
            "failure_type": self.failure_type.value,
            "affected_lane": self.affected_lane.value,
            "corrective_action": self.corrective_action.value,
            "evidence_snapshot": self.evidence_snapshot,
            "confidence": self.normalized_confidence(),
            "decay_rule": self.decay_rule,
            "reversal_condition": self.reversal_condition,
            "source_report": self.source_report,
            "human_review_required": self.human_review_required,
            "created_at": self.created_at,
        }


def propose_pruning_record(
    *,
    concept_id: str,
    failure_context_hash: str,
    failure_type: PruningFailureType,
    affected_lane: RuntimeLane,
    corrective_action: CorrectiveAction = CorrectiveAction.DAMPEN,
    evidence_snapshot: dict[str, object] | None = None,
    confidence: float = 0.5,
    source_report: str = "runtime_v14_scaffold",
) -> PruningRecord:
    return PruningRecord(
        concept_id=concept_id,
        failure_context_hash=failure_context_hash,
        failure_type=failure_type,
        affected_lane=affected_lane,
        corrective_action=corrective_action,
        evidence_snapshot=evidence_snapshot or {},
        confidence=confidence,
        decay_rule=_default_decay_rule(corrective_action),
        reversal_condition=_default_reversal_condition(corrective_action),
        source_report=source_report,
        human_review_required=should_require_human_review(failure_type, corrective_action),
    )


def apply_pruning_projection(state: ConceptLaneState, record: PruningRecord) -> ConceptLaneState:
    """Return a projected lane state without mutating the input state."""

    if record.concept_id != state.concept_id or record.corrective_action == CorrectiveAction.NO_ACTION:
        return state
    if record.corrective_action in {CorrectiveAction.DAMPEN, CorrectiveAction.REQUIRE_CONTEXT}:
        projected = LanePolicy(
            lane=record.affected_lane,
            permission=_current_or_default_permission(state, record.affected_lane),
            reason=f"projected dampening only: {record.failure_type.value}",
            confidence=max(0.0, 1.0 - record.normalized_confidence()),
            reversible=True,
        )
    elif record.corrective_action == CorrectiveAction.LANE_BLOCK:
        projected = LanePolicy(
            lane=record.affected_lane,
            permission=LanePermission.BLOCKED,
            reason=f"projected lane block only: {record.failure_type.value}",
            confidence=record.normalized_confidence(),
            reversible=True,
        )
    else:
        projected = LanePolicy(
            lane=record.affected_lane,
            permission=LanePermission.BLOCKED,
            reason=f"projected quarantine/review only: {record.failure_type.value}",
            confidence=record.normalized_confidence(),
            reversible=False,
        )
    return replace(state, policies=(*state.policies, projected))


def should_require_human_review(
    failure_type: PruningFailureType,
    corrective_action: CorrectiveAction,
) -> bool:
    return corrective_action in {CorrectiveAction.QUARANTINE, CorrectiveAction.REVIEW_REQUIRED} or failure_type in {
        PruningFailureType.FALSE_OR_CORRUPT_CONCEPT,
        PruningFailureType.BENCHMARK_ARTIFACT,
    }


def is_reversible_action(action: CorrectiveAction) -> bool:
    return action in {CorrectiveAction.DAMPEN, CorrectiveAction.REQUIRE_CONTEXT, CorrectiveAction.LANE_BLOCK, CorrectiveAction.NO_ACTION}


def propose_lane_dampening(
    *,
    concept_id: str,
    failure_context_hash: str,
    affected_lane: RuntimeLane,
    failure_type: PruningFailureType,
    evidence_snapshot: dict[str, object] | None = None,
    confidence: float = 0.5,
) -> PruningRecord:
    return propose_pruning_record(
        concept_id=concept_id,
        failure_context_hash=failure_context_hash,
        failure_type=failure_type,
        affected_lane=affected_lane,
        corrective_action=CorrectiveAction.DAMPEN,
        evidence_snapshot=evidence_snapshot,
        confidence=confidence,
    )


def is_reversible_pruning(record: PruningRecord) -> bool:
    return is_reversible_action(record.corrective_action)


FailureType = PruningFailureType


def _current_or_default_permission(state: ConceptLaneState, lane: RuntimeLane) -> LanePermission:
    policy = state.policy_for(lane)
    return policy.permission if policy is not None else LanePermission.VISIBLE


def _default_decay_rule(action: CorrectiveAction) -> str:
    if action == CorrectiveAction.NO_ACTION:
        return "none"
    if action in {CorrectiveAction.DAMPEN, CorrectiveAction.REQUIRE_CONTEXT, CorrectiveAction.LANE_BLOCK}:
        return "recover_after_successful_revalidation"
    return "manual_review_required"


def _default_reversal_condition(action: CorrectiveAction) -> str:
    if action == CorrectiveAction.NO_ACTION:
        return "not_applicable"
    if action in {CorrectiveAction.DAMPEN, CorrectiveAction.REQUIRE_CONTEXT, CorrectiveAction.LANE_BLOCK}:
        return "same context passes validation without drift"
    return "human review clears quarantine"
