from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from memory.semantic_promotion.promotion_candidate import PromotionCandidate


@dataclass(frozen=True)
class PromotionReport:
    """
    Read-only inspection summary for semantic promotion eligibility.

    Descriptive only.
    No authority.
    Safe to discard and recompute.
    """

    total_candidates: int
    eligible_count: int
    ineligible_count: int
    reasons_count: Dict[str, int]
    policy_version: Optional[str]


class PromotionReportBuilder:
    """
    Builds descriptive promotion summaries from PromotionCandidate artifacts.

    CONTRACT:
    - Read-only
    - Deterministic
    - Eligibility derived from `disqualified`
    - No thresholds
    - No decisions
    """

    def build(
        self,
        *,
        candidates: List[PromotionCandidate],
    ) -> PromotionReport:
        reasons: Dict[str, int] = {}
        eligible_count = 0

        for candidate in candidates:
            if not candidate.disqualified:
                eligible_count += 1

            for reason in candidate.disqualification_reasons:
                reasons[reason] = reasons.get(reason, 0) + 1

        total = len(candidates)

        return PromotionReport(
            total_candidates=total,
            eligible_count=eligible_count,
            ineligible_count=total - eligible_count,
            reasons_count=reasons,
            policy_version=candidates[0].policy_version if candidates else None,
        )
#passed validation##