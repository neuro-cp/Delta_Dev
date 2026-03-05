from __future__ import annotations


def test_removal_of_grounding_does_not_break_inspection(
    inspection_builder_without_grounding,
) -> None:
    report = inspection_builder_without_grounding.build(
        report_id="safe_remove"
    )

    # Sanity: inspection still valid
    assert report.report_id == "safe_remove"
    assert report.episode_count >= 0
