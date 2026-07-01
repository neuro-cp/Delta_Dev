from __future__ import annotations

from knowledge import PredictionRecord, SemanticKnowledgeRecord
from memory.persistent import MemoryRecord
from orchestration.novelty import NoveltyAnalyzer


def _memory(text: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id="memory-1",
        created_at="2026-06-30T00:00:00+00:00",
        kind="observation",
        text=text,
        source="test",
        layer="experience",
        confidence=1.0,
        tags=[],
        metadata={},
    )


def _knowledge(text: str) -> SemanticKnowledgeRecord:
    return SemanticKnowledgeRecord(
        concept_id="concept-1",
        created_at="2026-06-30T00:00:00+00:00",
        updated_at="2026-06-30T00:00:00+00:00",
        concept="job completion",
        definition=text,
        confidence=0.8,
    )


def test_repeated_experience_has_low_novelty():
    report = NoveltyAnalyzer().analyze(
        text="Solve an arithmetic task at difficulty 1 and explain the steps.",
        memories=[
            _memory("Solve an arithmetic task at difficulty 1 and explain the steps.")
        ],
        knowledge=[],
        required_capabilities=("mathematics", "reasoning"),
        known_capabilities=("mathematics", "reasoning"),
    )

    assert report.novelty_score < 0.2
    assert report.information_gain_score < 0.2
    assert report.experience_utility_score < 0.2
    assert report.worth_remembering is False


def test_contradictory_evidence_challenges_existing_belief():
    report = NoveltyAnalyzer().analyze(
        text="Job #42 did not complete after inspection.",
        knowledge=[_knowledge("Job #42 completed after inspection.")],
        required_capabilities=("reasoning",),
        known_capabilities=("reasoning",),
    )

    assert report.challenges_existing_belief is True
    assert report.invalidation_pressure is True
    assert report.belief_challenge_score == 1.0
    assert report.surprise_score > 0
    assert report.information_gain_score > 0.4
    assert report.worth_remembering is True


def test_new_capability_increases_novelty_pressure():
    report = NoveltyAnalyzer().analyze(
        text="Analyze the spatial layout in this image.",
        required_capabilities=("vision", "spatial_reasoning"),
        known_capabilities=("reasoning",),
    )

    assert report.requires_new_capability is True
    assert report.novelty_score > 0.8
    assert report.capability_expansion_score == 1.0
    assert report.experience_utility_score > 0.3
    assert report.worth_remembering is True


def test_high_information_gain_for_planning_failure_under_uncertainty():
    report = NoveltyAnalyzer().analyze(
        text="Current planning strategy consistently fails under uncertainty and will need revision.",
        memories=[_memory("Create a bounded plan for a task at difficulty 1.")],
        required_capabilities=("planning", "reflection", "prediction"),
        known_capabilities=("planning", "reasoning"),
    )

    assert report.prediction_opportunity_score == 1.0
    assert report.invalidation_pressure is True
    assert report.surprise_score > 0
    assert report.information_gain_score > 0.5
    assert report.experience_utility_score > 0.5


def test_failed_high_confidence_prediction_creates_high_surprise():
    report = NoveltyAnalyzer().analyze(
        text="Job #42 did not complete after inspection.",
        predictions=[
            PredictionRecord(
                prediction_id="prediction-1",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="concept-1",
                expectation="Job #42 will complete after inspection.",
                confidence=0.95,
                status="failed",
            )
        ],
        required_capabilities=("reasoning", "prediction"),
        known_capabilities=("reasoning", "prediction"),
    )

    assert report.surprise_score >= 0.9
    assert report.information_gain_score > 0.4
    assert report.experience_utility_score > 0.5


def test_provider_disagreement_adds_surprise_pressure():
    report = NoveltyAnalyzer().analyze(
        text="Two trusted providers disagree while using identical evidence.",
        required_capabilities=("reasoning", "reflection"),
        known_capabilities=("reasoning", "reflection"),
    )

    assert report.surprise_score >= 0.35
    assert report.worth_remembering is True


def test_novelty_summary_reports_pressure_rates():
    analyzer = NoveltyAnalyzer()
    reports = [
        analyzer.analyze(text="Known task", memories=[_memory("Known task")]),
        analyzer.analyze(text="This will produce a prediction."),
    ]
    summary = analyzer.summarize(reports)

    assert summary["count"] == 2
    assert summary["average_information_gain"] is not None
    assert summary["average_surprise"] is not None
    assert summary["average_experience_utility"] is not None
    assert summary["prediction_pressure_rate"] == 0.5
