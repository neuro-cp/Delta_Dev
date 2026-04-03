from __future__ import annotations

from typing import Any, Dict

from orchestration.schemas.execution_result import ExecutionResult
from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.task_graph import TaskGraph


class StrategyMemory:
    """
    Extracts a reusable strategy record from a completed loop.

    No persistence. No mutation. Returns a descriptive dictionary.
    """

    def build_record(
        self,
        *,
        inquiry: InquiryPacket,
        graph: TaskGraph,
        result: ExecutionResult,
    ) -> Dict[str, Any]:
        return {
            "inquiry_id": inquiry.inquiry_id,
            "task_type": graph.task_type.value,
            "node_count": len(graph.nodes),
            "selected_route_type": result.route_type,
            "success": result.success,
            "confidence": result.confidence,
            "semantic_tokens": list(inquiry.semantic_tokens),
        }
