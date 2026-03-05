from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationTrace:
    recommended_adjustment: int
    stability_index: int
    drift_score: int
    pressure: int
