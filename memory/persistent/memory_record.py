from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class MemoryRecord:
    """
    Durable autobiographical memory record.

    This is descriptive only. It does not authorize runtime action.
    """

    memory_id: str
    created_at: str
    kind: str
    text: str
    source: str
    layer: str = "experience"
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
