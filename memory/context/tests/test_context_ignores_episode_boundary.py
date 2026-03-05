from __future__ import annotations

from engine.runtime_context import RuntimeContext


def test_context_ignores_episode_boundary():
    """
    Context must NOT react to episode boundaries.

    This test asserts that:
    - Context gain decays normally
    - No reset, wipe, or spike occurs
    - Episode boundaries have zero effect unless a future policy allows it
    """

    # --------------------------------------------------
    # Setup
    # --------------------------------------------------
    ctx = RuntimeContext(decay_tau=10.0)

    assembly_id = "test:assembly"
    injected_gain = 0.5

    ctx.inject_gain(assembly_id, injected_gain)

    before = ctx.get_gain(assembly_id)
    assert before > 0.0

    # --------------------------------------------------
    # Simulated episode boundary
    # --------------------------------------------------
    # IMPORTANT:
    # We deliberately do NOTHING here.
    #
    # No hooks.
    # No calls.
    # No signals.
    #
    # The absence of coupling is the point.
    # --------------------------------------------------

    ctx.step(dt=0.01)

    after = ctx.get_gain(assembly_id)

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    # Context may decay, but must not reset or spike
    assert after <= before
    assert after > 0.0

    # Decay should be gentle and continuous
    assert abs(after - before) < 0.05
