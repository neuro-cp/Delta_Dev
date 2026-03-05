# engine/routing/tests/test_hypothesis_pressure_observational.py
from __future__ import annotations

import time

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server


BASE_DIR = r"C:\Users\Admin\Desktop\neural framework"


def main():
    print("=== HYPOTHESIS PRESSURE OBSERVATIONAL TEST ===")

    # ------------------------------------------------------------
    # Load brain
    # ------------------------------------------------------------
    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain, dt=0.01)

    # Safety: no urgency, no decision FX amplification
    runtime.enable_urgency = False
    runtime.enable_decision_fx = False

    # Start command server for live inspection
    start_command_server(runtime)

    print("\nLIVE RUNTIME | OBSERVATIONAL")
    print("Port 5557 | Ctrl+C to quit")
    print("Default view: POPULATIONS")
    print("-" * 100)

    # ------------------------------------------------------------
    # Phase 1: baseline (no stimulation)
    # ------------------------------------------------------------
    print("[PHASE 1] Baseline (no stimulation)")
    for _ in range(200):
        runtime.step()

    # ------------------------------------------------------------
    # Phase 2: sustained cortical bias
    # ------------------------------------------------------------
    print("[PHASE 2] Sustained association cortex stimulation")
    print("Injecting small, repeated assembly-level input")

    for step in range(600):
        # Every 5 steps, nudge association cortex assemblies
        if step % 5 == 0:
            runtime.inject_stimulus(
                region_id="association_cortex",
                magnitude=0.12,  # deliberately sub-decisional
            )

        runtime.step()

        # Periodic logging
        if step % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {}) or {}
            dom = snap.get("dominance", {})
            relief = runtime.snapshot_gate_state().get("relief", None)

            print(
                f"[STEP {step:04d}] "
                f"dominance={ {k: round(v, 4) for k, v in dom.items()} } "
                f"relief={round(relief, 4) if relief is not None else 'n/a'}"
            )

    # ------------------------------------------------------------
    # Phase 3: withdrawal
    # ------------------------------------------------------------
    print("[PHASE 3] Withdrawal (no stimulation)")
    for step in range(300):
        runtime.step()

        if step % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {}) or {}
            dom = snap.get("dominance", {})
            relief = runtime.snapshot_gate_state().get("relief", None)

            print(
                f"[WITHDRAW {step:04d}] "
                f"dominance={ {k: round(v, 4) for k, v in dom.items()} } "
                f"relief={round(relief, 4) if relief is not None else 'n/a'}"
            )

    print("\n=== TEST COMPLETE ===")
    print("No asserts. Inspect dominance, gate relief, and hypothesis behavior.")


if __name__ == "__main__":
    main()
