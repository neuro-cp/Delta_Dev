from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_console_module():
    module_path = Path(__file__).resolve().parents[3] / "tools" / "delta_console.py"
    spec = importlib.util.spec_from_file_location("delta_console_for_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_console_state_exposes_models_and_inference_observatory(tmp_path, monkeypatch):
    model_dir = tmp_path / "models" / "Phi-4-mini"
    model_dir.mkdir(parents=True)
    (model_dir / "Phi-4-mini-Q4_K_M.gguf").write_bytes(b"fake-model")
    monkeypatch.setenv("DELTA_MODEL_ROOT", str(tmp_path / "models"))

    console = _load_console_module()

    state = console._state()

    assert "models" in state
    assert "model_observatory" in state
    assert "model_inference_events" in state
    assert "provider_effectiveness" in state
    assert "active_provider" in state
    assert "gpu" in state
    assert "experiment_queue" in state
    assert "experiment_utility" in state
    assert "knowledge_quality" in state
    assert "generated_experiences" in state
    assert "world_model" in state
    assert state["model_observatory"]["total"] >= 0
    assert any(model["family"] == "phi4" for model in state["models"].values())
