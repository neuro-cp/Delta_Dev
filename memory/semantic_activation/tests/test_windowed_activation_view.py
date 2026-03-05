from __future__ import annotations

from memory.semantic_activation.windowed_view import WindowedActivationView
from memory.semantic_activation.inspection.windowed_activation_view import (
    WindowedActivationInspectionBuilder,
)


def test_sliding_window_respects_bounds() -> None:
    history = [
        {"a": 1.0},
        {"a": 0.8},
        {"a": 0.6},
        {"a": 0.4},
    ]

    window = WindowedActivationView.sliding_window(
        history=history,
        window_size=2,
    )

    assert len(window) == 2
    assert window[0]["a"] == 0.6
    assert window[1]["a"] == 0.4


def test_sliding_window_short_history() -> None:
    history = [{"x": 1.0}]

    window = WindowedActivationView.sliding_window(
        history=history,
        window_size=5,
    )

    assert window == history


def test_exponential_window_scales_monotonically() -> None:
    history = [
        {"a": 1.0},
        {"a": 1.0},
        {"a": 1.0},
    ]

    window = WindowedActivationView.exponential_window(
        history=history,
        decay=0.5,
    )

    assert window[0]["a"] < window[1]["a"] < window[2]["a"]


def test_inspection_builder_is_read_only() -> None:
    history = [
        {"x": 0.3},
        {"x": 0.2},
    ]

    builder = WindowedActivationInspectionBuilder()
    views = builder.build(windowed_history=history)

    assert len(views) == 2
    assert views[0].activations == {"x": 0.3}
    assert views[1].activations == {"x": 0.2}
