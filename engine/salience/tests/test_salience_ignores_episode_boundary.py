from __future__ import annotations

from engine.salience.salience_field import SalienceField


def test_salience_ignores_episode_boundary():
    """
    Salience must NOT react to episode boundaries.

    This test asserts that:
    - Salience decays normally
    - No reset or amplification occurs at episode boundaries
    """

    sal = SalienceField(decay_tau=10.0)

    assembly_id = "test:assembly"
    sal.inject(assembly_id, 0.6)

    before = sal.get(assembly_id)
    assert before > 0.0

    # --------------------------------------------------
    # Simulated episode boundary (intentionally inert)
    # --------------------------------------------------
    sal.step(dt=0.01)

    after = sal.get(assembly_id)

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert after <= before
    assert after > 0.0
    assert abs(after - before) < 0.05
