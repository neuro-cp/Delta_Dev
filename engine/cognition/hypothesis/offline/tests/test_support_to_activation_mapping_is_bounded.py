from __future__ import annotations

import math

from engine.cognition.hypothesis.offline.support_to_activation import SupportToActivation


def test_support_to_activation_mapping_is_bounded() -> None:
    """
    Phase 6 certification test.

    Verifies:
    - mapping is monotonic
    - activation is bounded in [0, 1]
    - mapping is stable for extreme values
    - no NaN or Inf propagation occurs

    This test certifies SupportToActivation as a safe, deterministic,
    offline-only shaping adapter.
    """

    mapper = SupportToActivation(
        gain=5.0,
        midpoint=0.4,
        max_activation=1.0,
    )

    # --------------------------------------------------
    # 1. Extreme negative support
    # --------------------------------------------------

    act = mapper.map(-1e6)
    assert math.isfinite(act)
    assert 0.0 <= act <= 1.0

    # --------------------------------------------------
    # 2. Zero support
    # --------------------------------------------------

    act = mapper.map(0.0)
    assert math.isfinite(act)
    assert 0.0 <= act <= 1.0

    # --------------------------------------------------
    # 3. Midpoint support
    # --------------------------------------------------

    act_mid = mapper.map(0.4)
    assert math.isfinite(act_mid)
    assert 0.0 < act_mid < 1.0

    # --------------------------------------------------
    # 4. Large positive support
    # --------------------------------------------------

    act = mapper.map(1e6)
    assert math.isfinite(act)
    assert act == 1.0  # saturates cleanly

    # --------------------------------------------------
    # 5. Monotonicity check
    # --------------------------------------------------

    supports = [-1.0, 0.0, 0.2, 0.4, 0.6, 1.0, 2.0]
    activations = [mapper.map(s) for s in supports]

    for a, b in zip(activations, activations[1:]):
        assert b >= a

    # --------------------------------------------------
    # 6. Defensive behavior for non-finite input
    # --------------------------------------------------

    assert mapper.map(float("inf")) == 0.0
    assert mapper.map(float("-inf")) == 0.0
    assert mapper.map(float("nan")) == 0.0
