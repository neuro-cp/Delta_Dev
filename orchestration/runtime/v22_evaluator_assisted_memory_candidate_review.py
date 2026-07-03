from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V22D_FLAGS = {
    "evaluator_candidate_review_enabled": True,
    "dry_run_default": True,
    "evaluator_output_authoritative": False,
    "evaluator_can_approve": False,
    "evaluator_can_write": False,
    "evaluator_can_delete": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "provider_call_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


class EvaluatorRecommendation(str, Enum):
    PROMOTE_TO_HUMAN_REVIEW = "promote_to_human_review"
    DEFER = "defer"
    REJECT_RECOMMENDED = "reject_recommended"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    AMBIGUITY_REVIEW_REQUIRED = "ambiguity_review_required"
    SARCASM_REVIEW_REQUIRED = "sarcasm_review_required"
    MALICIOUS_SIGNAL_REVIEW_REQUIRED = "malicious_signal_review_required"


@dataclass(frozen=True)
class EvaluatorCandidateReviewInput:
    candidate_id: str
    candidate_text: str
    provenance_reference_ids: tuple[str, ...]
    ambiguity_flag: bool = False
    sarcasm_flag: bool = False
    malicious_signal_flag: bool = False

    def as_dict(self) -> dict[str, object]:
        return {**self.__dict__, "provenance_reference_ids": list(self.provenance_reference_ids)}


def review_memory_candidate_with_evaluator(candidate: EvaluatorCandidateReviewInput, *, live_evaluator: bool = False) -> dict[str, object]:
    risks: list[str] = []
    if not candidate.provenance_reference_ids:
        risks.append("missing_provenance")
    if candidate.ambiguity_flag:
        risks.append("ambiguity")
    if candidate.sarcasm_flag:
        risks.append("sarcasm")
    if candidate.malicious_signal_flag:
        risks.append("malicious_signal")
    if live_evaluator:
        risks.append("live_evaluator_refused_by_default")
    recommendation = _recommendation_for_risks(risks)
    return {
        "phase": "Runtime V2.2D",
        "input": candidate.as_dict(),
        "risk_assessment": {
            "risk_assessment_id": _stable_id("v22d-risk", candidate.candidate_id, risks),
            "risks": risks,
            "advisory_only": True,
        },
        "recommendation": {
            "recommendation_id": _stable_id("v22d-recommendation", candidate.candidate_id, recommendation.value),
            "value": recommendation.value,
            "is_approval": False,
            "is_deletion": False,
            "advisory_only": True,
        },
        "decision": {
            "canonical_write_performed": False,
            "memory_deleted": False,
            "recall_mutated": False,
            "training_triggered": False,
        },
        "invariant_flags": dict(RUNTIME_V22D_FLAGS),
        "final_recommendation": "PROCEED_HYB1_OPT_IN_SHADOW_TRIAL_DESIGN",
    }


def validate_evaluator_candidate_review_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    recommendation = payload["recommendation"]
    return (
        recommendation["is_approval"] is False
        and recommendation["is_deletion"] is False
        and recommendation["advisory_only"] is True
        and flags["evaluator_candidate_review_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"evaluator_candidate_review_enabled", "dry_run_default"})
    )


def _recommendation_for_risks(risks: list[str]) -> EvaluatorRecommendation:
    if "malicious_signal" in risks:
        return EvaluatorRecommendation.MALICIOUS_SIGNAL_REVIEW_REQUIRED
    if "sarcasm" in risks:
        return EvaluatorRecommendation.SARCASM_REVIEW_REQUIRED
    if "ambiguity" in risks:
        return EvaluatorRecommendation.AMBIGUITY_REVIEW_REQUIRED
    if "missing_provenance" in risks:
        return EvaluatorRecommendation.NEEDS_MORE_EVIDENCE
    if "live_evaluator_refused_by_default" in risks:
        return EvaluatorRecommendation.DEFER
    return EvaluatorRecommendation.PROMOTE_TO_HUMAN_REVIEW


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
