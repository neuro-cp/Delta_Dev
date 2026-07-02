from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orchestration.runtime.runtime_planning import RuntimePlan
from orchestration.runtime.runtime_reasoning import RuntimeReasoningReport


@dataclass(frozen=True)
class RuntimeResponseDraft:
    answer: str
    confidence: float
    evidence_used: list[str]
    assumptions: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeResponseGenerator:
    """
    Deterministic response drafter over reasoning and planning artifacts.

    This does not call an LLM. It gives Runtime v1 a transparent baseline for
    testing whether activated knowledge can support an answer.
    """

    def draft(self, *, reasoning: RuntimeReasoningReport, plan: RuntimePlan) -> RuntimeResponseDraft:
        option = next((item for item in plan.options if item.title == plan.recommended_option), plan.options[0])
        if not reasoning.findings:
            answer = (
                "I do not have enough activated candidate knowledge to answer this with strong support. "
                "A conservative response should identify missing constraints and avoid claiming learned evidence."
            )
        else:
            support_lines = [
                f"- {finding.text}"
                for finding in reasoning.findings[:3]
            ]
            risk_lines = [f"- {risk}" for risk in option.risks[:3]]
            answer = "\n".join(
                [
                    "Recommended response strategy:",
                    "",
                    *[f"{index + 1}. {step}" for index, step in enumerate(option.steps)],
                    "",
                    "Activated support:",
                    *support_lines,
                    "",
                    "Risks or tradeoffs:",
                    *risk_lines,
                ]
            )
        return RuntimeResponseDraft(
            answer=answer,
            confidence=option.confidence,
            evidence_used=list(option.metadata.get("response_citable_evidence", option.supporting_evidence)),
            assumptions=list(reasoning.assumptions),
            metadata={
                "recommended_option": plan.recommended_option,
                "reasoning_confidence": reasoning.confidence,
                "plan_confidence": plan.confidence,
            },
        )
