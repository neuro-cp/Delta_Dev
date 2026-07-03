from __future__ import annotations

from orchestration.runtime.v22_evaluator_assisted_memory_candidate_review import EvaluatorCandidateReviewInput, review_memory_candidate_with_evaluator, validate_evaluator_candidate_review_safe


RUNTIME_V24E_FLAGS = {
    "evaluator_consolidation_ux_trial_enabled": True,
    "evaluator_output_authoritative": False,
    "evaluator_can_approve": False,
    "evaluator_can_write": False,
    "evaluator_can_delete": False,
    "memory_write_performed": False,
    "provider_call_performed": False,
    "evaluator_live_call_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


def run_evaluator_consolidation_ux_trial(candidate: dict[str, object], *, live_evaluator: bool = False) -> dict[str, object]:
    review_input = EvaluatorCandidateReviewInput(
        candidate_id=str(candidate.get("candidate_id", "")),
        candidate_text=str(candidate.get("candidate_text") or candidate.get("proposed_memory_text") or ""),
        provenance_reference_ids=tuple(str(item) for item in candidate.get("provenance_reference_ids", ())),
        ambiguity_flag=bool(candidate.get("ambiguity_flag") or candidate.get("ambiguous")),
        sarcasm_flag=bool(candidate.get("sarcasm_flag")),
        malicious_signal_flag=bool(candidate.get("malicious_signal_flag") or candidate.get("misuse_flag")),
    )
    review = review_memory_candidate_with_evaluator(review_input, live_evaluator=live_evaluator)
    return {
        "phase": "Runtime V2.4E",
        "candidate": candidate,
        "evaluator_review": review,
        "ux": {
            "review_displayed_as_advisory": True,
            "user_approval_still_required": True,
            "automatic_consolidation": False,
        },
        "decision": {
            "candidate_written": False,
            "evaluator_approval_accepted": False,
            "memory_write_performed": False,
            "provider_call_performed": False,
            "evaluator_live_call_performed": False,
            "recall_mutated": False,
            "training_triggered": False,
            "action_execution_performed": False,
        },
        "invariant_flags": dict(RUNTIME_V24E_FLAGS),
        "final_recommendation": "PROCEED_V24_SAFETY_CLOSURE",
    }


def validate_evaluator_consolidation_ux_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        validate_evaluator_candidate_review_safe(payload["evaluator_review"])
        and payload["decision"]["evaluator_approval_accepted"] is False
        and payload["decision"]["memory_write_performed"] is False
        and flags["evaluator_consolidation_ux_trial_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "evaluator_consolidation_ux_trial_enabled")
    )

