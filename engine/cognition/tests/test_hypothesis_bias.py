from __future__ import annotations

import pytest

from engine.cognition.hypothesis import Hypothesis
from engine.cognition.hypothesis_bias import HypothesisBias


# ============================================================
# Test: bias computed from stabilized hypothesis
# ============================================================

def test_bias_generated_from_hypothesis():
    h = Hypothesis(
        hypothesis_id="H-bias",
        created_step=0,
        activation=1.0,
    )

    biaser = HypothesisBias(bias_gain=0.1)

    bias = biaser.compute_bias(stabilized_hypotheses=[h])

    assert "H-bias" in bias
    assert bias["H-bias"] == pytest.approx(0.1)


# ============================================================
# Test: bias is bounded
# ============================================================

def test_bias_is_bounded():
    h = Hypothesis(
        hypothesis_id="H-bound",
        created_step=0,
        activation=10.0,
    )

    biaser = HypothesisBias(bias_gain=0.5, max_bias=0.2)

    bias = biaser.compute_bias(stabilized_hypotheses=[h])

    assert bias["H-bound"] == pytest.approx(0.2)


# ============================================================
# Test: inactive hypotheses produce no bias
# ============================================================

def test_inactive_hypothesis_no_bias():
    h = Hypothesis(
        hypothesis_id="H-inactive",
        created_step=0,
        activation=1.0,
        active=False,
    )

    biaser = HypothesisBias()

    bias = biaser.compute_bias(stabilized_hypotheses=[h])

    assert bias == {}


# ============================================================
# Test: empty input produces no bias
# ============================================================

def test_no_hypotheses_no_bias():
    biaser = HypothesisBias()

    bias = biaser.compute_bias(stabilized_hypotheses=[])

    assert bias == {}
