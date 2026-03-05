from memory.attention.attention_item import AttentionItem


def test_attention_item_is_immutable() -> None:
    item = AttentionItem(
        key="x",
        gain=1.0,
        created_step=0,
        source="test",
    )

    try:
        item.gain = 0.5  # type: ignore
        assert False, "AttentionItem should be immutable"
    except Exception:
        pass
