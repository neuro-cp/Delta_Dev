from orchestration.runtime.arc_iv_knowledge_evolution import (
    TRANSACTION_STAGES,
    KnowledgeEvolutionEngine,
    build_arc_iv_checkpoint,
    build_controlled_transaction,
    build_knowledge_diff,
    build_rollback_plan,
    build_version_graph,
    simulate_integration,
)
from orchestration.runtime.arc_iv_local_answer import is_arc_iv_question, run_arc_iv_answer
from orchestration.runtime.v31_learning_proposal import build_learning_proposals


def _candidate():
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")[0]
    return KnowledgeEvolutionEngine().build_candidate(proposal)


def test_arc_iv_engine_builds_candidate_without_writes():
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")[0]
    engine = KnowledgeEvolutionEngine()
    candidate = engine.build_candidate(proposal)
    assert candidate.source_proposal_id == proposal.proposal_id
    assert candidate.affected_entities
    assert candidate.affected_concepts
    assert candidate.affected_relationships
    assert candidate.write_performed is False


def test_arc_iv_version_graph_and_simulation_are_report_only():
    candidate = _candidate()
    graph = build_version_graph(candidate)
    simulation = simulate_integration(candidate)
    assert graph["live_write_performed"] is False
    assert len(graph["nodes"]) == 2
    assert simulation["write_performed"] is False
    assert simulation["graph_changes"]["new_candidate_node"] == 1


def test_arc_iv_controlled_transaction_stops_ready_to_integrate():
    tx = build_controlled_transaction(_candidate())
    assert tuple(tx.stages) == TRANSACTION_STAGES
    assert tx.current_stage == "ready_to_integrate"
    assert tx.ready_to_integrate is True
    assert tx.integrated is False
    assert tx.write_performed is False


def test_arc_iv_rollback_and_diff_are_available_without_mutation():
    candidate = _candidate()
    rollback = build_rollback_plan(candidate)
    diff = build_knowledge_diff(candidate)
    assert rollback.rollback_available is True
    assert rollback.dependency_list
    assert diff["diff_only"] is True
    assert diff["removed_relationships"] == []


def test_arc_iv_checkpoint_preserves_global_safety():
    data = build_arc_iv_checkpoint()
    assert data["live_knowledge_mutation"] is False
    assert data["integration_write_performed"] is False
    assert data["simulation_only"] is True
    assert data["model_b_default"] == "unchanged"
    assert data["hyb1"] == "dormant_env_gated"
    assert all(value is False for value in data["safety_invariants"].values())


def test_arc_iv_local_answers_cover_manual_smoke_safely():
    prompts = (
        "Show evolution candidate.",
        "Explain why this should evolve.",
        "Show impact.",
        "Show rollback.",
        "Show version graph.",
        "Show approval chain.",
        "Show simulation.",
        "What conflicts?",
        "Who must approve?",
    )
    for prompt in prompts:
        assert is_arc_iv_question(prompt)
        data = run_arc_iv_answer(prompt)
        assert data["phase"] == "Runtime ARC IV"
        assert data["safety"]["training_performed"] is False
        assert data["safety"]["provider_authority_granted"] is False
        assert data["safety"]["knowledge_mutation_performed"] is False
        assert data["safety"]["integration_write_performed"] is False
