from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# --------------------------------------------------
# Atomic records (pure data)
# --------------------------------------------------

@dataclass(frozen=True)
class ActivationSample:
    """
    Single time-sampled activation record.

    Pure observation.
    No interpretation.
    """
    step: int
    activation: float
    support: float


@dataclass(frozen=True)
class BiasEvent:
    """
    Offline bias proposal emitted by Phase 6.

    Advisory only.
    Carries no authority.
    """
    step: int
    bias_map: Dict[str, float]


@dataclass(frozen=True)
class StabilizationEvent:
    """
    Hypothesis stabilization marker.

    Emitted once per hypothesis.
    """
    step: int
    hypothesis_id: str


# --------------------------------------------------
# Timeline container (single hypothesis)
# --------------------------------------------------

@dataclass
class HypothesisTimeline:
    """
    Inspection-only timeline for a single hypothesis.

    CONTRACT:
    - Offline only
    - Append-only during construction
    - Safe to serialize
    - Carries NO authority
    """

    hypothesis_id: str

    # Time series
    activations: List[ActivationSample] = field(default_factory=list)

    # Key events
    stabilization: Optional[StabilizationEvent] = None
    bias_events: List[BiasEvent] = field(default_factory=list)

    # --------------------------------------------------
    # Append helpers (builder-only usage)
    # --------------------------------------------------

    def record_activation(
        self,
        *,
        step: int,
        activation: float,
        support: float,
    ) -> None:
        self.activations.append(
            ActivationSample(
                step=int(step),
                activation=float(activation),
                support=float(support),
            )
        )

    def record_stabilization(
        self,
        *,
        step: int,
    ) -> None:
        # Stabilization must be unique
        if self.stabilization is not None:
            return

        self.stabilization = StabilizationEvent(
            step=int(step),
            hypothesis_id=self.hypothesis_id,
        )

    def record_bias_event(
        self,
        *,
        step: int,
        bias_map: Dict[str, float],
    ) -> None:
        self.bias_events.append(
            BiasEvent(
                step=int(step),
                bias_map=dict(bias_map),
            )
        )


# --------------------------------------------------
# Multi-hypothesis bundle (pure container)
# --------------------------------------------------

@dataclass
class HypothesisTimelineBundle:
    """
    Inspection bundle for multiple hypotheses.

    Pure container.
    No logic.
    """

    timelines: Dict[str, HypothesisTimeline] = field(default_factory=dict)

    def get(self, hypothesis_id: str) -> HypothesisTimeline:
        if hypothesis_id not in self.timelines:
            self.timelines[hypothesis_id] = HypothesisTimeline(
                hypothesis_id=hypothesis_id
            )
        return self.timelines[hypothesis_id]

    def all_timelines(self) -> List[HypothesisTimeline]:
        return list(self.timelines.values())
