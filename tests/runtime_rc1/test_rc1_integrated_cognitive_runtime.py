from orchestration.runtime.rc1_integrated_cognitive_runtime import (
    detect_contradictions,
    load_integrated_semantic_records,
    retrieve_integrated_evidence,
    run_integrated_workflows,
    write_integrated_runtime_report,
)


def test_integrated_fixture_corpus_expands_to_twenty_documents_and_semantics():
    report = run_integrated_workflows()
    assert report["fixture_document_count"] == 20
    assert report["semantic_record_count"] >= 40
    assert report["workflow_count"] == 8


def test_integrated_retrieval_preserves_provenance_and_read_only_behavior():
    evidence = retrieve_integrated_evidence("Why did Project Atlas fail and what remains uncertain?")
    assert evidence
    assert all(item.provenance for item in evidence)
    report = run_integrated_workflows()
    assert report["safety"]["knowledge_mutation_performed"] is False
    assert report["safety"]["provider_call_performed"] is False


def test_integrated_contradiction_detection_preserves_conflicts():
    contradictions = detect_contradictions(load_integrated_semantic_records())
    topics = {item["topic"] for item in contradictions}
    assert "Worker C execution" in topics
    assert "Finance reserves" in topics
    assert all(item["resolution"] == "preserve contradiction pending stronger evidence" for item in contradictions)


def test_integrated_workflows_cover_required_paths():
    report = run_integrated_workflows()
    names = {workflow["name"] for workflow in report["workflows"]}
    assert "document_to_semantics_to_answer" in names
    assert "document_to_semantics_to_proposal" in names
    assert "question_answering" in names
    assert "contradiction" in names
    assert "multi_document_synthesis" in names
    assert "investigation" in names
    assert "self_explanation" in names
    assert "end_to_end_learning_simulation" in names
    assert report["simulated_substrate_delta"]["write_performed"] is False


def test_integrated_answer_support_exposes_reasoning_audit_and_rollback_paths():
    report = run_integrated_workflows()
    support = report["local_answer_support"]
    assert support["which_semantic_records_support_this"]
    assert support["show_reasoning_path"]
    assert support["show_audit_path"]
    assert support["show_rollback_path"]
    assert report["final_recommendation"] == "PROCEED_RC2_PLANNING_MANUAL_REVIEW_FIRST"


def test_integrated_runtime_report_generation():
    report = write_integrated_runtime_report()
    assert report["runtime_maturity_estimate"] == 98
