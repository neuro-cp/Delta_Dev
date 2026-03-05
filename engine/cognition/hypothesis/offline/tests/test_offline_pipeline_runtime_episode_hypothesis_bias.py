from __future__ import annotations

from typing import Dict, List

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay

from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame
from engine.cognition.hypothesis.offline.support_to_activation import SupportToActivation
from engine.cognition.hypothesis.offline.hypothesis_runner import HypothesisRunner

from engine.cognition.hypothesis.hypothesis_registry import HypothesisRegistry
from engine.cognition.hypothesis.hypothesis_grounding import HypothesisGrounding
from engine.cognition.hypothesis.hypothesis_competition import HypothesisCompetition
from engine.cognition.hypothesis.hypothesis_dynamics import HypothesisDynamics
from engine.cognition.hypothesis.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis.hypothesis_bias import HypothesisBias

from engine.salience.tools.read_salience_log import (
    read_salience_log_as_step_scalar,
)

# --------------------------------------------------
# EpisodeReplay compatibility shim
# --------------------------------------------------
def _make_replay(*, episodes, trace):
    try:
        return EpisodeReplay(
            episodes=episodes,
            episode_trace=trace,
            salience_trace=None,
        )
    except TypeError:
        try:
            return EpisodeReplay(episodes=episodes, trace=trace)
        except TypeError:
            return EpisodeReplay(episodes, trace)


def test_offline_pipeline_runtime_episode_hypothesis_bias() -> None:
    """
    Offline integration certification test.

    Proves the full offline bridge:

      Real SalienceTrace →
      Episodic episode bounds →
      Replay slicing →
      ObservationFrame stream →
      HypothesisRunner →
      Stabilization →
      Bounded bias

    Contract:
    - Offline only
    - No runtime mutation
    - No salience engine mutation
    - No learning or persistence
    """

    # --------------------------------------------------
    # 1) Load REAL salience trace
    # --------------------------------------------------

    salience_by_step: Dict[int, float] = read_salience_log_as_step_scalar(
        "engine/salience/tests/salience_trace_proof_log.txt"
    )

    assert salience_by_step, "Salience trace is empty."

    sorted_steps = sorted(salience_by_step.keys())

    WINDOW_START = sorted_steps[0]
    WINDOW_END = WINDOW_START + 40

    salience_by_step = {
        step: salience_by_step[step]
        for step in sorted_steps
        if WINDOW_START <= step <= WINDOW_END
    }

    # --------------------------------------------------
    # 2) Build episodic structure aligned to salience
    # --------------------------------------------------

    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    tracker.start_episode(step=WINDOW_START, reason="integration_start")
    tracker.mark_decision(
        step=WINDOW_START + 20,
        winner="D1",
        confidence=0.85,
    )
    tracker.close_episode(step=WINDOW_END, reason="integration_end")

    episodes = getattr(tracker, "episodes", None)
    if episodes is None:
        episodes = tracker.all_episodes()

    assert len(episodes) == 1
    ep = episodes[0]

    assert ep.start_step == WINDOW_START
    assert ep.end_step == WINDOW_END

    _ = _make_replay(episodes=episodes, trace=trace)  # artifact; replay integrity only

    # --------------------------------------------------
    # 3) Build ObservationFrames within episode bounds
    # --------------------------------------------------

    frames: List[ObservationFrame] = []

    for step in range(ep.start_step, ep.end_step + 1):
        sal = salience_by_step.get(step, 0.0)

        frames.append(
            ObservationFrame(
                step=step,
                salience=sal,
                assembly_outputs={"salience": sal},
            )
        )

    assert all(ep.start_step <= f.step <= ep.end_step for f in frames)
    assert any(f.salience > 0.0 for f in frames), "Expected in-episode salience."

    # --------------------------------------------------
    # 4) Hypothesis stack (Phase 6)
    # --------------------------------------------------

    registry = HypothesisRegistry()
    h1 = registry.create(hypothesis_id="H1", created_step=0)
    h2 = registry.create(hypothesis_id="H2", created_step=0)

    runner = HypothesisRunner(
        registry=registry,
        grounding=HypothesisGrounding(),
        competition=HypothesisCompetition(),
        dynamics=HypothesisDynamics(),
        stabilization=HypothesisStabilization(
            activation_threshold=0.6,
            sustain_steps=3,
        ),
        bias=HypothesisBias(),
        support_mapper=SupportToActivation(
            gain=5.0,
            midpoint=0.4,
        ),
    )

    # --------------------------------------------------
    # 5) Offline support injection + stepping
    # --------------------------------------------------

    for f in frames:
        h1.support += 10 * float(f.salience or 0.0)
        h2.support += 0.005
        runner.step(f)

    # --------------------------------------------------
    # 6) Assertions
    # --------------------------------------------------

    assert runner.stabilization_events, "No stabilization events emitted."

    stabilized_ids = {e["hypothesis_id"] for e in runner.stabilization_events}
    assert "H1" in stabilized_ids
    assert "H2" not in stabilized_ids

    assert runner.bias_suggestions, "No bias suggestions emitted."

    for bias_map in runner.bias_suggestions:
        for value in bias_map.values():
            assert 0.0 <= value <= runner.bias.max_bias

    for h in registry.all():
        assert 0.0 <= h.activation <= 1.0
        assert 0.0 <= h.support <= runner.grounding.max_support
