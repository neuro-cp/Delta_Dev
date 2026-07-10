from __future__ import annotations

from orchestration.runtime import rc2_governed_semantic_graph as graph
from orchestration.runtime import rc2_graph_assisted_reasoning as reasoning
from orchestration.runtime.rc2_conversational_mode_router import route_message


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
    graph.approve_limited_graph_edge_batch(batch_size=15)
    return store


def test_graph_assisted_reasoning_trial_is_read_only_and_separated(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)

    result = reasoning.build_graph_assisted_reasoning_trial(
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration.",
        diagnostics=True,
    )

    assert result["route"] == "read_only_graph_assisted_reasoning_trial"
    assert result["read_only"] is True
    assert result["trial_only"] is True
    assert result["graph_write_performed"] is False
    assert result["memory_write_performed"] is False
    assert result["provider_calls_performed"] is False
    assert result["training_performed"] is False
    assert result["canonical_write_performed"] is False
    assert "Retrieved concepts:" in result["answer"]
    assert "Approved graph edges:" in result["answer"]
    assert "Reasoning path:" in result["answer"]
    assert "Tentative inference:" in result["answer"]
    assert "Uncertainty:" in result["answer"]
    assert "Safety note:" in result["answer"]
    assert result["operator_review_payload"]["review_payload_type"] == "rc2_guided_reasoning_review"
    assert result["operator_review_payload"]["writes_performed"]["memory"] is False
    assert result["operator_review_payload"]["writes_performed"]["graph"] is False
    assert result["operator_review_payload"]["writes_performed"]["canonical"] is False
    assert result["operator_review_payload"]["tentative_inference"]
    assert result["operator_review_payload"]["uncertainty"]
    assert "approve_reasoning_as_useful" in result["operator_review_payload"]["allowed_review_actions"]


def test_reasoning_quality_scores_evidence_chain(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)

    result = reasoning.build_graph_assisted_reasoning_trial(
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."
    )

    assert result["reasoning_quality"]["overall_score"] >= 0.70
    assert result["reasoning_quality"]["evidence_chain_quality"] >= 0.80
    assert result["reasoning_quality"]["hallucination_risk"] <= 0.45


def test_router_invokes_graph_assisted_reasoning_only_when_explicit(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)

    graph_payload = route_message(
        "Conversation",
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration.",
    )
    normal_payload = route_message(
        "Conversation",
        "How does photosynthesis relate to respiration?",
    )

    assert graph_payload["route"] == "read_only_graph_assisted_reasoning_trial"
    assert graph_payload["graph_assisted_reasoning"]["read_only"] is True
    assert graph_payload["provider_calls_performed"] is False
    assert normal_payload["route"] == "developmental_multi_concept_retrieval"
    assert "graph_assisted_reasoning" not in normal_payload


def test_cross_domain_reasoning_evaluation_is_safe(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)

    result = reasoning.run_cross_domain_reasoning_evaluation()

    assert result["trial_count"] >= 5
    assert result["average_reasoning_quality"] >= 0.60
    assert result["read_only"] is True
    assert result["safety"]["training_performed"] is False
    assert result["safety"]["canonical_write_performed"] is False
    assert result["safety"]["provider_calls_performed"] is False
    assert "operator_review_readiness" in result
    assert "failure_taxonomy_counts" in result
    assert all("review_payload_summary" in item for item in result["results"])


def test_guided_reasoning_review_actions_are_review_only(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)
    trial = reasoning.build_graph_assisted_reasoning_trial(
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."
    )

    approved = reasoning.simulate_guided_reasoning_review_action(
        trial["operator_review_payload"],
        "approve_reasoning_as_useful",
    )
    missing = reasoning.simulate_guided_reasoning_review_action(
        trial["operator_review_payload"],
        "mark_missing_evidence",
        operator_notes="Need another support chain.",
    )
    rejected = reasoning.simulate_guided_reasoning_review_action(
        trial["operator_review_payload"],
        "not_a_real_action",
    )

    assert approved["review_only"] is True
    assert approved["writes_performed"]["memory"] is False
    assert approved["writes_performed"]["graph"] is False
    assert missing["operator_notes"] == "Need another support chain."
    assert "missing_graph_edge" in missing["failure_codes"]
    assert rejected["status"] == "invalid_action_rejected"
    assert rejected["action"] == "reject_reasoning"
    assert "operator_rejection" in rejected["failure_codes"]


def test_guided_reasoning_failure_taxonomy_flags_weak_payload():
    payload = {
        "user_question": "why",
        "retrieved_concepts": [
            {
                "concept_name": "Generic",
                "short_definition": "A reusable concept that helps explain causes, constraints, tradeoffs, and practical decisions.",
            }
        ],
        "approved_graph_edges_used": [],
        "evidence_chains": [],
        "confidence": 0.25,
        "overreach_risk": 0.5,
        "hallucination_risk": 0.5,
    }

    failures = reasoning.classify_guided_reasoning_failures(payload)

    assert "weak_retrieval" in failures
    assert "missing_graph_edge" in failures
    assert "generic_concept_substance" in failures
    assert "ambiguous_user_question" in failures
    assert "insufficient_evidence_chain" in failures


def test_guided_reasoning_operator_trial_report_writes_pair(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)
    monkeypatch.setattr(reasoning, "REPORTS", tmp_path)

    report = reasoning.write_guided_reasoning_operator_trial_report()

    assert (tmp_path / "RC2_GUIDED_REASONING_OPERATOR_TRIAL.json").exists()
    assert (tmp_path / "RC2_GUIDED_REASONING_OPERATOR_TRIAL.md").exists()
    assert report["trials_run"] >= 5
    assert report["operator_review_readiness"] >= 0.0
    assert report["sample_review_payload"]["writes_performed"]["memory"] is False
    assert report["simulated_review_actions"][0]["review_only"] is True
    assert report["safety_invariants"]["training_performed"] is False
    assert report["recommendation"] in {
        "CONTINUE_GUIDED_REASONING_REVIEW_POLISH",
        "PROCEED_OPERATOR_UI_POLISH",
        "PROCEED_GRAPH_EXPANSION_REVIEW_TRIAL",
        "READY_FOR_RC2_ARCHITECTURE_FREEZE",
    }


def test_reasoning_completion_report_preserves_invariants(monkeypatch, tmp_path):
    _isolate_graph_store(monkeypatch, tmp_path)

    report = reasoning.build_graph_assisted_reasoning_completion_report()

    assert report["architecture_status"]["read_only_graph_assisted_reasoning"] is True
    assert report["architecture_status"]["autonomous_reasoning"] is False
    assert "reasoning_validation" in report["validation"]
    assert report["validation"]["safety_validation"] is True
    assert report["safety_invariants"]["training_performed"] is False
    assert report["safety_invariants"]["graph_write_performed"] is False
    assert report["recommendation"] in {
        "CONTINUE_REASONING_CALIBRATION",
        "READY_FOR_OPERATOR_REASONING_MODE",
        "READY_FOR_GUIDED_REASONING_OPERATOR_TRIAL",
    }
