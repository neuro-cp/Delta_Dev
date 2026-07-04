from orchestration.runtime.arc_vi_executive_cognition import (
    build_arc_vi_checkpoint,
    build_decision_graph,
    build_executive_transaction,
    create_executive_goal,
    decompose_goal,
    evaluate_constraints,
    simulate_multi_goal_schedule,
)
from orchestration.runtime.arc_vi_local_answer import is_arc_vi_question, run_arc_vi_answer


def test_arc_vi_goal_object_is_planning_only():
    goal = create_executive_goal("topic X")
    assert goal.goal_id
    assert goal.status == "planning_only"
    assert goal.execution_performed is False
    assert "no_execution" in goal.constraints


def test_arc_vi_goal_decomposition_generates_tasks_without_execution():
    tasks = decompose_goal(create_executive_goal("topic X"))
    assert len(tasks) >= 4
    assert all(task.status == "planned_only" for task in tasks)
    assert tasks[-1].dependencies


def test_arc_vi_decision_graph_is_transient():
    goal = create_executive_goal("topic X")
    graph = build_decision_graph(goal, decompose_goal(goal))
    assert graph.transient is True
    assert graph.nodes
    assert graph.edges


def test_arc_vi_constraints_block_execution_paths():
    constraints = evaluate_constraints(create_executive_goal("topic X"))
    assert "autonomous_execution_disabled" in constraints["blockers"]
    assert "scheduler_disabled" in constraints["blockers"]
    assert constraints["safety"] == "blocked_for_execution"


def test_arc_vi_scheduler_is_simulation_only():
    schedule = simulate_multi_goal_schedule((create_executive_goal("topic X"),))
    assert schedule["simulation_only"] is True
    assert schedule["os_scheduler_started"] is False
    assert schedule["background_workers_started"] is False


def test_arc_vi_transaction_completes_planning_only():
    tx = build_executive_transaction(create_executive_goal("topic X"))
    assert tx.completed_planning_only is True
    assert tx.persistent_execution is False
    assert "destroy" in tx.stages


def test_arc_vi_checkpoint_preserves_global_safety():
    data = build_arc_vi_checkpoint("topic X")
    assert data["model_b_default"] == "unchanged"
    assert data["hyb1"] == "dormant_env_gated"
    assert data["training_performed"] is False
    assert data["provider_authority_granted"] is False
    assert data["autonomous_execution_performed"] is False
    assert data["scheduler_started"] is False
    assert data["memory_mutation_performed"] is False
    assert data["knowledge_mutation_performed"] is False
    assert all(value is False for value in data["safety_invariants"].values())


def test_arc_vi_local_answers_cover_manual_smoke_safely():
    prompts = (
        "Create a goal to understand topic X.",
        "Break this goal into tasks.",
        "Why did you choose those tasks?",
        "What evidence would you require?",
        "What capabilities would be used?",
        "What blocks execution?",
        "Why can't you execute this plan?",
    )
    for prompt in prompts:
        assert is_arc_vi_question(prompt)
        data = run_arc_vi_answer(prompt)
        assert data["phase"] == "Runtime ARC VI"
        assert data["safety"]["training_performed"] is False
        assert data["safety"]["provider_authority_granted"] is False
        assert data["safety"]["autonomous_execution_performed"] is False
        assert data["safety"]["scheduler_started"] is False
        assert data["safety"]["memory_mutation_performed"] is False
