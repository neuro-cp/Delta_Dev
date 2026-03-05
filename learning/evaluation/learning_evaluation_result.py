from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class LearningEvaluationResult:
    """
    Result of an offline learning evaluation.

    CONTRACT:
    - Immutable
    - Serializable
    - No authority
    - No side effects
    """

    allowed: bool
    reasons: Tuple[str, ...] = ()
