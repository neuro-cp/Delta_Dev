from __future__ import annotations

import json
from memory.inspection.inspection_report import InspectionReport


class JSONInspectionExporter:
    """
    Explicit JSON view over an InspectionReport.

    Read-only.
    Descriptive only.
    No authority leakage.
    """

    def export(self, report: InspectionReport) -> str:
        payload = {
            # --- Provenance ---
            "report_id": report.report_id,
            "generated_step": report.generated_step,
            "generated_time": report.generated_time,
            "inspected_components": list(report.inspected_components),

            # --- Core counts ---
            "episode_count": report.episode_count,
            "semantic_record_count": report.semantic_record_count,
            "drift_record_count": report.drift_record_count,
            "promotion_candidate_count": report.promotion_candidate_count,

            # --- Descriptive summaries ---
            "summaries": self._lower(report.summaries),

            # --- Warnings only (human-facing) ---
            "warnings": list(report.warnings),
        }

        return json.dumps(payload, indent=2, sort_keys=True)

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _lower(self, obj):
        """
        Lower inspection-only objects to JSON-safe primitives.
        """
        if isinstance(obj, dict):
            return {k: self._lower(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._lower(v) for v in obj]
        if hasattr(obj, "__dict__"):
            # Inspection views only: structural, no behavior
            return {
                k: self._lower(v)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        return obj
