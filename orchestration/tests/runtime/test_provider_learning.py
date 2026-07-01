from __future__ import annotations

from integration.model_runtime import ModelInferenceRecord, ProviderLearningEngine


def _record(
    *,
    model_id: str,
    confidence: float,
    latency: float,
    evidence_count: int,
    capabilities: list[str],
) -> ModelInferenceRecord:
    return ModelInferenceRecord(
        inference_id=f"id-{model_id}-{confidence}-{latency}",
        created_at="2026-06-30T00:00:00+00:00",
        provider="local_gguf",
        model_id=model_id,
        route="local",
        task_type="open_ended",
        prompt_tokens=10,
        response_tokens=10,
        latency_seconds=latency,
        confidence=confidence,
        evidence_count=evidence_count,
        metadata={"required_capabilities": capabilities},
    )


def test_provider_learning_profiles_observed_records_by_model():
    profiles = ProviderLearningEngine().profiles(
        [
            _record(
                model_id="phi4",
                confidence=0.8,
                latency=2.0,
                evidence_count=3,
                capabilities=["coding"],
            ),
            _record(
                model_id="phi4",
                confidence=0.6,
                latency=4.0,
                evidence_count=1,
                capabilities=["coding"],
            ),
        ]
    )

    assert len(profiles) == 1
    assert profiles[0].model_id == "phi4"
    assert profiles[0].observations == 2
    assert profiles[0].average_confidence == 0.7
    assert profiles[0].average_latency_seconds == 3.0
    assert "coding" in profiles[0].capability_scores


def test_provider_learning_ranks_by_observed_capability_score_not_name():
    records = [
        _record(
            model_id="alpha",
            confidence=0.9,
            latency=1.0,
            evidence_count=5,
            capabilities=["planning"],
        ),
        _record(
            model_id="zeta",
            confidence=0.5,
            latency=1.0,
            evidence_count=1,
            capabilities=["planning"],
        ),
    ]

    ranked = ProviderLearningEngine().rank_for_capability(
        records,
        capability="planning",
    )

    assert [profile.model_id for profile in ranked] == ["alpha", "zeta"]


def test_provider_learning_requires_observed_capability():
    records = [
        _record(
            model_id="phi4",
            confidence=0.9,
            latency=1.0,
            evidence_count=5,
            capabilities=["coding"],
        )
    ]

    ranked = ProviderLearningEngine().rank_for_capability(
        records,
        capability="vision",
    )

    assert ranked == []
