from orchestration.runtime.v32_cognitive_kernel import CognitiveKernel
from orchestration.runtime.v33_runtime_message_bus import RuntimeMessageBus, build_sample_event_flow
from orchestration.runtime.v34_cognitive_state import build_runtime_state_snapshot
from orchestration.runtime.v35_transaction_engine import CognitiveTransactionEngine
from orchestration.runtime.v36_unified_audit_graph import build_sample_audit_graph
from orchestration.runtime.v37_capability_registry import CognitiveCapabilityRegistry
from orchestration.runtime.v38_dynamic_pipeline_builder import build_dynamic_pipeline
from orchestration.runtime.v39_kernel_safety_checkpoint import build_kernel_safety_checkpoint
from orchestration.runtime.v39_local_kernel_answer import is_kernel_question, run_kernel_answer


def test_arc_i_kernel_has_required_managers_and_no_authority():
    kernel = CognitiveKernel()
    names = set(kernel.manager_names())
    assert {
        "ExperienceManager",
        "EvidenceManager",
        "RecallManager",
        "ReasoningManager",
        "LearningManager",
        "ReviewManager",
        "IntegrationManager",
        "SafetyManager",
    } <= names
    assert all(manager.mutating is False for manager in kernel.managers)


def test_arc_i_message_bus_records_events_without_mutation():
    bus = RuntimeMessageBus()
    event = bus.publish("test.event", "A", "B", {"ok": True})
    assert event.mutating is False
    assert len(bus.dispatch_log()) == 1
    assert build_sample_event_flow()["mutations_performed"] is False


def test_arc_i_runtime_state_snapshot_preserves_invariants():
    state = build_runtime_state_snapshot("What should DELTA learn?").as_dict()
    assert state["memory"]["memory_mutation_performed"] is False
    assert state["learning"]["integration_write_performed"] is False
    assert state["training_performed"] is False
    assert state["provider_call_performed"] is False


def test_arc_i_transaction_engine_never_mutates():
    tx = CognitiveTransactionEngine().plan_transaction("review", commit_allowed=True)
    assert tx.committed is True
    assert tx.mutation_performed is False


def test_arc_i_audit_graph_is_graph_only():
    graph = build_sample_audit_graph()
    assert graph.graph_only is True
    assert len(graph.nodes) == 6
    assert len(graph.edges) == 5


def test_arc_i_capability_registry_keeps_dangerous_capabilities_inactive():
    registry = CognitiveCapabilityRegistry()
    assert registry.resolve("training").active is False
    assert registry.resolve("provider_call").active is False
    assert registry.resolve("action_execution").active is False
    assert registry.resolve("self_description").active is True


def test_arc_i_dynamic_pipeline_is_non_mutating():
    pipeline = build_dynamic_pipeline("What should DELTA learn and explain routing?")
    assert pipeline.provider_required is False
    assert pipeline.mutation_allowed is False
    assert any(step.capability == "learning_opportunity_detection" for step in pipeline.steps)


def test_arc_i_kernel_checkpoint_preserves_all_safety_flags():
    checkpoint = build_kernel_safety_checkpoint()
    assert checkpoint["model_b_default"] == "unchanged"
    assert checkpoint["hyb1"] == "dormant_env_gated_shadow_only"
    assert checkpoint["training"] == "disabled"
    assert checkpoint["integration_writes"] == "disabled"
    assert all(value is False for value in checkpoint["safety_invariants"].values())


def test_arc_i_local_kernel_answers_cover_smoke_prompts_safely():
    for prompt in (
        "Show runtime state.",
        "Explain kernel routing.",
        "What would happen if this were approved?",
        "Explain your reasoning.",
    ):
        assert is_kernel_question(prompt)
        data = run_kernel_answer(prompt)
        assert data["phase"] == "Runtime ARC I V3.9"
        assert data["safety"]["training_performed"] is False
        assert data["safety"]["provider_call_performed"] is False
        assert data["safety"]["memory_mutation_performed"] is False
