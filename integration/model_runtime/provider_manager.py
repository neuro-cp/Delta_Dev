from __future__ import annotations

import gc
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from integration.model_runtime.inference_types import CanonicalInferenceResult
from integration.model_runtime.model_registry import ModelSpec, list_available_models
from integration.model_runtime.provider_qualification import load_capability_database


class ProviderRunner(Protocol):
    def produce_output(self, input_payload: dict[str, Any]) -> Any:
        ...


RunnerFactory = Callable[[ModelSpec], ProviderRunner]


def json_dumps_state(state: "ProviderLoadState") -> str:
    return json.dumps(asdict(state), indent=2, sort_keys=True)


@dataclass(frozen=True)
class ProviderLoadState:
    active_model: str | None
    loaded: bool
    loaded_at: float | None = None
    load_count: int = 0
    unload_count: int = 0
    n_gpu_layers: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderManager:
    """
    Manage serial provider residency for constrained local hardware.

    Delta owns memory, evidence, and governance. This manager only controls
    transient inference provider lifecycle so a 12 GB GPU hosts at most one
    local model at a time.
    """

    def __init__(
        self,
        *,
        available_models: Mapping[str, ModelSpec] | None = None,
        runner_factory: RunnerFactory | None = None,
        n_gpu_layers: int | None = None,
        keep_loaded: bool = False,
        status_path: str | Path | None = None,
        capability_db_path: str | Path | None = None,
        provider_capabilities: Mapping[str, Any] | None = None,
    ) -> None:
        self.available_models = dict(available_models or list_available_models())
        self.runner_factory = runner_factory
        self.n_gpu_layers = n_gpu_layers
        self.keep_loaded = keep_loaded
        self.status_path = Path(status_path) if status_path is not None else None
        self.capability_db_path = Path(capability_db_path) if capability_db_path else None
        self.provider_capabilities = dict(provider_capabilities or {})
        self._active_spec: ModelSpec | None = None
        self._runner: ProviderRunner | None = None
        self._loaded_at: float | None = None
        self._load_count = 0
        self._unload_count = 0

    def load(self, model_name: str) -> ProviderLoadState:
        spec = self._resolve(model_name)
        if self._active_spec is not None and self._active_spec.name == spec.name:
            return self.status()
        self.unload()
        self._runner = self._create_runner(spec)
        self._active_spec = spec
        self._loaded_at = time.time()
        self._load_count += 1
        return self._publish_status()

    def warm(self, model_name: str) -> ProviderLoadState:
        state = self.load(model_name)
        method = getattr(self._runner, "load_model", None)
        if callable(method):
            method()
        return self._publish_status()

    def infer(
        self,
        *,
        model_name: str,
        prompt: str,
        task_type: str = "open_ended",
        metadata: Mapping[str, Any] | None = None,
    ) -> CanonicalInferenceResult:
        self.load(model_name)
        if self._runner is None or self._active_spec is None:
            raise RuntimeError("ProviderManager.infer() has no active provider")

        input_payload = {
            "question": prompt,
            "prompt": prompt,
            "task_type": task_type,
            "metadata": dict(metadata or {}),
        }
        raw = self._runner.produce_output(input_payload)
        return self._canonical_result(raw, prompt=prompt, task_type=task_type)

    def unload(self) -> ProviderLoadState:
        if self._runner is not None:
            for method_name in ("unload", "close"):
                method = getattr(self._runner, method_name, None)
                if callable(method):
                    method()
                    break
            self._runner = None
            self._active_spec = None
            self._loaded_at = None
            self._unload_count += 1
            gc.collect()
        return self._publish_status()

    def status(self) -> ProviderLoadState:
        spec = self._active_spec
        return ProviderLoadState(
            active_model=spec.name if spec is not None else None,
            loaded=spec is not None,
            loaded_at=self._loaded_at,
            load_count=self._load_count,
            unload_count=self._unload_count,
            n_gpu_layers=self._gpu_layers_for(spec) if spec is not None else self.n_gpu_layers,
            metadata=self._metadata(spec),
        )

    def _publish_status(self) -> ProviderLoadState:
        state = self.status()
        if self.status_path is not None:
            self.status_path.parent.mkdir(parents=True, exist_ok=True)
            self.status_path.write_text(
                json_dumps_state(state),
                encoding="utf-8",
            )
        return state

    def _resolve(self, model_name: str) -> ModelSpec:
        key = str(model_name).strip().lower()
        if key in self.available_models:
            return self.available_models[key]
        for spec in self.available_models.values():
            if spec.name == key:
                return spec
        raise ValueError(f"Unknown or unavailable model '{model_name}'")

    def _create_runner(self, spec: ModelSpec) -> ProviderRunner:
        if self.runner_factory is not None:
            return self.runner_factory(spec)
        from integration.model_runtime.gguf_model_runner import GGUFModelRunner

        return GGUFModelRunner(spec.name, n_gpu_layers=self._gpu_layers_for(spec), keep_loaded=self.keep_loaded)

    def _canonical_result(
        self,
        raw: Any,
        *,
        prompt: str,
        task_type: str,
    ) -> CanonicalInferenceResult:
        if isinstance(raw, CanonicalInferenceResult):
            return raw
        if hasattr(raw, "payload"):
            payload = dict(getattr(raw, "payload") or {})
            canonical = payload.get("canonical_inference") or {}
            return CanonicalInferenceResult(
                provider=str(canonical.get("provider") or "local_gguf"),
                model_id=str(canonical.get("model_id") or self._active_spec.name),
                answer=str(payload.get("answer") or payload.get("raw_model_output") or ""),
                raw_output=str(payload.get("raw_model_output") or payload.get("answer") or ""),
                confidence=float(payload.get("confidence") or getattr(raw, "confidence_band", 0.0)),
                latency_seconds=float(canonical.get("latency_seconds") or 0.0),
                prompt_tokens=int(canonical.get("prompt_tokens") or len(prompt.split())),
                response_tokens=int(canonical.get("response_tokens") or 0),
                evidence=list(canonical.get("evidence") or []),
                metadata={
                    **dict(canonical.get("metadata") or {}),
                    "task_type": task_type,
                    "provider_manager": "serial_local_v1",
                },
            )
        answer = str(raw)
        spec = self._active_spec
        return CanonicalInferenceResult(
            provider=spec.provider if spec is not None else "unknown",
            model_id=spec.name if spec is not None else "unknown",
            answer=answer,
            raw_output=answer,
            confidence=0.0,
            latency_seconds=0.0,
            prompt_tokens=len(prompt.split()),
            response_tokens=len(answer.split()),
            evidence=[],
            metadata={"task_type": task_type, "provider_manager": "serial_local_v1"},
        )

    def _metadata(self, spec: ModelSpec | None) -> dict[str, Any]:
        if spec is None:
            return {"resident_provider_count": 0}
        profile = self._profile_for(spec)
        return {
            "resident_provider_count": 1,
            "provider": spec.provider,
            "family": spec.family,
            "quantization": spec.quantization,
            "context_length": spec.context_length,
            "recommended_context": profile.get("recommended_context"),
            "recommended_gpu_layers": profile.get("recommended_gpu_layers"),
            "backend_tokens_per_second": profile.get("average_tokens_per_second"),
            "capabilities": list(spec.capabilities),
            "size_bytes": spec.size_bytes,
            "path": str(Path(spec.path)),
            "mmproj_path": spec.mmproj_path,
        }

    def _gpu_layers_for(self, spec: ModelSpec | None) -> int | None:
        if self.n_gpu_layers is not None:
            return self.n_gpu_layers
        if spec is None:
            return None
        value = self._profile_for(spec).get("recommended_gpu_layers")
        if value is None:
            configured = os.getenv("DELTA_N_GPU_LAYERS", "").strip()
            if not configured:
                return None
            try:
                return int(configured)
            except ValueError:
                return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _profile_for(self, spec: ModelSpec) -> dict[str, Any]:
        if not self.provider_capabilities and self.capability_db_path is not None:
            self.provider_capabilities = load_capability_database(self.capability_db_path)
        profile = self.provider_capabilities.get(spec.name)
        if isinstance(profile, dict):
            return profile
        profile = self.provider_capabilities.get(spec.name.lower())
        return profile if isinstance(profile, dict) else {}
