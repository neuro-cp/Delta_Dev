from __future__ import annotations

from integration.model_runtime.inference_types import CanonicalInferenceResult
from orchestration.runtime import rc2_level2_runtime_integration as level2


class FakeProviderManager:
    def __init__(self):
        self.active_model = None
        self.load_count = 0
        self.unload_count = 0

    def load(self, model_name):
        if self.active_model != model_name:
            self.active_model = model_name
            self.load_count += 1
        return self.status()

    def infer(self, *, model_name, prompt, task_type="open_ended", metadata=None):
        self.load(model_name)
        return CanonicalInferenceResult(
            provider="fake_local",
            model_id=model_name,
            answer=f"Fake answer from {model_name}: {prompt[:60]}",
            raw_output=f"Fake answer from {model_name}: {prompt[:60]}",
            confidence=0.82,
            latency_seconds=0.01,
            prompt_tokens=len(prompt.split()),
            response_tokens=8,
            evidence=[],
            metadata={"task_type": task_type, **dict(metadata or {})},
        )

    def status(self):
        class State:
            active_model = self.active_model
            loaded = self.active_model is not None
            load_count = self.load_count
            unload_count = self.unload_count
            n_gpu_layers = None
            metadata = {"resident_provider_count": 1 if self.active_model else 0}

        return State()


def test_level2_runtime_report_uses_fake_warm_provider(monkeypatch):
    monkeypatch.setattr(level2, "ProviderManager", FakeProviderManager)
    report = level2.run_level2_runtime_integration(execute_models=True)
    assert report["cycles_completed"] >= 40
    assert report["actual_local_model_calls"] >= 20
    assert report["scores"]["safety_score"] == 1.0
    assert report["scores"]["planning_model_calls"] >= 5
    assert report["warmed_model"]["loaded"] is True
    assert report["planning_model"]["loaded"] is True
    assert report["recommendation"] in {"READY_FOR_LEVEL2_RC2_MANUAL_OPERATOR_REVIEW", "LEVEL2_REPAIR_REQUIRED"}


def test_level2_runtime_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(level2, "ProviderManager", FakeProviderManager)
    monkeypatch.setattr(level2, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(level2, "DOCS", tmp_path / "docs")
    report = level2.write_level2_runtime_reports(execute_models=True)
    assert (tmp_path / "reports" / "RC2_LEVEL2_RUNTIME_INTEGRATION.json").exists()
    assert (tmp_path / "reports" / "RC2_MODEL_RESIDENCY_AND_LATENCY.json").exists()
    assert (tmp_path / "reports" / "RC2_LEVEL2_FAILURES.json").exists()
    assert (tmp_path / "docs" / "continuation_rc2_level2_runtime.md").exists()
    assert report["safety"]["training_performed"] is False
