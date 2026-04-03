from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RouteCandidate:
    route_id: str
    route_type: str
    target_node_id: str
    rationale: str
    estimated_confidence: float = 0.0
    estimated_cost: float = 0.0
    allowed: bool = True
    blocked_reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)
