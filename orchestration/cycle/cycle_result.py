from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class CycleStageRecord:
    stage: str
    summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CognitiveCycleResult:
    """
    Output of one explicit Delta cognitive cycle.

    The cycle is coordination, not authority. Stages record what happened so the
    system can accumulate inspectable experience over time.
    """

    cycle_id: str
    prompt: str
    output: Any
    route_type: str
    success: bool
    confidence: float
    memory_ids: List[str]
    stages: List[CycleStageRecord]
    relationship_ids: List[str] = field(default_factory=list)
    learning_ids: List[str] = field(default_factory=list)
