from __future__ import annotations

from memory.inspection.promotion_diff import PromotionDiffBuilder
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
        supporting_episode_ids=[1],
        recurrence_count=1,
        persistence_span=5,
        stability_classification="stable",
        drift_consistent=True,
        disqualified=disqualified,
        disqualification_reasons=reasons,
    )


def test_promotion_diff_basic() -> None:
    before = [
        _candidate(
            semantic_id="sem:a",
            disqualified=True,
            reasons=["x"],
        ),
        _candidate(
            semantic_id="sem:b",
            disqualified=False,
            reasons=[],
        ),
    ]

    after = [
        _candidate(
            semantic_id="sem:a",
            disqualified=False,
            reasons=[],
        ),
        _candidate(
            semantic_id="sem:b",
            disqualified=False,
            reasons=[],
        ),
    ]

    diff = PromotionDiffBuilder().build(before=before, after=after)

    assert diff.became_eligible == ["sem:a"]
    assert diff.became_ineligible == []
    assert diff.reason_deltas == {}
