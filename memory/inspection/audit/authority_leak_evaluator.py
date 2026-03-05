from __future__ import annotations

from typing import List, Dict, Any

from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding
from memory.inspection.inspection_report import InspectionReport


class AuthorityLeakEvaluator(IntegrityAudit):
    """
    Audit-only evaluator for detecting semantic → authority leakage.

    CONTRACT:
    - Offline only
    - Inspection-layer only
    - No mutation
    - No gating
    - No authority
    - Safe to discard

    This class conforms to the IntegrityAudit interface and is
    executed only when explicitly included in an InspectionRunner.
    """

    AUDIT_ID = "authority_leak_evaluator"

    def __init__(self, *, report: InspectionReport) -> None:
        self._report = report

    # --------------------------------------------------
    # IntegrityAudit interface
    # --------------------------------------------------

    def run(self) -> List[IntegrityFinding]:
        """
        Execute the audit and return descriptive integrity findings.
        """
        return self._check_inspection_language()

    # --------------------------------------------------
    # Inspection language checks
    # --------------------------------------------------

    def _check_inspection_language(self) -> List[IntegrityFinding]:
        findings: List[IntegrityFinding] = []

        text_fields = [
            self._report.notes or "",
            *self._report.warnings,
            *self._report.anomalies,
        ]

        normative_tokens = (
            "should",
            "must",
            "recommended",
            "approved",
            "blocked",
            "failed",
            "passed",
        )

        for text in text_fields:
            lower = text.lower()
            matched = [t for t in normative_tokens if t in lower]

            if matched:
                findings.append(
                    IntegrityFinding(
                        audit_id=self.AUDIT_ID,
                        finding_id="inspection_normative_language",
                        severity="WARNING",
                        layer="inspection",
                        description=(
                            "Inspection text contains normative or prescriptive language."
                        ),
                        evidence={
                            "matched_tokens": matched,
                            "source_text": text,
                        },
                    )
                )
                break

        return findings
