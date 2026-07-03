from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v16_env import parse_env_file
from orchestration.runtime.v18_manual_provider_live_trial import run_provider_live_trial


APPROVAL_TEXT = "APPROVE_PROVIDER_LIVE_TRIAL\napproved_by=user\ntrial_scope=single_unknown_question_only"

RUNTIME_V21C_FLAGS = {
    "user_approved_provider_live_trial_enabled": True,
    "dry_run_default": True,
    "provider_response_authoritative": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}

Transport = Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]]


@dataclass(frozen=True)
class UserApprovedProviderTrialRequest:
    request_id: str
    question: str
    live_provider: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def parse_provider_trial_approval(text: str) -> dict[str, object]:
    lines = _normalize(text).split("\n") if _normalize(text) else []
    parsed: dict[str, object] = {"header": lines[0] if lines else "", "line_count": len(lines)}
    for line in lines[1:]:
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
    parsed["matches_required_shape"] = (
        parsed.get("header") == "APPROVE_PROVIDER_LIVE_TRIAL"
        and parsed.get("approved_by") == "user"
        and parsed.get("trial_scope") == "single_unknown_question_only"
        and parsed.get("line_count") == 3
    )
    return parsed


def run_user_approved_provider_live_trial(
    question: str,
    *,
    approval_text: str = "",
    live_provider: bool = False,
    env: dict[str, str] | None = None,
    transport: Transport | None = None,
) -> dict[str, object]:
    env_values = parse_env_file() if env is None else env
    approval = parse_provider_trial_approval(approval_text)
    local = route_local_knowledge_answer(question)
    request = UserApprovedProviderTrialRequest(_stable_id("v21c-request", question, live_provider), question, live_provider)
    blocks: list[str] = []
    if local.matched:
        blocks.append("known_local_question")
    if live_provider and not approval["matches_required_shape"]:
        blocks.append("exact_user_approval_required")
    if live_provider and not _env_gates_open(env_values):
        blocks.append("env_gates_required")
    if live_provider and not _api_key_present(env_values):
        blocks.append("api_key_required")
    if not live_provider:
        blocks.append("dry_run_no_live_provider")
    if blocks:
        return _payload(request, approval, blocks, None, provider_call_performed=False)
    trial = run_provider_live_trial(question, live_provider=True, env=env_values, transport=transport)
    return _payload(request, approval, [], trial, provider_call_performed=trial["trace"]["decision"]["provider_call_performed"])


def validate_user_approved_provider_trial_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    evidence = payload.get("provider_evidence_packet")
    evidence_safe = evidence is None or (evidence["authoritative"] is False and evidence["memory_candidate"] is False)
    return (
        evidence_safe
        and flags["user_approved_provider_live_trial_enabled"] is True
        and flags["dry_run_default"] is True
        and flags["provider_response_authoritative"] is False
        and all(value is False for key, value in flags.items() if key not in {"user_approved_provider_live_trial_enabled", "dry_run_default", "provider_response_authoritative"})
    )


def _payload(request: UserApprovedProviderTrialRequest, approval: dict[str, object], blocks: list[str], trial: dict[str, object] | None, *, provider_call_performed: bool) -> dict[str, object]:
    packet = trial["trace"]["evidence_packet"] if trial and trial["trace"].get("evidence_packet") else None
    return {
        "phase": "Runtime V2.1C",
        "request": request.as_dict(),
        "approval": approval,
        "gate": {
            "gate_id": _stable_id("v21c-gate", request.request_id, blocks),
            "permitted": not blocks,
            "blocks": blocks,
        },
        "redacted_request": trial["trace"]["redacted_request"] if trial else {"api_key_present": _api_key_present(parse_env_file()), "api_key_redacted": True},
        "provider_evidence_packet": packet,
        "decision": {
            "decision_id": _stable_id("v21c-decision", request.request_id, provider_call_performed),
            "provider_call_performed": provider_call_performed,
            "provider_answer_authoritative": False,
            "evidence_only": True,
        },
        "invariant_flags": dict(RUNTIME_V21C_FLAGS),
        "final_recommendation": "PROCEED_DAILY_EVALUATOR_SCHEDULER_ACTIVATION_USER_APPROVED",
    }


def _env_gates_open(env: dict[str, str]) -> bool:
    return env.get("DELTA_UNKNOWN_PROVIDER_ENABLED", "").lower() == "true" and env.get("DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL", "").lower() == "true"


def _api_key_present(env: dict[str, str]) -> bool:
    key = env.get("DELTA_UNKNOWN_PROVIDER_API_KEY") or env.get("DELTA_EVALUATOR_API_KEY") or ""
    return bool(key and key != "put_key_here")


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
