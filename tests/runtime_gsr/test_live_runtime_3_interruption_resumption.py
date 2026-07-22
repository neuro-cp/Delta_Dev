from __future__ import annotations

import json
import time
from pathlib import Path

from orchestration.runtime.live_general_3_learning_mission import run_live_general_3_approved_learning_mission
from orchestration.runtime.live_runtime_3_interruption_resumption import (
    compile_live_runtime_3_unattended_authority,
    prepare_live_runtime_3_mission,
    recover_live_runtime_3_interrupted_runner,
    run_live_runtime_3_bounded_unattended,
    start_live_runtime_3_process,
)


def _accepted_root(tmp_path: Path) -> Path:
    root = tmp_path / "accepted-general-3"
    run_live_general_3_approved_learning_mission(root=root, reset=True)
    return root


def _prepare(tmp_path: Path, *, first_cycles: int = 6):
    root = tmp_path / "live-runtime-3"
    controller = prepare_live_runtime_3_mission(runtime_root=root, accepted_competence_root=_accepted_root(tmp_path), reset=True)
    first = compile_live_runtime_3_unattended_authority(controller, runtime_root=root, generation=1, max_cycles=first_cycles)
    return root, first


def _restart(root: Path) -> dict:
    return json.loads((root / "restart_state.json").read_text(encoding="utf-8"))


def _state(root: Path) -> dict:
    return _restart(root)["continuous_learning_state"]["live_runtime_1"]


def _load_stop(root: Path, authority_id: str | None = None) -> dict:
    if authority_id:
        return json.loads((root / "unattended_stops" / f"{authority_id}.json").read_text(encoding="utf-8"))
    return json.loads((root / "unattended_stop" / "stop.json").read_text(encoding="utf-8"))


def test_live_runtime_3_interruption_reauthorization_and_terminal_resume(tmp_path):
    root, first = _prepare(tmp_path)

    first_stop = run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])
    interrupted = _state(root)

    assert first_stop["result_status"] == "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_PARTIAL"
    assert first_stop["stop_reason"] == "cycle_limit"
    assert interrupted["work_item_status"]["csv_validation"] == "completed"
    assert interrupted["work_item_status"]["json_validation"] == "completed"
    assert interrupted["work_item_status"]["cross_format_reconciliation"] == "ready"
    assert len(interrupted["evaluation_item_ids"]) == 2
    assert interrupted["counts"]["csv_learner"] == 1
    assert interrupted["counts"]["json_adapter"] == 1

    replay_first = run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])
    assert replay_first["artifact_digest"] == first_stop["artifact_digest"]
    assert _state(root)["counts"] == interrupted["counts"]

    from orchestration.runtime.continuous_runtime_controller import restore_continuous_mission_restart_state, start_continuous_runtime_controller

    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="tk-live-runtime-3", wake_mode="MANUAL"), _restart(root))
    second = compile_live_runtime_3_unattended_authority(restored, runtime_root=root, generation=2, max_cycles=6)

    assert set(second["allowed_work_item_ids"]) == {
        item["work_item_id"]
        for item in interrupted["work_items"]
        if interrupted["work_item_status"][item["label"]] != "completed"
    }
    assert not set(second["allowed_work_item_ids"]).intersection(first_stop["evaluation_item_ids"])

    second_stop = run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=second["authority_id"])
    final = _state(root)

    assert second_stop["result_status"] == "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_PASSED"
    assert second_stop["stop_reason"] == "terminal"
    assert len(final["evaluation_item_ids"]) == 4
    assert final["counts"]["csv_learner"] == 1
    assert final["counts"]["json_adapter"] == 1
    assert final["counts"]["reconciliation_executor"] == 1
    assert final["counts"]["final_synthesis"] == 1
    assert final["counts"]["evaluators"] == {"csv": 1, "json": 1, "reconciliation": 1, "final_synthesis": 1}
    assert final["counts"]["provider_calls"] == 0
    assert final["trusted_admissions"] == 0
    assert final["capability_promotions"] == 0
    assert (root / "unattended_authority_consumption" / f"{first['authority_id']}.json").exists()
    assert (root / "unattended_authority_consumption" / f"{second['authority_id']}.json").exists()


def test_live_runtime_3_second_authority_rejects_completed_work_replay(tmp_path):
    root, first = _prepare(tmp_path)
    run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])
    from orchestration.runtime.continuous_runtime_controller import restore_continuous_mission_restart_state, start_continuous_runtime_controller

    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="tk-live-runtime-3", wake_mode="MANUAL"), _restart(root))
    bad = compile_live_runtime_3_unattended_authority(restored, runtime_root=root, generation=2, max_cycles=6)
    state = _state(root)
    completed_id = next(item["work_item_id"] for item in state["work_items"] if state["work_item_status"][item["label"]] == "completed")
    bad["allowed_work_item_ids"] = tuple(bad["allowed_work_item_ids"]) + (completed_id,)
    from orchestration.runtime.live_runtime_3_interruption_resumption import _digest_record

    bad = _digest_record({key: value for key, value in bad.items() if key != "artifact_digest"})
    (root / "unattended_authority" / f"{bad['authority_id']}.json").write_text(json.dumps(bad, indent=2, sort_keys=True), encoding="utf-8")

    stop = run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=bad["authority_id"])

    assert stop["result_status"] == "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_BLOCKED"
    assert stop["stop_reason"] == "authority_verification_failed"
    assert _state(root)["counts"]["reconciliation_executor"] == 0


def test_live_runtime_3_integrity_rejects_corrupted_digest_and_mismatched_mission(tmp_path):
    root, first = _prepare(tmp_path)
    path = root / "unattended_authority" / f"{first['authority_id']}.json"
    corrupted = dict(first)
    corrupted["artifact_digest"] = "bad"
    path.write_text(json.dumps(corrupted, indent=2, sort_keys=True), encoding="utf-8")
    stop = run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])
    assert stop["stop_reason"] == "authority_missing"

    root2, first2 = _prepare(tmp_path / "mismatch")
    path2 = root2 / "unattended_authority" / f"{first2['authority_id']}.json"
    from orchestration.runtime.live_runtime_3_interruption_resumption import _digest_record

    bad = dict(first2)
    bad["mission_id"] = "wrong"
    bad = _digest_record({key: value for key, value in bad.items() if key != "artifact_digest"})
    path2.write_text(json.dumps(bad, indent=2, sort_keys=True), encoding="utf-8")
    stop2 = run_live_runtime_3_bounded_unattended(runtime_root=root2, authority_id=first2["authority_id"])
    assert stop2["stop_reason"] == "authority_verification_failed"


def test_live_runtime_3_simultaneous_runner_is_rejected(tmp_path):
    root, first = _prepare(tmp_path)
    (root / "runner.lock").mkdir()

    stop = run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])

    assert stop["result_status"] == "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_INTEGRITY_STOP"
    assert stop["stop_reason"] == "simultaneous_runner_rejected"
    assert _state(root)["counts"]["csv_learner"] == 0


def test_live_runtime_3_interrupted_running_worker_recovers_without_advancing(tmp_path):
    root, first = _prepare(tmp_path)
    (root / "runner.lock").mkdir()
    (root / "runner.lock" / "owner.json").write_text(json.dumps({"pid": 999999, "authority_id": first["authority_id"]}), encoding="utf-8")
    worker = json.loads((root / "worker_status.json").read_text(encoding="utf-8"))
    worker.update({"worker_state": "running", "authority_id": first["authority_id"], "process_id": 999999})
    (root / "worker_status.json").write_text(json.dumps(worker, indent=2, sort_keys=True), encoding="utf-8")

    stop = recover_live_runtime_3_interrupted_runner(runtime_root=root)

    assert stop["result_status"] == "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_PARTIAL"
    assert stop["stop_reason"] == "controlled_process_interruption"
    assert not (root / "runner.lock").exists()
    assert _state(root)["counts"]["csv_learner"] == 0


def test_live_runtime_3_terminal_rejects_new_unattended_authority(tmp_path):
    root, first = _prepare(tmp_path)
    run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])
    from orchestration.runtime.continuous_runtime_controller import restore_continuous_mission_restart_state, start_continuous_runtime_controller

    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="tk-live-runtime-3", wake_mode="MANUAL"), _restart(root))
    second = compile_live_runtime_3_unattended_authority(restored, runtime_root=root, generation=2, max_cycles=6)
    run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=second["authority_id"])
    terminal = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="tk-live-runtime-3", wake_mode="MANUAL"), _restart(root))

    try:
        compile_live_runtime_3_unattended_authority(terminal, runtime_root=root, generation=3, max_cycles=1)
    except ValueError as exc:
        assert str(exc) == "live_runtime_3_terminal_mission_rejects_unattended_authority"
    else:
        raise AssertionError("terminal mission accepted new unattended authority")


def test_live_runtime_3_process_cycle_limit_exits_and_can_resume(tmp_path):
    root, first = _prepare(tmp_path)
    process = start_live_runtime_3_process(runtime_root=root, authority_id=first["authority_id"])
    try:
        deadline = time.time() + 20
        while process.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        assert process.poll() == 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
    assert _load_stop(root, first["authority_id"])["stop_reason"] == "cycle_limit"
