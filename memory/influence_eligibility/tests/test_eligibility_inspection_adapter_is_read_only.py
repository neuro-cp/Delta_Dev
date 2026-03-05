from __future__ import annotations

from memory.influence_eligibility.eligibility_record import (
    InfluenceEligibilityRecord,
)
from memory.influence_eligibility.inspection_adapter import (
    InfluenceEligibilityInspectionAdapter,
)


def test_inspection_adapter_returns_records_verbatim() -> None:
    record = InfluenceEligibilityRecord(
        artifact_id="artifact:1",
        artifact_type="semantic_grounding",
        eligibility_policy_id="policy:v1",
        eligible=True,
        rationale="meets criteria",
    )

    adapter = InfluenceEligibilityInspectionAdapter()

    views = adapter.build_views(records=[record])

    assert views == [record]
