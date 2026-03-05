from __future__ import annotations

from typing import List, Dict, Any

from memory.proto_structural.pattern_statistics import PatternStatistics


class PatternStatisticsReport:
    """
    Inspection-only view of structural recurrence statistics.

    CONTRACT:
    - Descriptive only
    - No evaluation language
    - No recommendations
    """

    def __init__(self, *, entries: List[Dict[str, Any]]) -> None:
        self.entries = entries


class PatternStatisticsReportBuilder:
    """
    Builder: PatternStatistics → PatternStatisticsReport.
    """

    def build(self, *, stats: PatternStatistics) -> PatternStatisticsReport:
        entries: List[Dict[str, Any]] = []

        for sig in stats.ordered_signatures:
            entries.append(
                {
                    "signature": sig.as_canonical_tuple(),
                    "occurrences": stats.counts[sig],
                    "relative_frequency": stats.relative_frequency.get(sig, 0.0),
                }
            )

        return PatternStatisticsReport(entries=entries)