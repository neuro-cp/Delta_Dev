"""Runtime ARC I V3.8 dynamic pipeline builder."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from orchestration.runtime.v37_capability_registry import CognitiveCapabilityRegistry


@dataclass(frozen=True)
class PipelineStep:
    step_id: str
    capability: str
    handler: str
    active: bool
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DynamicPipeline:
    request: str
    steps: tuple[PipelineStep, ...]
    provider_required: bool = False
    mutation_allowed: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "request": self.request,
            "steps": [step.as_dict() for step in self.steps],
            "provider_required": self.provider_required,
            "mutation_allowed": self.mutation_allowed,
        }


def build_dynamic_pipeline(request: str, registry: CognitiveCapabilityRegistry | None = None) -> DynamicPipeline:
    registry = registry or CognitiveCapabilityRegistry()
    normalized = request.lower()
    capabilities = ["self_description"]
    if "explain" in normalized or "reasoning" in normalized:
        capabilities.append("pipeline_explanation")
    if "learn" in normalized or "corrected" in normalized or "proposal" in normalized:
        capabilities.extend(["learning_opportunity_detection", "learning_review", "gated_integration_scaffold"])
    if "atlas" in normalized or "semantic" in normalized or "consolidation" in normalized or "corpus" in normalized:
        capabilities.extend(["semantic_consolidation_cycle", "vertical_runtime_trace", "audit_graph_review"])
    steps = []
    for index, capability in enumerate(dict.fromkeys(capabilities)):
        record = registry.resolve(capability)
        if record:
            steps.append(PipelineStep(f"pipeline-step-{index+1}", capability, record.handler, record.active, record.mutating))
    return DynamicPipeline(request=request, steps=tuple(steps), provider_required=False, mutation_allowed=False)
