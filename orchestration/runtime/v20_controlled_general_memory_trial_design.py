from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V20B_FLAGS: dict[str, bool] = {
    "controlled_general_memory_trial_design_enabled": True,
    "memory_write_performed": False,
    "general_recall_activated": False,
    "provider_direct_write_allowed": False,
    "evaluator_direct_write_allowed": False,
    "training_triggered": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


class MemoryCandidateState(str, Enum):
    APPROVED = "approved"
    UNAPPROVED = "unapproved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class ControlledGeneralMemoryScope:
    scope_id: str
    one_record_per_approval: bool = True
    bulk_approval_allowed: bool = False
    authoritative_recall_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ControlledGeneralMemorySourcePolicy:
    policy_id: str
    provider_direct_write_allowed: bool = False
    evaluator_direct_write_allowed: bool = False
    session_summary_must_be_candidate_first: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ControlledGeneralMemoryWriteRequest:
    request_id: str
    candidate_id: str
    candidate_state: MemoryCandidateState
    approval_text: str = ""
    source_kind: str = "memory_candidate"

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["candidate_state"] = self.candidate_state.value
        return data


@dataclass(frozen=True)
class ControlledGeneralMemoryTrialDecision:
    decision_id: str
    candidate_id: str
    eligible_for_future_trial: bool
    reason: str
    writes_memory_now: bool = False
    activates_general_recall: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def design_controlled_general_memory_trial(candidate_id: str, state: MemoryCandidateState, *, source_kind: str = "memory_candidate") -> dict[str, object]:
    request = ControlledGeneralMemoryWriteRequest(_stable_id("v20b-request", candidate_id, state.value, source_kind), candidate_id, state, source_kind=source_kind)
    scope = ControlledGeneralMemoryScope(_stable_id("v20b-scope", "single-approval"))
    policy = ControlledGeneralMemorySourcePolicy(_stable_id("v20b-source-policy", source_kind))
    eligible = state is MemoryCandidateState.APPROVED and source_kind == "memory_candidate"
    reason = "approved memory candidates only" if eligible else "excluded until explicit approved memory candidate exists"
    decision = ControlledGeneralMemoryTrialDecision(_stable_id("v20b-decision", request.request_id, eligible), candidate_id, eligible, reason)
    return {
        "phase": "Runtime V2.0B",
        "request": request.as_dict(),
        "scope": scope.as_dict(),
        "source_policy": policy.as_dict(),
        "decision": decision.as_dict(),
        "invariant_flags": dict(RUNTIME_V20B_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_MEMORY_TRIAL_EXPLICIT_APPROVAL_ONLY",
    }


def validate_controlled_general_memory_design_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    decision = payload["decision"]
    return (
        decision["writes_memory_now"] is False
        and decision["activates_general_recall"] is False
        and flags["controlled_general_memory_trial_design_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "controlled_general_memory_trial_design_enabled")
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
