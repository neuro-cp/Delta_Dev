from __future__ import annotations

from typing import Iterable

from engine.cognition.hypothesis.offline.inspection.hypothesis_timeline import (
    HypothesisTimeline,
    HypothesisTimelineBundle,
)
from engine.cognition.hypothesis.offline.inspection.stabilization_window import (
    derive_stabilization_window,
)


# --------------------------------------------------
# Simple text renderer (inspection only)
# --------------------------------------------------

def render_hypothesis_timeline(
    timeline: HypothesisTimeline,
    *,
    max_rows: int | None = None,
    activation_threshold: float = 0.6,
) -> str:
    """
    Render a single hypothesis timeline as plain text.

    CONTRACT:
    - Inspection only
    - No side effects
    - No truncation unless explicitly requested
    """

    lines: list[str] = []

    lines.append(f"HYPOTHESIS: {timeline.hypothesis_id}")
    lines.append("-" * 60)

    # --------------------------------------------------
    # Stabilization summary
    # --------------------------------------------------

    if timeline.stabilization is not None:
        lines.append(
            f"STABILIZED at step {timeline.stabilization.step}"
        )

        window = derive_stabilization_window(
            timeline=timeline,
            activation_threshold=activation_threshold,
        )

        if window is not None:
            lines.append(
                f"SUSTAIN WINDOW: {window.start_step} → {window.end_step} "
                f"({window.sustain_steps} steps)"
            )
            lines.append(
                f"MEAN activation: {window.mean_activation:.4f}"
            )
            lines.append(
                f"MEAN support:    {window.mean_support:.4f}"
            )
    else:
        lines.append("STABILIZED: no")

    lines.append("")

    # --------------------------------------------------
    # Activation trace
    # --------------------------------------------------

    lines.append("ACTIVATION TRACE:")
    lines.append(" step | activation | support")
    lines.append("------+------------+---------")

    activations = timeline.activations
    if max_rows is not None:
        activations = activations[:max_rows]

    for a in activations:
        lines.append(
            f"{a.step:5d} | {a.activation:10.4f} | {a.support:7.4f}"
        )

    if max_rows is not None and len(timeline.activations) > max_rows:
        lines.append("  ... (truncated)")

    lines.append("")

    # --------------------------------------------------
    # Bias events
    # --------------------------------------------------

    if timeline.bias_events:
        lines.append("BIAS EVENTS:")
        for b in timeline.bias_events:
            lines.append(f" step {b.step}: {b.bias_map}")
    else:
        lines.append("BIAS EVENTS: none")

    lines.append("")
    return "\n".join(lines)


def render_hypothesis_bundle(
    bundle: HypothesisTimelineBundle,
    *,
    max_rows: int | None = None,
    activation_threshold: float = 0.6,
) -> str:
    """
    Render all hypothesis timelines in a bundle.
    """

    blocks: list[str] = []

    for timeline in bundle.all_timelines():
        blocks.append(
            render_hypothesis_timeline(
                timeline,
                max_rows=max_rows,
                activation_threshold=activation_threshold,
            )
        )

    return "\n\n".join(blocks)


# --------------------------------------------------
# Convenience printer (optional)
# --------------------------------------------------

def print_hypothesis_bundle(
    bundle: HypothesisTimelineBundle,
    *,
    max_rows: int | None = None,
    activation_threshold: float = 0.6,
) -> None:
    print(
        render_hypothesis_bundle(
            bundle,
            max_rows=max_rows,
            activation_threshold=activation_threshold,
        )
    )
