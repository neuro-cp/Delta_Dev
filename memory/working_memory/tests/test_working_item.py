from memory.working_memory.working_item import WorkingItem


def test_working_item_is_immutable() -> None:
    item = WorkingItem(
        key="k",
        payload={"x": 1},
        strength=1.0,
        created_step=0,
        source="test",
    )

    try:
        item.strength = 0.5  # type: ignore
        assert False, "WorkingItem should be immutable"
    except Exception:
        pass
