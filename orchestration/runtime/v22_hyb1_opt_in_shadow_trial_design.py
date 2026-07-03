from __future__ import annotations

import hashlib
from dataclasses import dataclass


APPROVAL_TEXT = "APPROVE_HYB1_SHADOW_TRIAL\napproved_by=user\ntrial_scope=shadow_comparison_only"

RUNTIME_V22E_FLAGS = {
    "hyb1_shadow_trial_design_enabled": True,
    "hyb1_shadow_execution_enabled_by_default": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "routing_default_changed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
}


@dataclass(frozen=True)
class HYB1ShadowTrialScope:
    scope_id: str
    shadow_comparison_only: bool = True
    output_authoritative: bool = False
    can_promote_hyb1: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def parse_hyb1_shadow_approval(text: str) -> dict[str, object]:
    normalized = _normalize(text)
    return {"approval_present": bool(normalized), "matches_required_shape": normalized == _normalize(APPROVAL_TEXT)}


def design_hyb1_shadow_trial(env: dict[str, str] | None = None, approval_text: str = "") -> dict[str, object]:
    env = env or {}
    approval = parse_hyb1_shadow_approval(approval_text)
    opt_in_ready = (
        env.get("DELTA_HYB1_SHADOW_TRIAL_ENABLED", "").lower() == "true"
        and env.get("DELTA_HYB1_SHADOW_TRIAL_ALLOW_EXECUTION", "").lower() == "true"
        and approval["matches_required_shape"]
    )
    return {
        "phase": "Runtime V2.2E",
        "scope": HYB1ShadowTrialScope(_stable_id("v22e-scope", "shadow")).as_dict(),
        "opt_in_gate": {
            "env_enabled": env.get("DELTA_HYB1_SHADOW_TRIAL_ENABLED", "").lower() == "true",
            "allow_execution": env.get("DELTA_HYB1_SHADOW_TRIAL_ALLOW_EXECUTION", "").lower() == "true",
            "approval": approval,
            "opt_in_ready": opt_in_ready,
        },
        "comparison_plan": {
            "model_b_remains_default": True,
            "hyb1_output_comparison_only": True,
            "hyb1_cannot_write_memory": True,
            "hyb1_cannot_alter_routing_defaults": True,
        },
        "decision": {
            "design_only": True,
            "executes_hyb1_now": False,
            "promotes_hyb1": False,
            "changes_default": False,
        },
        "invariant_flags": dict(RUNTIME_V22E_FLAGS),
        "final_recommendation": "PROCEED_V22_SAFETY_CLOSURE",
    }


def validate_hyb1_shadow_design_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    decision = payload["decision"]
    return (
        decision["executes_hyb1_now"] is False
        and decision["promotes_hyb1"] is False
        and decision["changes_default"] is False
        and flags["hyb1_shadow_trial_design_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "hyb1_shadow_trial_design_enabled")
    )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
