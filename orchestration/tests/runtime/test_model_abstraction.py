from __future__ import annotations

from integration.model_runtime.inference_types import CanonicalInferenceResult
from integration.model_runtime.model_registry import discover_local_models, get_model_spec


def test_local_model_discovery_from_model_root(tmp_path, monkeypatch):
    model_dir = tmp_path / "lmstudio-community" / "Phi-4-mini-reasoning-GGUF"
    model_dir.mkdir(parents=True)
    model_path = model_dir / "Phi-4-mini-reasoning-Q4_K_M.gguf"
    model_path.write_bytes(b"model")
    monkeypatch.setenv("DELTA_MODEL_ROOT", str(tmp_path))

    discovered = discover_local_models()
    spec = get_model_spec("phi4")

    assert discovered
    assert spec.family == "phi4"
    assert spec.quantization == "Q4_K_M"
    assert spec.provider == "local_gguf"
    assert spec.capabilities == ("text",)
    assert spec.path == str(model_path)


def test_model_discovery_marks_multimodal_projector(tmp_path, monkeypatch):
    model_dir = tmp_path / "lmstudio-community" / "Qwen2.5-VL-7B-Instruct-GGUF"
    model_dir.mkdir(parents=True)
    model_path = model_dir / "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
    projector_path = model_dir / "mmproj-model-f16.gguf"
    model_path.write_bytes(b"model")
    projector_path.write_bytes(b"projector")
    monkeypatch.setenv("DELTA_MODEL_ROOT", str(tmp_path))

    spec = next(iter(discover_local_models().values()))

    assert "vision" in spec.capabilities
    assert spec.mmproj_path == str(projector_path)


def test_canonical_inference_result_exports_ai_payload():
    result = CanonicalInferenceResult(
        provider="mock",
        model_id="mock-1",
        answer="answer",
        raw_output='{"answer": "answer", "confidence": 0.8}',
        confidence=0.8,
        latency_seconds=0.01,
        prompt_tokens=2,
        response_tokens=4,
        evidence=["e1"],
    )

    payload = result.to_ai_output_payload()

    assert payload["answer"] == "answer"
    assert payload["confidence"] == 0.8
    assert payload["canonical_inference"]["model_id"] == "mock-1"
    assert payload["canonical_inference"]["evidence"] == ["e1"]
