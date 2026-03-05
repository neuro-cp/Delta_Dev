from dataclasses import dataclass


@dataclass(frozen=True)
class CoherenceReport:
    coherence_index: int
    stability_index: int
    drift_score: int
    risk_index: int
    envelope_magnitude: int
