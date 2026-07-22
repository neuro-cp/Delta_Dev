from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.continuous_operator_monitor import load_monitor_snapshot
from orchestration.runtime.continuous_runtime_controller import (
    LIVE_RUNTIME_1_RECONCILIATION_COMPETENCE_DIGEST,
    advance_live_runtime_1_attended_mission,
    attach_live_runtime_1_attended_mission,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    run_live_runtime_1_attended_cycles,
    start_continuous_runtime_controller,
)
from orchestration.runtime.live_general_3_learning_mission import run_live_general_3_approved_learning_mission


def _controller(session_id: str):
    return start_continuous_runtime_controller(session_id=session_id, wake_mode="MANUAL")


def _runtime_state(controller) -> dict:
    return dict(controller.continuous_learning_state["live_runtime_1"])


def _advance(controller, cycles: int):
    current = controller
    for _ in range(cycles):
        current = advance_live_runtime_1_attended_mission(current)
    return current


def _accepted_root(tmp_path: Path) -> Path:
    root = tmp_path / "accepted-general-3"
    run_live_general_3_approved_learning_mission(root=root, reset=True)
    return root


def _run(controller, tmp_path: Path, root: Path, *, max_cycles: int = 11, reset: bool = False):
    return run_live_runtime_1_attended_cycles(
        controller,
        runtime_root=root,
        accepted_competence_root=_accepted_root(tmp_path),
        max_cycles=max_cycles,
        reset=reset,
    )


def _restore(controller):
    restart = export_continuous_mission_restart_state(controller)
    fresh = _controller(controller.session_id)
    return restore_continuous_mission_restart_state(fresh, restart)


def _inventory(root: Path) -> tuple[str, ...]:
    return tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))


def test_live_runtime_1_sustained_attended_mission_reaches_terminal(tmp_path):
    root = tmp_path / "live-runtime-1"
    controller = _run(_controller("live-runtime-1-main"), tmp_path, root, reset=True)
    state = _runtime_state(controller)

    assert controller.continuous_mission_state == "live_runtime_1_terminal"
    assert state["terminal"]["terminal_status"] == "LIVE_RUNTIME_1_SUSTAINED_ATTENDED_PASSED"
    assert state["scheduler_cycles"] == 10
    assert state["phase_history"] == (
        "mission_registered",
        "work_graph_registered",
        "csv_capability_resolved",
        "json_capability_resolved",
        "reconciliation_competence_bound",
        "synthesis_capability_resolved",
        "csv_completed",
        "json_completed",
        "reconciliation_completed",
        "final_synthesis_completed",
    )
    assert len(state["work_items"]) == 4
    assert len(state["evaluation_item_ids"]) == 4
    assert state["operator_requests_created"] == 0
    assert state["accepted_reconciliation_competence_digest"] == LIVE_RUNTIME_1_RECONCILIATION_COMPETENCE_DIGEST
    assert state["artifacts"]["accepted_competence_source_path"].endswith("live-general-3-reconciliation-competence-7e0b197edcfa7f63.json")
    assert state["counts"]["csv_learner"] == 1
    assert state["counts"]["json_adapter"] == 1
    assert state["counts"]["reconciliation_executor"] == 1
    assert state["counts"]["final_synthesis"] == 1
    assert state["counts"]["evaluators"] == {"csv": 1, "json": 1, "reconciliation": 1, "final_synthesis": 1}
    assert state["trusted_admissions"] == 0
    assert state["capability_promotions"] == 0
    assert state["tracked_source_mutation"] is False


def test_live_runtime_1_restart_after_graph_registration_resumes_without_outputs(tmp_path):
    root = tmp_path / "live-runtime-1"
    accepted = _accepted_root(tmp_path)
    controller = run_live_runtime_1_attended_cycles(_controller("live-runtime-1-graph"), runtime_root=root, accepted_competence_root=accepted, reset=True, max_cycles=2)
    before = _runtime_state(controller)

    restored = _restore(controller)
    final = run_live_runtime_1_attended_cycles(restored, runtime_root=root, accepted_competence_root=accepted, reset=False)
    state = _runtime_state(final)

    assert before["phase_history"] == ("mission_registered", "work_graph_registered")
    assert before["evaluation_item_ids"] == ()
    assert len(before["work_items"]) == 4
    assert state["terminal"]["terminal_status"] == "LIVE_RUNTIME_1_SUSTAINED_ATTENDED_PASSED"
    assert state["mission_registrations"] == 1
    assert state["work_graph_registrations"] == 1
    assert state["counts"]["csv_learner"] == 1
    assert state["counts"]["json_adapter"] == 1


def test_live_runtime_1_restart_after_independent_branches_resumes_dependents_only(tmp_path):
    root = tmp_path / "live-runtime-1"
    accepted = _accepted_root(tmp_path)
    controller = run_live_runtime_1_attended_cycles(_controller("live-runtime-1-branches"), runtime_root=root, accepted_competence_root=accepted, reset=True, max_cycles=8)
    before = _runtime_state(controller)
    before_inventory = _inventory(root)

    restored = _restore(controller)
    final = run_live_runtime_1_attended_cycles(restored, runtime_root=root, accepted_competence_root=accepted, reset=False)
    state = _runtime_state(final)

    assert before["phase_history"][-2:] == ("csv_completed", "json_completed")
    assert before["work_item_status"]["csv_validation"] == "completed"
    assert before["work_item_status"]["json_validation"] == "completed"
    assert before["work_item_status"]["cross_format_reconciliation"] == "ready"
    assert before["counts"]["csv_learner"] == 1
    assert before["counts"]["json_adapter"] == 1
    assert before["counts"]["reconciliation_executor"] == 0
    assert state["counts"]["csv_learner"] == 1
    assert state["counts"]["json_adapter"] == 1
    assert state["counts"]["reconciliation_executor"] == 1
    assert state["counts"]["final_synthesis"] == 1
    assert set(before_inventory).issubset(set(_inventory(root)))


def test_live_runtime_1_terminal_restart_and_replay_are_exact(tmp_path):
    root = tmp_path / "live-runtime-1"
    controller = _run(_controller("live-runtime-1-terminal"), tmp_path, root, reset=True)
    state = _runtime_state(controller)
    before_inventory = _inventory(root)

    restored = _restore(controller)
    replayed = advance_live_runtime_1_attended_mission(restored)
    replayed_state = _runtime_state(replayed)

    assert replayed_state["status"] == "terminal"
    assert replayed_state["terminal"]["artifact_digest"] == state["terminal"]["artifact_digest"]
    assert replayed_state["evaluation_item_ids"] == state["evaluation_item_ids"]
    assert replayed_state["counts"] == state["counts"]
    assert _inventory(root) == before_inventory


def test_live_runtime_1_monitor_reads_persistent_restart_state(tmp_path):
    runtime_root = tmp_path / "live-runtime-1"
    supervisor_root = tmp_path / "supervisor"
    supervisor_root.mkdir()
    controller = _run(_controller("live-runtime-1-monitor"), tmp_path, runtime_root, reset=True)
    restart = export_continuous_mission_restart_state(controller)
    (supervisor_root / "restart_state.json").write_text(json.dumps(restart, indent=2, sort_keys=True), encoding="utf-8")
    (supervisor_root / "worker_status.json").write_text(
        json.dumps(
            {
                "worker_state": "stopped_after_attended_live_runtime_1",
                "timestamp": "2026-07-22T00:00:00+00:00",
                "session_id": controller.session_id,
                "continuous_mission_state": controller.continuous_mission_state,
                "pending_application_decision_id": "",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (supervisor_root / "observation_requeue.json").write_text(json.dumps({"timestamp": "2026-07-22T00:00:00+00:00"}), encoding="utf-8")

    snapshot = load_monitor_snapshot(supervisor_root)

    assert snapshot.worker_state == "stopped_after_attended_live_runtime_1"
    assert snapshot.mission_state == "live_runtime_1_terminal"
    assert snapshot.operator_interaction_requests == ()


def test_live_runtime_1_fails_closed_without_persisted_accepted_competence(tmp_path):
    controller = attach_live_runtime_1_attended_mission(
        _controller("live-runtime-1-missing-accepted"),
        runtime_root=tmp_path / "live-runtime-1",
        accepted_competence_root=tmp_path / "missing-accepted",
        reset=True,
    )
    controller = _advance(controller, 4)

    try:
        advance_live_runtime_1_attended_mission(controller)
    except ValueError as exc:
        assert str(exc) == "live_runtime_1_accepted_reconciliation_competence_not_persisted"
    else:
        raise AssertionError("missing accepted competence did not fail closed")
