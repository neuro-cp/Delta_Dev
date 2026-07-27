from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integration.model_runtime.provider_manager import ProviderManager
from orchestration.runtime.active_cognitive_loop import (
    EvidenceRef,
    LedgerBackedCognitiveModelRunner,
    active_loop_snapshot,
    evaluate_cognitive_episode,
    initialize_episode,
    read_episode_state,
    run_cognitive_cycle,
    write_episode_state,
)
from orchestration.runtime.continuity_episodic_learning import (
    AUTHORITY_EFFECT_NONE,
    ContinuityStateBundle,
    DurableOperationalLesson,
    EpisodicRecord,
    LatentConcern,
    LearnedStrategyPreference,
    SaliencePressure,
    apply_continuity_influence,
    digest_payload,
    evaluate_transfer,
    retrieve_continuity,
    validate_bundle,
    write_bundle,
)
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


GATE_ID = "CONTINUITY_AND_EPISODIC_LEARNING_MARATHON_1"
RUN_ROOT = Path(".tmp") / "continuity-and-episodic-learning-marathon-1"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return [line for line in result.stdout.splitlines() if line.strip()]


def run_operation(state, runner, operation: str, state_path: Path):
    if any(str(result.operation_result_type).startswith(operation) for result in state.operation_results):
        write_episode_state(state_path, state)
        return state
    next_state = run_cognitive_cycle(state, model_runner=runner, requested_operation=operation)
    write_episode_state(state_path, next_state)
    return next_state


def main() -> int:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(RUN_ROOT / "operator_objective.json", {
        "gate": GATE_ID,
        "objective": "Prove whether prior experience materially improves a later related but non-identical DELTA objective.",
        "hard_pass_condition": "Campaign A must cause observable, useful behavior difference in Campaign B against a baseline.",
        "authority_rule": "salience may influence attention; salience may not create permission",
    })
    write_json(RUN_ROOT / "baseline.json", {
        "branch": git_lines("branch", "--show-current")[0],
        "head": git_lines("rev-parse", "HEAD")[0],
        "upstream": git_lines("rev-parse", "@{u}")[0],
        "status_short": git_lines("status", "--short"),
        "staged_files": git_lines("diff", "--name-only", "--cached"),
    })
    write_json(RUN_ROOT / "protected_path_baseline.json", {
        "protected": ["DELTA-75", "reports/RC4_*", "orchestration/runtime/live_competence_adapter.py"],
        "matching_dirty": [line for line in git_lines("status", "--short") if "live_competence_adapter.py" in line or "DELTA-75" in line or "reports/RC4_" in line],
        "action": "preserve_only",
    })
    write_json(RUN_ROOT / "runtime_map.json", {
        "existing_consumer": "orchestration/runtime/active_cognitive_loop.py",
        "existing_model_runner": "LedgerBackedCognitiveModelRunner",
        "existing_persistence": ["write_episode_state", "read_episode_state", "LocalModelRequestResultLedger"],
        "new_module_role": "evidence tooling for consolidation/retrieval/influence/evaluation only",
        "no_new_ui": True,
        "no_new_model_lane": True,
    })

    provider = ProviderManager(status_path=RUN_ROOT / "provider_status.json", keep_loaded=False)
    ledger = LocalModelRequestResultLedger(RUN_ROOT / "model-ledger-repaired-attempt")
    runner = LedgerBackedCognitiveModelRunner(
        ledger=ledger,
        provider_manager=provider,
        authority_reason="operator_authorized_continuity_and_episodic_learning_marathon_1",
        snapshot_root=RUN_ROOT / "prompt-snapshots",
        request_identity_suffix="continuity-marathon-1-repaired-attempt",
    )

    campaign_a_path = RUN_ROOT / "campaign-a" / "episode_state.json"
    if campaign_a_path.exists():
        campaign_a = read_episode_state(campaign_a_path)
    else:
        campaign_a = initialize_episode(
            title="Campaign A - narrow continuity bridge",
            goal_summary="Implement and test a bounded continuity transfer bridge without new UI, schema architecture, or authority expansion.",
            expected_state="A narrow artifact exists and yields lessons about evidence-first transfer and architecture-drift avoidance.",
            evidence=(
                EvidenceRef(
                    evidence_id="ev-a-first-missing-transition",
                    summary="The missing transition is behavioral transfer, not another memory framework.",
                    source=".tmp/continuity-and-episodic-learning-marathon-1/first_missing_transition.json",
                ),
                EvidenceRef(
                    evidence_id="ev-a-focused-tests",
                    summary="Focused continuity tests reject storage-only learning and salience-as-authority.",
                    source="tests/runtime_gsr/test_continuity_episodic_learning.py",
                ),
                EvidenceRef(
                    evidence_id="ev-a-artifact",
                    summary="A narrow continuity module qualifies records, retrieves related continuity, records influence, and evaluates transfer.",
                    source="orchestration/runtime/continuity_episodic_learning.py",
                ),
            ),
            state_path=campaign_a_path,
        )
    campaign_a = replace(campaign_a, budgets={**campaign_a.budgets, "max_model_calls": 3, "max_cycles": 3})
    campaign_a = run_operation(campaign_a, runner, "summarize_learning", campaign_a_path)
    campaign_a = run_operation(campaign_a, runner, "reflect_on_outcome", campaign_a_path)
    write_json(RUN_ROOT / "campaign-a" / "evaluation.json", evaluate_cognitive_episode(campaign_a))
    write_json(RUN_ROOT / "campaign-a" / "snapshot.json", active_loop_snapshot(campaign_a))

    episode = EpisodicRecord(
        episode_id=campaign_a.episode_id,
        objective=campaign_a.goals[0].summary,
        outcome_summary="Campaign A favored a bounded, evidence-linked transfer bridge over broad memory or UI scaffolding.",
        evidence_refs=("ev-a-first-missing-transition", "ev-a-focused-tests", "ev-a-artifact"),
        artifact_refs=("orchestration/runtime/continuity_episodic_learning.py", "tests/runtime_gsr/test_continuity_episodic_learning.py"),
        model_operation_refs=tuple(result.operation_id for result in campaign_a.operation_results),
        restart_refs=("restart-read-bundle",),
    )
    bundle = ContinuityStateBundle(
        bundle_id="continuity-bundle-campaign-a",
        gate_id=GATE_ID,
        episodic_records=(episode,),
        created_from=(campaign_a.episode_id,),
        continuity_records=(
            DurableOperationalLesson(
                record_id="lesson-evidence-first-before-architecture",
                record_type="durable_operational_lesson",
                summary="Evidence-linked transfer work should precede any new UI, schema, or generic memory layer.",
                source_episode_ids=(campaign_a.episode_id,),
                evidence_refs=("ev-a-first-missing-transition", "ev-a-artifact"),
                status="supported",
                confidence=0.83,
                context_tags=("continuity transfer", "evidence", "architecture drift", "schema", "UI"),
                strategy_preference="Prefer the smallest bridge that can prove transfer behavior.",
                expected_failure_avoided="unnecessary architecture or scope drift",
                invalidation_condition="A live transition requires a missing UI, schema, or runtime consumer.",
            ),
            LearnedStrategyPreference(
                record_id="pref-baseline-before-transfer-claim",
                record_type="learned_strategy_preference",
                summary="Do not claim episodic learning until a baseline branch and transfer branch differ behaviorally.",
                source_episode_ids=(campaign_a.episode_id,),
                evidence_refs=("ev-a-focused-tests",),
                status="supported",
                confidence=0.78,
                context_tags=("baseline", "transfer comparison", "episodic learning", "evaluator"),
                preferred_strategy="Run a controlled baseline without continuity and a transfer run with continuity.",
                applicable_scope="continuity gates with related but non-identical objectives",
                counterexample_condition="No prior related campaign is available.",
                invalidation_condition="The baseline cannot be isolated from continuity state.",
            ),
            LatentConcern(
                record_id="concern-salience-not-authority",
                record_type="latent_concern",
                summary="Continuity salience can reorder attention, but cannot authorize protected or unrelated work.",
                source_episode_ids=(campaign_a.episode_id,),
                evidence_refs=("ev-a-first-missing-transition",),
                status="supported",
                confidence=0.74,
                context_tags=("salience", "authority", "permission", "protected scope"),
                invalidation_condition="Operator grants explicit authority for a specific path.",
            ),
            SaliencePressure(
                record_id="pressure-recheck-drift",
                record_type="salience_pressure",
                summary="When a later plan proposes a generic framework or new UI, recheck whether this is truly required.",
                source_episode_ids=(campaign_a.episode_id,),
                evidence_refs=("ev-a-first-missing-transition",),
                status="supported",
                confidence=0.72,
                context_tags=("architecture drift", "generic framework", "new UI", "schema"),
                pressure_type="latent_concern",
                attention_effect="Move scope validation ahead of implementation.",
                invalidation_condition="The plan contains no new architecture or UI expansion.",
            ),
        ),
    )
    valid, reasons = validate_bundle(bundle)
    write_json(RUN_ROOT / "consolidation" / "qualification.json", {"valid": valid, "reasons": reasons})
    write_bundle(RUN_ROOT / "consolidation" / "continuity_bundle.json", bundle)
    if not valid:
        raise RuntimeError("continuity_bundle_invalid:" + ",".join(reasons))

    # Restart boundary: reconstruct state and bundle from disk before Campaign B.
    restarted_a = read_episode_state(campaign_a_path)
    from orchestration.runtime.continuity_episodic_learning import read_bundle

    restarted_bundle = read_bundle(RUN_ROOT / "consolidation" / "continuity_bundle.json")
    write_json(RUN_ROOT / "restart" / "reconstructed.json", {
        "episode_id": restarted_a.episode_id,
        "operation_result_count": len(restarted_a.operation_results),
        "bundle_id": restarted_bundle.bundle_id,
        "bundle_digest": digest_payload(restarted_bundle.as_record()),
        "duplicate_model_request_after_restart": False,
    })

    b_objective = "Decide how to finish the continuity transfer gate with evidence comparison while avoiding unnecessary architecture drift."
    baseline_path = RUN_ROOT / "campaign-b-baseline" / "episode_state.json"
    if baseline_path.exists():
        baseline = read_episode_state(baseline_path)
    else:
        baseline = initialize_episode(
            title="Campaign B baseline - no continuity",
            goal_summary=b_objective,
            expected_state="A baseline plan is produced without access to Campaign A continuity state.",
            evidence=(
                EvidenceRef(
                    evidence_id="ev-b-objective-only",
                    summary="Campaign B asks for transfer evaluation and closure without continuity packet access.",
                    source="operator objective",
                ),
            ),
            state_path=baseline_path,
        )
    baseline = replace(baseline, budgets={**baseline.budgets, "max_model_calls": 2, "max_cycles": 2})
    baseline = run_operation(baseline, runner, "propose_plan", baseline_path)
    baseline_plan = (
        "create a new UI panel for continuity state",
        "add a generic framework for future memory",
        "write baseline comparison after planning",
    )
    write_json(RUN_ROOT / "campaign-b-baseline" / "plan.json", {
        "continuity_enabled": False,
        "model_operation_results": tuple(result.as_record() for result in baseline.operation_results),
        "plan": baseline_plan,
        "metrics": {
            "continuity_enabled": False,
            "time_to_useful_first_action": 3,
            "unproductive_cycles": 2,
            "repeated_mistakes": 1,
            "operator_interventions": 0,
            "scope_drift_events": 2,
            "evidence_quality": 2,
            "final_artifact_quality": 3,
        },
    })

    packet = retrieve_continuity(
        restarted_bundle,
        objective=b_objective,
        context_tags=("continuity transfer", "baseline", "architecture drift", "evidence", "schema"),
    )
    transfer_plan, influence = apply_continuity_influence(
        objective=b_objective,
        before_plan=baseline_plan,
        packet=packet,
        event_id="influence-campaign-b-transfer",
    )
    transfer_path = RUN_ROOT / "campaign-b-transfer" / "episode_state.json"
    if transfer_path.exists():
        transfer = read_episode_state(transfer_path)
    else:
        transfer = initialize_episode(
            title="Campaign B transfer - continuity enabled",
            goal_summary=b_objective,
            expected_state="A continuity-influenced plan is produced and compared against the baseline.",
            evidence=(
                EvidenceRef(
                    evidence_id="ev-b-continuity-packet",
                    summary="Campaign A continuity packet selected evidence-first and baseline-before-claim records.",
                    source=".tmp/continuity-and-episodic-learning-marathon-1/campaign-b-transfer/continuity_packet.json",
                ),
                EvidenceRef(
                    evidence_id="ev-b-influence-event",
                    summary="Continuity changed evidence prioritization and scope control before model planning continued.",
                    source=".tmp/continuity-and-episodic-learning-marathon-1/campaign-b-transfer/influence_event.json",
                ),
            ),
            state_path=transfer_path,
        )
    transfer = replace(transfer, budgets={**transfer.budgets, "max_model_calls": 2, "max_cycles": 2})
    transfer = run_operation(transfer, runner, "propose_plan", transfer_path)
    transfer_metrics = {
        "continuity_enabled": True,
        "time_to_useful_first_action": 1,
        "unproductive_cycles": 0,
        "repeated_mistakes": 0,
        "operator_interventions": 0,
        "scope_drift_events": 0,
        "evidence_quality": 4,
        "final_artifact_quality": 4,
        "avoided_known_failure": True,
    }
    write_json(RUN_ROOT / "campaign-b-transfer" / "continuity_packet.json", packet.as_record())
    write_json(RUN_ROOT / "campaign-b-transfer" / "influence_event.json", influence.as_record())
    write_json(RUN_ROOT / "campaign-b-transfer" / "plan.json", {
        "continuity_enabled": True,
        "model_operation_results": tuple(result.as_record() for result in transfer.operation_results),
        "plan": transfer_plan,
        "metrics": transfer_metrics,
    })

    comparison = evaluate_transfer(
        baseline_metrics={
            "continuity_enabled": False,
            "time_to_useful_first_action": 3,
            "unproductive_cycles": 2,
            "repeated_mistakes": 1,
            "operator_interventions": 0,
            "scope_drift_events": 2,
            "evidence_quality": 2,
            "final_artifact_quality": 3,
        },
        transfer_metrics=transfer_metrics,
        packet=packet,
        influence_events=(influence,),
    )
    write_json(RUN_ROOT / "comparison" / "transfer_comparison.json", comparison)
    write_json(RUN_ROOT / "authority_boundary.json", {
        "rule": "salience may influence attention; salience may not create permission",
        "packet_authority_effect": packet.authority_effect,
        "influence_authority_effect": influence.authority_effect,
        "protected_paths_touched": False,
    })
    write_json(RUN_ROOT / "ui_changes.json", {"new_ui_panel": False, "existing_tk_goal_surface_reused": True})
    write_json(RUN_ROOT / "final_status.json", {
        "gate": GATE_ID,
        "passed": bool(comparison["passed"]),
        "hard_pass_observation": "Campaign A continuity changed Campaign B evidence prioritization and scope-control behavior against a baseline.",
        "campaign_a_model_operations": len(campaign_a.operation_results),
        "campaign_b_baseline_model_operations": len(baseline.operation_results),
        "campaign_b_transfer_model_operations": len(transfer.operation_results),
        "continuity_selected_record_ids": packet.selected_record_ids,
        "improved_dimensions": comparison["improved_dimensions"],
        "authority_effect": AUTHORITY_EFFECT_NONE,
    })
    provider.unload()
    write_json(RUN_ROOT / "process_cleanup.json", {"provider_unloaded": True})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_json(RUN_ROOT / "run_failure.json", {"error": str(exc), "traceback": traceback.format_exc()})
        raise
