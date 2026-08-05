from orchestration.runtime.conversational_runtime_operation import (
    background_cycle_hold_reason,
    handle_conversational_message,
    is_semantic_problem_frame_recall_message,
    is_semantic_problem_modeling_message,
    run_background_objective_cycle,
    start_or_restore_runtime,
)
from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel
from orchestration.runtime.provisional_semantic_consolidation import load_graph
from orchestration.runtime.semantic_problem_modeling import compile_semantic_problem_frame


GOAL = (
    "Your new goal is to review a small set of source-bound semantic scenarios. "
    "Keep their interpretations provisional, do not change source code, and do not restart."
)
CONSTRAINED_GOAL = (
    "Your new goal is to interpret the next few source-bound semantic scenarios as provisional semantic frames. "
    "Preserve the source, assumptions, uncertainty, safety limits, and validation checks. "
    "Do not call a model, access a provider, take an external action, change source code, or restart. "
    "Wait for the scenarios."
)
OPERATIONS_NOTE = (
    "Read this operations note: Invoice #A17 is 14 days overdue. "
    "Crew North cannot start the drainage job until the pump is delivered."
)
INCLINE_PROBLEM = (
    "Model this physics problem: A 2 kg block slides down a frictionless 30 degree incline. "
    "What is its acceleration?"
)
DEFENSIVE_SQL_FINDING = (
    "Review this defensive finding: User input is concatenated into a SQL query before execution."
)
PORTFOLIO_SCENARIO = (
    "Frame this portfolio scenario: Portfolio has 60% technology ETF, 30% broad-market index fund, "
    "and 10% cash. The operator worries about an AI/tech correction over a six-month horizon."
)
NEWTONS_EQUATION = "Explain F = ma as a model, including what it can solve for."
DASHBOARD_ANALYSIS = (
    "Analyze this simple dashboard goal: A contractor wants to see overdue invoices, today's jobs, "
    "and urgent client messages on one screen."
)


def _state_with_objective(tmp_path):
    result = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        GOAL,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert result.state.active_objective is not None
    return result.state


def _recorded_state(tmp_path):
    state = _state_with_objective(tmp_path)
    for prompt in (
        OPERATIONS_NOTE,
        INCLINE_PROBLEM,
        DEFENSIVE_SQL_FINDING,
        PORTFOLIO_SCENARIO,
        NEWTONS_EQUATION,
    ):
        state = handle_conversational_message(
            state,
            prompt,
            runtime_root=tmp_path,
            run_background_cycle=False,
        ).state
    return state


def _frames(state):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get("semantic_problem_frames", ()))


def _frame_by_domain(state, domain):
    return next(
        item
        for item in _frames(state)
        if item["semantic_input_frame"]["domain_guess"] == domain
    )


def test_supported_inputs_compile_to_deterministic_source_bound_provisional_frames(tmp_path):
    state = _state_with_objective(tmp_path)
    graph_before = load_graph(tmp_path)
    expected_domains = (
        "operations_logistics_receivables",
        "physics_mechanics",
        "defensive_cybersecurity",
        "finance_portfolio_risk",
        "physics_equation_model",
    )

    for prompt, domain in zip(
        (OPERATIONS_NOTE, INCLINE_PROBLEM, DEFENSIVE_SQL_FINDING, PORTFOLIO_SCENARIO, NEWTONS_EQUATION),
        expected_domains,
        strict=True,
    ):
        before_turns = len(state.conversation)
        assert is_semantic_problem_modeling_message(state, prompt)
        result = handle_conversational_message(
            state,
            prompt,
            runtime_root=tmp_path,
            run_background_cycle=False,
        )
        state = result.state
        frame = _frame_by_domain(state, domain)

        assert result.intent.intent_type == "semantic_problem_modeling"
        assert len(state.conversation) == before_turns + 2
        assert frame["record_kind"] == "semantic_problem_modeling_frame"
        assert frame["objective_id"] == state.active_objective.objective_id
        assert frame["provenance_status"] == "active_objective_source_bound_provisional"
        assert frame["semantic_input_frame"]["source_text"]
        assert frame["semantic_input_frame"]["source_turn_id"]
        assert frame["semantic_input_frame"]["source_spans"]
        assert frame["semantic_input_frame"]["status"] == "provisional_interpreted"
        assert frame["problem_model"]["status"] == "provisional_problem_model"
        assert frame["action_affordances"]
        assert "provisional" in result.reply.lower()
        assert "reviewed or admitted knowledge" in result.reply.lower()

    graph_after = load_graph(tmp_path)
    assert tuple(item["semantic_input_frame"]["domain_guess"] for item in _frames(state)) == expected_domains
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claims) == len(graph_before.claims)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert len(graph_after.packets) == len(graph_before.packets)
    assert len(graph_after.reviews) == len(graph_before.reviews)
    assert len(graph_after.admissions) == len(graph_before.admissions)
    assert not state.pending_chat_requests
    assert not state.resolved_chat_requests


def test_problem_frames_are_exact_once_and_preserved_across_restart(tmp_path):
    state = _recorded_state(tmp_path)
    before = _frame_by_domain(state, "operations_logistics_receivables")
    frame_ids = tuple(item["frame_id"] for item in _frames(state))
    progress_before = tuple(
        item
        for item in state.objective_progress
        if item.get("event") == "semantic_problem_frame_recorded"
    )

    repeated = handle_conversational_message(
        state,
        OPERATIONS_NOTE,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    repeated_frames = _frames(repeated.state)
    repeated_events = tuple(
        item
        for item in repeated.state.objective_progress
        if item.get("event") == "semantic_problem_frame_recorded"
    )
    restored = start_or_restore_runtime(tmp_path)
    after_restart = handle_conversational_message(
        restored,
        OPERATIONS_NOTE,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )

    assert len(repeated_frames) == 5
    assert tuple(item["frame_id"] for item in repeated_frames) == frame_ids
    assert tuple(item["frame_id"] for item in _frames(after_restart.state)) == frame_ids
    assert _frame_by_domain(after_restart.state, "operations_logistics_receivables")["created_at"] == before["created_at"]
    assert repeated_events == progress_before
    assert sum(
        1
        for item in after_restart.state.objective_progress
        if item.get("event") == "semantic_problem_frame_recorded"
        and item.get("frame_id") == before["frame_id"]
    ) == 1


def test_read_only_recalls_select_the_correct_source_bound_frame_without_new_records(tmp_path):
    state = _recorded_state(tmp_path)
    baseline_frames = _frames(state)
    recalls = (
        ("What did you perceive in the operations note?", "overdue receivable"),
        ("What was the unknown target in the incline problem?", "acceleration down the incline"),
        ("What made the SQL example a defensive finding?", "sql injection candidate"),
        ("What was the key financial risk?", "concentration risk"),
        ("What does F = ma let you solve for?", "net force"),
    )

    for prompt, expected_text in recalls:
        assert is_semantic_problem_frame_recall_message(state, prompt)
        result = handle_conversational_message(
            state,
            prompt,
            runtime_root=tmp_path,
            run_background_cycle=False,
        )
        state = result.state

        assert result.intent.intent_type == "semantic_problem_frame_recall"
        assert expected_text in result.reply.lower()
        assert "read-only recall" in result.reply.lower()
        assert _frames(state) == baseline_frames
        assert not state.pending_chat_requests


def test_unbound_or_nonsemantic_chat_remains_on_the_ordinary_path(tmp_path):
    no_objective = start_or_restore_runtime(tmp_path / "no-objective")
    assert not is_semantic_problem_modeling_message(no_objective, OPERATIONS_NOTE)
    ordinary_source = handle_conversational_message(
        no_objective,
        OPERATIONS_NOTE,
        runtime_root=tmp_path / "no-objective",
        run_background_cycle=False,
    )

    state = _recorded_state(tmp_path / "with-objective")
    frames_before = _frames(state)
    ordinary_math = handle_conversational_message(
        state,
        "What is 2 + 2?",
        runtime_root=tmp_path / "with-objective",
        run_background_cycle=False,
    )

    assert ordinary_source.intent.intent_type == "ordinary_conversation"
    assert "semantic_problem_frames" not in (ordinary_source.state.active_objective.provenance if ordinary_source.state.active_objective else {})
    assert ordinary_math.intent.intent_type == "ordinary_conversation"
    assert "semantic frame" not in ordinary_math.reply.lower()
    assert "provisional" not in ordinary_math.reply.lower()
    assert "local model" not in ordinary_math.reply.lower()
    assert _frames(ordinary_math.state) == frames_before
    assert not ordinary_math.state.pending_chat_requests


def test_compiler_rejects_unsupported_text_without_creating_an_ambiguous_frame():
    assert compile_semantic_problem_frame(
        "What color is the sky?",
        frame_scope_id="test-scope",
    ) is None
    assert compile_semantic_problem_frame(
        DASHBOARD_ANALYSIS,
        frame_scope_id="test-scope",
    ) is None


def test_operator_wait_and_no_model_constraints_hold_background_work_without_blocking_frames_or_restart(tmp_path):
    started = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        CONSTRAINED_GOAL,
        runtime_root=tmp_path,
        run_background_cycle=True,
        model_runner=ScriptedSemanticModel(),
    )
    state = started.state
    objective = state.active_objective
    assert objective is not None
    constraints = objective.provenance["execution_constraints"]

    assert constraints["no_local_model"] is True
    assert constraints["no_provider"] is True
    assert constraints["no_external_action"] is True
    assert constraints["wait_for_operator_input"] is True
    assert background_cycle_hold_reason(state) == "wait_for_operator_input"
    assert started.background_cycle_started is False
    assert not state.completed_cycle_keys
    assert not any(item.get("event") == "background_cycle" for item in state.objective_progress)
    assert "waiting for your next input" in started.reply.lower()

    frame_result = handle_conversational_message(
        state,
        OPERATIONS_NOTE,
        runtime_root=tmp_path,
        run_background_cycle=True,
        model_runner=ScriptedSemanticModel(),
    )
    assert frame_result.intent.intent_type == "semantic_problem_modeling"
    assert frame_result.background_cycle_started is False
    assert len(_frames(frame_result.state)) == 1
    assert not frame_result.state.completed_cycle_keys
    assert not any(item.get("event") == "background_cycle" for item in frame_result.state.objective_progress)

    restored = start_or_restore_runtime(tmp_path)
    assert background_cycle_hold_reason(restored) == "wait_for_operator_input"
    assert _frames(restored)[0]["frame_id"] == _frames(frame_result.state)[0]["frame_id"]
    held = run_background_objective_cycle(
        restored,
        runtime_root=tmp_path,
        reason="restart_waiting_fixture",
        model_runner=ScriptedSemanticModel(),
    )
    assert held == restored

    ordinary = handle_conversational_message(
        restored,
        "What is 2 + 2?",
        runtime_root=tmp_path,
        run_background_cycle=True,
        model_runner=ScriptedSemanticModel(),
    )
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert ordinary.background_cycle_started is False
    assert len(_frames(ordinary.state)) == 1
    assert not ordinary.state.pending_chat_requests

    released = handle_conversational_message(
        ordinary.state,
        "You may use a local model now.",
        runtime_root=tmp_path,
        run_background_cycle=False,
        model_runner=ScriptedSemanticModel(),
    )
    assert released.intent.intent_type == "objective_execution_constraints_release"
    assert background_cycle_hold_reason(released.state) == ""
    assert released.state.active_objective.provenance["execution_constraints"]["no_provider"] is True
    assert any(item.get("event") == "objective_execution_constraints_released" for item in released.state.objective_progress)

    advanced = run_background_objective_cycle(
        released.state,
        runtime_root=tmp_path,
        reason="explicit_operator_release_fixture",
        model_runner=ScriptedSemanticModel(),
    )
    assert len(advanced.completed_cycle_keys) == 1
