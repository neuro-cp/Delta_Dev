from __future__ import annotations

from memory.proposal_channels.proposal_record import ProposalRecord
from memory.proposal_channels.inspection_adapter import (
    ProposalInspectionAdapter,
)


def test_inspection_adapter_returns_proposals_verbatim() -> None:
    record = ProposalRecord(
        proposal_id="prop:1",
        source_artifact_id="artifact:1",
        source_artifact_type="semantic_grounding",
        proposed_target="pfc",
        proposal_channel_id="channel:v1",
        rationale="symbolic suggestion",
    )

    adapter = ProposalInspectionAdapter()

    views = adapter.build_views(proposals=[record])

    assert views == [record]
