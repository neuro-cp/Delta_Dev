# engine/routing/hypothesis_registry.py
from __future__ import annotations
from typing import Dict, Optional


class HypothesisRegistry:
    """
    Static registry mapping hypothesis IDs to striatal channels.

    This is STRUCTURAL, not dynamic.
    No learning, no adaptation, no decay.
    """

    def __init__(self):
        self._map: Dict[str, str] = {}

    def register(self, hypothesis_id: str, channel: str) -> None:
        self._map[hypothesis_id] = channel

    def resolve(self, hypothesis_id: Optional[str]) -> Optional[str]:
        if hypothesis_id is None:
            return None
        return self._map.get(hypothesis_id)

    def dump(self) -> Dict[str, str]:
        return dict(self._map)
