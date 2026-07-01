"""
Model runtime subsystem.

Responsible for:
- managing model registry
- handling runtime model sessions
- exposing runners that implement ExternalModelInterface
"""

from integration.model_runtime.inference_types import (
    CanonicalInferenceResult,
    InferenceRequest,
)
from integration.model_runtime.capability_planner import (
    CapabilityPlan,
    CapabilityPlanner,
)
from integration.model_runtime.model_observatory import (
    ModelInferenceRecord,
    ModelObservatory,
)
from integration.model_runtime.model_registry import (
    ModelSpec,
    get_model_spec,
    list_available_models,
    list_models,
)
from integration.model_runtime.provider_learning import (
    ProviderLearningEngine,
    ProviderPerformanceProfile,
)
from integration.model_runtime.provider_manager import (
    ProviderLoadState,
    ProviderManager,
)
from integration.model_runtime.provider_qualification import (
    ProviderQualificationRecord,
    ProviderQualificationReportWriter,
    ProviderQualificationSuite,
    load_capability_database,
    qualified_model_names,
)
from integration.model_runtime.model_comparison import (
    ModelComparisonEngine,
    ModelComparisonReport,
)
from integration.model_runtime.routing_policy import (
    ModelRouteDecision,
    ModelRoutingPolicy,
)

__all__ = [
    "CanonicalInferenceResult",
    "CapabilityPlan",
    "CapabilityPlanner",
    "InferenceRequest",
    "ModelInferenceRecord",
    "ModelObservatory",
    "ModelComparisonEngine",
    "ModelComparisonReport",
    "ModelSpec",
    "ProviderLearningEngine",
    "ProviderLoadState",
    "ProviderManager",
    "ProviderQualificationRecord",
    "ProviderQualificationReportWriter",
    "ProviderQualificationSuite",
    "ProviderPerformanceProfile",
    "load_capability_database",
    "qualified_model_names",
    "get_model_spec",
    "list_available_models",
    "list_models",
    "ModelRouteDecision",
    "ModelRoutingPolicy",
]
