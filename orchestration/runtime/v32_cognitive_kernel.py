"""Runtime ARC I V3.2 cognitive kernel skeleton.

The kernel is orchestration-only. Managers expose deterministic handlers, but
the kernel does not change cognition, train, write memory, call providers,
execute actions, or start background work.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KernelManager:
    name: str
    responsibility: str
    mutating: bool = False
    authority: str = "orchestration_only"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class CognitiveKernel:
    """Central orchestration surface for runtime cognitive operations."""

    def __init__(self, managers: tuple[KernelManager, ...] | None = None) -> None:
        self.managers = managers or default_kernel_managers()

    def manager_names(self) -> tuple[str, ...]:
        return tuple(manager.name for manager in self.managers)

    def route(self, capability: str) -> KernelManager | None:
        capability = capability.lower()
        for manager in self.managers:
            if capability in manager.name.lower() or capability in manager.responsibility.lower():
                return manager
        return None

    def describe(self) -> dict[str, object]:
        return {
            "phase": "Runtime V3.2",
            "kernel_role": "orchestration_only",
            "managers": [manager.as_dict() for manager in self.managers],
            "training_performed": False,
            "provider_call_performed": False,
            "memory_mutation_performed": False,
            "action_execution_performed": False,
        }


def default_kernel_managers() -> tuple[KernelManager, ...]:
    return (
        KernelManager("ExperienceManager", "experience capture and boundary review"),
        KernelManager("EvidenceManager", "evidence provenance and support inspection"),
        KernelManager("RecallManager", "candidate-context recall coordination"),
        KernelManager("ReasoningManager", "local deterministic reasoning/explanation coordination"),
        KernelManager("LearningManager", "learning opportunity and proposal scaffolds"),
        KernelManager("ReviewManager", "human/admin review state coordination"),
        KernelManager("IntegrationManager", "gated integration event scaffolds and rollback handles"),
        KernelManager("SafetyManager", "invariant checks and stop conditions"),
    )
