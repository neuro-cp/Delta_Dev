from __future__ import annotations

from typing import Iterable, List, Dict, Any, Set
import inspect

from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame
from engine.cognition.hypothesis.offline.support_to_activation import SupportToActivation

from engine.cognition.hypothesis.hypothesis_registry import HypothesisRegistry
from engine.cognition.hypothesis.hypothesis_grounding import HypothesisGrounding
from engine.cognition.hypothesis.hypothesis_competition import HypothesisCompetition
from engine.cognition.hypothesis.hypothesis_dynamics import HypothesisDynamics
from engine.cognition.hypothesis.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis.hypothesis_bias import HypothesisBias


class HypothesisRunner:
    """
    Offline hypothesis orchestration engine (Phase 6).

    CONTRACT:
    - Offline only
    - No runtime authority
    - No memory writes
    - Deterministic step order
    """

    def __init__(
        self,
        *,
        registry: HypothesisRegistry,
        grounding: HypothesisGrounding,
        competition: HypothesisCompetition,
        dynamics: HypothesisDynamics,
        stabilization: HypothesisStabilization,
        bias: HypothesisBias,
        support_mapper: SupportToActivation,
    ) -> None:
        self.registry = registry
        self.grounding = grounding
        self.competition = competition
        self.dynamics = dynamics
        self.stabilization = stabilization
        self.bias = bias
        self.support_mapper = support_mapper

        # Offline artifacts (append-only)
        self.stabilization_events: List[Dict[str, Any]] = []
        self.bias_suggestions: List[Dict[str, float]] = []

        # Track which hypotheses have ever stabilized (bias is only for these)
        self._stabilized_ids: Set[str] = set()

        # Signature compatibility probes (keeps runner resilient to older modules)
        self._grounding_params = set(inspect.signature(self.grounding.step).parameters.keys())
        self._stabilization_params = set(inspect.signature(self.stabilization.step).parameters.keys())

    def step(self, obs: ObservationFrame) -> None:
        # 1) Registry tick (ages)
        self.registry.tick()
        hypotheses = self.registry.all()

        # 2) Grounding (two supported forms)
        # Preferred canonical: observed_assemblies=Iterable[PopulationModel]
        if "observed_assemblies" in self._grounding_params:
            # ObservationFrame only has scalars, so default to "no assemblies observed"
            # (Integration test will supply a real list via a wrapper/adapter when ready.)
            self.grounding.step(hypotheses=hypotheses, observed_assemblies=[])
        else:
            # Back-compat: assembly_outputs dict
            self.grounding.step(hypotheses=hypotheses, assembly_outputs=obs.assembly_outputs or {})

        # 3) Support -> activation
        for h in hypotheses:
            h.activation = self.support_mapper.map(h.support)

        # 4) Competition
        self.competition.step(hypotheses)

        # 5) Dynamics
        self.dynamics.step(hypotheses)

        # 6) Stabilization (canonical has no step kw)
        if "step" in self._stabilization_params:
            events = self.stabilization.step(hypotheses, step=obs.step)  # legacy
        else:
            events = self.stabilization.step(hypotheses)

        if events:
            self.stabilization_events.extend(events)
            for e in events:
                hid = e.get("hypothesis_id")
                if isinstance(hid, str):
                    self._stabilized_ids.add(hid)

        # 7) Bias (ONLY from stabilized hypotheses)
        stabilized = [h for h in hypotheses if h.hypothesis_id in self._stabilized_ids]
        bias_map = self.bias.compute_bias(stabilized_hypotheses=stabilized)

        if bias_map:
            self.bias_suggestions.append(bias_map)

    def run(self, frames: Iterable[ObservationFrame]) -> None:
        for obs in frames:
            self.step(obs)
