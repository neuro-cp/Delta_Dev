from __future__ import annotations

from orchestration.attention import AttentionItem
from orchestration.reflection import ReflectionEngine
from learning.region import LearningEngine


def test_reflection_quality_scores_rich_successful_reflection():
    reflection = ReflectionEngine().reflect(
        prompt="Compare memory and attention",
        output="comparison complete",
        success=True,
        attended_items=[
            AttentionItem(
                item_id="m1",
                source="memory",
                text="memory context",
                score=0.8,
                factors={"task_relevance": 0.8},
            )
        ],
        memory_ids=["m1", "m2"],
        working_memory_summary={"item_count": 2},
    )

    quality = reflection.metadata["quality"]

    assert quality["score"] == 1.0
    assert quality["method"] == "reflection_quality_v1"
    assert quality["dimensions"]["working_memory_observed"] is True
    assert quality["dimensions"]["repetition_detected"] is True


def test_reflection_quality_scores_sparse_failed_reflection_lower():
    reflection = ReflectionEngine().reflect(
        prompt="",
        output="",
        success=False,
        attended_items=[],
        memory_ids=[],
        working_memory_summary={},
    )

    quality = reflection.metadata["quality"]

    assert quality["score"] == 0.0
    assert all(value is False for value in quality["dimensions"].values())


def test_learning_record_preserves_reflection_quality_metadata():
    reflection = ReflectionEngine().reflect(
        prompt="Compare memory and attention",
        output="comparison complete",
        success=True,
        attended_items=[],
        memory_ids=["m1"],
        working_memory_summary={"item_count": 1},
    )

    learning = LearningEngine().learn(
        cycle_id="cycle-1",
        prompt="Compare memory and attention",
        output="comparison complete",
        success=True,
        attended_items=[],
        reflection=reflection,
    )

    assert learning.metadata["reflection_quality"]["method"] == "reflection_quality_v1"


def test_learning_extracts_reusable_semantic_claims_from_output():
    reflection = ReflectionEngine().reflect(
        prompt="Revise inventory prediction confidence.",
        output=(
            "When inventory variance exceeds expected demand, prediction "
            "confidence should decrease. Conflicting policies require evidence "
            "ranking before action selection."
        ),
        success=True,
        attended_items=[],
        memory_ids=["prompt-memory", "output-memory"],
        working_memory_summary={"item_count": 1},
    )

    learning = LearningEngine().learn(
        cycle_id="cycle-claims",
        prompt="Revise inventory prediction confidence.",
        output=(
            "When inventory variance exceeds expected demand, prediction "
            "confidence should decrease. Conflicting policies require evidence "
            "ranking before action selection."
        ),
        success=True,
        attended_items=[],
        reflection=reflection,
    )

    candidate_texts = [candidate.text for candidate in learning.semantic_candidates]

    assert any("prediction confidence should decrease" in text for text in candidate_texts)
    assert any("evidence ranking" in text for text in candidate_texts)
    assert all("Repeated attended context" not in text for text in candidate_texts)
    assert learning.semantic_candidates[0].evidence_memory_ids == [
        "prompt-memory",
        "output-memory",
    ]


def test_learning_keeps_repeated_context_as_fallback_only():
    attended = [
        AttentionItem(
            item_id="m1",
            source="memory",
            text="prior context",
            score=0.8,
            factors={"task_relevance": 0.8},
        )
    ]
    reflection = ReflectionEngine().reflect(
        prompt="Compare prior context.",
        output="ok",
        success=True,
        attended_items=attended,
        memory_ids=["m1"],
        working_memory_summary={"item_count": 1},
    )

    learning = LearningEngine().learn(
        cycle_id="cycle-fallback",
        prompt="Compare prior context.",
        output="ok",
        success=True,
        attended_items=attended,
        reflection=reflection,
    )

    assert learning.semantic_candidates
    assert learning.semantic_candidates[0].text.startswith("Repeated attended context")
