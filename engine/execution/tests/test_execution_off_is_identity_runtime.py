from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


def _build_runtime() -> BrainRuntime:
    """
    Build a fresh BrainRuntime using the canonical loader lifecycle.
    """
    root = Path(__file__).resolve().parents[3]

    loader = NeuralFrameworkLoader(root)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    return BrainRuntime(brain)


def _snapshot(runtime: BrainRuntime) -> dict:
    """
    Capture a minimal but sufficient behavioral snapshot.
    """
    return {
        "gate": runtime.snapshot_gate_state(),
        "decision_bias": runtime.get_decision_bias(),
        "decision_fx": runtime.snapshot_decision_fx(),
        "context": dict(runtime.context.dump()) if runtime.enable_context else {},
        "regions": {
            k: runtime.snapshot_region_stats(k)
            for k in runtime.region_states.keys()
        },
    }


def test_execution_off_is_identity_runtime() -> None:
    """
    With execution disabled, runtime behavior must be identical
    to a baseline run with no execution influence.

    This test explicitly allows the runtime to pass through its
    natural stabilization (warm-up) phase before comparison.
    """

    rt_base = _build_runtime()
    rt_exec = _build_runtime()

    # NOTE:
    # Execution defaults to OFF and must behave as an identity transform.
    # We do NOT mutate execution_state directly (it is immutable by contract).

    # Enable subsystems so execution *could* matter
    rt_exec.enable_vta_value = True
    rt_exec.enable_decision_bias = True
    rt_exec.enable_pfc_adapter = True
    rt_exec.enable_decision_fx = True

    # ------------------------------------------------------------
    # Warm-up phase (allow dynamics to stabilize)
    # ------------------------------------------------------------
    for _ in range(300):
        rt_base.step()
        rt_exec.step()

    # ------------------------------------------------------------
    # Measurement window
    # ------------------------------------------------------------
    for _ in range(25):
        rt_base.step()
        rt_exec.step()

    snap_base = _snapshot(rt_base)
    snap_exec = _snapshot(rt_exec)

    # ------------------------------------------------------------
    # Identity assertions
    # ------------------------------------------------------------

    gate_base = snap_base["gate"]
    gate_exec = snap_exec["gate"]

    # Allow minimal floating-point drift after stabilization
    assert abs(gate_base["relief"] - gate_exec["relief"]) < 2e-5
    assert gate_base["decision"] == gate_exec["decision"]

    assert snap_base["decision_bias"] == snap_exec["decision_bias"]
    assert snap_base["decision_fx"] == snap_exec["decision_fx"]
    assert snap_base["context"] == snap_exec["context"]

    for region, stats_base in snap_base["regions"].items():
        stats_exec = snap_exec["regions"][region]

        if stats_base is None:
            assert stats_exec is None
            continue

        for k in ("mass", "mean", "std"):
            assert abs(stats_base[k] - stats_exec[k]) < 1e-9

        assert stats_base["n"] == stats_exec["n"]
##invalid##