from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from memory.working_memory.active_context import WorkingMemoryContext


@dataclass(frozen=True)
class ReasoningFinding:
    kind: str
    text: str
    confidence: float
    supporting_keys: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeReasoningReport:
    question: str
    findings: list[ReasoningFinding]
    assumptions: list[str]
    conflicts: list[str]
    evidence_keys: list[str]
    confidence: float


class RuntimeReasoningEngine:
    """
    Deterministic, read-only reasoning over active working memory.

    It does not learn, store, validate, promote, or call providers. Its role is
    to identify what active knowledge appears relevant enough to support a
    response.
    """

    def reason(self, *, question: str, context: WorkingMemoryContext) -> RuntimeReasoningReport:
        items = sorted(context.items, key=lambda item: item.priority, reverse=True)
        findings: list[ReasoningFinding] = []
        evidence_keys: list[str] = []
        for item in items[:12]:
            if item.kind != "candidate_knowledge":
                continue
            evidence_keys.append(item.key)
            findings.append(
                ReasoningFinding(
                    kind="supporting_concept",
                    text=item.text,
                    confidence=_bounded(
                        (0.50 * item.priority)
                        + (0.30 * float(item.metadata.get("confidence", 0.0) or 0.0))
                        + (0.20 * float(item.metadata.get("promotion_score", 0.0) or 0.0))
                    ),
                    supporting_keys=[item.key],
                    metadata={
                        "recommendation": item.metadata.get("recommendation"),
                        "relevance": item.metadata.get("relevance"),
                        "projected_centrality": item.metadata.get("projected_centrality"),
                    },
                )
            )
        assumptions = _assumptions(question=question, findings=findings)
        conflicts = [
            finding.text
            for finding in findings
            if "tradeoff" in finding.text.lower() or "risk" in finding.text.lower()
        ][:5]
        confidence = _bounded(sum(finding.confidence for finding in findings[:5]) / max(1, min(5, len(findings))))
        return RuntimeReasoningReport(
            question=question,
            findings=findings,
            assumptions=assumptions,
            conflicts=conflicts,
            evidence_keys=evidence_keys,
            confidence=round(confidence, 4),
        )


def _assumptions(*, question: str, findings: list[ReasoningFinding]) -> list[str]:
    assumptions = []
    if re.search(r"\bshould\b|\bstrategy\b|\bplan\b|\bprepare\b", question, re.I):
        assumptions.append("The user is asking for an actionable recommendation, not only a factual summary.")
    if findings:
        assumptions.append("The response should be grounded in activated candidate knowledge rather than direct provider recall alone.")
    else:
        assumptions.append("Activated candidate knowledge is sparse; any response should state low evidence support.")
    return assumptions


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
