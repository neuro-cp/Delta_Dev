from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v16_env import parse_env_file
from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import _default_transport, _extract_evaluator_text
from orchestration.runtime.v18_manual_provider_live_trial_gate import ProviderLiveTrialGateStatus, check_provider_live_trial_gate


RUNTIME_V18F_FLAGS: dict[str, bool] = {
    "manual_provider_live_trial_enabled": True,
    "dry_run_default": True,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_enabled": False,
    "provider_response_authoritative": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}

Transport = Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]]


@dataclass(frozen=True)
class ProviderLiveTrialRequest:
    request_id: str
    question: str
    live_provider: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderLiveTrialRedactedRequest:
    request_id: str
    endpoint: str
    model: str
    api_key_present: bool
    api_key_redacted: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderLiveEvidencePacket:
    evidence_packet_id: str
    provider_text: str
    provenance: str
    authoritative: bool = False
    memory_candidate: bool = False
    uncertainty: str = "provider evidence only"

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderLiveTrialDecision:
    decision_id: str
    decision: str
    provider_call_performed: bool
    provider_answer_authoritative: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderLiveTrialTrace:
    trace_id: str
    request: ProviderLiveTrialRequest
    redacted_request: ProviderLiveTrialRedactedRequest
    decision: ProviderLiveTrialDecision
    evidence_packet: ProviderLiveEvidencePacket | None

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "request": self.request.as_dict(),
            "redacted_request": self.redacted_request.as_dict(),
            "decision": self.decision.as_dict(),
            "evidence_packet": self.evidence_packet.as_dict() if self.evidence_packet else None,
        }


@dataclass(frozen=True)
class ProviderLiveTrialReportEntry:
    report_entry_id: str
    decision: str
    provider_call_performed: bool
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def run_provider_live_trial(question: str, *, live_provider: bool = False, env: dict[str, str] | None = None, transport: Transport | None = None) -> dict[str, object]:
    env_values = parse_env_file() if env is None else env
    request = ProviderLiveTrialRequest(_stable_id("v18f-request", question, live_provider), question, live_provider)
    redacted = ProviderLiveTrialRedactedRequest(_stable_id("v18f-redacted", question), env_values.get("DELTA_UNKNOWN_PROVIDER_ENDPOINT", "https://api.openai.com/v1/chat/completions"), env_values.get("DELTA_UNKNOWN_PROVIDER_MODEL", "gpt-4.1-mini"), _api_key_present(env_values))
    local = route_local_knowledge_answer(question)
    gate = check_provider_live_trial_gate(question, env=env_values)
    if local.matched:
        decision = ProviderLiveTrialDecision(_stable_id("v18f-decision", question, "local_known"), "local_known_provider_refused", False)
        return _payload(request, redacted, decision, None)
    if not live_provider:
        decision = ProviderLiveTrialDecision(_stable_id("v18f-decision", question, "dry_run"), "dry_run_provider_request", False)
        return _payload(request, redacted, decision, None)
    if gate["decision"]["status"] != ProviderLiveTrialGateStatus.PERMITTED.value:
        decision = ProviderLiveTrialDecision(_stable_id("v18f-decision", question, "refused"), "live_refused_by_gate", False)
        return _payload(request, redacted, decision, None)
    body = {"model": redacted.model, "temperature": 0, "max_tokens": 120, "messages": [{"role": "user", "content": question}]}
    key = env_values.get("DELTA_UNKNOWN_PROVIDER_API_KEY") or env_values.get("DELTA_EVALUATOR_API_KEY") or ""
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    response = (transport or _default_transport)(redacted.endpoint, headers, body, 30)
    text = _extract_evaluator_text(response)
    packet = ProviderLiveEvidencePacket(_stable_id("v18f-packet", question, text), text, "manual one-shot provider live trial")
    decision = ProviderLiveTrialDecision(_stable_id("v18f-decision", question, "packet"), "live_evidence_packet", True)
    return _payload(request, redacted, decision, packet)


def validate_provider_live_trial_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    packet = payload["trace"].get("evidence_packet")
    packet_safe = packet is None or (packet["authoritative"] is False and packet["memory_candidate"] is False)
    return (
        packet_safe
        and payload["trace"]["redacted_request"]["api_key_redacted"] is True
        and payload["trace"]["decision"]["provider_answer_authoritative"] is False
        and flags["manual_provider_live_trial_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"manual_provider_live_trial_enabled", "dry_run_default"})
    )


def _payload(request: ProviderLiveTrialRequest, redacted: ProviderLiveTrialRedactedRequest, decision: ProviderLiveTrialDecision, packet: ProviderLiveEvidencePacket | None) -> dict[str, object]:
    trace = ProviderLiveTrialTrace(_stable_id("v18f-trace", request.request_id, decision.decision), request, redacted, decision, packet)
    payload = {
        "phase": "Runtime V1.8F",
        "trace": trace.as_dict(),
        "report_entry": ProviderLiveTrialReportEntry(_stable_id("v18f-entry", decision.decision), decision.decision, decision.provider_call_performed, True).as_dict(),
        "invariant_flags": dict(RUNTIME_V18F_FLAGS),
        "final_recommendation": "PROCEED_PROVIDER_EVIDENCE_POST_REVIEW",
    }
    return payload


def _api_key_present(env: dict[str, str]) -> bool:
    key = env.get("DELTA_UNKNOWN_PROVIDER_API_KEY") or env.get("DELTA_EVALUATOR_API_KEY") or ""
    return bool(key and key != "put_key_here")


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
