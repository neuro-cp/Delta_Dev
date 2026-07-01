from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from integration.model_runtime.capability_planner import CapabilityPlan
from integration.model_runtime.model_registry import ModelSpec


@dataclass(frozen=True)
class ModelRouteDecision:
    route: str
    model_name: str | None
    rationale: str
    cloud_allowed: bool = False
    parallel: bool = False
    metadata: dict[str, Any] | None = None


class ModelRoutingPolicy:
    """
    Select model routes without granting models substrate authority.
    """

    _CAPABILITY_FAMILY_PRIORS: dict[str, tuple[str, ...]] = {
        "planning": ("phi4", "qwen", "mistral", "llama"),
        "coding": ("phi4", "qwen", "mistral", "llama"),
        "vision": ("qwen",),
        "translation": ("qwen", "llama", "mistral", "ministral"),
        "research": ("qwen", "llama", "mistral", "ministral"),
        "reflection": ("mistral", "qwen", "llama", "phi4"),
        "prediction": ("phi4", "qwen", "mistral", "llama"),
        "simulation": ("phi4", "qwen", "mistral", "llama"),
        "reasoning": ("phi4", "qwen", "mistral", "llama", "phi3"),
    }

    def decide(
        self,
        *,
        task_type: str,
        prompt: str,
        available_models: Mapping[str, ModelSpec],
        runtime_health: Mapping[str, Any] | None = None,
        capability_plan: CapabilityPlan | None = None,
        required_capabilities: Sequence[str] | None = None,
        allow_cloud: bool = False,
        force_parallel: bool = False,
    ) -> ModelRouteDecision:
        prompt_tokens = len(str(prompt).split())
        health = dict(runtime_health or {})
        prediction_quality = health.get("prediction_quality")
        capabilities = tuple(
            capability_plan.required_capabilities
            if capability_plan is not None
            else (required_capabilities or ())
        )

        if task_type == "math":
            return ModelRouteDecision(
                route="deterministic",
                model_name=None,
                rationale="Deterministic tasks should not spend model inference.",
                metadata={
                    "prompt_tokens": prompt_tokens,
                    "required_capabilities": list(capabilities),
                },
            )

        if force_parallel:
            return ModelRouteDecision(
                route="parallel_comparison",
                model_name=None,
                rationale="Operator requested parallel comparison.",
                parallel=True,
                cloud_allowed=allow_cloud,
                metadata={
                    "prompt_tokens": prompt_tokens,
                    "required_capabilities": list(capabilities),
                },
            )

        local = self._select_local_model(
            task_type=task_type,
            prompt_tokens=prompt_tokens,
            available_models=available_models,
            required_capabilities=capabilities,
        )
        if local is not None:
            return ModelRouteDecision(
                route="local",
                model_name=local.name,
                rationale="Selected available local model before cloud escalation.",
                cloud_allowed=False,
                metadata={
                    "prompt_tokens": prompt_tokens,
                    "family": local.family,
                    "context_length": local.context_length,
                    "prediction_quality": prediction_quality,
                    "required_capabilities": list(capabilities),
                    "capability_plan_task_type": capability_plan.task_type
                    if capability_plan is not None
                    else None,
                },
            )

        if allow_cloud:
            return ModelRouteDecision(
                route="cloud",
                model_name="openai",
                rationale=(
                    "No suitable local provider was available; cloud escalation was "
                    "explicitly allowed as a last resort."
                ),
                cloud_allowed=True,
                metadata={
                    "prompt_tokens": prompt_tokens,
                    "required_capabilities": list(capabilities),
                    "provider_identity_is_implementation_detail": True,
                },
            )

        return ModelRouteDecision(
            route="human_review",
            model_name=None,
            rationale="No suitable local model was available and cloud use was not allowed.",
            cloud_allowed=False,
            metadata={
                "prompt_tokens": prompt_tokens,
                "required_capabilities": list(capabilities),
            },
        )

    def _select_local_model(
        self,
        *,
        task_type: str,
        prompt_tokens: int,
        available_models: Mapping[str, ModelSpec],
        required_capabilities: Sequence[str] = (),
    ) -> ModelSpec | None:
        candidates: Sequence[ModelSpec] = sorted(
            {
                spec.name: spec
                for spec in available_models.values()
                if spec.provider == "local_gguf" and "text" in spec.capabilities
            }.values(),
            key=lambda spec: (spec.tier, spec.size_bytes),
        )
        if not candidates:
            return None

        capabilities = set(required_capabilities)
        if "vision" in capabilities:
            preferred = [spec for spec in candidates if "vision" in spec.capabilities]
        else:
            family_order = self._family_order(task_type, capabilities)
            preferred = [
                spec
                for family in family_order
                for spec in candidates
                if spec.family == family
            ]

        pool = preferred or list(candidates)
        for spec in pool:
            if prompt_tokens < spec.context_length * 0.75:
                return spec
        return None

    def _family_order(self, task_type: str, capabilities: set[str]) -> tuple[str, ...]:
        ordered: list[str] = []
        for capability in sorted(capabilities):
            ordered.extend(self._CAPABILITY_FAMILY_PRIORS.get(capability, ()))
        if task_type in {"planning", "diagnostic", "comparison"}:
            ordered.extend(self._CAPABILITY_FAMILY_PRIORS["planning"])
        if not ordered:
            ordered.extend(("phi3", "ministral", "phi4", "qwen", "mistral", "llama"))

        normalized: list[str] = []
        for family in ordered:
            if family not in normalized:
                normalized.append(family)
        return tuple(normalized)
