from __future__ import annotations

import json

from integration.model_runtime.model_registry import ModelSpec
from integration.model_runtime.provider_qualification import (
    LayerProbeResult,
    PromptProbeResult,
    ProviderQualificationReportWriter,
    ProviderQualificationSuite,
    capability_database,
)


def _spec(name: str, family: str = "phi4"):
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


class FakeProbeExecutor:
    def __init__(self):
        self.calls: list[tuple[str, int, int]] = []

    def probe(self, spec, *, n_gpu_layers, requested_context):
        self.calls.append((spec.name, n_gpu_layers, requested_context))
        if spec.name == "bad":
            return LayerProbeResult(
                n_gpu_layers=n_gpu_layers,
                requested_context=requested_context,
                load_success=False,
                inference_success=False,
                error="unsupported metadata",
            )
        if n_gpu_layers > 24:
            return LayerProbeResult(
                n_gpu_layers=n_gpu_layers,
                requested_context=requested_context,
                load_success=False,
                inference_success=False,
                error="out of memory",
            )
        return LayerProbeResult(
            n_gpu_layers=n_gpu_layers,
            requested_context=requested_context,
            load_success=True,
            inference_success=True,
            load_time_seconds=1.2,
            peak_ram_mb=2048,
            peak_vram_mb=8400,
            vram_baseline_mb=200,
            vram_after_unload_mb=250,
            gpu_memory_returned_to_baseline=True,
            prompt_results=(
                PromptProbeResult(
                    prompt_name="simple",
                    prompt="What is 2 + 2?",
                    success=True,
                    output="4",
                    output_tokens=1,
                    tokens_per_second=40.0,
                    first_token_latency_seconds=0.2,
                ),
                PromptProbeResult(
                    prompt_name="reasoning",
                    prompt="Explain why the sky appears blue in one paragraph.",
                    success=True,
                    output="Rayleigh scattering.",
                    output_tokens=2,
                    tokens_per_second=42.0,
                    first_token_latency_seconds=0.3,
                ),
                PromptProbeResult(
                    prompt_name="long_context",
                    prompt="Long context",
                    success=True,
                    output="Summary.",
                    output_tokens=1,
                    tokens_per_second=41.0,
                    first_token_latency_seconds=0.25,
                ),
                PromptProbeResult(
                    prompt_name="json_output",
                    prompt="JSON",
                    success=True,
                    output='{"answer":"4","confidence":1.0}',
                    output_tokens=1,
                    tokens_per_second=41.0,
                    first_token_latency_seconds=0.25,
                ),
                PromptProbeResult(
                    prompt_name="summarization",
                    prompt="Summarize",
                    success=True,
                    output="Qualification first.",
                    output_tokens=1,
                    tokens_per_second=41.0,
                    first_token_latency_seconds=0.25,
                ),
            ),
            metadata={"general.architecture": spec.family, "tokenizer.chat_template": "x"},
        )


def test_qualification_suite_continues_after_model_failure():
    executor = FakeProbeExecutor()
    suite = ProviderQualificationSuite(
        executor=executor,
        layer_candidates=(32, 24),
    )

    records = suite.qualify_all({"good": _spec("good"), "bad": _spec("bad")})

    by_name = {record.model_name: record for record in records}
    assert by_name["good"].qualified is True
    assert by_name["good"].recommended_gpu_layers == 24
    assert by_name["good"].recommended_context == 4096
    assert by_name["good"].average_tokens_per_second == 41.0
    assert by_name["good"].stable is True
    assert by_name["bad"].qualified is False
    assert "unsupported metadata" in "; ".join(by_name["bad"].errors)


def test_qualification_writer_creates_reports_and_capability_database(tmp_path):
    suite = ProviderQualificationSuite(
        executor=FakeProbeExecutor(),
        layer_candidates=(24,),
    )
    records = suite.qualify_all({"good": _spec("good")})
    writer = ProviderQualificationReportWriter(
        json_path=tmp_path / "provider_qualification.json",
        markdown_path=tmp_path / "provider_qualification.md",
        health_path=tmp_path / "provider_health.md",
        capability_db_path=tmp_path / "provider_capabilities.json",
    )

    writer.write(records)

    database = json.loads((tmp_path / "provider_capabilities.json").read_text())
    assert (tmp_path / "provider_qualification.json").exists()
    assert "Provider Qualification Report" in (
        tmp_path / "provider_qualification.md"
    ).read_text()
    assert "Provider Health" in (tmp_path / "provider_health.md").read_text()
    assert database["good"]["qualified"] is True
    assert database["good"]["recommended_context"] == 4096
    assert capability_database(records)["good"]["planning"] is True
