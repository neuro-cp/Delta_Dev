from __future__ import annotations

import sys
from pathlib import Path

from orchestration.runtime.continuous_runtime_controller import (
    attach_continuous_mission,
    attach_developmental_learning_mission,
    compile_operator_developmental_learning_mission,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal
from orchestration.runtime.developmental_learning import (
    classify_developmental_instruction,
    compile_developmental_mission_contract,
    load_retained_learning_bundle,
)


def _induction_bundle() -> dict:
    return {
        "assessment_dimensions": (
            {
                "dimension": "proof_structure",
                "baseline_case_id": "baseline-induction-structure",
                "baseline_components": (),
                "required_components": ("base_case", "induction_hypothesis", "induction_step"),
                "prerequisites": (),
                "evidence_ref": "retained-induction-primer",
            },
            {
                "dimension": "invalid_argument_detection",
                "baseline_case_id": "baseline-invalid-induction",
                "baseline_components": (),
                "required_components": ("identify_missing_induction_step",),
                "prerequisites": ("proof_structure",),
                "evidence_ref": "retained-induction-invalidity-guide",
            },
        ),
        "study_resources": (
            {
                "resource_id": "retained-induction-primer",
                "supports_dimensions": ("proof_structure",),
                "study_components": ("base_case", "induction_hypothesis", "induction_step"),
            },
            {
                "resource_id": "retained-induction-invalidity-guide",
                "supports_dimensions": ("invalid_argument_detection",),
                "study_components": ("identify_missing_induction_step",),
            },
        ),
        # These records are sealed test data. The attempt executor receives only
        # study_resources and cannot alter this collection.
        "sealed_evaluation_cases": (
            {"case_id": "held-out-divisibility-proof", "kind": "held_out", "capability_dimension": "proof_structure", "required_components": ("base_case", "induction_hypothesis", "induction_step")},
            {"case_id": "control-structure", "kind": "control", "capability_dimension": "proof_structure", "required_components": ("base_case",)},
            {"case_id": "adversarial-quote-like-claim", "kind": "adversarial", "capability_dimension": "proof_structure", "required_components": ("base_case", "induction_hypothesis", "induction_step"), "forbidden_components": ("skip_induction_step",)},
            {"case_id": "transfer-recurrence", "kind": "transfer", "capability_dimension": "proof_structure", "required_components": ("base_case", "induction_hypothesis", "induction_step")},
            {"case_id": "held-out-missing-step", "kind": "held_out", "capability_dimension": "invalid_argument_detection", "required_components": ("identify_missing_induction_step",)},
            {"case_id": "control-validity", "kind": "control", "capability_dimension": "invalid_argument_detection", "required_components": ("identify_missing_induction_step",)},
            {"case_id": "adversarial-unsupported-assumption", "kind": "adversarial", "capability_dimension": "invalid_argument_detection", "required_components": ("identify_missing_induction_step",)},
            {"case_id": "transfer-invalid-divisibility-proof", "kind": "transfer", "capability_dimension": "invalid_argument_detection", "required_components": ("identify_missing_induction_step",)},
        ),
    }


def test_instruction_classification_distinguishes_learning_from_conversation_and_repair():
    induction = classify_developmental_instruction("Learn mathematical induction today.")
    broad = classify_developmental_instruction("Today your goal is to learn math.")

    assert induction == {
        "mission_type": "developmental_learning",
        "domain": "mathematics",
        "topic": "mathematical_induction",
        "mission_mode": "bounded_learning_session",
    }
    assert broad and broad["topic"] == "exploratory"
    assert classify_developmental_instruction("Hello there") is None
    assert compile_developmental_mission_contract("Repair the parser regression") is None
    assert load_retained_learning_bundle("mathematics", "mathematical_induction") is not None


def test_learning_mission_assesses_evidence_selects_subgoal_and_does_not_invoke_pcm(tmp_path: Path):
    controller = start_continuous_runtime_controller(session_id="learning-induction")
    controller = compile_operator_developmental_learning_mission(controller, "Learn mathematical induction today.")

    state = controller.continuous_learning_state
    assert controller.continuous_mission_state == "learning_subgoal_active"
    assert state["mission"]["mission_type"] == "developmental_learning"
    assert state["mission"]["topic"] == "mathematical_induction"
    assert state["assessment"]["known_limitations"] == ("proof_structure", "invalid_argument_detection")
    assert state["resource_plan"]["selected_resource_classes"] == ("retained_local_sources",)
    assert controller.continuous_active_subgoal["execution_kind"] == "developmental_learning"
    assert controller.continuous_pcm_bridge_ledger == ()

    updated, result = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        python_executable=sys.executable,
    )

    assert result.accepted is True
    assert result.baseline == {"target": 0.0}
    assert result.candidate == {"target": 1.0}
    assert result.validation["control"] == {"target": 1.0}
    assert result.validation["held_out"] == {"target": 1.0}
    assert result.validation["adversarial"] == {"target": 1.0}
    assert updated.continuous_pcm_bridge_ledger == ()
    assert updated.continuous_active_subgoal["capability_target"] == "invalid_argument_detection"
    assert len(updated.continuous_learning_state["attempts"]) == 1
    assert updated.continuous_learning_state["attempts"][0]["resource_usage"] == {
        "retained_local_sources": 1,
        "provider_calls": 0,
        "web_calls": 0,
    }
    assert (Path(result.campaign_root) / "developmental_evaluation.json").exists()


def test_restart_preserves_learning_state_and_completed_gap_is_not_repeated(tmp_path: Path):
    controller = compile_operator_developmental_learning_mission(
        start_continuous_runtime_controller(session_id="learning-restart"),
        "Learn mathematical induction today.",
    )
    updated, _ = execute_continuous_active_subgoal(
        controller, artifact_root=tmp_path, repository_root=Path.cwd(), python_executable=sys.executable
    )
    restart = export_continuous_mission_restart_state(updated)
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="learning-restart"), restart)

    assert restored.continuous_learning_state["consumed_gap_ids"] == updated.continuous_learning_state["consumed_gap_ids"]
    assert restored.continuous_active_subgoal["source_gap_id"] not in restored.continuous_learning_state["consumed_gap_ids"]
    assert len(restored.continuous_learning_state["evaluations"]) == 1


def test_broad_math_goal_assesses_before_claiming_a_curriculum():
    controller = compile_operator_developmental_learning_mission(
        start_continuous_runtime_controller(session_id="broad-math"),
        "Today your goal is to learn math.",
    )

    mission = controller.continuous_learning_state["mission"]
    assert mission["mission_mode"] == "capability_assessment_then_learning"
    assert mission["topic"] == "exploratory"
    assert controller.continuous_learning_state["assessment"]["assessment_disposition"] == "assessment_completed"
    assert controller.continuous_active_subgoal


def test_repository_repair_stays_on_existing_continuous_mission_path():
    controller = attach_continuous_mission(
        start_continuous_runtime_controller(session_id="repair-stays-repair"), "Optimize your runtime."
    )
    assert controller.continuous_learning_state == {}
    assert controller.continuous_mission_contract["original_operator_goal"] == "Optimize your runtime."
