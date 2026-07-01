from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class CapabilityPlan:
    intent: str
    required_capabilities: tuple[str, ...]
    task_type: str
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityPlanner:
    """
    Determine cognitive capabilities before provider allocation.
    """

    _TASK_CAPABILITIES: dict[str, tuple[str, ...]] = {
        "math": ("mathematics", "reasoning"),
        "planning": ("planning", "reasoning"),
        "diagnostic": ("reasoning", "reflection"),
        "comparison": ("reasoning", "reflection"),
        "simulation": ("simulation", "prediction"),
        "prediction": ("prediction", "reasoning"),
        "coding": ("coding", "planning"),
        "translation": ("translation", "reasoning"),
        "research": ("research", "retrieval"),
        "vision": ("vision", "reasoning"),
        "reflection": ("reflection", "reasoning"),
    }

    _KEYWORD_CAPABILITIES: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("calculate", ("mathematics",)),
        ("sum", ("mathematics",)),
        ("schedule", ("planning", "mathematics")),
        ("plan", ("planning",)),
        ("code", ("coding",)),
        ("debug", ("coding", "diagnostic")),
        ("translate", ("translation",)),
        ("image", ("vision",)),
        ("vision", ("vision",)),
        ("simulate", ("simulation",)),
        ("predict", ("prediction",)),
        ("contradiction", ("reasoning", "reflection")),
        ("evidence", ("reasoning", "retrieval")),
        ("research", ("research", "retrieval")),
    )

    def plan(
        self,
        *,
        intent: str,
        task_type: str = "open_ended",
        metadata: dict[str, Any] | None = None,
        required_capabilities: Iterable[str] | None = None,
    ) -> CapabilityPlan:
        meta = dict(metadata or {})
        capabilities: list[str] = []
        capabilities.extend(self._TASK_CAPABILITIES.get(task_type, ("reasoning",)))
        capabilities.extend(str(item) for item in (required_capabilities or ()))
        lower_intent = str(intent).lower()
        for keyword, keyword_capabilities in self._KEYWORD_CAPABILITIES:
            if keyword in lower_intent:
                capabilities.extend(keyword_capabilities)

        normalized = self._normalize(capabilities)
        return CapabilityPlan(
            intent=str(intent),
            required_capabilities=normalized,
            task_type=str(task_type),
            rationale="Selected required cognitive capabilities before provider allocation.",
            metadata={
                **meta,
                "capability_selection_precedes_provider_allocation": True,
            },
        )

    @staticmethod
    def _normalize(capabilities: Iterable[str]) -> tuple[str, ...]:
        ordered: list[str] = []
        for capability in capabilities:
            normalized = str(capability).strip().lower()
            if normalized and normalized not in ordered:
                ordered.append(normalized)
        return tuple(ordered or ["reasoning"])
