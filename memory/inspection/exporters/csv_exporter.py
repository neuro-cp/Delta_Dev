from __future__ import annotations

import csv
import io
from memory.inspection.inspection_report import InspectionReport


class CSVInspectionExporter:
    """
    Flattens inspection counts and summaries only.

    Read-only view.
    No mutation.
    No authority.
    """

    def export(self, report: InspectionReport) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)

        writer.writerow(["field", "value"])

        # --- Core counts ---
        writer.writerow(["episode_count", report.episode_count])
        writer.writerow(["semantic_record_count", report.semantic_record_count])
        writer.writerow(["drift_record_count", report.drift_record_count])
        writer.writerow(
            ["promotion_candidate_count", report.promotion_candidate_count]
        )

        # --- Summaries (descriptive only) ---
        for key, value in report.summaries.items():
            writer.writerow([f"summary:{key}", value])

        return buf.getvalue()
