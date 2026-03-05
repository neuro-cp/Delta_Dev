from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class CognitiveEvaluationReport:
    proposal_count: int
    selected_count: int
    promotable_count: int
    delta_surface: Dict[str, int]
    stability_index: int
