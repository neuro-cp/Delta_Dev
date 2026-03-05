from __future__ import annotations

from collections import Counter
from typing import Iterable, Tuple

from memory.proto_structural.episode_signature import EpisodeSignature


class EpisodeSignatureBuilder:
    """
    Offline builder: Episode-like inputs → EpisodeSignature.

    CONTRACT:
    - Structural extraction only
    - No interpretation
    - No scoring
    """

    def build(
        self,
        *,
        length_steps: int,
        events: Iterable[str],
        regions: Iterable[str],
        transitions: Iterable[Tuple[str, str]],
    ) -> EpisodeSignature:
        event_list = list(events)
        region_set = frozenset(regions)

        transition_counter = Counter(transitions)
        transition_counts = tuple(
            (src, dst, count)
            for (src, dst), count in transition_counter.items()
        )

        return EpisodeSignature(
            length_steps=length_steps,
            event_count=len(event_list),
            event_types=frozenset(event_list),
            region_ids=region_set,
            transition_counts=transition_counts,
        )
