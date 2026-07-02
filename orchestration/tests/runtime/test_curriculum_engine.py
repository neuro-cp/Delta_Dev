from __future__ import annotations

from orchestration.curriculum import (
    CalibrationCurriculumGenerator,
    CurriculumEngine,
    CurriculumPerformance,
    broad_profile_names,
)
from orchestration.curriculum.broad_corpus import generate_broad_corpus
from orchestration.evaluation import CognitiveEvaluationResult


def test_curriculum_generates_structured_experience_not_knowledge():
    cases = CurriculumEngine().generate_sequence(
        count=3,
        domains=("arithmetic", "contradiction"),
    )

    assert [case.domain for case in cases] == [
        "arithmetic",
        "contradiction",
        "arithmetic",
    ]
    assert cases[0].difficulty == 1
    assert "mathematics" in cases[0].required_capabilities
    evaluation_case = cases[0].to_evaluation_case()
    assert evaluation_case.category == "arithmetic"
    assert evaluation_case.metadata["experience_type"] == "curriculum_task"
    assert evaluation_case.metadata["direct_knowledge_promotion"] is False


def test_curriculum_prioritizes_weak_domains_and_adapts_difficulty():
    cases = CurriculumEngine().generate_sequence(
        count=2,
        domains=("logic", "planning"),
        performance=(
            CurriculumPerformance(domain="logic", attempts=5, pass_rate=0.2),
            CurriculumPerformance(domain="planning", attempts=5, pass_rate=0.9),
        ),
    )

    assert cases[0].domain == "logic"
    assert cases[0].difficulty == 1
    assert cases[1].domain == "planning"
    assert cases[1].difficulty == 3


def test_curriculum_derives_performance_from_evaluation_results():
    engine = CurriculumEngine()
    performance = engine.performance_from_results(
        [
            CognitiveEvaluationResult(
                case_id="logic-1",
                category="logic",
                route_type="deterministic",
                success=True,
                confidence=0.8,
                latency_seconds=0.1,
                memory_count=1,
                relationship_count=1,
                learning_count=1,
                stage_count=4,
                passed=True,
            ),
            CognitiveEvaluationResult(
                case_id="logic-2",
                category="logic",
                route_type="deterministic",
                success=False,
                confidence=0.4,
                latency_seconds=0.3,
                memory_count=1,
                relationship_count=1,
                learning_count=1,
                stage_count=4,
                passed=False,
            ),
        ]
    )

    assert performance == [
        CurriculumPerformance(
            domain="logic",
            attempts=2,
            pass_rate=0.5,
            average_confidence=0.6,
            average_latency_seconds=0.2,
        )
    ]


def test_calibration_curriculum_selects_high_pressure_experiences():
    objectives = CalibrationCurriculumGenerator().generate(count=25)

    assert len(objectives) == 25
    assert all(item.calibration_score >= 0.4 for item in objectives)
    assert any(
        "prediction_pressure" in item.objective.expected_signals
        for item in objectives
    )
    assert any(
        "belief_revision" in item.objective.expected_signals
        or "contradiction_resolution" in item.objective.expected_signals
        for item in objectives
    )
    assert objectives == sorted(
        objectives,
        key=lambda item: (
            -item.calibration_score,
            item.objective.capability,
            item.objective.objective_id,
        ),
    )


def test_calibration_curriculum_penalizes_repetition():
    generator = CalibrationCurriculumGenerator()
    first = generator.generate(count=1)
    repeated = generator.generate(
        count=1,
        previous_prompts=[first[0].objective.prompt],
        min_utility=0.0,
    )

    assert repeated[0].objective.objective_id != first[0].objective.objective_id


def test_calibration_curriculum_filters_profiles():
    objectives = CalibrationCurriculumGenerator().generate(
        count=6,
        profiles=("scientific_reasoning",),
    )

    assert objectives
    assert all(
        item.objective.capability == "scientific_reasoning"
        or "scientific_reasoning" in item.objective.metadata.get("profiles", ())
        for item in objectives
    )


def test_calibration_curriculum_has_high_friction_profiles():
    generator = CalibrationCurriculumGenerator()

    for profile in (
        "contradiction",
        "planning",
        "causal_reasoning",
        "scientific_reasoning",
        "tool_use",
        "long_dependency",
    ):
        objectives = generator.generate(count=2, profiles=(profile,))
        assert objectives, profile


def test_broad_corpus_has_at_least_100_objectives_per_profile():
    corpus = generate_broad_corpus(minimum_per_profile=100)

    for profile in broad_profile_names():
        matching = [
            objective
            for objective in corpus
            if profile in objective.metadata.get("profiles", ())
        ]
        assert len(matching) >= 100, profile


def test_calibration_curriculum_can_select_broad_profiles():
    objectives = CalibrationCurriculumGenerator().generate(
        count=25,
        profiles=("probabilistic_reasoning", "systems_engineering"),
    )

    assert len(objectives) == 25
    assert {
        item.objective.metadata.get("profiles", ("",))[0]
        for item in objectives
    }.issubset({"probabilistic_reasoning", "systems_engineering"})
