from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v16_env import parse_env_file


RUNTIME_V18E_FLAGS: dict[str, bool] = {
    "manual_provider_live_trial_gate_enabled": True,
    "provider_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class ProviderLiveTrialGateStatus(str, Enum):
    PERMITTED = "permitted"
    REFUSED = "refused"


@dataclass(frozen=True)
class ProviderLiveTrialGateRequest:
    request_id: str
    question: str
    explicit_live_flag_required: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderLiveTrialGateRequirement:
    requirement_id: str
    name: str
    passed: bool
    rationale: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderLiveTrialGateDecision:
    decision_id: str
    status: ProviderLiveTrialGateStatus
    provider_call_performed: bool = False
    provider_answer_authoritative: bool = False

    def as_dict(self) -> dict[str, object]:
        return {"decision_id": self.decision_id, "status": self.status.value, "provider_call_performed": self.provider_call_performed, "provider_answer_authoritative": self.provider_answer_authoritative}


@dataclass(frozen=True)
class ProviderLiveTrialGateAuditRecord:
    audit_id: str
    key_present: bool
    key_redacted: bool
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProviderLiveTrialGateReportEntry:
    report_entry_id: str
    decision_status: str
    passed_requirements: int
    total_requirements: int

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def check_provider_live_trial_gate(question: str, *, env: dict[str, str] | None = None) -> dict[str, object]:
    env_values = parse_env_file() if env is None else env
    request = ProviderLiveTrialGateRequest(_stable_id("v18e-request", question), question)
    local = route_local_knowledge_answer(question)
    requirements = (
        _req("provider_enabled", _truthy(env_values.get("DELTA_UNKNOWN_PROVIDER_ENABLED")), "DELTA_UNKNOWN_PROVIDER_ENABLED must be true."),
        _req("live_call_allowed", _truthy(env_values.get("DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL")), "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL must be true."),
        _req("key_present", _api_key_present(env_values), "Unknown-provider or evaluator API key must be present."),
        _req("unsupported_locally", not local.matched, "Question must be unsupported by local router."),
        _req("explicit_cli_live_flag_future_required", True, "V1.8F must still require --live-provider."),
        _req("evidence_only", True, "Provider answer must remain evidence-only."),
        _req("no_mutation", True, "No memory write, recall mutation, training, or action execution allowed."),
    )
    permitted = all(requirement.passed for requirement in requirements)
    decision = ProviderLiveTrialGateDecision(_stable_id("v18e-decision", question, permitted), ProviderLiveTrialGateStatus.PERMITTED if permitted else ProviderLiveTrialGateStatus.REFUSED)
    audit = ProviderLiveTrialGateAuditRecord(_stable_id("v18e-audit", question), _api_key_present(env_values), True, True)
    return {
        "phase": "Runtime V1.8E",
        "request": request.as_dict(),
        "requirements": [requirement.as_dict() for requirement in requirements],
        "decision": decision.as_dict(),
        "audit_record": audit.as_dict(),
        "report_entry": ProviderLiveTrialGateReportEntry(_stable_id("v18e-entry", question), decision.status.value, sum(1 for item in requirements if item.passed), len(requirements)).as_dict(),
        "invariant_flags": dict(RUNTIME_V18E_FLAGS),
        "final_recommendation": "PROCEED_MANUAL_PROVIDER_LIVE_TRIAL_OPTIONAL_ONE_SHOT",
    }


def validate_provider_live_trial_gate_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["decision"]["provider_call_performed"] is False
        and payload["decision"]["provider_answer_authoritative"] is False
        and payload["audit_record"]["key_redacted"] is True
        and flags["manual_provider_live_trial_gate_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "manual_provider_live_trial_gate_enabled")
    )


def _req(name: str, passed: bool, rationale: str) -> ProviderLiveTrialGateRequirement:
    return ProviderLiveTrialGateRequirement(_stable_id("v18e-req", name, passed), name, passed, rationale)


def _api_key_present(env: dict[str, str]) -> bool:
    key = env.get("DELTA_UNKNOWN_PROVIDER_API_KEY") or env.get("DELTA_EVALUATOR_API_KEY") or ""
    return bool(key and key != "put_key_here")


def _truthy(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
