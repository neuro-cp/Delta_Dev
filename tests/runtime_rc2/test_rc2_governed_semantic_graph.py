from __future__ import annotations

import json

from orchestration.runtime import rc2_governed_semantic_graph as graph


def _isolate_graph_store(monkeypatch, tmp_path):
    store = tmp_path / "noncanonical_graph_edges.jsonl"
    review = tmp_path / "graph_review_events.jsonl"
    rollback = tmp_path / "graph_rollback_events.jsonl"
    monkeypatch.setattr(graph, "DATA", tmp_path)
    monkeypatch.setattr(graph, "GRAPH_EDGE_STORE", store)
    monkeypatch.setattr(graph, "GRAPH_REVIEW_LOG", review)
    monkeypatch.setattr(graph, "GRAPH_ROLLBACK_LOG", rollback)
    return store


def test_limited_graph_storage_trial_is_noncanonical_and_bounded(monkeypatch, tmp_path):
    store = _isolate_graph_store(monkeypatch, tmp_path)

    result = graph.approve_limited_graph_edge_batch(batch_size=12)

    assert result["stored_this_run"] == 12
    assert result["approved_edges_total"] == 12
    assert result["graph_store_mutated"] is True
    assert result["canonical_write_performed"] is False
    assert result["automatic_graph_growth_enabled"] is False
    assert result["synthesis_enabled_by_default"] is False
    rows = [json.loads(line) for line in store.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 12
    assert all(row["approval_status"] == "approved_noncanonical" for row in rows)
    assert all(row["canonical"] is False and row["noncanonical"] is True for row in rows)
    assert all(row["rollback_handle"] for row in rows)


def test_limited_graph_storage_trial_is_idempotent(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)

    first = graph.approve_limited_graph_edge_batch(batch_size=10)
    second = graph.approve_limited_graph_edge_batch(batch_size=10)

    assert first["stored_this_run"] == 10
    assert second["stored_this_run"] == 0
    assert second["approved_edges_total"] == 10
    assert second["batch_size_limit"] == 10


def test_graph_assisted_retrieval_is_read_only(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)
    graph.approve_limited_graph_edge_batch(batch_size=15)

    result = graph.graph_assisted_retrieval("How does photosynthesis relate to respiration?")

    assert result["read_only"] is True
    assert result["graph_write_performed"] is False
    assert result["synthesis_enabled"] is False
    assert result["edge_count"] > 0
    assert "Approved graph edges:" in result["answer"]


def test_bounded_traversal_prevents_cycles_and_explains_steps(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)
    graph.approve_limited_graph_edge_batch(batch_size=15)
    first_edge = graph.load_approved_graph_edges()[0]

    result = graph.bounded_graph_traversal(first_edge["source_concept_id"], max_depth=2)

    assert result["read_only"] is True
    assert result["cycle_prevention"] is True
    assert result["duplicate_expansion_prevention"] is True
    assert result["path_count"] > 0
    assert all(step["why_followed"] for path in result["paths"] for step in path)


def test_evidence_chains_include_confidence_uncertainty_and_source(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)
    graph.approve_limited_graph_edge_batch(batch_size=15)

    result = graph.build_evidence_chains("How does photosynthesis relate to respiration?")

    assert result["read_only"] is True
    assert result["graph_write_performed"] is False
    assert result["chain_count"] > 0
    assert result["evidence_chain_quality"]["score"] >= 0.80
    edge_steps = [step for chain in result["chains"] for step in chain["steps"] if step.get("edge_id")]
    assert edge_steps
    assert all(step["confidence"] and step["uncertainty"] and step["source_type"] for step in edge_steps)


def test_graph_diagnostics_and_report_preserve_safety(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)
    graph.approve_limited_graph_edge_batch(batch_size=15)

    diagnostics = graph.graph_diagnostics()
    report = graph.build_governed_semantic_graph_completion_report()

    assert diagnostics["edge_count"] == 15
    assert diagnostics["rollback_coverage"] == 1.0
    assert diagnostics["graph_consistency"] >= 0.80
    assert diagnostics["average_confidence"] >= 0.75
    assert report["validation"]["rollback_validation"] is True
    assert report["validation"]["safety_validation"] is True
    assert report["safety_invariants"]["training_performed"] is False
    assert report["safety_invariants"]["canonical_write_performed"] is False
    assert report["safety_invariants"]["provider_calls_performed"] is False
    assert report["recommendation"] in {
        "READY_FOR_GRAPH_ASSISTED_REASONING_TRIAL",
        "READY_FOR_OPERATOR_GRAPH_EXPANSION",
        "CONTINUE_GRAPH_REFINEMENT",
    }
