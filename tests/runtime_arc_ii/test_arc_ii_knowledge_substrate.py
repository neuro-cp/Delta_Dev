from orchestration.runtime.arc_ii_knowledge_substrate import (
    KNOWLEDGE_TYPES,
    build_arc_ii_checkpoint,
    build_health_metrics,
    build_knowledge_graph,
    build_knowledge_transaction,
    build_sample_substrate,
    make_version,
    semantic_query,
)
from orchestration.runtime.arc_ii_local_answer import is_arc_ii_question, run_arc_ii_answer


def test_arc_ii_defines_required_knowledge_objects_with_safety_fields():
    data = build_arc_ii_checkpoint()
    types = {obj["type"] for obj in data["knowledge_objects"]}
    assert set(KNOWLEDGE_TYPES) <= types
    for obj in data["knowledge_objects"]:
        for field in ("id", "type", "created", "updated", "provenance", "confidence", "review_state", "rollback_token", "audit_id"):
            assert field in obj
        assert obj["rollback_token"]
        assert obj["audit_id"]


def test_arc_ii_registries_are_reviewable_and_non_persistent():
    data = build_arc_ii_checkpoint()
    assert data["registries"]["entity_registry"]["objects"]
    assert data["registries"]["observation_registry"]["objects"]
    assert data["registries"]["evidence_registry"]["objects"]
    assert data["registries"]["relationship_registry"]["objects"]
    assert data["registries"]["concept_registry"]["objects"]
    assert data["live_persistence"] is False
    assert data["live_knowledge_integration"] is False


def test_arc_ii_graph_and_query_layer_are_deterministic():
    substrate = build_sample_substrate()
    graph = build_knowledge_graph(substrate["objects"])
    assert graph["deterministic"] is True
    assert graph["graph_only"] is True
    assert graph["nodes"]
    assert graph["edges"]
    assert semantic_query(substrate["objects"], "supporting_evidence")
    assert semantic_query(substrate["objects"], "observations")
    assert semantic_query(substrate["objects"], "procedures")


def test_arc_ii_health_metrics_and_diagnostics_are_report_only():
    data = build_arc_ii_checkpoint()
    metrics = build_health_metrics([obj for obj in build_sample_substrate()["objects"]], data["knowledge_graph"])
    assert "coverage" in metrics
    assert "confidence_distribution" in metrics
    assert data["semantic_diagnostics"]["mutation_performed"] is False


def test_arc_ii_transactions_stop_before_integration():
    obj = build_sample_substrate()["objects"][0]
    transaction = build_knowledge_transaction(obj, "approved")
    assert transaction.reviewed is True
    assert transaction.integrated is False
    assert transaction.rollback_token


def test_arc_ii_versioned_objects_preserve_history_and_rollback():
    obj = build_sample_substrate()["objects"][0]
    version = make_version(obj, label="new draft")
    assert version.version == obj.version + 1
    assert version.parent == obj.id
    assert version.supersedes == obj.id
    assert obj.id in version.history
    assert version.rollback_token


def test_arc_ii_local_answers_cover_manual_smoke_safely():
    prompts = (
        "Show Entity Registry",
        "Show Concept Registry",
        "Show Observation Registry",
        "Show Evidence Registry",
        "Show Knowledge Graph",
        "Show Provenance Tree",
        "Explain Knowledge Transaction",
        "Explain why this observation is not truth",
        "Explain why evidence is advisory",
    )
    for prompt in prompts:
        assert is_arc_ii_question(prompt)
        data = run_arc_ii_answer(prompt)
        assert data["phase"] == "Runtime ARC II"
        assert data["safety"]["training_performed"] is False
        assert data["safety"]["provider_authority_granted"] is False
        assert data["safety"]["memory_mutation_performed"] is False
        assert data["safety"]["live_knowledge_integration"] is False


def test_arc_ii_checkpoint_preserves_global_invariants():
    data = build_arc_ii_checkpoint()
    assert data["model_b_default"] == "unchanged"
    assert data["hyb1"] == "dormant_env_gated"
    assert data["authoritative_substrate"] is False
    assert all(value is False for value in data["safety_invariants"].values())
