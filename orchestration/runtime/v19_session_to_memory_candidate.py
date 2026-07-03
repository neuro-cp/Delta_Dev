from __future__ import annotations

import hashlib
from dataclasses import dataclass


RUNTIME_V19D_FLAGS: dict[str, bool] = {
    "session_to_candidate_flow_enabled": True,
    "memory_write_performed": False,
    "canonical_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class SessionMemoryCandidateRequest:
    request_id: str
    session_id: str
    session_summary: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SessionMemorySignal:
    signal_id: str
    kind: str
    value: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SessionMemoryCandidateProposal:
    proposal_id: str
    candidate_text: str
    canonical_write_ready: bool = False
    approved: bool = False
    written: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SessionMemoryCandidateSafetyReview:
    safety_review_id: str
    approval_required: bool
    ambiguity_flagged: bool
    misuse_blocked: bool
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SessionMemoryCandidateDecision:
    decision_id: str
    outcome: str
    write_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SessionMemoryCandidateAuditRecord:
    audit_id: str
    provider_call_performed: bool
    training_triggered: bool
    recall_mutated: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SessionMemoryCandidateReportEntry:
    report_entry_id: str
    outcome: str
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def propose_session_memory_candidate(session_summary: str, *, session_id: str = "default") -> dict[str, object]:
    request = SessionMemoryCandidateRequest(_stable_id("v19d-request", session_id, session_summary), session_id, session_summary)
    signals = tuple(_signals(session_summary))
    misuse = _misuse(session_summary)
    ambiguous = _ambiguous(session_summary)
    candidate = SessionMemoryCandidateProposal(_stable_id("v19d-proposal", session_summary), _candidate_text(session_summary))
    safety = SessionMemoryCandidateSafetyReview(_stable_id("v19d-safety", request.request_id), True, ambiguous, misuse, not misuse)
    decision = SessionMemoryCandidateDecision(_stable_id("v19d-decision", request.request_id), "blocked_for_misuse" if misuse else "review_required")
    audit = SessionMemoryCandidateAuditRecord(_stable_id("v19d-audit", request.request_id), False, False, False)
    return {
        "phase": "Runtime V1.9D",
        "request": request.as_dict(),
        "signals": [signal.as_dict() for signal in signals],
        "proposal": candidate.as_dict(),
        "safety_review": safety.as_dict(),
        "decision": decision.as_dict(),
        "audit_record": audit.as_dict(),
        "report_entry": SessionMemoryCandidateReportEntry(_stable_id("v19d-entry", request.request_id), decision.outcome, safety.safe).as_dict(),
        "invariant_flags": dict(RUNTIME_V19D_FLAGS),
        "final_recommendation": "PROCEED_V19_SAFETY_CHECKPOINT_REPORT",
    }


def validate_session_memory_candidate_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["proposal"]["canonical_write_ready"] is False
        and payload["proposal"]["approved"] is False
        and payload["proposal"]["written"] is False
        and payload["safety_review"]["approval_required"] is True
        and payload["decision"]["write_performed"] is False
        and flags["session_to_candidate_flow_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "session_to_candidate_flow_enabled")
    )


def _signals(summary: str) -> list[SessionMemorySignal]:
    text = summary.lower()
    signals = [SessionMemorySignal(_stable_id("v19d-signal", "summary"), "session_summary", summary)]
    if "maybe" in text or "not sure" in text or "ambiguous" in text:
        signals.append(SessionMemorySignal(_stable_id("v19d-signal", "ambiguous"), "ambiguity", "review_required"))
    if "ignore approval" in text or "bypass" in text:
        signals.append(SessionMemorySignal(_stable_id("v19d-signal", "misuse"), "misuse", "blocked"))
    return signals


def _candidate_text(summary: str) -> str:
    return "Session-derived candidate: " + " ".join(summary.split())[:240]


def _ambiguous(summary: str) -> bool:
    text = summary.lower()
    return "maybe" in text or "not sure" in text or "ambiguous" in text


def _misuse(summary: str) -> bool:
    text = summary.lower()
    return "ignore approval" in text or "bypass" in text


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
