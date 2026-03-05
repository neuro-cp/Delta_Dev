from __future__ import annotations

from typing import Optional, List

from memory.episodic.episode_tracker import EpisodeTracker
from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord
from memory.semantic_promotion.promotion_candidate import PromotionCandidate
from memory.inspection.inspection_report import InspectionReport

from memory.semantic_grounding.grounding_registry import (
    SemanticGroundingRegistry,
)
from memory.semantic_grounding.inspection_adapter import (
    SemanticGroundingInspectionAdapter,
)


class InspectionBuilder:
    """
    Offline builder for InspectionReport objects.

    This builder:
    - gathers counts and summaries
    - performs NO mutation
    - performs NO inference
    - carries NO authority
    - MUST NOT be used during runtime execution

    Removing this builder must not change system behavior.
    """

    def __init__(
        self,
        *,
        episode_tracker: EpisodeTracker,
        semantic_registry: SemanticRegistry,
        drift_records: List[DriftRecord],
        promotion_candidates: List[PromotionCandidate],
        semantic_grounding_registry: Optional[
            SemanticGroundingRegistry
        ] = None,
    ) -> None:
        self._episode_tracker = episode_tracker
        self._semantic_registry = semantic_registry
        self._drift_records = drift_records
        self._promotion_candidates = promotion_candidates
        self._semantic_grounding_registry = semantic_grounding_registry

        self._grounding_inspection_adapter = (
            SemanticGroundingInspectionAdapter()
            if semantic_grounding_registry is not None
            else None
        )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def build(
        self,
        *,
        report_id: str,
        generated_step: Optional[int] = None,
        generated_time: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> InspectionReport:
        """
        Build an immutable InspectionReport snapshot.
        """
        inspected_components = [
            "episodic",
            "semantic",
            "semantic_drift",
            "semantic_promotion",
        ]

        policy_versions = self._collect_policy_versions()
        schema_versions = self._collect_schema_versions()

        summaries = self._build_summaries()

        # --------------------------------------------------
        # Optional semantic grounding (inspection-only)
        # --------------------------------------------------
        if (
            self._semantic_grounding_registry is not None
            and self._grounding_inspection_adapter is not None
        ):
            summaries["semantic_grounding"] = (
                self._grounding_inspection_adapter.build_views(
                    grounding_registry=self._semantic_grounding_registry
                )
            )
            inspected_components.append("semantic_grounding")

        return InspectionReport(
            report_id=report_id,
            generated_step=generated_step,
            generated_time=generated_time,
            inspected_components=inspected_components,
            episode_count=len(self._episode_tracker.episodes),
            semantic_record_count=len(self._semantic_registry.records),
            drift_record_count=len(self._drift_records),
            promotion_candidate_count=len(self._promotion_candidates),
            summaries=summaries,
            anomalies=[],
            warnings=[],
            policy_versions=policy_versions,
            schema_versions=schema_versions,
            notes=notes,
        )

    # --------------------------------------------------
    # Internal helpers (read-only)
    # --------------------------------------------------

    def _collect_policy_versions(self) -> dict[str, str]:
        versions: dict[str, str] = {}

        for r in self._semantic_registry.records:
            versions.setdefault("semantic", r.policy_version)

        for d in self._drift_records:
            versions.setdefault("drift", d.policy_version)

        for c in self._promotion_candidates:
            versions.setdefault("promotion", c.policy_version)

        return versions

    def _collect_schema_versions(self) -> dict[str, str]:
        versions: dict[str, str] = {}

        for r in self._semantic_registry.records:
            versions.setdefault("semantic", r.schema_version)

        for d in self._drift_records:
            versions.setdefault("drift", d.schema_version)

        for c in self._promotion_candidates:
            versions.setdefault("promotion", c.schema_version)

        return versions

    def _build_summaries(self) -> dict[str, object]:
        """
        Lightweight, descriptive summaries only.
        """
        return {
            "episodes_closed": sum(
                1 for e in self._episode_tracker.episodes if e.closed
            ),
            "semantic_types": sorted(
                {r.pattern_type for r in self._semantic_registry.records}
            ),
            "drift_types": sorted(
                {d.semantic_type for d in self._drift_records}
            ),
            "promotion_disqualified_count": sum(
                1 for c in self._promotion_candidates if c.disqualified
            ),
        }
