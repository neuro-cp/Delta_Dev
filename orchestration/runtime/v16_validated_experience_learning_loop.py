from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from orchestration.runtime.v15_feedback_memory_candidate import build_feedback_memory_candidate_case
from orchestration.runtime.v15_first_interaction import build_first_interaction_result, validate_first_interaction_result_safe


RUNTIME_V16A_VALIDATED_EXPERIENCE_FLAGS: dict[str, bool] = {
    "validated_experience_loop_scaffold_enabled": True,
    "report_only": True,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "dataset_export_enabled": False,
    "provider_calls_enabled": False,
    "tool_calls_enabled": False,
    "action_execution_enabled": False,
    "memory_write_enabled": False,
    "canonical_write_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "general_recall_enabled": False,
    "autonomous_approval_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "scheduler_enabled": False,
    "background_listener_enabled": False,
    "runtime_defaults_changed": False,
}


class ValidatedExperienceStatus(str, Enum):
    VALID_FOR_REVIEW = "valid_for_review"
    BLOCKED_UNSAFE_REQUEST = "blocked_unsafe_request"
    INSUFFICIENT_SIGNAL = "insufficient_signal"


@dataclass(frozen=True)
class ValidatedExperienceLearningLoopResult:
    loop_id: str
    user_message: str
    feedback_text: str
    status: ValidatedExperienceStatus
    validation_summary: str
    memory_candidate_id: str = ""
    replay_review_marker_created: bool = False
    consolidation_candidate_created: bool = False
    canonical_write_performed: bool = False
    memory_write_performed: bool = False
    recall_mutated: bool = False
    training_triggered: bool = False
    provider_calls_performed: bool = False
    action_execution_performed: bool = False
    dataset_exported: bool = False
    candidate_only: bool = True
    applied: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def run_validated_experience_learning_loop(
    user_message: str,
    answer_text: str,
    feedback_text: str,
) -> dict[str, object]:
    if _contains_unsafe_request(user_message) or _contains_unsafe_request(feedback_text):
        result = ValidatedExperienceLearningLoopResult(
            loop_id=_stable_id("v16a-loop", user_message, feedback_text, "blocked"),
            user_message=user_message,
            feedback_text=feedback_text,
            status=ValidatedExperienceStatus.BLOCKED_UNSAFE_REQUEST,
            validation_summary="Unsafe activation request blocked; no learning path ran.",
            candidate_only=False,
        )
        return _payload(None, result)

    interaction = build_first_interaction_result(user_message)
    if not validate_first_interaction_result_safe(interaction):
        result = ValidatedExperienceLearningLoopResult(
            loop_id=_stable_id("v16a-loop", user_message, feedback_text, "insufficient"),
            user_message=user_message,
            feedback_text=feedback_text,
            status=ValidatedExperienceStatus.INSUFFICIENT_SIGNAL,
            validation_summary="Experience was not safe enough for review.",
        )
        return _payload(None, result)

    feedback_case = build_feedback_memory_candidate_case(user_message, answer_text, feedback_text)
    candidate = dict(feedback_case["memory_candidate"])
    result = ValidatedExperienceLearningLoopResult(
        loop_id=_stable_id("v16a-loop", interaction["result"]["result_id"], candidate["memory_candidate_id"]),
        user_message=user_message,
        feedback_text=feedback_text,
        status=ValidatedExperienceStatus.VALID_FOR_REVIEW,
        validation_summary="Experience and feedback produced an inert candidate for later review only.",
        memory_candidate_id=str(candidate["memory_candidate_id"]),
        replay_review_marker_created=True,
        consolidation_candidate_created=True,
    )
    return _payload(candidate, result)


def validate_validated_experience_loop_safe(payload: dict[str, object]) -> bool:
    result = payload["result"]
    flags = payload["invariant_flags"]
    candidate = payload.get("memory_candidate")
    candidate_safe = candidate is None or (
        candidate.get("human_approval_required") is True
        and candidate.get("canonical_write_ready") is False
        and candidate.get("approved") is False
        and candidate.get("written") is False
    )
    return (
        candidate_safe
        and result["canonical_write_performed"] is False
        and result["memory_write_performed"] is False
        and result["recall_mutated"] is False
        and result["training_triggered"] is False
        and result["provider_calls_performed"] is False
        and result["action_execution_performed"] is False
        and result["dataset_exported"] is False
        and result["applied"] is False
        and flags["validated_experience_loop_scaffold_enabled"] is True
        and flags["report_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"validated_experience_loop_scaffold_enabled", "report_only"})
    )


def _payload(memory_candidate: dict[str, object] | None, result: ValidatedExperienceLearningLoopResult) -> dict[str, object]:
    return {
        "phase": "Runtime V1.6A",
        "title": "Validated Experience Learning Loop",
        "memory_candidate": memory_candidate,
        "result": result.as_dict(),
        "invariant_flags": dict(RUNTIME_V16A_VALIDATED_EXPERIENCE_FLAGS),
    }


def _contains_unsafe_request(text: str) -> bool:
    normalized = " ".join(str(text).lower().split())
    unsafe_terms = (
        "train yourself",
        "fine tune",
        "fine-tune",
        "update weights",
        "write canonical",
        "promote memory",
        "activate recall",
        "call provider",
        "execute action",
        "export dataset",
    )
    return any(term in normalized for term in unsafe_terms)


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
