from __future__ import annotations

from typing import List

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord

from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding


class ProvenanceCoherenceAudit(IntegrityAudit):
    """
    Audit A3 — Provenance Coherence.

    Ensures that every derived structure (semantic, drift, consolidation)
    can be traced back to a valid originating episode.

    This audit enforces lineage integrity only.
    No timing, no counts, no mutation.
    """

    audit_id = "A3_PROVENANCE_COHERENCE"

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

        episode_ids = {e.episode_id for e in self._episode_tracker.episodes}

        # ==================================================
        # A3.1 Semantic → Episode provenance
        # ==================================================
        for record in self._semantic_registry.records:
            if record.episode_id not in episode_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"semantic_orphan:{record.record_id}",
                        severity="ERROR",
                        layer="semantic",
                        description=(
                            "Semantic record references a non-existent episode."
                        ),
                        evidence={
                            "semantic_id": record.record_id,
                            "episode_id": record.episode_id,
                        },
                    )
                )

        semantic_ids = {r.record_id for r in self._semantic_registry.records}

        # ==================================================
        # A3.2 Drift → Semantic provenance
        # ==================================================
        for drift in self._drift_records:
            if drift.semantic_id not in semantic_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"drift_orphan:{drift.semantic_id}",
                        severity="ERROR",
                        layer="drift",
                        description=(
                            "Drift record references a missing semantic record."
                        ),
                        evidence={"semantic_id": drift.semantic_id},
                    )
                )

        # ==================================================
        # A3.3 Consolidation → Episode provenance
        # ==================================================
        consolidated = self._consolidator.consolidate()

        for c in consolidated:
            if c.episode_id not in episode_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"consolidation_orphan:{c.episode_id}",
                        severity="ERROR",
                        layer="consolidation",
                        description=(
                            "Consolidated episode has no originating episode."
                        ),
                        evidence={"episode_id": c.episode_id},
                    )
                )

        return findings
