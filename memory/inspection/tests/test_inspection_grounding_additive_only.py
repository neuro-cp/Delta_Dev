from __future__ import annotations

from memory.inspection.inspection_builder import InspectionBuilder
from memory.semantic_grounding.grounding_record import SemanticRegionalGrounding
from memory.semantic_grounding.grounding_registry import SemanticGroundingRegistry


def test_grounding_is_additive_only(
    inspection_builder_without_grounding,
    inspection_builder_with_grounding,
) -> None:
    report_no = inspection_builder_without_grounding.build(
        report_id="no_grounding"
    )
    report_yes = inspection_builder_with_grounding.build(
        report_id="with_grounding"
    )

    # Core counts must match
    assert report_no.episode_count == report_yes.episode_count
    assert report_no.semantic_record_count == report_yes.semantic_record_count
    assert report_no.drift_record_count == report_yes.drift_record_count
    assert report_no.promotion_candidate_count == report_yes.promotion_candidate_count

    # Grounding must be the ONLY delta
    assert "semantic_grounding" not in report_no.summaries
    assert "semantic_grounding" in report_yes.summaries
