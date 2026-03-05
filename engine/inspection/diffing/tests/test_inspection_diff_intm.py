from __future__ import annotations

"""
Intermediate certification test: inspection diffing.

Verifies:
- Hypothesis appearance / disappearance is detected
- Stabilization deltas are captured
- DiffRunner produces a coherent DiffReport
- No runtime, replay, or cognition authority is involved
"""

from engine.inspection.diffing.diff_runner import DiffRunner
from engine.inspection.diffing.hypothesis_timeline_diff import HypothesisSummary


def test_inspection_diff_intermediate() -> None:
    """
    This test simulates two offline cognition inspection snapshots
    and verifies that the diffing layer detects meaningful changes.
    """

    # --------------------------------------------------
    # BEFORE snapshot (earlier cognition state)
    # --------------------------------------------------
    before = {
        "H1": HypothesisSummary(
            hypothesis_id="H1",
            stabilized=False,
            stabilization_step=None,
            peak_activation=0.42,
        ),
        "H2": HypothesisSummary(
            hypothesis_id="H2",
            stabilized=True,
            stabilization_step=50,
            peak_activation=0.88,
        ),
    }

    # --------------------------------------------------
    # AFTER snapshot (later cognition state)
    # --------------------------------------------------
    after = {
        # H1 now stabilizes later
        "H1": HypothesisSummary(
            hypothesis_id="H1",
            stabilized=True,
            stabilization_step=60,
            peak_activation=0.60,
        ),
        # H2 disappears entirely
        # New hypothesis H3 appears
        "H3": HypothesisSummary(
            hypothesis_id="H3",
            stabilized=False,
            stabilization_step=None,
            peak_activation=0.30,
        ),
    }

    # --------------------------------------------------
    # Run diff
    # --------------------------------------------------
    runner = DiffRunner()
    report = runner.diff_hypothesis_summaries(
        before=before,
        after=after,
    )

    # --------------------------------------------------
    # Assertions: high-level flags
    # --------------------------------------------------
    assert report.cognition_changed is True
    assert report.replay_changed is False
    assert report.hypothesis_diff is not None

    diff = report.hypothesis_diff

    # --------------------------------------------------
    # Assertions: identity changes
    # --------------------------------------------------
    assert diff.appeared == ["H3"]
    assert diff.disappeared == ["H2"]

    # --------------------------------------------------
    # Assertions: stabilization changes
    # --------------------------------------------------
    assert "H1" in diff.stabilization_changes
    assert diff.stabilization_changes["H1"]["before"] is None
    assert diff.stabilization_changes["H1"]["after"] == 60

    # --------------------------------------------------
    # Assertions: peak activation changes
    # --------------------------------------------------
    assert "H1" in diff.peak_activation_changes
    assert diff.peak_activation_changes["H1"]["before"] == 0.42
    assert diff.peak_activation_changes["H1"]["after"] == 0.60

    print("\n=== INSPECTION DIFF (INTERMEDIATE) ===")
    print("Appeared:", diff.appeared)
    print("Disappeared:", diff.disappeared)
    print("Stabilization delta:", diff.stabilization_changes)
    print("Peak activation delta:", diff.peak_activation_changes)
