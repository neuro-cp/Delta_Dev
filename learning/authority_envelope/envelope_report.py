from dataclasses import dataclass


@dataclass(frozen=True)
class EnvelopeReport:
    envelope_magnitude: int
    disagreement_score: int
    pressure: int
    recommended_adjustment: int
