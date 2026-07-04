from orchestration.runtime.rc1_document_audit_slice import build_document_audit_slice, write_document_audit_reports


def test_document_audit_slice_answers_required_questions():
    payload = build_document_audit_slice()
    answer = payload["answer"]
    assert answer["learned"]
    assert answer["contradictions"]
    assert answer["evidence_gaps"]
    assert answer["approval_impacts"]


def test_document_audit_slice_keeps_worker_c_uncertain():
    payload = build_document_audit_slice()
    gaps = " ".join(payload["answer"]["evidence_gaps"])
    refusals = " ".join(payload["answer"]["unsupported_refusals"])
    assert "Worker C" in gaps
    assert "Do not claim Worker C caused" in refusals


def test_document_audit_slice_is_fixture_only_and_non_mutating():
    payload = build_document_audit_slice()
    safety = payload["safety"]
    assert safety["fixture_only"] is True
    assert safety["document_upload_performed"] is False
    assert safety["live_document_ingestion_performed"] is False
    assert safety["training_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["knowledge_mutation_performed"] is False
    assert safety["memory_mutation_performed"] is False


def test_document_audit_slice_has_kernel_events_and_transactions():
    payload = build_document_audit_slice()
    assert len(payload["kernel_events"]) == 6
    assert len(payload["transactions"]) == 6
    assert all(transaction["mutation_performed"] is False for transaction in payload["transactions"])


def test_document_audit_report_generation():
    payload = write_document_audit_reports()
    assert payload["final_recommendation"] == "PROCEED_KERNEL_ROUTING_ENFORCEMENT"
    assert payload["estimated_runtime_maturity"] >= 82
