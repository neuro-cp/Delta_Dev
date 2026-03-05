from __future__ import annotations


def test_grounding_does_not_change_versions(
    inspection_builder_without_grounding,
    inspection_builder_with_grounding,
) -> None:
    r0 = inspection_builder_without_grounding.build(report_id="no")
    r1 = inspection_builder_with_grounding.build(report_id="yes")

    assert r0.policy_versions == r1.policy_versions
    assert r0.schema_versions == r1.schema_versions
