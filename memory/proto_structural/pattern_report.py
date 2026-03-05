from __future__ import annotations

from typing import List, Dict, Any

from memory.proto_structural.pattern_record import PatternRecord


class PatternReport:
    """
    Human-facing, inspection-only report of structural recurrence.

    CONTRACT:
    - Descriptive only
    - No evaluation language
    - No recommendations
    """

    def __init__(self, *, entries: List[Dict[str, Any]]) -> None:
        self.entries = entries


class PatternReportBuilder:
    def build(self, *, record: PatternRecord) -> PatternReport:
        entries: List[Dict[str, Any]] = []

        for sig, count in record.pattern_counts.items():
            entries.append(
                {
                    "signature": sig.as_canonical_tuple(),
                    "occurrences": count,
                }
            )

        return PatternReport(entries=entries)
