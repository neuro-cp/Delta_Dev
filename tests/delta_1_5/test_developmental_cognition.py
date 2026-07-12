from orchestration.runtime.delta_1_4_live_wikipedia_runtime import (
    WikipediaTextResult,
    handle_live_chat,
    start_live_wikipedia_runtime,
    wikipedia_query_from_message,
)
from orchestration.runtime.delta_1_5_developmental_cognition import (
    render_developmental_observation,
    run_wikipedia_developmental_cognition,
)


def _acid_base_transport(url: str, max_chars: int):
    assert "en.wikipedia.org" in url
    return {
        "title": "Acid-base reaction",
        "extract": (
            "In chemistry, an acid-base reaction is a chemical reaction that occurs between an acid and a base. "
            "It can be used to determine pH via titration. Several theoretical frameworks provide alternative "
            "conceptions of the reaction mechanisms; these are called the acid-base theories, for example, "
            "Bronsted-Lowry acid-base theory."
        )[:max_chars],
        "timestamp": "2026-01-01T00:00:00Z",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Acid-base_reaction"}},
    }


def _local_acid_base_snapshot(_query: str):
    return {
        "matched": True,
        "answer": "Acid Base Reactions Mechanism explains how acids and bases interact in chemistry.",
        "matches": [
            {
                "concept_name": "Acid Base Reactions Mechanism",
                "domain": "Chemistry",
                "memory_type": "knowledge",
                "short_definition": "Explains how acids and bases interact in chemistry.",
                "propositions": ["Acid base reactions involve acids and bases."],
                "related_concepts": ["Acid Base Reactions Measurement"],
            }
        ],
        "scores": [],
        "search_query": "acid-base reaction",
    }


def test_developmental_cognition_detects_higher_resolution_wikipedia_evidence():
    evidence = WikipediaTextResult(
        query="acid-base reaction",
        title="Acid-base reaction",
        extract=_acid_base_transport("https://en.wikipedia.org/wiki/Acid-base_reaction", 6000)["extract"],
        canonical_url="https://en.wikipedia.org/wiki/Acid-base_reaction",
        retrieved_at="2026-01-01T00:00:00Z",
    )

    result = run_wikipedia_developmental_cognition(evidence, local_query=_local_acid_base_snapshot)

    assert result.comparison.classification == "HIGHER_RESOLUTION"
    assert "titration" in result.comparison.novel_terms
    assert "Bronsted-Lowry acid-base theory" in result.comparison.novel_terms
    assert result.promotion_candidate.approval_required is True
    assert result.promotion_candidate.automatic_memory_write is False
    assert result.operator_inquiry.blocks_promotion is True
    assert result.safety["provider_calls_performed"] is False
    assert result.safety["canonical_write_performed"] is False


def test_developmental_observation_renders_operator_gate():
    evidence = WikipediaTextResult(
        query="acid-base reaction",
        title="Acid-base reaction",
        extract=_acid_base_transport("https://en.wikipedia.org/wiki/Acid-base_reaction", 6000)["extract"],
        canonical_url="https://en.wikipedia.org/wiki/Acid-base_reaction",
        retrieved_at="2026-01-01T00:00:00Z",
    )

    result = run_wikipedia_developmental_cognition(evidence, local_query=_local_acid_base_snapshot)
    rendered = render_developmental_observation(result)

    assert "Developmental observation" in rendered
    assert "Approve preparing a noncanonical expansion proposal" in rendered
    assert "No memory was written" in rendered


def test_live_wikipedia_intent_handles_operator_phrase():
    assert wikipedia_query_from_message("tell me what wikipedia has regarding acid base reactions?") == "acid base reactions"
    assert wikipedia_query_from_message("What does Wikipedia say about acid-base reaction?") == "acid-base reaction"


def test_live_lookup_surfaces_developmental_candidate_and_inquiry():
    session = start_live_wikipedia_runtime(runtime_id="delta15-live")
    session, response = handle_live_chat(
        session,
        "tell me what wikipedia has regarding acid base reactions?",
        wikipedia_transport=_acid_base_transport,
    )

    assert response.route == "live_wikipedia_text_retrieval"
    assert "Developmental observation" in response.answer
    assert response.payload["developmental_cognition"]["promotion_candidate"]["approval_required"] is True
    assert response.payload["promotion_candidate"]["automatic_memory_write"] is False
    assert response.payload["operator_inquiry"]["blocks_promotion"] is True
    assert len(session.operator_inquiries) == 1
    assert session.memory_write_performed is False


def test_remember_that_uses_governed_promotion_gate_not_memory_write():
    session = start_live_wikipedia_runtime(runtime_id="delta15-memory-gate")
    session, _first = handle_live_chat(session, "Wikipedia: Acid-base reaction", wikipedia_transport=_acid_base_transport)
    session, second = handle_live_chat(session, "remember that")

    assert second.route == "live_memory_governance"
    assert "cannot write memory automatically" in second.answer
    assert "gated promotion candidate" in second.answer
    assert second.payload["memory_candidate"] is None
    assert second.payload["promotion_candidate"]["approval_required"] is True
    assert session.memory_write_performed is False


def test_budget_exhaustion_does_not_fall_through_to_concept_router():
    session = start_live_wikipedia_runtime(runtime_id="delta15-budget", max_wikipedia_queries=1)
    session, _first = handle_live_chat(session, "Wikipedia: Acid-base reaction", wikipedia_transport=_acid_base_transport)
    session, second = handle_live_chat(session, "Look up acid-base reaction on Wikipedia", wikipedia_transport=_acid_base_transport)

    assert second.route == "live_wikipedia_budget_exhausted"
    assert "I did not retrieve another page" in second.answer
    assert "I know about Acid Base" not in second.answer
    assert second.payload["external_retrieval_performed"] is False
    assert session.retrieval_count == 1


def test_live_help_does_not_route_to_concept_memory():
    session = start_live_wikipedia_runtime(runtime_id="delta15-help")
    session, response = handle_live_chat(session, "how do i interact with you")

    assert response.route == "live_runtime_help"
    assert "Wikipedia text lookup" in response.answer
    assert "I know about" not in response.answer
    assert session.retrieval_count == 0
