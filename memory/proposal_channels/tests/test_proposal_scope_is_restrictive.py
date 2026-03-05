from __future__ import annotations

from memory.proposal_channels.proposal_scope import (
    ALLOWED_PROPOSAL_SOURCES,
)


def test_allowed_proposal_sources_are_exact() -> None:
    assert ALLOWED_PROPOSAL_SOURCES == {
        "semantic_grounding",
        "semantic_assembly_hypothesis",
        "semantic_activation_summary",
    }


def test_scope_excludes_runtime_and_decision_sources() -> None:
    forbidden = {
        "runtime",
        "decision",
        "value",
        "salience",
        "routing",
        "learning",
        "replay",
    }

    assert ALLOWED_PROPOSAL_SOURCES.isdisjoint(forbidden)
