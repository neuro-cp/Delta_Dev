from dataclasses import dataclass


@dataclass(frozen=True)
class FragilityReport:
    fragility_index: float
    coherence_index: int
    entropy_index: float
    momentum_index: int
    pressure: int
