from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class RelationshipRecord:
    relationship_id: str
    created_at: str
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float = 1.0
    evidence: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
