from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ValueProposal:
    """
    Proposed change to value state.

    CONTRACT:
    - Proposal only (may be rejected)
    - No authority
    - No policy
    """

    delta: float
    source: str
    note: Optional[str] = None


class ValueSource:
    """
    Interface for proposing value changes.

    Implementations may inspect offline data,
    episodic outcomes, or test scaffolds.

    CONTRACT:
    - Propose only
    - No state ownership
    """

    def propose(self) -> Optional[ValueProposal]:
        raise NotImplementedError
