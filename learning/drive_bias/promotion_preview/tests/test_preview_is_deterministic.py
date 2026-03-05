
def test_preview_is_deterministic():
    from learning.drive_bias.promotion_preview.promotion_preview_engine import (
        PromotionPreviewEngine,
    )

    engine = PromotionPreviewEngine()

    proposals = []
    selected = ["a", "b"]
    scores = {"a": 0.5, "b": 0.5}

    r1 = engine.preview(proposals=proposals, selected_ids=selected, scores=scores)
    r2 = engine.preview(proposals=proposals, selected_ids=selected, scores=scores)

    assert r1 == r2
