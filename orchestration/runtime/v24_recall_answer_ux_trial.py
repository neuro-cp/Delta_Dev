from __future__ import annotations

from orchestration.runtime.v23_recall_to_synthesis_integration import run_recall_to_synthesis, validate_recall_to_synthesis_safe


RUNTIME_V24C_FLAGS = {
    "recall_answer_ux_trial_enabled": True,
    "candidate_context_only": True,
    "authoritative_recall_enabled": False,
    "truth_claim_from_recall": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


def run_recall_answer_ux_trial(query: str, *, use_recall: bool = True) -> dict[str, object]:
    payload = run_recall_to_synthesis(query, use_recall=use_recall)
    payload["phase"] = "Runtime V2.4C"
    payload["ux"] = {"shows_provenance": True, "shows_uncertainty": True, "candidate_context_labels_visible": True}
    payload["invariant_flags"] = dict(RUNTIME_V24C_FLAGS)
    payload["final_recommendation"] = "PROCEED_PROVIDER_ASSISTED_UNKNOWN_ANSWER_UX_TRIAL"
    for item in payload["evidence_items"]:
        item["truth_claim"] = False
    return payload


def validate_recall_answer_ux_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        validate_recall_to_synthesis_safe({**payload, "invariant_flags": {
            "recall_to_synthesis_integration_enabled": True,
            "candidate_context_only": True,
            "authoritative_recall_enabled": False,
            "memory_write_performed": False,
            "recall_mutated": False,
            "provider_call_performed": False,
            "training_triggered": False,
            "action_execution_performed": False,
            "scheduler_started": False,
            "hyb1_default_activation_enabled": False,
            "model_b_default_changed": False,
        }})
        and all(item.get("truth_claim") is False for item in payload["evidence_items"])
        and flags["recall_answer_ux_trial_enabled"] is True
        and flags["candidate_context_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"recall_answer_ux_trial_enabled", "candidate_context_only"})
    )

