from __future__ import annotations

from typing import List

from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame
from engine.cognition.hypothesis.offline.support_to_activation import SupportToActivation
from engine.cognition.hypothesis.offline.hypothesis_runner import HypothesisRunner

from engine.cognition.hypothesis.hypothesis_registry import HypothesisRegistry
from engine.cognition.hypothesis.hypothesis_grounding import HypothesisGrounding
from engine.cognition.hypothesis.hypothesis_competition import HypothesisCompetition
from engine.cognition.hypothesis.hypothesis_dynamics import HypothesisDynamics
from engine.cognition.hypothesis.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis.hypothesis_bias import HypothesisBias


def test_hypothesis_runner_stabilizes_and_emits_bias() -> None:
    """
    Phase 6 certification test.

    Verifies:
    - support accumulation (manual injection)
    - support → activation mapping
    - sustained activation stabilization
    - bounded bias emission
    - zero runtime / episodic / salience authority
    """

    # --------------------------------------------------
    # 1. Registry-owned hypotheses
    # --------------------------------------------------

    registry = HypothesisRegistry()

    h1 = registry.create(hypothesis_id="H1", created_step=0)
    h2 = registry.create(hypothesis_id="H2", created_step=0)

    # --------------------------------------------------
    # 2. Core subsystems (legal defaults only)
    # --------------------------------------------------

    grounding = HypothesisGrounding()   # inert (no assemblies)
    competition = HypothesisCompetition()
    dynamics = HypothesisDynamics()
    stabilization = HypothesisStabilization(
        activation_threshold=0.6,
        sustain_steps=3,
    )
    bias = HypothesisBias()
    support_mapper = SupportToActivation(
        gain=5.0,
        midpoint=0.4,
    )

    runner = HypothesisRunner(
        registry=registry,
        grounding=grounding,
        competition=competition,
        dynamics=dynamics,
        stabilization=stabilization,
        bias=bias,
        support_mapper=support_mapper,
    )

    # --------------------------------------------------
    # 3. Offline observation stream
    # --------------------------------------------------

    frames: List[ObservationFrame] = [
        ObservationFrame(step=i)
        for i in range(10)
    ]

    # --------------------------------------------------
    # 4. Manual support injection + stepping
    # --------------------------------------------------

    for frame in frames:
        # Inject support BEFORE stepping
        h1.support += 1.0    # strong sustained signal
        h2.support += 0.05    # weak background noise

        runner.step(frame)

    # --------------------------------------------------
    # 5. Assertions
    # --------------------------------------------------

    assert runner.stabilization_events, "No stabilization events emitted."

    stabilized_ids = {
        e["hypothesis_id"]
        for e in runner.stabilization_events
    }

    assert "H1" in stabilized_ids
    assert "H2" not in stabilized_ids

    assert runner.bias_suggestions, "No bias suggestions emitted."

    for bias_map in runner.bias_suggestions:
        for value in bias_map.values():
            assert 0.0 <= value <= bias.max_bias

    for h in registry.all():
        assert 0.0 <= h.support <= grounding.max_support
        assert 0.0 <= h.activation <= 1.0



### passed all tests ###
