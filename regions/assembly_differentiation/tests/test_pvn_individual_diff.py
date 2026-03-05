from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

from regions.assembly_differentiation.pvn import PVNDifferentiationAdapter


BASE_DIR = Path(__file__).resolve().parents[3]


def test_pvn_structural_differentiation_trace():
    """
    Minimal grounding trace:
    Single PVN poke, log per-assembly firing rates for 10 steps.
    """

    # --------------------------------------------------
    # Build runtime
    # --------------------------------------------------
    loader = NeuralFrameworkLoader(BASE_DIR)

    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile()
    runtime = BrainRuntime(brain)

    # Explicitly neutralize higher systems
    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_salience = False

    # --------------------------------------------------
    # Apply PVN differentiation
    # --------------------------------------------------
    adapter = PVNDifferentiationAdapter(attenuation=0.25)
    adapter.apply(runtime)

    muted_ids = set(adapter.dump_state()["muted_assemblies"])

    # --------------------------------------------------
    # Locate PVN assemblies
    # --------------------------------------------------
    region = runtime.region_states["hypothalamus"]
    assemblies = region["populations"]["PARAVENTRICULAR_NUCLEUS"]

    assert len(assemblies) == 5, "Expected exactly 5 PVN assemblies"

    # --------------------------------------------------
    # Stimulation + logging
    # --------------------------------------------------
    STEPS = 10
    CURRENT = 0.05

    print("\n[PVN SINGLE-POKE TRACE]")
    print("step | asm | structural_gain | firing_rate")

    for step in range(STEPS):
        # identical injection into all assemblies
        for idx, _a in enumerate(assemblies):
            runtime.inject_stimulus(
                "hypothalamus",
                "PARAVENTRICULAR_NUCLEUS",
                idx,
                CURRENT,
            )

        runtime.step()

        for a in assemblies:
            sg = getattr(a, "_structural_gain", 1.0)
            label = "MUTED" if a.assembly_id in muted_ids else "NORM "
            print(
                f"{step:>4} | "
                f"{label} | "
                f"{a.assembly_id:<40} | "
                f"{sg:>5.2f} | "
                f"{a.output():.6f}"
            )


if __name__ == "__main__":
    test_pvn_structural_differentiation_trace()
