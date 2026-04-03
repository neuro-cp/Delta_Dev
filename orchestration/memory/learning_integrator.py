from __future__ import annotations

from typing import Any, Dict, Optional

from orchestration.schemas.execution_result import ExecutionResult
from orchestration.schemas.inquiry_packet import InquiryPacket


class LearningIntegrator:
    """
    Optional handoff into the existing learning input boundary.

    This class does not perform learning. It only prepares a lawful bundle
    if an injected adapter is available.
    """

    def __init__(self, *, learning_adapter: Optional[Any] = None) -> None:
        self._learning_adapter = learning_adapter

    def prepare_bundle(
        self,
        *,
        inquiry: InquiryPacket,
        result: ExecutionResult,
        strategy_record: Dict[str, Any],
    ) -> Optional[Any]:
        if self._learning_adapter is None:
            return None

        semantic_records = result.artifacts.get("semantic_activation_records")
        pattern_record = result.artifacts.get("pattern_record")
        semantic_episode_pairs = result.artifacts.get("semantic_episode_pairs")

        return self._learning_adapter.from_inspection_surface(
            replay_id=inquiry.inquiry_id,
            semantic_activation_records=semantic_records,
            pattern_record=pattern_record,
            semantic_episode_pairs=semantic_episode_pairs,
            tags={
                "selected_route_type": result.route_type,
                "task_type": strategy_record["task_type"],
            },
        )
