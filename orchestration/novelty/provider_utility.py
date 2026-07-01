from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from orchestration.novelty.novelty_analyzer import NoveltyReport


@dataclass(frozen=True)
class ProviderUtilityProfile:
    provider: str
    model_id: str
    experience_count: int
    average_utility: float
    average_information_gain: float
    average_surprise: float
    average_prediction_opportunity: float
    capability_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderUtilityProfiler:
    """
    Profile providers by the utility of experiences they generate.

    This is capability evidence, not a global provider leaderboard.
    """

    def profile(
        self,
        reports: Sequence[NoveltyReport],
    ) -> list[ProviderUtilityProfile]:
        buckets: dict[tuple[str, str], list[NoveltyReport]] = {}
        for report in reports:
            provider = str(report.metadata.get("provider") or "unknown")
            model_id = str(report.metadata.get("model_id") or "unknown")
            buckets.setdefault((provider, model_id), []).append(report)

        profiles: list[ProviderUtilityProfile] = []
        for (provider, model_id), items in sorted(buckets.items()):
            profiles.append(
                ProviderUtilityProfile(
                    provider=provider,
                    model_id=model_id,
                    experience_count=len(items),
                    average_utility=self._average(
                        item.experience_utility_score for item in items
                    ),
                    average_information_gain=self._average(
                        item.information_gain_score for item in items
                    ),
                    average_surprise=self._average(item.surprise_score for item in items),
                    average_prediction_opportunity=self._average(
                        item.prediction_opportunity_score for item in items
                    ),
                    capability_scores=self._capability_scores(items),
                    metadata={
                        "method": "provider_experience_utility_v1",
                        "not_global_ranking": True,
                    },
                )
            )
        return profiles

    def rank_by_capability(
        self,
        reports: Sequence[NoveltyReport],
        *,
        capability: str,
    ) -> list[ProviderUtilityProfile]:
        normalized = str(capability).strip().lower()
        profiles = [
            profile
            for profile in self.profile(reports)
            if normalized in profile.capability_scores
        ]
        return sorted(
            profiles,
            key=lambda profile: (
                -profile.capability_scores[normalized],
                profile.provider,
                profile.model_id,
            ),
        )

    def _capability_scores(self, reports: Sequence[NoveltyReport]) -> dict[str, float]:
        buckets: dict[str, list[float]] = {}
        for report in reports:
            for capability in report.required_capabilities:
                buckets.setdefault(capability, []).append(report.experience_utility_score)
        return {
            capability: self._average(values)
            for capability, values in sorted(buckets.items())
        }

    @staticmethod
    def _average(values) -> float:
        items = [float(value) for value in values]
        if not items:
            return 0.0
        return round(sum(items) / len(items), 4)
