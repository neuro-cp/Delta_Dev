from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class SpecialistDomain(str, Enum):
    GENERAL = "general"
    CODE = "code"
    MATH = "math"
    LAW = "law"
    MEDICAL = "medical"
    FINANCE = "finance"
    SCIENCE = "science"
    PLANNING = "planning"
    MEMORY = "memory"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SpecialistRoute:
    domain: SpecialistDomain
    route_reason: str
    question_for_specialist: str
    confidence: float = 0.0
    provider_hint: str = ""
    requires_external_call: bool = False
    allowed_to_call_now: bool = False

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain.value,
            "route_reason": self.route_reason,
            "question_for_specialist": self.question_for_specialist,
            "confidence": self.normalized_confidence(),
            "provider_hint": self.provider_hint,
            "requires_external_call": self.requires_external_call,
            "allowed_to_call_now": self.allowed_to_call_now,
        }


@dataclass(frozen=True)
class SpecialistResponseDraft:
    domain: SpecialistDomain
    answer: str
    confidence: float = 0.0
    caveats: tuple[str, ...] = field(default_factory=tuple)
    source: str = "mock_or_report_only"
    used_external_call: bool = False

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain.value,
            "answer": self.answer,
            "confidence": self.normalized_confidence(),
            "caveats": list(self.caveats),
            "source": self.source,
            "used_external_call": self.used_external_call,
        }


DOMAIN_PATTERNS: tuple[tuple[SpecialistDomain, tuple[str, ...]], ...] = (
    (SpecialistDomain.CODE, ("python", "javascript", "code", "bug", "function", "compile", "stack trace")),
    (SpecialistDomain.MATH, ("calculate", "equation", "proof", "derivative", "integral", "probability")),
    (SpecialistDomain.LAW, ("law", "legal", "contract", "statute", "liability", "court")),
    (SpecialistDomain.MEDICAL, ("medical", "doctor", "symptom", "diagnosis", "medicine", "treatment")),
    (SpecialistDomain.FINANCE, ("finance", "stock", "portfolio", "tax", "loan", "investment")),
    (SpecialistDomain.SCIENCE, ("experiment", "hypothesis", "physics", "chemistry", "biology", "scientific")),
    (SpecialistDomain.PLANNING, ("plan", "schedule", "allocate", "strategy", "timeline", "resources")),
    (SpecialistDomain.MEMORY, ("remember", "recall", "memory", "previous", "stored", "concept")),
)


def classify_question_domain(question: str) -> SpecialistDomain:
    lowered = str(question).lower()
    for domain, terms in DOMAIN_PATTERNS:
        if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in terms):
            return domain
    return SpecialistDomain.GENERAL if lowered.strip() else SpecialistDomain.UNKNOWN


def build_specialist_question(question: str, *, domain: SpecialistDomain | None = None) -> str:
    resolved = domain or classify_question_domain(question)
    return (
        f"Domain: {resolved.value}\n"
        f"Question: {str(question).strip()}\n"
        "Return a bounded, evidence-aware answer with caveats. Do not assume authority."
    )


def select_specialist_route(
    question: str,
    *,
    route_reason: str = "output discipline requested dormant specialist route",
    confidence: float = 0.5,
    provider_hint: str = "",
    allow_call: bool = False,
) -> SpecialistRoute:
    domain = classify_question_domain(question)
    return SpecialistRoute(
        domain=domain,
        route_reason=route_reason,
        question_for_specialist=build_specialist_question(question, domain=domain),
        confidence=confidence,
        provider_hint=provider_hint,
        requires_external_call=domain not in {SpecialistDomain.GENERAL, SpecialistDomain.UNKNOWN},
        allowed_to_call_now=bool(allow_call),
    )


def should_route_to_specialist(route: SpecialistRoute, *, min_confidence: float = 0.35) -> bool:
    return route.domain not in {SpecialistDomain.GENERAL, SpecialistDomain.UNKNOWN} and route.normalized_confidence() >= min_confidence


def merge_specialist_response(
    *,
    route: SpecialistRoute,
    response: SpecialistResponseDraft,
    base_answer: str = "",
) -> str:
    confidence = min(route.normalized_confidence(), response.normalized_confidence())
    prefix = "Specialist draft suggests" if confidence >= 0.6 else "A low-confidence specialist draft suggests"
    caveats = " ".join(response.caveats)
    base = f" Existing answer context: {base_answer}" if base_answer else ""
    caveat_text = f" Caveats: {caveats}" if caveats else ""
    return f"{prefix}: {response.answer}{caveat_text}{base}".strip()
