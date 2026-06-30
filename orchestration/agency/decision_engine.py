from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

from orchestration.agency.goal_system import GoalRecord
from orchestration.agency.planning_engine import PlanRecord


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    created_at: str
    goal_id: str
    plan_id: str
    decision: str
    score: float
    expected_reward: float
    goal_satisfaction: float
    confidence: float
    resource_cost: float
    risk: float
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DecisionEngine:
    """
    Selects among proposed plans without executing them.
    """

    def choose(
        self,
        *,
        goal: GoalRecord,
        plans: Sequence[PlanRecord],
    ) -> DecisionRecord:
        if not plans:
            raise ValueError("at least one plan is required for decision")
        plan = max(plans, key=lambda item: self._score(goal, item))
        score = self._score(goal, plan)
        return DecisionRecord(
            decision_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            goal_id=goal.goal_id,
            plan_id=plan.plan_id,
            decision="propose_plan",
            score=score,
            expected_reward=plan.expected_benefit,
            goal_satisfaction=goal.action_pressure,
            confidence=round(1.0 - plan.uncertainty, 4),
            resource_cost=goal.estimated_effort,
            risk=plan.expected_risk,
            rationale=(
                "Decision balances expected reward, goal pressure, confidence, "
                "resource cost, and risk. It proposes action only."
            ),
            metadata={"execution_authority": False},
        )

    @staticmethod
    def _score(goal: GoalRecord, plan: PlanRecord) -> float:
        score = (
            plan.expected_benefit * 0.35
            + goal.action_pressure * 0.25
            + (1.0 - plan.uncertainty) * 0.2
            - plan.expected_risk * 0.15
            - goal.estimated_effort * 0.05
        )
        return round(max(0.0, min(1.0, score)), 4)
