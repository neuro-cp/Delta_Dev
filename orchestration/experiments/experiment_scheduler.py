from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from integration.model_runtime import (
    CapabilityPlanner,
    ModelRouteDecision,
    ModelRoutingPolicy,
)
from integration.model_runtime.inference_types import CanonicalInferenceResult
from integration.model_runtime.provider_manager import ProviderManager
from integration.model_runtime.provider_qualification import qualified_model_names
from orchestration.experience import ExperienceGenerator, ExperienceRequest, ExperienceStore
from orchestration.novelty import NoveltyAnalyzer


@dataclass(frozen=True)
class ExperimentQueueItem:
    item_id: str
    created_at: str
    prompt: str
    capability: str
    task_type: str = "open_ended"
    status: str = "queued"
    provider_model: str | None = None
    route: str | None = None
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExperimentResult:
    item_id: str
    completed_at: str
    status: str
    route: str
    provider_model: str | None
    answer: str
    utility_score: float | None
    information_gain_score: float | None
    surprise_score: float | None
    generated_experience_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExperimentSchedulerSummary:
    queued: int
    running: int
    completed: int
    failed: int
    latest_results: tuple[ExperimentResult, ...]
    cumulative_utility: float
    active_provider: dict[str, Any]


class ExperimentQueueStore:
    """
    Append-only queue/result store for idle desktop experiments.
    """

    def __init__(self, queue_path: str | Path, results_path: str | Path | None = None) -> None:
        self.queue_path = Path(queue_path)
        self.results_path = Path(results_path) if results_path is not None else self.queue_path.with_name(
            "experiment_results.jsonl"
        )

    def enqueue_many(self, items: Iterable[ExperimentQueueItem]) -> list[ExperimentQueueItem]:
        records = list(items)
        if not records:
            return []
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        with self.queue_path.open("a", encoding="utf-8") as handle:
            for item in records:
                handle.write(json.dumps(self._jsonable(item), sort_keys=True) + "\n")
        return records

    def add_result(self, result: ExperimentResult) -> ExperimentResult:
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        with self.results_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._jsonable(result), sort_keys=True) + "\n")
        return result

    def items(self) -> list[ExperimentQueueItem]:
        if not self.queue_path.exists():
            return []
        records: list[ExperimentQueueItem] = []
        with self.queue_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    payload = json.loads(line)
                    records.append(ExperimentQueueItem(**payload))
        return records

    def results(self) -> list[ExperimentResult]:
        if not self.results_path.exists():
            return []
        records: list[ExperimentResult] = []
        with self.results_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(ExperimentResult(**json.loads(line)))
        return records

    def summary(self, active_provider: Mapping[str, Any] | None = None) -> ExperimentSchedulerSummary:
        items = self.items()
        results = self.results()
        completed_ids = {result.item_id for result in results if result.status == "completed"}
        failed_ids = {result.item_id for result in results if result.status == "failed"}
        queued = [
            item
            for item in items
            if item.item_id not in completed_ids
            and item.item_id not in failed_ids
            and item.status == "queued"
        ]
        utility_values = [
            float(result.utility_score)
            for result in results
            if result.utility_score is not None and result.status == "completed"
        ]
        return ExperimentSchedulerSummary(
            queued=len(queued),
            running=len([item for item in items if item.status == "running"]),
            completed=len(completed_ids),
            failed=len(failed_ids),
            latest_results=tuple(results[-10:]),
            cumulative_utility=round(sum(utility_values), 4),
            active_provider=dict(active_provider or {}),
        )

    def _jsonable(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._jsonable(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._jsonable(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [self._jsonable(item) for item in value]
        if isinstance(value, list):
            return [self._jsonable(item) for item in value]
        return value


class ExperimentScheduler:
    """
    Run capability-specific experiments through serial provider allocation.

    The scheduler creates experiences, scores their utility, and persists
    reports. It does not promote synthetic experience directly into knowledge.
    """

    def __init__(
        self,
        *,
        store: ExperimentQueueStore,
        provider_manager: ProviderManager | None = None,
        routing_policy: ModelRoutingPolicy | None = None,
        capability_planner: CapabilityPlanner | None = None,
        novelty_analyzer: NoveltyAnalyzer | None = None,
        experience_generator: ExperienceGenerator | None = None,
        experience_store: ExperienceStore | None = None,
        allow_cloud: bool = False,
        capability_db_path: str | Path | None = None,
    ) -> None:
        self.store = store
        self.provider_manager = provider_manager or ProviderManager()
        self.routing_policy = routing_policy or ModelRoutingPolicy()
        self.capability_planner = capability_planner or CapabilityPlanner()
        self.novelty_analyzer = novelty_analyzer or NoveltyAnalyzer()
        self.experience_generator = experience_generator or ExperienceGenerator()
        self.experience_store = experience_store
        self.allow_cloud = allow_cloud
        self.capability_db_path = Path(capability_db_path) if capability_db_path else None

    def enqueue_capability_batch(
        self,
        *,
        capability: str,
        prompts: Sequence[str],
        task_type: str = "open_ended",
        provider_model: str | None = None,
        priority: int = 0,
        metadata: Mapping[str, Any] | None = None,
    ) -> list[ExperimentQueueItem]:
        now = datetime.now(timezone.utc).isoformat()
        items = [
            ExperimentQueueItem(
                item_id=str(uuid.uuid4()),
                created_at=now,
                prompt=str(prompt),
                capability=str(capability).strip().lower(),
                task_type=str(task_type),
                provider_model=provider_model,
                priority=int(priority),
                metadata=dict(metadata or {}),
            )
            for prompt in prompts
        ]
        return self.store.enqueue_many(items)

    def run_next(self, *, limit: int = 1, unload_after_batch: bool = True) -> list[ExperimentResult]:
        pending = self._pending_items()[: max(0, int(limit))]
        results: list[ExperimentResult] = []
        for item in pending:
            try:
                results.append(self._run_item(item))
            except Exception as exc:
                results.append(
                    self.store.add_result(
                        ExperimentResult(
                            item_id=item.item_id,
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            status="failed",
                            route="error",
                            provider_model=item.provider_model,
                            answer="",
                            utility_score=None,
                            information_gain_score=None,
                            surprise_score=None,
                            generated_experience_count=0,
                            metadata={"error": str(exc)},
                        )
                    )
                )
        if unload_after_batch:
            self.provider_manager.unload()
        return results

    def summary(self) -> ExperimentSchedulerSummary:
        return self.store.summary(active_provider=asdict(self.provider_manager.status()))

    def _pending_items(self) -> list[ExperimentQueueItem]:
        result_ids = {result.item_id for result in self.store.results()}
        return sorted(
            [
                item
                for item in self.store.items()
                if item.status == "queued" and item.item_id not in result_ids
            ],
            key=lambda item: (-item.priority, item.created_at, item.item_id),
        )

    def _run_item(self, item: ExperimentQueueItem) -> ExperimentResult:
        plan = self.capability_planner.plan(
            intent=item.prompt,
            task_type=item.task_type,
            required_capabilities=(item.capability,),
            metadata=item.metadata,
        )
        decision = self._route(item, plan)
        if decision.route != "local" or decision.model_name is None:
            return self.store.add_result(
                ExperimentResult(
                    item_id=item.item_id,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    status="failed",
                    route=decision.route,
                    provider_model=decision.model_name,
                    answer="",
                    utility_score=None,
                    information_gain_score=None,
                    surprise_score=None,
                    generated_experience_count=0,
                    metadata={
                        "rationale": decision.rationale,
                        "cloud_allowed": decision.cloud_allowed,
                        "capability_plan": plan.required_capabilities,
                    },
                )
            )

        inference = self.provider_manager.infer(
            model_name=decision.model_name,
            prompt=item.prompt,
            task_type=item.task_type,
            metadata={
                **item.metadata,
                "capability": item.capability,
                "route": decision.route,
            },
        )
        experiences = self.experience_generator.generate(
            request=ExperienceRequest(
                prompt=item.prompt,
                required_experience_types=("observation", "hypothesis", "prediction", "reflection"),
                source="experiment_scheduler",
                curriculum_case_id=item.item_id,
                metadata={
                    "capability": item.capability,
                    "provider_model": decision.model_name,
                },
            ),
            provider_output=inference,
        )
        if self.experience_store is not None:
            self.experience_store.add_many(experiences)

        reports = []
        for experience in experiences:
            report = self.novelty_analyzer.analyze(
                text=experience.content,
                required_capabilities=plan.required_capabilities,
                known_capabilities=("reasoning",),
            )
            reports.append(
                type(report)(
                    **{
                        **report.__dict__,
                        "metadata": {
                            **report.metadata,
                            "provider": inference.provider,
                            "model_id": inference.model_id,
                            "experiment_item_id": item.item_id,
                        },
                    }
                )
            )
        summary = self.novelty_analyzer.summarize(reports)
        return self.store.add_result(
            ExperimentResult(
                item_id=item.item_id,
                completed_at=datetime.now(timezone.utc).isoformat(),
                status="completed",
                route=decision.route,
                provider_model=decision.model_name,
                answer=inference.answer,
                utility_score=summary.get("average_experience_utility"),
                information_gain_score=summary.get("average_information_gain"),
                surprise_score=summary.get("average_surprise"),
                generated_experience_count=len(experiences),
                metadata={
                    "capability_plan": list(plan.required_capabilities),
                    "route_rationale": decision.rationale,
                    "provider": inference.provider,
                    "model_id": inference.model_id,
                    "novelty_summary": summary,
                },
            )
        )

    def _route(self, item: ExperimentQueueItem, plan) -> ModelRouteDecision:
        if item.provider_model:
            if not self._provider_is_qualified(item.provider_model):
                return ModelRouteDecision(
                    route="human_review",
                    model_name=item.provider_model,
                    rationale="Pinned provider has not passed provider qualification.",
                    metadata={"capability_plan": list(plan.required_capabilities)},
                )
            return ModelRouteDecision(
                route="local",
                model_name=item.provider_model,
                rationale="Experiment item pinned a local provider model.",
                metadata={"capability_plan": list(plan.required_capabilities)},
            )
        return self.routing_policy.decide(
            task_type=item.task_type,
            prompt=item.prompt,
            available_models=self._available_models_for_routing(),
            capability_plan=plan,
            required_capabilities=plan.required_capabilities,
            allow_cloud=self.allow_cloud,
        )

    def _available_models_for_routing(self):
        if self.capability_db_path is None or not self.capability_db_path.exists():
            return self.provider_manager.available_models
        qualified = qualified_model_names(self.capability_db_path)
        if not qualified:
            return {}
        return {
            name: spec
            for name, spec in self.provider_manager.available_models.items()
            if name in qualified or spec.name in qualified
        }

    def _provider_is_qualified(self, model_name: str) -> bool:
        if self.capability_db_path is None or not self.capability_db_path.exists():
            return True
        qualified = qualified_model_names(self.capability_db_path)
        if not qualified:
            return False
        key = str(model_name).strip().lower()
        spec = self.provider_manager.available_models.get(key)
        return key in qualified or (spec is not None and spec.name in qualified)
