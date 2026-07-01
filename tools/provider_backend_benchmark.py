from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.model_runtime.model_registry import get_model_spec
from integration.model_runtime.provider_qualification import (
    load_capability_database,
    query_gpu_memory_mb,
    query_process_ram_mb,
)


PROMPT = "The capital of France is"


@dataclass(frozen=True)
class BackendBenchmarkRecord:
    model_name: str
    family: str
    qualified: bool
    n_gpu_layers: int | None
    context: int | None
    load_success: bool
    inference_success: bool
    quantization: str | None = None
    prompt_tokens: int = 0
    load_time_seconds: float | None = None
    unload_time_seconds: float | None = None
    first_token_latency_seconds: float | None = None
    tokens_per_second: float | None = None
    output_tokens: int = 0
    output_length: int = 0
    vram_baseline_mb: float | None = None
    peak_vram_mb: float | None = None
    vram_delta_mb: float | None = None
    ram_baseline_mb: float | None = None
    ram_mb: float | None = None
    ram_peak_mb: float | None = None
    cpu_utilization_percent: float | None = None
    gpu_utilization_percent: int | None = None
    backend_status: str = "unknown"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate llama.cpp backend/offload behavior.")
    parser.add_argument(
        "--capability-db-path",
        default=str(ROOT / "data" / "model_runtime" / "provider_capabilities.json"),
    )
    parser.add_argument("--json-path", default=str(ROOT / "reports" / "provider_backend_benchmark.json"))
    parser.add_argument("--markdown-path", default=str(ROOT / "reports" / "provider_backend_benchmark.md"))
    parser.add_argument("--max-tokens", type=int, default=100)
    parser.add_argument("--layers", default="")
    args = parser.parse_args()

    database = load_capability_database(args.capability_db_path)
    records: list[BackendBenchmarkRecord] = []
    for model_name, profile in database.items():
        if not isinstance(profile, dict) or profile.get("qualified") is not True:
            continue
        print(f"benchmarking={model_name}", flush=True)
        for layers in _layers(args.layers, profile):
            records.append(
                _benchmark(
                    model_name,
                    profile,
                    max_tokens=args.max_tokens,
                    n_gpu_layers=layers,
                )
            )
            _write(records, Path(args.json_path), Path(args.markdown_path))

    _write(records, Path(args.json_path), Path(args.markdown_path))
    print(f"wrote={args.json_path}", flush=True)
    print(f"wrote={args.markdown_path}", flush=True)
    return 0


def _benchmark(
    model_name: str,
    profile: dict[str, Any],
    *,
    max_tokens: int,
    n_gpu_layers: int | None,
) -> BackendBenchmarkRecord:
    baseline = query_gpu_memory_mb()
    peak = baseline
    ram_baseline = query_process_ram_mb()
    ram_peak = ram_baseline
    cpu_samples: list[float] = []
    gpu_util_samples: list[int] = []
    stop = threading.Event()
    output = ""
    token_count = 0
    first_token_latency = None
    load_time = None
    unload_time = None
    llm = None
    start = time.perf_counter()
    try:
        from llama_cpp import Llama

        spec = get_model_spec(model_name)
        context = profile.get("recommended_context") or profile.get("max_context") or spec.context_length
        sampler = threading.Thread(
            target=_sample_resources,
            args=(stop, cpu_samples, gpu_util_samples),
            daemon=True,
        )
        sampler.start()
        llm = Llama(
            model_path=spec.path,
            n_ctx=min(int(context), 8192),
            n_gpu_layers=int(n_gpu_layers or 0),
            n_threads=8,
            verbose=False,
        )
        load_time = time.perf_counter() - start
        peak = _max(peak, query_gpu_memory_mb())
        ram_peak = _max(ram_peak, query_process_ram_mb())
        generation_start = time.perf_counter()
        stream = llm(PROMPT, max_tokens=max_tokens, temperature=0.0, stream=True)
        for chunk in stream:
            token = str(chunk["choices"][0].get("text") or "")
            if not token:
                continue
            if first_token_latency is None:
                first_token_latency = time.perf_counter() - generation_start
            output += token
            token_count += 1
            peak = _max(peak, query_gpu_memory_mb())
            ram_peak = _max(ram_peak, query_process_ram_mb())
        elapsed = max(time.perf_counter() - generation_start, 0.0001)
        unload_start = time.perf_counter()
        llm = None
        gc.collect()
        unload_time = time.perf_counter() - unload_start
        delta = None
        if baseline is not None and peak is not None:
            delta = round(max(0.0, peak - baseline), 4)
        status = _backend_status(delta_mb=delta, n_gpu_layers=int(n_gpu_layers or 0))
        stop.set()
        sampler.join(timeout=2)
        return BackendBenchmarkRecord(
            model_name=model_name,
            family=spec.family,
            qualified=True,
            n_gpu_layers=int(n_gpu_layers or 0),
            context=min(int(context), 8192),
            quantization=spec.quantization,
            prompt_tokens=len(PROMPT.split()),
            load_success=True,
            inference_success=bool(output.strip()),
            load_time_seconds=round(load_time, 4),
            unload_time_seconds=round(unload_time, 4),
            first_token_latency_seconds=round(first_token_latency or elapsed, 4),
            tokens_per_second=round(token_count / elapsed, 4),
            output_tokens=token_count,
            output_length=len(output.strip()),
            vram_baseline_mb=baseline,
            peak_vram_mb=peak,
            vram_delta_mb=delta,
            ram_baseline_mb=ram_baseline,
            ram_mb=query_process_ram_mb(),
            ram_peak_mb=ram_peak,
            gpu_utilization_percent=max(gpu_util_samples) if gpu_util_samples else _gpu_utilization_percent(),
            cpu_utilization_percent=_average(cpu_samples),
            backend_status=status,
            metadata={"prompt": PROMPT, "max_tokens": max_tokens},
        )
    except Exception as exc:
        spec = get_model_spec(model_name)
        return BackendBenchmarkRecord(
            model_name=model_name,
            family=spec.family,
            qualified=True,
            n_gpu_layers=n_gpu_layers,
            context=profile.get("recommended_context"),
            quantization=spec.quantization,
            prompt_tokens=len(PROMPT.split()),
            load_success=load_time is not None,
            inference_success=False,
            load_time_seconds=round(load_time, 4) if load_time is not None else None,
            unload_time_seconds=round(unload_time, 4) if unload_time is not None else None,
            vram_baseline_mb=baseline,
            peak_vram_mb=peak,
            vram_delta_mb=round(max(0.0, (peak or 0) - (baseline or 0)), 4)
            if peak is not None and baseline is not None
            else None,
            ram_baseline_mb=ram_baseline,
            ram_mb=query_process_ram_mb(),
            ram_peak_mb=ram_peak,
            gpu_utilization_percent=_gpu_utilization_percent(),
            backend_status="failed",
            error=str(exc),
        )
    finally:
        stop.set()
        llm = None
        gc.collect()
        time.sleep(0.5)


def _backend_status(*, delta_mb: float | None, n_gpu_layers: int) -> str:
    if n_gpu_layers <= 0:
        return "cpu_configured"
    if delta_mb is None:
        return "unknown"
    if delta_mb < 1024:
        return "cpu_fallback_suspected"
    return "gpu_offload_observed"


def _gpu_utilization_percent() -> int | None:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=1.0,
        ).strip()
        return int(float(output.splitlines()[0]))
    except Exception:
        return None


def _sample_resources(
    stop: threading.Event,
    cpu_samples: list[float],
    gpu_util_samples: list[int],
) -> None:
    last_wall = time.perf_counter()
    last_cpu = _process_cpu_seconds()
    cpu_count = max(1, os.cpu_count() or 1)
    while not stop.is_set():
        current_wall = time.perf_counter()
        current_cpu = _process_cpu_seconds()
        if current_cpu is not None and last_cpu is not None:
            wall_delta = max(current_wall - last_wall, 0.0001)
            cpu_delta = max(current_cpu - last_cpu, 0.0)
            cpu_samples.append(round((cpu_delta / (wall_delta * cpu_count)) * 100.0, 4))
        last_wall = current_wall
        last_cpu = current_cpu
        util = _gpu_utilization_percent()
        if util is not None:
            gpu_util_samples.append(util)
        time.sleep(0.25)


def _process_cpu_seconds() -> float | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class FILETIME(ctypes.Structure):
            _fields_ = [
                ("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD),
            ]

        def ticks(value: FILETIME) -> int:
            return (int(value.dwHighDateTime) << 32) + int(value.dwLowDateTime)

        creation = FILETIME()
        exit_time = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        handle = ctypes.WinDLL("Kernel32.dll").GetCurrentProcess()
        ok = ctypes.WinDLL("Kernel32.dll").GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        )
        if not ok:
            return None
        return (ticks(kernel) + ticks(user)) / 10_000_000.0
    except Exception:
        return None


def _write(records: list[BackendBenchmarkRecord], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(_jsonable(records), indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(_markdown(records), encoding="utf-8")


def _markdown(records: list[BackendBenchmarkRecord]) -> str:
    lines = [
        "# Provider Backend Benchmark",
        "",
        "| Model | Quant | Ctx | Layers | Status | Prompt Tok | Gen Tok | First Token | tok/s | RAM Base | RAM Peak | VRAM Base | VRAM Peak | GPU Util | CPU Util | Load | Unload | Notes |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.model_name,
                    str(record.quantization or ""),
                    str(record.context or ""),
                    str(record.n_gpu_layers or ""),
                    record.backend_status,
                    str(record.prompt_tokens),
                    str(record.output_tokens),
                    _fmt(record.first_token_latency_seconds),
                    _fmt(record.tokens_per_second),
                    _fmt(record.ram_baseline_mb),
                    _fmt(record.ram_peak_mb),
                    _fmt(record.vram_baseline_mb),
                    _fmt(record.peak_vram_mb),
                    _fmt(record.gpu_utilization_percent),
                    _fmt(record.cpu_utilization_percent),
                    _fmt(record.load_time_seconds),
                    _fmt(record.unload_time_seconds),
                    (record.error or "").replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("Backend status is inferred from VRAM delta during a 100-token generation.")
    return "\n".join(lines) + "\n"


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _fmt(value: float | int | None) -> str:
    if value is None:
        return ""
    return str(round(float(value), 4))


def _max(left: float | None, right: float | None) -> float | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _average(values: list[float] | list[int]) -> float | None:
    if not values:
        return None
    return round(sum(float(value) for value in values) / len(values), 4)


def _layers(raw: str, profile: dict[str, Any]) -> list[int]:
    if raw.strip():
        return [int(item.strip()) for item in raw.split(",") if item.strip()]
    value = profile.get("recommended_gpu_layers")
    return [int(value or 0)]


if __name__ == "__main__":
    raise SystemExit(main())
