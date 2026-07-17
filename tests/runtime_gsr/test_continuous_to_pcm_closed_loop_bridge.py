from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from orchestration.runtime.continuous_mission_foundation import make_satisfied_transfer_record
from orchestration.runtime.continuous_mission_foundation import compile_behavioral_failure_record
from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_behavioral_failures,
    assess_continuous_mission_runtime,
    attach_continuous_mission,
    consume_continuous_capability_reassessment,
    export_continuous_mission_restart_state,
    refresh_continuous_mission_frontier,
    restore_continuous_mission_restart_state,
    select_continuous_mission_subgoal,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_subgoal_executor import (
    compile_continuous_pcm_bridge_fixture,
    execute_continuous_active_subgoal,
    execute_repository_contract_exact_replacement_fixture,
    execute_continuous_to_pcm_closed_loop_fixture,
)


def _controller(*, session_id: str = "continuous-pcm-bridge-test"):
    controller = start_continuous_runtime_controller(session_id=session_id)
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_runtime(
        controller,
        (
            {
                "evidence_source": "preexisting sealed fixture failure",
                "observed_behavior": "PCM structural validation has no sealed behavioral return to the continuous controller",
                "first_incorrect_transition": "accepted grounded design -> no mission-bound PCM attachment",
                "affected_capability": "continuous_pcm_bridge_fixture",
                "baseline_metric": "continuous_pcm_bridge_fixture=0.0",
                "confidence": 0.95,
                "operator_value": 0.95,
                "severity": 0.95,
                "estimated_implementation_breadth": "small",
                "validation_method": "sealed preimplementation behavior bundle",
            },
        ),
    )
    return select_continuous_mission_subgoal(refresh_continuous_mission_frontier(controller))


def test_fixture_compilation_is_mission_bound_and_does_not_embed_a_patch():
    controller = _controller()
    design = compile_continuous_pcm_bridge_fixture(controller, controller.continuous_active_subgoal)

    assert design["mission_id"]
    assert design["subgoal_id"] == controller.continuous_active_subgoal["subgoal_id"]
    assert design["preexisting_behavioral_failure_id"]
    assert design["allowed_paths"] == ("sample.py", "tests/test_pcm_generated_review.py")
    assert design["excluded_paths"]
    assert "replacement_text" not in design
    assert "patch" not in json.dumps(design, sort_keys=True).lower()


def test_fixture_requires_controller_owned_subgoal_and_weakness_ids():
    controller = _controller()
    with pytest.raises(ValueError):
        compile_continuous_pcm_bridge_fixture(controller, {"subgoal_id": "only-subgoal"})


def test_existing_pcm_lifecycle_returns_only_sealed_behavioral_success(tmp_path: Path):
    controller = _controller()
    updated, result = execute_continuous_to_pcm_closed_loop_fixture(
        controller,
        artifact_root=tmp_path,
        python_executable=sys.executable,
    )

    bundle_path = Path(result.campaign_root) / "sealed_behavioral_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bridge = updated.continuous_pcm_bridge_ledger[-1]
    knowledge = updated.continuous_knowledge_ledger[-1]

    assert result.accepted is True
    assert result.disposition == "behaviorally_demonstrated"
    assert result.baseline == {"target": False, "control": True, "held_out": False}
    assert result.candidate["structural_classification"] == "proposal_passed"
    assert result.validation == {
        "control": True,
        "held_out": True,
        "bundle_unchanged": True,
        "causal_restoration": True,
    }
    assert result.clean_reproduction["restored_baseline"] == {"target": False, "control": True, "held_out": False}
    assert bundle["created_before_implementation"] is True
    assert bridge["consumed_by_controller"] is True
    assert bridge["structural_disposition"] == "proposal_passed"
    assert bridge["behavioral_disposition"] == "behaviorally_demonstrated"
    assert knowledge["capability_acquired"] is True
    assert knowledge["behavioral_evaluation"]["evidence_independence"]["candidate_generated_expected_outputs"] is False
    assert updated.continuous_mission_state in {"subgoal_active", "observing_for_new_weaknesses"}
    assert not list((Path(result.campaign_root) / "sandboxes").glob("pcm2_sandbox_*"))


def test_existing_subgoal_executor_dispatches_only_the_explicit_fixture_kind(tmp_path: Path):
    controller = _controller(session_id="continuous-pcm-bridge-dispatch")
    controller = replace(
        controller,
        continuous_active_subgoal={
            **controller.continuous_active_subgoal,
            "execution_kind": "continuous_to_pcm_closed_loop_fixture",
        },
    )

    updated, result = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        python_executable=sys.executable,
    )

    assert result.disposition == "behaviorally_demonstrated"
    assert updated.continuous_pcm_bridge_ledger[-1]["consumed_by_controller"] is True


def _exact_replacement_controller():
    evidence = {
        "source_type": "failing_test",
        "source_reference": "sealed_score_gate_behavior.json",
        "source_digest": "sealed-score-gate-digest",
        "observed_behavior": "classify_score(69) returns pass because the current threshold is score >= 0.",
        "expected_behavior": "classify_score(69) returns fail while classify_score(70) returns pass.",
        "expected_behavior_identity": "score_gate_threshold_behavior",
        "expected_behavior_authority": "sealed_behavioral_evaluation_bundle",
        "expected_vs_observed_result": "exact_behavioral_logic_replacement",
        "baseline_reproduction": "score_gate_threshold=0.0",
        "reproduction_command_or_predicate": "sealed score-gate behavior predicate",
        "reproduction_attempts": (
            {
                "command_or_predicate_identity": "sealed score-gate behavior predicate",
                "input_or_state_reference": "sealed_score_gate_behavior.json",
                "started_at": "2026-07-16T00:00:00+00:00",
                "completed_at": "2026-07-16T00:00:01+00:00",
                "status": "completed",
                "result_classification": "threshold_behavior_failed",
                "result_digest": "score-gate-result-digest",
                "environment_digest": "score-gate-env-digest",
                "authoritative_runner_identity": "sealed_score_gate_behavior_v1",
            },
        ),
        "reproduction_result": "failed",
        "reproduction_output_digest": "score-gate-output-digest",
        "first_incorrect_transition": "score 69 evaluated -> threshold condition score >= 0 -> pass",
        "affected_runtime_stage": "repository_contract_exact_replacement",
        "affected_capability_id": "score_gate_threshold_behavior",
        "originating_mission_id": "repository-contract-exact-replacement-test",
        "suspected_owner_paths": ("score_gate.py",),
        "independent_evidence_paths": ("sealed_score_gate_behavior.json",),
        "allowed_scope": ("score_gate.py",),
        "excluded_scope": ("DELTA-75", "reports/RC4_*", "tests/"),
        "materiality_reason": "The threshold behavior is wrong while the function and controls remain otherwise bounded.",
        "reproducibility_status": "reproduced",
        "environment_digest": "score-gate-env-digest",
        "state_digest": "score-gate-state-digest",
        "authority_class": "local_execution_allowed",
        "ambiguity_status": "resolved",
        "current_disposition": "behaviorally_failed",
        "observed_at": "2026-07-16T00:00:02+00:00",
    }
    compiled = compile_behavioral_failure_record(evidence)
    assert compiled.accepted
    assert compiled.record is not None
    controller = start_continuous_runtime_controller(session_id="repository-contract-exact-replacement")
    controller = attach_continuous_mission(controller, "Repair one sealed score-gate threshold failure.")
    controller = assess_continuous_mission_behavioral_failures(controller, (compiled.record,))
    controller = refresh_continuous_mission_frontier(controller)
    controller = select_continuous_mission_subgoal(controller)
    assert controller.continuous_active_subgoal
    return controller


def test_repository_behavior_contract_enters_pcm_exact_replacement_and_reassessment(tmp_path: Path):
    controller = _exact_replacement_controller()

    updated, result = execute_repository_contract_exact_replacement_fixture(
        controller,
        artifact_root=tmp_path,
        python_executable=sys.executable,
    )
    root = Path(result.campaign_root)
    disposition = json.loads((root / "exact_replacement_bridge_disposition.json").read_text(encoding="utf-8"))
    patch = disposition["patch_proposal"]
    operation = patch["operations"][0]

    assert result.accepted is True
    assert result.disposition == "behaviorally_demonstrated"
    assert result.baseline == {"target": False, "control": True, "held_out": False}
    assert result.candidate["behavioral"] == {"target": True, "control": True, "held_out": True}
    assert result.clean_reproduction["restored_baseline"] == {"target": False, "control": True, "held_out": False}
    assert disposition["contract"]["local_implementation_eligibility"] == "locally_implementable_by_existing_pcm"
    assert disposition["contract"]["failure_mechanism"] == "exact_behavioral_logic_replacement"
    assert operation["operation"] == "exact_replace_text"
    assert "score >= 0" in operation["expected_old_text"]
    assert "score >= 70" in operation["replacement_text"]
    assert disposition["behavioral"]["evidence_independence"]["candidate_generated_expected_outputs"] is False
    assert disposition["tracked_source_mutated"] is False
    assert updated.continuous_knowledge_ledger[-1]["capability_acquired"] is True


def test_structural_evidence_does_not_consume_the_active_gap_as_solved():
    controller = _controller()
    structural = replace(
        make_satisfied_transfer_record(),
        capability_id="continuous_pcm_bridge_fixture",
        reassessment="candidate_structurally_validated",
        evidence_stage="candidate_structurally_validated",
        capability_acquired=False,
        eligible_for_behavioral_evaluation=True,
        behavioral_evaluation_ref="",
        behavioral_evaluation=None,
    )

    updated = consume_continuous_capability_reassessment(controller, structural)

    assert updated.continuous_consumed_weakness_signatures == controller.continuous_consumed_weakness_signatures
    assert updated.continuous_knowledge_ledger[-1]["capability_acquired"] is False
    assert updated.continuous_knowledge_ledger[-1]["evidence_stage"] == "candidate_structurally_validated"


def test_restart_and_delayed_replay_do_not_duplicate_pcm_or_reassessment(tmp_path: Path):
    controller = _controller(session_id="continuous-pcm-bridge-restart")
    updated, first = execute_continuous_to_pcm_closed_loop_fixture(
        controller,
        artifact_root=tmp_path,
        python_executable=sys.executable,
    )
    restart = export_continuous_mission_restart_state(updated)
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=updated.session_id),
        restart,
    )
    # Simulate a delayed worker replaying its already-completed subgoal after recovery.
    replaying = replace(restored, continuous_active_subgoal=controller.continuous_active_subgoal)
    replayed, duplicate = execute_continuous_to_pcm_closed_loop_fixture(
        replaying,
        artifact_root=tmp_path,
        python_executable=sys.executable,
    )

    assert first.consumed_once is True
    assert duplicate.disposition == "duplicate_pcm_bridge_result_prevented"
    assert duplicate.consumed_once is False
    assert replayed.continuous_pcm_bridge_ledger == restored.continuous_pcm_bridge_ledger
    assert replayed.continuous_knowledge_ledger == restored.continuous_knowledge_ledger


def test_completed_artifact_replay_recovers_lost_controller_consumption(tmp_path: Path):
    controller = _controller(session_id="continuous-pcm-bridge-lost-checkpoint")
    updated, first = execute_continuous_to_pcm_closed_loop_fixture(
        controller,
        artifact_root=tmp_path,
        python_executable=sys.executable,
    )

    # Simulate a crash after the durable bridge artifacts were written but before
    # a controller checkpoint captured the bridge ledger and knowledge record.
    recovered, replay = execute_continuous_to_pcm_closed_loop_fixture(
        controller,
        artifact_root=tmp_path,
        python_executable=sys.executable,
    )

    assert first.consumed_once is True
    assert replay.consumed_once is True
    assert replay.reason == "completed PCM bridge result recovered from durable artifact"
    assert recovered.continuous_pcm_bridge_ledger[-1]["bridge_id"] == updated.continuous_pcm_bridge_ledger[-1]["bridge_id"]
    assert recovered.continuous_knowledge_ledger[-1]["behavioral_evaluation_ref"] == updated.continuous_knowledge_ledger[-1]["behavioral_evaluation_ref"]
    assert len(recovered.continuous_knowledge_ledger) == len(controller.continuous_knowledge_ledger) + 1
