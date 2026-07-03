from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v16_env import parse_env_file
from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import _default_transport, _extract_evaluator_text


RUNTIME_V17D_SPECIALIST_FLAGS: dict[str, bool] = {
    "specialist_evidence_trial_enabled": True,
    "dry_run_default": True,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_enabled": False,
    "specialist_result_authoritative": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class SpecialistEvidenceDecisionValue(str, Enum):
    LOCAL_KNOWN_NO_SPECIALIST = "local_known_no_specialist"
    DRY_RUN_SPECIALIST_REQUEST = "dry_run_specialist_request"
    LIVE_REFUSED = "live_refused"
    LIVE_EVIDENCE_PACKET = "live_evidence_packet"


@dataclass(frozen=True)
class SpecialistEvidenceRequest:
    request_id: str
    question: str
    specialist_domain: str
    live_specialist: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


Transport = Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]]


def run_specialist_evidence_trial(question: str, *, specialist_domain: str = "general", live_specialist: bool = False, transport: Transport | None = None) -> dict[str, object]:
    request = SpecialistEvidenceRequest(_stable_id("v17d-specialist-request", question, specialist_domain, live_specialist), question, specialist_domain, live_specialist)
    local = route_local_knowledge_answer(question)
    if local.matched:
        return _payload(request, SpecialistEvidenceDecisionValue.LOCAL_KNOWN_NO_SPECIALIST, local.answer.as_dict() if local.answer else {}, None, False)
    env = parse_env_file()
    provider_request = _provider_contract(question, specialist_domain, env)
    gate_ok = _bool(env.get("DELTA_SPECIALIST_ROUTING_ENABLED")) and _bool(env.get("DELTA_SPECIALIST_ALLOW_LIVE_CALL")) and _api_key_present(env)
    if not live_specialist:
        return _payload(request, SpecialistEvidenceDecisionValue.DRY_RUN_SPECIALIST_REQUEST, provider_request, None, False)
    if not gate_ok:
        return _payload(request, SpecialistEvidenceDecisionValue.LIVE_REFUSED, provider_request, None, False)
    body = {"model": provider_request["model"], "temperature": 0, "max_tokens": 140, "messages": [{"role": "user", "content": f"Specialist domain: {specialist_domain}\nQuestion: {question}"}]}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + env.get("DELTA_EVALUATOR_API_KEY", "")}
    response = (transport or _default_transport)(provider_request["endpoint"], headers, body, 30)
    text = _extract_evaluator_text(response)
    packet = {"specialist_evidence_packet_id": _stable_id("v17d-packet", question, text), "specialist_text": text, "authoritative": False, "memory_candidate": False, "merge_applied": False}
    return _payload(request, SpecialistEvidenceDecisionValue.LIVE_EVIDENCE_PACKET, provider_request, packet, True)


def validate_specialist_evidence_trial_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    packet = payload.get("evidence_packet")
    packet_safe = packet is None or (packet["authoritative"] is False and packet["memory_candidate"] is False and packet["merge_applied"] is False)
    return (
        packet_safe
        and payload["decision"]["specialist_result_authoritative"] is False
        and payload["decision"]["memory_write_performed"] is False
        and payload["decision"]["recall_mutated"] is False
        and flags["specialist_evidence_trial_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"specialist_evidence_trial_enabled", "dry_run_default"})
    )


def _payload(request: SpecialistEvidenceRequest, decision: SpecialistEvidenceDecisionValue, route_or_contract: dict[str, object], packet: dict[str, object] | None, provider_call: bool) -> dict[str, object]:
    return {
        "phase": "Runtime V1.7D",
        "request": request.as_dict(),
        "route_or_provider_contract": route_or_contract,
        "evidence_packet": packet,
        "decision": {
            "decision_id": _stable_id("v17d-decision", request.request_id, decision.value),
            "decision": decision.value,
            "provider_call_performed": provider_call,
            "specialist_result_authoritative": False,
            "memory_write_performed": False,
            "recall_mutated": False,
        },
        "invariant_flags": dict(RUNTIME_V17D_SPECIALIST_FLAGS),
        "final_recommendation": "PROCEED_PROVIDER_EVIDENCE_REVIEW_UI_OR_LIMITED_GENERAL_RECALL_TRIAL",
    }


def _provider_contract(question: str, domain: str, env: dict[str, str]) -> dict[str, object]:
    return {
        "question": question,
        "specialist_domain": domain,
        "provider": env.get("DELTA_SPECIALIST_DEFAULT_PROVIDER", "openai"),
        "model": env.get("DELTA_SPECIALIST_DEFAULT_MODEL", "gpt-4.1-mini"),
        "endpoint": env.get("DELTA_UNKNOWN_PROVIDER_ENDPOINT", "https://api.openai.com/v1/chat/completions"),
        "api_key_present": _api_key_present(env),
        "api_key_redacted": True,
        "authoritative": False,
    }


def _api_key_present(env: dict[str, str]) -> bool:
    key = env.get("DELTA_EVALUATOR_API_KEY", "")
    return bool(key and key != "put_key_here")


def _bool(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
