from dataclasses import replace
import json
import tkinter as tk
from types import SimpleNamespace

from orchestration.runtime.chat_first_dispatch_contract import MessageDispatchResult, plan_message_dispatch
from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    handle_conversational_message,
    record_foreground_message_for_reconciliation,
    run_background_objective_cycle,
    start_or_restore_runtime,
)


GOAL_AND_QUESTION = "Your new goal is to study engine efficiency. Also, why does turbo lag happen?"
OVERSIZED_KNOWLEDGE_GOAL = (
    "Your new goal is to build a local knowledge map of residential heat-pump water heaters. "
    "Study how they work, compressor operation, refrigerant cycle, tank stratification, recovery time, "
    "electrical requirements, condensate drainage, room-volume constraints, noise, cold-space performance, "
    "hybrid resistance backup, installation location, maintenance, anode rods, filter cleaning, safety considerations, "
    "permitting, operating cost, utility rebates, household hot-water demand, conventional-electric comparison, seismic bracing, water chemistry, leak detection, service access, and when a conventional electric water heater may be a better fit. "
    "Use local cognition and existing local evidence first. Ask me only for missing information that materially changes the answer. "
    "Continue until your available local resources or budgets are exhausted, then give a clear completion, blocking, or remaining-gap report. "
    "Do not change source code or restart."
)
ADOPTION_AND_QUESTION = "Yes, adopt it. Also remind me what the winning score was."
CORRECTION_AND_QUESTION = "No, I meant your earlier angular-momentum answer. Also, why is the sky blue?"


def _state(tmp_path):
    return start_or_restore_runtime(tmp_path)


def _state_with_goal(tmp_path):
    return handle_conversational_message(
        _state(tmp_path),
        "Your goal today is to improve your English comprehension so we can communicate better.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state


def _with_request(state, request_type):
    request = ChatAddressableRequest(
        request_id=f"request-{request_type}",
        request_type=request_type,
        objective_id=state.active_objective.objective_id,
        goal_label="Language understanding",
        prompt_text="Review this bounded request.",
        max_calls=1,
        max_spend_usd=1.0,
    )
    return replace(state, pending_chat_requests=(request,))


def _with_requests(state, *request_types):
    requests = tuple(
        ChatAddressableRequest(
            request_id=f"request-{index}-{request_type}",
            request_type=request_type,
            objective_id=state.active_objective.objective_id,
            goal_label="Language understanding",
            prompt_text="Review this bounded request.",
            max_calls=1,
            max_spend_usd=1.0,
        )
        for index, request_type in enumerate(request_types, start=1)
    )
    return replace(state, pending_chat_requests=requests)


def test_pure_message_plans_are_independent_and_non_mutating(tmp_path):
    state = _state(tmp_path)
    before = state.as_record()

    plan = plan_message_dispatch(state, "What color is the sky?")

    assert plan.foreground.requested is True
    assert plan.foreground.owner == "rc2_router"
    assert plan.control.detected is False
    assert plan.persistence.expected_single_user_turn is True
    assert plan.persistence.transcript_write_count == 1
    assert state.as_record() == before


def test_background_preface_keeps_explicit_factual_clause_for_foreground(tmp_path):
    plan = plan_message_dispatch(_state_with_goal(tmp_path), "Okay while you're working on that tell me what color is the sky?")

    assert len(plan.segments) == 2
    assert plan.segments[0].kind == "context_prefix"
    assert plan.segments[1].text == "tell me what color is the sky?"
    assert plan.foreground.owner == "rc2_router"


def test_pure_control_messages_have_no_required_foreground_answer(tmp_path):
    state = _state_with_goal(tmp_path)

    for message, control_type in [("Pause the active goal.", "pause_goal"), ("Resume the active goal.", "resume_goal"), ("Stop the active goal.", "stop_goal"), ("Review the active goal.", "goal_review")]:
        plan = plan_message_dispatch(state, message)
        assert plan.control.control_type == control_type
        assert plan.control.detected is True
        assert plan.foreground.requested is False


def test_goal_plus_question_has_dual_handling_plan(tmp_path):
    plan = plan_message_dispatch(_state(tmp_path), GOAL_AND_QUESTION)

    assert plan.control.control_type == "create_goal"
    assert plan.foreground.requested is True
    assert plan.foreground.owner == "rc2_router"
    assert plan.background.start_requested is True
    assert plan.persistence.expected_single_user_turn is True
    assert len(plan.segments) == 2


def test_pending_approval_plus_question_binds_without_consuming(tmp_path):
    state = _with_request(_state_with_goal(tmp_path), "capability_adoption_and_restart")
    before = state.as_record()

    plan = plan_message_dispatch(state, ADOPTION_AND_QUESTION)

    assert plan.control.control_type == "capability_adoption"
    assert plan.pending_request.reply_bound is True
    assert plan.pending_request.consume_once is True
    assert plan.foreground.requested is True
    assert state.as_record() == before


def test_provider_and_side_thread_replies_are_represented_without_consumption(tmp_path):
    state = _state_with_goal(tmp_path)
    provider = plan_message_dispatch(_with_request(state, "provider_authority"), "Approve one call. Also, why is the sky blue?")
    side_thread = plan_message_dispatch(_with_request(state, "directional_question"), "Yes, prioritize that. Also explain angular momentum.")

    assert provider.control.control_type == "provider_approval"
    assert provider.pending_request.reply_bound is True
    assert provider.foreground.requested is True
    assert side_thread.control.control_type == "side_thread_resolution"
    assert side_thread.pending_request.reply_bound is True
    assert side_thread.foreground.requested is True


def test_unbound_adoption_requests_clarification_without_claiming_foreground(tmp_path):
    plan = plan_message_dispatch(_state(tmp_path), ADOPTION_AND_QUESTION)

    assert plan.control.control_type == "capability_adoption"
    assert plan.control.action == "clarify_target"
    assert plan.pending_request.request_detected is False
    assert plan.foreground.requested is True


def test_correction_and_question_are_dual_without_runtime_mutation(tmp_path):
    state = _state_with_goal(tmp_path)
    before = state.as_record()

    plan = plan_message_dispatch(state, CORRECTION_AND_QUESTION)

    assert plan.control.control_type == "correction"
    assert plan.foreground.requested is True
    assert any(item.terminal_disposition == "control_planned" for item in plan.clauses)
    assert any(item.terminal_disposition == "foreground_planned" for item in plan.clauses)
    assert plan.persistence.transcript_write_count == 1
    assert state.as_record() == before


def test_runtime_state_query_is_a_terminal_control_clause(tmp_path):
    state = _state_with_goal(tmp_path)

    plan = plan_message_dispatch(state, "Are you currently paused or running, and are there pending requests?")

    assert plan.control.control_type == "runtime_state_query"
    assert plan.foreground.requested is False
    assert len(plan.clauses) == 2
    assert all(item.control_type == "runtime_state_query" for item in plan.clauses)
    assert all(item.terminal_disposition == "control_planned" for item in plan.clauses)


def test_local_model_permission_reply_binds_to_visible_request(tmp_path):
    state = _with_request(_state_with_goal(tmp_path), "local_model_execution")

    plan = plan_message_dispatch(state, "Yes, ask it.")

    assert plan.control.control_type == "local_model_permission"
    assert plan.pending_request.reply_bound is True
    assert plan.pending_request.consume_once is True
    assert plan.clauses[0].pending_request_id == "request-local_model_execution"


def test_two_pending_requests_clarify_and_bind_none(tmp_path):
    state = _with_requests(_state_with_goal(tmp_path), "provider_authority", "local_model_execution")

    plan = plan_message_dispatch(state, "Yes, go ahead.")

    assert plan.control.control_type == "clarification"
    assert plan.control.action == "clarify_pending_request"
    assert plan.pending_request.request_detected is False
    assert all(not item.pending_request_id for item in plan.clauses)


def test_ambiguous_reference_plans_clarification_from_reconciler(tmp_path):
    state = _state_with_goal(tmp_path)
    state = record_foreground_message_for_reconciliation(state, "Explain thermal expansion in bridges.", runtime_root=tmp_path)
    state = record_foreground_message_for_reconciliation(state, "Now explain angular momentum in skating.", runtime_root=tmp_path)

    plan = plan_message_dispatch(state, "For the goal, compare that to the prior subject.")

    assert plan.control.control_type == "reference_clarification"
    assert plan.control.action == "create_reference_clarification"
    assert plan.foreground.requested is False
    assert plan.clauses[0].terminal_disposition == "control_planned"


def test_interactive_introspection_questions_route_to_authoritative_runtime_state(tmp_path):
    state = _state_with_goal(tmp_path)

    plan = plan_message_dispatch(state, "What are you doing right now?")

    assert plan.control.control_type == "interactive_introspection"
    assert plan.control.action == "render_interactive_introspection"
    assert plan.foreground.requested is False


def test_association_question_requires_a_contextual_clarification_not_a_bare_yes(tmp_path):
    state = _state_with_goal(tmp_path)
    request = ChatAddressableRequest(
        request_id="association-question",
        request_type="interactive_clarification",
        objective_id=state.active_objective.objective_id,
        goal_label="Association exploration",
        prompt_text="Is this dependency relevant to the direction you want to explore?",
        thread_id=state.active_objective.objective_id,
        rendered_turn_id="association-prompt-turn",
        render_sequence=8,
        accepted_response_types=("clarification",),
        baseline_metrics={"clarification_pressure": "cross_topic_relevance"},
    )
    state = replace(state, pending_chat_requests=(request,))

    bare_yes = plan_message_dispatch(state, "yes")
    contextual_answer = plan_message_dispatch(state, "Yes, that connection is relevant to the direction I want to explore.")

    assert bare_yes.control.detected is False
    assert contextual_answer.control.control_type == "interactive_clarification_resolution"
    assert contextual_answer.control.target_id == request.request_id


def test_latest_rendered_compatible_clarification_owns_a_mixed_reply(tmp_path):
    state = _state_with_goal(tmp_path)
    reference = ChatAddressableRequest(
        request_id="reference-question",
        request_type="reference_clarification",
        objective_id=state.active_objective.objective_id,
        goal_label="Reference clarification",
        prompt_text="Which earlier subject did you mean?",
        rendered_turn_id="reference-prompt-turn",
        render_sequence=4,
        accepted_response_types=("clarification",),
    )
    association = ChatAddressableRequest(
        request_id="association-question",
        request_type="interactive_clarification",
        objective_id=state.active_objective.objective_id,
        goal_label="Association exploration",
        prompt_text="Is this connection relevant to the direction you want to explore?",
        rendered_turn_id="association-prompt-turn",
        render_sequence=9,
        accepted_response_types=("clarification",),
    )
    state = replace(state, pending_chat_requests=(reference, association))

    plan = plan_message_dispatch(state, "I meant that connection is relevant to the direction I want to explore.")

    assert plan.control.control_type == "interactive_clarification_resolution"
    assert plan.control.target_id == association.request_id


def test_plan_is_idempotent_and_json_round_trips(tmp_path):
    state = _state_with_goal(tmp_path)
    first = plan_message_dispatch(state, GOAL_AND_QUESTION)
    second = plan_message_dispatch(state, GOAL_AND_QUESTION)
    record = first.as_record()
    rebuilt = MessageDispatchResult.from_record(json.loads(json.dumps(record)))

    assert first == second
    assert rebuilt == first
    assert first.as_record(include_message_text=False)["original_message"] == ""


def test_ambiguous_or_unknown_message_is_safe_and_does_not_start_worker(tmp_path):
    state = _state(tmp_path)
    plan = plan_message_dispatch(state, "That one, perhaps.")

    assert plan.control.detected is False
    assert plan.background.start_requested is False
    assert plan.events == ()
    assert plan.compatibility.compatibility_mode == "shadow_only"


def test_shadow_integration_records_plan_without_changing_legacy_output(monkeypatch, tmp_path):
    import DELTA

    monkeypatch.setattr(DELTA.DeltaApp, "_warm_default_model", lambda self: None)
    monkeypatch.setattr(DELTA, "CONVERSATIONAL_RUNTIME_ROOT", tmp_path / "conversational-runtime")
    root = tk.Tk()
    try:
        app = DELTA.DeltaApp(root)
        root.update()
        app.chat_input.insert(0, "What color is the sky?")
        app._send_chat()
        root.update()

        transcript = app.chat_history.get("1.0", tk.END).lower()
        diagnostic = app.dispatch_shadow_diagnostics[-1]
        assert "blue" in transcript
        assert diagnostic["foreground"]["owner"] == "rc2_router"
        assert diagnostic["actual"]["legacy_fallthrough"] is True
        assert diagnostic["actual"]["rendered_owner"] == "rc2_router"
        assert diagnostic["original_message"] == ""
    finally:
        root.destroy()


def test_shadow_planner_failure_does_not_break_legacy_chat(monkeypatch, tmp_path):
    import DELTA

    monkeypatch.setattr(DELTA, "plan_message_dispatch", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("shadow failure")))
    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = _state(tmp_path)
    app.dispatch_shadow_diagnostics = []

    message_id = app._record_dispatch_shadow_plan("What color is the sky?")

    assert message_id
    assert app.dispatch_shadow_diagnostics[-1]["diagnostic_error"] == "RuntimeError"


def test_coordinator_renders_foreground_and_goal_receipt_once(monkeypatch, tmp_path):
    import DELTA

    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = _state(tmp_path)
    app.conversational_runtime_root = tmp_path
    app.mode = SimpleNamespace(get=lambda: "Conversation")
    app.developer_overlay_enabled = SimpleNamespace(get=lambda: False)
    app.session_history = []
    app.chat_records = []
    app._recent_history_for_router = lambda: []
    app._update_active_topic_anchor = lambda _payload: None
    app._queue_concept_candidate = lambda _payload: None
    app._append_chat = lambda speaker, text: app.chat_records.append((speaker, text))
    app._append_session = lambda role, content: app.session_history.append({"role": role, "content": content})
    app._refresh_state_cards = lambda: None
    app._refresh_conversational_runtime_status = lambda: None
    app._start_conversational_background_cycle = lambda _reason: True

    plan = plan_message_dispatch(app.conversational_runtime_state, GOAL_AND_QUESTION)
    assert app._coordinate_mixed_dispatch(GOAL_AND_QUESTION, plan) is True

    reply = app.chat_records[-1][1].lower()
    assert "local reasoning model" in reply
    assert "[goal update]" in reply
    assert app.conversational_runtime_state.active_objective is not None
    assert sum(1 for item in app.session_history if item["role"] == "user" and GOAL_AND_QUESTION in item["content"]) == 1


def test_coordinator_persists_the_original_mixed_turn_once(tmp_path):
    import DELTA

    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = _state(tmp_path)
    app.conversational_runtime_root = tmp_path
    app.mode = SimpleNamespace(get=lambda: "Conversation")
    app.developer_overlay_enabled = SimpleNamespace(get=lambda: False)
    app.session_history = []
    app.chat_records = []
    app._recent_history_for_router = lambda: []
    app._update_active_topic_anchor = lambda _payload: None
    app._queue_concept_candidate = lambda _payload: None
    app._append_chat = lambda speaker, text: app.chat_records.append((speaker, text))
    app._append_session = lambda role, content: app.session_history.append({"role": role, "content": content})
    app._refresh_state_cards = lambda: None
    app._refresh_conversational_runtime_status = lambda: None
    app._start_conversational_background_cycle = lambda _reason: True

    assert app._coordinate_mixed_dispatch(GOAL_AND_QUESTION, plan_message_dispatch(app.conversational_runtime_state, GOAL_AND_QUESTION))

    turns = app.conversational_runtime_state.conversation
    assert [item.role for item in turns] == ["user", "assistant"]
    assert turns[0].text == GOAL_AND_QUESTION
    assert turns[0].intent_type == "coordinated_mixed_turn"
    assert turns[1].intent_type == "coordinated_composed_response"


def test_coordinator_treats_oversized_knowledge_goal_as_goal_scope_not_foreground(tmp_path):
    import DELTA

    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = _state(tmp_path)
    app.conversational_runtime_root = tmp_path
    app.mode = SimpleNamespace(get=lambda: "Conversation")
    app.developer_overlay_enabled = SimpleNamespace(get=lambda: False)
    app.session_history = []
    app.chat_records = []
    app._recent_history_for_router = lambda: []
    app._update_active_topic_anchor = lambda _payload: None
    app._queue_concept_candidate = lambda _payload: None
    app._append_chat = lambda speaker, text: app.chat_records.append((speaker, text))
    app._append_session = lambda role, content: app.session_history.append({"role": role, "content": content})
    app._refresh_state_cards = lambda: None
    app._refresh_conversational_runtime_status = lambda: None
    app._start_conversational_background_cycle = lambda _reason: True

    plan = plan_message_dispatch(app.conversational_runtime_state, OVERSIZED_KNOWLEDGE_GOAL)
    assert app._coordinate_mixed_dispatch(OVERSIZED_KNOWLEDGE_GOAL, plan) is True

    reply = app.chat_records[-1][1]
    assert "[Budget boundary]" not in reply
    assert "I can continue, but I need the topic or sentence" not in reply
    assert app.conversational_runtime_state.pending_chat_requests == ()


def test_budget_prompt_owns_yes_when_rendered_after_valid_ordinary_local_model_consent(tmp_path):
    import DELTA

    class FakeInput:
        def get(self):
            return "yes"

        def delete(self, *_args):
            return None

    state = handle_conversational_message(
        _state(tmp_path),
        "Your new goal is to study basement insulation. Study moisture, R value, costs, and installation constraints.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state
    state = replace(state, active_objective=replace(state.active_objective, cycle_budget=1, model_call_budget=1))
    state = run_background_objective_cycle(state, runtime_root=tmp_path, reason="bounded-budget-fixture")
    old_budget = state.active_objective.model_call_budget
    budget_request = replace(state.pending_chat_requests[-1], rendered_turn_id="budget-prompt", render_sequence=20)
    ordinary_request = ChatAddressableRequest(
        request_id="ordinary-local-consent",
        request_type="local_model_execution",
        objective_id="",
        goal_label="Local model permission",
        prompt_text="Ask the local model about the foreground question?",
        baseline_metrics={"question": "What is kinetic energy?"},
        thread_id="foreground-chat",
        created_sequence=1,
        render_sequence=10,
        accepted_response_types=("approved", "denied"),
    )
    state = replace(state, pending_chat_requests=(ordinary_request, budget_request))

    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = state
    app.conversational_runtime_root = tmp_path
    app.conversational_runtime_inference_in_flight = False
    app.live_runtime_request_in_flight = False
    app.live_runtime_session = None
    app.pending_local_model_question = "What is kinetic energy?"
    app.dispatch_shadow_diagnostics = []
    app.chat_input = FakeInput()
    app.session_history = []
    app.chat_records = []
    app._append_chat = lambda speaker, text: app.chat_records.append((speaker, text))
    app._append_session = lambda role, content: app.session_history.append({"role": role, "content": content})
    app._refresh_state_cards = lambda: None
    app._refresh_conversational_runtime_status = lambda: None
    app._set_conversational_runtime_working = lambda: None
    started = []
    app._start_conversational_background_cycle = lambda reason: started.append(reason) or True

    app._send_chat()

    assert app.pending_local_model_question == "What is kinetic energy?"
    assert [item.request_id for item in app.conversational_runtime_state.pending_chat_requests] == [ordinary_request.request_id]
    assert app.conversational_runtime_state.active_objective.model_call_budget > old_budget
    assert app.conversational_runtime_state.resolved_chat_requests[-1].request_type == "knowledge_model_budget_increase"
    assert started == ["pending_chat_request_resolved"]


def test_background_merge_keeps_runtime_budget_request_resolvable(tmp_path):
    import DELTA

    prior = handle_conversational_message(
        _state(tmp_path),
        "Your new goal is to study basement insulation. Study moisture, R value, costs, and installation constraints.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state
    prior = replace(prior, active_objective=replace(prior.active_objective, cycle_budget=1, model_call_budget=1))
    worker_state = run_background_objective_cycle(prior, runtime_root=tmp_path, reason="budget-exhaustion")

    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = prior
    merged = app._merge_conversational_background_result(prior, worker_state)

    assert merged.lifecycle_state == "paused_budget"
    assert len(merged.pending_chat_requests) == 1
    request = merged.pending_chat_requests[0]
    assert request.request_type == "knowledge_model_budget_increase"
    assert request.objective_id == merged.active_objective.objective_id


def test_foreground_local_model_prompt_owns_yes_when_rendered_after_goal_budget_prompt(tmp_path):
    import DELTA

    prior = handle_conversational_message(
        _state(tmp_path),
        "Your new goal is to study basement insulation. Study moisture, R value, costs, and installation constraints.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state
    prior = replace(prior, active_objective=replace(prior.active_objective, cycle_budget=1, model_call_budget=1))
    worker_state = run_background_objective_cycle(prior, runtime_root=tmp_path, reason="budget-exhaustion")
    budget_request = replace(worker_state.pending_chat_requests[-1], rendered_turn_id="budget-prompt", render_sequence=10)
    ordinary_request = ChatAddressableRequest(
        request_id="ordinary-local-consent",
        request_type="local_model_execution",
        objective_id="",
        goal_label="Local model permission",
        prompt_text="Ask the local model about the foreground question?",
        baseline_metrics={"question": "What is kinetic energy?"},
        thread_id="foreground-chat",
        created_sequence=2,
        render_sequence=20,
        accepted_response_types=("approved", "denied"),
    )
    worker_state = replace(worker_state, pending_chat_requests=(budget_request, ordinary_request))

    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = prior
    app.conversational_runtime_root = tmp_path
    app.conversational_runtime_inference_in_flight = False
    app.pending_local_model_question = "What is kinetic energy?"
    app.session_history = []
    app.chat_records = []
    app._append_chat = lambda speaker, text: app.chat_records.append((speaker, text))
    app._append_session = lambda role, content: app.session_history.append({"role": role, "content": content})
    app._refresh_state_cards = lambda: None
    app._refresh_conversational_runtime_status = lambda: None
    selected = []
    def resolve_local(_message, *, request_id=""):
        selected.append(request_id)
        app.conversational_runtime_state = replace(
            app.conversational_runtime_state,
            pending_chat_requests=tuple(
                item for item in app.conversational_runtime_state.pending_chat_requests
                if item.request_id != request_id
            ),
        )
        return "[Local model]\nResolved foreground consent."
    app._resolve_local_model_permission = resolve_local
    app.conversational_runtime_state = app._merge_conversational_background_result(prior, worker_state)

    assert app._handle_conversational_runtime_message("yes") is True

    assert selected == [ordinary_request.request_id]
    assert [item.request_id for item in app.conversational_runtime_state.pending_chat_requests] == [budget_request.request_id]


def test_coordinator_clarifies_unbound_adoption_and_keeps_foreground(tmp_path):
    import DELTA

    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = _state(tmp_path)
    app.conversational_runtime_root = tmp_path
    app.mode = SimpleNamespace(get=lambda: "Conversation")
    app.developer_overlay_enabled = SimpleNamespace(get=lambda: False)
    app.session_history = []
    app.chat_records = []
    app._recent_history_for_router = lambda: []
    app._update_active_topic_anchor = lambda _payload: None
    app._queue_concept_candidate = lambda _payload: None
    app._append_chat = lambda speaker, text: app.chat_records.append((speaker, text))
    app._append_session = lambda role, content: app.session_history.append({"role": role, "content": content})
    app._refresh_state_cards = lambda: None
    app._refresh_conversational_runtime_status = lambda: None
    app._start_conversational_background_cycle = lambda _reason: True

    assert app._coordinate_mixed_dispatch(ADOPTION_AND_QUESTION, plan_message_dispatch(app.conversational_runtime_state, ADOPTION_AND_QUESTION)) is True
    reply = app.chat_records[-1][1].lower()
    assert "do not have an eligible pending capability adoption request" in reply
    assert "local reasoning model" in reply
