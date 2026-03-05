from dataclasses import dataclass


@dataclass(frozen=True)
class RecallExecutionInfluence:
    semantic_id: str
    scaled_pressure: float
