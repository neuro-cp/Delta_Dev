from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class AIOutputBundle:
    role: str
    mode: str
    payload: Dict[str, Any]
    confidence_band: Optional[float] = None
