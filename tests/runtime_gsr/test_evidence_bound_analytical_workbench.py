from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    is_evidence_bound_analysis_recall_message,
    start_or_restore_runtime,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph


GOAL = (
    "Your new goal is to use the next source-bound semantic scenarios for bounded analysis. "
    "Keep source evidence, assumptions, validation checks, limits, and safe next actions provisional. "
    "Do not change source code or restart."
)
OPERATIONS = (
    "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
)
INCLINE = "A 2 kg block slides down a frictionless 30 degree incline. What acceleration should it have?"
SQL = "User input is concatenated into a SQL query before execution."
PORTFOLIO = (
    "Portfolio is 70% high-growth tech ETFs, 20% cash, 10% small-cap value. "
    "User worries about a six-month AI correction."
)
EQUATION = "What does F = ma mean as a problem-solving model?"
UNSUPPORTED = "What color is the sky?"


def _state_with_objective(tmp_path):
    result = handle_conversational_message(
        start_or_restore_runtime(tmp_path),
        GOAL,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert result.state.active_objective is not None
    return result.state


def _frames(state):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get("semantic_problem_frames", ()))


def _analyses(state):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get("evidence_bound_analyses", ()))


def _frame_by_domain(state, domain):
    return next(
        item
        for item in _frames(state)
        if item["semantic_input_frame"]["domain_guess"] == domain
    )


def _analysis_by_domain(state, domain):
    return next(item for item in _analyses(state) if item["domain"] == domain)


def _recorded_state(tmp_path):
    state = _state_with_objective(tmp_path)
    for prompt in (OPERATIONS, INCLINE, SQL, PORTFOLIO, EQUATION):
        state = handle_conversational_message(
            state,
            prompt,
            runtime_root=tmp_path,
            run_background_cycle=False,
        ).state
    return state


def test_frames_compile_to_evidence_bound_analyses_with_source_lineage_and_no_side_effects(tmp_path):
    state = _state_with_objective(tmp_path)
    graph_before = load_graph(tmp_path)
    expected = (
        (OPERATIONS, "operations_logistics_receivables", "pump delivery"),
        (INCLINE, "physics_mechanics", "4.9 m/s^2"),
        (SQL, "defensive_cybersecurity", "sql injection candidate"),
        (PORTFOLIO, "finance_portfolio_risk", "concentration"),
        (EQUATION, "physics_equation_model", "net force"),
    )

    for prompt, domain, expected_text in expected:
        before_turns = len(state.conversation)
        result = handle_conversational_message(
            state,
            prompt,
            runtime_root=tmp_path,
            run_background_cycle=False,
        )
        state = result.state
        frame = _frame_by_domain(state, domain)
        analysis = _analysis_by_domain(state, domain)

        assert result.intent.intent_type == "semantic_problem_modeling"
        assert len(state.conversation) == before_turns + 2
        assert expected_text in result.reply.lower()
        assert analysis["record_kind"] == "evidence_bound_analysis_record"
        assert analysis["objective_id"] == state.active_objective.objective_id
        assert analysis["provenance_status"] == "active_objective_source_bound_provisional"
        assert analysis["source_frame_id"] == frame["frame_id"]
        assert analysis["source_problem_model_id"] == frame["problem_model"]["problem_model_id"]
        assert analysis["source_turn_id"] == frame["semantic_input_frame"]["source_turn_id"]
        assert analysis["source_text"] == frame["semantic_input_frame"]["source_text"]
        assert analysis["evidence_items"]
        assert all(item["source_span"] for item in analysis["evidence_items"])
        assert all(item["confidence_label"] == "source_stated" for item in analysis["evidence_items"])
        assert analysis["validation_checks"]
        assert analysis["safe_next_actions"]
        assert all(item["tool_required"] is False for item in analysis["safe_next_actions"])
        assert all(item["external_action"] is False for item in analysis["safe_next_actions"])
        assert analysis["status"] == "provisional_analysis"
        assert "graph claim" in result.reply.lower()
        assert "external action" in result.reply.lower()

    graph_after = load_graph(tmp_path)
    assert len(_frames(state)) == 5
    assert len(_analyses(state)) == 5
    assert len({item["analysis_id"] for item in _analyses(state)}) == 5
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claims) == len(graph_before.claims)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert len(graph_after.packets) == len(graph_before.packets)
    assert len(graph_after.reviews) == len(graph_before.reviews)
    assert len(graph_after.admissions) == len(graph_before.admissions)
    assert not state.pending_chat_requests
    assert not state.resolved_chat_requests
    assert not state.completed_cycle_keys


def test_analysis_exact_once_restart_and_read_only_cross_domain_recall(tmp_path):
    state = _recorded_state(tmp_path)
    analysis_ids = tuple(item["analysis_id"] for item in _analyses(state))
    frame_ids = tuple(item["frame_id"] for item in _frames(state))
    operations = _analysis_by_domain(state, "operations_logistics_receivables")

    repeated = handle_conversational_message(
        state,
        OPERATIONS,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert tuple(item["analysis_id"] for item in _analyses(repeated.state)) == analysis_ids
    assert sum(
        1
        for item in repeated.state.objective_progress
        if item.get("event") == "evidence_bound_analysis_recorded"
        and item.get("analysis_id") == operations["analysis_id"]
    ) == 1

    recalls = (
        ("What operational bottleneck did you identify?", "pump delivery"),
        ("What method did you use for the incline problem?", "newtonian force decomposition"),
        ("What made the SQL case defensive?", "untrusted input"),
        ("What were the main finance risks?", "concentration"),
        ("What validation check applies to F = ma?", "net force"),
    )
    baseline = _analyses(repeated.state)
    state = repeated.state
    for prompt, expected_text in recalls:
        assert is_evidence_bound_analysis_recall_message(state, prompt)
        result = handle_conversational_message(
            state,
            prompt,
            runtime_root=tmp_path,
            run_background_cycle=False,
        )
        state = result.state
        assert result.intent.intent_type == "semantic_evidence_bound_analysis_recall"
        assert expected_text in result.reply.lower()
        assert "read-only source-bound analysis recall" in result.reply.lower()
        assert _analyses(state) == baseline
        assert not state.pending_chat_requests

    restored = start_or_restore_runtime(tmp_path)
    assert tuple(item["analysis_id"] for item in _analyses(restored)) == analysis_ids
    assert tuple(item["frame_id"] for item in _frames(restored)) == frame_ids
    after_restart = handle_conversational_message(
        restored,
        OPERATIONS,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )
    assert tuple(item["analysis_id"] for item in _analyses(after_restart.state)) == analysis_ids
    assert sum(
        1
        for item in after_restart.state.objective_progress
        if item.get("event") == "evidence_bound_analysis_recorded"
        and item.get("analysis_id") == operations["analysis_id"]
    ) == 1


def test_cyber_and_finance_analysis_stay_defensive_and_nonexecuting(tmp_path):
    state = _state_with_objective(tmp_path)
    for prompt in (SQL, PORTFOLIO):
        state = handle_conversational_message(
            state,
            prompt,
            runtime_root=tmp_path,
            run_background_cycle=False,
        ).state

    cyber = _analysis_by_domain(state, "defensive_cybersecurity")
    finance = _analysis_by_domain(state, "finance_portfolio_risk")
    assert cyber["selected_method"] == "defensive source-to-sink review"
    assert "exploit payload" in " ".join(cyber["prohibited_actions"]).lower()
    assert "scan a target" in " ".join(cyber["prohibited_actions"]).lower()
    assert all(item["external_action"] is False for item in cyber["safe_next_actions"])
    assert finance["selected_method"] == "concentration and scenario risk analysis"
    assert any("100%" in item["expected_property"] for item in finance["validation_checks"])
    assert "trade" in " ".join(finance["prohibited_actions"]).lower()
    assert "fabricate market" in " ".join(finance["prohibited_actions"]).lower()
    assert all(item["external_action"] is False for item in finance["safe_next_actions"])
    assert not state.pending_chat_requests
    assert not state.resolved_chat_requests


def test_unbound_and_unsupported_chat_never_creates_an_analysis_record(tmp_path):
    unbound = start_or_restore_runtime(tmp_path / "unbound")
    no_objective = handle_conversational_message(
        unbound,
        OPERATIONS,
        runtime_root=tmp_path / "unbound",
        run_background_cycle=False,
    )
    assert no_objective.intent.intent_type == "ordinary_conversation"
    assert no_objective.state.active_objective is None

    state = _recorded_state(tmp_path / "with-objective")
    analyses_before = _analyses(state)
    ordinary = handle_conversational_message(
        state,
        "What is 2 + 2?",
        runtime_root=tmp_path / "with-objective",
        run_background_cycle=False,
    )
    unsupported = handle_conversational_message(
        ordinary.state,
        UNSUPPORTED,
        runtime_root=tmp_path / "with-objective",
        run_background_cycle=False,
    )

    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "evidence-bound analysis" not in ordinary.reply.lower()
    assert _analyses(ordinary.state) == analyses_before
    assert unsupported.intent.intent_type == "ordinary_conversation"
    assert _analyses(unsupported.state) == analyses_before
    assert not unsupported.state.pending_chat_requests
