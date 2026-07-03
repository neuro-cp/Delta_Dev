from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V16I_REVIEW_LOOP_FLAGS: dict[str, bool] = {
    "memory_candidate_review_loop_enabled": True,
    "canonical_write_performed": False,
    "memory_write_performed": False,
    "source_deleted": False,
    "provider_call_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class MemoryCandidateReviewDecisionValue(str, Enum):
    EDIT_PROPOSED = "edit_proposed"
    REJECTED_FOR_REVIEW = "rejected_for_review"
    DEFERRED = "deferred"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    READY_FOR_EXPLICIT_APPROVAL = "ready_for_explicit_approval"


@dataclass(frozen=True)
class MemoryCandidateReviewRequest:
    request_id: str
    candidate_id: str
    candidate_text: str
    reviewer_note: str = ""

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class MemoryCandidateEditProposal:
    proposal_id: str
    candidate_id: str
    edited_text: str
    applied: bool = False
    canonical_write_ready: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class MemoryCandidateReviewDecision:
    decision_id: str
    candidate_id: str
    decision: MemoryCandidateReviewDecisionValue
    rationale: str
    applied: bool = False
    approved: bool = False
    canonical_write_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["decision"] = self.decision.value
        return data


@dataclass(frozen=True)
class MemoryCandidateReviewAuditRecord:
    audit_id: str
    candidate_id: str
    no_provider_call: bool = True
    no_memory_write: bool = True
    no_recall_mutation: bool = True
    no_training: bool = True
    source_record_preserved: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_memory_candidate_review_request(candidate_id: str, candidate_text: str, reviewer_note: str = "") -> MemoryCandidateReviewRequest:
    return MemoryCandidateReviewRequest(_stable_id("v16i-review-request", candidate_id, candidate_text, reviewer_note), candidate_id, candidate_text, reviewer_note)


def propose_memory_candidate_edit(request: MemoryCandidateReviewRequest, edited_text: str) -> dict[str, object]:
    proposal = MemoryCandidateEditProposal(_stable_id("v16i-edit", request.candidate_id, edited_text), request.candidate_id, edited_text)
    decision = _decision(request.candidate_id, MemoryCandidateReviewDecisionValue.EDIT_PROPOSED, "Edited candidate proposal created for review only.")
    return _payload(request, decision, proposal)


def reject_memory_candidate(request: MemoryCandidateReviewRequest) -> dict[str, object]:
    return _payload(request, _decision(request.candidate_id, MemoryCandidateReviewDecisionValue.REJECTED_FOR_REVIEW, "Candidate rejected as review decision only."), None)


def defer_memory_candidate(request: MemoryCandidateReviewRequest) -> dict[str, object]:
    return _payload(request, _decision(request.candidate_id, MemoryCandidateReviewDecisionValue.DEFERRED, "Candidate deferred as review decision only."), None)


def request_more_evidence_for_memory_candidate(request: MemoryCandidateReviewRequest) -> dict[str, object]:
    return _payload(request, _decision(request.candidate_id, MemoryCandidateReviewDecisionValue.NEEDS_MORE_EVIDENCE, "More evidence requested; no provider call performed."), None)


def mark_memory_candidate_ready_for_explicit_approval(request: MemoryCandidateReviewRequest) -> dict[str, object]:
    return _payload(request, _decision(request.candidate_id, MemoryCandidateReviewDecisionValue.READY_FOR_EXPLICIT_APPROVAL, "Ready for strict explicit approval text; not approved yet."), None)


def validate_memory_candidate_review_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    decision = payload["decision"]
    audit = payload["audit"]
    edit = payload.get("edit_proposal")
    edit_safe = edit is None or (edit["applied"] is False and edit["canonical_write_ready"] is False)
    return (
        edit_safe
        and decision["applied"] is False
        and decision["approved"] is False
        and decision["canonical_write_performed"] is False
        and audit["no_provider_call"] is True
        and audit["no_memory_write"] is True
        and audit["no_recall_mutation"] is True
        and audit["no_training"] is True
        and audit["source_record_preserved"] is True
        and flags["memory_candidate_review_loop_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "memory_candidate_review_loop_enabled")
    )


def _decision(candidate_id: str, value: MemoryCandidateReviewDecisionValue, rationale: str) -> MemoryCandidateReviewDecision:
    return MemoryCandidateReviewDecision(_stable_id("v16i-decision", candidate_id, value.value), candidate_id, value, rationale)


def _payload(request: MemoryCandidateReviewRequest, decision: MemoryCandidateReviewDecision, edit: MemoryCandidateEditProposal | None) -> dict[str, object]:
    audit = MemoryCandidateReviewAuditRecord(_stable_id("v16i-audit", request.candidate_id, decision.decision.value), request.candidate_id)
    return {
        "phase": "Runtime V1.6I",
        "request": request.as_dict(),
        "edit_proposal": edit.as_dict() if edit else None,
        "decision": decision.as_dict(),
        "audit": audit.as_dict(),
        "invariant_flags": dict(RUNTIME_V16I_REVIEW_LOOP_FLAGS),
        "final_recommendation": "PROCEED_CANONICAL_MEMORY_ROLLBACK_TRIAL",
    }


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
