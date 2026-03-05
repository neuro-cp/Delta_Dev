from __future__ import annotations

from typing import List

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord

from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding


class TemporalCoherenceAudit(IntegrityAudit):
    """
    Audit A2 — Temporal Coherence.

    Verifies that time- and step-based ordering across
    episodes and trace records is internally consistent.

    Read-only. Observational. No mutation.
    """

    audit_id = "A2_TEMPORAL_COHERENCE"

    def __init__(
        self,
        *,
        episode_tracker: EpisodeTracker,
        episode_trace: EpisodeTrace,
        consolidator: EpisodeConsolidator,
        semantic_registry: SemanticRegistry,
        drift_records: List[DriftRecord],
    ) -> None:
        self._episode_tracker = episode_tracker
        self._episode_trace = episode_trace
        self._consolidator = consolidator
        self._semantic_registry = semantic_registry
        self._drift_records = drift_records

    def run(self) -> List[IntegrityFinding]:
        findings: List[IntegrityFinding] = []

        # ==================================================
        # A2.1 Episode temporal ordering
        # ==================================================
        for ep in self._episode_tracker.episodes:
            if not ep.closed:
                continue

            # --- Time ordering ---
            if ep.end_time < ep.start_time:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"episode_time_inversion:{ep.episode_id}",
                        severity="ERROR",
                        layer="episodic",
                        description="Episode end_time precedes start_time.",
                        evidence={
                            "episode_id": ep.episode_id,
                            "start_time": ep.start_time,
                            "end_time": ep.end_time,
                        },
                    )
                )

            # --- Step ordering ---
            if ep.end_step < ep.start_step:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"episode_step_inversion:{ep.episode_id}",
                        severity="ERROR",
                        layer="episodic",
                        description="Episode end_step precedes start_step.",
                        evidence={
                            "episode_id": ep.episode_id,
                            "start_step": ep.start_step,
                            "end_step": ep.end_step,
                        },
                    )
                )

        # ==================================================
        # A2.2 Trace temporal ordering
        # ==================================================
        trace_by_episode = {}

        for rec in getattr(self._episode_trace, "_records", []):
            trace_by_episode.setdefault(rec.episode_id, []).append(rec)

        for episode_id, records in trace_by_episode.items():
            start_times = [r.time for r in records if r.kind == "start"]
            close_times = [r.time for r in records if r.kind == "close"]

            if not start_times or not close_times:
                continue

            earliest_start = min(start_times)
            earliest_close = min(close_times)

            if earliest_close < earliest_start:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"trace_time_inversion:{episode_id}",
                        severity="ERROR",
                        layer="trace",
                        description="Trace close precedes trace start in time.",
                        evidence={
                            "episode_id": episode_id,
                            "start_time": earliest_start,
                            "close_time": earliest_close,
                        },
                    )
                )

        return findings
