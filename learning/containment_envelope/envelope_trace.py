from dataclasses import dataclass


@dataclass(frozen=True)
class ContainmentEnvelopeTrace:
    allowed_adjustment: int
    fragility_index: float
    max_adjustment: int
