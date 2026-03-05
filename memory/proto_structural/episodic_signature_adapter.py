from __future__ import annotations

from typing import Iterable, Tuple, List

from memory.proto_structural.signature_builder import EpisodeSignatureBuilder
from memory.proto_structural.episode_signature import EpisodeSignature
from memory.episodic.episode_trace import EpisodeTraceRecord


class EpisodicSignatureAdapter:
    """
    Offline adapter: Episode → EpisodeSignature.

    CONTRACT:
    - Offline only
    - Structural extraction only
    - No interpretation
    - No accumulation
    - No mutation of inputs
    - No inspection coupling
    """

    def __init__(self) -> None:
        self._builder = EpisodeSignatureBuilder()

    def build_signature(
        self,
        *,
        episode,
        episode_trace,
    ) -> EpisodeSignature:
        """
        Build a structural EpisodeSignature from a CLOSED episode.

        REQUIRED episode interface:
        - episode.episode_id : int
        - episode.closed     : bool

        REQUIRED episode_trace interface:
        - records() -> List[EpisodeTraceRecord]
        """

        if not episode.closed:
            raise ValueError(
                "EpisodicSignatureAdapter requires a CLOSED episode."
            )

        # --------------------------------------------------
        # Filter records for this episode
        # --------------------------------------------------
        records: List[EpisodeTraceRecord] = [
            r for r in episode_trace.records()
            if r.episode_id == episode.episode_id
        ]

        if not records:
            raise ValueError(
                "No trace records found for closed episode."
            )

        # --------------------------------------------------
        # Derive length (forensic)
        # --------------------------------------------------
        steps = [r.step for r in records]
        length_steps: int = max(steps) - min(steps) + 1

        # --------------------------------------------------
        # Structural event types
        # --------------------------------------------------
        events: List[str] = [r.event for r in records]

        # --------------------------------------------------
        # Structural region set (payload-derived only)
        # --------------------------------------------------
        regions = set()
        for r in records:
            for key in ("region", "source_region", "target_region", "winner"):
                val = r.payload.get(key)
                if isinstance(val, str):
                    regions.add(val)

        # --------------------------------------------------
        # Structural transitions (temporal)
        # --------------------------------------------------
        transitions: List[Tuple[str, str]] = []
        for prev, curr in zip(events, events[1:]):
            transitions.append((prev, curr))

        return self._builder.build(
            length_steps=length_steps,
            events=events,
            regions=regions,
            transitions=transitions,
        )
