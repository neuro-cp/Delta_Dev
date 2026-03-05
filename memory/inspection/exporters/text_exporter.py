from __future__ import annotations
from memory.inspection.inspection_report import InspectionReport


class TextInspectionExporter:
    """
    Human-readable inspection summary.

    Read-only.
    Descriptive only.
    """

    def export(self, report: InspectionReport) -> str:
        lines: list[str] = []

        lines.append("INSPECTION REPORT")
        lines.append("=" * 20)

        # --- Provenance ---
        lines.append(f"Report ID: {report.report_id}")
        lines.append(f"Generated step: {report.generated_step}")
        lines.append(f"Generated time: {report.generated_time}")
        lines.append(f"Inspected components: {', '.join(report.inspected_components)}")

        lines.append("")

        # --- Core counts ---
        lines.append(f"Episode count: {report.episode_count}")
        lines.append(f"Semantic record count: {report.semantic_record_count}")
        lines.append(f"Drift record count: {report.drift_record_count}")
        lines.append(f"Promotion candidate count: {report.promotion_candidate_count}")

        # --- Summaries ---
        if report.summaries:
            lines.append("")
            lines.append("Summaries:")
            for key, value in report.summaries.items():
                lines.append(f"  - {key}: {value}")

        # --- Warnings ---
        if report.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in report.warnings:
                lines.append(f"  * {warning}")

        return "\n".join(lines)
