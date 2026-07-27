from __future__ import annotations

from enum import Enum


class ModelExecutionLane(str, Enum):
    CHAT = "chat"
    COGNITIVE_OPERATION = "cognitive_operation"


def normalize_execution_lane(value: object, *, task_type: str = "") -> ModelExecutionLane:
    if isinstance(value, ModelExecutionLane):
        return value
    raw = str(value or "").strip()
    if not raw:
        if task_type == "active_cognitive_json_operation":
            return ModelExecutionLane.COGNITIVE_OPERATION
        return ModelExecutionLane.CHAT
    try:
        return ModelExecutionLane(raw)
    except ValueError as exc:
        raise ValueError(f"unsupported_model_execution_lane:{raw}") from exc
