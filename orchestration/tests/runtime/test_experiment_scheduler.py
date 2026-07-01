from __future__ import annotations

import json

from integration.model_runtime import CanonicalInferenceResult, ProviderManager
from integration.model_runtime.model_registry import ModelSpec
from orchestration.experiments import ExperimentQueueStore, ExperimentScheduler


def _spec(name: str, family: str):
    return ModelSpec(
        name=name,
        path=f"/models/{name}.gguf",
        tier=1,
        description=name,
        context_length=4096,
        family=family,
        quantization="Q4",
        size_bytes=100,
    )


class FakeRunner:
    def __init__(self, model_id: str):
        self.model_id = model_id

    def produce_output(self, input_payload):
        prompt = input_payload["prompt"]
        answer = (
            "Unexpected provider disagreement will challenge the current planning "
            f"belief for {prompt}."
        )
        return CanonicalInferenceResult(
            provider="local_gguf",
            model_id=self.model_id,
            answer=answer,
            raw_output=answer,
            confidence=0.75,
            latency_seconds=0.01,
            prompt_tokens=len(prompt.split()),
            response_tokens=len(answer.split()),
        )


def test_experiment_scheduler_runs_queued_item_and_scores_utility(tmp_path):
    provider_manager = ProviderManager(
        available_models={"phi4": _spec("phi4", "phi4")},
        runner_factory=lambda spec: FakeRunner(spec.name),
    )
    scheduler = ExperimentScheduler(
        store=ExperimentQueueStore(
            tmp_path / "experiment_queue.jsonl",
            tmp_path / "experiment_results.jsonl",
        ),
        provider_manager=provider_manager,
    )
    scheduler.enqueue_capability_batch(
        capability="planning",
        task_type="planning",
        prompts=["Revise a plan after new evidence contradicts it."],
        provider_model="phi4",
    )

    results = scheduler.run_next(limit=1)
    summary = scheduler.summary()

    assert len(results) == 1
    assert results[0].status == "completed"
    assert results[0].provider_model == "phi4"
    assert results[0].generated_experience_count == 4
    assert results[0].utility_score is not None
    assert summary.completed == 1
    assert summary.queued == 0
    assert summary.cumulative_utility > 0


def test_experiment_scheduler_rejects_unqualified_pinned_provider(tmp_path):
    capability_db = tmp_path / "provider_capabilities.json"
    capability_db.write_text(
        json.dumps({"phi4": {"qualified": False}}),
        encoding="utf-8",
    )
    provider_manager = ProviderManager(
        available_models={"phi4": _spec("phi4", "phi4")},
        runner_factory=lambda spec: FakeRunner(spec.name),
    )
    scheduler = ExperimentScheduler(
        store=ExperimentQueueStore(
            tmp_path / "experiment_queue.jsonl",
            tmp_path / "experiment_results.jsonl",
        ),
        provider_manager=provider_manager,
        capability_db_path=capability_db,
    )
    scheduler.enqueue_capability_batch(
        capability="planning",
        task_type="planning",
        prompts=["Run only if qualified."],
        provider_model="phi4",
    )

    results = scheduler.run_next(limit=1)

    assert results[0].status == "failed"
    assert results[0].route == "human_review"
    assert "qualification" in results[0].metadata["rationale"]
