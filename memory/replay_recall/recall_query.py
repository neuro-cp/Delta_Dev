from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class RecallQuery:
    active_regions: Set[str]
    decision_present: bool
