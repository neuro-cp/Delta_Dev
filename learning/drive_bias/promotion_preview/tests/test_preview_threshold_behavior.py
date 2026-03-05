
from dataclasses import dataclass


@dataclass(frozen=True)
class DummyProposal:
    proposal_id: str


def test_preview_threshold_behavior():
    from learning.drive_bias.promotion_preview.promotion_preview_engine import (
        PromotionPreviewEngine,
    )

    engine = PromotionPreviewEngine()

    proposals = [DummyProposal("a")]
    selected = ["a"]
    scores = {"a": 0.4}

    result = engine.preview(
        proposals=proposals,
        selected_ids=selected,
        scores=scores,
        threshold=0.5,
    )

    assert result == []
