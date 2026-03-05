# memory/semantic_promotion/inspection_visibility_adapter.py

from __future__ import annotations

from typing import Iterable

from memory.inspection.inspection_report import InspectionReport
from memory.semantic_promotion.promoted_semantic import PromotedSemantic


class PromotionInspectionVisibilityAdapter:
    """
    Optional inspection adapter that exposes promoted semantics
    through inspection reports.

    CONTRACT:
    - Read-only
    - Offline only
    - No authority
    - No mutation
    - Safe to discard and recompute

    This adapter provides visibility only. It does not influence
    runtime, learning, replay, or promotion behavior.
    """

    def attach(
        self,
        *,
        report: InspectionReport,
        promoted_semantics: Iterable[PromotedSemantic],
    ) -> InspectionReport:
        promoted_list = list(promoted_semantics)

        # Copy report fields immutably
        kwargs = dict(report.__dict__)
        kwargs["summaries"] = dict(report.summaries)

        kwargs["summaries"]["promoted_semantics"] = [
            {
                "semantic_id": p.semantic_id,
                "policy_version": p.promotion_policy_version,
                "promotion_step": p.promotion_step,
                "promotion_time": p.promotion_time,
                "recurrence_count": p.recurrence_count,
                "persistence_span": p.persistence_span,
                "stability_classification": p.stability_classification,
                "confidence_estimate": p.confidence_estimate,
            }
            for p in promoted_list
        ]

        return InspectionReport(**kwargs)
