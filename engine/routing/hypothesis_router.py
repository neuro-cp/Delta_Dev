# engine/routing/hypothesis_router.py
from __future__ import annotations
from typing import Optional

from engine.routing.hypothesis_registry import HypothesisRegistry


class HypothesisRouter:
    """
    Routes activity based on hypothesis identity.

    If no hypothesis is present, routing is bypassed.
    """

    def __init__(self, registry: HypothesisRegistry):
        self.registry = registry

    def route(
        self,
        hypothesis_id: Optional[str],
        default_channel: Optional[str] = None,
    ) -> Optional[str]:
        """
        Returns the striatal channel to route into.

        - If hypothesis_id is None → return default_channel
        - If hypothesis_id is known → return mapped channel
        - If hypothesis_id is unknown → return default_channel
        """
        ch = self.registry.resolve(hypothesis_id)
        return ch if ch is not None else default_channel
