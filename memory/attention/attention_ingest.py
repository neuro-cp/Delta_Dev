from __future__ import annotations

from typing import Iterable, List

from memory.attention.attention_item import AttentionItem
from memory.attention.attention_field import AttentionField
from memory.attention.attention_source import AttentionSource


class AttentionIngest:
    """
    Ingests attention proposals from multiple sources.

    CONTRACT:
    - Deterministic
    - Order-preserving
    - No interpretation
    """

    def __init__(
        self,
        *,
        field: AttentionField,
        sources: Iterable[AttentionSource],
    ) -> None:
        self._field = field
        self._sources: List[AttentionSource] = list(sources)

    def ingest(self) -> None:
        for source in self._sources:
            for item in source.propose():
                self._field.add(item)
