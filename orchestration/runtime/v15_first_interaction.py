from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_runtime_console import RuntimeConsolePreview, build_runtime_console_preview


STARTER_DELTA_QUESTION = "What is DELTA's current replay and consolidation path?"

RUNTIME_V15D_INVARIANT_FLAGS: dict[str, bool] = {
    "first_live_console_interaction_enabled": True,
    "runtime_console_gate_open": True,
    "only_runtime_console_gate_open": True,
    "provider_calls_enabled": False,
    "tool_calls_enabled": False,
    "memory_mutation_enabled": False,
    "canonical_write_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
    "specialist_routing_enabled": False,
    "action_execution_enabled": False,
    "dry_run_action_execution_enabled": False,
    "training_enabled": False,
    "dataset_export_enabled": False,
    "scheduler_enabled": False,
    "background_ingestion_enabled": False,
    "runtime_defaults_changed": False,
}


class FirstInteractionResponseMode(str, Enum):
    LOCAL_ARCHITECTURE_SUMMARY = "local_architecture_summary"
    LOCAL_UNKNOWN_SCAFFOLD_NOTICE = "local_unknown_scaffold_notice"


@dataclass(frozen=True)
class FirstInteractionRequest:
    request_id: str
    user_message: str
    source: str = "manual_console"
    one_shot: bool = True
    auto_ingest: bool = False
    training_example: bool = False
    memory_write_requested: bool = False
    provider_call_requested: bool = False
    action_execution_requested: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class FirstInteractionGateStatus:
    gate_status_id: str
    runtime_console_gate_open: bool
    allowed_components: tuple[str, ...]
    blocked_components: tuple[str, ...]
    model_b_default_preserved: bool = True
    hyb1_default_activation_enabled: bool = False
    provider_calls_enabled: bool = False
    memory_writes_enabled: bool = False
    action_execution_enabled: bool = False
    training_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class FirstInteractionSafetyStatus:
    safety_status_id: str
    request_id: str
    provider_calls_enabled: bool = False
    tool_calls_enabled: bool = False
    memory_mutation_enabled: bool = False
    canonical_write_enabled: bool = False
    runtime_recall_mutation_enabled: bool = False
    hyb1_default_activation_enabled: bool = False
    specialist_routing_enabled: bool = False
    action_execution_enabled: bool = False
    training_enabled: bool = False
    scheduler_enabled: bool = False
    side_effects_created: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class FirstInteractionResponsePreview:
    response_preview_id: str
    request_id: str
    response_text: str
    response_mode: FirstInteractionResponseMode
    uncertainty_note: str = ""
    evidence_summary: str = ""
    deterministic_local: bool = True
    provider_generated: bool = False
    model_default_changed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class FirstInteractionTrace:
    trace_id: str
    request_id: str
    experience_preview_id: str = ""
    semantic_preview_id: str = ""
    safety_status_id: str = ""
    response_preview_id: str = ""
    generated_for_manual_interaction: bool = True
    persisted_to_memory: bool = False
    persisted_to_canonical_store: bool = False
    provider_called: bool = False
    action_executed: bool = False
    training_triggered: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class FirstInteractionResult:
    result_id: str
    request_id: str
    trace_id: str
    response_preview_id: str
    safety_status_id: str
    completed: bool = True
    manual_only: bool = True
    local_only: bool = True
    deterministic_only: bool = True
    provider_called: bool = False
    action_executed: bool = False
    memory_mutated: bool = False
    training_triggered: bool = False
    side_effects_created: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class FirstInteractionReportEntry:
    report_entry_id: str
    result_id: str
    request_summary: str
    gate_summary: str
    trace_summary: str
    response_summary: str
    safety_summary: str
    unresolved_gaps: tuple[str, ...]
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_first_interaction_request(user_message: str) -> FirstInteractionRequest:
    message = " ".join(str(user_message).split())
    return FirstInteractionRequest(request_id=_stable_id("first-interaction-request", message), user_message=message)


def create_first_interaction_gate_status(request: FirstInteractionRequest) -> FirstInteractionGateStatus:
    return FirstInteractionGateStatus(
        gate_status_id=_stable_id("first-interaction-gate", request.request_id),
        runtime_console_gate_open=True,
        allowed_components=("manual console message", "raw experience preview", "semantic preview", "trace/safety output", "deterministic response preview"),
        blocked_components=("provider calls", "tool calls", "memory writes", "canonical writes", "recall mutation", "HYB1 default activation", "specialist routing", "action execution", "training", "dataset export", "schedulers"),
    )


def create_first_interaction_safety_status(request: FirstInteractionRequest) -> FirstInteractionSafetyStatus:
    return FirstInteractionSafetyStatus(safety_status_id=_stable_id("first-interaction-safety", request.request_id), request_id=request.request_id)


def create_first_interaction_response_preview(request: FirstInteractionRequest, console_preview: RuntimeConsolePreview) -> FirstInteractionResponsePreview:
    lowered = request.user_message.lower()
    if "replay" in lowered and "consolidation" in lowered and "delta" in lowered:
        mode = FirstInteractionResponseMode.LOCAL_ARCHITECTURE_SUMMARY
        response = (
            "DELTA's current replay and consolidation path is: manual/raw message -> experience boundary/record -> "
            "episodic feedback capture -> replay markers/batches -> replay review -> consolidation candidate -> "
            "consolidation decision -> sleep-cycle plan -> canonical memory draft/record design. Canonical writes remain disabled."
        )
        evidence = "local V1.4 scaffold summary: experience adapter, feedback capture, replay, consolidation, sleep-cycle, canonical design"
        uncertainty = "This is a deterministic local scaffold summary, not provider reasoning."
    else:
        mode = FirstInteractionResponseMode.LOCAL_UNKNOWN_SCAFFOLD_NOTICE
        response = (
            "I cannot answer that from the local DELTA scaffold yet. I generated a manual console trace and safety status, "
            "but provider calls, memory writes, action execution, training, and HYB1 default activation remain disabled."
        )
        evidence = f"semantic preview: {console_preview.semantic_frame.normalized_summary}"
        uncertainty = "Knowledge retrieval/provider reasoning is not active in this path."
    return FirstInteractionResponsePreview(
        response_preview_id=_stable_id("first-interaction-response", request.request_id, response, mode.value),
        request_id=request.request_id,
        response_text=response,
        response_mode=mode,
        uncertainty_note=uncertainty,
        evidence_summary=evidence,
    )


def build_first_interaction_result(user_message: str) -> dict[str, object]:
    request = create_first_interaction_request(user_message)
    gate = create_first_interaction_gate_status(request)
    console_preview = build_runtime_console_preview(request.user_message, source_reference="manual-v15-first-interaction")
    safety = create_first_interaction_safety_status(request)
    response = create_first_interaction_response_preview(request, console_preview)
    trace = FirstInteractionTrace(
        trace_id=_stable_id("first-interaction-trace", request.request_id, console_preview.preview_id, safety.safety_status_id, response.response_preview_id),
        request_id=request.request_id,
        experience_preview_id=console_preview.experience_record.record_id,
        semantic_preview_id=console_preview.semantic_frame.frame_id,
        safety_status_id=safety.safety_status_id,
        response_preview_id=response.response_preview_id,
    )
    result = FirstInteractionResult(
        result_id=_stable_id("first-interaction-result", request.request_id, trace.trace_id, response.response_preview_id, safety.safety_status_id),
        request_id=request.request_id,
        trace_id=trace.trace_id,
        response_preview_id=response.response_preview_id,
        safety_status_id=safety.safety_status_id,
    )
    entry = FirstInteractionReportEntry(
        report_entry_id=_stable_id("first-interaction-entry", result.result_id),
        result_id=result.result_id,
        request_summary=request.user_message,
        gate_summary="only runtime console gate open",
        trace_summary="experience and semantic preview generated without persistence",
        response_summary=response.response_mode.value,
        safety_summary="provider/tool/action/memory/training paths disabled",
        unresolved_gaps=("retrieval not active", "provider reasoning not active", "memory writes disabled"),
        recommended_next_review_step="V1.5E HYB1 limited opt-in trial design",
    )
    return {
        "request": request.as_dict(),
        "gate_status": gate.as_dict(),
        "console_preview": console_preview.as_dict(),
        "safety_status": safety.as_dict(),
        "response_preview": response.as_dict(),
        "trace": trace.as_dict(),
        "result": result.as_dict(),
        "report_entry": entry.as_dict(),
        "invariant_flags": dict(RUNTIME_V15D_INVARIANT_FLAGS),
    }


def validate_first_interaction_result_safe(data: dict[str, object]) -> bool:
    request = data["request"]
    gate = data["gate_status"]
    safety = data["safety_status"]
    trace = data["trace"]
    result = data["result"]
    flags = data["invariant_flags"]
    return (
        isinstance(request, dict)
        and request["one_shot"] is True
        and request["auto_ingest"] is False
        and gate["runtime_console_gate_open"] is True
        and safety["provider_calls_enabled"] is False
        and trace["persisted_to_memory"] is False
        and trace["persisted_to_canonical_store"] is False
        and result["provider_called"] is False
        and result["action_executed"] is False
        and result["memory_mutated"] is False
        and result["training_triggered"] is False
        and flags["first_live_console_interaction_enabled"] is True
        and flags["only_runtime_console_gate_open"] is True
        and all(value is False for key, value in flags.items() if key not in {"first_live_console_interaction_enabled", "runtime_console_gate_open", "only_runtime_console_gate_open"})
    )


def format_first_interaction_cli_output(data: dict[str, object]) -> str:
    response = data["response_preview"]
    trace = data["trace"]
    safety = data["safety_status"]
    flags = data["invariant_flags"]
    return "\n".join(
        [
            "DELTA First Interaction Preview",
            "",
            str(response["response_text"]),
            "",
            "Trace:",
            f"- trace_id: {trace['trace_id']}",
            f"- experience_preview_id: {trace['experience_preview_id']}",
            f"- semantic_preview_id: {trace['semantic_preview_id']}",
            f"- persisted_to_memory: {trace['persisted_to_memory']}",
            f"- persisted_to_canonical_store: {trace['persisted_to_canonical_store']}",
            "",
            "Safety:",
            f"- provider_calls_enabled: {safety['provider_calls_enabled']}",
            f"- tool_calls_enabled: {safety['tool_calls_enabled']}",
            f"- action_execution_enabled: {safety['action_execution_enabled']}",
            f"- training_enabled: {safety['training_enabled']}",
            f"- canonical_write_enabled: {safety['canonical_write_enabled']}",
            f"- runtime_recall_mutation_enabled: {safety['runtime_recall_mutation_enabled']}",
            f"- hyb1_default_activation_enabled: {safety['hyb1_default_activation_enabled']}",
            f"- model_b_default_changed: {flags['model_b_default_changed']}",
            "",
            "Status: local deterministic console-only preview; no provider calls, no actions, no memory writes, no training.",
        ]
    )


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
    digest = hashlib.sha256("|".join(_normalize_part(part) for part in parts).encode("utf-8")).hexdigest()[:16]
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
