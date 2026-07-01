from __future__ import annotations

from integration.model_runtime import (
    CanonicalInferenceResult,
    ModelObservatory,
    ModelRoutingPolicy,
)
from integration.model_runtime.model_registry import ModelSpec


def _spec(name: str, family: str, tier: int, context: int = 4096):
    return ModelSpec(
        name=name,
        path=f"/models/{name}.gguf",
        tier=tier,
        description=name,
        context_length=context,
        family=family,
        quantization="Q4",
        size_bytes=100,
    )


def test_routing_policy_prefers_deterministic_for_math():
    decision = ModelRoutingPolicy().decide(
        task_type="math",
        prompt="What is 2 + 2?",
        available_models={"phi3": _spec("phi3", "phi3", 1)},
    )

    assert decision.route == "deterministic"
    assert decision.model_name is None
    assert decision.cloud_allowed is False


def test_routing_policy_prefers_local_before_cloud():
    decision = ModelRoutingPolicy().decide(
        task_type="comparison",
        prompt="Compare memory and attention",
        available_models={
            "phi3": _spec("phi3", "phi3", 1),
            "phi4": _spec("phi4", "phi4", 2, context=8192),
        },
        allow_cloud=True,
    )

    assert decision.route == "local"
    assert decision.model_name == "phi4"
    assert decision.cloud_allowed is False


def test_routing_policy_requires_explicit_cloud_permission():
    decision = ModelRoutingPolicy().decide(
        task_type="open_ended",
        prompt="Explain the system",
        available_models={},
        allow_cloud=False,
    )

    assert decision.route == "human_review"
    assert decision.model_name is None


def test_model_observatory_records_and_summarizes_inference(tmp_path):
    observatory = ModelObservatory(tmp_path / "inference.jsonl")
    result = CanonicalInferenceResult(
        provider="local_gguf",
        model_id="phi3",
        answer="answer",
        raw_output="answer",
        confidence=0.7,
        latency_seconds=1.25,
        prompt_tokens=5,
        response_tokens=2,
        evidence=["e1"],
    )

    record = observatory.record(
        result=result,
        route="local",
        task_type="open_ended",
    )
    metrics = observatory.metrics()

    assert record.model_id == "phi3"
    assert record.evidence_count == 1
    assert metrics["total"] == 1
    assert metrics["by_model"] == {"phi3": 1}
    assert metrics["average_latency_seconds"] == 1.25
    assert metrics["average_confidence"] == 0.7
