from __future__ import annotations

from typing import Iterable

from orchestration.schemas.execution_plan import ExecutionPlan
from orchestration.schemas.route_candidate import RouteCandidate


class ArbitrationSelector:
    """
    Deterministic route selector.
    """

    _ORDER = {
        "deterministic_solver": 0,
        "recall": 1,
        "llm": 2,
        "operator_query": 3,
    }

    def select(self, candidates: Iterable[RouteCandidate]) -> ExecutionPlan:
        viable = [c for c in candidates if c.allowed]
        if not viable:
            raise ValueError("No viable route candidates available")

        viable.sort(
            key=lambda c: (
                -c.estimated_confidence,
                c.estimated_cost,
                self._ORDER.get(c.route_type, 999),
                c.route_id,
            )
        )

        selected = viable[0]

        return ExecutionPlan(
            plan_id=f"plan:{selected.route_id}",
            selected_route_id=selected.route_id,
            selected_route_type=selected.route_type,
            target_node_id=selected.target_node_id,
            steps=[f"execute:{selected.route_type}", f"target:{selected.target_node_id}"],
            metadata={"selected_confidence": selected.estimated_confidence},
        )
