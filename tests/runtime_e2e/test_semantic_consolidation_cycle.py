import json

from orchestration.runtime.e2e_semantic_consolidation_cycle import (
    decide_consolidation,
    fixture_experiences,
    run_cycle,
    semantic_records_from_experiences,
    write_reports,
)


def test_fixture_experiences_are_created():
    experiences = fixture_experiences()
    assert len(experiences) == 8
    assert all(record.persisted_to_live_memory is False for record in experiences)


def test_semantic_records_are_produced_from_fixture_experiences():
    experiences = fixture_experiences()
    semantic_records = semantic_records_from_experiences(experiences)
    assert len(semantic_records) == len(experiences)
    assert all(record.provenance for record in semantic_records)


def test_replay_batch_references_semantic_records():
    payload = run_cycle()
    semantic_ids = {record["semantic_id"] for record in payload["semantic_records"]}
    assert set(payload["replay_batch"]["semantic_ids"]) == semantic_ids


def test_consolidation_candidates_preserve_provenance():
    payload = run_cycle()
    assert payload["consolidation_candidates"]
    assert all(candidate["provenance"] for candidate in payload["consolidation_candidates"])


def test_consolidation_decision_requires_approval():
    payload = run_cycle()
    candidate = payload["consolidation_candidates"][0]
    from orchestration.runtime.e2e_semantic_consolidation_cycle import E2EConsolidationCandidate

    candidate_obj = E2EConsolidationCandidate(
        candidate_id=candidate["candidate_id"],
        semantic_ids=tuple(candidate["semantic_ids"]),
        synthesized_claim=candidate["synthesized_claim"],
        provenance=tuple(candidate["provenance"]),
    )
    decision = decide_consolidation(candidate_obj, "yes")
    assert decision.approved is False
    assert decision.live_write_performed is False


def test_simulated_consolidated_records_are_created_only_in_harness():
    payload = run_cycle()
    records = payload["simulated_consolidated_knowledge"]
    assert records
    assert all(record["simulated_only"] is True for record in records)
    assert payload["audit"]["safety_flags"]["canonical_memory_mutated"] is False


def test_inquiry_retrieves_relevant_records():
    payload = run_cycle()
    evidence_claims = [item["claim"] for item in payload["retrieved_evidence"]]
    assert any("failed" in claim.lower() for claim in evidence_claims)
    assert any("provenance" in claim.lower() for claim in evidence_claims)


def test_grounded_synthesis_uses_retrieved_records():
    payload = run_cycle()
    answer = payload["grounded_answer"]
    assert set(answer["supporting_evidence_ids"]) == set(payload["audit"]["retrieved_evidence_ids"])
    assert "semantic/consolidated records" in answer["answer"]


def test_answer_includes_what_is_known():
    payload = run_cycle()
    known = payload["grounded_answer"]["known_claims"]
    assert "Atlas likely failed because Registry B rejected entries missing provenance." in known
    assert "Adding provenance restored successful routing." in known


def test_answer_includes_what_remains_uncertain():
    payload = run_cycle()
    uncertainty = payload["grounded_answer"]["uncertainty"]
    assert any("Worker C" in item for item in uncertainty)


def test_answer_refuses_unsupported_claims():
    payload = run_cycle()
    refused = payload["grounded_answer"]["unsupported_claims_refused"]
    assert "Atlas failed because Worker C executed incorrectly." in refused


def test_no_provider_call_occurs():
    assert run_cycle()["audit"]["safety_flags"]["provider_call_performed"] is False


def test_no_model_training_occurs():
    flags = run_cycle()["audit"]["safety_flags"]
    assert flags["model_training_performed"] is False
    assert flags["fine_tuning_performed"] is False
    assert flags["weight_update_performed"] is False


def test_no_live_memory_mutation_occurs():
    assert run_cycle()["audit"]["safety_flags"]["canonical_memory_mutated"] is False


def test_no_live_knowledge_mutation_occurs():
    assert run_cycle()["audit"]["safety_flags"]["live_knowledge_mutated"] is False


def test_audit_trail_covers_every_stage():
    payload = run_cycle()
    audit = payload["audit"]
    assert audit["replay_batch_id"]
    assert audit["consolidation_candidate_ids"]
    assert audit["consolidated_record_ids"]
    assert audit["retrieved_evidence_ids"]


def test_rollback_token_exists():
    payload = run_cycle()
    assert payload["audit"]["safety_flags"]["rollback_available"] is True
    assert payload["simulated_consolidated_knowledge"]


def test_json_report_is_valid():
    payload = write_reports()
    rendered = json.dumps(payload, sort_keys=True)
    assert json.loads(rendered)["audit"]["final_recommendation"] == "PROCEED_VERTICAL_INTEGRATION_PATHOLOGY_REDUCTION"
