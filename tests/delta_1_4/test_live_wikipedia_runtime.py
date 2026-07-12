from orchestration.runtime.delta_1_4_live_wikipedia_runtime import (
    handle_live_chat,
    retrieve_wikipedia_text,
    start_live_wikipedia_runtime,
    stop_live_wikipedia_runtime,
    wikipedia_query_from_message,
)


def _fake_transport(url: str, max_chars: int):
    assert "en.wikipedia.org" in url
    return {
        "title": "Ada Lovelace",
        "extract": "Ada Lovelace was an English mathematician and writer, chiefly known for her work on Charles Babbage's Analytical Engine."[:max_chars],
        "timestamp": "2026-01-01T00:00:00Z",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Ada_Lovelace"}},
    }


def test_wikipedia_query_extraction_is_bounded():
    assert wikipedia_query_from_message("Wikipedia: Ada Lovelace") == "Ada Lovelace"
    assert wikipedia_query_from_message("Look up Ada Lovelace on Wikipedia.") == "Ada Lovelace"
    assert wikipedia_query_from_message("Who is Ada Lovelace?") == "Ada Lovelace"
    assert wikipedia_query_from_message("Thanks, that makes sense.") == ""


def test_retrieve_wikipedia_text_uses_text_summary_only():
    result = retrieve_wikipedia_text("Ada Lovelace", transport=_fake_transport)

    assert result.title == "Ada Lovelace"
    assert "Analytical Engine" in result.extract
    assert result.canonical_url.endswith("Ada_Lovelace")
    assert result.media_retrieved is False
    assert result.external_links_followed is False
    assert result.safety["external_retrieval_performed"] is True
    assert result.safety["network_calls_performed"] is True
    assert result.safety["provider_calls_performed"] is False


def test_live_runtime_start_enables_wikipedia_surface_without_provider():
    session = start_live_wikipedia_runtime(runtime_id="test")

    surface = session.runtime.future_surfaces[0]
    assert session.active is True
    assert surface.capability == "WIKIPEDIA_TEXT_READ_ONLY"
    assert surface.state == "ACTIVE"
    assert surface.retrieval_implemented is True
    assert surface.network_code_present is True
    assert surface.provider_present is False
    assert session.wikipedia_profile.enabled is True
    assert session.wikipedia_profile.network_calls_allowed is True
    assert session.provider_calls_performed is False


def test_live_chat_can_use_wikipedia_then_respects_query_budget():
    session = start_live_wikipedia_runtime(runtime_id="chat")
    session, first = handle_live_chat(
        session,
        "Wikipedia: Ada Lovelace",
        wikipedia_transport=_fake_transport,
    )

    assert first.route == "live_wikipedia_text_retrieval"
    assert "Ada Lovelace" in first.answer
    assert "No provider was called" in first.answer
    assert session.retrieval_count == 1
    assert first.payload["external_retrieval_performed"] is True
    assert first.payload["provider_calls_performed"] is False
    assert first.payload["memory_candidate"] is None

    session, second = handle_live_chat(
        session,
        "Wikipedia: Grace Hopper",
        wikipedia_transport=_fake_transport,
    )
    assert session.retrieval_count == 1
    assert second.route != "live_wikipedia_text_retrieval"
    assert "query budget is already used" in second.answer


def test_live_chat_falls_back_to_router_without_retrieval_for_ordinary_turn():
    session = start_live_wikipedia_runtime(runtime_id="fallback")
    session, response = handle_live_chat(session, "What do you think makes a good debugging partner?")

    assert response.wikipedia_result is None
    assert response.payload["provider_calls_performed"] is False
    assert session.retrieval_count == 0
    assert "debugging partner" in response.answer.lower()


def test_stop_live_runtime_disables_session():
    session = start_live_wikipedia_runtime(runtime_id="stop")
    stopped = stop_live_wikipedia_runtime(session)

    assert stopped.active is False
    assert stopped.runtime.state == "IDLE"
