from orchestration.runtime.delta_1_4_live_wikipedia_runtime import (
    handle_live_chat,
    retrieve_wikipedia_text,
    start_live_wikipedia_runtime,
    stop_live_wikipedia_runtime,
    wikipedia_query_from_message,
)
from orchestration.runtime.live_runtime_behavioral_campaign import run_adaptive_live_runtime_campaign


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
    assert wikipedia_query_from_message("Tell me what Wikipedia has regarding Ada Lovelace.") == "Ada Lovelace"
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
    assert session.wikipedia_profile.max_queries_per_objective == 0
    assert session.provider_calls_performed is False


def test_live_chat_can_use_wikipedia_then_respects_query_budget():
    session = start_live_wikipedia_runtime(runtime_id="chat", max_wikipedia_queries=3)
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
    assert first.payload["memory_candidate"]["source_type"] == "live_wikipedia_promotion_candidate"
    assert first.payload["promotion_candidate"]["approval_required"] is True

    session, second = handle_live_chat(
        session,
        "Wikipedia: Grace Hopper",
        wikipedia_transport=_fake_transport,
    )
    assert second.route == "live_wikipedia_text_retrieval"
    assert session.retrieval_count == 2
    session, third = handle_live_chat(
        session,
        "Wikipedia: Katherine Johnson",
        wikipedia_transport=_fake_transport,
    )
    assert third.route == "live_wikipedia_text_retrieval"
    assert session.retrieval_count == 3
    session, fourth = handle_live_chat(
        session,
        "Wikipedia: Margaret Hamilton",
        wikipedia_transport=_fake_transport,
    )
    assert session.retrieval_count == 3
    assert fourth.route == "live_wikipedia_budget_exhausted"
    assert "I did not retrieve another page" in fourth.answer


def test_default_live_wikipedia_budget_is_unlimited_but_transport_can_be_fake():
    session = start_live_wikipedia_runtime(runtime_id="unlimited")
    for index in range(5):
        session, response = handle_live_chat(
            session,
            f"Wikipedia: Topic {index}",
            wikipedia_transport=_fake_transport,
        )
        assert response.route == "live_wikipedia_text_retrieval"
    assert session.retrieval_count == 5


def test_live_promotion_approval_prepares_review_proposal_and_keeps_memory_gated():
    session = start_live_wikipedia_runtime(runtime_id="approval")
    session, first = handle_live_chat(session, "Wikipedia: Ada Lovelace", wikipedia_transport=_fake_transport)

    assert first.payload["memory_candidate"]
    assert session.operator_inquiries
    session, approval = handle_live_chat(session, "yes", wikipedia_transport=_fake_transport)

    assert approval.route == "live_promotion_approval"
    assert session.prepared_review_proposals
    assert session.prepared_review_proposals[-1]["status"] == "PREPARED_FOR_OPERATOR_REVIEW"
    assert approval.payload["memory_candidate"]["operator_review_required"] is True
    assert "No memory was written" in approval.answer
    assert session.memory_write_performed is False
    assert session.canonical_write_performed is False
    session, pending = handle_live_chat(session, "What are your pending inquiries?")
    assert "No pending operator inquiries" in pending.answer


def test_live_promotion_approval_handles_punctuated_prepare_variant():
    session = start_live_wikipedia_runtime(runtime_id="approval-punctuation")
    session, _first = handle_live_chat(session, "Wikipedia: Ada Lovelace", wikipedia_transport=_fake_transport)
    session, approval = handle_live_chat(session, "okay, prepare it", wikipedia_transport=_fake_transport)

    assert approval.route == "live_promotion_approval"
    assert len(session.prepared_review_proposals) == 1
    assert session.memory_write_performed is False


def test_live_pending_inquiries_are_rendered_from_session_queue():
    session = start_live_wikipedia_runtime(runtime_id="pending")
    session, _first = handle_live_chat(session, "Wikipedia: Ada Lovelace", wikipedia_transport=_fake_transport)
    session, response = handle_live_chat(session, "What are your pending inquiries?")

    assert response.route == "live_pending_inquiries"
    assert "Pending inquiries" in response.answer
    assert "Approve preparing" in response.answer


def test_ambiguous_approval_requires_specific_candidate_then_accepts_selection():
    session = start_live_wikipedia_runtime(runtime_id="ambiguous")
    session, _first = handle_live_chat(session, "Wikipedia: Ada Lovelace", wikipedia_transport=_fake_transport)
    session, _second = handle_live_chat(session, "Wikipedia: Grace Hopper", wikipedia_transport=_fake_transport)
    session, ambiguous = handle_live_chat(session, "approve that", wikipedia_transport=_fake_transport)

    assert ambiguous.route == "live_promotion_approval_ambiguous"
    assert "multiple pending" in ambiguous.answer
    assert not session.prepared_review_proposals

    session, approved = handle_live_chat(session, "approve first", wikipedia_transport=_fake_transport)
    assert approved.route == "live_promotion_approval"
    assert len(session.prepared_review_proposals) == 1


def test_partial_candidate_title_selects_pending_candidate_without_silent_guess():
    session = start_live_wikipedia_runtime(runtime_id="partial-title")
    session, _first = handle_live_chat(session, "Wikipedia: Ada Lovelace", wikipedia_transport=_fake_transport)
    session, _second = handle_live_chat(session, "Wikipedia: Grace Hopper", wikipedia_transport=_fake_transport)
    session, ambiguous = handle_live_chat(session, "not that one", wikipedia_transport=_fake_transport)

    assert ambiguous.route == "live_promotion_rejection_ambiguous"

    session, selected = handle_live_chat(session, "approve Ada Lovelace local knowledge review", wikipedia_transport=_fake_transport)
    assert selected.route == "live_promotion_approval"
    assert len(session.prepared_review_proposals) == 1


def test_live_wikipedia_transport_failure_fails_closed_without_candidate():
    def failing_transport(_url: str, _max_chars: int):
        raise TimeoutError("synthetic timeout")

    session = start_live_wikipedia_runtime(runtime_id="wiki-failure")
    session, response = handle_live_chat(session, "Wikipedia: Missing page deterministic case", wikipedia_transport=failing_transport)

    assert response.route == "live_wikipedia_retrieval_failed"
    assert "failed safely" in response.answer
    assert response.payload["memory_candidate"] is None
    assert session.retrieval_count == 0
    assert session.memory_write_performed is False


def test_suspended_live_runtime_blocks_background_continuation_and_model_offer():
    session = start_live_wikipedia_runtime(runtime_id="suspend")
    session, _response = handle_live_chat(session, "Suspend runtime")
    session, blocked = handle_live_chat(session, "Try to continue the background initiative.")

    assert session.autonomy_status == "SUSPENDED"
    assert blocked.route == "live_runtime_suspended"
    assert "suspended" in blocked.answer.lower()
    assert "local model" not in blocked.answer.lower()


def test_adaptive_live_runtime_behavioral_campaign_passes_without_real_wikipedia():
    result = run_adaptive_live_runtime_campaign(max_scenarios=18)

    assert result.passed is True
    assert result.coverage["pathology_count"] == 0
    assert "live_wikipedia_text_retrieval" in result.coverage["unique_routes"]
    assert result.coverage["network_policy"].startswith("bulk campaign uses deterministic fake Wikipedia")


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
