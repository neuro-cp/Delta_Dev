from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ReflectionRecord:
    learned: List[str] = field(default_factory=list)
    repeated: List[str] = field(default_factory=list)
    surprises: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    consolidation_candidates: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
