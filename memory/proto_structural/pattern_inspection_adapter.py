from __future__ import annotations

from memory.inspection.inspection_report import InspectionReport
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.pattern_report import PatternReportBuilder


class ProtoStructuralInspectionAdapter:
    """
    Optional adapter to expose proto-structural patterns
    through inspection reports.

    CONTRACT:
    - Read-only
    - Optional
    - No authority
    """

    def attach(
        self,
        *,
        report: InspectionReport,
        pattern_record: PatternRecord,
    ) -> InspectionReport:
        builder = PatternReportBuilder()
        pattern_report = builder.build(record=pattern_record)

        kwargs = dict(report.__dict__)
        kwargs["proto_structural_patterns"] = pattern_report

        return InspectionReport(**kwargs)
