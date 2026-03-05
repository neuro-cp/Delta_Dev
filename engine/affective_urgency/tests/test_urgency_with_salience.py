from __future__ import annotations

from pathlib import Path
import time

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

ROOT = Path(__file__).resolve().parents[3]
DT = 0.01

BASELINE_STEPS = 300
TEST_STEPS = 800
REPORT_EVERY = 50

TARGET_REGION = "striatum"
TARGET_POP = "D1"

def main() -> None:
    print("=== URGENCY × SALIENCE (SPARSITY) TEST ===")

    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    rt = BrainRuntime(brain, dt=DT)

    # Enable systems explicitly
    rt.enable_salience = True
    rt.enable_urgency = True

    # -------------------------
    # Baseline settling
    # -------------------------
    print("[BASELINE] settling")
    for _ in range(BASELINE_STEPS):
        rt.step()
    print("[BASELINE] settled")

    # -------------------------
    # Structural salience injection
    # -------------------------
    print("[SALIENCE] inducing sparsity via asymmetric drive")

    for _ in range(TEST_STEPS):
        # Asymmetric cortical drive → salience via sparsity gate
        rt.inject_stimulus(
            TARGET_REGION,
            population_id=TARGET_POP,
            magnitude=1.2,
        )

        rt.step()

        if rt.step_count % REPORT_EVERY == 0:
            snap = getattr(rt, "_last_striatum_snapshot", {})
            dom = snap.get("dominance", {})
            delta = 0.0
            if len(dom) >= 2:
                vals = sorted(dom.values(), reverse=True)
                delta = vals[0] - vals[1]

            relief = rt.snapshot_gate_state()["relief"]
            urg = getattr(rt.urgency_adapter, "last_urgency", 0.0)

            print(
                f"[STEP {rt.step_count}] "
                f"delta={delta:.6f} "
                f"relief={relief:.4f} "
                f"urgency={urg:.4f}"
            )

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
