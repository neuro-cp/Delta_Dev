from dataclasses import dataclass


@dataclass(frozen=True)
class ContainmentEnvelopeReport:
    allowed_adjustment: int
    fragility_index: float
    max_adjustment: int
