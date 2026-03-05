from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class ExecutionPreviewReport:
    delta_surface: Dict[str, int]
