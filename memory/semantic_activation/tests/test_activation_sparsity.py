from __future__ import annotations

from memory.semantic_activation.sparsity import ActivationSparsifier


def test_soft_threshold_reduces_density() -> None:
    activations = {
        "a": 1.0,
        "b": 0.4,
        "c": 0.1,
    }

    sparse = ActivationSparsifier.soft_threshold(
        activations,
        epsilon=0.3,
    )

    assert "a" in sparse
    assert "b" in sparse
    assert "c" not in sparse

    assert abs(sparse["a"] - 0.7) < 1e-9
    assert abs(sparse["b"] - 0.1) < 1e-9


def test_soft_threshold_noop_when_epsilon_non_positive() -> None:
    activations = {"x": 1.0, "y": 2.0}

    assert ActivationSparsifier.soft_threshold(
        activations,
        epsilon=0.0,
    ) == activations

    assert ActivationSparsifier.soft_threshold(
        activations,
        epsilon=-1.0,
    ) == activations


def test_energy_budget_scales_uniformly() -> None:
    activations = {
        "a": 2.0,
        "b": 1.0,
        "c": 1.0,
    }

    budgeted = ActivationSparsifier.energy_budget(
        activations,
        budget=2.0,
    )

    assert abs(sum(budgeted.values()) - 2.0) < 1e-9

    # relative ratios preserved
    assert abs(budgeted["a"] / budgeted["b"] - 2.0) < 1e-9
    assert abs(budgeted["b"] - budgeted["c"]) < 1e-9


def test_energy_budget_noop_when_under_budget() -> None:
    activations = {
        "x": 0.5,
        "y": 0.25,
    }

    assert ActivationSparsifier.energy_budget(
        activations,
        budget=2.0,
    ) == activations


def test_energy_budget_zero_or_negative_budget_clears() -> None:
    activations = {
        "x": 1.0,
        "y": 1.0,
    }

    assert ActivationSparsifier.energy_budget(
        activations,
        budget=0.0,
    ) == {}

    assert ActivationSparsifier.energy_budget(
        activations,
        budget=-1.0,
    ) == {}
##validated##