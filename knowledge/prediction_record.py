from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class PredictionRecord:
    prediction_id: str
    created_at: str
    source_concept_id: str
    expectation: str
    confidence: float
    status: str = "open"
    supporting_observations: List[str] = field(default_factory=list)
    failing_observations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
