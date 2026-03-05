from __future__ import annotations

import pytest

from engine.cognition.hypothesis import Hypothesis
from engine.cognition.hypothesis_competition import HypothesisCompetition


# ============================================================
# Test: no competition with single hypothesis
# ============================================================

def test_single_hypothesis_unchanged():
    h = Hypothesis(
        hypothesis_id="H-solo",
        created_step=0,
        activation=1.0,
    )

    comp = HypothesisCompetition(competition_gain=0.5)
    comp.step([h])

    assert h.activation == 1.0
    assert h.active is True


# ============================================================
# Test: mutual suppression occurs
# ============================================================

def test_mutual_suppression():
    h1 = Hypothesis(
        hypothesis_id="H-1",
        created_step=0,
        activation=1.0,
    )
    h2 = Hypothesis(
        hypothesis_id="H-2",
        created_step=0,
        activation=1.0,
    )

    comp = HypothesisCompetition(competition_gain=0.1)
    comp.step([h1, h2])

    assert h1.activation < 1.0
    assert h2.activation < 1.0
    assert h1.active is True
    assert h2.active is True


# ============================================================
# Test: stronger hypothesis suppresses weaker
# ============================================================

def test_stronger_hypothesis_survives():
    h_strong = Hypothesis(
        hypothesis_id="H-strong",
        created_step=0,
        activation=1.0,
    )
    h_weak = Hypothesis(
        hypothesis_id="H-weak",
        created_step=0,
        activation=0.2,
    )

    comp = HypothesisCompetition(competition_gain=0.5, min_activation=0.05)

    for _ in range(5):
        comp.step([h_strong, h_weak])

    assert h_strong.active is True
    assert h_strong.activation > 0.0
    assert h_weak.active is False
    assert h_weak.activation == 0.0


# ============================================================
# Test: inactive hypotheses ignored
# ============================================================

def test_inactive_hypothesis_not_considered():
    h_active = Hypothesis(
        hypothesis_id="H-active",
        created_step=0,
        activation=1.0,
    )
    h_inactive = Hypothesis(
        hypothesis_id="H-inactive",
        created_step=0,
        activation=1.0,
        active=False,
    )

    comp = HypothesisCompetition(competition_gain=0.5)
    comp.step([h_active, h_inactive])

    assert h_active.activation == 1.0
    assert h_active.active is True
    assert h_inactive.activation == 1.0
    assert h_inactive.active is False
