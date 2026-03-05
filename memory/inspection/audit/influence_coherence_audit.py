from __future__ import annotations

from typing import List, Dict

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord

from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding


class InfluenceCoherenceAudit(IntegrityAudit):
    """
    Audit A4 — Influence / Causal Coherence.

    Verifies that causal influence across layers is lawful:
    - Episodes must close before influencing semantics
    - Semantics must exist before drift
    - Consolidation must not invent causal sources

    Observational only. No mutation. No repair.
    """

    audit_id = "A4_INFLUENCE_COHERENCE"

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

    # --------------------------------------------------
    # Audit execution
    # --------------------------------------------------

    def run(self) -> List[IntegrityFinding]:
        findings: List[IntegrityFinding] = []

        # ==================================================
        # A4.1 Semantic must reference closed episodes only
        # ==================================================
        closed_episode_ids = {
            ep.episode_id
            for ep in self._episode_tracker.episodes
            if ep.closed
        }

        for record in self._semantic_registry.records:
            if record.episode_id not in closed_episode_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"semantic_influences_open_episode:{record.record_id}",
                        severity="ERROR",
                        layer="semantic",
                        description=(
                            "Semantic record references an episode that was "
                            "not closed at time of influence."
                        ),
                        evidence={
                            "semantic_id": record.record_id,
                            "episode_id": record.episode_id,
                        },
                    )
                )

        # ==================================================
        # A4.2 Drift must reference existing semantic records
        # ==================================================
        semantic_ids = {r.record_id for r in self._semantic_registry.records}

        for drift in self._drift_records:
            if drift.semantic_id not in semantic_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"drift_without_semantic:{drift.semantic_id}",
                        severity="ERROR",
                        layer="drift",
                        description=(
                            "Drift record references a semantic record "
                            "that does not exist."
                        ),
                        evidence={
                            "semantic_id": drift.semantic_id,
                            "timestamp": drift.timestamp,
                        },
                    )
                )

        # ==================================================
        # A4.3 Consolidation must not invent episode origins
        # ==================================================
        consolidated = self._consolidator.consolidate()
        known_episode_ids = {ep.episode_id for ep in self._episode_tracker.episodes}

        for c in consolidated:
            if c.episode_id not in known_episode_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"consolidation_without_episode:{c.episode_id}",
                        severity="ERROR",
                        layer="consolidation",
                        description=(
                            "Consolidated artifact references an episode "
                            "that does not exist in episodic memory."
                        ),
                        evidence={
                            "episode_id": c.episode_id,
                        },
                    )
                )

        return findings
