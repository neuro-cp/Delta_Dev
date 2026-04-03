from __future__ import annotations

from typing import Dict, List

from orchestration.schemas.route_candidate import RouteCandidate
from orchestration.schemas.task_graph import TaskGraph, TaskType


class RouteCandidateBuilder:
    """
    Build possible route candidates for the graph root.
    """

    def build(self, graph: TaskGraph, constraints: Dict[str, object]) -> List[RouteCandidate]:
        allowed_routes = list(constraints.get("allowed_routes", []))
        candidates: List[RouteCandidate] = []

        root = graph.root()
        target_node_id = root.node_id if root is not None else graph.root_node_id

        for route_type in allowed_routes:
            rationale = self._rationale_for(route_type, graph.task_type)
            candidates.append(
                RouteCandidate(
                    route_id=f"{graph.graph_id}:{route_type}",
                    route_type=route_type,
                    target_node_id=target_node_id,
                    rationale=rationale,
                    estimated_confidence=0.0,
                    estimated_cost=self._cost_for(route_type),
                    allowed=True,
                    metadata={"task_type": graph.task_type.value},
                )
            )

        return candidates

    @staticmethod
    def _cost_for(route_type: str) -> float:
        costs = {
            "deterministic_solver": 0.1,
            "recall": 0.3,
            "llm": 0.6,
            "operator_query": 1.0,
        }
        return costs.get(route_type, 0.5)

    @staticmethod
    def _rationale_for(route_type: str, task_type: TaskType) -> str:
        return f"{route_type} route for {task_type.value}"
