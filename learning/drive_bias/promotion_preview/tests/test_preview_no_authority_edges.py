
def test_preview_no_authority_edges():
    import inspect
    import learning.drive_bias.promotion_preview.promotion_preview_engine as mod

    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
    assert "semantic" not in src.lower()
