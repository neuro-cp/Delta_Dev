"""Operator-started live runtime bridge with polite Wikipedia text retrieval.

The bridge keeps Wikipedia as a session-scoped capability. It is inactive until
the operator starts the live runtime, uses only one text summary request per
turn, rate-limits the default transport, records provenance, and falls back to
the existing router for ordinary conversation. It does not call providers,
write memory, commit, push, schedule work, or retrieve media.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import json
import re
import threading
import time
from typing import Any, Callable, Mapping
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
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


WikipediaTransport = Callable[[str, int], dict[str, Any]]
_WIKIPEDIA_TRANSPORT_LOCK = threading.Lock()
_LAST_WIKIPEDIA_TRANSPORT_AT = 0.0
_MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS = 1.0
_WIKIPEDIA_RESPONSE_CACHE: dict[str, dict[str, Any]] = {}
_MAX_WIKIPEDIA_TRANSPORT_RETRIES = 2
_WIKIPEDIA_TRANSPORT_BACKOFF_SECONDS = 0.5


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
    prepared_review_proposals: tuple[dict[str, Any], ...] = ()
    operator_inquiries: tuple[dict[str, Any], ...] = ()
    pending_local_model_request: dict[str, Any] | None = None
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


def activated_wikipedia_profile(*, max_queries_per_objective: int = 0) -> WikipediaPermissionProfile:
    return WikipediaPermissionProfile(
        enabled=True,
        network_calls_allowed=True,
        max_queries_per_objective=max(0, int(max_queries_per_objective)),
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
    max_wikipedia_queries: int = 0,
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
        permission_profile=activated_wikipedia_profile(max_queries_per_objective=max_wikipedia_queries),
        dependencies=("operator_started_live_runtime", "text_summary_endpoint", "session_scoped_retrieval", "provenance_required"),
        retrieval_implemented=True,
        network_code_present=True,
        provider_present=False,
    )
    runtime = replace(runtime, future_surfaces=(surface,))
    queue = enqueue_event(
        runtime.event_queue,
        create_event("runtime_startup", "Operator started live runtime with polite Wikipedia text retrieval.", source="delta_1_4_ui"),
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
    provider_manager: Any | None = None,
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

    control = _runtime_control_intent(message)
    if control:
        session, response = _handle_runtime_control_intent(session, control)
        return session, response

    if session.autonomy_status == "SUSPENDED":
        answer = "The live runtime is suspended. I cannot continue background initiative work, retrieve Wikipedia, or offer local-model escalation until you resume or restart it."
        payload = _base_live_payload("live_runtime_suspended", answer)
        response = _response(answer, "live_runtime_suspended", payload, None, runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    if _is_pending_inquiry_question(message):
        answer, payload = _render_pending_inquiries(session)
        response = _response(answer, "live_pending_inquiries", payload, None, runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    if _has_pending_local_model_request(session) and _is_explicit_local_model_cancellation(message):
        request = session.pending_local_model_request or {}
        LocalModelRequestResultLedger().reject_request(str(request.get("request_id") or ""))
        answer = "The pending local-model request was cancelled. No model was called, no provider was called, and no memory was written."
        payload = _base_live_payload("live_local_model_request_cancelled", answer)
        payload.update({
            "local_model_request": request,
            "provider_calls_performed": False,
            "memory_candidate": None,
        })
        updated = _advance_continuous_controller(
            replace(session, pending_local_model_request=None),
            "OPERATOR_REJECTION",
            {"summary": "operator cancelled pending local model request", "request_id": str(request.get("request_id") or "")},
            priority=65,
            correlation_id=str(request.get("request_id") or ""),
        )
        response = _response(answer, "live_local_model_request_cancelled", payload, None, updated.runtime.state, safety_metadata())
        return replace(updated, turns=updated.turns + (response,)), response

    if _has_pending_local_model_request(session) and _is_explicit_local_model_request(message):
        if session.autonomy_status == "PAUSED":
            answer = "I heard the local-model approval, but live initiative processing is paused. Resume the live runtime before I run the approved local inference turn."
            payload = _base_live_payload("live_runtime_paused", answer)
            payload["pending_local_model_request"] = session.pending_local_model_request
            response = _response(answer, "live_runtime_paused", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        return _run_approved_local_model_request(
            session,
            message,
            history=history,
            developer_overlay=developer_overlay,
            provider_manager=provider_manager,
        )

    if _has_pending_local_model_request(session) and _has_pending_promotion_inquiry(session) and _is_unqualified_affirmation(message):
        answer, payload = _render_ambiguous_live_action(session)
        response = _response(answer, "live_operator_action_ambiguous", payload, None, runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    if _has_pending_local_model_request(session) and not _has_pending_promotion_inquiry(session) and _is_affirmative(message):
        if session.autonomy_status == "PAUSED":
            answer = "I heard the local-model approval, but live initiative processing is paused. Resume the live runtime before I run the approved local inference turn."
            payload = _base_live_payload("live_runtime_paused", answer)
            payload["pending_local_model_request"] = session.pending_local_model_request
            response = _response(answer, "live_runtime_paused", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        return _run_approved_local_model_request(
            session,
            message,
            history=history,
            developer_overlay=developer_overlay,
            provider_manager=provider_manager,
        )

    if _is_affirmative(message) and _has_pending_promotion_inquiry(session):
        selected_inquiry, ambiguity = _select_pending_promotion_inquiry(session, message)
        if ambiguity:
            answer, payload = _render_ambiguous_promotion_approval(session)
            response = _response(answer, "live_promotion_approval_ambiguous", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        if session.autonomy_status == "PAUSED":
            answer = "I heard the approval, but live initiative processing is paused. Resume the live runtime before I prepare the proposal."
            payload = _base_live_payload("live_runtime_paused", answer)
            response = _response(answer, "live_runtime_paused", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        updated, answer, payload = _approve_pending_promotion(session, selected_inquiry)
        response = _response(answer, "live_promotion_approval", payload, None, updated.runtime.state, safety_metadata())
        return replace(updated, turns=updated.turns + (response,)), response

    if _is_rejection(message) and _has_pending_promotion_inquiry(session):
        selected_inquiry, ambiguity = _select_pending_promotion_inquiry(session, message)
        if ambiguity:
            answer, payload = _render_ambiguous_promotion_approval(session, rejection=True)
            response = _response(answer, "live_promotion_rejection_ambiguous", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        updated, answer, payload = _reject_pending_promotion(session, selected_inquiry)
        response = _response(answer, "live_promotion_rejection", payload, None, updated.runtime.state, safety_metadata())
        return replace(updated, turns=updated.turns + (response,)), response

    if _is_live_help_request(message):
        answer = _render_live_help()
        payload = _base_live_payload("live_runtime_help", answer)
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
    if session.autonomy_status == "PAUSED" and (query or _is_continuation_pressure(message)):
        answer = "Live initiative processing is paused. I will not retrieve new evidence, continue background work, or prepare proposals until you resume."
        payload = _base_live_payload("live_runtime_paused", answer)
        response = _response(answer, "live_runtime_paused", payload, None, runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    if query and _wikipedia_budget_allows(session):
        try:
            result = retrieve_wikipedia_text(query, profile=session.wikipedia_profile, transport=wikipedia_transport)
        except Exception as exc:  # noqa: BLE001 - retrieval failures fail closed into an explicit live route.
            answer = "\n".join([
                f"Wikipedia retrieval failed safely for `{query}`.",
                f"Reason: {type(exc).__name__}: {str(exc)[:180]}",
                "No provider was called, no memory was written, and no promotion candidate was prepared from this failed retrieval.",
            ])
            payload = _base_live_payload("live_wikipedia_retrieval_failed", answer)
            payload.update({
                "query": query,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc)[:500],
                "external_retrieval_performed": False,
                "network_calls_performed": bool(wikipedia_transport is None),
                "wikipedia_failure": True,
            })
            response = _response(answer, "live_wikipedia_retrieval_failed", payload, None, runtime.state, safety_metadata())
            updated = _advance_continuous_controller(
                replace(session, runtime=runtime),
                "WIKIPEDIA_FAILURE",
                {"summary": f"Wikipedia retrieval failed for {query}", "exception_type": type(exc).__name__},
                priority=68,
            )
            return replace(updated, turns=updated.turns + (response,)), response
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
            "memory_candidate": _memory_candidate_from_development(development_payload),
            "promotion_candidate": development_payload["promotion_candidate"],
            "operator_inquiry": development_payload["operator_inquiry"],
            "conversation_topic_state": {
                "state_kind": "SUBSTANTIVE_TOPIC",
                "topic": result.title,
                "source_turn": "current",
                "source_route": "live_wikipedia_text_retrieval",
                "last_user_prompt": message,
                "last_visible_answer": answer.split("\n\n--- Developer Overlay ---", 1)[0][:600],
                "entities": [result.title],
                "confidence": 0.86,
                "supersedes_anchor": True,
                "read_only": True,
            },
            "routing_observability": _live_routing_trace(
                message,
                "live_wikipedia_text_retrieval",
                query=query,
                rc2_fallback_considered=False,
                wikipedia_considered=True,
            ),
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
            operator_inquiries=session.operator_inquiries + (_session_inquiry_from_development(development_payload),),
            retrieval_count=session.retrieval_count + 1,
        )
        updated_session, cycle = run_delta_1_6_background_cycle(updated_session)
        updated_session = replace(updated_session, continuous_controller=run_controller_cycle(updated_session.continuous_controller, session=updated_session) if updated_session.continuous_controller else None)
        payload["operational_self_model"] = updated_session.operational_self_model.as_dict() if updated_session.operational_self_model else {}
        payload["background_cycle"] = cycle.as_dict()
        payload["continuous_controller"] = controller_snapshot(updated_session.continuous_controller) if updated_session.continuous_controller else {}
        response = _response(answer, "live_wikipedia_text_retrieval", payload, result, updated_session.runtime.state, _retrieval_safety())
        return replace(updated_session, turns=updated_session.turns[:-1] + (response,)), response

    if query and _wikipedia_budget_exhausted(session):
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

    pending_request = session.pending_local_model_request
    if pending_request is not None:
        session = replace(session, pending_local_model_request=None)
    payload = route_message("Conversation", message, history=history, execute_local_model=False)
    answer = render_route(payload, developer_overlay=developer_overlay)
    local_offer = payload.get("local_model_offer")
    if str(payload.get("route") or "") == "local_model_consent_required" and isinstance(local_offer, dict) and local_offer.get("offered"):
        request = _new_local_model_request(session, message, payload)
        payload = {**payload, "live_runtime_local_model_request": request}
        session = replace(session, pending_local_model_request=request)
    payload["live_routing_observability"] = _live_routing_trace(
        message,
        str(payload.get("route") or "conversation_fallback"),
        query=query,
        rc2_fallback_considered=True,
        wikipedia_considered=bool(query),
    )
    response = _response(answer, str(payload.get("route") or "conversation_fallback"), payload, None, runtime.state, safety_metadata())
    updated = _advance_continuous_controller(replace(session, runtime=runtime), "VALIDATION_RESULT", {"summary": "ordinary chat routed without continuous work"}, priority=20)
    return replace(updated, turns=updated.turns + (response,)), response


def wikipedia_query_from_message(message: str) -> str:
    text = " ".join(str(message or "").strip().strip(" .?!").split())
    lower = text.lower()
    if not _has_explicit_wikipedia_intent(lower):
        return ""
    patterns = (
        r"^(?:wikipedia|wiki)\s*[:\-]?\s*(.+)$",
        r"tell me what wikipedia has (?:regarding|about|on)\s+(.+)$",
        r"what does wikipedia (?:have|say) (?:regarding|about|on)\s+(.+)$",
        r"what has wikipedia got (?:regarding|about|on)\s+(.+)$",
        r"look up\s+(.+?)\s+on wikipedia$",
        r"retrieve\s+(.+?)(?:\s+from wikipedia)?$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            query = re.sub(r"\b(on|from)\s+wikipedia\b", "", match.group(1), flags=re.IGNORECASE).strip(" ?.!")
            return _clean_query(query)
    return ""


def _has_explicit_wikipedia_intent(lower: str) -> bool:
    if "wikipedia" in lower or re.search(r"(^|\s)wiki\s*[:\-]", lower):
        return True
    if lower.startswith("retrieve ") and "from wikipedia" in lower:
        return True
    return bool(re.match(r"^look up .+ on wikipedia$", lower))


def _live_routing_trace(
    message: str,
    selected_route: str,
    *,
    query: str = "",
    rc2_fallback_considered: bool,
    wikipedia_considered: bool,
) -> dict[str, Any]:
    return {
        "layer": "delta_1_4_live_wikipedia_runtime",
        "selected_route": selected_route,
        "raw_message": message,
        "wikipedia_query": query,
        "explicit_wikipedia_intent": _has_explicit_wikipedia_intent(" ".join(str(message or "").lower().split())),
        "wikipedia_considered": wikipedia_considered,
        "rc2_fallback_considered": rc2_fallback_considered,
        "read_only": True,
        "ephemeral": True,
    }


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
    last_error: Exception | None = None
    for attempt in range(_MAX_WIKIPEDIA_TRANSPORT_RETRIES + 1):
        try:
            return _default_wikipedia_transport_once(url, max_chars)
        except (URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt >= _MAX_WIKIPEDIA_TRANSPORT_RETRIES:
                break
            time.sleep(_WIKIPEDIA_TRANSPORT_BACKOFF_SECONDS * (2 ** attempt))
    raise RuntimeError(f"Wikipedia retrieval failed after bounded retries: {last_error}") from last_error


def _default_wikipedia_transport_once(url: str, max_chars: int) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "DELTA-governed-runtime/1.0 (operator-started local experiment)"})
    global _LAST_WIKIPEDIA_TRANSPORT_AT
    with _WIKIPEDIA_TRANSPORT_LOCK:
        cached = _WIKIPEDIA_RESPONSE_CACHE.get(url)
        if cached is not None:
            return dict(cached)
        now = time.monotonic()
        elapsed = now - _LAST_WIKIPEDIA_TRANSPORT_AT
        if elapsed < _MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS:
            time.sleep(_MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS - elapsed)
        _LAST_WIKIPEDIA_TRANSPORT_AT = time.monotonic()
        with urlopen(request, timeout=8) as response:  # noqa: S310 - operator-started throttled Wikipedia-only retrieval
            raw = response.read(max_chars + 4096).decode("utf-8", errors="replace")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise RuntimeError("Wikipedia response was not a JSON object.")
        _WIKIPEDIA_RESPONSE_CACHE[url] = dict(data)
        return dict(data)


def _wait_for_polite_wikipedia_slot() -> None:
    global _LAST_WIKIPEDIA_TRANSPORT_AT
    with _WIKIPEDIA_TRANSPORT_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_WIKIPEDIA_TRANSPORT_AT
        if elapsed < _MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS:
            time.sleep(_MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS - elapsed)
        _LAST_WIKIPEDIA_TRANSPORT_AT = time.monotonic()


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


def _base_live_payload(route: str, answer: str) -> dict[str, Any]:
    return {
        "mode": "Live Runtime",
        "route": route,
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


def _runtime_control_intent(message: str) -> str:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    if not text:
        return ""
    if "runtime" not in text and "initiative" not in text and text not in {"pause", "resume", "suspend", "status"}:
        return ""
    if re.search(r"\b(suspend)\b", text):
        return "SUSPEND"
    if re.search(r"\b(pause)\b", text):
        return "PAUSE"
    if re.search(r"\b(resume|restart)\b", text):
        return "RESUME"
    if "status" in text or "objective state" in text or "report current objective" in text:
        return "REPORT"
    return ""


def _handle_runtime_control_intent(session: LiveWikipediaRuntimeSession, control: str) -> tuple[LiveWikipediaRuntimeSession, LiveChatResponse]:
    if control == "PAUSE":
        updated = pause_live_initiative(session)
        answer = _render_runtime_state(updated, prefix="Paused live initiative processing.")
        payload = _base_live_payload("live_runtime_control_pause", answer)
    elif control == "SUSPEND":
        updated = suspend_live_runtime_initiative(session)
        answer = _render_runtime_state(updated, prefix="Suspended the live runtime initiative path.")
        payload = _base_live_payload("live_runtime_control_suspend", answer)
    elif control == "RESUME":
        updated = resume_live_initiative(session)
        answer = _render_runtime_state(updated, prefix="Resumed live initiative processing.")
        payload = _base_live_payload("live_runtime_control_resume", answer)
    else:
        updated = session
        answer = _render_runtime_state(updated)
        payload = _base_live_payload("live_runtime_control_report", answer)
    payload.update({
        "operator_inquiries": tuple(updated.operator_inquiries[-5:]),
        "promotion_candidate": updated.promotion_candidates[-1] if updated.promotion_candidates else None,
        "prepared_review_proposal": updated.prepared_review_proposals[-1] if updated.prepared_review_proposals else None,
        "continuous_controller": controller_snapshot(updated.continuous_controller) if updated.continuous_controller else {},
    })
    response = _response(answer, str(payload["route"]), payload, None, updated.runtime.state, safety_metadata())
    return replace(updated, turns=updated.turns + (response,)), response


def _render_runtime_state(session: LiveWikipediaRuntimeSession, *, prefix: str = "") -> str:
    model = build_operational_self_model(session=session, initiatives=session.initiatives)
    objectives = model.active_objectives or model.queued_objectives or ("no active objective beyond maintaining the live session",)
    inquiries = model.pending_operator_inquiries or ("none",)
    lines = []
    if prefix:
        lines.append(prefix)
        lines.append("")
    lines.extend([
        f"Runtime state: {getattr(session.runtime, 'state', 'unknown')}.",
        f"Autonomy: {session.autonomy_status}.",
        f"Wikipedia budget: {_wikipedia_budget_label(session)}.",
        "Current objective:",
    ])
    lines.extend(f"- {item}" for item in objectives[:3])
    lines.append("Pending inquiries:")
    lines.extend(f"- {item}" for item in inquiries[:5])
    return "\n".join(lines)


def _is_pending_inquiry_question(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    return any(marker in text for marker in ("pending inquiries", "pending inquiry", "questions are pending", "what are your pending"))


def _is_affirmative(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    text = re.sub(r"[,;:]+", " ", text)
    text = " ".join(text.split())
    if text.startswith(("approve ", "approved ", "prepare ", "go ahead ", "do it ", "yes ", "proceed ")):
        return True
    return text in {
        "yes",
        "y",
        "yes please",
        "yeah",
        "yep",
        "approve",
        "approve that",
        "approved",
        "go ahead",
        "do it",
        "that's fine",
        "thats fine",
        "proceed",
        "the first one",
        "first one",
        "okay prepare it",
        "ok prepare it",
        "prepare it",
        "prepare the proposal",
        "ok",
        "okay",
        "sure",
    }


def _is_rejection(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    text = re.sub(r"[,;:]+", " ", text)
    text = " ".join(text.split())
    if text.startswith(("reject ", "decline ", "discard ", "cancel ", "drop ", "defer ")):
        return True
    return text in {
        "no",
        "n",
        "reject",
        "reject it",
        "decline",
        "not now",
        "not that one",
        "cancel",
        "cancel that",
        "stop",
        "discard",
        "drop it",
        "don't continue",
        "dont continue",
        "never mind",
        "nevermind",
        "defer this",
    }


def _has_pending_local_model_request(session: LiveWikipediaRuntimeSession) -> bool:
    request = session.pending_local_model_request
    if not isinstance(request, dict) or not request.get("request_id"):
        return False
    try:
        record = LocalModelRequestResultLedger().observe_request(str(request["request_id"]))
    except (KeyError, RuntimeError):
        return False
    return record.get("lifecycle_state") == "pending_operator_approval"


def _normalized_operator_text(message: str) -> str:
    text = " ".join(str(message or "").lower().strip(" ?.! ").split())
    text = re.sub(r"[,;:]+", " ", text)
    return " ".join(text.split())


def _is_explicit_local_model_request(message: str) -> bool:
    text = _normalized_operator_text(message)
    return any(marker in text for marker in (
        "ask local model",
        "ask the local model",
        "use local model",
        "use the local model",
        "run local model",
        "run the local model",
        "ask llama",
        "ask mistral",
        "use llama",
        "use mistral",
    ))


def _is_explicit_local_model_cancellation(message: str) -> bool:
    text = _normalized_operator_text(message)
    return any(marker in text for marker in (
        "cancel local model",
        "cancel the local model",
        "do not ask local model",
        "dont ask local model",
        "do not use local model",
        "dont use local model",
    ))


def _is_unqualified_affirmation(message: str) -> bool:
    return _normalized_operator_text(message) in {
        "yes",
        "y",
        "yes please",
        "yeah",
        "yep",
        "approve",
        "approved",
        "go ahead",
        "do it",
        "proceed",
        "okay",
        "ok",
        "sure",
    }


def _new_local_model_request(
    session: LiveWikipediaRuntimeSession,
    message: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    lane = dict(payload.get("selected_model_lane") or {})
    offer = dict(payload.get("local_model_offer") or {})
    record = LocalModelRequestResultLedger().create_or_reuse_request(
        semantic_identity=stable_id("live-local-model-semantic", session.session_id, " ".join(message.split())),
        question=message,
        requester_type="live_conversation",
        requester_reference=session.session_id,
        session_reference=session.session_id,
        question_objective=str(offer.get("prompt") or "local conversation answer"),
        lane=lane,
    )
    return {**record, "status": "PENDING_OPERATOR_APPROVAL", "lane": str(lane.get("lane") or ""), "selected_model": str(lane.get("selected_model") or ""), "selected_model_id": str(lane.get("selected_model_id") or "")}


def create_local_model_pending_request(
    *,
    session_id: str,
    message: str,
    lane: Mapping[str, Any],
    semantic_identity: str,
) -> dict[str, Any]:
    """Compatibility wrapper that delegates request ownership to the ledger."""

    record = LocalModelRequestResultLedger().create_or_reuse_request(
        semantic_identity=semantic_identity,
        question=message,
        requester_type="mission_bound_learning",
        requester_reference=session_id,
        mission_id=session_id,
        question_objective="mission-bound information need",
        lane=lane,
    )
    return {**record, "status": "PENDING_OPERATOR_APPROVAL", "lane": str(lane.get("lane") or ""), "selected_model": str(lane.get("selected_model") or ""), "selected_model_id": str(lane.get("selected_model_id") or "")}


def _render_ambiguous_live_action(session: LiveWikipediaRuntimeSession) -> tuple[str, dict[str, Any]]:
    request = session.pending_local_model_request or {}
    candidates = [
        _promotion_title_for_inquiry(session, inquiry) or "unnamed promotion candidate"
        for inquiry in _pending_promotion_inquiries(session)
    ]
    candidate_text = "; ".join(candidates[:3]) or "a promotion candidate"
    answer = "\n".join([
        "There are multiple pending operator actions, so I will not guess what this approval means.",
        f"Promotion review: {candidate_text}.",
        f"Local inference request: {request.get('selected_model_id') or request.get('selected_model') or 'selected local model'} for the queued question.",
        "Say `ask the local model` to run the local inference turn, or name the promotion candidate you want reviewed.",
        "No model was called and no memory was written.",
    ])
    payload = _base_live_payload("live_operator_action_ambiguous", answer)
    payload.update({
        "pending_local_model_request": request,
        "pending_promotion_titles": candidates,
        "provider_calls_performed": False,
        "memory_candidate": None,
    })
    return answer, payload


def _run_approved_local_model_request(
    session: LiveWikipediaRuntimeSession,
    approval_message: str,
    *,
    history: list[dict[str, str]] | None,
    developer_overlay: bool,
    provider_manager: Any | None,
) -> tuple[LiveWikipediaRuntimeSession, LiveChatResponse]:
    request = dict(session.pending_local_model_request or {})
    target = str(request.get("question") or request.get("message") or "").strip()
    if not target:
        answer = "The pending local-model request was invalid, so it was cleared without calling a model."
        payload = _base_live_payload("live_local_model_request_invalid", answer)
        response = _response(answer, "live_local_model_request_invalid", payload, None, session.runtime.state, safety_metadata())
        return replace(session, pending_local_model_request=None, turns=session.turns + (response,)), response

    ledger = LocalModelRequestResultLedger()
    request_id = str(request.get("request_id") or "")
    ledger.approve_request(request_id, "operator_approved_one_use")
    terminal = ledger.execute_claimed_request(request_id, {"history": history, "provider_manager": provider_manager})
    lane = dict(terminal.get("selected_lane") or request)
    executed = terminal.get("lifecycle_state") == "completed"
    result = ledger.observe_result(str(terminal.get("result_id") or "")) if executed else {}
    model_result = {"executed": executed, "answer": str(result.get("response_reference") or ""), "model_id": str(result.get("model_identity") or ""), "reason": str(terminal.get("failure_classification") or "")}
    model_id = str(model_result.get("model_id") or lane.get("selected_model_id") or lane.get("selected_model") or "")
    latency_seconds = float(result.get("latency_seconds") or 0.0)
    updated = replace(session, pending_local_model_request=None)

    if executed:
        updated = _record_local_model_residency(updated, lane, model_result, provider_manager)
        updated = _advance_continuous_controller(
            updated,
            "MODEL_READY",
            {
                "model_id": model_id,
                "lane": str(lane.get("lane") or request.get("lane") or ""),
                "local_model_call_performed": True,
                "latency_seconds": latency_seconds,
                "operator_request_id": str(request.get("request_id") or ""),
            },
            priority=70,
            correlation_id=str(request.get("request_id") or ""),
        )
        answer = str(model_result.get("answer") or "").strip()
        answer += "\n\nThis was one explicitly approved local inference turn. No provider, external retrieval, or memory write was performed."
        route = "live_local_model_inference"
    else:
        reason = str(model_result.get("reason") or "local_model_execution_failed")
        updated = _record_local_model_residency(updated, lane, model_result, provider_manager, failure_reason=reason)
        updated = _advance_continuous_controller(
            updated,
            "MODEL_UNAVAILABLE",
            {
                "model_id": model_id,
                "lane": str(lane.get("lane") or request.get("lane") or ""),
                "attempted": True,
                "reason": reason,
                "operator_request_id": str(request.get("request_id") or ""),
            },
            priority=70,
            correlation_id=str(request.get("request_id") or ""),
        )
        answer = "\n".join([
            "The explicitly approved local inference turn did not complete.",
            f"Reason: {reason}",
            "No provider was called, no external retrieval occurred, and no memory was written. The request was cleared rather than retried automatically.",
        ])
        route = "live_local_model_unavailable"

    payload = {
        **_base_live_payload(route, answer),
        "mode": "Live Runtime",
        "route": route,
        "answer": answer,
        "live_runtime_local_model_execution": True,
        "operator_approval_request_id": str(request.get("request_id") or ""),
        "ledger_result_id": str(terminal.get("result_id") or ""),
        "local_model_request": request,
        "model_execution": {
            "executed": executed,
            "model_id": model_id,
            "lane": str(lane.get("lane") or request.get("lane") or ""),
            "latency_seconds": latency_seconds,
        },
        "provider_calls_performed": False,
        "web_search_performed": False,
        "external_retrieval_performed": False,
        "network_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "memory_candidate": None,
        "supporting_information_offer": None,
        "local_model_offer": None,
        "continuous_controller": controller_snapshot(updated.continuous_controller) if updated.continuous_controller else {},
    }
    if developer_overlay:
        payload["developer_overlay"] = {
            "approval_message": approval_message,
            "target_question": target,
            "request_id": request.get("request_id"),
            "executed": executed,
            "model_id": model_id,
        }
    response = _response(answer, route, payload, None, updated.runtime.state, safety_metadata())
    return replace(updated, turns=updated.turns + (response,)), response


def _record_local_model_residency(
    session: LiveWikipediaRuntimeSession,
    lane: dict[str, Any],
    model_result: dict[str, Any],
    provider_manager: Any | None,
    *,
    failure_reason: str = "",
) -> LiveWikipediaRuntimeSession:
    controller = session.continuous_controller
    if controller is None:
        return session
    status = _provider_residency_status(provider_manager)
    executed = bool(model_result.get("executed"))
    selected_model = str(model_result.get("model_id") or lane.get("selected_model_id") or lane.get("selected_model") or "")
    resident_model = str(status.get("active_model") or selected_model) if executed and status.get("loaded", True) else ""
    if failure_reason:
        residency_status = f"unavailable:{failure_reason[:120]}"
    elif status.get("loaded", False):
        residency_status = "warm"
    else:
        residency_status = "completed_not_resident"
    residency = replace(
        controller.model_residency,
        resident_model_id=resident_model,
        resident_lane=str(lane.get("lane") or ""),
        residency_status=residency_status,
        model_calls_this_cycle=controller.model_residency.model_calls_this_cycle + (1 if executed else 0),
    )
    return replace(session, continuous_controller=replace(controller, model_residency=residency))


def _provider_residency_status(provider_manager: Any | None) -> dict[str, Any]:
    status_method = getattr(provider_manager, "status", None)
    if not callable(status_method):
        return {}
    try:
        status = status_method()
    except Exception:  # noqa: BLE001 - status reporting cannot interfere with an already-completed inference turn.
        return {}
    return {
        "active_model": str(getattr(status, "active_model", "") or ""),
        "loaded": bool(getattr(status, "loaded", False)),
    }


def _has_pending_promotion_inquiry(session: LiveWikipediaRuntimeSession) -> bool:
    return any(str(item.get("status") or "").upper() in {"QUEUED", "SURFACED"} for item in session.operator_inquiries) and bool(session.promotion_candidates)


def _pending_promotion_inquiries(session: LiveWikipediaRuntimeSession) -> tuple[dict[str, Any], ...]:
    return tuple(
        item
        for item in session.operator_inquiries
        if isinstance(item, dict) and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"} and item.get("promotion_candidate_id")
    )


def _select_pending_promotion_inquiry(session: LiveWikipediaRuntimeSession, message: str) -> tuple[dict[str, Any] | None, bool]:
    pending = _pending_promotion_inquiries(session)
    if not pending:
        return None, False
    if len(pending) == 1:
        return pending[-1], False
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    text = re.sub(r"[,;:]+", " ", text)
    text = " ".join(text.split())
    if text in {"not that one", "cancel that", "drop it", "defer this", "reject that", "approve that", "approve that proposal", "yes", "okay", "ok"}:
        return None, True
    if "first" in text:
        return pending[0], False
    if "second" in text or "candidate 2" in text or "number 2" in text:
        return pending[min(1, len(pending) - 1)], False
    if "last" in text or "latest" in text or "most recent" in text or "that one" in text:
        return pending[-1], False
    target_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", re.sub(r"\b(approve|approved|prepare|reject|decline|discard|cancel|drop|defer|the|one|candidate)\b", " ", text))
        if len(token) > 2
    }
    for inquiry in pending:
        title = _promotion_title_for_inquiry(session, inquiry).lower()
        if title and title in text:
            return inquiry, False
        title_tokens = set(re.findall(r"[a-z0-9]+", title))
        if target_tokens and target_tokens.issubset(title_tokens):
            return inquiry, False
    return None, True


def _promotion_title_for_inquiry(session: LiveWikipediaRuntimeSession, inquiry: dict[str, Any]) -> str:
    candidate_id = str(inquiry.get("promotion_candidate_id") or "")
    for candidate in session.promotion_candidates:
        if str(candidate.get("candidate_id") or "") == candidate_id:
            return str(candidate.get("title") or "")
    return ""


def _promotion_candidate_for_inquiry(session: LiveWikipediaRuntimeSession, inquiry: dict[str, Any] | None) -> dict[str, Any]:
    candidate_id = str((inquiry or {}).get("promotion_candidate_id") or "")
    for candidate in session.promotion_candidates:
        if str(candidate.get("candidate_id") or "") == candidate_id:
            return candidate
    return session.promotion_candidates[-1]


def _render_ambiguous_promotion_approval(session: LiveWikipediaRuntimeSession, *, rejection: bool = False) -> tuple[str, dict[str, Any]]:
    pending = _pending_promotion_inquiries(session)
    action = "reject" if rejection else "approve"
    lines = [f"I found multiple pending promotion candidates, so I need a specific target before I {action} one."]
    for index, inquiry in enumerate(pending, start=1):
        title = _promotion_title_for_inquiry(session, inquiry) or str(inquiry.get("prompt") or f"candidate {index}")
        lines.append(f"- {index}. {title}")
    lines.append("Say `approve first`, `approve latest`, or name the candidate title.")
    answer = "\n".join(lines)
    payload = _base_live_payload("live_promotion_rejection_ambiguous" if rejection else "live_promotion_approval_ambiguous", answer)
    payload.update({"operator_inquiries": pending, "promotion_candidates": session.promotion_candidates[-8:]})
    return answer, payload


def _approve_pending_promotion(session: LiveWikipediaRuntimeSession, inquiry: dict[str, Any] | None = None) -> tuple[LiveWikipediaRuntimeSession, str, dict[str, Any]]:
    candidate = _promotion_candidate_for_inquiry(session, inquiry)
    memory_candidate = _memory_candidate_from_promotion(candidate)
    proposal = {
        "proposal_id": stable_id("live-noncanonical-review-proposal", candidate.get("candidate_id"), len(session.prepared_review_proposals)),
        "promotion_candidate_id": candidate.get("candidate_id"),
        "title": candidate.get("title"),
        "source_url": candidate.get("source_url"),
        "proposed_changes": tuple(candidate.get("proposed_changes") or ()),
        "evidence_terms": tuple(candidate.get("evidence_terms") or ()),
        "status": "PREPARED_FOR_OPERATOR_REVIEW",
        "canonical_write_performed": False,
        "memory_write_performed": False,
        "safety": safety_metadata(),
    }
    inquiries = tuple(
        {**item, "status": "APPROVED_FOR_PROPOSAL_PREPARATION"} if isinstance(item, dict) and str(item.get("promotion_candidate_id") or "") == str(candidate.get("candidate_id") or "") and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"} else item
        for item in session.operator_inquiries
    )
    runtime = replace(session.runtime, journal=append_journal(session.runtime.journal, "live_promotion_approval", str(candidate.get("title") or "promotion candidate"), (str(candidate.get("candidate_id") or ""),), session.runtime.cycle))
    updated = replace(session, runtime=runtime, operator_inquiries=inquiries, prepared_review_proposals=session.prepared_review_proposals + (proposal,))
    updated, cycle = run_delta_1_6_background_cycle(updated)
    if updated.continuous_controller:
        updated = replace(updated, continuous_controller=run_controller_cycle(updated.continuous_controller, session=updated))
    answer = "\n".join([
        "Approved. I prepared the noncanonical expansion proposal within the current live-session scope.",
        "",
        "Proposal contents:",
        *[f"- {item}" for item in proposal["proposed_changes"][:5]],
        "",
        "No memory was written. Select the candidate in Concept Review and press Accept Selected Concept only if you want to store it as noncanonical local knowledge.",
    ])
    payload = _base_live_payload("live_promotion_approval", answer)
    payload.update({
        "memory_candidate": memory_candidate,
        "promotion_candidate": candidate,
        "prepared_review_proposal": proposal,
        "operator_inquiries": inquiries[-5:],
        "background_cycle": cycle.as_dict(),
    })
    return updated, answer, payload


def _reject_pending_promotion(session: LiveWikipediaRuntimeSession, inquiry: dict[str, Any] | None = None) -> tuple[LiveWikipediaRuntimeSession, str, dict[str, Any]]:
    candidate = _promotion_candidate_for_inquiry(session, inquiry)
    inquiries = tuple(
        {**item, "status": "REJECTED_BY_OPERATOR"} if isinstance(item, dict) and str(item.get("promotion_candidate_id") or "") == str(candidate.get("candidate_id") or "") and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"} else item
        for item in session.operator_inquiries
    )
    updated = replace(session, operator_inquiries=inquiries)
    answer = "Rejected. I left the promotion candidate unprepared and wrote no memory."
    payload = _base_live_payload("live_promotion_rejection", answer)
    payload.update({"operator_inquiries": inquiries[-5:], "promotion_candidate": candidate})
    return updated, answer, payload


def _is_continuation_pressure(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    return any(marker in text for marker in ("continue", "background initiative", "prepare proposal", "keep working", "go on", "proceed"))


def _wikipedia_budget_allows(session: LiveWikipediaRuntimeSession) -> bool:
    limit = int(session.wikipedia_profile.max_queries_per_objective or 0)
    return limit <= 0 or session.retrieval_count < limit


def _wikipedia_budget_exhausted(session: LiveWikipediaRuntimeSession) -> bool:
    limit = int(session.wikipedia_profile.max_queries_per_objective or 0)
    return limit > 0 and session.retrieval_count >= limit


def _wikipedia_budget_label(session: LiveWikipediaRuntimeSession) -> str:
    limit = int(session.wikipedia_profile.max_queries_per_objective or 0)
    if limit <= 0:
        return f"{session.retrieval_count}/unlimited"
    return f"{session.retrieval_count}/{limit}"


def _render_pending_inquiries(session: LiveWikipediaRuntimeSession) -> tuple[str, dict[str, Any]]:
    model = build_operational_self_model(session=session, initiatives=session.initiatives)
    inquiries = tuple(
        item
        for item in session.operator_inquiries[-8:]
        if isinstance(item, dict) and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"}
    )
    pending_text = tuple(str(item.get("prompt") or "") for item in inquiries if str(item.get("prompt") or "").strip())
    if pending_text:
        answer = "Pending inquiries:\n" + "\n".join(f"- {item}" for item in pending_text[:8])
    else:
        answer = "No pending operator inquiries are queued right now."
    payload = _base_live_payload("live_pending_inquiries", answer)
    payload.update({
        "operator_inquiries": inquiries,
        "promotion_candidate": session.promotion_candidates[-1] if session.promotion_candidates else None,
        "operational_self_model": model.as_dict(),
    })
    return answer, payload


def _session_inquiry_from_development(development_payload: dict[str, Any]) -> dict[str, Any]:
    inquiry = dict(development_payload["operator_inquiry"])
    inquiry.setdefault("status", "QUEUED")
    inquiry.setdefault("notification_class", "IN_APP_NORMAL")
    inquiry.setdefault("authority_class", "OPERATOR_APPROVAL_REQUIRED")
    inquiry.setdefault("promotion_candidate_id", development_payload["promotion_candidate"]["candidate_id"])
    return inquiry


def _memory_candidate_from_development(development_payload: dict[str, Any]) -> dict[str, Any]:
    return _memory_candidate_from_promotion(development_payload["promotion_candidate"])


def _memory_candidate_from_promotion(candidate: dict[str, Any]) -> dict[str, Any]:
    terms = [str(item) for item in (candidate.get("evidence_terms") or ()) if str(item).strip()]
    changes = [str(item) for item in (candidate.get("proposed_changes") or ()) if str(item).strip()]
    name = str(candidate.get("title") or "Wikipedia review candidate").replace(" local knowledge review", "").strip()
    source_url = str(candidate.get("source_url") or "")
    concept_id = stable_id("live-review-concept", candidate.get("candidate_id") or name)
    short_definition = (
        f"Review-only Wikipedia evidence candidate for {name}. "
        f"Candidate terms: {', '.join(terms[:5]) or 'article-level evidence'}."
    )
    return {
        "concept_id": concept_id,
        "concept_name": name,
        "concept_type": "review_candidate",
        "short_definition": short_definition,
        "propositions": changes or (short_definition,),
        "related_concepts": terms[:8],
        "explains": [f"Whether {name} should improve noncanonical local knowledge."],
        "examples": [source_url] if source_url else [],
        "misconceptions": [],
        "uncertainty": "operator_review_required_wikipedia_evidence",
        "source_answer_id": str(candidate.get("candidate_id") or concept_id),
        "source_question": str(candidate.get("title") or name),
        "source_model_lane": "live_wikipedia_developmental_cognition",
        "source_model_id": "no_provider_model",
        "source_type": "live_wikipedia_promotion_candidate",
        "approval_status": "pending_operator_review_wikipedia_candidate",
        "memory_type": "knowledge",
        "rollback_handle": f"rollback-{concept_id}",
        "created_at": utc_now(),
        "canonical": False,
        "training_performed": False,
        "provider_calls_performed": False,
        "source_url": source_url,
        "promotion_candidate_id": candidate.get("candidate_id"),
        "operator_review_required": True,
    }


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
