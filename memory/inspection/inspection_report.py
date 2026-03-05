from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from memory.inspection.audit.integrity_finding import IntegrityFinding
from memory.inspection.semantic_activation_report import SemanticActivationReport
from memory.inspection.promotion_report import PromotionReport


@dataclass(frozen=True)
class InspectionReport:
    """
    Immutable, offline inspection snapshot.
    """

    report_id: str
    generated_step: Optional[int]
    generated_time: Optional[float]

    inspected_components: List[str]

    episode_count: int
    semantic_record_count: int
    drift_record_count: int
    promotion_candidate_count: int

    summaries: Dict[str, Any] = field(default_factory=dict)

    # --------------------------------------------------
    # Cognitive layer visibility (optional, read-only)
    # --------------------------------------------------
    working_memory_bias: Optional[Dict[str, Any]] = None
    attention_bias: Optional[Dict[str, Any]] = None
    drive_state: Optional[Dict[str, Any]] = None

    semantic_activation: Optional[SemanticActivationReport] = None
    promotion_summary: Optional[PromotionReport] = None

    anomalies: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    policy_versions: Dict[str, str] = field(default_factory=dict)
    schema_versions: Dict[str, str] = field(default_factory=dict)

    notes: Optional[str] = None


@dataclass(frozen=True)
class InspectionAuditSummary:
    total_findings: int
    error_count: int
    warning_count: int
    by_audit: Dict[str, List[IntegrityFinding]]
    by_layer: Dict[str, List[IntegrityFinding]]
    by_severity: Dict[str, List[IntegrityFinding]]


@dataclass(frozen=True)
class InspectionReportWithAudits(InspectionReport):
    audits: InspectionAuditSummary = field(
        default_factory=lambda: InspectionAuditSummary(
            total_findings=0,
            error_count=0,
            warning_count=0,
            by_audit={},
            by_layer={},
            by_severity={},
        )
    )
