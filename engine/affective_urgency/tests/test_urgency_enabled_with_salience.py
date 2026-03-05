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

# Urgency dynamics (NEW — minimal, safe)
URGENCY_RISE = 0.03
URGENCY_DECAY = 0.01

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
    print("=== URGENCY × SALIENCE TEST (URGENCY ENABLED, NO VALUE) ===")

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

    # ---------------- Enable urgency signal (CRITICAL) ----------------
    rt.urgency_signal.enabled = True
    rt.urgency_signal.rise_rate = URGENCY_RISE
    rt.urgency_signal.decay_rate = URGENCY_DECAY

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------
    print("[BASELINE] settling")
    for _ in range(BASELINE_STEPS):
        rt.step()
    print("[BASELINE] settled")

    # --------------------------------------------------------
    # Test loop
    # --------------------------------------------------------
    print("[SALIENCE] inducing sustained asymmetry")

    for step in range(1, TEST_STEPS + 1):

        # Sustain asymmetric drive
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
