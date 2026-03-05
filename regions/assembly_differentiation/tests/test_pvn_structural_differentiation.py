from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from unittest import loader

import numpy as np

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

from regions.assembly_differentiation.pvn import PVNDifferentiationAdapter


BASE_DIR = Path(__file__).resolve().parents[3]


def test_pvn_structural_differentiation_effect():
    """
    Grounding test:
    Identical stimulation -> differentiated assemblies diverge in activity.
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

    # Sanity: no salience/value/urgency
    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_salience = False


    # --------------------------------------------------
    # Apply PVN differentiation
    # --------------------------------------------------
    adapter = PVNDifferentiationAdapter(attenuation=0.25)
    adapter.apply(runtime)

    muted_ids = set(adapter.dump_state()["muted_assemblies"])
    assert len(muted_ids) == 2, "Expected exactly 2 muted PVN assemblies"

    # --------------------------------------------------
    # Locate PVN assemblies
    # --------------------------------------------------
    region = runtime.region_states["hypothalamus"]
    assemblies = region["populations"]["PARAVENTRICULAR_NUCLEUS"]

    assert len(assemblies) == 5

    muted = [a for a in assemblies if a.assembly_id in muted_ids]
    normal = [a for a in assemblies if a.assembly_id not in muted_ids]

    # --------------------------------------------------
    # Stimulation protocol
    # --------------------------------------------------
    STEPS = 40
    CURRENT = 0.05

    traces: Dict[str, List[float]] = {
        a.assembly_id: [] for a in assemblies
    }

    for _ in range(STEPS):
        # identical injection into ALL assemblies
        for idx, _a in enumerate(assemblies):
            runtime.inject_stimulus(
                "hypothalamus",
                "PARAVENTRICULAR_NUCLEUS",
                idx,
                float(CURRENT),
            )



        runtime.step()

        for a in assemblies:
            traces[a.assembly_id].append(a.output())

    # --------------------------------------------------
    # Analysis
    # --------------------------------------------------
    muted_means = [
        np.mean(traces[a.assembly_id]) for a in muted
    ]
    normal_means = [
        np.mean(traces[a.assembly_id]) for a in normal
    ]

    mean_muted = float(np.mean(muted_means))
    mean_normal = float(np.mean(normal_means))

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert mean_muted < mean_normal, (
        f"Muted assemblies not suppressed: "
        f"muted={mean_muted:.4f}, normal={mean_normal:.4f}"
    )

    # muted assemblies should be similar to each other
    assert np.std(muted_means) < np.std(normal_means) * 1.5

    # non-muted assemblies should cluster tightly
    assert np.std(normal_means) < mean_normal * 0.25

    print(
        "[OK] PVN differentiation grounding passed\n"
        f"  mean_normal = {mean_normal:.4f}\n"
        f"  mean_muted  = {mean_muted:.4f}\n"
        f"  muted_ids  = {sorted(muted_ids)}"
    )
if __name__ == "__main__":
    test_pvn_structural_differentiation_effect()
