from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

from regions.assembly_differentiation.adapter import (
    AssemblyDifferentiationAdapter,
)

BASE_DIR = Path(__file__).resolve().parents[3]


def test_adapter_allows_partial_assembly_touch(monkeypatch):
    """
    Audit test:
    Differentiation modules may legally touch a subset
    of declared assemblies without raising errors.
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

    # --------------------------------------------------
    # Fake differentiation touching only indices {1, 4}
    # --------------------------------------------------
    def fake_differentiate(*, region_name, assemblies, seed):
        targets = {1, 4}
        for idx, a in enumerate(assemblies):
            if idx in targets:
                a._structural_gain = 0.5

    module = AssemblyDifferentiationAdapter._load_region_module("hypothalamus")
    assert module is not None

    monkeypatch.setattr(module, "differentiate", fake_differentiate)

    # --------------------------------------------------
    # Apply adapter (this must NOT throw)
    # --------------------------------------------------
    AssemblyDifferentiationAdapter.apply(runtime=runtime)

    # --------------------------------------------------
    # Verify only those assemblies were touched
    # --------------------------------------------------
    region = runtime.region_states["hypothalamus"]
    assemblies = region["populations"]["PARAVENTRICULAR_NUCLEUS"]

    gains = [
        getattr(a, "_structural_gain", 1.0)
        for a in assemblies
    ]

    assert gains[1] == 0.5
    assert gains[4] == 0.5

    for i, g in enumerate(gains):
        if i not in (1, 4):
            assert g == 1.0, f"Assembly {i} was modified unexpectedly"
