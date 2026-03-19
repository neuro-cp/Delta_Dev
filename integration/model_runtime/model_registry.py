"""
integration/model_runtime/model_registry.py

Model registry for local GGUF models.

Responsibilities
----------------
• Declare available models
• Provide deterministic lookup
• Contain no runtime logic
• Contain no GPU interaction

This module is purely descriptive.
"""

from dataclasses import dataclass
from typing import Dict


# ---------------------------------------------------------------------
# Model specification
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class ModelSpec:
    """
    Immutable description of a model available to the runtime.
    """

    name: str
    path: str
    tier: int
    description: str
    context_length: int


# ---------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------

MODEL_REGISTRY: Dict[str, ModelSpec] = {

    # ---------------------------------------------------------------
    # Tier 1 – Fast structured reasoning
    # ---------------------------------------------------------------

    "phi3": ModelSpec(
        name="phi3",
        path=r"G:\Models\microsoft\Phi-3-mini-4k-instruct-gguf\Phi-3-mini-4k-instruct-q4.gguf",
        tier=1,
        description="Fast structured reasoning model",
        context_length=4096,
    ),

    # ---------------------------------------------------------------
    # Tier 2 – Deeper reasoning attempt
    # ---------------------------------------------------------------

    "phi4": ModelSpec(
        name="phi4",
        path=r"G:\Models\lmstudio-community\Phi-4-mini-reasoning-GGUF\Phi-4-mini-reasoning-Q4_K_M.gguf",
        tier=2,
        description="Reasoning-focused model with deeper inference capability",
        context_length=8192,
    ),

    # ---------------------------------------------------------------
    # Tier 3 – Deep reasoning / analysis
    # ---------------------------------------------------------------

    "qwen": ModelSpec(
        name="qwen",
        path=r"G:\Models\lmstudio-community\Qwen2.5-VL-7B-Instruct-GGUF\Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
        tier=3,
        description="Qwen2.5-VL multimodal reasoning model",
        context_length=32768,
    ),

    # ---------------------------------------------------------------
    # Tier 4 – Knowledge + reasoning fallback
    # ---------------------------------------------------------------

    "llama": ModelSpec(
        name="llama",
        path=r"G:\Models\lmstudio-community\Meta-Llama-3.1-8B-Instruct-GGUF\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        tier=4,
        description="Broad knowledge and reasoning fallback model",
        context_length=8192,
    ),
}


# ---------------------------------------------------------------------
# Access helpers
# ---------------------------------------------------------------------

def get_model_spec(model_name: str) -> ModelSpec:
    """
    Deterministic lookup of model specification.
    """

    try:
        return MODEL_REGISTRY[model_name]

    except KeyError as exc:
        available = ", ".join(MODEL_REGISTRY.keys())
        raise ValueError(
            f"Unknown model '{model_name}'. Available models: {available}"
        ) from exc


def list_models() -> Dict[str, ModelSpec]:
    """
    Return registry snapshot.
    """

    return dict(MODEL_REGISTRY)