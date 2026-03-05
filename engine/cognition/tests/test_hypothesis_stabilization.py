from __future__ import annotations

import pytest

from engine.cognition.hypothesis import Hypothesis
from engine.cognition.hypothesis_stabilization import HypothesisStabilization


# ============================================================
# Test: stabilization after sustained activation
# ============================================================

def test_hypothesis_stabilizes_after_sustain():
    h = Hypothesis(
        hypothesis_id="H-stable",
        created_step=0,
        activation=1.0,
    )

    stab = HypothesisStabilization(
        activation_threshold=0.5,
        sustain_steps=3,
    )

    events = []
    for _ in range(3):
        events = stab.step([h])

    assert len(events) == 1
    event = events[0]

    assert event["event"] == "hypothesis_stabilized"
    assert event["hypothesis_id"] == "H-stable"
    assert event["activation"] == 1.0


# ============================================================
# Test: no stabilization if activation drops
# ============================================================

def test_no_stabilization_if_activation_fluctuates():
    h = Hypothesis(
        hypothesis_id="H-fluctuate",
        created_step=0,
        activation=1.0,
    )

    stab = HypothesisStabilization(
        activation_threshold=0.5,
        sustain_steps=3,
    )

    # step 1: above threshold
    stab.step([h])

    # step 2: drop below threshold
    h.activation = 0.1
    stab.step([h])

    # step 3–4: back above, but counter reset
    h.activation = 1.0
    events = stab.step([h])
    events = stab.step([h])

    assert events == []


# ============================================================
# Test: inactive hypothesis never stabilizes
# ============================================================

def test_inactive_hypothesis_never_stabilizes():
    h = Hypothesis(
        hypothesis_id="H-inactive",
        created_step=0,
        activation=1.0,
        active=False,
    )

    stab = HypothesisStabilization(
        activation_threshold=0.5,
        sustain_steps=2,
    )

    for _ in range(5):
        events = stab.step([h])

    assert events == []


# ============================================================
# Test: multiple hypotheses tracked independently
# ============================================================

def test_multiple_hypotheses_independent_counters():
    h1 = Hypothesis(
        hypothesis_id="H-1",
        created_step=0,
        activation=1.0,
    )
    h2 = Hypothesis(
        hypothesis_id="H-2",
        created_step=0,
        activation=0.0,
    )

    stab = HypothesisStabilization(
        activation_threshold=0.5,
        sustain_steps=2,
    )

    stab.step([h1, h2])
    events = stab.step([h1, h2])

    assert len(events) == 1
    assert events[0]["hypothesis_id"] == "H-1"
