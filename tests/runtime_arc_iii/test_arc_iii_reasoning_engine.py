from orchestration.runtime.arc_iii_local_answer import is_arc_iii_question, run_arc_iii_answer
from orchestration.runtime.arc_iii_reasoning_engine import (
    build_arc_iii_checkpoint,
    build_reasoning_context,
    build_reasoning_graph,
    build_self_consistency,
    derive_confidence,
    generate_hypotheses,
    run_reasoning,
)


def test_arc_iii_context_builder_assembles_substrate_objects_without_mutation():
    context = build_reasoning_context("Why is this true?")
    assert context.entities
    assert context.concepts
    assert context.relationships
    assert context.observations
    assert context.evidence
    assert context.procedures
    assert context.substrate_mutated is False


def test_arc_iii_reasoning_graph_is_session_only_and_cited():
    graph = build_reasoning_graph(build_reasoning_context("Why is this true?"))
    assert graph.session_only is True
    assert graph.destroyed_after_request is True
    assert graph.nodes
    assert graph.edges
    assert all(edge.citation for edge in graph.edges)


def test_arc_iii_hypotheses_are_not_promoted():
    context = build_reasoning_context("Why is this true?")
    graph = build_reasoning_graph(context)
    hypotheses = generate_hypotheses(context, graph)
    assert len(hypotheses) >= 2
    assert all(hypothesis.promoted is False for hypothesis in hypotheses)


def test_arc_iii_confidence_never_exceeds_supporting_edges():
    graph = build_reasoning_graph(build_reasoning_context("Why is this true?"))
    derived = derive_confidence(graph)
    assert derived <= min(edge.confidence for edge in graph.edges)
    assert 0 <= derived <= 1


def test_arc_iii_full_reasoning_contains_required_layers():
    data = run_reasoning("Why is this true?")
    for key in (
        "reasoning_context",
        "reasoning_graph",
        "hypotheses",
        "evidence_chain",
        "contradiction_framework",
        "alternative_paths",
        "counterfactual",
        "goal_deliberation",
        "explanation_tree",
        "reflection_pass",
        "reasoning_transaction",
    ):
        assert key in data
    assert data["knowledge_mutation_performed"] is False
    assert data["provider_call_performed"] is False


def test_arc_iii_self_consistency_is_deterministic():
    data = build_self_consistency("Why is this true?")
    assert data["rerun_performed"] is True
    assert data["divergence"] is False


def test_arc_iii_checkpoint_preserves_global_invariants():
    data = build_arc_iii_checkpoint()
    assert data["model_b_default"] == "unchanged"
    assert data["hyb1"] == "dormant_env_gated"
    assert data["reasoning_transient"] is True
    assert data["reasoning_graph_destroyed_after_request"] is True
    assert all(value is False for value in data["safety_invariants"].values())


def test_arc_iii_local_answers_cover_manual_smoke_safely():
    prompts = (
        "Why is this true?",
        "What evidence supports it?",
        "What evidence opposes it?",
        "Show reasoning graph.",
        "Show confidence.",
        "Show discarded hypotheses.",
        "Show reflection.",
    )
    for prompt in prompts:
        assert is_arc_iii_question(prompt)
        data = run_arc_iii_answer(prompt)
        assert data["phase"] == "Runtime ARC III"
        assert data["safety"]["knowledge_mutation_performed"] is False
        assert data["safety"]["memory_mutation_performed"] is False
        assert data["safety"]["provider_call_performed"] is False
        assert data["safety"]["hypotheses_promoted"] is False
