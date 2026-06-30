from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from orchestration.agency.decision_engine import DecisionEngine, DecisionRecord
from orchestration.agency.executive_controller import ExecutiveController
from orchestration.agency.goal_system import GoalRecord
from orchestration.agency.planning_engine import PlanRecord, PlanningEngine
from orchestration.simulation import SimulationReport


@dataclass(frozen=True)
class AgencyProposal:
    proposed_action: str
    goal_id: str | None
    plan_id: str | None
    decision: DecisionRecord | None
    rationale: str
    executive_allocation: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgencyRegion:
    """
    Answers what Delta should do next.

    Agency owns no knowledge and has no execution authority. It coordinates
    goals, planning, simulation, decision, and self-model signals into a
    proposed next action.
    """

    def __init__(
        self,
        *,
        executive: ExecutiveController | None = None,
        planner: PlanningEngine | None = None,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        self._executive = executive or ExecutiveController()
        self._planner = planner or PlanningEngine()
        self._decision_engine = decision_engine or DecisionEngine()

    def propose(
        self,
        *,
        goals: Sequence[GoalRecord],
        simulation: SimulationReport | None = None,
        self_model: dict[str, Any] | None = None,
    ) -> AgencyProposal:
        available_goals = list(goals)
        if not available_goals:
            available_goals = self._intrinsic_goals(self_model or {})
        selected = self._executive.prioritize_goals(available_goals)
        allocation = self._executive.allocation_report(available_goals)
        if not selected:
            return AgencyProposal(
                proposed_action="observe",
                goal_id=None,
                plan_id=None,
                decision=None,
                rationale="No active goals exist; continue observing.",
                executive_allocation=allocation,
                metadata={"execution_authority": False},
            )

        goal = selected[0]
        plan = self._planner.build_plan(goal=goal, simulation=simulation)
        decision = self._decision_engine.choose(goal=goal, plans=[plan])
        return AgencyProposal(
            proposed_action=plan.strategy,
            goal_id=goal.goal_id,
            plan_id=plan.plan_id,
            decision=decision,
            rationale=(
                "Agency selected the highest-pressure goal and proposed the "
                "best available non-executing plan."
            ),
            executive_allocation=allocation,
            metadata={
                "execution_authority": False,
                "plan": plan,
                "source": "agency_region",
            },
        )

    @staticmethod
    def _intrinsic_goals(self_model: dict[str, Any]) -> list[GoalRecord]:
        observations = list(self_model.get("self_observations", []))
        goals: list[GoalRecord] = []
        for observation in observations:
            kind = str(observation.get("kind", "self_observation"))
            summary = str(observation.get("summary", "")).strip()
            if not summary:
                continue
            goals.append(
                GoalRecord(
                    goal_id=f"intrinsic:{kind}",
                    created_at=str(self_model.get("generated_at", "")),
                    updated_at=str(self_model.get("generated_at", "")),
                    description=f"Investigate self-observation: {summary}",
                    origin="self_model",
                    priority=0.65,
                    urgency=0.45,
                    expected_value=0.7,
                    estimated_effort=0.45,
                    confidence=0.6,
                    metadata={"virtual": True, "observation_kind": kind},
                )
            )
        return goals
