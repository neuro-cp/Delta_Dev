from __future__ import annotations
from typing import List

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord
from memory.inspection.inspection_report import InspectionReport

from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding


class StructuralCoherenceAudit(IntegrityAudit):
    """
    Audit A1 — Structural & Count Coherence.

    Detects mismatches across episodic, consolidation,
    semantic, drift, and inspection layers.
    """

    audit_id = "A1_STRUCTURAL_COHERENCE"

    def __init__(
        self,
        *,
        episode_tracker: EpisodeTracker,
        episode_trace: EpisodeTrace,
        consolidator: EpisodeConsolidator,
        semantic_registry: SemanticRegistry,
        drift_records: List[DriftRecord],
        inspection_report: InspectionReport | None = None,
    ) -> None:
        self._episode_tracker = episode_tracker
        self._episode_trace = episode_trace
        self._consolidator = consolidator
        self._semantic_registry = semantic_registry
        self._drift_records = drift_records
        self._inspection_report = inspection_report

    def run(self) -> List[IntegrityFinding]:
        findings: List[IntegrityFinding] = []

        # --------------------------------------------------
        # A1.1 Episodic closure consistency
        # --------------------------------------------------
        traced_episode_ids = {
            r.episode_id
            for r in self._episode_trace.records()
            if r.event == "close"
}
        for ep in self._episode_tracker.episodes:
            if ep.closed and ep.episode_id not in traced_episode_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"missing_trace:{ep.episode_id}",
                        severity="ERROR",
                        layer="episodic",
                        description="Closed episode has no corresponding trace entry.",
                        evidence={"episode_id": ep.episode_id},
                    )
                )

        # --------------------------------------------------
        # A1.2 Consolidation coherence
        # --------------------------------------------------
        consolidated = self._consolidator.consolidate()
        closed_count = sum(1 for e in self._episode_tracker.episodes if e.closed)

        if len(consolidated) != closed_count:
            findings.append(
                IntegrityFinding(
                    audit_id=self.audit_id,
                    finding_id="consolidation_count_mismatch",
                    severity="ERROR",
                    layer="consolidation",
                    description="Consolidated episode count does not match closed episode count.",
                    evidence={
                        "closed_episodes": closed_count,
                        "consolidated": len(consolidated),
                    },
                )
            )

        # --------------------------------------------------
        # A1.3 Semantic grounding
        # --------------------------------------------------
        valid_episode_ids = {e.episode_id for e in self._episode_tracker.episodes}

        for r in self._semantic_registry.records:
            if r.episode_id not in valid_episode_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"orphan_semantic:{r.record_id}",
                        severity="ERROR",
                        layer="semantic",
                        description="Semantic record references missing episode.",
                        evidence={
                            "semantic_id": r.record_id,
                            "episode_id": r.episode_id,
                        },
                    )
                )

        # --------------------------------------------------
        # A1.4 Drift legitimacy
        # --------------------------------------------------
        semantic_ids = {r.record_id for r in self._semantic_registry.records}

        for d in self._drift_records:
            if d.semantic_id not in semantic_ids:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id=f"orphan_drift:{d.semantic_id}",
                        severity="ERROR",
                        layer="drift",
                        description="Drift record references missing semantic record.",
                        evidence={"semantic_id": d.semantic_id},
                    )
                )

        # --------------------------------------------------
        # A1.5 Inspection reconciliation
        # --------------------------------------------------
        if self._inspection_report is not None:
            if self._inspection_report.episode_count != len(self._episode_tracker.episodes):
                findings.append(
                    IntegrityFinding(
                        audit_id=self.audit_id,
                        finding_id="inspection_episode_count_mismatch",
                        severity="ERROR",
                        layer="inspection",
                        description="Inspection report episode count mismatch.",
                        evidence={
                            "reported": self._inspection_report.episode_count,
                            "actual": len(self._episode_tracker.episodes),
                        },
                    )
                )

        return findings
