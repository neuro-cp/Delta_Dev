from __future__ import annotations

from pathlib import Path

from orchestration.runtime.bootstrap_adjacent_learning import (
    ACCEPTED_BOOTSTRAP_E_ROOT,
    BOOTSTRAP_F_ASSISTED_ROOT,
    BOOTSTRAP_F_CONTROL_ROOT,
    CASE_CLASSES,
    MISSING_CONCEPTS,
    run_bootstrap_f_comparison,
    run_csv_schema_adjacent_campaign,
)


def test_bootstrap_f_comparison_uses_equivalent_evaluator_and_separate_bootstrap_access(tmp_path):
    result = run_bootstrap_f_comparison(
        control_root=tmp_path / "control",
        assisted_root=tmp_path / "assisted",
        reset=True,
    )

    assert result["equivalent_evaluator_difficulty"] is True
    assert result["control"]["behavioral_case_digest"] == result["assisted"]["behavioral_case_digest"]
    assert result["control"]["retrieval_claims"] == 0
    assert result["assisted"]["retrieval_claims"] == 1
    assert result["control"]["aggregate_disposition"] == "adjacent_learning_failed"
    assert result["assisted"]["aggregate_disposition"] == "adjacent_learning_passed"
    assert result["control"]["terminal_competence_state"] == "not_created"
    assert result["assisted"]["terminal_competence_state"] == "autonomously_learned_competence"
    assert result["assisted"]["retrieval_summary"]["validated_prerequisites"]
    assert len(result["assisted"]["retrieval_summary"]["validated_prerequisites"]) == 6
    assert result["control_passed_cases"] < result["assisted_passed_cases"] == len(CASE_CLASSES)


def test_bootstrap_f_counterfactuals_are_discriminative(tmp_path):
    result = run_bootstrap_f_comparison(
        control_root=tmp_path / "control",
        assisted_root=tmp_path / "assisted",
        reset=True,
    )
    assisted = result["assisted"]

    assert assisted["counterfactual_pass_counts"]["empty"] == 0
    assert assisted["counterfactual_pass_counts"]["irrelevant"] == 0
    assert assisted["counterfactual_pass_counts"]["keyword"] == 0
    assert assisted["counterfactual_pass_counts"]["missing_only"] < len(CASE_CLASSES)
    assert assisted["counterfactual_pass_counts"]["unstructured"] == 0
    assert assisted["counterfactual_pass_counts"]["incorrect"] < len(CASE_CLASSES)


def test_bootstrap_f_exact_once_replay_suppresses_execution(tmp_path):
    root = tmp_path / "assisted"
    first = run_csv_schema_adjacent_campaign(root=root, assisted=True, reset=True)
    before = tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))
    replay = run_csv_schema_adjacent_campaign(root=root, assisted=True, reset=False)
    after = tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))

    assert first["aggregate_disposition"] == "adjacent_learning_passed"
    assert replay["replay_suppressed"] is True
    assert replay["learner_calls"] == 0
    assert replay["evaluator_calls"] == 0
    assert replay["evaluation_digest"] == first["evaluation_digest"]
    assert replay["autonomous_competence_digest"] == first["autonomous_competence_digest"]
    assert before == after


def test_bootstrap_f_artifacts_preserve_boundaries(tmp_path):
    result = run_bootstrap_f_comparison(
        control_root=tmp_path / "control",
        assisted_root=tmp_path / "assisted",
        reset=True,
    )
    assisted = result["assisted"]

    assert Path(ACCEPTED_BOOTSTRAP_E_ROOT).exists()
    assert assisted["provider_calls"] == result["control"]["provider_calls"] == 0
    assert assisted["trusted_admissions"] == result["control"]["trusted_admissions"] == 0
    assert assisted["capability_promotions"] == result["control"]["capability_promotions"] == 0
    assert assisted["missing_concepts"] == MISSING_CONCEPTS
    assert assisted["autonomous_competence_id"].startswith("bootstrap-f-autonomous-competence-")
    assert assisted["candidate_digest"]
    assert assisted["learner_attempt_digest"]
    assert assisted["evaluation_digest"]


def test_bootstrap_f_default_roots_are_disposable_tmp_paths():
    assert BOOTSTRAP_F_CONTROL_ROOT.parts[0] == ".tmp"
    assert BOOTSTRAP_F_ASSISTED_ROOT.parts[0] == ".tmp"
