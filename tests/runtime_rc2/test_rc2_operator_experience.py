from __future__ import annotations

from orchestration.runtime import rc2_governed_semantic_graph as graph
from orchestration.runtime import rc2_graph_assisted_reasoning as reasoning
from orchestration.runtime import rc2_operator_experience as operator_experience


def _isolate_graph_store(monkeypatch, tmp_path):
    store = tmp_path / "noncanonical_graph_edges.jsonl"
    review = tmp_path / "graph_review_events.jsonl"
    rollback = tmp_path / "graph_rollback_events.jsonl"
    monkeypatch.setattr(graph, "DATA", tmp_path)
    monkeypatch.setattr(graph, "GRAPH_EDGE_STORE", store)
    monkeypatch.setattr(graph, "GRAPH_REVIEW_LOG", review)
    monkeypatch.setattr(graph, "GRAPH_ROLLBACK_LOG", rollback)
    monkeypatch.setattr(reasoning, "graph_assisted_retrieval", graph.graph_assisted_retrieval)
    monkeypatch.setattr(reasoning, "build_evidence_chains", graph.build_evidence_chains)
    monkeypatch.setattr(reasoning, "graph_diagnostics", graph.graph_diagnostics)
    monkeypatch.setattr(operator_experience, "load_approved_graph_edges", graph.load_approved_graph_edges)
    monkeypatch.setattr(operator_experience, "graph_diagnostics", graph.graph_diagnostics)
    graph.approve_limited_graph_edge_batch(batch_size=15)


def test_operator_timeline_and_review_card_are_read_only(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)

    timeline = operator_experience.build_unified_operator_timeline(
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."
    )
    card = timeline["review_card"]

    assert timeline["timeline_type"] == "rc2_operator_cognitive_timeline"
    assert [step["stage"] for step in timeline["steps"]] == [
        "conversation",
        "retrieval",
        "graph_expansion",
        "evidence_chain",
        "reasoning",
        "review_outcome",
        "concept_candidate",
        "graph_candidate",
        "memory_decision",
    ]
    assert card["review_card_type"] == "rc2_unified_operator_review_card"
    assert card["retrieved_concepts"]
    assert card["graph_edges"]
    assert card["evidence_chains"]
    assert card["writes_performed"]["memory"] is False
    assert card["writes_performed"]["graph"] is False
    assert card["debug_clutter_removed"] is True
    assert timeline["safety"]["training_performed"] is False
    assert timeline["safety"]["canonical_write_performed"] is False


def test_reasoning_diff_replay_and_visualization_are_operator_ready(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)
    previous = reasoning.build_graph_assisted_reasoning_trial(
        "Use graph-assisted reasoning to explain how gravity relates to orbital motion."
    )
    current = reasoning.build_graph_assisted_reasoning_trial(
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."
    )

    diff = operator_experience.build_reasoning_diff(previous, current)
    replay = operator_experience.build_conversation_replay(
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."
    )
    visualization = operator_experience.build_graph_visualization_payload(
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."
    )

    assert diff["diff_type"] == "rc2_reasoning_diff"
    assert "confidence_change" in diff
    assert replay["step_count"] == 9
    assert replay["deterministic"] is True
    assert visualization["visualization_type"] == "rc2_graph_visualization_payload"
    assert visualization["nodes"]
    assert visualization["edges"]
    assert visualization["read_only"] is True


def test_operator_queue_dashboard_and_productivity_preserve_invariants(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)

    dashboard = operator_experience.build_cognitive_state_dashboard()
    queue = operator_experience.build_operator_work_queue()
    metrics = operator_experience.build_operator_productivity_metrics()

    assert dashboard["dashboard_type"] == "rc2_operator_cognitive_state_dashboard"
    assert dashboard["safety_gates"]["provider_calls_performed"] is False
    assert dashboard["safety_gates"]["training_performed"] is False
    assert queue["queue_type"] == "rc2_unified_operator_work_queue"
    assert queue["queue_size"] >= 3
    assert all(item["executes_automatically"] is False for item in queue["items"])
    assert metrics["metrics_type"] == "rc2_operator_productivity_metrics"
    assert metrics["queue_completion_simulated"] is False
    assert metrics["operator_review_readiness"] >= 0.0


def test_operator_experience_completion_report_writes_pair(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)
    monkeypatch.setattr(operator_experience, "REPORTS", tmp_path)

    report = operator_experience.write_operator_experience_completion_report()

    assert (tmp_path / "RC2_OPERATOR_EXPERIENCE_COMPLETION.json").exists()
    assert (tmp_path / "RC2_OPERATOR_EXPERIENCE_COMPLETION.md").exists()
    assert report["phase"] == "RC2.14-RC2.17 Operator Experience Completion"
    assert report["timeline_implementation"]["read_only"] is True
    assert report["unified_review_payload"]["read_only"] is True
    assert report["replay_readiness"]["read_only"] is True
    assert report["visualization_readiness"]["read_only"] is True
    assert report["safety_invariants"]["graph_write_performed"] is False
    assert report["safety_invariants"]["concept_approval_performed"] is False
    assert report["recommendation"] in {
        "READY_FOR_RC2_ARCHITECTURE_FREEZE",
        "PROCEED_GOVERNED_GRAPH_EXPANSION",
        "CONTINUE_OPERATOR_EXPERIENCE_POLISH",
    }
