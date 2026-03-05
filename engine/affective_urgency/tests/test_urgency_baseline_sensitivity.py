from __future__ import annotations

from pathlib import Path
import time

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

URGENCY_RISE = 0.002
URGENCY_DECAY = 0.001


# ============================================================
# Helpers
# ============================================================

def summarize(label: str, deltas, reliefs, decisions):
    print(f"\n[{label}]")
    print(f"mean delta = {sum(deltas)/len(deltas):.6f}")
    print(f"max  delta = {max(deltas):.6f}")
    print(f"GPi relief peak = {max(reliefs):.6f}")
    print(f"decision events = {decisions}")


# ============================================================
# Test
# ============================================================

def main():
    print("=== URGENCY BASELINE SENSITIVITY TEST ===")

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

    # -----------------------------
    # Disable other systems
    # -----------------------------
    rt.enable_salience = False
    rt.enable_vta_value = False
    rt.enable_decision_bias = True   # bias exists but no drivers
    rt.enable_urgency = True

    # Configure urgency
    rt.urgency_signal.enabled = True
    rt.urgency_signal.rise_rate = URGENCY_RISE
    rt.urgency_signal.decay_rate = URGENCY_DECAY

    deltas = []
    reliefs = []
    decision_events = 0

    # -----------------------------
    # Baseline settle
    # -----------------------------
    for _ in range(BASELINE_STEPS):
        rt.step()

    print("[BASELINE] settled")

    # -----------------------------
    # Urgency active phase
    # -----------------------------
    for i in range(TEST_STEPS):
        rt.step()

        snap = getattr(rt, "_last_striatum_snapshot", {})
        dom = snap.get("dominance", {})

        if len(dom) >= 2:
            vals = sorted(dom.values(), reverse=True)
            deltas.append(vals[0] - vals[1])
        else:
            deltas.append(0.0)

        reliefs.append(rt.snapshot_gate_state()["relief"])

        if rt.get_decision_state() is not None:
            decision_events += 1

        if i % REPORT_EVERY == 0 and i > 0:
            print(
                f"[STEP {i}] "
                f"delta={deltas[-1]:.6f} "
                f"relief={reliefs[-1]:.4f} "
                f"urgency={rt.urgency_adapter.last_urgency:.4f}"
            )

    summarize("URGENCY", deltas, reliefs, decision_events)

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
