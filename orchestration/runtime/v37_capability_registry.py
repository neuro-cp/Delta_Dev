"""Runtime ARC I V3.7 cognitive capability registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from orchestration.runtime.v32_cognitive_kernel import CognitiveKernel


@dataclass(frozen=True)
class CapabilityRecord:
    capability: str
    handler: str
    active: bool
    mutating: bool = False
    authority: str = "orchestration_only"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class CognitiveCapabilityRegistry:
    def __init__(self, records: tuple[CapabilityRecord, ...] | None = None) -> None:
        self.records = records or default_capability_records()

    def resolve(self, capability: str) -> CapabilityRecord | None:
        capability = capability.lower()
        for record in self.records:
            if capability in record.capability.lower():
                return record
        return None

    def as_dict(self) -> dict[str, object]:
        return {
            "phase": "Runtime V3.7",
            "records": [record.as_dict() for record in self.records],
            "kernel_managers": list(CognitiveKernel().manager_names()),
        }


def default_capability_records() -> tuple[CapabilityRecord, ...]:
    return (
        CapabilityRecord("self_description", "ReasoningManager", True),
        CapabilityRecord("pipeline_explanation", "ReasoningManager", True),
        CapabilityRecord("semantic_consolidation_cycle", "IntegrationManager", True),
        CapabilityRecord("vertical_runtime_trace", "IntegrationManager", True),
        CapabilityRecord("audit_graph_review", "ReviewManager", True),
        CapabilityRecord("learning_opportunity_detection", "LearningManager", True),
        CapabilityRecord("learning_review", "ReviewManager", True),
        CapabilityRecord("gated_integration_scaffold", "IntegrationManager", True),
        CapabilityRecord("provider_call", "SafetyManager", False),
        CapabilityRecord("training", "SafetyManager", False),
        CapabilityRecord("action_execution", "SafetyManager", False),
        CapabilityRecord("scheduler_activation", "SafetyManager", False),
    )
