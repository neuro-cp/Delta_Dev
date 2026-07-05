from pathlib import Path

import pytest

from orchestration.runtime.ov1_operational_validation import (
    BASE_CORPUS,
    answer_question,
    benchmark_corpus,
    build_noncanonical_graph,
    detect_conflicts,
    executive_review,
    extract_semantic_objects,
    load_allowlisted_corpus,
    run_ov1_validation,
    write_ov1_reports,
)


def test_ov1_loader_requires_allowlisted_directory(tmp_path):
    with pytest.raises(ValueError):
        load_allowlisted_corpus(tmp_path)


def test_ov1_loader_assigns_reversible_provenance_and_checksums():
    docs = load_allowlisted_corpus()
    assert len(docs) == 20
    assert all(doc.checksum and doc.provenance and doc.reversible for doc in docs)
    assert all(Path(doc.path).suffix in {".md", ".txt"} for doc in docs)


def test_ov1_semantic_extraction_preserves_provenance():
    objects = extract_semantic_objects(load_allowlisted_corpus())
    assert any(obj.object_type == "entity" for obj in objects)
    assert any(obj.object_type == "claim" for obj in objects)
    assert any(obj.object_type == "uncertainty" for obj in objects)
    assert all(obj.provenance for obj in objects)


def test_ov1_noncanonical_graph_supports_lookup_and_traversal():
    graph = build_noncanonical_graph(extract_semantic_objects(load_allowlisted_corpus()))
    assert graph["noncanonical"] is True
    assert graph["entity_lookup"]
    assert graph["claim_lookup"]
    assert graph["source_lookup"]
    assert graph["graph_traversal"]


def test_ov1_answers_only_from_evidence_with_uncertainty():
    objects = extract_semantic_objects(load_allowlisted_corpus())
    answer = answer_question("Why did Project Atlas fail and what remains uncertain?", objects)
    assert answer.supporting_evidence_ids
    assert answer.confidence < 0.9
    assert answer.uncertainty
    assert "Retrieved noncanonical semantic records" in answer.reasoning_summary


def test_ov1_contradiction_engine_finds_expected_clusters():
    conflicts = detect_conflicts(extract_semantic_objects(load_allowlisted_corpus()))
    topics = {item["topic"] for item in conflicts}
    assert "Worker C execution" in topics
    assert "Finance reserves" in topics
    assert "Historical event date" in topics


def test_ov1_investigation_and_executive_review_do_not_execute():
    conflicts = detect_conflicts(extract_semantic_objects(load_allowlisted_corpus()))
    review = executive_review(conflicts)
    assert review["execution_performed"] is False
    assert review["blockers"]
    assert "manual OV1 review" in review["recommended_next_step"]


def test_ov1_benchmark_validates_20_50_100_document_corpora():
    for size in (20, 50, 100):
        result = benchmark_corpus(size)
        assert result["document_count"] == size
        assert result["passed"] is True
        assert result["overall_score"] >= 0.9


def test_ov1_validation_preserves_safety_and_recommends_ov2():
    report = run_ov1_validation()
    assert report["benchmark_pass_rate"] == 1.0
    assert report["operational_confidence_score"] >= 0.9
    assert report["safety"]["provider_call_performed"] is False
    assert report["safety"]["knowledge_mutation_performed"] is False
    assert report["final_recommendation"] == "PROCEED_OV2_CONTROLLED_LIVE_CORPUS_PILOT_REVIEW"


def test_ov1_reports_are_generated():
    report = write_ov1_reports()
    assert report["base_document_count"] == 20
