from __future__ import annotations

from typing import Iterable, List

from memory.influence_eligibility.eligibility_record import (
    InfluenceEligibilityRecord,
)


class InfluenceEligibilityInspectionAdapter:
    """
    Inspection-only adapter for influence eligibility records.

    Provides visibility without authority.
    """

    def build_views(
        self,
        *,
        records: Iterable[InfluenceEligibilityRecord],
    ) -> List[InfluenceEligibilityRecord]:
        return list(records)
