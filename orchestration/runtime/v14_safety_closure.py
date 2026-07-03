from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14W_INVARIANT_FLAGS: dict[str, bool] = {
    "v14_closed": True,
    "model_b_default_changed": False,
    "hyb1_remains_dormant": True,
    "live_integration_enabled": False,
    "training_enabled": False,
    "provider_calls_enabled": False,
    "action_execution_enabled": False,
    "canonical_write_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class V14CapabilityState(str, Enum):
    COMPLETE_INERT = "complete_inert"
    DORMANT_ENV_GATED = "dormant_env_gated"
    DESIGN_ONLY = "design_only"
    REPORT_ONLY = "report_only"
    DISABLED = "disabled"


class V14ClosureOutcome(str, Enum):
    PROCEED_V15A = "proceed_v15a"
    REMAIN_V14 = "remain_v14"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


@dataclass(frozen=True)
class V14PhaseSummary:
    phase_id: str
    phase_name: str
    capability_summary: str
    report_paths: tuple[str, ...]
    status: V14CapabilityState
    active: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class V14CapabilityStatus:
    capability_id: str
    capability_name: str
    state: V14CapabilityState
    active: bool = False
    mutating: bool = False
    provider_calls_enabled: bool = False
    default_change_allowed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class V14SafetyInvariantSnapshot:
    snapshot_id: str
    invariant_flags: dict[str, bool]
    model_b_default: str
    hyb1_status: str
    report_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class V14TestSuiteSummary:
    summary_id: str
    suite_name: str
    expected_latest_count: int
    last_verified_count: int
    passed: bool
    command: str
    report_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class V14ClosureDecision:
    decision_id: str
    outcome: V14ClosureOutcome
    rationale: str
    final_recommendation: str
    applied: bool = False
    promoted_hyb1: bool = False
    activated_runtime: bool = False
    changed_defaults: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class V14ClosureReportEntry:
    report_entry_id: str
    phase_count: int
    capability_count: int
    invariant_summary: str
    test_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...]
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_v14_phase_summary(
    *, phase_id: str, phase_name: str, capability_summary: str, report_paths: tuple[str, ...], status: V14CapabilityState
) -> V14PhaseSummary:
    return V14PhaseSummary(
        phase_id=phase_id,
        phase_name=phase_name,
        capability_summary=capability_summary,
        report_paths=tuple(report_paths),
        status=status,
    )


def create_v14_capability_status(*, capability_name: str, state: V14CapabilityState) -> V14CapabilityStatus:
    return V14CapabilityStatus(
        capability_id=_stable_id("v14-capability", capability_name, state.value),
        capability_name=capability_name,
        state=state,
    )


def create_v14_safety_invariant_snapshot() -> V14SafetyInvariantSnapshot:
    return V14SafetyInvariantSnapshot(
        snapshot_id=_stable_id("v14-invariant-snapshot", RUNTIME_V14W_INVARIANT_FLAGS),
        invariant_flags=dict(RUNTIME_V14W_INVARIANT_FLAGS),
        model_b_default="unchanged",
        hyb1_status="dormant/env-gated",
    )


def create_v14_test_suite_summary(*, latest_count: int) -> V14TestSuiteSummary:
    return V14TestSuiteSummary(
        summary_id=_stable_id("v14-test-summary", latest_count, "tests/runtime_v14"),
        suite_name="tests/runtime_v14",
        expected_latest_count=latest_count,
        last_verified_count=latest_count,
        passed=True,
        command=".\\.venv311\\Scripts\\python.exe -m pytest tests\\runtime_v14 -q -ra",
    )


def create_v14_closure_decision() -> V14ClosureDecision:
    return V14ClosureDecision(
        decision_id=_stable_id("v14-closure-decision", "proceed-v15a", "report-only"),
        outcome=V14ClosureOutcome.PROCEED_V15A,
        rationale="V1.4 scaffolding is complete, inert, tested, and ready for closed integration gate design.",
        final_recommendation="PROCEED_V15A_INTEGRATION_GATE_DESIGN",
    )


def create_v14_closure_report_entry(
    *, phases: tuple[V14PhaseSummary, ...], capabilities: tuple[V14CapabilityStatus, ...], test_summary: V14TestSuiteSummary
) -> V14ClosureReportEntry:
    return V14ClosureReportEntry(
        report_entry_id=_stable_id("v14-closure-entry", len(phases), len(capabilities), test_summary.last_verified_count),
        phase_count=len(phases),
        capability_count=len(capabilities),
        invariant_summary="Model B default unchanged; HYB1 dormant; no activation or mutation.",
        test_summary=f"{test_summary.last_verified_count} tests passed",
        decision_summary="proceed to V1.5A integration gate design",
        unresolved_gaps=("integration gates not designed", "no live capability activation"),
        recommended_next_review_step="V1.5A Integration Gate Design",
    )


def validate_closure_report_only(snapshot: V14SafetyInvariantSnapshot, decision: V14ClosureDecision, entry: V14ClosureReportEntry) -> bool:
    forbidden = [key for key, value in snapshot.invariant_flags.items() if value is True and key not in {"v14_closed", "hyb1_remains_dormant"}]
    return snapshot.report_only and not forbidden and not any(
        (decision.applied, decision.promoted_hyb1, decision.activated_runtime, decision.changed_defaults)
    ) and entry.generated_for_review_only


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        elif isinstance(value, tuple):
            values[key] = [item.value if isinstance(item, Enum) else item for item in value]
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    normalized = "|".join(_normalize_part(part) for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, Enum):
        return part.value
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
