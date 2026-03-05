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

# Value signal (authorization pressure)
VALUE_MAG = 0.6

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

    trace = rt.urgency_trace
    last = trace.last() if trace else None
    urgency = last["urgency"] if last else 0.0

    print(
        f"[STEP {step}] "
        f"delta={delta:.6f} "
        f"relief={relief:.4f} "
        f"urgency={urgency:.4f}"
    )

# ============================================================
# Test
# ============================================================

def main():
    print("=== URGENCY × VALUE TEST (NO SALIENCE) ===")

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

    # ---------------- Enable systems ----------------
    rt.enable_competition = True
    rt.enable_urgency = True
    rt.enable_vta_value = True

    # Explicitly DISABLE salience
    rt.enable_salience = False

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------
    print("[BASELINE] settling")
    for _ in range(BASELINE_STEPS):
        rt.step()
    print("[BASELINE] settled")

    # --------------------------------------------------------
    # Apply sustained value (authorization only)
    # --------------------------------------------------------
    print(f"[VALUE] setting value = {VALUE_MAG}")
    rt.value_set(VALUE_MAG)

    # --------------------------------------------------------
    # Run test
    # --------------------------------------------------------
    for step in range(1, TEST_STEPS + 1):
        rt.step()

        if step % REPORT_EVERY == 0:
            log_step(rt, step)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------
    trace = rt.urgency_trace
    records = trace.records() if trace else []

    if records:
        summary = trace.summary()
        print("\n[URGENCY]")
        print(f"mean urgency = {summary.get('mean_urgency', 0.0):.6f}")
        print(f"max  urgency = {summary.get('max_urgency', 0.0):.6f}")
    else:
        print("\n[URGENCY] no urgency recorded (unexpected)")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
