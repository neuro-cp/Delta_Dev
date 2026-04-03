from __future__ import annotations

from typing import Dict, List

from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.task_graph import TaskGraph, TaskType


class ConstraintEngine:
    """
    Structural route constraints only.

    Output is a descriptive dictionary consumed by the route builder.
    """

    def apply(self, inquiry: InquiryPacket, graph: TaskGraph) -> Dict[str, object]:
        allowed_routes: List[str] = ["llm", "recall"]
        blocked_routes: List[str] = []
        notes: List[str] = []

        if graph.task_type == TaskType.MATH:
            allowed_routes.insert(0, "deterministic_solver")
            notes.append("math_solver_enabled")

        if graph.task_type == TaskType.AMBIGUOUS:
            allowed_routes.append("operator_query")
            notes.append("operator_query_enabled_for_ambiguity")

        if graph.task_type == TaskType.LOOKUP:
            notes.append("lookup_prefers_recall_or_llm")

        if inquiry.role is None or inquiry.mode is None:
            notes.append("no_substrate_role_mode_present")

        return {
            "allowed_routes": allowed_routes,
            "blocked_routes": blocked_routes,
            "notes": notes,
        }
