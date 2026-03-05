# engine/routing/tests/test_hypothesis_routing_observational.py
from __future__ import annotations

import time
from zipfile import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server


def main():
    print("\n=== HYPOTHESIS ROUTING — OBSERVATIONAL TEST ===\n")

    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parents[3]
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
    runtime.enable_urgency = False
    runtime.enable_decision_fx = False

    start_command_server(runtime)
    print("LIVE RUNTIME | OBSERVATIONAL")
    print("Port 5557 | Ctrl+C to quit")
    print("-" * 100)

    # ------------------------------------------------------------
    # PHASE 1 — Baseline
    # ------------------------------------------------------------
    print("[PHASE 1] Baseline (no hypotheses, no stimulation)")
    for i in range(200):
        runtime.step()
        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            print(
                f"[BASE {i:04d}] dominance={snap.get('dominance')} "
                f"relief={runtime.snapshot_gate_state()['relief']:.4f}"
            )

    # ------------------------------------------------------------
    # PHASE 2 — Hypothesis assignment (structural only)
    # ------------------------------------------------------------
    print("\n[PHASE 2] Assigning hypotheses to association cortex assemblies")

    assoc = runtime.region_states.get("association_cortex")
    if not assoc:
        raise RuntimeError("association_cortex not found")

    assemblies = [
        p for plist in assoc["populations"].values() for p in plist
    ]

    if len(assemblies) < 2:
        raise RuntimeError("Not enough association cortex assemblies")

    # Assign competing hypotheses
    runtime.hypothesis_registry.register(assemblies[0].assembly_id, "H1")
    runtime.hypothesis_registry.register(assemblies[1].assembly_id, "H2")

    print(
        f"Assigned:\n"
        f"  {assemblies[0].assembly_id} → H1\n"
        f"  {assemblies[1].assembly_id} → H2"
    )

    # ------------------------------------------------------------
    # PHASE 3 — Weak sustained cortical drive
    # ------------------------------------------------------------
    print("\n[PHASE 3] Sustained weak association cortex stimulation")

    for i in range(600):
        runtime.inject_stimulus(
            region_id="association_cortex",
            magnitude=0.02,
        )

        runtime.step()

        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            routing = snap.get("routing", {})
            print(
                f"[STEP {i:04d}] "
                f"routing={routing} "
                f"dominance={snap.get('dominance')} "
                f"relief={runtime.snapshot_gate_state()['relief']:.4f}"
            )

    # ------------------------------------------------------------
    # PHASE 4 — Withdrawal
    # ------------------------------------------------------------
    print("\n[PHASE 4] Withdrawal (no stimulation)")

    for i in range(300):
        runtime.step()
        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            print(
                f"[WITHDRAW {i:04d}] dominance={snap.get('dominance')} "
                f"relief={runtime.snapshot_gate_state()['relief']:.4f}"
            )

    print("\n=== TEST COMPLETE ===")
    print("Inspect routing → dominance → relief causality.")
    print("No asserts by design.\n")


if __name__ == "__main__":
    main()
