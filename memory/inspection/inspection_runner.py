from __future__ import annotations

from typing import List, Dict, Optional
from collections import defaultdict

from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding
from memory.inspection.inspection_report import (
    InspectionReport,
    InspectionAuditSummary,
    InspectionReportWithAudits,
)
from memory.inspection.semantic_activation_report import (
    SemanticActivationReportBuilder,
)
from memory.inspection.promotion_report import PromotionReportBuilder
from memory.semantic_activation.multiscale_record import MultiscaleActivationRecord
from memory.semantic_promotion.promotion_candidate import PromotionCandidate


class InspectionRunner:
    """
    Offline inspection orchestrator.

    CONTRACT:
    - Offline only
    - Read-only
    - No mutation of runtime, memory, or cognition
    - Aggregates audit findings without interpretation
    """

    def __init__(
        self,
        *,
        base_report: InspectionReport,
        audits: List[IntegrityAudit],
        semantic_activation_record: Optional[MultiscaleActivationRecord] = None,
        promotion_candidates: Optional[List[PromotionCandidate]] = None,
    ) -> None:
        self._base_report = base_report
        self._audits = audits
        self._semantic_activation_record = semantic_activation_record
        self._promotion_candidates = promotion_candidates

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def run(self) -> InspectionReportWithAudits:
        """
        Execute all provided integrity audits and assemble
        a complete inspection report with audit summaries.

        This method:
        - does NOT gate
        - does NOT enforce
        - does NOT interpret findings
        """

        findings: List[IntegrityFinding] = []
        for audit in self._audits:
            findings.extend(audit.run())

        audit_summary = self._summarize(findings)

        # Start from immutable base report
        base_kwargs = dict(self._base_report.__dict__)

        if self._semantic_activation_record is not None:
            base_kwargs["semantic_activation"] = (
                SemanticActivationReportBuilder()
                .build(record=self._semantic_activation_record)
            )

        if self._promotion_candidates is not None:
            base_kwargs["promotion_summary"] = (
                PromotionReportBuilder()
                .build(candidates=self._promotion_candidates)
            )

        return InspectionReportWithAudits(
            **base_kwargs,
            audits=audit_summary,
        )

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _summarize(
        self,
        findings: List[IntegrityFinding],
    ) -> InspectionAuditSummary:
        """
        Aggregate integrity findings by audit, layer, and severity.

        This summary is descriptive only and carries no authority.
        """

        by_audit: Dict[str, List[IntegrityFinding]] = defaultdict(list)
        by_layer: Dict[str, List[IntegrityFinding]] = defaultdict(list)
        by_severity: Dict[str, List[IntegrityFinding]] = defaultdict(list)

        for finding in findings:
            by_audit[finding.audit_id].append(finding)
            by_layer[finding.layer].append(finding)
            by_severity[finding.severity].append(finding)

        return InspectionAuditSummary(
            total_findings=len(findings),
            error_count=len(by_severity.get("ERROR", [])),
            warning_count=len(by_severity.get("WARNING", [])),
            by_audit=dict(by_audit),
            by_layer=dict(by_layer),
            by_severity=dict(by_severity),
        )
