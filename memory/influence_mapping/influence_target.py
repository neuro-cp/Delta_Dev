from dataclasses import dataclass


@dataclass(frozen=True)
class InfluenceTarget:
    target_type: str
    magnitude: float
