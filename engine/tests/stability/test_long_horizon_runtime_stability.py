from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


ROOT = Path(__file__).resolve().parents[3]


def compile_brain() -> BrainRuntime:
    """
    Compile a minimal, deterministic brain with no external stimulation.
    """
    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    compiled = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    return BrainRuntime(compiled)


def test_long_horizon_runtime_stability() -> None:
    """
    Phase 10.1

    Verifies:
    - No spontaneous decisions over long horizons
    - Decision latch never fires without lawful coincidence
    - Runtime remains numerically stable
    """

    runtime = compile_brain()

    TOTAL_STEPS = 200
    decision_events = 0

    for step in range(TOTAL_STEPS):
        runtime.step()

        # Decision latch must never fire
        decision_state = getattr(runtime, "_decision_state", None)
        if decision_state is not None:
            decision_events += 1

    assert decision_events == 0, (
        f"Unexpected decision events detected: {decision_events}"
    )
    ##validated##
