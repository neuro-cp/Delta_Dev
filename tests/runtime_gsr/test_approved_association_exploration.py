from orchestration.runtime.approved_association_exploration import execute_once, queue_exploration
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger
from orchestration.runtime.provisional_semantic_consolidation import ClaimVersion, ProvisionalSemanticGraphState, SemanticEdge


def _graph():
    return ProvisionalSemanticGraphState(
        graph_id="association-exploration-graph",
        claim_versions=(
            ClaimVersion("source", "claim-source", 1, "Capture rooftop runoff.", "pending_consolidation", (), (), (), (), "sha256:source", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("target", "claim-target", 1, "Route barrel overflow safely.", "pending_consolidation", (), (), (), (), "sha256:target", "2026-08-01T00:00:00+00:00"),
        ),
        edges=(SemanticEdge("depends", "depends_on", "target", "source", "2026-08-01T00:00:00+00:00"),),
    )


def _valid(_question, _lane):
    return {
        "executed": True,
        "model_id": "fake-local-model",
        "answer": '{"shared_structure":"Rooftop runoff enters the barrel before the overflow route handles surplus.","possible_implication":"The rooftop collection path constrains safe barrel overflow routing.","relation_limits":"This is a possible design relationship, not a causal fact.","uncertainty":"Local evidence does not establish a specific installation.","suggested_next_question":"Which installation constraints apply?"}',
    }


def test_approved_association_executes_once_and_records_only_provisional_evidence(tmp_path):
    graph = _graph()
    queued = queue_exploration(tmp_path, graph, candidate_id="candidate", originating_thread_id="thread", source_record_ids=("source", "target"), relation_edge_ids=("depends",), approval_request_id="approval")

    completed, updated = execute_once(tmp_path, graph, queued, executor=_valid)
    repeated, repeated_graph = execute_once(tmp_path, updated, completed, executor=_valid)
    ledger = LocalModelRequestResultLedger(tmp_path / "model-ledger")

    assert completed.lifecycle_state == "explored_pending_consolidation"
    assert repeated.lifecycle_state == "explored_pending_consolidation"
    assert repeated_graph.as_record() == updated.as_record()
    assert len(ledger.export_state()["requests"]) == 1
    request = next(iter(ledger.export_state()["requests"].values()))
    assert request["execution_attempt_count"] == 1
    assert graph.edges[0] in updated.edges
    assert any(edge.edge_type == "derived_from" for edge in updated.edges)
    assert graph.claim_versions[0] in updated.claim_versions
    assert any(completed.insight_experience_id in item.source_experience_refs for item in updated.claim_versions)
    insight = next(item for item in updated.experiences if item.experience_id == completed.insight_experience_id)
    assert insight.metadata["association_candidate_id"] == "candidate"
    assert insight.metadata["epistemic_state"] == "pending_consolidation"


def test_invalid_association_output_blocks_without_new_call_or_graph_mutation(tmp_path):
    graph = _graph()
    queued = queue_exploration(tmp_path, graph, candidate_id="candidate", originating_thread_id="thread", source_record_ids=("source", "target"), relation_edge_ids=("depends",), approval_request_id="approval")

    blocked, updated = execute_once(tmp_path, graph, queued, executor=lambda _q, _l: {"executed": True, "model_id": "fake", "answer": "This connection is validated."})

    assert blocked.lifecycle_state == "exploration_blocked"
    assert blocked.failure_reason == "typed_output_invalid"
    assert updated.as_record() == graph.as_record()
    request = next(iter(LocalModelRequestResultLedger(tmp_path / "model-ledger").export_state()["requests"].values()))
    assert request["execution_attempt_count"] == 1


def test_unsupported_absence_of_uncertainty_is_rejected(tmp_path):
    graph = _graph()
    queued = queue_exploration(tmp_path, graph, candidate_id="candidate", originating_thread_id="thread", source_record_ids=("source", "target"), relation_edge_ids=("depends",), approval_request_id="approval")
    answer = (
        '{"shared_structure":"Rooftop runoff enters the barrel before overflow routing.",'
        '"possible_implication":"The rooftop path influences barrel overflow routing.",'
        '"relation_limits":"The relation does not establish site drainage capacity.",'
        '"uncertainty":"There is no uncertainty about this relationship.",'
        '"suggested_next_question":"Where should surplus water be routed?"}'
    )

    blocked, updated = execute_once(tmp_path, graph, queued, executor=lambda _q, _l: {"executed": True, "model_id": "fake", "answer": answer})

    assert blocked.lifecycle_state == "exploration_blocked"
    assert updated.as_record() == graph.as_record()


def test_labeled_local_model_output_is_normalized_as_the_same_typed_contract(tmp_path):
    graph = _graph()
    queued = queue_exploration(tmp_path, graph, candidate_id="candidate", originating_thread_id="thread", source_record_ids=("source", "target"), relation_edge_ids=("depends",), approval_request_id="approval")
    answer = (
        "Shared_structure refers to rooftop runoff entering the barrel before overflow routing. "
        "Possible_implication is that the rooftop collection path constrains safe barrel routing. "
        "Relation_limits suggest that each barrel installation may differ. "
        "Uncertainty exists in the local installation details. "
        "Suggested_next_question could be: Which constraints apply here?"
    )

    completed, updated = execute_once(tmp_path, graph, queued, executor=lambda _q, _l: {"executed": True, "model_id": "fake", "answer": answer})

    assert completed.lifecycle_state == "explored_pending_consolidation"
    assert len(updated.experiences) == 1


def test_output_that_omits_one_source_claim_is_rejected(tmp_path):
    graph = _graph()
    queued = queue_exploration(tmp_path, graph, candidate_id="candidate", originating_thread_id="thread", source_record_ids=("source", "target"), relation_edge_ids=("depends",), approval_request_id="approval")
    answer = (
        '{"shared_structure":"Rooftop runoff is captured.",'
        '"possible_implication":"Collection can reduce runoff.",'
        '"relation_limits":"Roof conditions vary.",'
        '"uncertainty":"Local roof area is not recorded.",'
        '"suggested_next_question":"What roof area is available?"}'
    )

    blocked, updated = execute_once(tmp_path, graph, queued, executor=lambda _q, _l: {"executed": True, "model_id": "fake", "answer": answer})

    assert blocked.lifecycle_state == "exploration_blocked"
    assert updated.as_record() == graph.as_record()


def test_default_executor_uses_the_cognitive_operation_contract(monkeypatch, tmp_path):
    graph = _graph()
    queued = queue_exploration(tmp_path, graph, candidate_id="candidate", originating_thread_id="thread", source_record_ids=("source", "target"), relation_edge_ids=("depends",), approval_request_id="approval")
    captured = {}

    def infer(**kwargs):
        captured.update(kwargs)
        return _valid("", {})

    monkeypatch.setattr("orchestration.runtime.approved_association_exploration.execute_local_model_inference", infer)
    completed, _ = execute_once(tmp_path, graph, queued)

    assert completed.lifecycle_state == "explored_pending_consolidation"
    assert captured["task_type"] == "active_cognitive_json_operation"
    assert captured["metadata"]["execution_lane"] == "cognitive_operation"
    assert captured["metadata"]["operation_type"] == "approved_association_exploration"


def test_semicolon_delimited_qwen_output_with_uncertainty_is_accepted(tmp_path):
    graph = _graph()
    queued = queue_exploration(tmp_path, graph, candidate_id="candidate", originating_thread_id="thread", source_record_ids=("source", "target"), relation_edge_ids=("depends",), approval_request_id="approval")
    answer = (
        "shared_structure: A downspout transfers rooftop runoff into a rain barrel; "
        "possible_implication: The collection path constrains where surplus water begins; "
        "relation_limits: The path does not establish a site-safe discharge route; "
        "uncertainty: Local drainage conditions are not recorded; "
        "suggested_next_question: Where should surplus water be routed?"
    )

    completed, updated = execute_once(tmp_path, graph, queued, executor=lambda _q, _l: {"executed": True, "model_id": "fake", "answer": answer})

    assert completed.lifecycle_state == "explored_pending_consolidation"
    assert len(updated.experiences) == 1
