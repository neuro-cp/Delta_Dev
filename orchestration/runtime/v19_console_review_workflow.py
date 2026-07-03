from __future__ import annotations

import hashlib
from dataclasses import dataclass


RUNTIME_V19C_FLAGS: dict[str, bool] = {
    "console_review_workflow_enabled": True,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


APPROVE_TEMPLATE = "APPROVE_CANONICAL_MEMORY_WRITE\ncandidate_id={candidate_id}\napproved_by=user\napproval_scope=single_memory_candidate_only"
REJECT_TEMPLATE = "REJECT_MEMORY_CANDIDATE\ncandidate_id={candidate_id}\nrejected_by=user\nrejection_scope=single_memory_candidate_only"
DEFER_TEMPLATE = "DEFER_MEMORY_CANDIDATE\ncandidate_id={candidate_id}\ndeferred_by=user\ndefer_scope=single_memory_candidate_only"


@dataclass(frozen=True)
class ConsoleReviewWorkflowResult:
    result_id: str
    candidate_id: str
    action: str
    export_text: str
    writes_memory: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def export_console_review_action(action: str, candidate_id: str) -> dict[str, object]:
    if action == "approve":
        text = APPROVE_TEMPLATE.format(candidate_id=candidate_id)
    elif action == "reject":
        text = REJECT_TEMPLATE.format(candidate_id=candidate_id)
    elif action == "defer":
        text = DEFER_TEMPLATE.format(candidate_id=candidate_id)
    else:
        text = f"UNSUPPORTED_REVIEW_ACTION\ncandidate_id={candidate_id}\naction={action}"
    result = ConsoleReviewWorkflowResult(_stable_id("v19c-result", action, candidate_id), candidate_id, action, text)
    return {"phase": "Runtime V1.9C", "result": result.as_dict(), "invariant_flags": dict(RUNTIME_V19C_FLAGS), "final_recommendation": "PROCEED_SESSION_TO_CANDIDATE_MEMORY_PROPOSAL_FLOW"}


def review_candidate(candidate_id: str) -> dict[str, object]:
    return {"phase": "Runtime V1.9C", "candidate_id": candidate_id, "review_required": True, "canonical_write_ready": False, "invariant_flags": dict(RUNTIME_V19C_FLAGS), "final_recommendation": "PROCEED_SESSION_TO_CANDIDATE_MEMORY_PROPOSAL_FLOW"}


def validate_console_review_workflow_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    result = payload.get("result", {})
    return (
        result.get("writes_memory", False) is False
        and flags["console_review_workflow_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "console_review_workflow_enabled")
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
