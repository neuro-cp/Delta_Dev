from __future__ import annotations

import pytest

from engine.cognition.hypothesis import Hypothesis
from engine.cognition.hypothesis_dynamics import HypothesisDynamics


# ============================================================
# Test: activation decays over time
# ============================================================

def test_activation_decays():
    h = Hypothesis(
        hypothesis_id="H-decay",
        created_step=0,
        activation=1.0,
    )

    dyn = HypothesisDynamics(decay_rate=0.1)

    dyn.step([h])

    assert 0.0 < h.activation < 1.0
    assert h.active is True


# ============================================================
# Test: repeated decay deactivates hypothesis
# ============================================================

def test_decay_deactivates_hypothesis():
    h = Hypothesis(
        hypothesis_id="H-deactivate",
        created_step=0,
        activation=0.05,
    )

    dyn = HypothesisDynamics(decay_rate=0.5, min_activation=0.01)

    # step until inactive
    for _ in range(10):
        dyn.step([h])
        if not h.active:
            break

    assert h.activation == 0.0
    assert h.active is False


# ============================================================
# Test: zero activation remains inert
# ============================================================

def test_zero_activation_is_inert():
    h = Hypothesis(
        hypothesis_id="H-zero",
        created_step=0,
        activation=0.0,
    )

    dyn = HypothesisDynamics(decay_rate=0.5)

    dyn.step([h])

    assert h.activation == 0.0
    assert h.active is False


# ============================================================
# Test: inactive hypotheses are ignored
# ============================================================

def test_inactive_hypothesis_not_modified():
    h = Hypothesis(
        hypothesis_id="H-inactive",
        created_step=0,
        activation=0.5,
        active=False,
    )

    dyn = HypothesisDynamics(decay_rate=0.5)

    dyn.step([h])

    assert h.activation == 0.5
    assert h.active is False
