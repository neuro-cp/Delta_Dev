from __future__ import annotations

from tools.phase27_knowledge_maturation_audit import (
    _lifespan_summary,
    _prediction_taxonomy,
    _promotion_velocity,
    _redundancy_taxonomy,
)


def test_phase27_taxonomy_classifies_unvisited_late_and_quality_blocked_predictions():
    decisions_by_id = {
        "old": {
            "concept_id": "old",
            "dimensions": {"redundancy_penalty": 0.0, "prompt_artifact_penalty": 0.0},
            "evidence": {"open_contradictions": 0},
        },
        "late": {
            "concept_id": "late",
            "dimensions": {"redundancy_penalty": 0.0, "prompt_artifact_penalty": 0.0},
            "evidence": {"open_contradictions": 0},
        },
        "redundant": {
            "concept_id": "redundant",
            "dimensions": {"redundancy_penalty": 0.5, "prompt_artifact_penalty": 0.0},
            "evidence": {"open_contradictions": 0},
        },
    }
    predictions = [
        {"prediction_id": "p-old", "source_concept_id": "old", "status": "open", "metadata": {}},
        {"prediction_id": "p-late", "source_concept_id": "late", "status": "open", "metadata": {}},
        {
            "prediction_id": "p-redundant",
            "source_concept_id": "redundant",
            "status": "open",
            "metadata": {"validation": {"outcome": "open"}},
        },
    ]

    taxonomy = _prediction_taxonomy(
        predictions=predictions,
        decisions_by_id=decisions_by_id,
        concept_ticks={"old": 10, "late": 90, "redundant": 20},
        max_tick=100,
    )

    assert taxonomy["never_revisited"] == 1
    assert taxonomy["late_cycle_backlog"] == 1
    assert taxonomy["blocked_by_redundancy"] == 1


def test_phase27_velocity_and_lifespan_are_report_only_derivations():
    decisions = [
        {"concept_id": "a", "recommendation": "Promotion Eligible"},
        {"concept_id": "b", "recommendation": "Validated"},
        {"concept_id": "c", "recommendation": "Reject"},
    ]
    ticks = {"a": 10, "b": 40, "c": 90}

    velocity = _promotion_velocity(decisions=decisions, concept_ticks=ticks, max_tick=100)
    lifespan = _lifespan_summary(decisions=decisions, concept_ticks=ticks, max_tick=100)

    assert any(row["cycle"] == 50 and row["promotion_eligible"] == 1 for row in velocity)
    assert lifespan["survival_by_age"][0]["survivors"] == 2


def test_phase27_redundancy_taxonomy_distinguishes_reusable_overlap():
    decisions = [
        {
            "concept": "Evidence supports planning",
            "recommendation": "Validated",
            "dimensions": {"redundancy_penalty": 0.25},
        },
        {
            "concept": "Evidence supports planning",
            "recommendation": "Candidate",
            "dimensions": {"redundancy_penalty": 0.25},
        },
        {
            "concept": "Another overlapping planning concept",
            "recommendation": "Reject",
            "dimensions": {"redundancy_penalty": 0.55},
        },
    ]

    taxonomy = _redundancy_taxonomy(decisions)

    assert taxonomy["exact_duplicate_text"] == 2
    assert taxonomy["high_paraphrase_overlap"] == 1
