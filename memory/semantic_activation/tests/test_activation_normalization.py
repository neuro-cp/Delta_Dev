from __future__ import annotations

from memory.semantic_activation.normalization import ActivationNormalizer


def test_max_normalization_scales_relative_values() -> None:
    activations = {
        "a": 2.0,
        "b": 1.0,
        "c": 0.5,
    }

    norm = ActivationNormalizer.max_normalize(activations)

    assert norm["a"] == 1.0
    assert norm["b"] == 0.5
    assert norm["c"] == 0.25


def test_sum_normalization_scales_to_unit_mass() -> None:
    activations = {
        "x": 1.0,
        "y": 1.0,
        "z": 2.0,
    }

    norm = ActivationNormalizer.sum_normalize(activations)

    assert abs(sum(norm.values()) - 1.0) < 1e-9
    assert norm["z"] == 0.5


def test_normalization_handles_empty_and_zero_safely() -> None:
    assert ActivationNormalizer.max_normalize({}) == {}
    assert ActivationNormalizer.sum_normalize({}) == {}

    zeros = {"a": 0.0, "b": 0.0}
    assert ActivationNormalizer.max_normalize(zeros) == zeros
    assert ActivationNormalizer.sum_normalize(zeros) == zeros
