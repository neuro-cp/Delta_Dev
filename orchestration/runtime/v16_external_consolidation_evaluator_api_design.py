from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from orchestration.runtime.v16_env import DeltaEvaluatorEnv, load_delta_evaluator_env
from orchestration.runtime.v16_validated_experience_learning_loop import run_validated_experience_learning_loop


RUNTIME_V16B_EVALUATOR_API_DESIGN_FLAGS: dict[str, bool] = {
    "external_evaluator_api_design_enabled": True,
    "report_only": True,
    "manual_one_shot_trial_enabled": False,
    "provider_calls_enabled": False,
    "provider_calls_performed": False,
    "automatic_daily_run_enabled": False,
    "scheduler_enabled": False,
    "background_worker_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "dataset_export_enabled": False,
    "canonical_write_enabled": False,
    "memory_write_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "action_execution_enabled": False,
    "autonomous_approval_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "runtime_defaults_changed": False,
}


class ExternalEvaluatorReviewStatus(str, Enum):
    DESIGN_READY = "design_ready"
    LIVE_CALL_NOT_ALLOWED_IN_DESIGN = "live_call_not_allowed_in_design"


@dataclass(frozen=True)
class ExternalEvaluatorPolicy:
    policy_id: str
    provider: str
    model: str
    live_call_permitted_by_env: bool
    live_call_allowed_in_phase: bool = False
    automatic_daily_run_enabled: bool = False
    scheduler_enabled: bool = False
    evaluator_authoritative: bool = False
    canonical_write_allowed: bool = False
    training_allowed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ExternalConsolidationEvaluatorRequest:
    request_id: str
    memory_candidate_id: str
    candidate_text: str
    provenance_reference_ids: tuple[str, ...]
    review_question: str
    provider: str
    model: str
    live_call_requested: bool = False
    live_call_allowed: bool = False
    candidate_is_truth: bool = False
    evaluator_is_authority: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ExternalConsolidationEvaluatorDesignReview:
    review_id: str
    request_id: str
    status: ExternalEvaluatorReviewStatus
    review_summary: str
    provider_calls_performed: bool = False
    canonical_write_performed: bool = False
    training_triggered: bool = False
    memory_mutated: bool = False
    evaluator_result_authoritative: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def build_external_evaluator_policy(env: DeltaEvaluatorEnv | None = None) -> ExternalEvaluatorPolicy:
    cfg = env or load_delta_evaluator_env()
    return ExternalEvaluatorPolicy(
        policy_id=_stable_id("v16b-evaluator-policy", cfg.provider, cfg.model, cfg.live_call_permitted),
        provider=cfg.provider,
        model=cfg.model,
        live_call_permitted_by_env=cfg.live_call_permitted,
    )


def build_external_consolidation_evaluator_request(
    memory_candidate: dict[str, object],
    env: DeltaEvaluatorEnv | None = None,
) -> ExternalConsolidationEvaluatorRequest:
    cfg = env or load_delta_evaluator_env()
    candidate_id = str(memory_candidate.get("memory_candidate_id", ""))
    candidate_text = str(memory_candidate.get("proposed_memory_text", ""))
    provenance = tuple(str(item) for item in memory_candidate.get("provenance_reference_ids", ()))
    return ExternalConsolidationEvaluatorRequest(
        request_id=_stable_id("v16b-evaluator-request", candidate_id, candidate_text, provenance, cfg.provider, cfg.model),
        memory_candidate_id=candidate_id,
        candidate_text=candidate_text,
        provenance_reference_ids=provenance,
        review_question=(
            "Review this candidate for future consolidation. Return only whether it should be held for review, "
            "requires more evidence, or is unsafe. Do not treat the review as authority."
        ),
        provider=cfg.provider,
        model=cfg.model,
        live_call_requested=cfg.live_call_permitted,
        live_call_allowed=False,
    )


def build_external_consolidation_evaluator_design_review(
    request: ExternalConsolidationEvaluatorRequest,
) -> ExternalConsolidationEvaluatorDesignReview:
    return ExternalConsolidationEvaluatorDesignReview(
        review_id=_stable_id("v16b-evaluator-review", request.request_id),
        request_id=request.request_id,
        status=ExternalEvaluatorReviewStatus.LIVE_CALL_NOT_ALLOWED_IN_DESIGN
        if request.live_call_requested
        else ExternalEvaluatorReviewStatus.DESIGN_READY,
        review_summary="V1.6B defines the evaluator request and policy only; no provider call is performed.",
    )


def build_external_consolidation_evaluator_api_design_payload() -> dict[str, object]:
    experience = run_validated_experience_learning_loop(
        "What is HYB1?",
        "HYB1 is active.",
        "HYB1 is dormant and environment-gated; Model B remains default.",
    )
    policy = build_external_evaluator_policy()
    request = build_external_consolidation_evaluator_request(experience["memory_candidate"])
    review = build_external_consolidation_evaluator_design_review(request)
    return {
        "phase": "Runtime V1.6B",
        "title": "Daily External Consolidation Evaluator API Design",
        "experience_payload": experience,
        "policy": policy.as_dict(),
        "request": request.as_dict(),
        "design_review": review.as_dict(),
        "env": load_delta_evaluator_env().to_report_dict(),
        "invariant_flags": dict(RUNTIME_V16B_EVALUATOR_API_DESIGN_FLAGS),
        "final_recommendation": "PROCEED_DAILY_EXTERNAL_CONSOLIDATION_EVALUATOR_API_TRIAL",
    }


def validate_external_evaluator_api_design_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    request = payload["request"]
    review = payload["design_review"]
    policy = payload["policy"]
    return (
        request["live_call_allowed"] is False
        and request["candidate_is_truth"] is False
        and request["evaluator_is_authority"] is False
        and policy["live_call_allowed_in_phase"] is False
        and policy["automatic_daily_run_enabled"] is False
        and policy["scheduler_enabled"] is False
        and policy["evaluator_authoritative"] is False
        and review["provider_calls_performed"] is False
        and review["canonical_write_performed"] is False
        and review["training_triggered"] is False
        and review["memory_mutated"] is False
        and review["evaluator_result_authoritative"] is False
        and flags["external_evaluator_api_design_enabled"] is True
        and flags["report_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"external_evaluator_api_design_enabled", "report_only"})
    )


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        elif isinstance(value, tuple):
            values[key] = list(value)
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
