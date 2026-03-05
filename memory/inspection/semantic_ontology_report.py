from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord
from memory.semantic_promotion.promotion_candidate import PromotionCandidate
from memory.semantic.semantic_ontology_registry import SemanticOntology


@dataclass(frozen=True)
class SemanticOntologyReport:
    """
    Human-facing inspection report organized by semantic ontology.

    This report is:
    - descriptive only
    - offline
    - non-authoritative
    - safe to discard and recompute

    Removing this report must not change system behavior.
    """

    ontology: SemanticOntology
    semantic_count: int
    drift_summary: Dict[str, int]
    promotion_eligibility_count: int
    notes: str | None = None


class SemanticOntologyReportBuilder:
    """
    Builder for ontology-aligned semantic inspection reports.

    This builder:
    - reads offline artifacts only
    - performs no mutation
    - performs no ranking
    - performs no inference
    """

    def build(
        self,
        *,
        registry: SemanticRegistry,
        drift_records: List[DriftRecord],
        promotion_candidates: List[PromotionCandidate],
    ) -> List[SemanticOntologyReport]:
        reports: List[SemanticOntologyReport] = []

        drift_by_type: Dict[str, List[DriftRecord]] = {}
        for d in drift_records:
            drift_by_type.setdefault(d.semantic_type, []).append(d)

        promo_by_type: Dict[str, List[PromotionCandidate]] = {}
        for p in promotion_candidates:
            promo_by_type.setdefault(p.pattern_type, []).append(p)

        for ontology in SemanticOntology:
            # Semantic records aligned to this ontology
            semantics = [
                r for r in registry.records
                if r.pattern_type == ontology.value
            ]

            # Drift diagnostics (descriptive only)
            drift = drift_by_type.get(ontology.value, [])
            drift_summary = {
                "total": len(drift),
                "persistent": sum(1 for d in drift if d.is_persistent),
                "novel": sum(1 for d in drift if d.is_novel),
            }

            # Promotion eligibility (no execution)
            promos = promo_by_type.get(ontology.value, [])
            eligible = sum(1 for p in promos if not p.disqualified)

            reports.append(
                SemanticOntologyReport(
                    ontology=ontology,
                    semantic_count=len(semantics),
                    drift_summary=drift_summary,
                    promotion_eligibility_count=eligible,
                    notes=None,
                )
            )

        return reports
