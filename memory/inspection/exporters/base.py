from __future__ import annotations
from typing import Protocol
from memory.inspection.inspection_report import InspectionReport


class InspectionExporter(Protocol):
    """
    Export-only interface.

    Implementations must:
    - Not mutate the report
    - Not access runtime
    - Not compute new semantics
    """

    def export(self, report: InspectionReport) -> str:
        ...
