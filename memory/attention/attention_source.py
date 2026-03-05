from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from memory.attention.attention_item import AttentionItem


class AttentionSource(ABC):
    """
    Abstract attention source.

    CONTRACT:
    - Read-only
    - Produces AttentionItems
    - No mutation of upstream systems
    """

    @abstractmethod
    def propose(self) -> Iterable[AttentionItem]:
        """
        Produce attention proposals.

        Must be:
        - Stateless or internally read-only
        - Deterministic per step
        """
        raise NotImplementedError
