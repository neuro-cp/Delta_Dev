# engine/routing/tests/test_hypothesis_salience_sparsity_observational.py
from __future__ import annotations

import time
from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


BASE_DIR = Path(__file__).resolve().parents[3]


def main():
    print("\n=== HYPOTHESIS × SALIENCE SPARSITY (OBSERVATIONAL) ===\n")

    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain)
    runtime.enable_salience = True
    runtime.enable_pre_decision_adaptation = False

    # --- Enable sparsity gate explicitly ---
    if hasattr(runtime.salience, "enable_sparsity"):
        runtime.salience.enable_sparsity = True

    print("[PHASE 1] Baseline (no hypotheses)")
    for i in range(200):
        runtime.step()
        if i % 100 == 0:
            snap = runtime._last_striatum_snapshot or {}
            print(
                f"[BASE {i:04d}] "
                f"dominance={snap.get('dominance')} "
                f"relief={runtime.snapshot_gate_state()['relief']:.4f}"
            )

    # --- Assign hypotheses to association cortex assemblies ---
    assoc = runtime.region_states.get("association_cortex")
    assemblies = [
        p for plist in assoc["populations"].values() for p in plist
    ]

    print("\n[PHASE 2] Assigning hypotheses")
    for i, p in enumerate(assemblies[:2]):
        hid = f"H{i+1}"
        runtime.hypothesis_registry.register(p.assembly_id, hid)
        print(f"  {p.assembly_id} → {hid}")

    # --- Weak sustained stimulation ---
    print("\n[PHASE 3] Sustained weak stimulation with sparsity")
    for step in range(500):
        runtime.inject_stimulus(
            region_id="association_cortex",
            magnitude=0.12,
        )
        runtime.step()

        if step % 100 == 0:
            snap = runtime._last_striatum_snapshot or {}
            active = [
                aid for aid, v in snap.get("instant", {}).items() if v > 0.01
            ]
            print(
                f"[STEP {step:04d}] "
                f"active={len(active)} "
                f"dominance={snap.get('dominance')} "
                f"relief={runtime.snapshot_gate_state()['relief']:.4f}"
            )

    print("\n[PHASE 4] Withdrawal")
    for i in range(200):
        runtime.step()
        if i % 100 == 0:
            snap = runtime._last_striatum_snapshot or {}
            print(
                f"[WITHDRAW {i:04d}] "
                f"dominance={snap.get('dominance')} "
                f"relief={runtime.snapshot_gate_state()['relief']:.4f}"
            )

    print("\n=== TEST COMPLETE ===")
    print("Inspect active assembly count vs dominance vs relief.")
    print("No asserts by design.")


if __name__ == "__main__":
    main()
