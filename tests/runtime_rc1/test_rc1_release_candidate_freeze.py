from __future__ import annotations

from orchestration.runtime.rc1_release_candidate_freeze import (
    FINAL_RECOMMENDATION,
    SAFETY,
    answer_rc1_question,
    failure_classification,
    final_review,
    is_rc1_question,
    observation_framework,
    release_manifest,
    validation_summary,
    write_rc1_reports,
)


def test_rc1_manifest_freezes_architecture_without_activation():
    manifest = release_manifest()
    assert manifest["status"] == "release_candidate_freeze"
    assert manifest["architecture_expansion_complete"] is True
    assert manifest["operational_baseline"] is True
    assert all(value is False for value in manifest["safety"].values())


def test_rc1_validation_preserves_safety_invariants():
    validation = validation_summary()
    assert validation["deterministic"] is True
    assert validation["governed"] is True
    assert validation["rollback_capable"] is True
    assert validation["operator_controlled"] is True
    assert SAFETY["model_training_performed"] is False
    assert SAFETY["provider_authority_changed"] is False
    assert SAFETY["routing_changed"] is False


def test_rc1_observation_framework_is_evidence_driven():
    framework = observation_framework()
    assert "reproduction_steps" in framework["required_fields"]
    assert "evidence_path" in framework["required_fields"]
    assert framework["opinion_only_entries_allowed"] is False


def test_rc1_failure_classification_has_priorities():
    classification = failure_classification()
    assert "governance" in classification["classes"]
    assert "P0" in classification["priorities"]


def test_rc1_final_recommendation():
    review = final_review()
    assert review["passed"] is True
    assert review["final_recommendation"] == FINAL_RECOMMENDATION


def test_rc1_reports_and_answer_route():
    payload = write_rc1_reports()
    answer = answer_rc1_question("What is DELTA Runtime v4.0 RC1?")
    assert payload["passed"] is True
    assert is_rc1_question("Why was architecture frozen?")
    assert answer["phase"] == "DELTA Runtime v4.0 RC1"

