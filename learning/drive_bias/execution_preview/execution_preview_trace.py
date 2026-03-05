from dataclasses import dataclass
from typing import Dict, List

@dataclass(frozen=True)
class ExecutionPreviewTrace:
    promotable_ids: List[str]
    delta_surface: Dict[str, int]
