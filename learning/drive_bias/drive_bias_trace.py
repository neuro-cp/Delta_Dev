from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DriveBiasTrace:
    proposal_scores: Dict[str, float]
