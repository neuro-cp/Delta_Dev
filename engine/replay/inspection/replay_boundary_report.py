from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

from engine.replay.execution.replay_execution_report import ReplayExecutionReport
from memory.episodic.episode_trace import EpisodeTrace


@dataclass(frozen=True)
class ReplayBoundaryReport:
    boundaries: List[Dict[str, Any]]


def build_replay_boundary_report(
    *,
    execution_report: ReplayExecutionReport,
    episode_trace: EpisodeTrace,
) -> ReplayBoundaryReport:
    """
    Build a boundary report for the episodes actually executed during replay.

    This function is:
    - Offline
    - Read-only
    - Replay-native (respects ReplayExecutionReport ordering)
    """
    executed_ids = set(execution_report.executed_episode_ids)
    out: List[Dict[str, Any]] = []

    for r in episode_trace.records():
        if r.event == "close" and r.episode_id in executed_ids:
            out.append({
                "episode_id": r.episode_id,
                "step": r.step,
                "reason": r.payload.get("reason"),
            })

    # Deterministic ordering
    out.sort(key=lambda x: (x["step"], x["episode_id"]))

    return ReplayBoundaryReport(boundaries=out)