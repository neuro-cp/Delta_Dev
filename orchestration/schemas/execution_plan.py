from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    selected_route_id: str
    selected_route_type: str
    target_node_id: str
    steps: List[str]
    metadata: Dict[str, object] = field(default_factory=dict)
