from __future__ import annotations

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v21_provider_live_trial_user_approved import run_user_approved_provider_live_trial


APPROVAL_TEXT = "APPROVE_PROVIDER_LIVE_TRIAL\napproved_by=user\ntrial_scope=single_unknown_question_only\napproval_source=localhost_full_review_console"
_BASE_APPROVAL = "APPROVE_PROVIDER_LIVE_TRIAL\napproved_by=user\ntrial_scope=single_unknown_question_only"

RUNTIME_V24D_FLAGS = {
    "provider_unknown_answer_ux_trial_enabled": True,
    "dry_run_default": True,
    "provider_output_authoritative": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


def parse_provider_unknown_ux_approval(text: str) -> dict[str, object]:
    normalized = _normalize(text)
    return {"approval_present": bool(normalized), "matches_required_shape": normalized == _normalize(APPROVAL_TEXT)}


def run_provider_unknown_answer_ux_trial(question: str, *, approval_text: str = "", live_provider: bool = False, env: dict[str, str] | None = None, transport=None) -> dict[str, object]:
    local = route_local_knowledge_answer(question)
    approval = parse_provider_unknown_ux_approval(approval_text)
    effective_approval = _BASE_APPROVAL if approval["matches_required_shape"] else ""
    provider = None
    if local.matched:
        blocks = ["known_local_question"]
    else:
        provider = run_user_approved_provider_live_trial(question, approval_text=effective_approval, live_provider=live_provider, env=env or {}, transport=transport)
        blocks = provider["gate"]["blocks"]
    return {
        "phase": "Runtime V2.4D",
        "local_answer": local.as_dict(),
        "approval": approval,
        "provider_trial": provider,
        "blocks": blocks,
        "redaction": {"api_key_redacted": True, "api_key_rendered": False},
        "decision": {
            "provider_call_performed": bool(provider and provider["decision"]["provider_call_performed"]),
            "provider_answer_authoritative": False,
            "memory_write_performed": False,
            "recall_mutated": False,
            "training_triggered": False,
            "action_execution_performed": False,
        },
        "invariant_flags": dict(RUNTIME_V24D_FLAGS),
        "final_recommendation": "PROCEED_EVALUATOR_REVIEWED_CONSOLIDATION_UX_TRIAL",
    }


def validate_provider_unknown_answer_ux_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["decision"]["provider_answer_authoritative"] is False
        and payload["decision"]["memory_write_performed"] is False
        and payload["redaction"]["api_key_rendered"] is False
        and flags["provider_unknown_answer_ux_trial_enabled"] is True
        and flags["dry_run_default"] is True
        and flags["provider_output_authoritative"] is False
        and all(value is False for key, value in flags.items() if key not in {"provider_unknown_answer_ux_trial_enabled", "dry_run_default", "provider_output_authoritative"})
    )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())

