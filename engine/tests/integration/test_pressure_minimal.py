from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_runtime_hook import EpisodeRuntimeHook

from memory.proto_structural.episodic_signature_adapter import (
    EpisodicSignatureAdapter,
)
from memory.proto_structural.pattern_accumulator import PatternAccumulator
from memory.proto_structural.pattern_statistics import PatternStatisticsBuilder


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _build_runtime() -> BrainRuntime:
    """
    Build a fully compiled runtime with episodic observation enabled.
    """
    loader = NeuralFrameworkLoader(PROJECT_ROOT)

    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain)

    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    runtime.episode_hook = EpisodeRuntimeHook(tracker=tracker)

    return runtime


def test_proto_structural_pressure_exists() -> None:
    """
    Proves that proto-structural pressure can arise from a real,
    causally valid episode produced by the runtime.
    """

    runtime = _build_runtime()

    # --------------------------------------------------
    # Phase 1: build internal dynamics (no decisions)
    # --------------------------------------------------
    for _ in range(200):
        runtime.step()

    # --------------------------------------------------
    # Phase 2: open a lawful coincidence window
    # --------------------------------------------------
    runtime.inject_decision_coincidence(
        delta_boost=runtime.DECISION_DOMINANCE_THRESHOLD,
        relief_boost=runtime.DECISION_RELIEF_THRESHOLD,
        steps=runtime.DECISION_SUSTAIN_STEPS,
    )

    # --------------------------------------------------
    # Phase 3: allow latch to fire (or fail honestly)
    # --------------------------------------------------
    for _ in range(200):
        runtime.step()
        if runtime.get_decision_state() is not None:
            break

    decision = runtime.get_decision_state()
    assert decision is not None, "No decision occurred; no episode to analyze"

    # --------------------------------------------------
    # Extract closed episode
    # --------------------------------------------------
    tracker: EpisodeTracker = runtime.episode_hook.tracker
    episode = tracker.last_closed_episode()

    assert episode is not None
    assert episode.closed

    # --------------------------------------------------
    # Proto-structural extraction
    # --------------------------------------------------
    adapter = EpisodicSignatureAdapter()
    signature = adapter.build_signature(
        episode=episode,
        episode_trace=tracker._trace,
    )

    accumulator = PatternAccumulator()
    accumulator.ingest([signature])

    record = accumulator.snapshot()
    stats = PatternStatisticsBuilder().build(record=record)

    # --------------------------------------------------
    # Assertions: pressure exists
    # --------------------------------------------------
    assert stats.total_occurrences == 1
    assert stats.total_signatures == 1

##passed validation##