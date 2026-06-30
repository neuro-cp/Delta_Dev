from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class ContradictionRecord:
    contradiction_id: str
    created_at: str
    claim_a_id: str
    claim_b_id: str
    reason: str
    severity: float
    metadata: Dict[str, Any] = field(default_factory=dict)
