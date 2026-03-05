from __future__ import annotations

import pytest

from engine.cognition.hypothesis import Hypothesis
from engine.cognition.hypothesis_grounding import HypothesisGrounding


class DummyAssembly:
    """
    Minimal stand-in for PopulationModel (read-only).
    """
    def __init__(self, value: float):
        self._value = float(value)

    def output(self) -> float:
        return self._value


# ============================================================
# Test: hypotheses accumulate support from assemblies
# ============================================================

def test_support_accumulates():
    h = Hypothesis(
        hypothesis_id="H-ground",
        created_step=0,
    )

    assemblies = [
        DummyAssembly(0.5),
        DummyAssembly(1.0),
        DummyAssembly(1.5),
    ]

    grounding = HypothesisGrounding(support_gain=1.0)

    grounding.step(
        hypotheses=[h],
        observed_assemblies=assemblies,
    )

    assert h.support == pytest.approx(3.0)
    assert h.active is True


# ============================================================
# Test: inactive hypotheses ignored
# ============================================================

def test_inactive_hypothesis_not_updated():
    h = Hypothesis(
        hypothesis_id="H-inactive",
        created_step=0,
        active=False,
    )

    assemblies = [DummyAssembly(2.0)]

    grounding = HypothesisGrounding()

    grounding.step(
        hypotheses=[h],
        observed_assemblies=assemblies,
    )

    assert h.support == 0.0
    assert h.active is False


# ============================================================
# Test: support is bounded
# ============================================================

def test_support_is_bounded():
    h = Hypothesis(
        hypothesis_id="H-bound",
        created_step=0,
    )

    assemblies = [DummyAssembly(100.0)]

    grounding = HypothesisGrounding(
        support_gain=1.0,
        max_support=5.0,
    )

    grounding.step(
        hypotheses=[h],
        observed_assemblies=assemblies,
    )

    assert h.support == 5.0


# ============================================================
# Test: assemblies are not modified
# ============================================================

def test_grounding_is_read_only():
    a = DummyAssembly(1.0)
    h = Hypothesis(
        hypothesis_id="H-readonly",
        created_step=0,
    )

    grounding = HypothesisGrounding()

    grounding.step(
        hypotheses=[h],
        observed_assemblies=[a],
    )

    assert a.output() == 1.0
