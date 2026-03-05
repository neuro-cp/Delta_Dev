from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProposalRecord:
    """
    Immutable proposal record.

    A proposal is a symbolic statement that an artifact
    *suggests* a possible influence target.

    It does NOT apply influence.
    """

    proposal_id: str

    source_artifact_id: str
    source_artifact_type: str

    proposed_target: str  # symbolic (e.g. region_id)

    proposal_channel_id: str

    rationale: Optional[str] = None
