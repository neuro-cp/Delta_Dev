from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TaskType(str, Enum):
    MATH = "math"
    COMPARISON = "comparison"
    LOOKUP = "lookup"
    DIAGNOSTIC = "diagnostic"
    PLANNING = "planning"
    AMBIGUOUS = "ambiguous"
    OPEN_ENDED = "open_ended"


@dataclass(frozen=True)
class TaskNode:
    node_id: str
    label: str
    task_type: TaskType
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskGraph:
    graph_id: str
    root_node_id: str
    nodes: List[TaskNode]
    task_type: TaskType
    notes: List[str] = field(default_factory=list)

    def root(self) -> Optional[TaskNode]:
        for node in self.nodes:
            if node.node_id == self.root_node_id:
                return node
        return None
