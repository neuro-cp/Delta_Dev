
def test_preview_is_read_only():
    from learning.drive_bias.promotion_preview.promotion_preview_engine import (
        PromotionPreviewEngine,
    )

    engine = PromotionPreviewEngine()

    proposals = []
    selected = ["x"]
    scores = {"x": 1.0}

    before = dict(scores)
    engine.preview(proposals=proposals, selected_ids=selected, scores=scores)

    assert scores == before
