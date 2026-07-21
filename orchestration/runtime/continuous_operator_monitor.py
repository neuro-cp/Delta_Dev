"""Read-only operator monitor for continuous developmental runtime artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKER_STATUS = "worker_status.json"
RESTART_STATE = "restart_state.json"
OBSERVATION_REQUEUE = "observation_requeue.json"
OPERATOR_APPLICATION_DECISION = "operator_application_decision.json"
OPERATOR_INTERACTION_RESPONSE = "operator_interaction_response.json"


@dataclass(frozen=True)
class ContinuousMonitorSnapshot:
    supervisor_root: str
    worker_state: str
    status_timestamp: str
    mission_state: str
    main_goal: str
    active_subgoal: str
    completed_main_goal_ids: tuple[str, ...]
    completed_main_goals: int
    knowledge_records: int
    pending_application_decision_id: str
    api_enabled: bool
    developmental_gaps: tuple[str, ...]
    confidence: float | None
    needs_additional_insight: bool
    next_candidates: tuple[str, ...]
    operator_interaction_requests: tuple[dict[str, Any], ...]
    observation_timestamp: str
    runtime_trace: tuple[str, ...] = ()
    process_hint: str = "artifact_read_only"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContinuousMonitorEvent:
    event_type: str
    severity: str
    title: str
    summary: str
    action_hint: str
    signature: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class OperatorInteractionRequest:
    request_id: str
    request_kind: str
    priority: str
    question: str
    rationale: str
    evidence_refs: tuple[str, ...]
    source_main_goal: str
    source_subgoal: str
    blocked_transition: str
    authority_scope: str
    blocking_scope: str
    status: str
    created_at: str
    permitted_responses: tuple[str, ...]
    authority_granted: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NotificationReceipt:
    event: ContinuousMonitorEvent
    should_alert: bool
    first_seen_at: str
    last_seen_at: str
    repeat_count: int


class MonitorNotificationMemory:
    """In-memory popup dedupe for one monitor process."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._escalated_signatures: set[str] = set()

    def record(
        self,
        event: ContinuousMonitorEvent,
        *,
        now: str | None = None,
        stall_repeat_threshold: int = 6,
    ) -> NotificationReceipt:
        timestamp = now or datetime.now(timezone.utc).isoformat()
        record = self._records.get(event.signature)
        if record is None:
            self._records[event.signature] = {
                "first_seen_at": timestamp,
                "last_seen_at": timestamp,
                "repeat_count": 1,
            }
            return NotificationReceipt(event, True, timestamp, timestamp, 1)
        record["last_seen_at"] = timestamp
        record["repeat_count"] = max(1, int(record.get("repeat_count") or 0)) + 1
        repeat_count = max(1, int(record["repeat_count"]))
        if (
            event.event_type == "observation_with_unresolved_gaps"
            and repeat_count >= stall_repeat_threshold
            and event.signature not in self._escalated_signatures
        ):
            self._escalated_signatures.add(event.signature)
            escalated = ContinuousMonitorEvent(
                event_type="observation_stalled_without_new_evidence",
                severity="medium",
                title="Observation Stalled Without New Evidence",
                summary=f"No material observation change after {repeat_count} equivalent reads.",
                action_hint="Review the Operator Inbox if a concrete question exists; otherwise let the runtime continue quietly.",
                signature=f"stall:{event.signature}",
            )
            self._records[escalated.signature] = {
                "first_seen_at": timestamp,
                "last_seen_at": timestamp,
                "repeat_count": 1,
            }
            return NotificationReceipt(escalated, True, timestamp, timestamp, 1)
        return NotificationReceipt(
            event,
            False,
            str(record["first_seen_at"]),
            str(record["last_seen_at"]),
            repeat_count,
        )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def application_action_for_option(option: str) -> str:
    actions = {
        "Approve Once": "APPLY_VALIDATED_CANDIDATE",
        "Reject": "REJECT_CANDIDATE",
        "Request Revision": "REQUEST_REVISION",
        "Defer": "CONTINUE_SANDBOX_RESEARCH",
    }
    return actions[option]


def _normalize_identifier(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("normalized_objective", "goal_id", "capability_id", "objective", "id"):
            if value.get(key):
                return str(value[key]).strip()
    return str(value or "").strip()


def _completed_goal_ids(items: Any) -> tuple[str, ...]:
    return tuple(item for item in (_normalize_identifier(value) for value in (items or ())) if item)


def _filter_next_candidates(candidates: Any, *, main_goal: str, completed: tuple[str, ...]) -> tuple[str, ...]:
    blocked = {main_goal, *completed}
    filtered: list[str] = []
    for candidate in candidates or ():
        normalized = _normalize_identifier(candidate)
        if not normalized or normalized in blocked or normalized in filtered:
            continue
        filtered.append(normalized)
    return tuple(filtered)


def _confidence_bucket(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{round(value, 1):.1f}"


def _signature(*parts: Any) -> str:
    body = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _runtime_trace(restart: dict[str, Any]) -> tuple[str, ...]:
    """Return a compact, read-only explanation of the active learning lifecycle."""
    learning = restart.get("continuous_learning_state") or {}
    if not isinstance(learning, dict):
        return ()
    mission = learning.get("mission") or {}
    bundle = learning.get("retained_bundle") or {}
    authoring = learning.get("isolated_evaluator_authoring") or {}
    pending = authoring.get("pending_request") or {}
    trace: list[str] = []
    if mission:
        trace.append(
            "MISSION: "
            + str(mission.get("topic") or mission.get("primary_capability_target") or "unknown")
            + " | target="
            + str(mission.get("mission_id") or "unrecorded")
        )
    if bundle:
        trace.append(
            "LEARNING EVIDENCE: "
            + str(bundle.get("source_type") or "retained")
            + " | status="
            + str(bundle.get("resource_status") or "unknown")
        )
    if pending:
        trace.append(
            "EVALUATOR GATE: "
            + str(pending.get("status") or "unknown")
            + " | request="
            + str(pending.get("request_id") or "unrecorded")
            + " | provider="
            + str(pending.get("provider") or "unrecorded")
        )
        trace.append(
            "BOUNDARY: evaluator authoring is isolated; no learner answer, tracked-source action, or capability promotion is permitted."
        )
    policy = learning.get("developmental_resource_policy") or {}
    if policy:
        trace.append(
            "RESOURCE POLICY: " + str(policy.get("policy_state") or policy.get("status") or "recorded"))
    return tuple(trace)


def load_monitor_snapshot(supervisor_root: str | Path) -> ContinuousMonitorSnapshot:
    root = Path(supervisor_root)
    worker = _read_json(root / WORKER_STATUS)
    restart = _read_json(root / RESTART_STATE)
    observation = _read_json(root / OBSERVATION_REQUEUE)
    main_goal = restart.get("continuous_main_goal") or {}
    active = restart.get("continuous_active_subgoal") or {}
    assessment = restart.get("continuous_developmental_self_assessment") or {}
    api = restart.get("continuous_api_authority") or {}
    main_goal_name = str(main_goal.get("normalized_objective") or "")
    completed = _completed_goal_ids(restart.get("continuous_completed_main_goals") or ())
    return ContinuousMonitorSnapshot(
        supervisor_root=str(root),
        worker_state=str(worker.get("worker_state") or "unknown"),
        status_timestamp=str(worker.get("timestamp") or ""),
        mission_state=str(restart.get("continuous_mission_state") or worker.get("continuous_mission_state") or "unknown"),
        main_goal=main_goal_name,
        active_subgoal=str(active.get("measurable_objective") or ""),
        completed_main_goal_ids=completed,
        completed_main_goals=len(tuple(restart.get("continuous_completed_main_goals") or ())),
        knowledge_records=len(tuple(restart.get("continuous_knowledge_ledger") or ())),
        pending_application_decision_id=str(restart.get("pending_application_decision_id") or worker.get("pending_application_decision_id") or ""),
        api_enabled=bool(api.get("enabled")),
        developmental_gaps=tuple(str(item) for item in (assessment.get("developmental_gaps") or ())),
        confidence=float(assessment["confidence"]) if "confidence" in assessment and assessment.get("confidence") is not None else None,
        needs_additional_insight=bool(assessment.get("needs_additional_insight")),
        next_candidates=_filter_next_candidates(
            main_goal.get("next_main_goal_candidates") or (),
            main_goal=main_goal_name,
            completed=completed,
        ),
        operator_interaction_requests=tuple(
            dict(item)
            for item in (restart.get("continuous_developmental_insight_requests") or ())
            if dict(item).get("status") == "pending"
        ),
        observation_timestamp=str(observation.get("timestamp") or ""),
        runtime_trace=_runtime_trace(restart),
    )


def classify_monitor_event(snapshot: ContinuousMonitorSnapshot) -> ContinuousMonitorEvent:
    if snapshot.worker_state in {"unknown", "worker_failed_recovery"}:
        return ContinuousMonitorEvent(
            event_type="runtime_attention_required",
            severity="high",
            title="Runtime Needs Attention",
            summary=f"Worker state is {snapshot.worker_state}. Check supervisor artifacts before relying on progress.",
            action_hint="Inspect worker_status.json and restart_state.json.",
            signature=_signature("worker", snapshot.worker_state, snapshot.mission_state),
        )
    if snapshot.pending_application_decision_id:
        return ContinuousMonitorEvent(
            event_type="operator_application_decision_required",
            severity="high",
            title="Operator Decision Required",
            summary=f"Application decision pending: {snapshot.pending_application_decision_id}",
            action_hint="Review the application package before approving or rejecting tracked-source action.",
            signature=_signature("pending", snapshot.pending_application_decision_id),
        )
    if snapshot.operator_interaction_requests:
        request = dict(snapshot.operator_interaction_requests[-1])
        return ContinuousMonitorEvent(
            event_type="operator_insight_requested",
            severity="medium",
            title="Operator Insight Requested",
            summary=str(request.get("exact_question") or request.get("question") or "Operator insight is requested."),
            action_hint="Answer from the Operator Inbox. Ordinary insight grants no authority.",
            signature=_signature("operator_request", request.get("request_id"), request.get("status")),
        )
    if snapshot.api_enabled:
        return ContinuousMonitorEvent(
            event_type="api_authority_active",
            severity="medium",
            title="API Authority Active",
            summary="Runtime reports API authority enabled.",
            action_hint="Confirm provider use remains within the active authorization.",
            signature=_signature("api", "enabled"),
        )
    if snapshot.active_subgoal:
        return ContinuousMonitorEvent(
            event_type="active_subgoal_running",
            severity="normal",
            title="Subgoal Running",
            summary=f"{snapshot.active_subgoal}",
            action_hint="No operator action needed unless it reaches an application or authority boundary.",
            signature=_signature("subgoal", snapshot.main_goal, snapshot.active_subgoal),
        )
    if snapshot.mission_state == "observing_for_new_weaknesses" and snapshot.developmental_gaps:
        return ContinuousMonitorEvent(
            event_type="observation_with_unresolved_gaps",
            severity="medium",
            title="Observing With Unresolved Gaps",
            summary="Runtime is observing while developmental gaps remain: " + ", ".join(snapshot.developmental_gaps[:4]),
            action_hint="Let it continue unless the same observation repeats without new evidence.",
            signature=_signature(
                "observe_gaps",
                snapshot.mission_state,
                snapshot.main_goal,
                snapshot.active_subgoal,
                tuple(sorted(snapshot.developmental_gaps)),
                tuple(snapshot.next_candidates),
                _confidence_bucket(snapshot.confidence),
                snapshot.needs_additional_insight,
                snapshot.pending_application_decision_id,
                snapshot.knowledge_records,
            ),
        )
    if snapshot.mission_state == "observing_for_new_weaknesses":
        return ContinuousMonitorEvent(
            event_type="honest_observation",
            severity="normal",
            title="Honest Observation",
            summary="No active subgoal or pending decision is recorded.",
            action_hint="No immediate action. Watch for a new candidate goal, authority request, or stall.",
            signature=_signature("observe", snapshot.main_goal, snapshot.knowledge_records),
        )
    return ContinuousMonitorEvent(
        event_type="runtime_state_update",
        severity="normal",
        title="Runtime State Update",
        summary=f"Mission state: {snapshot.mission_state}",
        action_hint="No immediate action inferred.",
        signature=_signature("state", snapshot.mission_state, snapshot.main_goal, snapshot.active_subgoal),
    )


def build_operator_interaction_requests(snapshot: ContinuousMonitorSnapshot) -> tuple[OperatorInteractionRequest, ...]:
    if snapshot.pending_application_decision_id:
        return (
            OperatorInteractionRequest(
                request_id=snapshot.pending_application_decision_id,
                request_kind="application_review",
                priority="high",
                question="Approve or reject the pending tracked-source application package.",
                rationale="A protected tracked-source transition is blocked on explicit operator authority.",
                evidence_refs=(snapshot.pending_application_decision_id,),
                source_main_goal=snapshot.main_goal,
                source_subgoal=snapshot.active_subgoal,
                blocked_transition="validated_candidate -> tracked_source_application",
                authority_scope="one-time exact tracked-source application only",
                blocking_scope="affected application branch",
                status="pending",
                created_at=snapshot.status_timestamp,
                permitted_responses=("Approve Once", "Reject", "Request Revision", "Defer", "Inspect Evidence"),
            ),
        )
    if snapshot.mission_state != "awaiting_operator_insight":
        return ()
    requests: list[OperatorInteractionRequest] = []
    for item in snapshot.operator_interaction_requests:
        if str(item.get("status") or "pending") != "pending":
            continue
        request_kind = str(item.get("request_kind") or "insight")
        options = tuple(str(option) for option in (item.get("permitted_responses") or item.get("options") or ()))
        requests.append(
            OperatorInteractionRequest(
                request_id=str(item.get("request_id") or ""),
                request_kind=request_kind,
                priority="normal",
                question=str(item.get("exact_question") or item.get("question") or ""),
                rationale=str(item.get("rationale") or item.get("why_it_matters") or ""),
                evidence_refs=tuple(str(ref) for ref in (item.get("evidence_refs") or item.get("source_gap_ids") or ())),
                source_main_goal=str(item.get("source_main_goal") or item.get("affected_main_goal") or snapshot.main_goal),
                source_subgoal=str(item.get("source_subgoal") or snapshot.active_subgoal),
                blocked_transition=str(item.get("blocked_transition") or ""),
                authority_scope=str(item.get("authority_scope") or "none; response is evidence only"),
                blocking_scope=str(item.get("blocking_scope") or "affected reasoning branch"),
                status=str(item.get("status") or "pending"),
                created_at=str(item.get("created_at") or snapshot.status_timestamp),
                permitted_responses=options or ("continue local simulation only", "treat as accepted boundary", "defer", "ask for clarification"),
                authority_granted=bool(item.get("authority_granted")),
            )
        )
    return tuple(requests)


def render_monitor_summary(snapshot: ContinuousMonitorSnapshot, event: ContinuousMonitorEvent) -> str:
    confidence = "unknown" if snapshot.confidence is None else f"{snapshot.confidence:.2f}"
    requests = build_operator_interaction_requests(snapshot)
    lines: list[str] = []
    lines.extend(("Operator Inbox",))
    if not requests:
        lines.append("No direct operator response is required.")
    for request in requests:
        lines.extend(
            (
                "",
                f"{request.request_kind.upper()} REQUEST [{request.priority}]",
                f"Request ID: {request.request_id}",
                f"Question: {request.question}",
                f"Why: {request.rationale}",
                f"Blocked transition: {request.blocked_transition}",
                f"Authority requested: {request.authority_scope}",
                f"Blocking scope: {request.blocking_scope}",
                f"Allowed responses: {', '.join(request.permitted_responses)}",
                f"Authority granted by response: {request.authority_granted}",
            )
        )
    lines.extend(
        (
            "",
            "Runtime Status",
            event.title,
            "",
            f"Event: {event.event_type} ({event.severity})",
            f"Summary: {event.summary}",
            f"Action: {event.action_hint}",
            "",
            f"Worker: {snapshot.worker_state} at {snapshot.status_timestamp}",
            f"Mission state: {snapshot.mission_state}",
            f"Main goal: {snapshot.main_goal}",
            f"Active subgoal: {snapshot.active_subgoal or 'none'}",
            f"Completed main goals: {snapshot.completed_main_goals}",
            f"Knowledge records: {snapshot.knowledge_records}",
            f"Pending application: {snapshot.pending_application_decision_id or 'none'}",
            f"API enabled: {snapshot.api_enabled}",
            f"Confidence: {confidence}",
            f"Needs insight: {snapshot.needs_additional_insight}",
            f"Gaps: {', '.join(snapshot.developmental_gaps) if snapshot.developmental_gaps else 'none'}",
            f"Next candidates: {', '.join(snapshot.next_candidates) if snapshot.next_candidates else 'none'}",
        )
    )
    if snapshot.runtime_trace:
        lines.extend(("", "Live Runtime Trace"))
        lines.extend(snapshot.runtime_trace)
    lines.extend(("", f"Supervisor root: {snapshot.supervisor_root}"))
    return "\n".join(lines)


def launch_monitor_ui(supervisor_root: str | Path, *, poll_seconds: float = 5.0) -> None:
    import tkinter as tk
    from tkinter import ttk

    root_path = Path(supervisor_root)
    window = tk.Tk()
    window.title("DELTA Continuous Runtime Monitor")
    window.geometry("560x440")
    window.minsize(480, 360)

    status_var = tk.StringVar(value="Starting monitor...")
    title = ttk.Label(window, textvariable=status_var, font=("Segoe UI", 11, "bold"))
    title.pack(fill=tk.X, padx=10, pady=(8, 4))

    response_label = ttk.Label(window, text="Operator response")
    response_label.pack(fill=tk.X, padx=10, pady=(4, 0))
    response_box = tk.Text(window, wrap="word", height=3)
    response_box.pack(fill=tk.X, padx=10, pady=(0, 4))
    response_buttons = ttk.Frame(window)
    response_buttons.pack(fill=tk.X, padx=10, pady=(0, 8))
    dynamic_response_buttons: list[ttk.Button] = []

    frame = ttk.Frame(window)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
    scrollbar = ttk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text = tk.Text(frame, wrap="word", height=18, yscrollcommand=scrollbar.set)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text.yview)
    text.configure(state="disabled")

    notification_memory = MonitorNotificationMemory()

    def set_text(value: str) -> None:
        text.configure(state="normal")
        text.delete("1.0", tk.END)
        text.insert("1.0", value)
        text.configure(state="normal")

    def copy_summary() -> None:
        window.clipboard_clear()
        window.clipboard_append(text.get("1.0", tk.END).strip())

    def open_folder() -> None:
        os.startfile(str(root_path))

    def pending_request() -> OperatorInteractionRequest | None:
        snapshot = load_monitor_snapshot(root_path)
        requests = build_operator_interaction_requests(snapshot)
        return requests[0] if requests else None

    def submit_interaction(selected_option: str) -> None:
        request = pending_request()
        if request is None:
            set_text(text.get("1.0", tk.END).strip() + "\n\nNo pending operator interaction request is available.")
            return
        if request.request_kind == "application_review":
            if selected_option == "Inspect Evidence":
                open_folder()
                return
            _atomic_write_json(
                root_path / OPERATOR_APPLICATION_DECISION,
                {
                    "decision_id": request.request_id,
                    "action": application_action_for_option(selected_option),
                    "operator_text": response_box.get("1.0", tk.END).strip(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "authority_granted": selected_option == "Approve Once",
                    "approved_scope": request.authority_scope if selected_option == "Approve Once" else "",
                },
            )
            refresh()
            return
        payload = {
            "request_id": request.request_id,
            "response_kind": request.request_kind,
            "operator_text": response_box.get("1.0", tk.END).strip(),
            "selected_option": selected_option,
            "approved_scope": "" if request.request_kind == "insight" else request.authority_scope,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "authority_granted": request.request_kind != "insight" and selected_option.lower().startswith("approve"),
        }
        _atomic_write_json(root_path / OPERATOR_INTERACTION_RESPONSE, payload)
        refresh()

    def _button_label(option: str) -> str:
        return " ".join(part.capitalize() for part in option.replace("_", " ").split())

    def refresh_response_buttons(requests: tuple[OperatorInteractionRequest, ...]) -> None:
        for button in dynamic_response_buttons:
            button.destroy()
        dynamic_response_buttons.clear()
        if not requests:
            button = ttk.Button(response_buttons, text="No Pending Request", state="disabled")
            button.pack(side=tk.LEFT, padx=3)
            dynamic_response_buttons.append(button)
            return
        for option in requests[0].permitted_responses:
            button = ttk.Button(response_buttons, text=_button_label(option), command=lambda value=option: submit_interaction(value))
            button.pack(side=tk.LEFT, padx=3)
            dynamic_response_buttons.append(button)

    def refresh() -> None:
        try:
            snapshot = load_monitor_snapshot(root_path)
            event = classify_monitor_event(snapshot)
            receipt = notification_memory.record(event)
            status_var.set(f"{receipt.event.title} - {snapshot.mission_state} - repeats {receipt.repeat_count}")
            requests = build_operator_interaction_requests(snapshot)
            refresh_response_buttons(requests)
            set_text(render_monitor_summary(snapshot, receipt.event))
            if receipt.should_alert:
                if receipt.event.severity in {"high", "medium"}:
                    window.deiconify()
                    window.lift()
                    window.bell()
        except Exception as exc:  # noqa: BLE001 - monitor must display read errors.
            status_var.set("Monitor read error")
            set_text(f"Monitor read error: {type(exc).__name__}: {exc}\n\nSupervisor root: {root_path}")
        window.after(max(1000, int(poll_seconds * 1000)), refresh)

    buttons = ttk.Frame(window)
    buttons.pack(fill=tk.X, padx=10, pady=(4, 10))
    ttk.Button(buttons, text="Refresh", command=refresh).pack(side=tk.LEFT, padx=3)
    ttk.Button(buttons, text="Copy Summary", command=copy_summary).pack(side=tk.LEFT, padx=3)
    ttk.Button(buttons, text="Open Artifact Folder", command=open_folder).pack(side=tk.LEFT, padx=3)
    ttk.Button(buttons, text="Dismiss", command=window.destroy).pack(side=tk.RIGHT, padx=3)

    refresh()
    window.mainloop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only DELTA continuous runtime operator monitor")
    parser.add_argument("--supervisor-root", required=True)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.once:
        snapshot = load_monitor_snapshot(args.supervisor_root)
        event = classify_monitor_event(snapshot)
        print(render_monitor_summary(snapshot, event))
        return 0
    launch_monitor_ui(args.supervisor_root, poll_seconds=args.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
