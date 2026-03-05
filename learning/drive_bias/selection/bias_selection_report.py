from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BiasSelectionReport:
    scores: Dict[str, float]
    selected_ids: List[str]
