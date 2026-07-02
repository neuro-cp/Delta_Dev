from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orchestration.runtime.runtime_reasoning import RuntimeReasoningReport


@dataclass(frozen=True)
class RuntimePlanOption:
    title: str
    steps: list[str]
    confidence: float
    supporting_evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimePlan:
    question: str
    options: list[RuntimePlanOption]
    recommended_option: str | None
    confidence: float


class RuntimePlanner:
    """
    Deterministic action-plan builder over a reasoning report.

    This is intentionally modest: it converts active reasoning into a small set
    of candidate response plans without learning or mutating state.
    """

    def plan(self, report: RuntimeReasoningReport) -> RuntimePlan:
        if not report.findings:
            option = RuntimePlanOption(
                title="Low-evidence response",
                steps=[
                    "State that Delta has insufficient activated candidate knowledge.",
                    "Answer conservatively from the question wording only.",
                    "Avoid claiming canonical knowledge support.",
                ],
                confidence=0.25,
                supporting_evidence=[],
                risks=["Response may be generic because no candidate knowledge activated."],
            )
            return RuntimePlan(
                question=report.question,
                options=[option],
                recommended_option=option.title,
                confidence=option.confidence,
            )

        top = report.findings[:5]
        evidence = [key for finding in top for key in finding.supporting_keys]
        risks = report.conflicts or ["No explicit conflict surfaced in the activated context."]
        evidence_option = RuntimePlanOption(
            title="Evidence-grounded recommendation",
            steps=[
                "Summarize the user's objective.",
                "Use the highest-confidence activated concepts as support.",
                "Name tradeoffs and uncertainty before recommending an action.",
                "Return a concise answer with evidence notes.",
            ],
            confidence=round(report.confidence, 4),
            supporting_evidence=evidence,
            risks=risks,
            metadata={"finding_count": len(report.findings)},
        )
        conservative_option = RuntimePlanOption(
            title="Conservative clarification-first response",
            steps=[
                "State the strongest activated concepts.",
                "Ask for missing constraints before prescribing a detailed plan.",
            ],
            confidence=round(max(0.2, report.confidence - 0.15), 4),
            supporting_evidence=evidence[:3],
            risks=["May be less useful if the user expects an immediate plan."],
        )
        return RuntimePlan(
            question=report.question,
            options=[evidence_option, conservative_option],
            recommended_option=evidence_option.title,
            confidence=evidence_option.confidence,
        )
