from __future__ import annotations

from typing import Dict

from engine.cognition.hypothesis.offline.hypothesis_runner import HypothesisRunner
from engine.cognition.hypothesis.offline.inspection.hypothesis_timeline import (
    HypothesisTimeline,
    HypothesisTimelineBundle,
)


# --------------------------------------------------
# Timeline Builder (inspection only)
# --------------------------------------------------

class HypothesisTimelineBuilder:
    """
    Constructs hypothesis timelines from offline artifacts.

    CONTRACT:
    - Offline only
    - Read-only
    - Deterministic
    - No cognition, learning, or inference
    - Safe to run multiple times
    """

    def __init__(self, *, runner: HypothesisRunner) -> None:
        self._runner = runner

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def build(self) -> HypothesisTimelineBundle:
        """
        Build timelines for all hypotheses known to the runner.
        """

        bundle = HypothesisTimelineBundle()

        # --------------------------------------------------
        # 1) Activation + support history
        # --------------------------------------------------

        trace = getattr(self._runner, "trace", None)
        if trace is not None:
            for record in trace:
                timeline = bundle.get(record.hypothesis_id)

                timeline.record_activation(
                    step=record.step,
                    activation=record.activation,
                    support=record.support,
                )

        # --------------------------------------------------
        # 2) Stabilization events
        # --------------------------------------------------

        for event in self._runner.stabilization_events:
            hypothesis_id = event.get("hypothesis_id")
            step = event.get("step")

            if hypothesis_id is None or step is None:
                continue

            timeline = bundle.get(hypothesis_id)
            timeline.record_stabilization(step=step)

        # --------------------------------------------------
        # 3) Bias events (advisory only)
        # --------------------------------------------------

        for bias_event in self._runner.bias_suggestions:
            step = bias_event.get("step")
            bias_map = bias_event.get("bias")

            if step is None or bias_map is None:
                continue

            # Bias proposals may apply to multiple hypotheses
            for hypothesis_id, _value in bias_map.items():
                timeline = bundle.get(hypothesis_id)

                timeline.record_bias_event(
                    step=step,
                    bias_map=bias_map,
                )

        return bundle
