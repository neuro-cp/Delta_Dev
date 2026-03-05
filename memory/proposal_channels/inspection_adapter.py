from __future__ import annotations

from typing import Iterable, List

from memory.proposal_channels.proposal_record import ProposalRecord


class ProposalInspectionAdapter:
    """
    Inspection-only adapter for proposal records.

    Provides visibility without authority.
    """

    def build_views(
        self,
        *,
        proposals: Iterable[ProposalRecord],
    ) -> List[ProposalRecord]:
        return list(proposals)
