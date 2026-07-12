from __future__ import annotations

from integration.model_runtime import CanonicalInferenceResult, ProviderManager
from integration.model_runtime.model_registry import ModelSpec


def _spec(name: str, family: str):
    return ModelSpec(
        name=name,
        path=f"/models/{name}.gguf",
        tier=1,
        description=name,
        context_length=4096,
        family=family,
        quantization="Q4",
        size_bytes=100,
    )


class FakeRunner:
    closed: list[str] = []
    load_model_calls: list[str] = []

    def __init__(self, model_id: str):
        self.model_id = model_id

    def produce_output(self, input_payload):
        prompt = input_payload["prompt"]
        return CanonicalInferenceResult(
            provider="local_gguf",
            model_id=self.model_id,
            answer=f"{self.model_id}: {prompt}",
            raw_output=f"{self.model_id}: {prompt}",
            confidence=0.8,
            latency_seconds=0.01,
            prompt_tokens=len(prompt.split()),
            response_tokens=3,
        )

    def load_model(self):
        self.load_model_calls.append(self.model_id)

    def close(self):
        self.closed.append(self.model_id)


def test_provider_manager_keeps_only_one_active_provider(tmp_path):
    FakeRunner.closed = []
    manager = ProviderManager(
        available_models={
            "phi4": _spec("phi4", "phi4"),
            "qwen": _spec("qwen", "qwen"),
        },
        runner_factory=lambda spec: FakeRunner(spec.name),
        status_path=tmp_path / "provider_status.json",
    )

    manager.load("phi4")
    state = manager.load("qwen")

    assert state.active_model == "qwen"
    assert state.loaded is True
    assert state.load_count == 2
    assert state.unload_count == 1
    assert FakeRunner.closed == ["phi4"]
    assert "qwen" in (tmp_path / "provider_status.json").read_text()


def test_provider_manager_canonicalizes_inference_result():
    manager = ProviderManager(
        available_models={"phi4": _spec("phi4", "phi4")},
        runner_factory=lambda spec: FakeRunner(spec.name),
    )

    result = manager.infer(
        model_name="phi4",
        prompt="Create a plan",
        task_type="planning",
    )

    assert result.model_id == "phi4"
    assert result.answer == "phi4: Create a plan"
    assert result.prompt_tokens == 3


def test_provider_manager_warms_and_reuses_active_provider(tmp_path):
    FakeRunner.closed = []
    FakeRunner.load_model_calls = []
    manager = ProviderManager(
        available_models={"llama": _spec("llama", "llama")},
        runner_factory=lambda spec: FakeRunner(spec.name),
        keep_loaded=True,
        status_path=tmp_path / "provider_status.json",
    )

    warmed = manager.warm("llama")
    result = manager.infer(model_name="llama", prompt="What is fire?")
    state = manager.status()

    assert warmed.active_model == "llama"
    assert result.model_id == "llama"
    assert state.load_count == 1
    assert state.unload_count == 0
    assert FakeRunner.load_model_calls == ["llama"]
    assert FakeRunner.closed == []


def test_provider_manager_uses_capability_database_gpu_layers(tmp_path):
    manager = ProviderManager(
        available_models={"phi4": _spec("phi4", "phi4")},
        runner_factory=lambda spec: FakeRunner(spec.name),
        provider_capabilities={
            "phi4": {
                "recommended_gpu_layers": 36,
                "average_tokens_per_second": 16.0,
            }
        },
    )

    state = manager.load("phi4")

    assert state.n_gpu_layers == 36
    assert state.metadata["recommended_gpu_layers"] == 36
    assert state.metadata["backend_tokens_per_second"] == 16.0


def test_provider_manager_reports_process_scoped_gpu_layer_override(monkeypatch):
    monkeypatch.setenv("DELTA_N_GPU_LAYERS", "-1")
    manager = ProviderManager(
        available_models={"llama": _spec("llama", "llama")},
        runner_factory=lambda spec: FakeRunner(spec.name),
    )

    state = manager.load("llama")

    assert state.n_gpu_layers == -1
