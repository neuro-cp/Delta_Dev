from __future__ import annotations

from memory.inspection.exporters.json_exporter import JSONInspectionExporter
from memory.inspection.exporters.text_exporter import TextInspectionExporter


def test_grounding_exports_are_stable(
    inspection_report_with_grounding,
) -> None:
    json_blob = JSONInspectionExporter().export(
        inspection_report_with_grounding
    )
    text_blob = TextInspectionExporter().export(
        inspection_report_with_grounding
    )

    # Grounding must be visible
    assert "semantic_grounding" in json_blob
    assert "semantic_grounding" in text_blob

    # No numeric or dynamic influence allowed
    for forbidden in ("weight", "gain", "activation", "bias"):
        assert forbidden not in json_blob
        assert forbidden not in text_blob
