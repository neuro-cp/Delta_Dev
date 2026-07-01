"""
integration/model_runtime/model_registry.py

Dynamic local model registry for Delta's model abstraction layer.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class ModelSpec:
    name: str
    path: str
    tier: int
    description: str
    context_length: int
    provider: str = "local_gguf"
    family: str = "unknown"
    quantization: str = "unknown"
    size_bytes: int = 0
    mmproj_path: str | None = None
    capabilities: tuple[str, ...] = ("text",)


def model_root() -> Path:
    configured = os.getenv("DELTA_MODEL_ROOT", "").strip()
    if configured:
        return Path(configured)
    return Path(r"G:\models")


def discover_local_models(root: str | Path | None = None) -> Dict[str, ModelSpec]:
    base = Path(root) if root is not None else model_root()
    if not base.exists():
        return {}

    specs: Dict[str, ModelSpec] = {}
    mmproj_by_dir = {
        path.parent: path
        for path in base.rglob("*.gguf")
        if path.name.lower().startswith("mmproj")
    }
    for path in sorted(base.rglob("*.gguf")):
        if path.name.lower().startswith("mmproj"):
            continue
        spec = _spec_from_path(path, mmproj_by_dir.get(path.parent))
        specs[spec.name] = spec

    return specs


def list_available_models() -> Dict[str, ModelSpec]:
    discovered = discover_local_models()
    aliased: Dict[str, ModelSpec] = dict(discovered)
    for alias, spec in _aliases(discovered).items():
        aliased.setdefault(alias, spec)
    return aliased


def list_models() -> Dict[str, ModelSpec]:
    return list_available_models()


def get_model_spec(model_name: str) -> ModelSpec:
    available = list_available_models()
    key = str(model_name).strip().lower()
    if key in available:
        return available[key]
    raise ValueError(f"Unknown or unavailable model '{model_name}'")


def _spec_from_path(path: Path, mmproj_path: Path | None) -> ModelSpec:
    file_name = path.stem
    dir_name = path.parent.name
    model_id = _model_id(dir_name, file_name)
    family = _family(file_name + " " + dir_name)
    quantization = _quantization(file_name)
    size_bytes = path.stat().st_size
    capabilities = ("text", "vision") if mmproj_path is not None else ("text",)

    return ModelSpec(
        name=model_id,
        path=str(path),
        tier=_tier(family, size_bytes),
        description=f"{family} local GGUF model ({quantization})",
        context_length=_context_length(family, file_name),
        provider="local_gguf",
        family=family,
        quantization=quantization,
        size_bytes=size_bytes,
        mmproj_path=str(mmproj_path) if mmproj_path else None,
        capabilities=capabilities,
    )


def _aliases(discovered: Dict[str, ModelSpec]) -> Dict[str, ModelSpec]:
    aliases: Dict[str, ModelSpec] = {}
    for spec in discovered.values():
        name = spec.name.lower()
        if spec.family == "phi3":
            aliases.setdefault("phi3", spec)
        if spec.family == "phi4":
            aliases.setdefault("phi4", spec)
        if spec.family == "qwen" and "vl" not in name:
            aliases.setdefault("qwen", spec)
        if spec.family == "llama":
            aliases.setdefault("llama", spec)
        if spec.family == "mistral":
            aliases.setdefault("mistral", spec)
    return aliases


def _model_id(dir_name: str, file_name: str) -> str:
    raw = f"{dir_name}-{file_name}".lower()
    raw = raw.replace(".gguf", "")
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    raw = re.sub(r"-+", "-", raw)
    return raw


def _family(text: str) -> str:
    lower = text.lower()
    if "phi-4" in lower or "phi4" in lower:
        return "phi4"
    if "phi-3" in lower or "phi3" in lower:
        return "phi3"
    if "qwen" in lower:
        return "qwen"
    if "llama" in lower:
        return "llama"
    if "ministral" in lower:
        return "ministral"
    if "mistral" in lower:
        return "mistral"
    return "unknown"


def _quantization(file_name: str) -> str:
    match = re.search(r"(q\d(?:_[a-z]+(?:_[a-z]+)?)?|f16|bf16)", file_name.lower())
    return match.group(1).upper() if match else "unknown"


def _context_length(family: str, file_name: str) -> int:
    lower = file_name.lower()
    if "4k" in lower:
        return 4096
    if family == "qwen":
        return 32768
    if family in {"llama", "phi4", "mistral", "ministral"}:
        return 8192
    return 4096


def _tier(family: str, size_bytes: int) -> int:
    if family == "phi3":
        return 1
    if family in {"phi4", "ministral"}:
        return 2
    if family in {"qwen", "mistral"}:
        return 3
    if family == "llama":
        return 4
    return 5 if size_bytes else 9
