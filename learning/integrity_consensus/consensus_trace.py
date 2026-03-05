from dataclasses import dataclass


@dataclass(frozen=True)
class ConsensusTrace:
    pressure: int
    aggregate_index: int
    recommended_adjustment: int
    disagreement_score: int
