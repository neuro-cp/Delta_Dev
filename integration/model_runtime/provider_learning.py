from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from integration.model_runtime.model_observatory import ModelInferenceRecord


@dataclass(frozen=True)
class ProviderPerformanceProfile:
    provider: str
    model_id: str
    observations: int
    average_latency_seconds: float
    average_confidence: float
    average_evidence_count: float
    capability_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderLearningEngine:
    """
    Derive provider effectiveness from observed inference records.

    This is observational. It does not create permanent provider preferences
    and does not grant providers authority over Delta cognition.
    """

    def profiles(
        self,
        records: Iterable[ModelInferenceRecord],
    ) -> list[ProviderPerformanceProfile]:
        buckets: dict[tuple[str, str], list[ModelInferenceRecord]] = {}
        for record in records:
            buckets.setdefault((record.provider, record.model_id), []).append(record)

        profiles: list[ProviderPerformanceProfile] = []
        for (provider, model_id), items in sorted(buckets.items()):
            observations = len(items)
            latency = sum(item.latency_seconds for item in items) / observations
            confidence = sum(item.confidence for item in items) / observations
            evidence = sum(item.evidence_count for item in items) / observations
            profiles.append(
                ProviderPerformanceProfile(
                    provider=provider,
                    model_id=model_id,
                    observations=observations,
                    average_latency_seconds=round(latency, 4),
                    average_confidence=round(confidence, 4),
                    average_evidence_count=round(evidence, 4),
                    capability_scores=self._capability_scores(items),
                    metadata={"source": "inference_observatory"},
                )
            )
        return profiles

    def rank_for_capability(
        self,
        records: Iterable[ModelInferenceRecord],
        *,
        capability: str,
        min_observations: int = 1,
    ) -> list[ProviderPerformanceProfile]:
        normalized = str(capability).strip().lower()
        profiles = [
            profile
            for profile in self.profiles(records)
            if profile.observations >= min_observations
            and normalized in profile.capability_scores
        ]
        return sorted(
            profiles,
            key=lambda profile: (
                -profile.capability_scores[normalized],
                profile.average_latency_seconds,
                profile.model_id,
            ),
        )

    def _capability_scores(
        self,
        records: list[ModelInferenceRecord],
    ) -> dict[str, float]:
        buckets: dict[str, list[ModelInferenceRecord]] = {}
        for record in records:
            for capability in self._record_capabilities(record):
                buckets.setdefault(capability, []).append(record)

        scores: dict[str, float] = {}
        for capability, items in sorted(buckets.items()):
            scores[capability] = round(
                sum(self._score(item) for item in items) / len(items),
                4,
            )
        return scores

    def _record_capabilities(self, record: ModelInferenceRecord) -> tuple[str, ...]:
        raw = record.metadata.get("required_capabilities", ())
        if isinstance(raw, str):
            raw = [raw]
        capabilities = []
        for item in raw:
            normalized = str(item).strip().lower()
            if normalized and normalized not in capabilities:
                capabilities.append(normalized)
        if not capabilities:
            capabilities.append(str(record.task_type).strip().lower() or "open_ended")
        return tuple(capabilities)

    def _score(self, record: ModelInferenceRecord) -> float:
        confidence = max(0.0, min(1.0, float(record.confidence)))
        evidence = min(1.0, float(record.evidence_count) / 5.0)
        latency_penalty = min(0.5, max(0.0, float(record.latency_seconds)) / 20.0)
        return max(0.0, confidence * 0.7 + evidence * 0.3 - latency_penalty)
