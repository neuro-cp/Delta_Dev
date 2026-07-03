from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


APPROVAL_TEXT = "APPROVE_HYB1_SHADOW_TRIAL\napproved_by=user\ntrial_scope=shadow_comparison_only"

RUNTIME_V23A_FLAGS = {
    "hyb1_shadow_simulation_enabled": True,
    "disabled_by_default": True,
    "model_b_default_changed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "hyb1_authoritative": False,
    "memory_write_performed": False,
    "provider_call_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
}


@dataclass(frozen=True)
class HYB1ShadowSimulationRequest:
    request_id: str
    prompt: str
    approval_text: str = ""

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def parse_hyb1_shadow_approval(text: str) -> dict[str, object]:
    normalized = _normalize(text)
    return {
        "approval_present": bool(normalized),
        "matches_required_shape": normalized == _normalize(APPROVAL_TEXT),
    }


def run_hyb1_shadow_simulation(prompt: str, *, approval_text: str = "", env: dict[str, str] | None = None) -> dict[str, object]:
    env_values = os.environ if env is None else env
    approval = parse_hyb1_shadow_approval(approval_text)
    gate = {
        "gate_id": _stable_id("v23a-gate", prompt, approval["matches_required_shape"]),
        "approval_required": True,
        "env_enabled": str(env_values.get("DELTA_HYB1_SHADOW_TRIAL_ENABLED", "")).lower() == "true",
        "env_execution_allowed": str(env_values.get("DELTA_HYB1_SHADOW_TRIAL_ALLOW_EXECUTION", "")).lower() == "true",
        "approval": approval,
    }
    gate["simulation_permitted"] = bool(gate["env_enabled"] and gate["env_execution_allowed"] and approval["matches_required_shape"])
    model_b = {
        "output_id": _stable_id("v23a-model-b", prompt),
        "model": "Model B",
        "default_runtime": True,
        "output_text": f"Model B baseline response for: {prompt}",
        "authoritative": False,
    }
    hyb1 = {
        "output_id": _stable_id("v23a-hyb1", prompt),
        "model": "HYB1",
        "dormant_candidate": True,
        "comparison_only": True,
        "output_text": f"HYB1 shadow candidate response for: {prompt}",
        "authoritative": False,
    }
    scorecard = {
        "scorecard_id": _stable_id("v23a-scorecard", model_b["output_id"], hyb1["output_id"]),
        "compared": gate["simulation_permitted"],
        "model_b_preserved": True,
        "hyb1_promotion_blocked": True,
        "memory_write_performed": False,
        "provider_call_performed": False,
    }
    return {
        "phase": "Runtime V2.3A",
        "request": HYB1ShadowSimulationRequest(_stable_id("v23a-request", prompt), prompt, approval_text).as_dict(),
        "gate": gate,
        "model_b_output": model_b,
        "hyb1_candidate_output": hyb1,
        "scorecard": scorecard,
        "decision": {
            "runs_shadow_comparison": gate["simulation_permitted"],
            "changes_default": False,
            "promotes_hyb1": False,
            "hyb1_authority": False,
        },
        "invariant_flags": dict(RUNTIME_V23A_FLAGS),
        "final_recommendation": "PROCEED_LOCALHOST_WRITE_EXECUTION_BRIDGE",
    }


def validate_hyb1_shadow_simulation_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["decision"]["changes_default"] is False
        and payload["decision"]["promotes_hyb1"] is False
        and payload["hyb1_candidate_output"]["comparison_only"] is True
        and flags["hyb1_shadow_simulation_enabled"] is True
        and flags["disabled_by_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"hyb1_shadow_simulation_enabled", "disabled_by_default"})
    )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

