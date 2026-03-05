from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RecallRuntimeResult:
    applied_targets: Dict[str, float]
