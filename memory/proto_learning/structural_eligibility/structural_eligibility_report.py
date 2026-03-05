from __future__ import annotations
from typing import List, Dict, Any
from .structural_candidate import StructuralCandidate

class StructuralEligibilityReport:
    def __init__(self, *, entries: List[Dict[str, Any]]) -> None:
        self.entries = entries

class StructuralEligibilityReportBuilder:
    def build(self, *, candidates: List[StructuralCandidate]) -> StructuralEligibilityReport:
        entries: List[Dict[str, Any]] = []

        for c in candidates:
            entries.append(
                {
                    "signature": c.signature.as_canonical_tuple(),
                    "occurrences": c.occurrences,
                    "relative_frequency": c.relative_frequency,
                    "confidence_score": c.confidence_score,
                }
            )

        return StructuralEligibilityReport(entries=entries)
