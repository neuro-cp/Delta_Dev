from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

from memory.episodic.episode_trace import EpisodeTrace, EpisodeTraceRecord


@dataclass(frozen=True)
class BoundaryInspectionReport:
    episodes: List[int]
    records: List[Dict[str, Any]]


def inspect_boundaries(trace: EpisodeTrace) -> BoundaryInspectionReport:
    records: List[EpisodeTraceRecord] = trace.records()

    out: List[Dict[str, Any]] = []
    episode_ids = set()

    for r in records:
        if r.event in ("start", "close"):
            episode_ids.add(r.episode_id)
            out.append({
                "episode_id": r.episode_id,
                "step": r.step,
                "event": r.event,
                "payload": dict(r.payload),
            })

    return BoundaryInspectionReport(
        episodes=sorted(episode_ids),
        records=out,
    )
