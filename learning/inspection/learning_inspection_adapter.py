from __future__ import annotations

from typing import Dict, Any

from learning.schemas.learning_session_report import LearningSessionReport
from memory.inspection.inspection_report import InspectionReport


class LearningInspectionAdapter:
    """
    Optional adapter to attach learning summaries to InspectionReport.

    CONTRACT:
    - Read-only
    - No mutation of existing fields
    - Learning remains advisory
    """

    def attach(
        self,
        *,
        report: InspectionReport,
        session_report: LearningSessionReport,
    ) -> InspectionReport:
        summaries: Dict[str, Any] = dict(report.summaries)

        summaries["learning"] = {
            "replay_id": session_report.replay_id,
            "proposal_count": session_report.proposal_count,
            "rejected_count": session_report.rejected_count,
            "audit_passed": session_report.audit_passed,
            "audit_notes": session_report.audit_notes,
        }

        kwargs = dict(report.__dict__)
        kwargs["summaries"] = summaries

        return InspectionReport(**kwargs)
