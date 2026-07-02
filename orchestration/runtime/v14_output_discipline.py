from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class AnswerConfidenceBand(str, Enum):
    DIRECT_ANSWER = "direct_answer"
    BEST_GUESS = "best_guess"
    WEAK_GUESS = "weak_guess"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ROUTE_TO_SPECIALIST = "route_to_specialist"
    ABSTAIN = "abstain"


class UnknownAnswerReason(str, Enum):
    MISSING_EVIDENCE = "missing_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    WEAK_CONTEXT = "weak_context"
    HIGH_NOISE_RISK = "high_noise_risk"
    UNSAFE_ACTION_RISK = "unsafe_action_risk"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    OUTSIDE_DOMAIN = "outside_domain"
    NEEDS_SPECIALIST = "needs_specialist"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OutputDisciplineDecision:
    confidence_band: AnswerConfidenceBand
    reason: UnknownAnswerReason
    should_answer: bool
    should_route: bool
    should_abstain: bool
    allowed_phrasing: tuple[str, ...] = ()
    blocked_phrasing: tuple[str, ...] = ()
    evidence_summary: str = ""
    confidence: float = 0.0
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "confidence_band": self.confidence_band.value,
            "reason": self.reason.value,
            "should_answer": self.should_answer,
            "should_route": self.should_route,
            "should_abstain": self.should_abstain,
            "allowed_phrasing": list(self.allowed_phrasing),
            "blocked_phrasing": list(self.blocked_phrasing),
            "evidence_summary": self.evidence_summary,
            "confidence": self.normalized_confidence(),
            "notes": self.notes,
        }


SAFE_UNKNOWN_LOOKUP_PHRASE = "I don't know yet. Let me look."
BEST_GUESS_PREFIX = "My best guess is..."
WEAK_GUESS_PREFIX = "I think..."
STRONGEST_ANSWER_PREFIX = "The strongest answer I found is..."
LOW_CONFIDENCE_PHRASE = "I'm not confident enough to answer directly."
ACTION_CAUTION_PHRASE = "This needs more evidence before action."

OVERCONFIDENT_PATTERNS = (
    r"\bdefinitely\b",
    r"\bcertainly\b",
    r"\bobviously\b",
    r"\bguaranteed\b",
    r"\bmust\b",
    r"\balways\b",
    r"\bnever\b",
    r"\bwithout (?:a )?doubt\b",
)


def decide_output_mode(
    *,
    evidence_count: int = 0,
    confidence: float = 0.0,
    noise_risk: float = 0.0,
    conflicting_evidence: bool = False,
    unsafe_action_risk: bool = False,
    outside_domain: bool = False,
    needs_specialist: bool = False,
    evidence_summary: str = "",
) -> OutputDisciplineDecision:
    confidence = max(0.0, min(1.0, float(confidence)))
    noise_risk = max(0.0, min(1.0, float(noise_risk)))
    blocked = tuple(pattern.strip("\\b") for pattern in OVERCONFIDENT_PATTERNS)

    if unsafe_action_risk:
        return OutputDisciplineDecision(
            confidence_band=AnswerConfidenceBand.ABSTAIN,
            reason=UnknownAnswerReason.UNSAFE_ACTION_RISK,
            should_answer=False,
            should_route=False,
            should_abstain=True,
            allowed_phrasing=(ACTION_CAUTION_PHRASE, LOW_CONFIDENCE_PHRASE),
            blocked_phrasing=blocked,
            evidence_summary=evidence_summary,
            confidence=confidence,
            notes="unsafe action risk requires abstention or bounded caution",
        )
    if needs_specialist:
        return OutputDisciplineDecision(
            confidence_band=AnswerConfidenceBand.ROUTE_TO_SPECIALIST,
            reason=UnknownAnswerReason.NEEDS_SPECIALIST,
            should_answer=False,
            should_route=True,
            should_abstain=False,
            allowed_phrasing=(SAFE_UNKNOWN_LOOKUP_PHRASE,),
            blocked_phrasing=blocked,
            evidence_summary=evidence_summary,
            confidence=confidence,
            notes="route request is dormant; no provider call is allowed here",
        )
    if outside_domain:
        return OutputDisciplineDecision(
            confidence_band=AnswerConfidenceBand.ROUTE_TO_SPECIALIST,
            reason=UnknownAnswerReason.OUTSIDE_DOMAIN,
            should_answer=False,
            should_route=True,
            should_abstain=False,
            allowed_phrasing=(SAFE_UNKNOWN_LOOKUP_PHRASE,),
            blocked_phrasing=blocked,
            evidence_summary=evidence_summary,
            confidence=confidence,
        )
    if conflicting_evidence:
        return OutputDisciplineDecision(
            confidence_band=AnswerConfidenceBand.WEAK_GUESS,
            reason=UnknownAnswerReason.CONFLICTING_EVIDENCE,
            should_answer=True,
            should_route=False,
            should_abstain=False,
            allowed_phrasing=(WEAK_GUESS_PREFIX, LOW_CONFIDENCE_PHRASE),
            blocked_phrasing=blocked,
            evidence_summary=evidence_summary,
            confidence=confidence,
        )
    if evidence_count <= 0:
        return OutputDisciplineDecision(
            confidence_band=AnswerConfidenceBand.INSUFFICIENT_EVIDENCE,
            reason=UnknownAnswerReason.MISSING_EVIDENCE,
            should_answer=False,
            should_route=False,
            should_abstain=True,
            allowed_phrasing=(LOW_CONFIDENCE_PHRASE, SAFE_UNKNOWN_LOOKUP_PHRASE),
            blocked_phrasing=blocked,
            evidence_summary=evidence_summary,
            confidence=confidence,
        )
    if noise_risk >= 0.65:
        return OutputDisciplineDecision(
            confidence_band=AnswerConfidenceBand.WEAK_GUESS,
            reason=UnknownAnswerReason.HIGH_NOISE_RISK,
            should_answer=True,
            should_route=False,
            should_abstain=False,
            allowed_phrasing=(WEAK_GUESS_PREFIX, LOW_CONFIDENCE_PHRASE),
            blocked_phrasing=blocked,
            evidence_summary=evidence_summary,
            confidence=confidence,
            notes="same-topic noise risk blocks overconfident phrasing",
        )
    if confidence >= 0.75 and evidence_count >= 2:
        return OutputDisciplineDecision(
            confidence_band=AnswerConfidenceBand.DIRECT_ANSWER,
            reason=UnknownAnswerReason.UNKNOWN,
            should_answer=True,
            should_route=False,
            should_abstain=False,
            allowed_phrasing=(STRONGEST_ANSWER_PREFIX,),
            blocked_phrasing=(),
            evidence_summary=evidence_summary,
            confidence=confidence,
        )
    if confidence >= 0.45:
        return OutputDisciplineDecision(
            confidence_band=AnswerConfidenceBand.BEST_GUESS,
            reason=UnknownAnswerReason.WEAK_CONTEXT,
            should_answer=True,
            should_route=False,
            should_abstain=False,
            allowed_phrasing=(BEST_GUESS_PREFIX, WEAK_GUESS_PREFIX),
            blocked_phrasing=blocked,
            evidence_summary=evidence_summary,
            confidence=confidence,
        )
    return OutputDisciplineDecision(
        confidence_band=AnswerConfidenceBand.INSUFFICIENT_EVIDENCE,
        reason=UnknownAnswerReason.WEAK_CONTEXT,
        should_answer=False,
        should_route=False,
        should_abstain=True,
        allowed_phrasing=(LOW_CONFIDENCE_PHRASE,),
        blocked_phrasing=blocked,
        evidence_summary=evidence_summary,
        confidence=confidence,
    )


def format_uncertain_answer(decision: OutputDisciplineDecision, answer: str) -> str:
    if decision.should_abstain:
        return format_abstention(decision)
    if decision.confidence_band == AnswerConfidenceBand.ROUTE_TO_SPECIALIST:
        return format_unknown_lookup_notice(decision)
    if decision.confidence_band == AnswerConfidenceBand.BEST_GUESS:
        return format_best_guess_answer(answer, prefix=BEST_GUESS_PREFIX)
    if decision.confidence_band == AnswerConfidenceBand.WEAK_GUESS:
        return format_best_guess_answer(answer, prefix=WEAK_GUESS_PREFIX)
    return block_overconfident_phrasing(f"{STRONGEST_ANSWER_PREFIX} {answer}", decision)


def format_unknown_lookup_notice(decision: OutputDisciplineDecision | None = None) -> str:
    if decision and decision.reason == UnknownAnswerReason.UNSAFE_ACTION_RISK:
        return ACTION_CAUTION_PHRASE
    return SAFE_UNKNOWN_LOOKUP_PHRASE


def format_best_guess_answer(answer: str, *, prefix: str = BEST_GUESS_PREFIX) -> str:
    return f"{prefix} {answer}".strip()


def format_abstention(decision: OutputDisciplineDecision) -> str:
    if decision.reason == UnknownAnswerReason.UNSAFE_ACTION_RISK:
        return ACTION_CAUTION_PHRASE
    return LOW_CONFIDENCE_PHRASE


def block_overconfident_phrasing(text: str, decision: OutputDisciplineDecision) -> str:
    if not decision.blocked_phrasing:
        return text
    cleaned = str(text)
    for pattern in OVERCONFIDENT_PATTERNS:
        cleaned = re.sub(pattern, "likely", cleaned, flags=re.I)
    return cleaned
