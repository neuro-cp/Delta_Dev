from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine.cognition.hypothesis.offline.inspection.hypothesis_timeline import (
    HypothesisTimeline,
)


# --------------------------------------------------
# Immutable inspection artifact
# --------------------------------------------------

@dataclass(frozen=True)
class StabilizationWindow:
    """
    Post-hoc explanation of hypothesis stabilization.

    CONTRACT:
    - Derived from inspection data only
    - Immutable
    - No authority
    """

    hypothesis_id: str

    start_step: int
    end_step: int
    sustain_steps: int

    mean_activation: float
    mean_support: float


# --------------------------------------------------
# Derivation logic (inspection-only)
# --------------------------------------------------

def derive_stabilization_window(
    *,
    timeline: HypothesisTimeline,
    activation_threshold: float,
) -> Optional[StabilizationWindow]:
    """
    Derive the stabilization window for a hypothesis timeline.

    Returns None if:
    - hypothesis never stabilized
    - activation history is missing
    """

    if timeline.stabilization is None:
        return None

    if not timeline.activations:
        return None

    stabilize_step = timeline.stabilization.step

    # Walk backwards to find first sustained threshold crossing
    window_samples = []

    for sample in reversed(timeline.activations):
        if sample.step > stabilize_step:
            continue

        if sample.activation >= activation_threshold:
            window_samples.append(sample)
        else:
            break

    if not window_samples:
        return None

    window_samples.reverse()

    start_step = window_samples[0].step
    end_step = window_samples[-1].step

    mean_activation = sum(s.activation for s in window_samples) / len(window_samples)
    mean_support = sum(s.support for s in window_samples) / len(window_samples)

    return StabilizationWindow(
        hypothesis_id=timeline.hypothesis_id,
        start_step=start_step,
        end_step=end_step,
        sustain_steps=len(window_samples),
        mean_activation=mean_activation,
        mean_support=mean_support,
    )
