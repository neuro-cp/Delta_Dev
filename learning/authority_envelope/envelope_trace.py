from dataclasses import dataclass


@dataclass(frozen=True)
class EnvelopeTrace:
    envelope_magnitude: int
    disagreement_score: int
    pressure: int
    recommended_adjustment: int
