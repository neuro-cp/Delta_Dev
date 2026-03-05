from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[3]
DT = 0.01

BASELINE_STEPS = 300
TEST_STEPS = 800
REPORT_EVERY = 50

# Salience (lawful asymmetry)
TARGET_REGION = "striatum"
TARGET_POP = "D1"
POKE_MAG = 0.6
POKE_EVERY = 5
POKE_DURATION = 400

# Value
VALUE_LEVEL = 0.6

# ============================================================
# Helpers
# ============================================================

def log_step(rt: BrainRuntime, step: int):
    snap = getattr(rt, "_last_striatum_snapshot", {}) or {}
    dom = snap.get("dominance", {})

    delta = 0.0
    if len(dom) >= 2:
        vals = sorted(dom.values(), reverse=True)
        delta = vals[0] - vals[1]

    relief = rt.snapshot_gate_state().get("relief", 0.0)

    # 🔑 REAL URGENCY (adapter-level)
    urgency = getattr(rt.urgency_adapter, "last_urgency", 0.0)

    print(
        f"[STEP {step}] "
        f"delta={delta:.6f} "
        f"relief={relief:.4f} "
        f"urgency_eff={urgency:.6f}"
    )

# ============================================================
# Test
# ============================================================

def main():
    print("=== URGENCY ADAPTER COUPLING TEST ===")

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

    # --------------------------------------------------------
    # Explicit system enables (NO defaults)
    # --------------------------------------------------------
    rt.enable_competition = True
    rt.enable_salience = True

    rt.enable_vta_value = True
    rt.value_signal.enabled = True

    rt.enable_urgency = True
    rt.urgency_signal.enabled = True

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------
    print("[BASELINE] settling")
    for _ in range(BASELINE_STEPS):
        rt.step()
    print("[BASELINE] settled")

    # --------------------------------------------------------
    # Value authorization
    # --------------------------------------------------------
    print(f"[VALUE] setting value = {VALUE_LEVEL}")
    rt.value_set(VALUE_LEVEL)

    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------
    print("[SALIENCE] inducing sustained asymmetry")

    for step in range(1, TEST_STEPS + 1):

        if step <= POKE_DURATION and step % POKE_EVERY == 0:
            rt.inject_stimulus(
                TARGET_REGION,
                TARGET_POP,
                magnitude=POKE_MAG,
            )

        rt.step()

        if step % REPORT_EVERY == 0:
            log_step(rt, step)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------
    urg = getattr(rt.urgency_adapter, "last_urgency", 0.0)

    print("\n[URGENCY EFFECTIVE SUMMARY]")
    print(f"final effective urgency = {urg:.6f}")

    decision = rt.get_decision_state()
    print("\n[DECISION]")
    print(f"decision fired = {decision is not None}")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
