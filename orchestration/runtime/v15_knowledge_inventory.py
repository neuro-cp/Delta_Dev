from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


RUNTIME_V15_KNOWLEDGE_INVENTORY_FLAGS: dict[str, bool] = {
    "inventory_report_enabled": True,
    "repo_scan_enabled": True,
    "model_training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "provider_calls_enabled": False,
    "provider_calls_performed": False,
    "memory_mutation_enabled": False,
    "memory_mutation_performed": False,
    "canonical_write_enabled": False,
    "runtime_recall_active": False,
    "runtime_recall_mutation_enabled": False,
    "hyb1_promoted": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
    "training_enabled": False,
    "action_execution_enabled": False,
    "tool_calls_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class KnowledgeInventoryCategory(str, Enum):
    LEARNED_MODEL_KNOWLEDGE = "learned_model_knowledge"
    REPO_LOCAL_SCAFFOLD_KNOWLEDGE = "repo_local_scaffold_knowledge"
    REPORTS = "reports"
    TESTS = "tests"
    RUNTIME_CONSOLE_RESPONSE_TEMPLATES = "runtime_console_response_templates"
    PHASE_SUMMARIES = "phase_summaries"
    SAFETY_INVARIANTS = "safety_invariants"
    ACTIVE_CAPABILITIES = "active_capabilities"
    INACTIVE_CAPABILITIES = "inactive_capabilities"
    UNAVAILABLE_KNOWLEDGE = "unavailable_knowledge"


@dataclass(frozen=True)
class KnowledgeInventoryItem:
    item_id: str
    category: KnowledgeInventoryCategory
    name: str
    summary: str
    source_path: str = ""
    available_locally: bool = True
    active: bool = False
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class RuntimeKnowledgeInventory:
    inventory_id: str
    repo_root: str
    generated_at: str
    items: tuple[KnowledgeInventoryItem, ...]
    invariant_flags: dict[str, bool]
    active_capabilities: tuple[str, ...]
    inactive_capabilities: tuple[str, ...]
    unavailable_knowledge: tuple[str, ...]
    local_answer_scope: tuple[str, ...]
    learned_model_knowledge_summary: str
    repo_local_knowledge_summary: str

    def as_dict(self) -> dict[str, object]:
        return {
            "inventory_id": self.inventory_id,
            "repo_root": self.repo_root,
            "generated_at": self.generated_at,
            "items": [item.as_dict() for item in self.items],
            "invariant_flags": dict(self.invariant_flags),
            "active_capabilities": list(self.active_capabilities),
            "inactive_capabilities": list(self.inactive_capabilities),
            "unavailable_knowledge": list(self.unavailable_knowledge),
            "local_answer_scope": list(self.local_answer_scope),
            "learned_model_knowledge_summary": self.learned_model_knowledge_summary,
            "repo_local_knowledge_summary": self.repo_local_knowledge_summary,
        }


def build_runtime_knowledge_inventory(repo_root: str | Path = ".") -> RuntimeKnowledgeInventory:
    root = Path(repo_root).resolve()
    reports = _scan_files(root / "reports", ("runtime_v14*.md", "runtime_v15*.md"))
    tests = _scan_files(root / "tests", ("runtime_v14/test_*.py", "runtime_v15/test_*.py"))
    modules = _scan_files(root / "orchestration" / "runtime", ("v14_*.py", "v15_*.py", "runtime_reasoning.py"))
    scripts = _scan_files(root / "scripts", ("runtime_console.py", "runtime_console_smoke.py", "ask_delta.py", "delta_knowledge_inventory.py"))
    phase_items = _phase_summary_items(reports)
    items: list[KnowledgeInventoryItem] = [
        _item(
            KnowledgeInventoryCategory.LEARNED_MODEL_KNOWLEDGE,
            "No Codex model training performed",
            "Codex did not train model weights, fine-tune a model, or create a learned model artifact in this repo.",
            available_locally=False,
        ),
        _item(
            KnowledgeInventoryCategory.REPO_LOCAL_SCAFFOLD_KNOWLEDGE,
            "Repo-local DELTA scaffold",
            "DELTA can inspect local runtime modules, reports, docs, tests, and deterministic console response templates.",
        ),
    ]
    items.extend(_file_items(KnowledgeInventoryCategory.REPORTS, reports, "Runtime report artifact"))
    items.extend(_file_items(KnowledgeInventoryCategory.TESTS, tests, "Runtime regression test file"))
    items.extend(_file_items(KnowledgeInventoryCategory.REPO_LOCAL_SCAFFOLD_KNOWLEDGE, modules, "Runtime scaffold module"))
    items.extend(_file_items(KnowledgeInventoryCategory.REPO_LOCAL_SCAFFOLD_KNOWLEDGE, scripts, "Runtime script"))
    items.extend(phase_items)
    items.extend(_runtime_console_template_items())
    items.extend(_safety_invariant_items())
    items.extend(_active_capability_items())
    items.extend(_inactive_capability_items())
    items.extend(_unavailable_knowledge_items())
    inventory_id = _stable_id(
        "knowledge-inventory",
        tuple(item.item_id for item in items),
        RUNTIME_V15_KNOWLEDGE_INVENTORY_FLAGS,
    )
    return RuntimeKnowledgeInventory(
        inventory_id=inventory_id,
        repo_root=str(root),
        generated_at=datetime.now(timezone.utc).isoformat(),
        items=tuple(items),
        invariant_flags=dict(RUNTIME_V15_KNOWLEDGE_INVENTORY_FLAGS),
        active_capabilities=(
            "manual runtime console message preview",
            "raw experience preview construction",
            "structural semantic preview construction",
            "trace/safety/status generation",
            "deterministic local response preview",
            "repo-local knowledge inventory report generation",
        ),
        inactive_capabilities=(
            "provider calls",
            "HYB1 default activation",
            "active recall bridge",
            "canonical memory writes",
            "memory mutation",
            "training/fine-tuning/weight updates",
            "dataset export",
            "specialist routing",
            "action/tool execution",
            "background schedulers/listeners/queues",
        ),
        unavailable_knowledge=(
            "arbitrary world knowledge without provider/model integration",
            "canonical memory contents until canonical store and recall are activated",
            "learned model updates because no training has occurred",
            "live external facts because provider calls remain disabled",
            "user-specific memory unless explicitly present in repo-local reports",
        ),
        local_answer_scope=(
            "DELTA scaffold and phase history from repo-local reports",
            "safety boundaries and invariant flags",
            "runtime console response templates",
            "available local scripts/modules/tests",
            "Model B/HYB1 local comparison report summaries",
        ),
        learned_model_knowledge_summary="No new learned model knowledge was created by Codex; model weights were not trained or changed.",
        repo_local_knowledge_summary="Repo-local architectural/self-description knowledge is available through files, reports, tests, and deterministic response templates.",
    )


def summarize_inventory(inventory: RuntimeKnowledgeInventory) -> dict[str, object]:
    by_category: dict[str, int] = {}
    for item in inventory.items:
        by_category[item.category.value] = by_category.get(item.category.value, 0) + 1
    return {
        "inventory_id": inventory.inventory_id,
        "category_counts": dict(sorted(by_category.items())),
        "active_capabilities": list(inventory.active_capabilities),
        "inactive_capabilities": list(inventory.inactive_capabilities),
        "unavailable_knowledge": list(inventory.unavailable_knowledge),
        "model_training_occurred": False,
        "hyb1_promoted": False,
        "provider_calls_occurred": False,
        "memory_or_recall_mutation_occurred": False,
    }


def validate_inventory_non_mutating(inventory: RuntimeKnowledgeInventory) -> bool:
    flags = inventory.invariant_flags
    return (
        flags["inventory_report_enabled"] is True
        and flags["repo_scan_enabled"] is True
        and all(
            value is False
            for key, value in flags.items()
            if key not in {"inventory_report_enabled", "repo_scan_enabled"}
        )
        and "manual runtime console message preview" in inventory.active_capabilities
        and "provider calls" in inventory.inactive_capabilities
        and "arbitrary world knowledge without provider/model integration" in inventory.unavailable_knowledge
    )


def _scan_files(base: Path, patterns: tuple[str, ...]) -> tuple[Path, ...]:
    if not base.exists():
        return ()
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in base.glob(pattern) if path.is_file())
    return tuple(sorted(set(files), key=lambda path: str(path).lower()))


def _file_items(category: KnowledgeInventoryCategory, paths: tuple[Path, ...], summary: str) -> tuple[KnowledgeInventoryItem, ...]:
    return tuple(
        _item(category, path.name, summary, source_path=str(path), available_locally=True, active=False)
        for path in paths
    )


def _phase_summary_items(report_paths: tuple[Path, ...]) -> tuple[KnowledgeInventoryItem, ...]:
    items: list[KnowledgeInventoryItem] = []
    for path in report_paths:
        name = path.stem.replace("runtime_", "").replace("_", " ")
        if any(token in path.name for token in ("v14", "v15")):
            items.append(_item(KnowledgeInventoryCategory.PHASE_SUMMARIES, name, "Phase summary available as repo-local report.", str(path)))
    return tuple(items)


def _runtime_console_template_items() -> tuple[KnowledgeInventoryItem, ...]:
    return (
        _item(
            KnowledgeInventoryCategory.RUNTIME_CONSOLE_RESPONSE_TEMPLATES,
            "DELTA replay/consolidation local summary",
            "Deterministic response for questions about DELTA's replay and consolidation scaffold.",
            "orchestration/runtime/v15_first_interaction.py",
            active=True,
        ),
        _item(
            KnowledgeInventoryCategory.RUNTIME_CONSOLE_RESPONSE_TEMPLATES,
            "Unknown scaffold notice",
            "Deterministic local fallback for questions outside repo-local scaffold knowledge.",
            "orchestration/runtime/v15_first_interaction.py",
            active=True,
        ),
    )


def _safety_invariant_items() -> tuple[KnowledgeInventoryItem, ...]:
    return tuple(
        _item(KnowledgeInventoryCategory.SAFETY_INVARIANTS, key, f"Invariant flag is {value}.", active=value)
        for key, value in sorted(RUNTIME_V15_KNOWLEDGE_INVENTORY_FLAGS.items())
    )


def _active_capability_items() -> tuple[KnowledgeInventoryItem, ...]:
    return tuple(
        _item(KnowledgeInventoryCategory.ACTIVE_CAPABILITIES, name, "Active local/non-mutating capability.", active=True)
        for name in (
            "manual runtime console message preview",
            "repo-local knowledge inventory",
            "deterministic local response preview",
        )
    )


def _inactive_capability_items() -> tuple[KnowledgeInventoryItem, ...]:
    return tuple(
        _item(KnowledgeInventoryCategory.INACTIVE_CAPABILITIES, name, "Capability remains disabled/inactive.", active=False)
        for name in (
            "provider calls",
            "HYB1 default activation",
            "active recall bridge",
            "canonical memory writes",
            "training",
            "specialist routing",
            "action execution",
        )
    )


def _unavailable_knowledge_items() -> tuple[KnowledgeInventoryItem, ...]:
    return tuple(
        _item(KnowledgeInventoryCategory.UNAVAILABLE_KNOWLEDGE, name, "Unavailable until future gated activation.", available_locally=False)
        for name in (
            "arbitrary current world facts",
            "canonical memory recall",
            "trained/fine-tuned model knowledge",
            "external provider/model answers",
        )
    )


def _item(
    category: KnowledgeInventoryCategory,
    name: str,
    summary: str,
    source_path: str = "",
    *,
    available_locally: bool = True,
    active: bool = False,
    mutating: bool = False,
) -> KnowledgeInventoryItem:
    return KnowledgeInventoryItem(
        item_id=_stable_id("inventory-item", category.value, name, summary, source_path, available_locally, active, mutating),
        category=category,
        name=name,
        summary=summary,
        source_path=source_path,
        available_locally=available_locally,
        active=active,
        mutating=mutating,
    )


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        elif isinstance(value, tuple):
            values[key] = [item.value if isinstance(item, Enum) else item for item in value]
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(_normalize_part(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, Enum):
        return part.value
    if isinstance(part, Path):
        return str(part)
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)
