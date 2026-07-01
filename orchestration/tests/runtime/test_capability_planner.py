from __future__ import annotations

from integration.model_runtime import CapabilityPlanner, ModelRoutingPolicy, ModelSpec


def _spec(
    name: str,
    *,
    family: str,
    tier: int,
    capabilities: tuple[str, ...] = ("text",),
) -> ModelSpec:
    return ModelSpec(
        name=name,
        path=f"{name}.gguf",
        tier=tier,
        description=name,
        context_length=8192,
        provider="local_gguf",
        family=family,
        quantization="Q4",
        size_bytes=100,
        capabilities=capabilities,
    )


def test_capability_planner_derives_required_capabilities_before_provider_allocation():
    plan = CapabilityPlanner().plan(
        intent="Plan and debug a software change",
        task_type="planning",
    )

    assert plan.required_capabilities[:2] == ("planning", "reasoning")
    assert "coding" in plan.required_capabilities
    assert "diagnostic" in plan.required_capabilities
    assert plan.metadata["capability_selection_precedes_provider_allocation"] is True


def test_routing_policy_uses_capability_plan_for_local_provider_choice():
    available = {
        "phi3": _spec("phi3", family="phi3", tier=1),
        "phi4": _spec("phi4", family="phi4", tier=2),
    }
    plan = CapabilityPlanner().plan(
        intent="Debug code",
        task_type="open_ended",
    )

    decision = ModelRoutingPolicy().decide(
        task_type="open_ended",
        prompt=plan.intent,
        available_models=available,
        capability_plan=plan,
    )

    assert decision.route == "local"
    assert decision.model_name == "phi4"
    assert "coding" in decision.metadata["required_capabilities"]


def test_routing_policy_prefers_vision_capable_provider_for_vision_capability():
    available = {
        "text": _spec("text", family="phi4", tier=1),
        "vision": _spec("vision", family="qwen", tier=2, capabilities=("text", "vision")),
    }
    plan = CapabilityPlanner().plan(
        intent="Analyze this image",
        task_type="vision",
    )

    decision = ModelRoutingPolicy().decide(
        task_type="vision",
        prompt=plan.intent,
        available_models=available,
        capability_plan=plan,
    )

    assert decision.route == "local"
    assert decision.model_name == "vision"
    assert "vision" in decision.metadata["required_capabilities"]
