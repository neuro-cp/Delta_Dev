from __future__ import annotations

import hashlib
from dataclasses import dataclass


RUNTIME_V19A_FLAGS: dict[str, bool] = {
    "controlled_general_memory_recall_expansion_design_enabled": True,
    "general_memory_active": False,
    "authoritative_recall_active": False,
    "provider_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class GeneralMemoryExpansionScope:
    scope_id: str
    design_only: bool = True
    activates_general_memory: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class GeneralMemorySourcePolicy:
    policy_id: str
    allowed_sources: tuple[str, ...]
    excluded_sources: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"policy_id": self.policy_id, "allowed_sources": list(self.allowed_sources), "excluded_sources": list(self.excluded_sources)}


@dataclass(frozen=True)
class GeneralMemoryWritePolicy:
    policy_id: str
    exact_approval_required: bool = True
    autonomous_write_allowed: bool = False
    rollback_required: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class GeneralRecallExpansionPolicy:
    policy_id: str
    recall_candidate_context_only: bool = True
    authoritative_recall_allowed: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class GeneralMemorySafetyGate:
    gate_id: str
    no_scheduler_dependency: bool
    no_training_dependency: bool
    audit_required: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class GeneralMemoryExpansionDecision:
    decision_id: str
    outcome: str
    activated: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class GeneralMemoryExpansionAuditPlan:
    audit_plan_id: str
    audit_required: bool
    rollback_required: bool
    provenance_required: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class GeneralMemoryExpansionReportEntry:
    report_entry_id: str
    safe: bool
    decision: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_controlled_general_memory_recall_expansion_design() -> dict[str, object]:
    source_policy = GeneralMemorySourcePolicy(
        _stable_id("v19a-source-policy"),
        allowed_sources=("approved canonical records only",),
        excluded_sources=("unapproved candidates", "rejected candidates", "deferred candidates", "rolled-back records", "provider/specialist/evaluator output without candidate plus approval"),
    )
    write_policy = GeneralMemoryWritePolicy(_stable_id("v19a-write-policy"))
    recall_policy = GeneralRecallExpansionPolicy(_stable_id("v19a-recall-policy"))
    decision = GeneralMemoryExpansionDecision(_stable_id("v19a-decision"), "design_only_not_activated")
    data = {
        "phase": "Runtime V1.9A",
        "scope": GeneralMemoryExpansionScope(_stable_id("v19a-scope")).as_dict(),
        "source_policy": source_policy.as_dict(),
        "write_policy": write_policy.as_dict(),
        "recall_policy": recall_policy.as_dict(),
        "safety_gate": GeneralMemorySafetyGate(_stable_id("v19a-gate"), True, True, True).as_dict(),
        "decision": decision.as_dict(),
        "audit_plan": GeneralMemoryExpansionAuditPlan(_stable_id("v19a-audit"), True, True, True).as_dict(),
        "report_entry": GeneralMemoryExpansionReportEntry(_stable_id("v19a-entry"), True, decision.outcome).as_dict(),
        "invariant_flags": dict(RUNTIME_V19A_FLAGS),
        "final_recommendation": "PROCEED_UX_FIRST_LOCAL_DELTA_CONSOLE",
    }
    return data


def validate_general_memory_expansion_design_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["scope"]["design_only"] is True
        and payload["scope"]["activates_general_memory"] is False
        and payload["write_policy"]["autonomous_write_allowed"] is False
        and payload["recall_policy"]["authoritative_recall_allowed"] is False
        and payload["decision"]["activated"] is False
        and flags["controlled_general_memory_recall_expansion_design_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "controlled_general_memory_recall_expansion_design_enabled")
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
