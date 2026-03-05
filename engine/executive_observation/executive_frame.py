
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class ExecutiveFrame:
    step: int
    episode_id: str | None
    observations: Dict[str, Any]
