
from dataclasses import dataclass


@dataclass(frozen=True)
class DummyProposal:
    proposal_id: str


def test_preview_respects_selection():
    from learning.drive_bias.promotion_preview.promotion_preview_engine import (
        PromotionPreviewEngine,
    )

    engine = PromotionPreviewEngine()

    proposals = [DummyProposal("a"), DummyProposal("b")]
    selected = ["a"]
    scores = {"a": 1.0, "b": 1.0}

    result = engine.preview(
        proposals=proposals,
        selected_ids=selected,
        scores=scores,
        threshold=0.0,
    )

    assert result == ["a"]
