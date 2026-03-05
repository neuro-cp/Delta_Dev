
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PromotionPreviewReport:
    proposal_id: str
    selected: bool
    promotable: bool
    score: Optional[float]
    reason: Optional[str] = None
