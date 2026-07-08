from __future__ import annotations

from orchestration.runtime.rc2_concept_growth_run import make_candidate, quality_check


def test_growth_candidate_uses_semantic_related_concepts_for_diet():
    candidate = make_candidate("nutrition", "calorie budgeting")
    ok, reasons, score = quality_check(candidate)

    assert ok is True
    assert reasons == []
    assert score == 1.0
    assert "meal planning" in candidate["related_concepts"]
    assert "calorie budgeting" in candidate["related_concepts"]
    assert "nutrition planning" in candidate["related_concepts"]
    for bad in {"monday", "breakfast", "yogurt", "calorie", "every"}:
        assert bad not in candidate["related_concepts"]


def test_growth_candidate_rejects_vague_keyword_concept():
    candidate = {
        **make_candidate("planning productivity", "task decomposition"),
        "concept_name": "What",
        "related_concepts": ["monday", "breakfast", "yogurt"],
    }

    ok, reasons, score = quality_check(candidate)

    assert ok is False
    assert "concept_name_too_short" in reasons
    assert "bad_related_concepts" in reasons
    assert score < 1.0
