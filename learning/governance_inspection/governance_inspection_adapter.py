from __future__ import annotations

from typing import Any, Dict


class GovernanceInspectionAdapter:
    """
    Read-only governance inspection adapter.

    CONTRACT:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    - No registry access
    - No authority
    - Safe to discard
    """

    def summarize(self, *, session_report: Any) -> Dict[str, Any]:
        """
        Extracts governance-relevant information
        from a LearningSessionReport.

        Returns a normalized, inspection-safe dict.
        """

        if session_report is None:
            return {}

        record = getattr(session_report, "governance_record", None)
        approved = getattr(session_report, "governance_approved", None)

        if record is None:
            return {
                "governance_present": False,
                "approved": None,
            }

        return {
            "governance_present": True,
            "approved": approved,
            "fragility_index": record.get("fragility_index"),
            "fragility_ratio": record.get("fragility_ratio"),
            "max_adjustment": record.get("max_adjustment"),
            "allowed_adjustment": record.get("allowed_adjustment"),
            "proposed_adjustment": record.get("proposed_adjustment"),
            "applied_adjustment": record.get("applied_adjustment"),
            "was_clamped": record.get("was_clamped"),
        }