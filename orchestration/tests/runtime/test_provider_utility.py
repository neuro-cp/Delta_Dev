from __future__ import annotations

from orchestration.novelty import NoveltyAnalyzer, ProviderUtilityProfiler


def _report(provider: str, model_id: str, text: str, capabilities: tuple[str, ...]):
    report = NoveltyAnalyzer().analyze(
        text=text,
        required_capabilities=capabilities,
        known_capabilities=("reasoning",),
    )
    return type(report)(
        **{
            **report.__dict__,
            "metadata": {
                **report.metadata,
                "provider": provider,
                "model_id": model_id,
            },
        }
    )


def test_provider_utility_profiles_experience_utility_without_global_ranking():
    reports = [
        _report(
            "local_gguf",
            "phi4",
            "Current planning strategy fails under uncertainty and will need revision.",
            ("planning", "prediction"),
        ),
        _report(
            "local_gguf",
            "qwen",
            "Known task",
            ("translation",),
        ),
    ]

    profiles = ProviderUtilityProfiler().profile(reports)

    assert len(profiles) == 2
    assert all(profile.metadata["not_global_ranking"] is True for profile in profiles)
    assert profiles[0].experience_count == 1


def test_provider_utility_ranks_within_capability_only():
    reports = [
        _report(
            "local_gguf",
            "phi4",
            "Current planning strategy fails under uncertainty and will need revision.",
            ("planning",),
        ),
        _report(
            "local_gguf",
            "qwen",
            "Create a bounded plan for a task at difficulty 1.",
            ("planning",),
        ),
    ]

    ranked = ProviderUtilityProfiler().rank_by_capability(
        reports,
        capability="planning",
    )

    assert [profile.model_id for profile in ranked] == ["phi4", "qwen"]
    assert ranked[0].capability_scores["planning"] > ranked[1].capability_scores["planning"]
