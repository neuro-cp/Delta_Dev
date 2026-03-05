from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InfluenceEligibilityRecord:
    """
    Immutable, descriptive eligibility record.

    Represents a statement that an artifact *meets*
    predefined eligibility criteria.

    This does not grant influence.
    """

    artifact_id: str
    artifact_type: str

    eligibility_policy_id: str

    eligible: bool

    rationale: Optional[str] = None
