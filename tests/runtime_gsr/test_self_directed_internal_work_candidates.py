from dataclasses import replace

import pytest

from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    handle_conversational_message,
    is_internal_work_recall_message,
    select_chat_request_owner,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import classify_internal_work_operator_response
from orchestration.runtime.provisional_semantic_consolidation import load_graph


INTERNAL_WORK_GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. When missing context materially blocks a clearer refinement, "
    "ask me one useful clarification and bind my answer to the relevant analysis. After that, identify one remaining uncertainty as an "
    "internal continuation proposal so I can keep it ready, defer it, dismiss it, or provide context. Do not call a model or provider, "
    "use a tool, take an external action, change source code, or restart. Wait for my scenarios."
)
PARAPHRASED_INTERNAL_WORK_GOAL = (
    "Your new goal is to assess my source-bound scenarios while keeping evidence and limits visible. Seek one clarification when an unknown "
    "changes a provisional update. Once a response leaves another unresolved detail, independently offer a safe next-step candidate for that "
    "detail and let me choose whether to retain, postpone, ignore, or answer it. Keep this local: no model, provider, tool, external action, "
    "source change, or restart."
)
NO_INTERNAL_WORK_AUTHORITY_GOAL = (
    "Your new goal is to hold the next source-bound scenarios as provisional analyses. Keep evidence, assumptions, validation checks, limits, "
    "and safe next actions. Do not call a model, access a provider, take an external action, change source code, or restart."
)
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
CYBER = "A request parameter is appended into a SQL command before execution."
EQUATION = "Can you explain force equals mass times acceleration as a problem-solving model?"


def _start(tmp_path, goal=INTERNAL_WORK_GOAL):
    result = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        goal,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert result.state.active_objective is not None
    return result.state


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _send(state, text, tmp_path):
    return handle_conversational_message(
        state,
        text,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )


def _prepared_continuation(tmp_path, goal=INTERNAL_WORK_GOAL):
    framed = _send(_start(tmp_path, goal), OPERATIONS, tmp_path)
    answered = _send(framed.state, "The pump is due Friday afternoon.", tmp_path)
    return framed, answered


def test_refinement_creates_one_provenance_owned_internal_continuation_from_an_unresolved_slot(tmp_path):
    graph_before = load_graph(tmp_path)
    framed, answered = _prepared_continuation(tmp_path)

    assert framed.state.pending_chat_requests[0].request_type == "evidence_bound_analysis_question"
    assert answered.intent.intent_type == "semantic_evidence_bound_analysis_question_answer"
    candidates = _records(answered.state, "internal_work_candidates")
    selections = _records(answered.state, "internal_work_selections")
    refinements = _records(answered.state, "analysis_refinements")
    pending = answered.state.pending_chat_requests

    latest_candidates = [item for item in candidates if item["source_refinement_id"] == refinements[-1]["refinement_id"]]
    selected = next(item for item in latest_candidates if item["status"] == "surfaced")
    assert selected["unresolved_slot_id"] == "logistics.invoice_payment_status"
    assert selected["latest_state_id"] == refinements[-1]["refinement_id"]
    assert selected["source_analysis_id"] == refinements[-1]["source_analysis_id"]
    assert all(item["unresolved_slot_id"] != "logistics.pump_delivery_eta" for item in latest_candidates)
    assert any(
        item["unresolved_slot_id"] == "logistics.pump_delivery_eta" and item["status"] == "suppressed_resolved"
        for item in candidates
    )
    assert len(pending) == 1
    assert pending[0].request_type == "internal_work_continuation"
    assert pending[0].baseline_metrics["internal_work_candidate_id"] == selected["internal_work_candidate_id"]
    assert pending[0].baseline_metrics["semantic_binding_key"] == selected["semantic_binding_key"]
    assert sum(item["status"] == "surfaced" for item in selections) == 1
    assert "one safe internal continuation" in answered.reply.lower()
    assert "no model, provider, tool" in answered.reply.lower()
    assert not _records(answered.state, "internal_work_dispositions")

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_candidate_generation_is_authority_gated_but_remains_restart_safe_and_exact_once(tmp_path):
    state = _start(tmp_path, NO_INTERNAL_WORK_AUTHORITY_GOAL)
    first = _send(state, OPERATIONS, tmp_path)
    candidates = _records(first.state, "internal_work_candidates")
    selections = _records(first.state, "internal_work_selections")

    assert candidates
    assert all(item["status"] == "deferred_not_authorized" for item in candidates)
    assert all(item["status"] == "deferred_not_authorized" for item in selections)
    assert not first.state.pending_chat_requests

    restored = start_or_restore_runtime(tmp_path)
    repeated = _send(restored, OPERATIONS, tmp_path)
    assert _records(repeated.state, "internal_work_candidates") == candidates
    assert _records(repeated.state, "internal_work_selections") == selections
    assert not repeated.state.pending_chat_requests


@pytest.mark.parametrize(
    ("response", "expected_status"),
    (
        ("Please keep that continuation ready for a later bounded step.", "accepted"),
        ("Leave this available for a later bounded pass.", "accepted"),
        ("Hold that issue for later; do not pursue it now.", "operator_deferred"),
        ("Set the issue aside; it is not a priority right now.", "operator_deferred"),
        ("Do not surface that continuation again for this analysis.", "operator_dismissed"),
        ("Please do not bring this continuation up again in this analysis.", "operator_dismissed"),
        ("The invoice is disputed while the delivery remains planned for Friday.", "resolved_by_answer"),
        ("The customer contests the bill, so funds will not be released yet.", "resolved_by_answer"),
    ),
)
def test_internal_continuation_dispositions_bind_once_without_execution(tmp_path, response, expected_status):
    _framed, prepared = _prepared_continuation(tmp_path)
    request = prepared.state.pending_chat_requests[0]
    candidate_id = request.baseline_metrics["internal_work_candidate_id"]

    assert classify_internal_work_operator_response(request.baseline_metrics, response) == expected_status
    assert select_chat_request_owner(prepared.state, response) == request

    result = _send(prepared.state, response, tmp_path)
    candidates = _records(result.state, "internal_work_candidates")
    selections = _records(result.state, "internal_work_selections")
    dispositions = _records(result.state, "internal_work_dispositions")

    assert result.intent.intent_type == "semantic_internal_work_disposition"
    assert len(dispositions) == 1
    assert dispositions[0]["candidate_id"] == candidate_id
    assert dispositions[0]["surface_request_id"] == request.request_id
    assert dispositions[0]["status"] == expected_status
    assert next(item for item in candidates if item["internal_work_candidate_id"] == candidate_id)["status"] == expected_status
    assert next(item for item in selections if item["candidate_id"] == candidate_id)["status"] == expected_status
    assert not result.state.pending_chat_requests
    assert len(result.state.resolved_chat_requests) == 2
    assert result.state.resolved_chat_requests[-1].request_id == request.request_id
    assert result.state.resolved_chat_requests[-1].consumption_count == 1
    assert "did not create graph truth" in result.reply.lower()
    assert len(_records(result.state, "analysis_refinements")) == 1

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "internal_work_dispositions") == dispositions
    duplicate = _send(restored, response, tmp_path)
    assert len(_records(duplicate.state, "internal_work_dispositions")) == 1
    assert len(_records(duplicate.state, "analysis_refinements")) == 1


def test_directed_internal_work_goal_generalizes_and_preserves_foreground_chat(tmp_path):
    _framed, prepared = _prepared_continuation(tmp_path, PARAPHRASED_INTERNAL_WORK_GOAL)
    request = prepared.state.pending_chat_requests[0]

    ordinary = _send(prepared.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "internal continuation" not in ordinary.reply.lower()
    assert len(ordinary.state.pending_chat_requests) == 1
    assert ordinary.state.pending_chat_requests[0].request_id == request.request_id
    assert not _records(ordinary.state, "internal_work_dispositions")

    answered = _send(ordinary.state, "The invoice is still unpaid, not disputed.", tmp_path)
    assert answered.intent.intent_type == "semantic_internal_work_disposition"
    assert _records(answered.state, "internal_work_dispositions")[0]["status"] == "resolved_by_answer"
    assert not answered.state.pending_chat_requests

    recall_prompt = "What internal continuation remains from that analysis?"
    assert is_internal_work_recall_message(answered.state, recall_prompt)
    recalled = _send(answered.state, recall_prompt, tmp_path)
    assert recalled.intent.intent_type == "semantic_internal_work_recall"
    assert "read-only provenance recall" in recalled.reply.lower()
    assert len(_records(recalled.state, "internal_work_dispositions")) == 1


def test_existing_request_suppresses_an_internal_proposal_without_creating_a_second_queue(tmp_path):
    state = _start(tmp_path, INTERNAL_WORK_GOAL)
    objective = state.active_objective
    assert objective is not None
    existing = ChatAddressableRequest(
        request_id="unrelated-pending-request",
        request_type="interactive_clarification",
        objective_id=objective.objective_id,
        goal_label="Existing request",
        prompt_text="Which source should I use?",
        rendered_turn_id="existing-turn",
        render_sequence=300,
        accepted_response_types=("clarification",),
    )
    state = replace(state, pending_chat_requests=(existing,))
    result = _send(state, FINANCE, tmp_path)

    candidates = _records(result.state, "internal_work_candidates")
    selections = _records(result.state, "internal_work_selections")
    assert candidates
    assert all(item["status"] == "suppressed_existing_request" for item in candidates)
    assert all(item["status"] == "suppressed_existing_request" for item in selections)
    assert len(result.state.pending_chat_requests) == 1
    assert result.state.pending_chat_requests[0].request_id == existing.request_id


@pytest.mark.parametrize("scenario", (FINANCE, CYBER, EQUATION))
def test_internal_candidate_identity_is_domain_and_source_bound_not_prompt_literal(tmp_path, scenario):
    state = _start(tmp_path, PARAPHRASED_INTERNAL_WORK_GOAL)
    result = _send(state, scenario, tmp_path)
    candidates = _records(result.state, "internal_work_candidates")

    assert candidates
    assert all(item["active_objective_id"] == result.state.active_objective.objective_id for item in candidates)
    assert all(item["semantic_binding_key"].startswith(result.state.active_objective.objective_id + "|") for item in candidates)
    assert all(item["source_analysis_id"] for item in candidates)
    assert all(item["source_frame_id"] for item in candidates)
    assert all("model" in " ".join(item["prohibited_actions"]).lower() for item in candidates)
