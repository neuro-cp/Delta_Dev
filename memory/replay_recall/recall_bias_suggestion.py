from dataclasses import dataclass


@dataclass(frozen=True)
class RecallBiasSuggestion:
    semantic_id: str
    pressure: float
