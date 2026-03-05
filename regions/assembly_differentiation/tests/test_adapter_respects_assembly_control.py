from __future__ import annotations

from pathlib import Path
from typing import List

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

from regions.assembly_differentiation.adapter import (
    AssemblyDifferentiationAdapter,
)

BASE_DIR = Path(__file__).resolve().parents[3]


def test_adapter_uses_assembly_control_cardinality(monkeypatch):
    """
    Audit test:
    Adapter must pass exactly the number of assemblies
    declared in config/assembly_control.json.
    """

    # --------------------------------------------------
    # Build runtime (no stepping)
    # --------------------------------------------------
    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile()
    runtime = BrainRuntime(brain)

    # --------------------------------------------------
    # Capture what differentiate() receives
    # --------------------------------------------------
    received: List[int] = []

    def fake_differentiate(*, region_name, assemblies, seed):
        if region_name == "hypothalamus":
            received.append(len(assemblies))

    # Patch the hypothalamus differentiation module
    module = AssemblyDifferentiationAdapter._load_region_module("hypothalamus")
    assert module is not None

    monkeypatch.setattr(module, "differentiate", fake_differentiate)

    # --------------------------------------------------
    # Apply adapter
    # --------------------------------------------------
    AssemblyDifferentiationAdapter.apply(runtime=runtime)

    # --------------------------------------------------
    # Assert against control file
    # --------------------------------------------------
    assert len(received) == 1, "Differentiate should be called once for hypothalamus"

    expected = AssemblyDifferentiationAdapter._load_assembly_control()["hypothalamus"]
    assert received[0] == expected, (
        f"Adapter passed {received[0]} assemblies, "
        f"expected {expected} from assembly_control.json"
    )
