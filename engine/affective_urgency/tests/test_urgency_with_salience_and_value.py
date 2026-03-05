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

# Asymmetric drive parameters (lawful salience induction)
TARGET_REGION = "striatum"
TARGET_POP = "D1"
POKE_MAG = 0.6
POKE_EVERY = 5        # sustain asymmetry
POKE_DURATION = 400  # steps

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
    records = trace.records()

    if len(records) >= 2:
        u_now = records[-1]["urgency"]
        u_prev = records[-2]["urgency"]
        du = u_now - u_prev
    elif records:
        u_now = records[-1]["urgency"]
        du = 0.0
    else:
        u_now = 0.0
        du = 0.0

    print(
        f"[STEP {step}] "
        f"delta={delta:.6f} "
        f"relief={relief:.4f} "
        f"urgency={u_now:.6f} "
        f"dU/step={du:.6f}"
    )

# ============================================================
# Test
# ============================================================

def main():
    print("=== URGENCY × SALIENCE (CONTINUOUS VIEW, NO VALUE) ===")

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
    rt.enable_salience = True
    rt.enable_urgency = True

    # Explicitly disable value
    rt.enable_vta_value = False

    # ------------------------------------------------
    # Baseline
    # ------------------------------------------------
    print("[BASELINE] settling")
    for _ in range(BASELINE_STEPS):
        rt.step()
    print("[BASELINE] settled")

    # ------------------------------------------------
    # Test loop
    # ------------------------------------------------
    print("[SALIENCE] inducing sustained asymmetry")

    for step in range(1, TEST_STEPS + 1):

        # Sustain lawful asymmetry
        if step <= POKE_DURATION and step % POKE_EVERY == 0:
            rt.inject_stimulus(
                TARGET_REGION,
                TARGET_POP,
                magnitude=POKE_MAG,
            )

        rt.step()

        if step % REPORT_EVERY == 0:
            log_step(rt, step)

    # ------------------------------------------------
    # Summary (ground truth)
    # ------------------------------------------------
    trace = rt.urgency_trace
    records = trace.records()

    if records:
        summary = trace.summary()
        print("\n[URGENCY TRACE]")
        print(f"samples        = {summary['count']}")
        print(f"mean urgency   = {summary['mean_urgency']:.6f}")
        print(f"max  urgency   = {summary['max_urgency']:.6f}")

        # Show final slope (sanity)
        if len(records) >= 2:
            du_final = records[-1]["urgency"] - records[-2]["urgency"]
            print(f"final dU/step  = {du_final:.6f}")
    else:
        print("\n[URGENCY] no urgency recorded (unexpected)")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
