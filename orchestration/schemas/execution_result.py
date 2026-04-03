from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class EvaluationReport:
    passed: bool
    completeness: float
    consistency: float
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    plan_id: str
    route_type: str
    success: bool
    output: Any
    confidence: float
    artifacts: Dict[str, Any] = field(default_factory=dict)
    evaluation: Optional[EvaluationReport] = None
