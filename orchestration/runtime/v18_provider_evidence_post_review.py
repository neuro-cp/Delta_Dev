from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from orchestration.runtime.v18_manual_provider_live_trial import run_provider_live_trial


RUNTIME_V18G_FLAGS: dict[str, bool] = {
    "provider_evidence_post_review_enabled": True,
    "evaluator_call_performed": False,
    "provider_evidence_authoritative": False,
    "evaluator_review_authoritative": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class ProviderEvidenceRiskFlag(str, Enum):
    POOR_PROVENANCE = "poor_provenance"
    CONFLICT_REQUIRES_UNCERTAINTY = "conflict_requires_uncertainty"
    PROVIDER_EVIDENCE_ONLY = "provider_evidence_only"


@dataclass(frozen=True)
class ProviderEvidencePostReviewRequest:
    request_id: str
    question: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderEvidenceCrossCheckInput:
    input_id: str
    provider_decision: str
    provider_text: str
    provenance: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderEvidenceCrossCheckReview:
    review_id: str
    disposition: str
    advisory_only: bool
    rationale: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderEvidenceReviewDecision:
    decision_id: str
    outcome: str
    provider_authority: bool = False
    evaluator_authority: bool = False
    memory_write_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderEvidencePostReviewAuditRecord:
    audit_id: str
    risk_flags: tuple[ProviderEvidenceRiskFlag, ...]
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return {"audit_id": self.audit_id, "risk_flags": [flag.value for flag in self.risk_flags], "safe": self.safe}


@dataclass(frozen=True)
class ProviderEvidencePostReviewReportEntry:
    report_entry_id: str
    outcome: str
    risk_count: int
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def review_provider_evidence(question: str, *, provider_payload: dict[str, object] | None = None) -> dict[str, object]:
    payload = provider_payload or run_provider_live_trial(question)
    trace = payload["trace"]
    packet = trace.get("evidence_packet")
    text = packet["provider_text"] if packet else f"Provider trial decision: {trace['decision']['decision']}"
    cross_input = ProviderEvidenceCrossCheckInput(_stable_id("v18g-input", question), trace["decision"]["decision"], text, packet.get("provenance", "dry-run provider trial") if packet else "dry-run provider trial")
    risks = _risk_flags(question, cross_input)
    review = ProviderEvidenceCrossCheckReview(_stable_id("v18g-review", question), "advisory_review_complete", True, "Local cross-check only; provider evidence remains non-authoritative.")
    decision = ProviderEvidenceReviewDecision(_stable_id("v18g-decision", question), "hold_as_evidence_only")
    audit = ProviderEvidencePostReviewAuditRecord(_stable_id("v18g-audit", question), tuple(risks), True)
    return {
        "phase": "Runtime V1.8G",
        "request": ProviderEvidencePostReviewRequest(_stable_id("v18g-request", question), question).as_dict(),
        "cross_check_input": cross_input.as_dict(),
        "cross_check_review": review.as_dict(),
        "decision": decision.as_dict(),
        "audit_record": audit.as_dict(),
        "report_entry": ProviderEvidencePostReviewReportEntry(_stable_id("v18g-entry", question), decision.outcome, len(risks), audit.safe).as_dict(),
        "invariant_flags": dict(RUNTIME_V18G_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_MEMORY_RECALL_EXPANSION_DESIGN",
    }


def validate_provider_evidence_post_review_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["cross_check_review"]["advisory_only"] is True
        and payload["decision"]["provider_authority"] is False
        and payload["decision"]["evaluator_authority"] is False
        and payload["decision"]["memory_write_performed"] is False
        and flags["provider_evidence_post_review_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "provider_evidence_post_review_enabled")
    )


def _risk_flags(question: str, cross_input: ProviderEvidenceCrossCheckInput) -> list[ProviderEvidenceRiskFlag]:
    flags = [ProviderEvidenceRiskFlag.PROVIDER_EVIDENCE_ONLY]
    if not cross_input.provenance:
        flags.append(ProviderEvidenceRiskFlag.POOR_PROVENANCE)
    if "truth" in question.lower() or "conflict" in question.lower():
        flags.append(ProviderEvidenceRiskFlag.CONFLICT_REQUIRES_UNCERTAINTY)
    return flags


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
