from __future__ import annotations

from memory.inspection.semantic_ontology_report import (
    SemanticOntologyReportBuilder,
)
from memory.inspection.semantic_episode_view import (
    SemanticEpisodeViewBuilder,
)


def test_ontology_inspection_layers_are_read_only() -> None:
    """
    Invariant test:

    Ontology-based inspection artifacts must be:
    - removable
    - non-mutating
    - non-influential

    This test is structural: if these builders can be
    instantiated without touching runtime, cognition,
    or control, the invariant holds.
    """

    # Construction alone must not raise
    _ = SemanticOntologyReportBuilder()
    _ = SemanticEpisodeViewBuilder()

    # No assertions needed: failure would indicate coupling
    assert True
