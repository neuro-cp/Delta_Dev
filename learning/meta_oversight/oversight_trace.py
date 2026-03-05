from dataclasses import dataclass


@dataclass(frozen=True)
class OversightTrace:
    aggregate_index: int
    pressure: int
    execution_surface: int
    drive_score: int
