from __future__ import annotations

from orchestration.runtime.ov6_ov10_operational_readiness import (
    answer_ov6_ov10_question,
    is_ov6_ov10_question,
    run_ov10_controlled_training_readiness_review,
    run_ov6_controlled_allowlisted_corpus_pilot,
    run_ov6_ov10_operational_readiness,
    run_ov7_integrated_readonly_runtime,
    run_ov8_activation_readiness,
    run_ov9_operational_hardening,
    write_ov6_ov10_reports,
)


def test_ov6_generates_noncanonical_records_with_provenance_checksums_and_rollback():
    payload = run_ov6_controlled_allowlisted_corpus_pilot()

    assert payload["passed"] is True
    assert payload["full_provenance"] is True
    assert payload["checksums_present"] is True
    assert payload["noncanonical_only"] is True
    assert payload["rollback_delete"]["available"] is True
    assert payload["rollback_delete"]["execution_performed"] is False


def test_ov7_integrates_readonly_runtime_without_mutation():
    payload = run_ov7_integrated_readonly_runtime()

    assert payload["passed"] is True
    assert payload["cognitive_integrity_score"] >= 0.9
    assert payload["read_only_evaluation_loop"]["mutation_performed"] is False
    assert payload["safety"]["provider_call_performed"] is False


def test_ov8_assigns_activation_eligibility_to_every_capability():
    payload = run_ov8_activation_readiness()

    assert payload["passed"] is True
    assert payload["activation_performed"] is False
    assert payload["activation_confidence"] >= 0.85
    assert len(payload["capabilities"]) == 20
    assert all(item["activation_eligibility"] for item in payload["capabilities"])


def test_ov9_hardens_noisy_duplicate_conflicting_and_malformed_cases():
    payload = run_ov9_operational_hardening()

    assert payload["passed"] is True
    assert payload["repair_required"] is False
    assert {"noisy_documents", "duplicate_evidence", "malformed_inputs"} <= set(payload["stress_types"])
    assert all(item["score"] >= 0.75 for item in payload["scenarios"])


def test_ov10_marks_ready_for_controlled_training_pilot_without_training():
    payload = run_ov10_controlled_training_readiness_review()

    assert payload["passed"] is True
    assert payload["training_enabled"] is False
    assert payload["training_performed"] is False
    assert payload["training_readiness_assessment"] == "Ready for controlled training pilot"
    assert payload["final_recommendation"] == "READY_FOR_CONTROLLED_TRAINING_PILOT"


def test_ov6_ov10_combined_review_preserves_safety():
    payload = run_ov6_ov10_operational_readiness()

    assert payload["passed"] is True
    assert payload["operational_readiness_score"] >= 0.9
    assert payload["safety"]["training_performed"] is False
    assert payload["safety"]["provider_call_performed"] is False
    assert payload["safety"]["canonical_write_performed"] is False
    assert payload["safety"]["live_knowledge_mutation_performed"] is False
    assert payload["safety"]["hyb1_promoted"] is False


def test_ov6_ov10_local_answer_route():
    assert is_ov6_ov10_question("Is DELTA ready for controlled training?")
    answer = answer_ov6_ov10_question("training readiness")

    assert answer["phase"] == "OV6-OV10 Operational Readiness"
    assert answer["training_readiness_assessment"] == "Ready for controlled training pilot"
    assert answer["safety"]["training_performed"] is False


def test_ov6_ov10_reports_are_written():
    payload = write_ov6_ov10_reports()

    assert payload["final_recommendation"] == "READY_FOR_CONTROLLED_TRAINING_PILOT"
    assert payload["ov10"]["training_enabled"] is False
