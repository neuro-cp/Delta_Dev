from __future__ import annotations

import json
import time
from pathlib import Path

from orchestration.runtime.continuous_runtime_controller import (
    advance_live_runtime_1_attended_mission,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.live_general_3_learning_mission import run_live_general_3_approved_learning_mission
from orchestration.runtime.live_runtime_4_crash_integrity import (
    _commit_advancement,
    _digest_record,
    _persist,
    _prepare_advancement,
    compile_live_runtime_4_unattended_authority,
    prepare_live_runtime_4_mission,
    recover_live_runtime_4_interrupted_runner,
    run_live_runtime_4_bounded_unattended,
    start_live_runtime_4_process,
)


def _accepted_root(tmp_path: Path) -> Path:
    root = tmp_path / "accepted-general-3"
    run_live_general_3_approved_learning_mission(root=root, reset=True)
    return root


def _prepare(tmp_path: Path, *, first_cycles: int = 8):
    root = tmp_path / "live-runtime-4"
    controller = prepare_live_runtime_4_mission(runtime_root=root, accepted_competence_root=_accepted_root(tmp_path), reset=True)
    first = compile_live_runtime_4_unattended_authority(controller, runtime_root=root, generation=1, max_cycles=first_cycles)
    return root, first


def _restart(root: Path) -> dict:
    return json.loads((root / "restart_state.json").read_text(encoding="utf-8"))


def _state(root: Path) -> dict:
    return _restart(root)["continuous_learning_state"]["live_runtime_1"]


def _restored(root: Path):
    return restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="tk-live-runtime-4", wake_mode="MANUAL"),
        _restart(root),
    )


def test_live_runtime_4_crash_recovery_reauthorization_and_terminal_resume(tmp_path):
    root, first = _prepare(tmp_path)
    process = start_live_runtime_4_process(
        runtime_root=root,
        authority_id=first["authority_id"],
        fault_after_prepared_phase="json_completed",
    )
    deadline = time.time() + 25
    while process.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if process.poll() is None:
        process.kill()
        process.wait(timeout=5)
    assert process.returncode == 77

    post_crash = _state(root)
    assert post_crash["work_item_status"]["csv_validation"] == "completed"
    assert post_crash["work_item_status"]["json_validation"] == "ready"
    assert post_crash["counts"]["csv_learner"] == 1
    assert post_crash["counts"]["json_adapter"] == 0
    assert len(post_crash["evaluation_item_ids"]) == 1
    assert (root / "runner.lock").exists()

    crash_stop = recover_live_runtime_4_interrupted_runner(runtime_root=root)
    recovery = crash_stop["recovery_classification"]
    assert crash_stop["result_status"] == "LIVE_RUNTIME_4_CRASH_INTEGRITY_PARTIAL"
    assert crash_stop["stop_reason"] == "runner_crash_recovered"
    assert recovery["phase"] == "json_completed"
    assert recovery["disposition"] == "prepared_not_applied_discarded"
    assert not (root / "runner.lock").exists()
    assert (root / "unattended_authority_consumption" / f"{first['authority_id']}.json").exists()

    replay_old = run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])
    assert replay_old["artifact_digest"] == crash_stop["artifact_digest"]
    assert _state(root)["counts"]["json_adapter"] == 0

    second = compile_live_runtime_4_unattended_authority(_restored(root), runtime_root=root, generation=2, max_cycles=8)
    completed_ids = {item["work_item_id"] for item in post_crash["work_items"] if post_crash["work_item_status"][item["label"]] == "completed"}
    assert not completed_ids.intersection(second["allowed_work_item_ids"])

    terminal_stop = run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=second["authority_id"])
    final = _state(root)
    assert terminal_stop["result_status"] == "LIVE_RUNTIME_4_CRASH_INTEGRITY_PASSED"
    assert terminal_stop["stop_reason"] == "terminal"
    assert len(final["evaluation_item_ids"]) == 4
    assert final["counts"]["csv_learner"] == 1
    assert final["counts"]["json_adapter"] == 1
    assert final["counts"]["reconciliation_executor"] == 1
    assert final["counts"]["final_synthesis"] == 1
    assert final["counts"]["evaluators"] == {"csv": 1, "json": 1, "reconciliation": 1, "final_synthesis": 1}
    assert final["counts"]["provider_calls"] == 0
    assert final["trusted_admissions"] == 0
    assert final["capability_promotions"] == 0


def test_live_runtime_4_already_committed_recovery_finalizes_journal_without_replay(tmp_path):
    root, first = _prepare(tmp_path)
    controller = _restored(root)
    prepared = _prepare_advancement(root, controller, first)
    advanced = advance_live_runtime_1_attended_mission(controller)
    _persist(root, advanced, worker_state="running", authority_id=first["authority_id"])
    (root / "runner.lock").mkdir()
    (root / "runner.lock" / "owner.json").write_text(json.dumps({"pid": 999999, "authority_id": first["authority_id"]}), encoding="utf-8")

    stop = recover_live_runtime_4_interrupted_runner(runtime_root=root)

    assert stop["recovery_classification"]["disposition"] == "already_committed_recovered"
    assert stop["recovery_classification"]["advancement_id"] == prepared["advancement_id"]
    assert _state(root)["scheduler_cycles"] == 3
    assert _state(root)["counts"]["csv_learner"] == 0


def test_live_runtime_4_concurrent_runner_is_rejected_before_advancement(tmp_path):
    root, first = _prepare(tmp_path)
    (root / "runner.lock").mkdir()
    (root / "runner.lock" / "owner.json").write_text(json.dumps({"pid": __import__("os").getpid(), "authority_id": first["authority_id"]}), encoding="utf-8")

    stop = run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])

    assert stop["result_status"] == "LIVE_RUNTIME_4_CRASH_INTEGRITY_INTEGRITY_STOP"
    assert stop["stop_reason"] == "concurrent_runner_rejected"
    assert _state(root)["scheduler_cycles"] == 2
    assert _state(root)["counts"]["csv_learner"] == 0


def test_live_runtime_4_stale_lock_is_recovered_after_dead_pid(tmp_path):
    root, first = _prepare(tmp_path, first_cycles=0)
    (root / "runner.lock").mkdir()
    (root / "runner.lock" / "owner.json").write_text(json.dumps({"pid": 999999, "authority_id": first["authority_id"]}), encoding="utf-8")

    stop = run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])

    assert stop["stop_reason"] == "cycle_limit"
    assert not (root / "runner.lock").exists()
    checkpoints = "\n".join(path.read_text(encoding="utf-8") for path in (root / "unattended_checkpoints").glob("*.json"))
    assert "stale_lock_recovered" in checkpoints


def test_live_runtime_4_authority_integrity_negative_controls(tmp_path):
    root, first = _prepare(tmp_path)
    authority_path = root / "unattended_authority" / f"{first['authority_id']}.json"

    corrupted = dict(first)
    corrupted["artifact_digest"] = "bad"
    authority_path.write_text(json.dumps(corrupted, indent=2, sort_keys=True), encoding="utf-8")
    stop = run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])
    assert stop["stop_reason"] == "authority_verification_failed"
    assert _state(root)["scheduler_cycles"] == 2

    root2, first2 = _prepare(tmp_path / "mismatch")
    bad = dict(first2)
    bad["mission_id"] = "wrong"
    bad = _digest_record({key: value for key, value in bad.items() if key != "artifact_digest"})
    (root2 / "unattended_authority" / f"{bad['authority_id']}.json").write_text(json.dumps(bad, indent=2, sort_keys=True), encoding="utf-8")
    stop2 = run_live_runtime_4_bounded_unattended(runtime_root=root2, authority_id=bad["authority_id"])
    assert stop2["stop_reason"] == "authority_verification_failed"

    root3, first3 = _prepare(tmp_path / "expired")
    expired = dict(first3)
    expired["expires_at_epoch_seconds"] = 0
    expired = _digest_record({key: value for key, value in expired.items() if key != "artifact_digest"})
    (root3 / "unattended_authority" / f"{expired['authority_id']}.json").write_text(json.dumps(expired, indent=2, sort_keys=True), encoding="utf-8")
    stop3 = run_live_runtime_4_bounded_unattended(runtime_root=root3, authority_id=expired["authority_id"])
    assert stop3["stop_reason"] == "authority_verification_failed"


def test_live_runtime_4_completed_and_terminal_authority_rejections(tmp_path):
    root, first = _prepare(tmp_path, first_cycles=6)
    run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=first["authority_id"], fault_after_prepared_phase=None)
    second = compile_live_runtime_4_unattended_authority(_restored(root), runtime_root=root, generation=2, max_cycles=8)
    bad_second = compile_live_runtime_4_unattended_authority(
        _restored(root),
        runtime_root=root,
        generation=2,
        max_cycles=8,
        operator_approval_token="operator-approved-live-runtime-4-generation-2-negative-control",
    )
    completed_id = next(item["work_item_id"] for item in _state(root)["work_items"] if _state(root)["work_item_status"][item["label"]] == "completed")
    bad = dict(bad_second)
    bad["allowed_work_item_ids"] = tuple(bad["allowed_work_item_ids"]) + (completed_id,)
    bad = _digest_record({key: value for key, value in bad.items() if key != "artifact_digest"})
    (root / "unattended_authority" / f"{bad['authority_id']}.json").write_text(json.dumps(bad, indent=2, sort_keys=True), encoding="utf-8")

    replay_stop = run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=bad["authority_id"])
    assert replay_stop["stop_reason"] == "authority_verification_failed"

    final_stop = run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=second["authority_id"])
    assert final_stop["stop_reason"] == "terminal"
    try:
        compile_live_runtime_4_unattended_authority(_restored(root), runtime_root=root, generation=3, max_cycles=1)
    except ValueError as exc:
        assert str(exc) == "live_runtime_4_terminal_mission_rejects_unattended_authority"
    else:
        raise AssertionError("terminal mission accepted a new authority")


def test_live_runtime_4_committed_records_are_written_for_normal_advancements(tmp_path):
    root, first = _prepare(tmp_path, first_cycles=1)
    stop = run_live_runtime_4_bounded_unattended(runtime_root=root, authority_id=first["authority_id"])
    committed = tuple((root / "advancement_journal").glob("*.committed.json"))
    prepared = tuple((root / "advancement_journal").glob("*.prepared.json"))

    assert stop["stop_reason"] == "cycle_limit"
    assert len(prepared) == 1
    assert len(committed) == 1
    assert _state(root)["scheduler_cycles"] == 3
