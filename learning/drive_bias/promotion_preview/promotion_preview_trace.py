
from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PromotionPreviewTrace:
    selected_ids: List[str]
    promotable_ids: List[str]
    threshold: float
