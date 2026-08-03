from orchestration.runtime.approved_revisit_reinquiry import execute_once, queue_reinquiry
from orchestration.runtime.provisional_semantic_consolidation import ProvisionalSemanticGraphState, SemanticExperience


def _answer(_question, _lane):
    return {"executed": True, "model_id": "fake", "answer": '{"revised_proposition":"Use a narrower relation.","retained_supported_portion":"Both items manage flow.","discarded_or_corrected_portion":"The earlier causal claim was too broad.","evidence_still_missing":"Installation data.","uncertainty":"The local record is incomplete.","possible_next_question":"Which installation applies?"}'}


def test_revisit_executes_once_and_preserves_original_insight(tmp_path):
    original = SemanticExperience("insight-1", "local_model_output", "provisional", "old", (), "2026-08-02T00:00:00+00:00", "sha256:old")
    graph = ProvisionalSemanticGraphState(graph_id="g", experiences=(original,))
    queued = queue_reinquiry(tmp_path, candidate_id="candidate", approval_request_id="approval", original_insight_id="insight-1", review_id="review", packet_id="packet", overlay_id="overlay", weakness="too broad")

    completed, updated = execute_once(tmp_path, graph, queued, executor=_answer)
    repeated, replayed = execute_once(tmp_path, updated, completed, executor=_answer)

    assert completed.lifecycle_state == "revisited_pending_consolidation"
    assert repeated.lifecycle_state == "revisited_pending_consolidation"
    assert len(updated.experiences) == 2
    assert replayed.as_record() == updated.as_record()
    revised = next(item for item in updated.experiences if item.experience_id == completed.revised_insight_id)
    assert revised.metadata["revises_insight_id"] == "insight-1"
    assert original in updated.experiences


def test_revisit_invalid_output_blocks_without_graph_mutation(tmp_path):
    graph = ProvisionalSemanticGraphState(graph_id="g")
    queued = queue_reinquiry(tmp_path, candidate_id="candidate", approval_request_id="approval", original_insight_id="insight", review_id="review", packet_id="packet", overlay_id="overlay", weakness="too broad")
    blocked, updated = execute_once(tmp_path, graph, queued, executor=lambda *_: {"executed": True, "model_id": "fake", "answer": "invalid"})
    assert blocked.lifecycle_state == "revisit_blocked_invalid_output"
    assert updated.as_record() == graph.as_record()


def test_labeled_revisit_output_uses_the_same_typed_contract(tmp_path):
    graph = ProvisionalSemanticGraphState(graph_id="g")
    queued = queue_reinquiry(tmp_path, candidate_id="candidate", approval_request_id="approval", original_insight_id="insight", review_id="review", packet_id="packet", overlay_id="overlay", weakness="too broad")
    answer = "Revised_proposition: Narrow the relation. Retained_supported_portion: Both items manage flow. Discarded_or_corrected_portion: The causal wording was too broad. Evidence_still_missing: Installation data. Uncertainty: Local context is incomplete. Possible_next_question: Which installation applies?"
    completed, _ = execute_once(tmp_path, graph, queued, executor=lambda *_: {"executed": True, "model_id": "fake", "answer": answer})
    assert completed.lifecycle_state == "revisited_pending_consolidation"
