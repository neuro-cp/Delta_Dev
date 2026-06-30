"""
integration/model_runtime/model_registry.py
"""

from dataclasses import dataclass
from typing import Dict
import os


@dataclass(frozen=True)
class ModelSpec:
    name: str
    path: str
    tier: int
    description: str
    context_length: int


# -----------------------------
# Profile
# -----------------------------

def _machine_profile() -> str:
    return os.getenv("DELTA_MACHINE_PROFILE", "laptop").strip().lower()


# -----------------------------
# Safe path resolver
# -----------------------------

def _safe_path(primary: str, fallback: str) -> str:
    if os.path.exists(primary):
        return primary
    if os.path.exists(fallback):
        return fallback
    raise ValueError(f"No valid model path found:\n- {primary}\n- {fallback}")


# -----------------------------
# Path resolvers
# -----------------------------

def _phi3_path() -> str:
    laptop = (
        r"C:\Users\Admin\Desktop\models\lmstudio-community"
        r"\Phi-3.1-mini-4k-instruct-GGUF"
        r"\Phi-3.1-mini-4k-instruct-Q4_K_M.gguf"
    )

    desktop = (
        r"G:\Models\microsoft"
        r"\Phi-3-mini-4k-instruct-gguf"
        r"\Phi-3-mini-4k-instruct-q4.gguf"
    )

    return _safe_path(laptop, desktop)


def _phi4_path() -> str:
    laptop = (
        r"C:\Users\Admin\Desktop\models\lmstudio-community"
        r"\Phi-4-mini-reasoning-GGUF"
        r"\Phi-4-mini-reasoning-Q4_K_M.gguf"
    )

    desktop = (
        r"G:\Models\lmstudio-community"
        r"\Phi-4-mini-reasoning-GGUF"
        r"\Phi-4-mini-reasoning-Q4_K_M.gguf"
    )

    return _safe_path(laptop, desktop)


def _qwen_path() -> str:
    laptop = (
        r"C:\Users\Admin\Desktop\models\lmstudio-community"
        r"\Qwen2.5-7B-Instruct-GGUF"
        r"\Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    )

    desktop = (
        r"G:\Models\lmstudio-community"
        r"\Qwen2.5-7B-Instruct-GGUF"
        r"\Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    )

    return _safe_path(laptop, desktop)


def _llama_path() -> str:
    laptop = (
        r"C:\Users\Admin\Desktop\models\lmstudio-community"
        r"\Meta-Llama-3.1-8B-Instruct-GGUF"
        r"\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
    )

    desktop = (
        r"G:\Models\lmstudio-community"
        r"\Meta-Llama-3.1-8B-Instruct-GGUF"
        r"\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
    )

    return _safe_path(laptop, desktop)


# -----------------------------
# Registry
# -----------------------------

MODEL_REGISTRY: Dict[str, ModelSpec] = {
    "phi3": ModelSpec(
        name="phi3",
        path="",
        tier=1,
        description="Fast structured reasoning model",
        context_length=4096,
    ),
    "phi4": ModelSpec(
        name="phi4",
        path="",
        tier=2,
        description="Reasoning-focused model",
        context_length=8192,
    ),
    "qwen": ModelSpec(
        name="qwen",
        path="",
        tier=3,
        description="Qwen2.5 instruct model",
        context_length=32768,
    ),
    "llama": ModelSpec(
        name="llama",
        path="",
        tier=4,
        description="Fallback general model",
        context_length=8192,
    ),
}


# -----------------------------
# Runtime resolution
# -----------------------------

def _resolve_path(model_name: str) -> str:
    if model_name == "phi3":
        return _phi3_path()
    if model_name == "phi4":
        return _phi4_path()
    if model_name == "qwen":
        return _qwen_path()
    if model_name == "llama":
        return _llama_path()

    raise ValueError(f"Unknown model '{model_name}'")


def get_model_spec(model_name: str) -> ModelSpec:
    base = MODEL_REGISTRY.get(model_name)
    if not base:
        raise ValueError(f"Unknown model '{model_name}'")

    return ModelSpec(
        name=base.name,
        path=_resolve_path(model_name),
        tier=base.tier,
        description=base.description,
        context_length=base.context_length,
    )


def list_models() -> Dict[str, ModelSpec]:
    return {name: get_model_spec(name) for name in MODEL_REGISTRY}


def list_available_models() -> Dict[str, ModelSpec]:
    available: Dict[str, ModelSpec] = {}

    for name in MODEL_REGISTRY:
        try:
            available[name] = get_model_spec(name)
        except ValueError:
            continue

    return available
