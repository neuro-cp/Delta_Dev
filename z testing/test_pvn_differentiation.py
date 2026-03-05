from __future__ import annotations

from pathlib import Path
import json

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from regions.assembly_differentiation.pvn import PVNDifferentiationAdapter


BASE_DIR = Path(__file__).resolve().parent


def dump_pvn(runtime, step: int, out: dict):
    region = runtime.region_states["hypothalamus"]
    assemblies = region["populations"]["PARAVENTRICULAR_NUCLEUS"]

    snapshot = []
    for a in assemblies:
        snapshot.append({
            "assembly_id": a.assembly_id,
            "activity": float(a.activity),
            "structural_gain": getattr(a, "_structural_gain", 1.0),
        })

    out[str(step)] = snapshot


def main():
    # ----------------------------
    # Load + compile brain
    # ----------------------------
    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()
    brain = loader.compile()

    runtime = BrainRuntime(brain)

    # ----------------------------
    # Apply PVN differentiation
    # ----------------------------
    adapter = PVNDifferentiationAdapter(attenuation=0.25)
    adapter.apply(runtime)

    print("[PVN ADAPTER]", adapter.dump_state())

    # ----------------------------
    # Run short simulation
    # ----------------------------
    dump = {
        "adapter": adapter.dump_state(),
        "steps": {}
    }

    for step in range(40):
        runtime.step()

        if step in (0, 5, 10, 20, 39):
            dump_pvn(runtime, step, dump["steps"])

    # ----------------------------
    # Write dump
    # ----------------------------
    out_path = BASE_DIR / "pvn_differentiation_dump.json"
    with out_path.open("w") as f:
        json.dump(dump, f, indent=2)

    print(f"[OK] PVN dump written to {out_path}")


if __name__ == "__main__":
    main()
