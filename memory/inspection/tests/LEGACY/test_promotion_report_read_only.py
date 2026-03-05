from __future__ import annotations

from memory.inspection.promotion_report import PromotionReportBuilder
from memory.semantic_promotion.promotion_candidate import PromotionCandidate


def _candidate(
    *,
    semantic_id: str,
    disqualified: bool,
    reasons: list[str],
) -> PromotionCandidate:
    return PromotionCandidate(
        semantic_id=semantic_id,
        pattern_type="test_pattern",
        policy_version="v1",
        schema_version="s1",
        supporting_episode_ids=[1, 2],
        recurrence_count=2,
        persistence_span=10,
        stability_classification="stable",
        drift_consistent=True,
        disqualified=disqualified,
        disqualification_reasons=reasons,
    )


def test_promotion_report_read_only() -> None:
    candidates = [
        _candidate(
            semantic_id="sem:a",
            disqualified=True,
            reasons=["insufficient_duration"],
        ),
        _candidate(
            semantic_id="sem:b",
            disqualified=False,
            reasons=[],
        ),
    ]

    report = PromotionReportBuilder().build(candidates=candidates)

    assert report.total_candidates == 2
    assert report.eligible_count == 1
    assert report.ineligible_count == 1
    assert report.reasons_count == {"insufficient_duration": 1}
    assert report.policy_version == "v1"
