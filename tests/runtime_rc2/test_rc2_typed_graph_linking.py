from __future__ import annotations

from orchestration.runtime.rc2_typed_graph_linking import (
    RELATION_TYPES,
    build_candidate_graph_links,
    build_typed_graph_linking_design_report,
    graph_edge_schema,
    graph_quality_metrics,
    retrieve_graph_edge_evidence,
    simulate_operator_review,
    validate_graph_edge,
)


def test_graph_edge_schema_is_governed_and_noncanonical():
    schema = graph_edge_schema()

    assert schema["storage_policy"]["operator_review_required"] is True
    assert schema["storage_policy"]["noncanonical_default"] is True
    assert schema["storage_policy"]["canonical_write_allowed"] is False
    assert set(RELATION_TYPES).issuperset({"depends_on", "supports", "causes", "related_to"})
    assert schema["safety"]["training_performed"] is False
    assert schema["safety"]["automatic_graph_link_approval"] is False


def test_candidate_graph_links_are_review_only_and_valid():
    report = build_candidate_graph_links()

    assert report["candidate_link_count"] > 0
    assert report["written"] is False
    assert report["approved"] is False
    assert report["safety"]["graph_store_mutated"] is False
    edge = report["candidate_links"][0]
    validation = validate_graph_edge(edge)
    assert validation["valid"] is True
    assert edge["approved"] is False
    assert edge["noncanonical"] is True
    assert edge["rollback_handle"].startswith("rollback-")


def test_operator_review_harness_simulates_without_mutating_graph():
    candidates = build_candidate_graph_links()
    review = simulate_operator_review(candidates)

    assert review["graph_store_mutated"] is False
    assert review["approval_is_simulated"] is True
    assert review["review_completion"] == 1.0
    assert review["accepted_count"] + review["rejected_count"] + review["edited_count"] == candidates["candidate_link_count"]
    for edge in review["accepted_edges"]:
        assert edge["approved"] is True
        assert edge["noncanonical"] is True
        assert edge["status"] == "approved_noncanonical_simulated"


def test_graph_quality_and_read_only_retrieval_stay_safe():
    quality = graph_quality_metrics()
    retrieval = retrieve_graph_edge_evidence("How does photosynthesis relate to respiration?")

    assert quality["graph_store_mutated"] is False
    assert quality["rollback_coverage"] == 1.0
    assert quality["candidate_links"] > 0
    assert quality["graph_consistency"] >= 0.80
    assert quality["average_confidence"] >= 0.75
    assert quality["storage_gate"]["ready_for_storage_trial"] is True
    assert retrieval["read_only"] is True
    assert retrieval["graph_store_mutated"] is False
    assert retrieval["synthesis_enabled"] is False


def test_typed_graph_linking_design_report_preserves_invariants():
    report = build_typed_graph_linking_design_report()

    assert report["phase"] == "RC2.7 Typed Graph Linking Design"
    assert report["candidate_report"]["written"] is False
    assert report["review_report"]["graph_store_mutated"] is False
    assert report["quality"]["graph_store_mutated"] is False
    assert report["quality"]["edited_links"] == 0
    assert "related_to" not in report["quality"]["relation_distribution"]
    assert report["safety"]["training_performed"] is False
    assert report["safety"]["canonical_write_performed"] is False
    assert report["safety"]["provider_calls_performed"] is False
