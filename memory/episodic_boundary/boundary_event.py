
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class BoundaryEvent:
    step: int
    reason: str
    region: Optional[str] = None
