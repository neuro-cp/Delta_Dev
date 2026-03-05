from __future__ import annotations

from memory.influence_eligibility.eligibility_scope import (
    ELIGIBLE_ARTIFACT_TYPES,
)


def test_scope_contains_expected_artifact_types() -> None:
    assert ELIGIBLE_ARTIFACT_TYPES == {
        "semantic_grounding",
        "semantic_assembly_hypothesis",
        "semantic_activation_summary",
        "inspection_diff",
    }


def test_scope_excludes_runtime_and_decision_artifacts() -> None:
    forbidden = {
        "runtime",
        "decision",
        "value",
        "salience",
        "routing",
        "learning",
    }

    assert ELIGIBLE_ARTIFACT_TYPES.isdisjoint(forbidden)
