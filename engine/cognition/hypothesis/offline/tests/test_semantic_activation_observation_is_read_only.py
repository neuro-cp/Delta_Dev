from __future__ import annotations

from copy import deepcopy

from engine.cognition.hypothesis.offline.hypothesis_runner import HypothesisRunner
from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame

from engine.cognition.hypothesis.hypothesis_registry import HypothesisRegistry
from engine.cognition.hypothesis.hypothesis_grounding import HypothesisGrounding
from engine.cognition.hypothesis.hypothesis_competition import HypothesisCompetition
from engine.cognition.hypothesis.hypothesis_dynamics import HypothesisDynamics
from engine.cognition.hypothesis.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis.hypothesis_bias import HypothesisBias
from engine.cognition.hypothesis.offline.support_to_activation import SupportToActivation


def _build_runner() -> HypothesisRunner:
    """
    Construct a minimal offline HypothesisRunner with
    empty/default components.

    This mirrors existing cognition tests and must not
    depend on semantic activation.
    """
    return HypothesisRunner(
        registry=HypothesisRegistry(),
        grounding=HypothesisGrounding(),
        competition=HypothesisCompetition(),
        dynamics=HypothesisDynamics(),
        stabilization=HypothesisStabilization(),
        bias=HypothesisBias(),
        support_mapper=SupportToActivation(),
    )


def test_semantic_activation_is_observational_only() -> None:
    """
    Invariant test:

    Adding semantic_activation to ObservationFrame MUST NOT:
    - change hypothesis stabilization events
    - change bias suggestions
    - change registry state

    Cognition behavior must be identical with or without SAFs.
    """

    runner_plain = _build_runner()
    runner_with_semantics = _build_runner()

    frames_plain = [
        ObservationFrame(step=0),
        ObservationFrame(step=1),
        ObservationFrame(step=2),
    ]

    frames_with_semantics = [
        ObservationFrame(step=0, semantic_activation={"pattern_a": 1.0}),
        ObservationFrame(step=1, semantic_activation={"pattern_a": 0.8}),
        ObservationFrame(step=2, semantic_activation={"pattern_a": 0.6}),
    ]

    runner_plain.run(frames_plain)
    runner_with_semantics.run(frames_with_semantics)

    # --- compare stabilization events ---
    assert runner_plain.stabilization_events == runner_with_semantics.stabilization_events

    # --- compare bias suggestions ---
    assert runner_plain.bias_suggestions == runner_with_semantics.bias_suggestions

    # --- compare registry state (ids + activations) ---
    plain_hyps = runner_plain.registry.all()
    semantic_hyps = runner_with_semantics.registry.all()

    assert len(plain_hyps) == len(semantic_hyps)

    for h1, h2 in zip(plain_hyps, semantic_hyps):
        assert h1.hypothesis_id == h2.hypothesis_id
        assert h1.activation == h2.activation
        assert h1.support == h2.support
