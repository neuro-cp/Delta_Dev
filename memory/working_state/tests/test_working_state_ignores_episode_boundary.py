from __future__ import annotations

from memory.working_state.pfc_adapter import PFCAdapter


def test_working_state_ignores_episode_boundary():
    """
    Working state must NOT disengage on episode boundaries.

    Engagement and decay behavior must remain unchanged
    unless an explicit reset policy exists.
    """

    pfc = PFCAdapter(enable=True)

    # Simulate post-decision engagement
    pfc.ingest_decision(
        {
            "commit": True,
            "winner": "D1",
            "confidence": 0.8,
        }
    )

    assert pfc.is_engaged()

    before = pfc.strength()
    assert before > 0.0

    # --------------------------------------------------
    # Simulated episode boundary (no-op)
    # --------------------------------------------------
    pfc.step(dt=0.01)

    after = pfc.strength()

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert pfc.is_engaged()
    assert after <= before
    assert abs(after - before) < 0.05
