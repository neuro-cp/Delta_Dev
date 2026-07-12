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


def start_live_wikipedia_runtime(*, runtime_id: str = "delta-live-ui") -> LiveWikipediaRuntimeSession:
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
    return LiveWikipediaRuntimeSession(
        session_id=stable_id("delta14-session", runtime.runtime_id, utc_now()),
        runtime=runtime,
        wikipedia_profile=surface.permission_profile,
        active=True,
        started_at=utc_now(),
    )


def stop_live_wikipedia_runtime(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    event = create_event("runtime_shutdown", "Operator stopped live Wikipedia runtime.", source="delta_1_4_ui")
    queue = enqueue_event(session.runtime.event_queue, event)
    runtime = run_wake_cycle(replace(session.runtime, event_queue=queue))
    journal = append_journal(runtime.journal, "live_runtime_stop", "Live Wikipedia runtime stopped by operator.", (), runtime.cycle)
    return replace(session, runtime=replace(runtime, journal=journal, state="IDLE"), active=False)


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
    query = wikipedia_query_from_message(message)
    if query and session.retrieval_count < session.wikipedia_profile.max_queries_per_objective:
        result = retrieve_wikipedia_text(query, profile=session.wikipedia_profile, transport=wikipedia_transport)
        answer = render_wikipedia_answer(message, result)
        if developer_overlay:
            answer += "\n\n--- Developer Overlay ---\nRoute: live_wikipedia_text_retrieval\n"
            answer += "Wikipedia result:\n" + json.dumps(asdict(result), indent=2, sort_keys=True)
        payload = {
            "mode": "Live Runtime",
            "route": "live_wikipedia_text_retrieval",
            "answer": answer,
            "wikipedia_result": asdict(result),
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": True,
            "network_calls_performed": True,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
        }
        runtime = replace(
            runtime,
            journal=append_journal(runtime.journal, "wikipedia_retrieval", f"Retrieved Wikipedia text for {result.title}.", (result.canonical_url,), runtime.cycle),
        )
        response = _response(answer, "live_wikipedia_text_retrieval", payload, result, runtime.state, _retrieval_safety())
        return replace(session, runtime=runtime, turns=session.turns + (response,), retrieval_count=session.retrieval_count + 1), response

    payload = route_message("Conversation", message, history=history, execute_local_model=False)
    answer = render_route(payload, developer_overlay=developer_overlay)
    if query and session.retrieval_count >= session.wikipedia_profile.max_queries_per_objective:
        answer += "\n\nWikipedia retrieval was skipped because this live session's per-objective query budget is already used."
    response = _response(answer, str(payload.get("route") or "conversation_fallback"), payload, None, runtime.state, safety_metadata())
    return replace(session, runtime=runtime, turns=session.turns + (response,)), response


def wikipedia_query_from_message(message: str) -> str:
    text = " ".join(str(message or "").strip().strip(" .?!").split())
    lower = text.lower()
    patterns = (
        r"^(?:wikipedia|wiki)\s*[:\-]?\s*(.+)$",
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
