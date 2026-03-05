from dataclasses import dataclass


@dataclass(frozen=True)
class DriveSignal:
    drive_id: str
    magnitude: float
    source: str
