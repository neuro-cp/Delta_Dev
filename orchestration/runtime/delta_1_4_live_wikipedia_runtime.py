"""Operator-started live runtime bridge with bounded Wikipedia text retrieval.

The bridge keeps Wikipedia as a session-scoped capability. It is inactive until
the operator starts the live runtime, uses only one text summary request per
turn, records provenance, and falls back to the existing router for ordinary
conversation. It does not call providers, write memory, commit, push, schedule
work, or retrieve media.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import json
import re
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now
from orchestration.runtime.delta_1_1_development_loop import WikipediaPermissionProfile
from orchestration.runtime.delta_1_2_live_runtime import (
    FutureSurfaceReadiness,
    LiveRuntimeConfig,
    LiveRuntimeState,
    append_journal,
    boot_live_runtime,
    create_event,
    enqueue_event,
    run_wake_cycle,
)
from orchestration.runtime.continuous_runtime_controller import (
    ContinuousRuntimeController,
    controller_snapshot,
    enqueue_continuous_event,
    make_continuous_event,
    pause_controller,
    resume_controller,
    run_controller_cycle,
    shutdown_controller,
    start_continuous_runtime_controller,
    suspend_controller,
)
from orchestration.runtime.delta_1_5_developmental_cognition import (
    DevelopmentalCognitionResult,
    render_developmental_observation,
    run_wikipedia_developmental_cognition,
)
from orchestration.runtime.delta_1_6_operational_autonomy import (
    AuthorityDecision,
    BackgroundCycleResult,
    IdentityProposal,
    Initiative,
    OperationalSelfModel,
    answer_operational_self_model_question,
    build_operational_self_model,
    is_operational_self_model_question,
    run_delta_1_6_background_cycle,
    set_autonomy_status,
)
from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message


WikipediaTransport = Callable[[str, int], dict[str, Any]]


@dataclass(frozen=True)
class WikipediaTextResult:
    query: str
    title: str
    extract: str
    canonical_url: str
    retrieved_at: str
    source: str = "wikipedia_rest_summary"
    revision_timestamp: str = ""
    chars_used: int = 0
    retrieval_performed: bool = True
    media_retrieved: bool = False
    external_links_followed: bool = False
    safety: dict[str, bool] = field(default_factory=lambda: {
        **safety_metadata(),
        "external_retrieval_performed": True,
        "network_calls_performed": True,
    })


@dataclass(frozen=True)
class LiveChatResponse:
    answer: str
    route: str
    payload: dict[str, Any]
    wikipedia_result: WikipediaTextResult | None
    runtime_state: str
    safety: dict[str, bool]


@dataclass(frozen=True)
class LiveWikipediaRuntimeSession:
    session_id: str
    runtime: LiveRuntimeState
    wikipedia_profile: WikipediaPermissionProfile
    active: bool
    started_at: str
    turns: tuple[LiveChatResponse, ...] = ()
    developmental_results: tuple[DevelopmentalCognitionResult, ...] = ()
    promotion_candidates: tuple[dict[str, Any], ...] = ()
    operator_inquiries: tuple[dict[str, Any], ...] = ()
    operational_self_model: OperationalSelfModel | None = None
    initiatives: tuple[Initiative, ...] = ()
    authority_decisions: tuple[AuthorityDecision, ...] = ()
    identity_proposals: tuple[IdentityProposal, ...] = ()
    last_background_cycle: BackgroundCycleResult | None = None
    identity_status: str = "UNDEFINED"
    autonomy_status: str = "ACTIVE"
    continuous_controller: ContinuousRuntimeController | None = None
    retrieval_count: int = 0
    provider_calls_performed: bool = False
    memory_write_performed: bool = False
    canonical_write_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def activated_wikipedia_profile() -> WikipediaPermissionProfile:
    return WikipediaPermissionProfile(
        enabled=True,
        network_calls_allowed=True,
        max_queries_per_objective=1,
        max_pages_per_query=1,
        max_total_characters=6000,
        operator_approval_required=True,
        persistence="ephemeral_session_only",
    )


def start_live_wikipedia_runtime(
    *,
    runtime_id: str = "delta-live-ui",
    resident_model_id: str | None = None,
    resident_lane: str | None = None,
    residency_status: str = "unknown",
) -> LiveWikipediaRuntimeSession:
    config = LiveRuntimeConfig(
        runtime_id=stable_id("delta14-live-runtime", runtime_id),
        mode="DEVELOPMENT_SESSION",
        network_enabled=True,
        provider_enabled=False,
        timers_enabled=False,
    )
    runtime = boot_live_runtime(config)
    surface = FutureSurfaceReadiness(
        capability="WIKIPEDIA_TEXT_READ_ONLY",
        state="ACTIVE",
        permission_profile=activated_wikipedia_profile(),
        dependencies=("operator_started_live_runtime", "text_summary_endpoint", "per_turn_query_budget", "provenance_required"),
        retrieval_implemented=True,
        network_code_present=True,
        provider_present=False,
    )
    runtime = replace(runtime, future_surfaces=(surface,))
    queue = enqueue_event(
        runtime.event_queue,
        create_event("runtime_startup", "Operator started live runtime with bounded Wikipedia text retrieval.", source="delta_1_4_ui"),
    )
    runtime = run_wake_cycle(replace(runtime, event_queue=queue))
    session = LiveWikipediaRuntimeSession(
        session_id=stable_id("delta14-session", runtime.runtime_id, utc_now()),
        runtime=runtime,
        wikipedia_profile=surface.permission_profile,
        active=True,
        started_at=utc_now(),
    )
    controller = start_continuous_runtime_controller(
        session_id=session.session_id,
        resident_model_id=resident_model_id,
        resident_lane=resident_lane,
        residency_status=residency_status,
    )
    return replace(session, operational_self_model=build_operational_self_model(session=session), continuous_controller=controller)


def stop_live_wikipedia_runtime(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    event = create_event("runtime_shutdown", "Operator stopped live Wikipedia runtime.", source="delta_1_4_ui")
    queue = enqueue_event(session.runtime.event_queue, event)
    runtime = run_wake_cycle(replace(session.runtime, event_queue=queue))
    journal = append_journal(runtime.journal, "live_runtime_stop", "Live Wikipedia runtime stopped by operator.", (), runtime.cycle)
    controller = shutdown_controller(session.continuous_controller) if session.continuous_controller else None
    return replace(session, runtime=replace(runtime, journal=journal, state="IDLE"), active=False, continuous_controller=controller)


def handle_live_chat(
    session: LiveWikipediaRuntimeSession,
    message: str,
    *,
    history: list[dict[str, str]] | None = None,
    developer_overlay: bool = False,
    wikipedia_transport: WikipediaTransport | None = None,
) -> tuple[LiveWikipediaRuntimeSession, LiveChatResponse]:
    if not session.active:
        payload = route_message("Conversation", message, history=history, execute_local_model=False)
        answer = render_route(payload, developer_overlay=developer_overlay)
        response = _response(answer, "inactive_fallback", payload, None, session.runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    event = create_event("operator_message", message, source="ui_live_chat", payload={"live_runtime": True})
    runtime = run_wake_cycle(replace(session.runtime, event_queue=enqueue_event(session.runtime.event_queue, event)))
    session = _advance_continuous_controller(replace(session, runtime=runtime), "OPERATOR_MESSAGE", {"message": message}, priority=70)
    runtime = session.runtime

    if _is_live_help_request(message):
        answer = _render_live_help()
        payload = {
            "mode": "Live Runtime",
            "route": "live_runtime_help",
            "answer": answer,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": False,
            "network_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
            "promotion_candidate": None,
        }
        response = _response(answer, "live_runtime_help", payload, None, runtime.state, safety_metadata())
        return replace(session, runtime=runtime, turns=session.turns + (response,)), response

    if _is_memory_request(message):
        answer, payload = _render_memory_gate(session)
        response = _response(answer, "live_memory_governance", payload, None, runtime.state, safety_metadata())
        return replace(session, runtime=runtime, turns=session.turns + (response,)), response

    if is_operational_self_model_question(message):
        updated_session, cycle = run_delta_1_6_background_cycle(replace(session, runtime=runtime))
        answer = answer_operational_self_model_question(message, updated_session)
        payload = {
            "mode": "Live Runtime",
            "route": "live_operational_self_model",
            "answer": answer,
            "operational_self_model": updated_session.operational_self_model.as_dict() if updated_session.operational_self_model else {},
            "background_cycle": cycle.as_dict(),
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": False,
            "network_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
            "promotion_candidate": updated_session.promotion_candidates[-1] if updated_session.promotion_candidates else None,
            "operator_inquiry": updated_session.operator_inquiries[-1] if updated_session.operator_inquiries else None,
        }
        response = _response(answer, "live_operational_self_model", payload, None, updated_session.runtime.state, safety_metadata())
        return replace(updated_session, turns=updated_session.turns + (response,)), response

    if _is_live_context_declaration(message):
        answer = "Noted as live-session context. I will treat this as operator-provided behavioral evidence for this session only; no memory was written."
        payload = {
            "mode": "Live Runtime",
            "route": "live_context_declaration",
            "answer": answer,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": False,
            "network_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
            "promotion_candidate": None,
        }
        runtime = replace(
            runtime,
            journal=append_journal(runtime.journal, "live_context_declaration", message[:500], (), runtime.cycle),
        )
        response = _response(answer, "live_context_declaration", payload, None, runtime.state, safety_metadata())
        updated = _advance_continuous_controller(replace(session, runtime=runtime), "DEVELOPMENTAL_SIGNAL", {"summary": "operator live context declaration", "title": "Live context declaration"}, priority=40)
        return replace(updated, turns=updated.turns + (response,)), response

    query = wikipedia_query_from_message(message)
    if query and session.retrieval_count < session.wikipedia_profile.max_queries_per_objective:
        result = retrieve_wikipedia_text(query, profile=session.wikipedia_profile, transport=wikipedia_transport)
        development = run_wikipedia_developmental_cognition(result)
        development_payload = development.as_dict()
        answer = render_wikipedia_answer(message, result)
        answer += "\n\n" + render_developmental_observation(development)
        if developer_overlay:
            answer += "\n\n--- Developer Overlay ---\nRoute: live_wikipedia_text_retrieval\n"
            answer += "Wikipedia result:\n" + json.dumps(asdict(result), indent=2, sort_keys=True)
            answer += "\nDevelopmental cognition:\n" + json.dumps(development_payload, indent=2, sort_keys=True)
        payload = {
            "mode": "Live Runtime",
            "route": "live_wikipedia_text_retrieval",
            "answer": answer,
            "wikipedia_result": asdict(result),
            "developmental_cognition": development_payload,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": True,
            "network_calls_performed": True,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
            "promotion_candidate": development_payload["promotion_candidate"],
            "operator_inquiry": development_payload["operator_inquiry"],
        }
        runtime = replace(
            runtime,
            journal=append_journal(runtime.journal, "wikipedia_retrieval", f"Retrieved Wikipedia text for {result.title}.", (result.canonical_url,), runtime.cycle),
        )
        runtime = replace(
            runtime,
            journal=append_journal(runtime.journal, "developmental_observation", development.observation, (result.canonical_url,), runtime.cycle),
        )
        session = _advance_continuous_controller(
            replace(session, runtime=runtime),
            "WIKIPEDIA_RESULT",
            {"title": result.title, "url": result.canonical_url, "classification": development.comparison.classification},
            priority=75,
            correlation_id=development.cycle_id,
        )
        session = _advance_continuous_controller(
            session,
            "PROMOTION_CANDIDATE",
            {"title": development.promotion_candidate.title, "prompt": development.operator_inquiry.prompt},
            priority=72,
            correlation_id=development.promotion_candidate.candidate_id,
            objective_id=development.objective.objective_id,
        )
        runtime = session.runtime
        response = _response(answer, "live_wikipedia_text_retrieval", payload, result, runtime.state, _retrieval_safety())
        updated_session = replace(
            session,
            runtime=runtime,
            turns=session.turns + (response,),
            developmental_results=session.developmental_results + (development,),
            promotion_candidates=session.promotion_candidates + (development_payload["promotion_candidate"],),
            operator_inquiries=session.operator_inquiries + (development_payload["operator_inquiry"],),
            retrieval_count=session.retrieval_count + 1,
        )
        updated_session, cycle = run_delta_1_6_background_cycle(updated_session)
        updated_session = replace(updated_session, continuous_controller=run_controller_cycle(updated_session.continuous_controller, session=updated_session) if updated_session.continuous_controller else None)
        payload["operational_self_model"] = updated_session.operational_self_model.as_dict() if updated_session.operational_self_model else {}
        payload["background_cycle"] = cycle.as_dict()
        payload["continuous_controller"] = controller_snapshot(updated_session.continuous_controller) if updated_session.continuous_controller else {}
        response = _response(answer, "live_wikipedia_text_retrieval", payload, result, updated_session.runtime.state, _retrieval_safety())
        return replace(updated_session, turns=updated_session.turns[:-1] + (response,)), response

    if query and session.retrieval_count >= session.wikipedia_profile.max_queries_per_objective:
        answer = _render_budget_exhausted(session)
        payload = {
            "mode": "Live Runtime",
            "route": "live_wikipedia_budget_exhausted",
            "answer": answer,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": False,
            "network_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
            "promotion_candidate": session.promotion_candidates[-1] if session.promotion_candidates else None,
            "operator_inquiry": session.operator_inquiries[-1] if session.operator_inquiries else None,
        }
        response = _response(answer, "live_wikipedia_budget_exhausted", payload, None, runtime.state, safety_metadata())
        updated = _advance_continuous_controller(replace(session, runtime=runtime), "RESOURCE_LIMIT_REACHED", {"summary": "Wikipedia session query budget exhausted"}, priority=65)
        return replace(updated, turns=updated.turns + (response,)), response

    payload = route_message("Conversation", message, history=history, execute_local_model=False)
    answer = render_route(payload, developer_overlay=developer_overlay)
    response = _response(answer, str(payload.get("route") or "conversation_fallback"), payload, None, runtime.state, safety_metadata())
    updated = _advance_continuous_controller(replace(session, runtime=runtime), "VALIDATION_RESULT", {"summary": "ordinary chat routed without continuous work"}, priority=20)
    return replace(updated, turns=updated.turns + (response,)), response


def wikipedia_query_from_message(message: str) -> str:
    text = " ".join(str(message or "").strip().strip(" .?!").split())
    lower = text.lower()
    patterns = (
        r"^(?:wikipedia|wiki)\s*[:\-]?\s*(.+)$",
        r"tell me what wikipedia has (?:regarding|about|on)\s+(.+)$",
        r"what does wikipedia (?:have|say) (?:regarding|about|on)\s+(.+)$",
        r"what has wikipedia got (?:regarding|about|on)\s+(.+)$",
        r"look up\s+(.+?)(?:\s+on wikipedia)?$",
        r"retrieve\s+(.+?)(?:\s+from wikipedia)?$",
        r"tell me about\s+(.+)$",
        r"what is\s+(.+)$",
        r"who is\s+(.+)$",
    )
    if not any(term in lower for term in ("wikipedia", "wiki", "look up", "retrieve", "what is", "who is", "tell me about")):
        return ""
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            query = re.sub(r"\b(on|from)\s+wikipedia\b", "", match.group(1), flags=re.IGNORECASE).strip(" ?.!")
            return _clean_query(query)
    return ""


def retrieve_wikipedia_text(
    query: str,
    *,
    profile: WikipediaPermissionProfile | None = None,
    transport: WikipediaTransport | None = None,
) -> WikipediaTextResult:
    profile = profile or activated_wikipedia_profile()
    if not profile.enabled or not profile.network_calls_allowed:
        raise PermissionError("Wikipedia retrieval is not enabled for this live runtime session.")
    clean_query = _clean_query(query)
    if not clean_query:
        raise ValueError("Wikipedia query is empty.")
    page_title = clean_query.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(page_title, safe='')}"
    data = transport(url, profile.max_total_characters) if transport else _default_wikipedia_transport(url, profile.max_total_characters)
    extract = " ".join(str(data.get("extract") or "").split())[: profile.max_total_characters]
    title = str(data.get("title") or clean_query).strip()
    canonical = str(((data.get("content_urls") or {}).get("desktop") or {}).get("page") or f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='/_:')}")
    return WikipediaTextResult(
        query=clean_query,
        title=title,
        extract=extract or "Wikipedia returned no text extract for this page.",
        canonical_url=canonical,
        retrieved_at=utc_now(),
        revision_timestamp=str(data.get("timestamp") or ""),
        chars_used=len(extract),
    )


def render_wikipedia_answer(message: str, result: WikipediaTextResult) -> str:
    return "\n".join([
        f"Wikipedia says: {result.title}",
        "",
        result.extract,
        "",
        f"Source: {result.canonical_url}",
        "",
        "This is external Wikipedia text evidence, not canonical DELTA memory. No provider was called and no memory was written.",
    ])


def _default_wikipedia_transport(url: str, max_chars: int) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "DELTA-governed-runtime/1.0 (operator-started local experiment)"})
    try:
        with urlopen(request, timeout=8) as response:  # noqa: S310 - bounded operator-started Wikipedia-only retrieval
            raw = response.read(max_chars + 4096).decode("utf-8", errors="replace")
    except URLError as exc:
        raise RuntimeError(f"Wikipedia retrieval failed: {exc}") from exc
    return json.loads(raw)


def _clean_query(query: str) -> str:
    clean = re.sub(r"\s+", " ", str(query or "")).strip(" ?.!")
    clean = re.sub(r"^(the article about|article about)\s+", "", clean, flags=re.IGNORECASE)
    return clean[:120]


def _retrieval_safety() -> dict[str, bool]:
    return {
        **safety_metadata(),
        "external_retrieval_performed": True,
        "network_calls_performed": True,
    }


def _is_memory_request(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip().split())
    return bool(re.search(r"\b(remember|save|store|memorize)\s+(that|this|it|the previous|what you found)\b", text))


def _is_live_help_request(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    return text in {
        "how do i interact with you",
        "how do i use this",
        "what can i do here",
        "what should i ask you",
        "help",
        "help me use this",
    }


def _is_live_context_declaration(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip().split())
    if text.startswith(("context:", "note:", "observation:")):
        return True
    return bool(re.search(r"\b(this is|we are|you are)\b.*\blive runtime\b", text))


def _render_live_help() -> str:
    return "\n".join([
        "You can chat normally, or ask for a Wikipedia text lookup by saying `Wikipedia: topic` or `Look up topic on Wikipedia`.",
        "After a lookup, I will compare the article against local approved concepts and surface any reviewable knowledge gap.",
        "I cannot remember or promote anything automatically. If you say `remember that`, I will show the gated promotion candidate and ask for approval.",
    ])


def pause_live_initiative(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    updated = set_autonomy_status(session, "PAUSED")
    controller = pause_controller(updated.continuous_controller) if updated.continuous_controller else None
    return replace(updated, continuous_controller=controller)


def resume_live_initiative(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    updated = set_autonomy_status(session, "ACTIVE")
    controller = resume_controller(updated.continuous_controller) if updated.continuous_controller else None
    return replace(updated, continuous_controller=controller)


def suspend_live_runtime_initiative(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    updated = set_autonomy_status(session, "SUSPENDED")
    controller = suspend_controller(updated.continuous_controller) if updated.continuous_controller else None
    return replace(updated, continuous_controller=controller)


def _advance_continuous_controller(
    session: LiveWikipediaRuntimeSession,
    event_type: str,
    payload: dict[str, Any],
    *,
    priority: int = 50,
    correlation_id: str = "",
    objective_id: str = "",
) -> LiveWikipediaRuntimeSession:
    if not session.continuous_controller:
        return session
    event = make_continuous_event(
        event_type,
        source="live_wikipedia_runtime",
        session_id=session.session_id,
        payload=payload,
        priority=priority,
        correlation_id=correlation_id,
        objective_id=objective_id,
    )
    controller = enqueue_continuous_event(session.continuous_controller, event)
    controller = run_controller_cycle(controller, session=session)
    return replace(session, continuous_controller=controller)


def _render_memory_gate(session: LiveWikipediaRuntimeSession) -> tuple[str, dict[str, Any]]:
    candidate = session.promotion_candidates[-1] if session.promotion_candidates else None
    inquiry = session.operator_inquiries[-1] if session.operator_inquiries else None
    if candidate and inquiry:
        title = str(candidate.get("title") or "the last evidence item")
        changes = candidate.get("proposed_changes") or ()
        preview = str(changes[0]) if changes else "Review the last evidence item as a noncanonical candidate."
        answer = "\n".join([
            "I cannot write memory automatically from the live runtime.",
            f"I do have a gated promotion candidate: {title}.",
            preview,
            str(inquiry.get("prompt") or "Approve preparing this as a noncanonical review proposal?"),
            "No memory was written.",
        ])
    else:
        answer = "\n".join([
            "I cannot write memory automatically from the live runtime.",
            "There is not yet a promotion candidate in this session. Ask for a Wikipedia lookup first, then I can compare it against local knowledge and prepare a gated review item.",
            "No memory was written.",
        ])
    payload = {
        "mode": "Live Runtime",
        "route": "live_memory_governance",
        "answer": answer,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "external_retrieval_performed": False,
        "network_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "memory_candidate": None,
        "promotion_candidate": candidate,
        "operator_inquiry": inquiry,
    }
    return answer, payload


def _render_budget_exhausted(session: LiveWikipediaRuntimeSession) -> str:
    if session.developmental_results:
        latest = session.developmental_results[-1]
        title = latest.evidence_title
        return (
            f"Wikipedia retrieval is already used for this live objective by `{title}`. "
            "I did not retrieve another page. I can keep discussing the retrieved evidence, compare the promotion candidate, "
            "or you can stop and start the live runtime for a fresh objective."
        )
    return (
        "Wikipedia retrieval is already used for this live objective. I did not retrieve another page. "
        "You can stop and start the live runtime for a fresh objective."
    )


def _response(
    answer: str,
    route: str,
    payload: dict[str, Any],
    result: WikipediaTextResult | None,
    runtime_state: str,
    safety: dict[str, bool],
) -> LiveChatResponse:
    return LiveChatResponse(
        answer=answer,
        route=route,
        payload=payload,
        wikipedia_result=result,
        runtime_state=runtime_state,
        safety=safety,
    )
