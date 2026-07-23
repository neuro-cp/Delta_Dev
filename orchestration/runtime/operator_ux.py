"""Human-facing operator UX adapters over governed runtime records."""

from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


FIXED_TIMESTAMP = "2026-07-22T00:00:00+00:00"

APPROVAL_TEXT = {
    "yes",
    "approve",
    "approved",
    "go ahead",
    "do it",
    "that's fine",
    "thats fine",
    "proceed",
}
REJECTION_TEXT = {"no", "decline", "deny", "don't do that", "dont do that", "stop", "not now"}
EXPLANATION_TEXT = {
    "explain",
    "why",
    "why do you need that",
    "what does this mean",
    "i don't understand",
    "i dont understand",
    "can you simplify that",
}
PAUSE_TEXT = {"pause", "wait", "hold on", "leave it paused", "ask me later"}

HUMAN_STATE_LABELS = {
    "blocked_operator_authority": "Waiting for your approval",
    "blocked_learning_required": "A new capability is needed",
    "waiting_dependency": "Waiting for another task",
    "waiting_dependencies": "Waiting for another task",
    "integrity_stop": "Stopped because an integrity check failed",
    "skipped_by_operator": "Skipped at your request",
    "completed": "Completed",
    "failed": "Could not complete",
    "queued": "Planning",
    "ready": "Ready",
    "running": "Working",
    "terminal": "Completed",
    "paused": "Paused",
}


def digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    data = dict(payload)
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return data


def normalize_operator_intent(text: str) -> dict[str, str]:
    normalized = " ".join(text.strip().lower().replace("’", "'").split())
    if normalized in APPROVAL_TEXT:
        intent = "approve"
    elif normalized in REJECTION_TEXT:
        intent = "decline"
    elif normalized in EXPLANATION_TEXT:
        intent = "explain"
    elif normalized in PAUSE_TEXT:
        intent = "pause"
    else:
        intent = "ambiguous"
    return {
        "schema": "operator_ux_intent_v1",
        "raw_text": text,
        "normalized_text": normalized,
        "intent": intent,
        "requires_clarification": intent == "ambiguous",
    }


def human_state_label(state: str) -> str:
    return HUMAN_STATE_LABELS.get(str(state), str(state).replace("_", " ").strip().capitalize() or "Unknown")


def compile_operator_request_card(request: Mapping[str, Any]) -> dict[str, Any]:
    details = dict(request.get("details") or {})
    card = {
        "schema": "operator_ux_request_card_v1",
        "request_id": request["request_id"],
        "title": str(request.get("title") or "I need your approval"),
        "what_delta_wants": str(request.get("what_delta_wants") or request.get("action") or "Continue this goal."),
        "why": str(request.get("why") or "This step needs your decision before DELTA can continue."),
        "missing_information_or_capability": str(request.get("missing_information_or_capability") or details.get("missing_capability") or "No extra capability named."),
        "files_or_resources": tuple(request.get("files_or_resources") or ()),
        "may_change": str(request.get("may_change") or "Nothing outside the disposable mission artifacts."),
        "provider_or_network_use": str(request.get("provider_or_network_use") or "No provider calls or network expansion."),
        "learning_attempts": int(request.get("learning_attempts") or 0),
        "limits": dict(request.get("limits") or {}),
        "recommended_action": str(request.get("recommended_action") or "Approve"),
        "if_declined": str(request.get("if_declined") or "The blocked branch will remain unresolved or be skipped."),
        "buttons": ("Approve", "Decline", "Explain", "Change limits", "Pause goal"),
        "technical_details_hidden": True,
        "technical_details": {
            key: request.get(key)
            for key in ("request_id", "authority_id", "authority_digest", "approval_token", "mission_id", "work_item_id")
            if request.get(key)
        },
    }
    return digest_record(card)


def explain_operator_request(request: Mapping[str, Any]) -> str:
    card = compile_operator_request_card(request)
    return (
        f"{card['what_delta_wants']}\n\n"
        f"Why it is needed: {card['why']}\n"
        f"Access required: {card['provider_or_network_use']}; files/resources: {', '.join(card['files_or_resources']) or 'none listed'}.\n"
        f"What could change: {card['may_change']}\n"
        "What will not happen: no deployment, credential use, trusted admission, capability promotion, or hidden source mutation.\n"
        f"If you decline: {card['if_declined']}"
    )


def compile_formal_operator_response(request: Mapping[str, Any], intent: Mapping[str, Any], *, response_source: str) -> dict[str, Any]:
    if intent.get("intent") not in {"approve", "decline", "pause"}:
        raise ValueError("operator_ux_response_requires_decision_intent")
    disposition = {"approve": "approved", "decline": "declined", "pause": "paused"}[str(intent["intent"])]
    return digest_record({
        "schema": "operator_ux_formal_response_v1",
        "response_id": stable_id("operator-ux-response", request["request_id"], disposition, response_source),
        "request_id": request["request_id"],
        "request_digest": request["artifact_digest"],
        "operator_intent": intent["intent"],
        "formal_disposition": disposition,
        "response_source": response_source,
        "consumed": False,
        "created_at": FIXED_TIMESTAMP,
    })


def consume_formal_operator_response(response: Mapping[str, Any]) -> dict[str, Any]:
    if response.get("consumed") is True:
        raise ValueError("operator_ux_response_already_consumed")
    return digest_record({
        **{key: value for key, value in response.items() if key != "artifact_digest"},
        "consumed": True,
        "consumed_at": FIXED_TIMESTAMP,
        "consumption_id": stable_id("operator-ux-response-consumption", response["response_id"], response["request_digest"]),
    })


def compile_narration_event(
    *,
    mission_id: str,
    work_item_id: str = "",
    phase: str,
    event_type: str,
    message: str,
    source_artifact: str,
) -> dict[str, Any]:
    return digest_record({
        "schema": "operator_ux_narration_event_v1",
        "event_id": stable_id("operator-ux-narration", mission_id, work_item_id, phase, event_type, source_artifact),
        "mission_id": mission_id,
        "work_item_id": work_item_id,
        "runtime_phase": phase,
        "event_type": event_type,
        "message": message,
        "source_artifact": source_artifact,
        "timestamp": FIXED_TIMESTAMP,
        "chain_of_thought_exposed": False,
    })


def narration_from_live_runtime_state(state: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    mission = dict(state.get("mission") or {})
    mission_id = str(mission.get("mission_id") or "pending")
    status_by_label = dict(state.get("work_item_status") or {})
    work_items = {str(item.get("label")): str(item.get("work_item_id") or "") for item in tuple(state.get("work_items") or ())}
    messages = [
        ("goal_recognized", "mission_registered", "", "I understand the current supported goal and am tracking it as one governed mission."),
        ("planning", "work_graph_registered", "", "I divided this into CSV validation, JSON validation, reconciliation, and a final report."),
    ]
    if status_by_label.get("csv_validation") == "completed":
        messages.append(("working", "csv_completed", work_items.get("csv_validation", ""), "CSV validation completed. A validated result is available."))
    if status_by_label.get("json_validation") == "completed":
        messages.append(("working", "json_completed", work_items.get("json_validation", ""), "JSON validation completed using a declared adapter capability."))
    if status_by_label.get("cross_format_reconciliation") in {"ready", "completed"}:
        messages.append(("capability_check", "reconciliation_ready", work_items.get("cross_format_reconciliation", ""), "A validated reconciliation capability is available for this mission."))
    if status_by_label.get("dynamic_synthesis") in {"waiting_dependencies", "waiting_dependency"}:
        messages.append(("waiting", "dynamic_synthesis_waiting", work_items.get("dynamic_synthesis", ""), "I am waiting for the remaining task before producing the final report."))
    if state.get("status") == "terminal":
        messages.append(("completed", "terminal", "", "The goal is complete. Four validated results are available in Evaluation."))
    return tuple(
        compile_narration_event(
            mission_id=mission_id,
            work_item_id=work_item_id,
            phase=phase,
            event_type=event_type,
            message=message,
            source_artifact=bootstrap_digest({"phase": phase, "status": status_by_label, "scheduler_cycles": state.get("scheduler_cycles")}),
        )
        for event_type, phase, work_item_id, message in messages
    )


def goal_card_from_live_runtime_state(state: Mapping[str, Any]) -> dict[str, Any]:
    mission = dict(state.get("mission") or {})
    status_by_label = dict(state.get("work_item_status") or {})
    completed = sum(1 for value in status_by_label.values() if value == "completed")
    total = len(status_by_label) or 4
    if state.get("status") == "terminal":
        state_text = "Completed"
    elif any(value in {"blocked_operator_authority", "blocked_learning_required"} for value in status_by_label.values()):
        state_text = "Waiting for you"
    elif any(value in {"waiting_dependencies", "waiting_dependency"} for value in status_by_label.values()):
        state_text = "Working"
    else:
        state_text = "Planning" if completed == 0 else "Working"
    return digest_record({
        "schema": "operator_ux_goal_card_v1",
        "goal_id": stable_id("operator-ux-goal", mission.get("mission_id") or "pending"),
        "mission_id": mission.get("mission_id") or "",
        "title": "Compare customer records",
        "objective": mission.get("objective") or "Validate CSV and JSON records, reconcile them, and produce a final report.",
        "state": state_text,
        "progress_completed": completed,
        "progress_total": total,
        "current_activity": human_state_label(next((value for value in status_by_label.values() if value != "completed"), state.get("status") or "queued")),
        "next_expected_action": "Review Evaluation results" if state.get("status") == "terminal" else "Continue the next eligible task",
        "unresolved_issue": "" if state.get("status") == "terminal" else "Some tasks are not complete yet.",
        "capability_source": "Learned CSV competence, declared JSON adapter, validated bootstrap reasoning, and governed reconciliation competence where available.",
        "last_update": FIXED_TIMESTAMP,
        "technical_details_hidden": True,
    })


def audit_rc_tabs() -> dict[str, Any]:
    return {
        "RC3": {
            "displays": "Capability panel diagnostics from RC3 snapshot builders.",
            "active_workflow_dependency": False,
            "safe_destination": "Developer diagnostics",
        },
        "RC4": {
            "displays": "Governed action runtime diagnostics and report generation.",
            "active_workflow_dependency": False,
            "safe_destination": "Developer diagnostics",
        },
        "RC5": {
            "displays": "Purpose-aligned developmental cognition diagnostics and manual consultation packet status.",
            "active_workflow_dependency": False,
            "safe_destination": "Developer diagnostics",
        },
    }
