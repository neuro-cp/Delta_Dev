from __future__ import annotations

from memory.inspection.diffing.diff_runner import DiffRunner


def test_grounding_diff_is_isolated(
    inspection_report_without_grounding,
    inspection_report_with_grounding,
) -> None:
    diff = DiffRunner().run(
        inspection_report_without_grounding,
        inspection_report_with_grounding,
    )

    # Grounding differences allowed
    assert "semantic_grounding" in diff.changed_sections

    # Nothing else may change
    forbidden = {
        "semantic",
        "semantic_activation",
        "semantic_promotion",
        "semantic_drift",
        "learning",
        "episodic",
    }

    assert diff.changed_sections.isdisjoint(forbidden)
