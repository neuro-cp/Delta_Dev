from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from memory.semantic_activation.multiscale_record import (
    MultiscaleActivationRecord,
)


@dataclass(frozen=True)
class SemanticActivationReport:
    """
    High-level, human-facing inspection report for semantic activation.

    Descriptive only.
    No authority.
    Safe to discard and recompute.
    """

    snapshot_index: int
    scales_present: List[str]
    term_counts_by_scale: Dict[str, int]
    value_ranges_by_scale: Dict[str, Dict[str, float]]


class SemanticActivationReportBuilder:
    """
    Builds descriptive inspection summaries from multiscale
    semantic activation snapshots.

    CONTRACT:
    - Read-only
    - Deterministic
    - No thresholds
    - No rankings
    - No policy
    """

    def build(
        self,
        *,
        record: Optional[MultiscaleActivationRecord],
    ) -> Optional[SemanticActivationReport]:
        if record is None:
            return None

        term_counts: Dict[str, int] = {}
        ranges: Dict[str, Dict[str, float]] = {}

        for scale, activations in record.activations_by_scale.items():
            term_counts[scale] = len(activations)

            if activations:
                values = list(activations.values())
                ranges[scale] = {
                    "min": min(values),
                    "max": max(values),
                }
            else:
                ranges[scale] = {
                    "min": 0.0,
                    "max": 0.0,
                }

        return SemanticActivationReport(
            snapshot_index=record.snapshot_index,
            scales_present=list(record.activations_by_scale.keys()),
            term_counts_by_scale=term_counts,
            value_ranges_by_scale=ranges,
        )
