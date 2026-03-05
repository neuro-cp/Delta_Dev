from __future__ import annotations

from typing import List, Dict
from collections import Counter

from memory.episodic.episode_tracker import EpisodeTracker
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord

from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding


class SaturationCoherenceAudit(IntegrityAudit):
    """
    Audit A5 — Saturation / Loop Coherence.

    Detects runaway reinforcement, drift accumulation,
    and replay loops that indicate stalled cognition.

    Observational only. No mutation.
    """

    audit_id = "A5_SATURATION_COHERENCE"

    def __init__(
        self,
        *,
        episode_tracker: EpisodeTracker,
        consolidator: EpisodeConsolidator,
        semantic_registry: SemanticRegistry,
        drift_records: List[DriftRecord],
        max_semantic_ratio: float = 0.6,
        max_replay_ratio: float = 0.5,
        max_monotonic_drift_steps: int = 3,
    ) -> None:
        self._episode_tracker = episode_tracker
        self._consolidator = consolidator
        self._semantic_registry = semantic_registry
        self._drift_records = drift_records

        self._max_semantic_ratio = max_semantic_ratio
        self._max_replay_ratio = max_replay_ratio
        self._max_monotonic_drift_steps = max_monotonic_drift_steps

    def run(self) -> List[IntegrityFinding]:
        findings: List[IntegrityFinding] = []

        episode_count = max(1, len(self._episode_tracker.episodes))

        # ==================================================
        # A5.1 Semantic saturation
        # ==================================================
        semantic_counts = Counter(
            getattr(r, "semantic_id", None)
            for r in self._semantic_registry.records
        )

        for semantic_id, count in semantic_counts.items():
            ratio = count / episode_count
            if ratio > self._max_semantic_ratio:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"semantic_saturation:{semantic_id}",
                        severity="WARNING",
                        layer="semantic",
                        description=(
                            "Semantic appears disproportionately often "
                            "relative to episode count."
                        ),
                        evidence={
                            "semantic_id": semantic_id,
                            "count": count,
                            "episode_count": episode_count,
                            "ratio": ratio,
                        },
                    )
                )

        # ==================================================
        # A5.2 Drift monotonic accumulation
        # ==================================================
        drift_by_semantic: Dict[str, List[float]] = {}

        for d in self._drift_records:
            sid = getattr(d, "semantic_id", None)
            drift_by_semantic.setdefault(sid, []).append(
                getattr(d, "delta", 0.0)
            )

        for semantic_id, deltas in drift_by_semantic.items():
            if len(deltas) < self._max_monotonic_drift_steps:
                continue

            if all(
                deltas[i] <= deltas[i + 1]
                for i in range(len(deltas) - 1)
            ):
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"drift_runaway:{semantic_id}",
                        severity="WARNING",
                        layer="drift",
                        description=(
                            "Drift magnitude increases monotonically "
                            "without stabilization."
                        ),
                        evidence={
                            "semantic_id": semantic_id,
                            "deltas": deltas,
                        },
                    )
                )

        # ==================================================
        # A5.3 Episode replay loop
        # ==================================================
        consolidated = self._consolidator.consolidate()
        episode_ids = [
            getattr(c, "episode_id", None)
            for c in consolidated
        ]

        if episode_ids:
            replay_counts = Counter(episode_ids)
            total = len(episode_ids)

            for eid, count in replay_counts.items():
                ratio = count / total
                if ratio > self._max_replay_ratio:
                    findings.append(
                        IntegrityFinding(
                            audit_id=self.audit_id,
                            finding_id=f"episode_replay_loop:{eid}",
                            severity="WARNING",
                            layer="consolidation",
                            description=(
                                "Episode appears repeatedly in consolidation "
                                "output, indicating a replay loop."
                            ),
                            evidence={
                                "episode_id": eid,
                                "count": count,
                                "total": total,
                                "ratio": ratio,
                            },
                        )
                    )

        return findings
