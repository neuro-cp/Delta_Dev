from __future__ import annotations

import gc
import json
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence

from integration.model_runtime.model_registry import ModelSpec, discover_local_models


STRESS_PROMPTS: tuple[tuple[str, str], ...] = (
    ("simple", "What is 2 + 2?"),
    ("reasoning", "Explain why the sky appears blue in one paragraph."),
    (
        "long_context",
        "Read this operational note and summarize the main constraint: "
        + "Delta must qualify providers before unattended experiments. " * 80,
    ),
    (
        "json_output",
        'Return strict JSON with keys "answer" and "confidence" for the question: what is 2 + 2?',
    ),
    (
        "summarization",
        "Summarize in two sentences why provider qualification should happen before autonomous experiments.",
    ),
)


@dataclass(frozen=True)
class PromptProbeResult:
    prompt_name: str
    prompt: str
    success: bool
    output: str = ""
    output_tokens: int = 0
    output_length: int = 0
    tokens_per_second: float | None = None
    first_token_latency_seconds: float | None = None
    error: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LayerProbeResult:
    n_gpu_layers: int
    requested_context: int
    load_success: bool
    inference_success: bool
    load_time_seconds: float | None = None
    peak_ram_mb: float | None = None
    peak_vram_mb: float | None = None
    vram_baseline_mb: float | None = None
    vram_after_unload_mb: float | None = None
    gpu_memory_returned_to_baseline: bool | None = None
    prompt_results: tuple[PromptProbeResult, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ProviderQualificationRecord:
    model_name: str
    path: str
    family: str
    provider: str
    context_length: int
    quantization: str
    size_bytes: int
    capabilities: tuple[str, ...]
    architecture: str | None
    requires_mmproj: bool
    mmproj_path: str | None
    chat_template_available: bool | None
    qualified: bool
    stable: bool
    recommended_gpu_layers: int | None
    recommended_context: int | None
    load_success: bool
    inference_success: bool
    load_time_seconds: float | None
    peak_ram_mb: float | None
    peak_vram_mb: float | None
    average_tokens_per_second: float | None
    first_token_latency_seconds: float | None
    gpu_memory_returned_to_baseline: bool | None
    prompt_success_count: int = 0
    prompt_total_count: int = 0
    notes: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    layer_probes: tuple[LayerProbeResult, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelProbeExecutor(Protocol):
    def probe(
        self,
        spec: ModelSpec,
        *,
        n_gpu_layers: int,
        requested_context: int,
    ) -> LayerProbeResult:
        ...


class GpuMemorySampler:
    def __init__(self) -> None:
        self.values_mb: list[float] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.values_mb = []
        self._stop.clear()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def peak_mb(self) -> float | None:
        if not self.values_mb:
            return None
        return max(self.values_mb)

    def current_mb(self) -> float | None:
        return query_gpu_memory_mb()

    def _sample_loop(self) -> None:
        while not self._stop.is_set():
            value = query_gpu_memory_mb()
            if value is not None:
                self.values_mb.append(value)
            time.sleep(0.1)


class LlamaCppProbeExecutor:
    """
    Probe one model/layer setting with llama.cpp and always release it.
    """

    def __init__(self, *, max_context: int = 8192, max_tokens: int = 64) -> None:
        self.max_context = int(max_context)
        self.max_tokens = int(max_tokens)

    def probe(
        self,
        spec: ModelSpec,
        *,
        n_gpu_layers: int,
        requested_context: int,
    ) -> LayerProbeResult:
        baseline_vram = query_gpu_memory_mb()
        sampler = GpuMemorySampler()
        sampler.start()
        start = time.perf_counter()
        llm = None
        try:
            from llama_cpp import Llama

            llm = Llama(
                model_path=spec.path,
                n_ctx=min(int(requested_context), self.max_context),
                n_gpu_layers=int(n_gpu_layers),
                n_threads=max(2, _cpu_threads()),
                verbose=False,
            )
            load_time = time.perf_counter() - start
            metadata = dict(getattr(llm, "metadata", {}) or {})
            prompt_results = (
                *(self._run_prompt(llm, name, prompt) for name, prompt in STRESS_PROMPTS),
            )
            inference_success = all(result.success for result in prompt_results)
            return LayerProbeResult(
                n_gpu_layers=int(n_gpu_layers),
                requested_context=min(int(requested_context), self.max_context),
                load_success=True,
                inference_success=inference_success,
                load_time_seconds=round(load_time, 4),
                peak_ram_mb=query_process_ram_mb(),
                peak_vram_mb=sampler.peak_mb(),
                vram_baseline_mb=baseline_vram,
                vram_after_unload_mb=None,
                gpu_memory_returned_to_baseline=None,
                prompt_results=prompt_results,
                metadata=metadata,
                error=None
                if inference_success
                else "; ".join(result.error or "" for result in prompt_results if not result.success),
            )
        except Exception as exc:
            return LayerProbeResult(
                n_gpu_layers=int(n_gpu_layers),
                requested_context=min(int(requested_context), self.max_context),
                load_success=False,
                inference_success=False,
                peak_ram_mb=query_process_ram_mb(),
                peak_vram_mb=sampler.peak_mb(),
                vram_baseline_mb=baseline_vram,
                error=str(exc),
            )
        finally:
            llm = None
            gc.collect()
            time.sleep(0.5)
            sampler.stop()

    def _run_prompt(self, llm: Any, prompt_name: str, prompt: str) -> PromptProbeResult:
        output = ""
        token_count = 0
        start = time.perf_counter()
        first_token_latency: float | None = None
        try:
            stream = llm(
                prompt,
                max_tokens=self.max_tokens,
                temperature=0.0,
                stream=True,
            )
            for chunk in stream:
                token = str(chunk["choices"][0].get("text") or "")
                if not token:
                    continue
                if first_token_latency is None:
                    first_token_latency = time.perf_counter() - start
                output += token
                token_count += 1
            elapsed = max(time.perf_counter() - start, 0.0001)
            return PromptProbeResult(
                prompt_name=prompt_name,
                prompt=prompt,
                success=bool(output.strip()),
                output=output.strip(),
                output_tokens=token_count,
                output_length=len(output.strip()),
                tokens_per_second=round(token_count / elapsed, 4),
                first_token_latency_seconds=round(first_token_latency or elapsed, 4),
                error=None if output.strip() else "empty output",
            )
        except Exception as exc:
            return PromptProbeResult(
                prompt_name=prompt_name,
                prompt=prompt,
                success=False,
                output=output.strip(),
                output_tokens=token_count,
                output_length=len(output.strip()),
                error=str(exc),
            )


class TimeoutProbeExecutor:
    """
    Run each probe in a subprocess so hung loads/generations can be killed.
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 300,
        max_context: int = 8192,
        max_tokens: int = 64,
    ) -> None:
        self.timeout_seconds = int(timeout_seconds)
        self.max_context = int(max_context)
        self.max_tokens = int(max_tokens)

    def probe(
        self,
        spec: ModelSpec,
        *,
        n_gpu_layers: int,
        requested_context: int,
    ) -> LayerProbeResult:
        worker = Path(__file__).resolve().parents[2] / "tools" / "provider_probe_worker.py"
        command = [
            sys.executable,
            str(worker),
            "--spec-json",
            json.dumps(asdict(spec)),
            "--n-gpu-layers",
            str(int(n_gpu_layers)),
            "--requested-context",
            str(int(requested_context)),
            "--max-context",
            str(self.max_context),
            "--max-tokens",
            str(self.max_tokens),
        ]
        try:
            completed = subprocess.run(
                command,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return LayerProbeResult(
                n_gpu_layers=int(n_gpu_layers),
                requested_context=min(int(requested_context), self.max_context),
                load_success=False,
                inference_success=False,
                peak_ram_mb=query_process_ram_mb(),
                peak_vram_mb=query_gpu_memory_mb(),
                error=f"probe timed out after {self.timeout_seconds}s",
            )
        if completed.returncode == 0 and completed.stdout.strip():
            return _layer_probe_from_payload(json.loads(completed.stdout))
        stderr = completed.stderr.strip()
        return LayerProbeResult(
            n_gpu_layers=int(n_gpu_layers),
            requested_context=min(int(requested_context), self.max_context),
            load_success=False,
            inference_success=False,
            error=f"probe process exited with code {completed.returncode}: {stderr}",
        )


class ProviderQualificationSuite:
    def __init__(
        self,
        *,
        executor: ModelProbeExecutor | None = None,
        layer_candidates: Sequence[int] = (32, 28, 24, 22, 16, 8, 0),
        context_candidates: Sequence[int] = (8192, 4096, 2048),
        vram_baseline_tolerance_mb: float = 512.0,
    ) -> None:
        self.executor = executor or LlamaCppProbeExecutor()
        self.layer_candidates = tuple(int(value) for value in layer_candidates)
        self.context_candidates = tuple(int(value) for value in context_candidates)
        self.vram_baseline_tolerance_mb = float(vram_baseline_tolerance_mb)

    def qualify_all(
        self,
        models: Mapping[str, ModelSpec] | None = None,
    ) -> list[ProviderQualificationRecord]:
        discovered = dict(models or discover_local_models())
        records: list[ProviderQualificationRecord] = []
        for spec in sorted(discovered.values(), key=lambda item: item.name):
            records.append(self.qualify(spec))
        return records

    def qualify(self, spec: ModelSpec) -> ProviderQualificationRecord:
        notes: list[str] = []
        errors: list[str] = []
        layer_probes: list[LayerProbeResult] = []
        for layers in self.layer_candidates:
            for requested_context in self._context_candidates_for(spec):
                try:
                    probe = self.executor.probe(
                        spec,
                        n_gpu_layers=layers,
                        requested_context=requested_context,
                    )
                    probe = self._with_unload_memory_status(probe)
                except Exception as exc:
                    probe = LayerProbeResult(
                        n_gpu_layers=layers,
                        requested_context=requested_context,
                        load_success=False,
                        inference_success=False,
                        error=str(exc),
                    )
                layer_probes.append(probe)
                if probe.error:
                    errors.append(
                        f"layers={layers} context={requested_context}: {probe.error}"
                    )
                if probe.load_success and probe.inference_success:
                    break
            if layer_probes[-1].load_success and layer_probes[-1].inference_success:
                break

        best = next(
            (probe for probe in layer_probes if probe.load_success and probe.inference_success),
            None,
        )
        if best is None:
            notes.append("No probed GPU-layer setting completed both load and inference.")
        if _looks_like_vision_model(spec) and spec.mmproj_path is None:
            notes.append("Model name suggests vision support but no mmproj was discovered.")
        metadata = best.metadata if best is not None else {}
        architecture = _architecture(spec, metadata)
        chat_template = _chat_template_available(metadata)
        prompt_results = list(best.prompt_results if best is not None else ())
        token_rates = [
            result.tokens_per_second
            for result in prompt_results
            if result.tokens_per_second is not None
        ]
        first_token = [
            result.first_token_latency_seconds
            for result in prompt_results
            if result.first_token_latency_seconds is not None
        ]
        prompt_success_count = len(
            [
                result
                for result in prompt_results
                if result.success
            ]
        )
        prompt_total_count = len(prompt_results)
        stable = (
            best is not None
            and prompt_total_count == len(STRESS_PROMPTS)
            and prompt_success_count == prompt_total_count
            and best.gpu_memory_returned_to_baseline is not False
        )
        qualified = best is not None and stable and not (
            _looks_like_vision_model(spec) and spec.mmproj_path is None
        )
        return ProviderQualificationRecord(
            model_name=spec.name,
            path=spec.path,
            family=spec.family,
            provider=spec.provider,
            context_length=spec.context_length,
            quantization=spec.quantization,
            size_bytes=spec.size_bytes,
            capabilities=spec.capabilities,
            architecture=architecture,
            requires_mmproj=_looks_like_vision_model(spec),
            mmproj_path=spec.mmproj_path,
            chat_template_available=chat_template,
            qualified=qualified,
            stable=stable,
            recommended_gpu_layers=best.n_gpu_layers if best is not None else None,
            recommended_context=best.requested_context if best is not None else None,
            load_success=best.load_success if best is not None else False,
            inference_success=best.inference_success if best is not None else False,
            load_time_seconds=best.load_time_seconds if best is not None else None,
            peak_ram_mb=best.peak_ram_mb if best is not None else None,
            peak_vram_mb=best.peak_vram_mb if best is not None else None,
            average_tokens_per_second=_average(token_rates),
            first_token_latency_seconds=min(first_token) if first_token else None,
            gpu_memory_returned_to_baseline=best.gpu_memory_returned_to_baseline
            if best is not None
            else None,
            prompt_success_count=prompt_success_count,
            prompt_total_count=prompt_total_count,
            notes=tuple(notes),
            errors=tuple(errors),
            layer_probes=tuple(layer_probes),
            metadata={
                "qualification_method": "provider_qualification_v2",
                "layer_candidates": list(self.layer_candidates),
                "context_candidates": list(self._context_candidates_for(spec)),
                "stress_prompts": [name for name, _ in STRESS_PROMPTS],
            },
        )

    def _with_unload_memory_status(self, probe: LayerProbeResult) -> LayerProbeResult:
        final_vram = query_gpu_memory_mb()
        baseline = probe.vram_baseline_mb
        returned = None
        if baseline is not None and final_vram is not None:
            returned = final_vram <= baseline + self.vram_baseline_tolerance_mb
        return LayerProbeResult(
            **{
                **asdict(probe),
                "vram_after_unload_mb": final_vram,
                "gpu_memory_returned_to_baseline": returned,
                "prompt_results": tuple(probe.prompt_results),
            }
        )

    def _context_candidates_for(self, spec: ModelSpec) -> tuple[int, ...]:
        candidates = [value for value in self.context_candidates if value <= spec.context_length]
        if spec.context_length not in candidates:
            candidates.insert(0, spec.context_length)
        normalized: list[int] = []
        for value in sorted(candidates, reverse=True):
            if value > 0 and value not in normalized:
                normalized.append(value)
        return tuple(normalized)


class ProviderQualificationReportWriter:
    def __init__(
        self,
        *,
        json_path: str | Path,
        markdown_path: str | Path,
        capability_db_path: str | Path,
        health_path: str | Path | None = None,
    ) -> None:
        self.json_path = Path(json_path)
        self.markdown_path = Path(markdown_path)
        self.capability_db_path = Path(capability_db_path)
        self.health_path = Path(health_path) if health_path is not None else self.markdown_path.with_name(
            "provider_health.md"
        )

    def write(self, records: Sequence[ProviderQualificationRecord]) -> None:
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.capability_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.health_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.write_text(
            json.dumps(_jsonable(records), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.markdown_path.write_text(_markdown(records), encoding="utf-8")
        self.capability_db_path.write_text(
            json.dumps(capability_database(records), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.health_path.write_text(_health_markdown(records), encoding="utf-8")


def capability_database(records: Sequence[ProviderQualificationRecord]) -> dict[str, Any]:
    return {
        record.model_name: {
            "qualified": record.qualified,
            "provider": record.provider,
            "family": record.family,
            "vision": "vision" in record.capabilities,
            "coding": record.family in {"phi4", "qwen", "mistral", "llama"}
            and record.qualified,
            "planning": record.family in {"phi4", "qwen", "mistral", "llama"}
            and record.qualified,
            "reasoning": record.qualified,
            "recommended_gpu_layers": record.recommended_gpu_layers,
            "recommended_context": record.recommended_context,
            "max_context": record.recommended_context or record.context_length,
            "average_tokens_per_second": record.average_tokens_per_second,
            "first_token_latency_seconds": record.first_token_latency_seconds,
            "peak_vram_mb": record.peak_vram_mb,
            "chat_template_available": record.chat_template_available,
            "requires_mmproj": record.requires_mmproj,
            "mmproj_path": record.mmproj_path,
            "stable": record.stable,
            "memory_leak_suspected": record.gpu_memory_returned_to_baseline is False,
            "failure_count": len(record.errors),
            "notes": list(record.notes),
        }
        for record in records
    }


def load_capability_database(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.exists():
        return {}
    return json.loads(candidate.read_text(encoding="utf-8"))


def _layer_probe_from_payload(payload: dict[str, Any]) -> LayerProbeResult:
    prompts = tuple(
        PromptProbeResult(**item)
        for item in payload.get("prompt_results", [])
    )
    return LayerProbeResult(
        **{
            **payload,
            "prompt_results": prompts,
        }
    )


def qualified_model_names(path: str | Path) -> set[str]:
    database = load_capability_database(path)
    return {
        name
        for name, profile in database.items()
        if isinstance(profile, dict) and profile.get("qualified") is True
    }


def query_gpu_memory_mb() -> float | None:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=1.0,
        ).strip()
    except Exception:
        return None
    if not output:
        return None
    try:
        return float(output.splitlines()[0].strip())
    except ValueError:
        return None


def query_process_ram_mb() -> float | None:
    try:
        import psutil

        return round(psutil.Process().memory_info().rss / (1024 * 1024), 4)
    except Exception:
        pass
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        kernel = ctypes.WinDLL("Kernel32.dll")
        psapi = ctypes.WinDLL("Psapi.dll")
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        handle = kernel.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb,
        )
        if not ok:
            return None
        return round(counters.WorkingSetSize / (1024 * 1024), 4)
    except Exception:
        return None


def _markdown(records: Sequence[ProviderQualificationRecord]) -> str:
    lines = [
        "# Provider Qualification Report",
        "",
        "| Model | Loads | Inference | VRAM | tok/s | Recommended GPU Layers | Notes |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for record in records:
        notes = "; ".join(record.notes or record.errors or ("Qualified",))
        lines.append(
            "| "
            + " | ".join(
                [
                    record.model_name,
                    "yes" if record.load_success else "no",
                    "yes" if record.inference_success else "no",
                    _fmt(record.peak_vram_mb),
                    _fmt(record.average_tokens_per_second),
                    str(record.recommended_gpu_layers)
                    if record.recommended_gpu_layers is not None
                    else "",
                    notes.replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("Failures are recorded per model; one failure does not abort the suite.")
    return "\n".join(lines) + "\n"


def _health_markdown(records: Sequence[ProviderQualificationRecord]) -> str:
    lines = [
        "# Provider Health",
        "",
        "| Model | Qualified | Stable | Memory Leak | GPU Layers | Context | tok/s | Failures | Last Successful Run |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for record in records:
        last_success = ""
        for probe in reversed(record.layer_probes):
            if probe.load_success and probe.inference_success:
                last_success = f"layers={probe.n_gpu_layers}, context={probe.requested_context}"
                break
        lines.append(
            "| "
            + " | ".join(
                [
                    record.model_name,
                    "yes" if record.qualified else "no",
                    "yes" if record.stable else "no",
                    "yes" if record.gpu_memory_returned_to_baseline is False else "no",
                    str(record.recommended_gpu_layers or ""),
                    str(record.recommended_context or ""),
                    _fmt(record.average_tokens_per_second),
                    str(len(record.errors)),
                    last_success,
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("This file is Delta's provider maintenance log for the current hardware profile.")
    return "\n".join(lines) + "\n"


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _architecture(spec: ModelSpec, metadata: Mapping[str, Any]) -> str | None:
    for key in ("general.architecture", "llama.architecture", "architecture"):
        value = metadata.get(key)
        if value:
            return str(value)
    return spec.family if spec.family != "unknown" else None


def _chat_template_available(metadata: Mapping[str, Any]) -> bool | None:
    if not metadata:
        return None
    return any("chat_template" in str(key).lower() for key in metadata)


def _looks_like_vision_model(spec: ModelSpec) -> bool:
    text = f"{spec.name} {spec.path}".lower()
    return "vision" in spec.capabilities or "vl" in text or "vision" in text


def _average(values: Iterable[float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 4)


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return str(round(float(value), 2))


def _cpu_threads() -> int:
    try:
        import os

        return max(2, (os.cpu_count() or 4) // 2)
    except Exception:
        return 4
