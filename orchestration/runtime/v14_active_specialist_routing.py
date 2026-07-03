from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14N_INVARIANT_FLAGS: dict[str, bool] = {
    "specialist_routing_enabled": False,
    "provider_calls_enabled": False,
    "network_enabled": False,
    "human_approval_gate_enabled": False,
    "merge_protocol_integration_enabled": False,
    "canonical_write_enabled": False,
    "active_store_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "scheduler_enabled": False,
    "execution_enabled": False,
    "runtime_defaults_changed": False,
}


class SpecialistRoutingRequestKind(str, Enum):
    EVIDENCE_GAP = "evidence_gap"
    CONTRADICTION_CHECK = "contradiction_check"
    CITATION_CHECK = "citation_check"
    MATH_CHECK = "math_check"
    CODE_CHECK = "code_check"
    POLICY_CHECK = "policy_check"
    DOMAIN_CHECK = "domain_check"
    SAFETY_CHECK = "safety_check"
    UNKNOWN_RESOLUTION = "unknown_resolution"


class SpecialistType(str, Enum):
    GENERALIST_REVIEW = "generalist_review"
    EVIDENCE_SPECIALIST = "evidence_specialist"
    CONTRADICTION_SPECIALIST = "contradiction_specialist"
    CITATION_SPECIALIST = "citation_specialist"
    MATH_SPECIALIST = "math_specialist"
    CODE_SPECIALIST = "code_specialist"
    POLICY_SPECIALIST = "policy_specialist"
    SAFETY_SPECIALIST = "safety_specialist"
    UNKNOWN_SPECIALIST = "unknown_specialist"


class SpecialistRoutingOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    GATED_OFF = "gated_off"
    REQUIRES_HUMAN_APPROVAL = "requires_human_approval"
    ELIGIBLE_FOR_FUTURE_ROUTING = "eligible_for_future_routing"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


@dataclass(frozen=True)
class SpecialistRoutingRequest:
    request_id: str
    request_kind: SpecialistRoutingRequestKind
    question: str
    evidence_gap: str = ""
    lane_scope: tuple[str, ...] = ()
    source_trace_ids: tuple[str, ...] = ()
    preferred_specialist: SpecialistType = SpecialistType.GENERALIST_REVIEW
    routing_enabled: bool = False
    provider_calls_enabled: bool = False
    network_enabled: bool = False
    active: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "request_kind": self.request_kind.value,
            "question": self.question,
            "evidence_gap": self.evidence_gap,
            "lane_scope": list(self.lane_scope),
            "source_trace_ids": list(self.source_trace_ids),
            "preferred_specialist": self.preferred_specialist.value,
            "routing_enabled": self.routing_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "network_enabled": self.network_enabled,
            "active": self.active,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistRoutingGate:
    gate_id: str
    request_id: str
    routing_enabled: bool = False
    provider_calls_enabled: bool = False
    network_enabled: bool = False
    human_approval_required: bool = True
    human_approval_present: bool = False
    merge_protocol_integration_enabled: bool = False
    rationale: str = "active specialist routing is gated off by default"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id,
            "request_id": self.request_id,
            "routing_enabled": self.routing_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "network_enabled": self.network_enabled,
            "human_approval_required": self.human_approval_required,
            "human_approval_present": self.human_approval_present,
            "merge_protocol_integration_enabled": self.merge_protocol_integration_enabled,
            "rationale": self.rationale,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SpecialistProviderContract:
    contract_id: str
    specialist_type: SpecialistType
    provider_name: str = "future_provider_placeholder"
    allowed_input_kinds: tuple[SpecialistRoutingRequestKind, ...] = ()
    allowed_output_contract: str = "bounded evidence packet draft only"
    active: bool = False
    provider_calls_enabled: bool = False
    network_enabled: bool = False
    authority_granted: bool = False
    may_write_memory: bool = False
    may_mutate_runtime: bool = False
    may_execute_actions: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_id": self.contract_id,
            "specialist_type": self.specialist_type.value,
            "provider_name": self.provider_name,
            "allowed_input_kinds": [kind.value for kind in self.allowed_input_kinds],
            "allowed_output_contract": self.allowed_output_contract,
            "active": self.active,
            "provider_calls_enabled": self.provider_calls_enabled,
            "network_enabled": self.network_enabled,
            "authority_granted": self.authority_granted,
            "may_write_memory": self.may_write_memory,
            "may_mutate_runtime": self.may_mutate_runtime,
            "may_execute_actions": self.may_execute_actions,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SpecialistRoutingDecision:
    decision_id: str
    request_id: str
    gate_id: str
    contract_id: str
    outcome: SpecialistRoutingOutcome
    rationale: str
    selected_specialist: SpecialistType
    applied: bool = False
    provider_called: bool = False
    routing_executed: bool = False
    network_used: bool = False
    memory_written: bool = False
    canonical_written: bool = False
    merge_protocol_invoked: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14N_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "gate_id": self.gate_id,
            "contract_id": self.contract_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "selected_specialist": self.selected_specialist.value,
            "applied": self.applied,
            "provider_called": self.provider_called,
            "routing_executed": self.routing_executed,
            "network_used": self.network_used,
            "memory_written": self.memory_written,
            "canonical_written": self.canonical_written,
            "merge_protocol_invoked": self.merge_protocol_invoked,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SpecialistRoutingTrace:
    trace_id: str
    request_id: str
    gate_id: str
    contract_id: str
    decision_id: str
    source_trace_ids: tuple[str, ...] = ()
    generated_for_review_only: bool = True
    applied: bool = False
    provider_called: bool = False
    memory_written: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "gate_id": self.gate_id,
            "contract_id": self.contract_id,
            "decision_id": self.decision_id,
            "source_trace_ids": list(self.source_trace_ids),
            "generated_for_review_only": self.generated_for_review_only,
            "applied": self.applied,
            "provider_called": self.provider_called,
            "memory_written": self.memory_written,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SpecialistRoutingPlan:
    plan_id: str
    request_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    trace_ids: tuple[str, ...] = ()
    routing_enabled: bool = False
    provider_calls_enabled: bool = False
    network_enabled: bool = False
    human_approval_gate_enabled: bool = False
    merge_protocol_integration_enabled: bool = False
    memory_mutation_enabled: bool = False
    execution_enabled: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14N_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "request_ids": list(self.request_ids),
            "decision_ids": list(self.decision_ids),
            "trace_ids": list(self.trace_ids),
            "routing_enabled": self.routing_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "network_enabled": self.network_enabled,
            "human_approval_gate_enabled": self.human_approval_gate_enabled,
            "merge_protocol_integration_enabled": self.merge_protocol_integration_enabled,
            "memory_mutation_enabled": self.memory_mutation_enabled,
            "execution_enabled": self.execution_enabled,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SpecialistRoutingReportEntry:
    report_entry_id: str
    trace_id: str
    request_summary: str
    gate_summary: str
    contract_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = "design action authorization before enabling routing"
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "report_entry_id": self.report_entry_id,
            "trace_id": self.trace_id,
            "request_summary": self.request_summary,
            "gate_summary": self.gate_summary,
            "contract_summary": self.contract_summary,
            "decision_summary": self.decision_summary,
            "unresolved_gaps": list(self.unresolved_gaps),
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
        }


def create_specialist_routing_request(
    *,
    request_kind: SpecialistRoutingRequestKind,
    question: str,
    evidence_gap: str = "",
    lane_scope: tuple[str, ...] = (),
    source_trace_ids: tuple[str, ...] = (),
    preferred_specialist: SpecialistType | None = None,
    notes: str = "",
) -> SpecialistRoutingRequest:
    preferred = preferred_specialist or _default_specialist_for_kind(request_kind)
    request_id = _stable_id(
        "specialist-routing-request",
        request_kind.value,
        question,
        evidence_gap,
        ",".join(lane_scope),
        ",".join(source_trace_ids),
        preferred.value,
    )
    return SpecialistRoutingRequest(
        request_id=request_id,
        request_kind=request_kind,
        question=question.strip(),
        evidence_gap=evidence_gap.strip(),
        lane_scope=tuple(lane_scope),
        source_trace_ids=tuple(source_trace_ids),
        preferred_specialist=preferred,
        notes=notes,
    )


def create_specialist_routing_gate(request_id: str, *, rationale: str = "") -> SpecialistRoutingGate:
    gate_id = _stable_id("specialist-routing-gate", request_id, rationale)
    return SpecialistRoutingGate(
        gate_id=gate_id,
        request_id=request_id,
        rationale=rationale or "active specialist routing is gated off by default",
    )


def create_specialist_provider_contract(
    *,
    specialist_type: SpecialistType,
    provider_name: str = "future_provider_placeholder",
    allowed_input_kinds: tuple[SpecialistRoutingRequestKind, ...] = (),
) -> SpecialistProviderContract:
    contract_id = _stable_id(
        "specialist-provider-contract",
        specialist_type.value,
        provider_name,
        ",".join(kind.value for kind in allowed_input_kinds),
    )
    return SpecialistProviderContract(
        contract_id=contract_id,
        specialist_type=specialist_type,
        provider_name=provider_name,
        allowed_input_kinds=tuple(allowed_input_kinds),
    )


def decide_specialist_routing(
    request: SpecialistRoutingRequest,
    gate: SpecialistRoutingGate,
    contract: SpecialistProviderContract,
) -> SpecialistRoutingDecision:
    if any(RUNTIME_V14N_INVARIANT_FLAGS.values()):
        outcome = SpecialistRoutingOutcome.BLOCKED_BY_INVARIANT
        rationale = "runtime invariant flags are not in the dormant baseline state"
    elif not gate.routing_enabled or not contract.active or not request.routing_enabled:
        outcome = SpecialistRoutingOutcome.GATED_OFF
        rationale = "specialist routing is design-only and gated off"
    elif gate.human_approval_required and not gate.human_approval_present:
        outcome = SpecialistRoutingOutcome.REQUIRES_HUMAN_APPROVAL
        rationale = "future active routing would require explicit approval"
    else:
        outcome = SpecialistRoutingOutcome.ELIGIBLE_FOR_FUTURE_ROUTING
        rationale = "eligible only as a future routing design candidate"
    decision_id = _stable_id("specialist-routing-decision", request.request_id, gate.gate_id, contract.contract_id, outcome.value)
    return SpecialistRoutingDecision(
        decision_id=decision_id,
        request_id=request.request_id,
        gate_id=gate.gate_id,
        contract_id=contract.contract_id,
        outcome=outcome,
        rationale=rationale,
        selected_specialist=contract.specialist_type,
    )


def create_specialist_routing_trace(
    request: SpecialistRoutingRequest,
    gate: SpecialistRoutingGate,
    contract: SpecialistProviderContract,
    decision: SpecialistRoutingDecision,
) -> SpecialistRoutingTrace:
    trace_id = _stable_id("specialist-routing-trace", request.request_id, gate.gate_id, contract.contract_id, decision.decision_id)
    return SpecialistRoutingTrace(
        trace_id=trace_id,
        request_id=request.request_id,
        gate_id=gate.gate_id,
        contract_id=contract.contract_id,
        decision_id=decision.decision_id,
        source_trace_ids=request.source_trace_ids,
    )


def create_specialist_routing_plan(
    *,
    requests: tuple[SpecialistRoutingRequest, ...] = (),
    decisions: tuple[SpecialistRoutingDecision, ...] = (),
    traces: tuple[SpecialistRoutingTrace, ...] = (),
) -> SpecialistRoutingPlan:
    plan_id = _stable_id(
        "specialist-routing-plan",
        ",".join(request.request_id for request in requests),
        ",".join(decision.decision_id for decision in decisions),
        ",".join(trace.trace_id for trace in traces),
    )
    return SpecialistRoutingPlan(
        plan_id=plan_id,
        request_ids=tuple(request.request_id for request in requests),
        decision_ids=tuple(decision.decision_id for decision in decisions),
        trace_ids=tuple(trace.trace_id for trace in traces),
    )


def create_specialist_routing_report_entry(
    *,
    trace: SpecialistRoutingTrace,
    request: SpecialistRoutingRequest,
    gate: SpecialistRoutingGate,
    contract: SpecialistProviderContract,
    decision: SpecialistRoutingDecision,
    unresolved_gaps: tuple[str, ...] = (),
) -> SpecialistRoutingReportEntry:
    report_entry_id = _stable_id("specialist-routing-report-entry", trace.trace_id, decision.decision_id)
    return SpecialistRoutingReportEntry(
        report_entry_id=report_entry_id,
        trace_id=trace.trace_id,
        request_summary=f"{request.request_kind.value}: {request.evidence_gap or request.question}",
        gate_summary="routing/provider/network disabled",
        contract_summary=f"{contract.specialist_type.value} contract inactive",
        decision_summary=f"{decision.outcome.value}: {decision.rationale}",
        unresolved_gaps=tuple(unresolved_gaps),
    )


def validate_specialist_routing_request_inert(request: SpecialistRoutingRequest) -> bool:
    return not any((request.routing_enabled, request.provider_calls_enabled, request.network_enabled, request.active))


def validate_specialist_routing_gate_closed(gate: SpecialistRoutingGate) -> bool:
    return (
        gate.human_approval_required
        and not gate.human_approval_present
        and not any((gate.routing_enabled, gate.provider_calls_enabled, gate.network_enabled, gate.merge_protocol_integration_enabled))
    )


def validate_specialist_provider_contract_inactive(contract: SpecialistProviderContract) -> bool:
    return not any(
        (
            contract.active,
            contract.provider_calls_enabled,
            contract.network_enabled,
            contract.authority_granted,
            contract.may_write_memory,
            contract.may_mutate_runtime,
            contract.may_execute_actions,
        )
    )


def validate_specialist_routing_decision_report_only(decision: SpecialistRoutingDecision) -> bool:
    return (
        not any(
            (
                decision.applied,
                decision.provider_called,
                decision.routing_executed,
                decision.network_used,
                decision.memory_written,
                decision.canonical_written,
                decision.merge_protocol_invoked,
            )
        )
        and all(value is False for value in decision.invariant_flags.values())
    )


def validate_specialist_routing_trace_review_only(trace: SpecialistRoutingTrace) -> bool:
    return trace.generated_for_review_only and not any((trace.applied, trace.provider_called, trace.memory_written))


def validate_specialist_routing_plan_inert(plan: SpecialistRoutingPlan) -> bool:
    return (
        not any(
            (
                plan.routing_enabled,
                plan.provider_calls_enabled,
                plan.network_enabled,
                plan.human_approval_gate_enabled,
                plan.merge_protocol_integration_enabled,
                plan.memory_mutation_enabled,
                plan.execution_enabled,
            )
        )
        and all(value is False for value in plan.invariant_flags.values())
    )


def validate_specialist_routing_report_entry_review_only(entry: SpecialistRoutingReportEntry) -> bool:
    return entry.generated_for_review_only


def _default_specialist_for_kind(request_kind: SpecialistRoutingRequestKind) -> SpecialistType:
    mapping = {
        SpecialistRoutingRequestKind.EVIDENCE_GAP: SpecialistType.EVIDENCE_SPECIALIST,
        SpecialistRoutingRequestKind.CONTRADICTION_CHECK: SpecialistType.CONTRADICTION_SPECIALIST,
        SpecialistRoutingRequestKind.CITATION_CHECK: SpecialistType.CITATION_SPECIALIST,
        SpecialistRoutingRequestKind.MATH_CHECK: SpecialistType.MATH_SPECIALIST,
        SpecialistRoutingRequestKind.CODE_CHECK: SpecialistType.CODE_SPECIALIST,
        SpecialistRoutingRequestKind.POLICY_CHECK: SpecialistType.POLICY_SPECIALIST,
        SpecialistRoutingRequestKind.DOMAIN_CHECK: SpecialistType.GENERALIST_REVIEW,
        SpecialistRoutingRequestKind.SAFETY_CHECK: SpecialistType.SAFETY_SPECIALIST,
        SpecialistRoutingRequestKind.UNKNOWN_RESOLUTION: SpecialistType.UNKNOWN_SPECIALIST,
    }
    return mapping[request_kind]


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
