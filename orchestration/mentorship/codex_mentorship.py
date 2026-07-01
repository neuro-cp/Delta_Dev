from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from integration.model_runtime import ProviderPerformanceProfile
from knowledge import KnowledgeQualityReport


@dataclass(frozen=True)
class CodexMentorshipReport:
    findings: list[str]
    weaknesses: list[str]
    recommended_engineering_tasks: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class CodexMentorshipEngine:
    """
    Generate engineering mentorship from observed Delta evidence.

    Codex does not edit Delta cognition directly. It inspects reports and
    proposes architecture, governance, and validation work.
    """

    def generate(
        self,
        *,
        runtime_summary: dict[str, Any] | None = None,
        knowledge_quality: Sequence[KnowledgeQualityReport] = (),
        provider_profiles: Sequence[ProviderPerformanceProfile] = (),
    ) -> CodexMentorshipReport:
        summary = dict(runtime_summary or {})
        findings: list[str] = []
        weaknesses: list[str] = []
        tasks: list[str] = []

        if summary:
            ticks_requested = summary.get("ticks_requested")
            ticks_completed = summary.get("ticks_completed")
            findings.append(f"runtime_ticks={ticks_completed}/{ticks_requested}")
            if ticks_requested and ticks_completed != ticks_requested:
                weaknesses.append("runtime_incomplete")
                tasks.append("Investigate runtime interruption or tick failure.")

            prediction_quality = summary.get("prediction_quality", {})
            coverage = prediction_quality.get("coverage")
            if coverage is not None and coverage < 0.75:
                weaknesses.append("prediction_coverage_low")
                tasks.append("Improve prediction validation coverage.")

        weak_knowledge = [
            report
            for report in knowledge_quality
            if report.derived_confidence < 0.45 or report.contradiction_count > 0
        ]
        if weak_knowledge:
            weaknesses.append("knowledge_quality_pressure")
            tasks.append("Review weak or contradicted knowledge before distillation.")
            findings.append(f"weak_knowledge_count={len(weak_knowledge)}")

        if provider_profiles:
            findings.append(f"provider_profiles={len(provider_profiles)}")
        else:
            weaknesses.append("provider_evidence_missing")
            tasks.append("Run provider-observed curriculum experiments.")

        return CodexMentorshipReport(
            findings=findings,
            weaknesses=list(dict.fromkeys(weaknesses)),
            recommended_engineering_tasks=list(dict.fromkeys(tasks)),
            metadata={
                "role": "systems_engineering_mentor",
                "read_only": True,
                "does_not_edit_delta_cognition": True,
            },
        )
