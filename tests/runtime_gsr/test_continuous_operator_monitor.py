import json
from pathlib import Path

from orchestration.runtime.continuous_operator_monitor import (
    MonitorNotificationMemory,
    application_action_for_option,
    build_operator_interaction_requests,
    classify_monitor_event,
    load_monitor_snapshot,
    render_monitor_summary,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _supervisor_root(tmp_path: Path) -> Path:
    root = tmp_path / "supervisor"
    root.mkdir()
    _write_json(
        root / "worker_status.json",
        {
            "worker_state": "worker_running",
            "timestamp": "2026-07-15T20:10:00Z",
            "continuous_mission_state": "running",
        },
    )
    _write_json(
        root / "restart_state.json",
        {
            "continuous_mission_state": "running",
            "continuous_main_goal": {
                "normalized_objective": "improve transfer validation",
                "next_main_goal_candidates": [
                    "improve transfer validation",
                    "goal-a",
                    "source diversity",
                    "communication calibration",
                ],
            },
            "continuous_active_subgoal": {
                "measurable_objective": "prove transfer across held-out records",
            },
            "continuous_completed_main_goals": ["goal-a", "goal-b"],
            "continuous_knowledge_ledger": ["record-a", "record-b", "record-c"],
            "continuous_developmental_self_assessment": {
                "confidence": 0.7,
                "needs_additional_insight": True,
                "developmental_gaps": ["missing tracked integration proof"],
            },
            "continuous_api_authority": {"enabled": False},
        },
    )
    _write_json(root / "observation_requeue.json", {"timestamp": "2026-07-15T20:09:00Z"})
    return root


def test_monitor_snapshot_reads_runtime_artifacts(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)

    snapshot = load_monitor_snapshot(root)

    assert snapshot.worker_state == "worker_running"
    assert snapshot.mission_state == "running"
    assert snapshot.main_goal == "improve transfer validation"
    assert snapshot.active_subgoal == "prove transfer across held-out records"
    assert snapshot.completed_main_goals == 2
    assert snapshot.knowledge_records == 3
    assert snapshot.developmental_gaps == ("missing tracked integration proof",)
    assert snapshot.completed_main_goal_ids == ("goal-a", "goal-b")
    assert snapshot.next_candidates == ("source diversity", "communication calibration")


def test_monitor_classifies_pending_application_as_operator_boundary(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["pending_application_decision_id"] = "apply-candidate-001"
    _write_json(state_path, state)

    event = classify_monitor_event(load_monitor_snapshot(root))

    assert event.event_type == "operator_application_decision_required"
    assert event.severity == "high"
    assert "apply-candidate-001" in event.summary


def test_monitor_classifies_active_subgoal_without_operator_action(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)

    event = classify_monitor_event(load_monitor_snapshot(root))

    assert event.event_type == "active_subgoal_running"
    assert event.severity == "normal"
    assert "prove transfer" in event.summary


def test_monitor_classifies_observation_with_unresolved_gaps(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["continuous_mission_state"] = "observing_for_new_weaknesses"
    state["continuous_active_subgoal"] = {}
    _write_json(state_path, state)

    event = classify_monitor_event(load_monitor_snapshot(root))

    assert event.event_type == "observation_with_unresolved_gaps"
    assert event.severity == "medium"
    assert "missing tracked integration proof" in event.summary


def test_identical_observation_polls_alert_once_and_track_repeats(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["continuous_mission_state"] = "observing_for_new_weaknesses"
    state["continuous_active_subgoal"] = {}
    _write_json(state_path, state)
    memory = MonitorNotificationMemory()

    event = classify_monitor_event(load_monitor_snapshot(root))
    first = memory.record(event, now="2026-07-15T20:10:00Z")
    second = memory.record(event, now="2026-07-15T20:10:05Z")

    assert first.should_alert is True
    assert first.repeat_count == 1
    assert second.should_alert is False
    assert second.repeat_count == 2


def test_heartbeat_changes_do_not_create_new_observation_event(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["continuous_mission_state"] = "observing_for_new_weaknesses"
    state["continuous_active_subgoal"] = {}
    _write_json(state_path, state)
    first_event = classify_monitor_event(load_monitor_snapshot(root))

    worker_path = root / "worker_status.json"
    worker = json.loads(worker_path.read_text(encoding="utf-8"))
    worker["timestamp"] = "2026-07-15T20:11:00Z"
    _write_json(worker_path, worker)
    second_event = classify_monitor_event(load_monitor_snapshot(root))

    assert second_event.signature == first_event.signature


def test_changed_gap_creates_new_observation_event(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["continuous_mission_state"] = "observing_for_new_weaknesses"
    state["continuous_active_subgoal"] = {}
    _write_json(state_path, state)
    first_event = classify_monitor_event(load_monitor_snapshot(root))

    state["continuous_developmental_self_assessment"]["developmental_gaps"].append("new transfer caveat")
    _write_json(state_path, state)
    second_event = classify_monitor_event(load_monitor_snapshot(root))

    assert second_event.signature != first_event.signature


def test_stall_escalation_occurs_once_for_repeated_observation(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["continuous_mission_state"] = "observing_for_new_weaknesses"
    state["continuous_active_subgoal"] = {}
    _write_json(state_path, state)
    event = classify_monitor_event(load_monitor_snapshot(root))
    memory = MonitorNotificationMemory()

    receipts = [memory.record(event, now=f"2026-07-15T20:10:0{idx}Z", stall_repeat_threshold=3) for idx in range(5)]

    assert [receipt.should_alert for receipt in receipts] == [True, False, True, False, False]
    assert receipts[2].event.event_type == "observation_stalled_without_new_evidence"


def test_needs_insight_creates_evidence_only_request_not_authority(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["continuous_mission_state"] = "awaiting_operator_insight"
    state["continuous_active_subgoal"] = {}
    state["continuous_developmental_insight_requests"] = [
        {
            "request_id": "insight-001",
            "request_kind": "insight",
            "status": "pending",
            "exact_question": "Should this caveat remain an active development gap?",
            "rationale": "The answer changes prioritization.",
            "affected_main_goal": "improve transfer validation",
            "affected_gap": "missing tracked integration proof",
            "blocked_transition": "observation -> next developmental priority",
            "authority_scope": "none; ordinary insight text grants no authority",
            "permitted_responses": ["continue local simulation only", "treat as accepted boundary"],
            "authority_granted": False,
        }
    ]
    _write_json(state_path, state)

    requests = build_operator_interaction_requests(load_monitor_snapshot(root))

    assert len(requests) == 1
    request = requests[0]
    assert request.request_kind == "insight"
    assert request.authority_scope == "none; ordinary insight text grants no authority"
    assert request.authority_granted is False


def test_consumed_interaction_is_not_rendered_as_a_live_operator_button(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["continuous_mission_state"] = "awaiting_operator_insight"
    state["continuous_developmental_insight_requests"] = [
        {
            "request_id": "insight-consumed",
            "request_kind": "insight",
            "status": "consumed",
            "exact_question": "Old question that must remain historical only.",
            "permitted_responses": ["defer"],
        },
        {
            "request_id": "insight-pending",
            "request_kind": "insight",
            "status": "pending",
            "exact_question": "The one current question.",
            "permitted_responses": ["defer"],
        },
    ]
    _write_json(state_path, state)

    requests = build_operator_interaction_requests(load_monitor_snapshot(root))

    assert [item.request_id for item in requests] == ["insight-pending"]


def test_pending_application_request_is_authority_scoped(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["pending_application_decision_id"] = "apply-candidate-001"
    _write_json(state_path, state)

    request = build_operator_interaction_requests(load_monitor_snapshot(root))[0]

    assert request.request_kind == "application_review"
    assert request.priority == "high"
    assert request.authority_scope == "one-time exact tracked-source application only"


def test_application_review_buttons_map_to_existing_application_actions() -> None:
    assert application_action_for_option("Approve Once") == "APPLY_VALIDATED_CANDIDATE"
    assert application_action_for_option("Reject") == "REJECT_CANDIDATE"
    assert application_action_for_option("Request Revision") == "REQUEST_REVISION"
    assert application_action_for_option("Defer") == "CONTINUE_SANDBOX_RESEARCH"


def test_monitor_renders_copyable_summary_with_grounded_state(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    snapshot = load_monitor_snapshot(root)
    summary = render_monitor_summary(snapshot, classify_monitor_event(snapshot))

    assert "Subgoal Running" in summary
    assert "Main goal: improve transfer validation" in summary
    assert "Active subgoal: prove transfer across held-out records" in summary
    assert "Operator Inbox" in summary
    assert "Supervisor root:" in summary


def test_monitor_renders_read_only_learning_trace_without_provider_payloads(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    state_path = root / "restart_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["continuous_learning_state"] = {
        "mission": {"mission_id": "mission-001", "topic": "spectral_theorem"},
        "retained_bundle": {"source_type": "authorized_external_research", "resource_status": "provisional"},
        "isolated_evaluator_authoring": {
            "pending_request": {
                "request_id": "evaluator-001",
                "status": "pending_operator_approval",
                "provider": "openai",
                "user_prompt": "must never be rendered",
            }
        },
    }
    _write_json(state_path, state)

    summary = render_monitor_summary(load_monitor_snapshot(root), classify_monitor_event(load_monitor_snapshot(root)))

    assert "Live Runtime Trace" in summary
    assert "MISSION: spectral_theorem | target=mission-001" in summary
    assert "EVALUATOR GATE: pending_operator_approval | request=evaluator-001 | provider=openai" in summary
    assert "must never be rendered" not in summary


def test_monitor_reads_do_not_mutate_runtime_artifacts(tmp_path: Path) -> None:
    root = _supervisor_root(tmp_path)
    before = {path.name: path.read_text(encoding="utf-8") for path in root.iterdir()}

    snapshot = load_monitor_snapshot(root)
    event = classify_monitor_event(snapshot)
    render_monitor_summary(snapshot, event)

    after = {path.name: path.read_text(encoding="utf-8") for path in root.iterdir()}
    assert after == before
