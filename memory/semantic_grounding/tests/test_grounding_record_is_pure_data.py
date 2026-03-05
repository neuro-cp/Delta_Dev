from __future__ import annotations

from memory.semantic_grounding.grounding_record import (
    SemanticRegionalGrounding,
)


def test_grounding_record_is_immutable() -> None:
    record = SemanticRegionalGrounding(
        semantic_id="sem:1",
        grounded_regions=frozenset({"pfc", "pulvinar"}),
        notes=None,
    )

    try:
        record.semantic_id = "mutated"  # type: ignore[misc]
        mutated = True
    except Exception:
        mutated = False

    assert mutated is False


def test_grounding_record_has_no_numeric_fields() -> None:
    record = SemanticRegionalGrounding(
        semantic_id="sem:1",
        grounded_regions=frozenset({"pfc"}),
        notes=None,
    )

    for value in record.__dict__.values():
        assert not isinstance(value, (int, float))
