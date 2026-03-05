from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DriveBiasReport:
    scores: Dict[str, float]
