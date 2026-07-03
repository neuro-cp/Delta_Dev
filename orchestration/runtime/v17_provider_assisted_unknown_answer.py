from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v16_env import parse_env_file
from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import _default_transport, _extract_evaluator_text


RUNTIME_V17C_UNKNOWN_FLAGS: dict[str, bool] = {
    "provider_assisted_unknown_path_enabled": True,
    "dry_run_default": True,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "provider_response_authoritative": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class UnknownAnswerDecisionValue(str, Enum):
    LOCAL_KNOWN = "local_known"
    DRY_RUN_PROVIDER_REQUEST = "dry_run_provider_request"
    LIVE_REFUSED = "live_refused"
    LIVE_EVIDENCE_PACKET = "live_evidence_packet"


@dataclass(frozen=True)
class UnknownAnswerRequest:
    request_id: str
    question: str
    live_provider: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


Transport = Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]]


def answer_unknown_with_controlled_provider(question: str, *, live_provider: bool = False, transport: Transport | None = None) -> dict[str, object]:
    request = UnknownAnswerRequest(_stable_id("v17c-unknown-request", question, live_provider), question, live_provider)
    local_route = route_local_knowledge_answer(question)
    if local_route.matched:
        return _payload(request, UnknownAnswerDecisionValue.LOCAL_KNOWN, local_route.answer.as_dict() if local_route.answer else {}, None, provider_call=False)
    env = parse_env_file()
    gate_ok = _bool(env.get("DELTA_UNKNOWN_PROVIDER_ENABLED")) and _bool(env.get("DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL")) and _api_key_present(env)
    provider_request = _provider_request(question, env)
    if not live_provider:
        return _payload(request, UnknownAnswerDecisionValue.DRY_RUN_PROVIDER_REQUEST, provider_request, None, provider_call=False)
    if not gate_ok:
        return _payload(request, UnknownAnswerDecisionValue.LIVE_REFUSED, provider_request, None, provider_call=False)
    body = {"model": provider_request["model"], "temperature": 0, "max_tokens": 120, "messages": [{"role": "user", "content": question}]}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + env.get("DELTA_EVALUATOR_API_KEY", "")}
    response = (transport or _default_transport)(provider_request["endpoint"], headers, body, 30)
    text = _extract_evaluator_text(response)
    packet = {"evidence_packet_id": _stable_id("v17c-evidence", question, text), "provider_text": text, "authoritative": False, "memory_candidate": False, "uncertainty": "provider-assisted evidence only"}
    return _payload(request, UnknownAnswerDecisionValue.LIVE_EVIDENCE_PACKET, provider_request, packet, provider_call=True)


def validate_unknown_answer_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    packet = payload.get("evidence_packet")
    packet_safe = packet is None or (packet["authoritative"] is False and packet["memory_candidate"] is False)
    return (
        packet_safe
        and payload["decision"]["provider_answer_authoritative"] is False
        and payload["decision"]["memory_write_performed"] is False
        and payload["decision"]["recall_mutated"] is False
        and flags["provider_assisted_unknown_path_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"provider_assisted_unknown_path_enabled", "dry_run_default"})
    )


def _payload(request: UnknownAnswerRequest, decision: UnknownAnswerDecisionValue, route_or_request: dict[str, object], evidence_packet: dict[str, object] | None, *, provider_call: bool) -> dict[str, object]:
    return {
        "phase": "Runtime V1.7C",
        "request": request.as_dict(),
        "route_or_provider_request": route_or_request,
        "evidence_packet": evidence_packet,
        "decision": {
            "decision_id": _stable_id("v17c-decision", request.request_id, decision.value),
            "decision": decision.value,
            "provider_call_performed": provider_call,
            "provider_answer_authoritative": False,
            "memory_write_performed": False,
            "recall_mutated": False,
        },
        "invariant_flags": dict(RUNTIME_V17C_UNKNOWN_FLAGS),
        "final_recommendation": "PROCEED_SPECIALIST_SLM_EVIDENCE_ACQUISITION_TRIAL",
    }


def _provider_request(question: str, env: dict[str, str]) -> dict[str, object]:
    return {"question": question, "model": env.get("DELTA_UNKNOWN_PROVIDER_MODEL", "gpt-4.1-mini"), "endpoint": env.get("DELTA_UNKNOWN_PROVIDER_ENDPOINT", "https://api.openai.com/v1/chat/completions"), "api_key_present": _api_key_present(env), "api_key_redacted": True, "authoritative": False}


def _api_key_present(env: dict[str, str]) -> bool:
    key = env.get("DELTA_EVALUATOR_API_KEY", "")
    return bool(key and key != "put_key_here")


def _bool(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
