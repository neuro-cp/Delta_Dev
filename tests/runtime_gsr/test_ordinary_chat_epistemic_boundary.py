import pytest

from orchestration.runtime.epistemic_answer_mode import resolve_epistemic_answer_mode
from orchestration.runtime.provisional_semantic_consolidation import ClaimVersion, ProvisionalSemanticGraphState
from orchestration.runtime.rc2_conversational_mode_router import route_message


@pytest.mark.parametrize(("message", "expected"), (
    ("What is 2 + 2?", "4"),
    ("What is water made of?", "H2O"),
    ("Explain gravity simply.", "attraction"),
    ("What color is the sky?", "blue"),
))
def test_unbound_everyday_questions_remain_ordinary_conversation(message, expected):
    payload = route_message("Conversation", message)
    assert payload["route"] in {"ordinary_local_reasoning", "local_conversation_model_lane"}
    assert expected.lower() in payload["answer"].lower()
    assert payload.get("local_model_offer") is None
    assert "learned local knowledge" not in payload["answer"].lower()
    assert payload.get("canonical_write_performed") is False


def test_explicitly_bound_provisional_claim_uses_epistemic_mode_without_affecting_plain_chat():
    graph = ProvisionalSemanticGraphState(
        graph_id="bound-claim",
        claim_versions=(ClaimVersion("claim-v1", "claim", 1, "A provisional DELTA claim.", "pending_consolidation", (), (), (), (), "sha256:claim", "2026-08-02T00:00:00+00:00"),),
    )
    assert resolve_epistemic_answer_mode(graph, ("claim-v1",)) == "consolidation_in_progress"
    assert resolve_epistemic_answer_mode(graph, ()) == "ordinary_conversation"
