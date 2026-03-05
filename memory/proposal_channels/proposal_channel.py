from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from memory.proposal_channels.proposal_record import ProposalRecord


class ProposalChannel(ABC):
    """
    Abstract proposal channel.

    Channels convert eligible artifacts into
    symbolic proposals.

    Channels must be:
    - offline
    - deterministic
    - magnitude-free
    - authority-free
    """

    channel_id: str

    @abstractmethod
    def propose(
        self,
        *,
        eligible_artifacts: Iterable[object],
    ) -> List[ProposalRecord]:
        raise NotImplementedError
