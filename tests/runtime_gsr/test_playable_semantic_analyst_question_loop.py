from dataclasses import replace

from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    handle_conversational_message,
    is_evidence_bound_analysis_refinement_recall_message,
    start_or_restore_runtime,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph


QUESTION_GOAL = (
    "Your new goal is to help me analyze source-bound scenarios provisionally. "
    "When missing context or uncertainty blocks a clearer refinement, ask me one concise clarification, "
    "bind my response to the relevant analysis, and update that analysis without changing source code, "
    "calling a model or provider, using a tool, taking an external action, or restarting. Wait for my scenarios."
)
PARAPHRASED_QUESTION_GOAL = (
    "Your new goal is to assess the scenarios I provide while retaining their evidence and limits. "
    "Seek my clarification only when an unknown detail materially affects a provisional update, then use the reply "
    "to refine the associated record. Keep this local: no model, provider, tool, external action, source change, or restart."
)
NO_INITIATIVE_GOAL = (
    "Your new goal is to hold the next source-bound scenarios as provisional analyses. "
    "Keep evidence, assumptions, validation checks, limits, and safe next actions. "
    "Do not call a model, access a provider, take an external action, change source code, or restart."
)
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
CYBER = "A request parameter is appended into a SQL command before execution."
EQUATION = "Can you explain force equals mass times acceleration as a problem-solving model?"


def _start(tmp_path, goal=QUESTION_GOAL):
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


def _record_scenario(state, text, tmp_path):
    return handle_conversational_message(
        state,
        text,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )


def test_candidates_are_source_bound_exact_once_and_quiet_without_objective_authority(tmp_path):
    state = _start(tmp_path, NO_INITIATIVE_GOAL)
    graph_before = load_graph(tmp_path)

    result = _record_scenario(state, OPERATIONS, tmp_path)
    objective = result.state.active_objective
    assert objective is not None
    candidates = _records(result.state, "operator_question_candidates")
    selections = _records(result.state, "operator_question_selections")

    assert result.intent.intent_type == "semantic_problem_modeling"
    assert len(candidates) == 4
    assert {item["unknown_slot_id"] for item in candidates} == {
        "logistics.pump_delivery_eta",
        "logistics.invoice_payment_status",
        "logistics.alternate_resource_available",
        "logistics.job_priority",
    }
    assert all(item["source_frame_id"] == objective.provenance["semantic_problem_frames"][0]["frame_id"] for item in candidates)
    assert all(item["source_analysis_id"] == objective.provenance["evidence_bound_analyses"][0]["analysis_id"] for item in candidates)
    assert all(item["question_binding_key"].startswith(objective.objective_id + "|") for item in candidates)
    assert all(item["status"] == "deferred_not_authorized" for item in candidates)
    assert all(item["status"] == "deferred_not_authorized" for item in selections)
    assert not result.state.pending_chat_requests
    assert not result.state.resolved_chat_requests

    repeated = _record_scenario(result.state, OPERATIONS, tmp_path)
    assert _records(repeated.state, "operator_question_candidates") == candidates
    assert _records(repeated.state, "operator_question_selections") == selections
    assert not repeated.state.pending_chat_requests

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_question_initiative_generalizes_over_authorized_objective_wording(tmp_path):
    state = _start(tmp_path, PARAPHRASED_QUESTION_GOAL)

    result = _record_scenario(state, OPERATIONS, tmp_path)
    candidates = _records(result.state, "operator_question_candidates")
    selections = _records(result.state, "operator_question_selections")
    pending = result.state.pending_chat_requests

    selected = next(item for item in candidates if item["status"] == "asked")
    assert selected["unknown_slot_id"] == "logistics.pump_delivery_eta"
    assert len(pending) == 1
    assert pending[0].request_type == "evidence_bound_analysis_question"
    assert pending[0].baseline_metrics["question_id"] == selected["question_id"]
    assert pending[0].baseline_metrics["source_frame_id"] == selected["source_frame_id"]
    assert pending[0].baseline_metrics["source_analysis_id"] == selected["source_analysis_id"]
    assert pending[0].rendered_turn_id
    assert pending[0].render_sequence > 0
    assert "expected to arrive" in result.reply.lower()
    assert sum(item["status"] == "asked" for item in candidates) == 1
    assert sum(item["status"] == "asked" for item in selections) == 1
    assert sum(item["status"] == "suppressed_low_priority" for item in selections) == 3


def test_finance_and_cyber_select_safe_high_value_questions_without_spam(tmp_path):
    state = _start(tmp_path)
    finance_result = _record_scenario(state, FINANCE, tmp_path)
    finance_candidate = next(item for item in _records(finance_result.state, "operator_question_candidates") if item["status"] == "asked")
    assert finance_candidate["unknown_slot_id"] == "finance.drawdown_tolerance"
    assert finance_result.state.pending_chat_requests[0].baseline_metrics["expected_answer_type"] == "risk_threshold"
    assert "unacceptable" in finance_result.reply.lower()
    assert "trade instruction" in finance_result.reply.lower()

    state = _start(tmp_path / "cyber")
    cyber_result = _record_scenario(state, CYBER, tmp_path / "cyber")
    cyber_candidate = next(item for item in _records(cyber_result.state, "operator_question_candidates") if item["status"] == "asked")
    assert cyber_candidate["unknown_slot_id"] == "cyber.authorization_context"
    assert "own" in cyber_result.reply.lower()
    assert "payloads" in cyber_result.reply.lower()
    assert len(cyber_result.state.pending_chat_requests) == 1


def test_existing_pending_request_suppresses_new_analysis_question_without_creating_a_second_queue(tmp_path):
    state = _start(tmp_path)
    objective = state.active_objective
    assert objective is not None
    other_request = ChatAddressableRequest(
        request_id="existing-chat-request",
        request_type="interactive_clarification",
        objective_id=objective.objective_id,
        goal_label="Existing operator question",
        prompt_text="Which source should I use?",
        rendered_turn_id="existing-rendered-turn",
        render_sequence=90,
        accepted_response_types=("clarification",),
    )
    state = replace(state, pending_chat_requests=(other_request,))

    result = _record_scenario(state, OPERATIONS, tmp_path)
    candidates = _records(result.state, "operator_question_candidates")
    selections = _records(result.state, "operator_question_selections")
    assert len(result.state.pending_chat_requests) == 1
    assert result.state.pending_chat_requests[0].request_id == other_request.request_id
    assert all(item["status"] == "suppressed_existing_request" for item in candidates)
    assert all(item["status"] == "suppressed_existing_request" for item in selections)


def test_answer_binds_only_to_selected_question_and_appends_one_refinement(tmp_path):
    state = _start(tmp_path)
    framed = _record_scenario(state, OPERATIONS, tmp_path)
    original_analysis = _records(framed.state, "evidence_bound_analyses")[0]
    candidate = next(item for item in _records(framed.state, "operator_question_candidates") if item["status"] == "asked")
    request = framed.state.pending_chat_requests[0]

    unrelated = _record_scenario(framed.state, "What is 2 + 2?", tmp_path)
    assert unrelated.intent.intent_type == "ordinary_conversation"
    assert "evidence-bound analysis" not in unrelated.reply.lower()
    assert len(unrelated.state.pending_chat_requests) == 1
    assert unrelated.state.pending_chat_requests[0].request_id == request.request_id
    assert not _records(unrelated.state, "operator_question_answers")

    answered = _record_scenario(unrelated.state, "The delivery is expected Friday afternoon.", tmp_path)
    answers = _records(answered.state, "operator_question_answers")
    refinements = _records(answered.state, "analysis_refinements")
    candidates = _records(answered.state, "operator_question_candidates")

    assert answered.intent.intent_type == "semantic_evidence_bound_analysis_question_answer"
    assert len(answers) == 1
    assert answers[0]["question_id"] == candidate["question_id"]
    assert answers[0]["source_frame_id"] == candidate["source_frame_id"]
    assert answers[0]["source_analysis_id"] == candidate["source_analysis_id"]
    assert answers[0]["status"] == "bound_operator_answer"
    assert len(refinements) == 1
    assert refinements[0]["source_analysis_id"] == original_analysis["analysis_id"]
    assert refinements[0]["source_question_id"] == candidate["question_id"]
    assert refinements[0]["source_answer_id"] == answers[0]["answer_id"]
    assert "time-bounded" in refinements[0]["after_summary"]
    assert _records(answered.state, "evidence_bound_analyses")[0] == original_analysis
    assert not answered.state.pending_chat_requests
    assert len(answered.state.resolved_chat_requests) == 1
    assert answered.state.resolved_chat_requests[0].request_id == request.request_id
    assert answered.state.resolved_chat_requests[0].consumption_count == 1
    assert next(item for item in candidates if item["question_id"] == candidate["question_id"])["status"] == "resolved"
    assert "appended your answer" in answered.reply.lower()


def test_new_source_scenario_is_not_swallowed_as_an_answer_to_pending_question(tmp_path):
    state = _start(tmp_path)
    first = _record_scenario(state, OPERATIONS, tmp_path)
    pending_id = first.state.pending_chat_requests[0].request_id

    second = _record_scenario(first.state, EQUATION, tmp_path)
    assert second.intent.intent_type == "semantic_problem_modeling"
    assert len(_records(second.state, "evidence_bound_analyses")) == 2
    assert not _records(second.state, "operator_question_answers")
    assert len(second.state.pending_chat_requests) == 1
    assert second.state.pending_chat_requests[0].request_id == pending_id
    equation_candidates = [
        item for item in _records(second.state, "operator_question_candidates")
        if item["domain"] == "physics_equation_model"
    ]
    assert equation_candidates
    assert all(item["status"] == "suppressed_existing_request" for item in equation_candidates)


def test_refinement_recall_and_restart_are_read_only_and_exact_once(tmp_path):
    state = _start(tmp_path)
    framed = _record_scenario(state, OPERATIONS, tmp_path)
    answered = _record_scenario(framed.state, "The pump should arrive on Friday.", tmp_path)
    objective = answered.state.active_objective
    assert objective is not None
    ids = {
        "frame": _records(answered.state, "semantic_problem_frames")[0]["frame_id"],
        "analysis": _records(answered.state, "evidence_bound_analyses")[0]["analysis_id"],
        "candidate": _records(answered.state, "operator_question_candidates")[0]["question_id"],
        "answer": _records(answered.state, "operator_question_answers")[0]["answer_id"],
        "refinement": _records(answered.state, "analysis_refinements")[0]["refinement_id"],
    }

    changed_prompt = "What changed after my answer?"
    uncertain_prompt = "What is still uncertain?"
    chain_prompt = "What did we analyze, what did you ask, and what did my answer change?"
    baseline_candidates = _records(answered.state, "operator_question_candidates")
    baseline_answers = _records(answered.state, "operator_question_answers")
    baseline_refinements = _records(answered.state, "analysis_refinements")
    for prompt, expected in (
        (changed_prompt, ("time-bounded",)),
        (uncertain_prompt, ("uncertainty",)),
        (chain_prompt, ("recorded chain", "when is pump expected to arrive?", "the pump should arrive on friday.")),
    ):
        assert is_evidence_bound_analysis_refinement_recall_message(answered.state, prompt)
        recalled = _record_scenario(answered.state, prompt, tmp_path)
        assert recalled.intent.intent_type == "semantic_evidence_bound_analysis_refinement_recall"
        assert all(item in recalled.reply.lower() for item in expected)
        assert _records(recalled.state, "operator_question_candidates") == baseline_candidates
        assert _records(recalled.state, "operator_question_answers") == baseline_answers
        assert _records(recalled.state, "analysis_refinements") == baseline_refinements
        answered = recalled

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "semantic_problem_frames")[0]["frame_id"] == ids["frame"]
    assert _records(restored, "evidence_bound_analyses")[0]["analysis_id"] == ids["analysis"]
    assert _records(restored, "operator_question_candidates")[0]["question_id"] == ids["candidate"]
    assert _records(restored, "operator_question_answers")[0]["answer_id"] == ids["answer"]
    assert _records(restored, "analysis_refinements")[0]["refinement_id"] == ids["refinement"]
    duplicate = _record_scenario(restored, "The pump should arrive on Friday.", tmp_path)
    assert len(_records(duplicate.state, "operator_question_answers")) == 1
    assert len(_records(duplicate.state, "analysis_refinements")) == 1
