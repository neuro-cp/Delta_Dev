from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from orchestration.agency.goal_system import GoalRecord


@dataclass(frozen=True)
class ExecutiveController:
    """
    Prioritizes cognitive work without replacing other regions.
    """

    max_goals: int = 3

    def prioritize_goals(self, goals: Sequence[GoalRecord]) -> list[GoalRecord]:
        active = [goal for goal in goals if goal.status == "active"]
        return sorted(active, key=lambda goal: goal.action_pressure, reverse=True)[
            : self.max_goals
        ]

    def allocation_report(self, goals: Sequence[GoalRecord]) -> dict[str, object]:
        prioritized = self.prioritize_goals(goals)
        return {
            "active_goal_count": len([goal for goal in goals if goal.status == "active"]),
            "selected_goal_ids": [goal.goal_id for goal in prioritized],
            "interruption_policy": "defer low-pressure goals when higher-pressure goals exist",
            "execution_authority": False,
        }
