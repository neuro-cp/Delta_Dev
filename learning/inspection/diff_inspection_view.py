from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class DiffInspectionView:
    """
    Read-only inspection view for a LearningBundleDiff.

    CONTRACT:
    - Purely observational
    - Deterministic
    - Serializable-friendly
    - No authority or feedback
    """
    has_difference: bool
    semantic: Dict[str, Any]
    structural: Dict[str, Any]
