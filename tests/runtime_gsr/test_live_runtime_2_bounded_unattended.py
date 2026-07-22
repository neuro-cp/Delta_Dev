from __future__ import annotations

import json
import hashlib
import time
from pathlib import Path

from orchestration.runtime.continuous_runtime_controller import (
    export_continuous_mission_restart_state,
)
from orchestration.runtime.live_general_3_learning_mission import run_live_general_3_approved_learning_mission
from orchestration.runtime.live_runtime_2_bounded_unattended import (
    compile_live_runtime_2_unattended_authority,
    prepare_live_runtime_2_mission,
    run_live_runtime_2_bounded_unattended,
)


def _accepted_root(tmp_path: Path) -> Path:
    root = tmp_path / "accepted-general-3"
    run_live_general_3_approved_learning_mission(root=root, reset=True)
    return root


def _prepare(tmp_path: Path, *, max_cycles: int = 12, max_duration_seconds: int = 1200):
    root = tmp_path / "live-runtime-2"
    controller = prepare_live_runtime_2_mission(runtime_root=root, accepted_competence_root=_accepted_root(tmp_path), reset=True)
    authority = compile_live_runtime_2_unattended_authority(
        controller,
        runtime_root=root,
        max_cycles=max_cycles,
        max_duration_seconds=max_duration_seconds,
        provider_budget=0,
    )
    return root, controller, authority


def _restart(root: Path) -> dict:
    return json.loads((root / "restart_state.json").read_text(encoding="utf-8"))


def _state(root: Path) -> dict:
    return _restart(root)["continuous_learning_state"]["live_runtime_1"]


def _write_restart(root: Path, restart: dict) -> None:
    (root / "restart_state.json").write_text(json.dumps(restart, indent=2, sort_keys=True), encoding="utf-8")


def _inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.json"))
    }


def test_live_runtime_2_bounded_unattended_reaches_terminal_and_consumes_authority(tmp_path):
    root, _controller, authority = _prepare(tmp_path)

    stop = run_live_runtime_2_bounded_unattended(runtime_root=root)
    state = _state(root)

    assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PASSED"
    assert stop["stop_reason"] == "terminal"
    assert stop["authority_id"] == authority["authority_id"]
    assert state["terminal"]["terminal_status"] == "LIVE_RUNTIME_1_SUSTAINED_ATTENDED_PASSED"
    assert len(state["evaluation_item_ids"]) == 4
    assert state["counts"]["provider_calls"] == 0
    assert state["counts"]["csv_learner"] == 1
    assert state["counts"]["json_adapter"] == 1
    assert state["counts"]["reconciliation_executor"] == 1
    assert state["counts"]["final_synthesis"] == 1
    assert state["counts"]["evaluators"] == {"csv": 1, "json": 1, "reconciliation": 1, "final_synthesis": 1}
    assert state["trusted_admissions"] == 0
    assert state["capability_promotions"] == 0
    assert state["tracked_source_mutation"] is False
    assert (root / "unattended_authority_consumption" / f"{authority['authority_id']}.json").exists()
    assert (root / "unattended_checkpoints" / "000-graph_registered.json").exists()
    assert (root / "unattended_checkpoints" / "001-unattended_authority_accepted.json").exists()


def test_live_runtime_2_consumed_authority_replay_does_not_rerun(tmp_path):
    root, _controller, _authority = _prepare(tmp_path)
    first = run_live_runtime_2_bounded_unattended(runtime_root=root)
    before = _inventory(root)

    second = run_live_runtime_2_bounded_unattended(runtime_root=root)
    after = _inventory(root)
    state = _state(root)

    assert second["artifact_digest"] == first["artifact_digest"]
    assert state["counts"]["csv_learner"] == 1
    assert state["counts"]["json_adapter"] == 1
    assert before == after


def test_live_runtime_2_requires_current_mission_authority(tmp_path):
    root = tmp_path / "live-runtime-2"
    prepare_live_runtime_2_mission(runtime_root=root, accepted_competence_root=_accepted_root(tmp_path), reset=True)

    stop = run_live_runtime_2_bounded_unattended(runtime_root=root)

    assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_BLOCKED"
    assert stop["stop_reason"] == "authority_missing"


def test_live_runtime_2_rejects_authority_for_another_mission(tmp_path):
    root, _controller, authority = _prepare(tmp_path)
    bad = dict(authority)
    bad["mission_id"] = "other-mission"
    bad["artifact_digest"] = ""
    from orchestration.runtime.live_runtime_2_bounded_unattended import _digest_record

    bad = _digest_record({key: value for key, value in bad.items() if key != "artifact_digest"})
    (root / "unattended_authority" / f"{authority['authority_id']}.json").write_text(json.dumps(bad, indent=2, sort_keys=True), encoding="utf-8")

    stop = run_live_runtime_2_bounded_unattended(runtime_root=root)

    assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_INTEGRITY_STOP"
    assert stop["stop_reason"] == "authority_verification_failed"
    assert _state(root)["counts"]["csv_learner"] == 0


def test_live_runtime_2_cycle_limit_stops_without_terminal(tmp_path):
    root, _controller, _authority = _prepare(tmp_path, max_cycles=1)

    stop = run_live_runtime_2_bounded_unattended(runtime_root=root)
    state = _state(root)

    assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PARTIAL"
    assert stop["stop_reason"] == "cycle_limit"
    assert state["status"] != "terminal"
    assert state["counts"]["csv_learner"] == 0


def test_live_runtime_2_wall_clock_expiration_stops_without_terminal(tmp_path):
    root, _controller, _authority = _prepare(tmp_path, max_duration_seconds=0)

    stop = run_live_runtime_2_bounded_unattended(runtime_root=root)

    assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PARTIAL"
    assert stop["stop_reason"] == "wall_clock_expired"
    assert _state(root)["counts"]["csv_learner"] == 0


def test_live_runtime_2_terminal_state_stops_immediately(tmp_path):
    root, _controller, _authority = _prepare(tmp_path)
    run_live_runtime_2_bounded_unattended(runtime_root=root)
    first_state = _state(root)
    first_counts = dict(first_state["counts"])

    stop = run_live_runtime_2_bounded_unattended(runtime_root=root)

    assert stop["stop_reason"] == "terminal"
    assert _state(root)["counts"] == first_counts


def test_live_runtime_2_guardrails_stop_provider_learning_second_mission_and_mutation(tmp_path):
    cases = (
        ("provider_calls", ("counts", "provider_calls"), 1, "provider_call_attempt"),
        ("learning_attempt", ("learning_attempts_created",), 1, "learning_attempt_creation"),
        ("operator_requests", ("operator_requests_created",), 1, "unexpected_operator_request"),
        ("second_mission", ("mission_registrations",), 2, "second_mission_detection"),
        ("tracked_source", ("tracked_source_mutation",), True, "tracked_source_mutation"),
        ("trusted_admission", ("trusted_admissions",), 1, "trusted_admission_changed"),
        ("promotion", ("capability_promotions",), 1, "capability_promotion_changed"),
    )
    for label, path, value, reason in cases:
        root, _controller, _authority = _prepare(tmp_path / label)
        restart = _restart(root)
        state = restart["continuous_learning_state"]["live_runtime_1"]
        target = state
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        _write_restart(root, restart)

        stop = run_live_runtime_2_bounded_unattended(runtime_root=root)

        assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_INTEGRITY_STOP"
        assert stop["stop_reason"] == reason


def test_live_runtime_2_guardrails_stop_fixture_mutation(tmp_path):
    root, _controller, _authority = _prepare(tmp_path)
    run_live_runtime_2_bounded_unattended(runtime_root=root)
    restart = _restart(root)
    state = restart["continuous_learning_state"]["live_runtime_1"]
    state["artifacts"]["csv_result"]["fixture_input_digests_after"][0][1] = "mutated"
    consumption = root / "unattended_authority_consumption"
    for path in consumption.glob("*.json"):
        path.unlink()
    consumption.rmdir()
    _write_restart(root, restart)

    stop = run_live_runtime_2_bounded_unattended(runtime_root=root)

    assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_INTEGRITY_STOP"
    assert stop["stop_reason"] == "fixture_input_mutation"


def test_live_runtime_2_process_exits_and_writes_terminal_stop(tmp_path):
    root, _controller, _authority = _prepare(tmp_path)
    from orchestration.runtime.live_runtime_2_bounded_unattended import start_live_runtime_2_process

    process = start_live_runtime_2_process(runtime_root=root)
    try:
        deadline = time.time() + 20
        while process.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        assert process.poll() == 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)

    stop = json.loads((root / "unattended_stop" / "stop.json").read_text(encoding="utf-8"))
    assert stop["result_status"] == "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PASSED"
    assert json.loads((root / "worker_status.json").read_text(encoding="utf-8"))["worker_state"] == "stopped"
