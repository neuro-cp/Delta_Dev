from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BiasSelectionTrace:
    scores: Dict[str, float]
    selected_ids: List[str]
