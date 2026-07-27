from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integration.model_runtime.provider_manager import ProviderManager
from orchestration.runtime.active_cognitive_loop import (
    EvidenceRef,
    LedgerBackedCognitiveModelRunner,
    active_loop_snapshot,
    evaluate_cognitive_episode,
    initialize_episode,
    interrupt_focus,
    read_episode_state,
    resume_focus,
    run_cognitive_cycle,
    write_episode_state,
)
from orchestration.runtime.delta_1_0_common import utc_now
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


RUN_ID = "live-run-operation-schema-specialized-v5"
RUN_ROOT = ROOT / ".tmp" / "active-cognitive-architecture-marathon-1" / RUN_ID

EPISODES = [
    {
        "key": "episode-b-research",
        "title": "Episode B research and synthesis",
        "goal": "research and synthesize whether the current active cognition runtime can support sustained local repository work",
        "expected": "useful research synthesis artifact produced from local evidence",
        "evidence": [
            ("b_runtime_surface", "repo", "Active loop runtime has persistent state, focus selection, typed operations, local model ledger, and prompt snapshots.", "orchestration/runtime/active_cognitive_loop.py contains runtime state, focus, working memory, model execution, validation, and learning artifact functions."),
            ("b_schema_checkpoint", "checkpoint", "Operation-specific schema checkpoint passed and produced durable Episode A evidence.", "Commit eded3528 added operation-specific active cognition and staged closure evidence proving typed operation execution into an active episode."),
            ("b_prior_block", "prior evidence", "Contrary evidence: the earlier marathon status was usefulness-blocked.", ".tmp/active-cognitive-architecture-marathon-1/final_status.json reported live episodes were not qualified and useful Episode A was missing revision/artifact at that time."),
            ("b_user_target", "operator", "The operator now wants sustained exercisable cognition rather than more schema work.", "Required proof is broad objective -> DELTA selects focus -> multiple operations -> evidence revision -> useful work -> restart survival -> next focus selection."),
        ],
    },
    {
        "key": "episode-c-failed-hypothesis",
        "title": "Episode C failed hypothesis revision",
        "goal": "revise a failed hypothesis about the active cognition runtime using contrary evidence",
        "expected": "failed hypothesis is weakened or revised from evidence and summarized",
        "evidence": [
            ("c_initial_hypothesis_support", "repo", "Supporting evidence: active cognition runtime exposes focus, hypothesis, and model operation structures.", "The runtime can formulate hypotheses, compare evidence, and write learning artifacts."),
            ("c_failed_hypothesis_contrary", "prior evidence", "Contrary evidence: the previous marathon claim that live cognition was complete failed.", "Episode B and E were not run; C and D were scripted only; final status was usefulness-blocked."),
            ("c_repair_evidence", "checkpoint", "Operation-specific schema specialization repaired model operation consumption.", "The newer checkpoint showed strict model outputs can revise hypotheses and produce useful Episode A artifacts."),
            ("c_revision_target", "operator", "The target is not to preserve the old broad success claim.", "The useful outcome is a narrower revised hypothesis about what DELTA can now prove live."),
        ],
    },
    {
        "key": "episode-d-restart",
        "title": "Episode D interruption restart and resume",
        "goal": "survive interruption, persisted restart, and resume while preserving active focus and evidence-linked cognition",
        "expected": "interrupted state restores and resumes into useful cognitive work",
        "interrupt_after_cycles": 1,
        "evidence": [
            ("d_persistence_support", "repo", "State serialization and readback are implemented for active cognitive episodes.", "write_episode_state and read_episode_state round-trip ActiveCognitiveEpisodeState."),
            ("d_restart_requirement", "operator", "The proof requires survival across restart rather than only in-memory scripted tests.", "Episode D must persist an interruption, restore it, resume focus, and continue model operations."),
            ("d_prior_limitation", "prior evidence", "Contrary evidence: earlier restart coverage was only round-trip tests, not live model episode evidence.", "The previous final status classified Episode D as covered_by_round_trip_tests_not_live."),
            ("d_useful_target", "operator", "The useful target is a durable restart/resume artifact with model operations after restoration.", "The episode should show focus ID continuity and post-resume learning."),
        ],
    },
    {
        "key": "episode-e-next-focus",
        "title": "Episode E autonomous next-focus selection",
        "goal": "select and begin the next useful focus after completing a prior cognitive episode",
        "expected": "autonomous next focus is selected and begun from evidence without operator choosing it",
        "force_successor_select_next_focus": True,
        "evidence": [
            ("e_completed_prior_work", "prior episode", "Prior live episodes produced research, revision, and restart evidence.", "The next focus should be selected from unresolved evidence rather than assigned as another schema task."),
            ("e_unresolved_research_need", "repo", "Research synthesis still needs translation into an implementation-facing closure decision.", "The useful follow-up is to choose what remaining runtime behavior needs direct exercise or repair."),
            ("e_unresolved_restart_need", "repo", "Restart evidence needs to be connected to autonomous continuation policy.", "After resume, DELTA should choose a next focus from active candidates and begin it."),
            ("e_operator_constraint", "operator", "Do not begin another architecture gate; stay within ACTIVE_COGNITIVE_ARCHITECTURE_MARATHON_1.", "Next-focus selection must remain within the current marathon and keep identify_evidence_need deferred unless genuinely needed."),
        ],
    },
]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def evidence(items: list[tuple[str, str, str, str]]) -> list[EvidenceRef]:
    return [EvidenceRef(*item) for item in items]


def record_episode(root: Path, state, extra: dict[str, object]) -> None:
    write_json(root / "runtime_state.json", state.as_record())
    write_json(root / "snapshot.json", active_loop_snapshot(state))
    write_json(root / "evaluation.json", evaluate_cognitive_episode(state))
    write_json(root / "operation_requests.json", [request.as_record() for request in state.operation_requests])
    write_json(root / "operation_results.json", [result.as_record() for result in state.operation_results])
    write_json(root / "working_memory_packets.json", [packet.as_record() for packet in state.working_memory_packets])
    write_json(root / "hypotheses.json", [hypothesis.as_record() for hypothesis in state.hypotheses])
    write_json(root / "useful_artifacts.json", list(state.useful_artifacts))
    write_json(root / "learning_updates.json", list(state.learning_updates))
    write_json(root / "episode_extra.json", extra)


def run_live_episode(config: dict[str, object], provider: ProviderManager) -> dict[str, object]:
    root = RUN_ROOT / str(config["key"])
    state_path = root / "state.json"
    state = initialize_episode(
        title=str(config["title"]),
        goal_summary=str(config["goal"]),
        expected_state=str(config["expected"]),
        evidence=evidence(config["evidence"]),  # type: ignore[arg-type]
        state_path=state_path,
    )
    runner = LedgerBackedCognitiveModelRunner(
        ledger=LocalModelRequestResultLedger(root / "ledger"),
        provider_manager=provider,
        authority_reason="operator_authorized_active_cognitive_architecture_marathon_1_live_episodes",
        snapshot_root=root,
        request_identity_suffix=str(config["key"]) + "-v5",
    )
    extra: dict[str, object] = {"events": []}
    events: list[dict[str, object]] = extra["events"]  # type: ignore[assignment]
    for _ in range(5):
        if state.completed or state.loop_state.startswith("blocked") or state.loop_state == "paused_budget":
            break
        state = run_cognitive_cycle(state, model_runner=runner)
        write_episode_state(state_path, state)
        latest = state.operation_results[-1]
        events.append({
            "event": "cycle_completed",
            "cycle": len(state.cycles),
            "operation": state.operation_requests[-1].operation_type,
            "accepted": latest.accepted,
            "rejections": latest.rejection_reasons,
            "loop_state": state.loop_state,
        })
        print(json.dumps(events[-1], default=str), flush=True)
        if config.get("interrupt_after_cycles") == len(state.cycles):
            interrupted_focus_id = state.attention.active_focus_id if state.attention else ""
            state = interrupt_focus(
                state,
                reason="checkpointed interruption during live Episode D",
                priority="high",
                return_condition="restore persisted state and continue the same focus",
            )
            write_episode_state(state_path, state)
            restored = read_episode_state(state_path)
            state = resume_focus(restored, reason="restored from persisted live Episode D state")
            write_episode_state(state_path, state)
            events.append({
                "event": "interrupt_persist_restore_resume",
                "interrupted_focus_id": interrupted_focus_id,
                "restored_focus_id": restored.attention.active_focus_id if restored.attention else "",
                "resumed_focus_id": state.attention.active_focus_id if state.attention else "",
            })
    if config.get("force_successor_select_next_focus"):
        successor = initialize_episode(
            title=str(config["title"]) + " successor focus begin",
            goal_summary="begin the next useful focus selected from Episode E evidence after completion",
            expected_state="next focus selected and first operation begun",
            evidence=evidence(config["evidence"]),  # type: ignore[arg-type]
            state_path=root / "successor_state.json",
        )
        successor = run_cognitive_cycle(successor, model_runner=runner, requested_operation="select_next_focus")
        write_episode_state(root / "successor_state.json", successor)
        extra["successor_state"] = successor.as_record()
        extra["successor_evaluation"] = evaluate_cognitive_episode(successor)
        extra["successor_operation"] = successor.operation_requests[-1].operation_type if successor.operation_requests else ""
        extra["successor_started_focus"] = successor.attention.active_focus_id if successor.attention else ""
    record_episode(root, state, extra)
    evaluation = evaluate_cognitive_episode(state)
    status = {
        "episode": config["key"],
        "status": "passed" if evaluation["passed"] else "failed",
        "evaluation": evaluation,
        "operations": [request.operation_type for request in state.operation_requests],
        "model_call_count": state.model_call_count,
        "cycle_count": len(state.cycles),
        "completed": state.completed,
        "identify_evidence_need_used": any(request.operation_type == "identify_evidence_need" for request in state.operation_requests),
        "useful_artifact_count": len(state.useful_artifacts),
        "learning_update_count": len(state.learning_updates),
        "root": str(root),
        "events": events,
    }
    write_json(root / "final_episode_status.json", status)
    return status


def main() -> int:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {"run_id": RUN_ID, "started_at": utc_now(), "status": "running", "episodes": []}
    provider = ProviderManager(keep_loaded=True)
    try:
        for config in EPISODES:
            status = run_live_episode(config, provider)
            summary["episodes"].append(status)  # type: ignore[index, union-attr]
            print(json.dumps({"episode": status["episode"], "status": status["status"], "ops": status["operations"], "failures": status["evaluation"]["failure_classifications"]}, default=str), flush=True)
        summary["status"] = "passed" if all(item["status"] == "passed" for item in summary["episodes"]) else "failed"  # type: ignore[index]
    finally:
        try:
            provider.unload()
        except Exception as exc:
            summary["provider_unload_error"] = str(exc)
    summary["completed_at"] = utc_now()
    summary["identify_evidence_need_used"] = any(item.get("identify_evidence_need_used") for item in summary["episodes"])  # type: ignore[index]
    write_json(RUN_ROOT / "live_episode_summary.json", summary)
    print(json.dumps({"run_root": str(RUN_ROOT), "status": summary["status"], "identify_evidence_need_used": summary["identify_evidence_need_used"]}, indent=2, sort_keys=True), flush=True)
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
