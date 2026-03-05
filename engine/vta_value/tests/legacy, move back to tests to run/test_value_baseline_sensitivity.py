# engine/vta_value/tests/test_value_baseline_sensitivity.py
from __future__ import annotations

import statistics
from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(r"C:/Users/Admin/Desktop/neural framework")

DT = 0.01

BASELINE_STEPS = 300
VALUE_STEPS = 400
POST_STEPS = 300

VALUE_MAG = 0.3   # deliberately modest


# ============================================================
# Helpers
# ============================================================

def dominance_delta(rt: BrainRuntime) -> float:
    """
    Absolute D1–D2 dominance delta at population level.
    """
    pops = rt.region_states["striatum"]["populations"]
    d1 = sum(p.output() for p in pops.get("D1_MSN", []))
    d2 = sum(p.output() for p in pops.get("D2_MSN", []))
    return abs(d1 - d2)


def gpi_relief(rt: BrainRuntime) -> float:
    """
    Authoritative GPi relief value as computed by runtime.
    """
    return getattr(rt, "_last_gate_strength", 1.0)


def decision_fired(rt: BrainRuntime) -> bool:
    """
    Whether a decision has been committed.
    """
    return rt.get_decision_state() is not None


# ============================================================
# Test
# ============================================================

def main() -> None:
    print("=== TEST: Value baseline sensitivity (observational) ===")

    # -------------------------
    # Build system
    # -------------------------
    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    rt = BrainRuntime(brain, dt=DT)

    # ============================================================
    # Baseline (no value)
    # ============================================================
    baseline_deltas = []

    for _ in range(BASELINE_STEPS):
        rt.step()
        baseline_deltas.append(dominance_delta(rt))

    print(f"[BASELINE] mean delta = {statistics.mean(baseline_deltas):.6f}")
    print(f"[BASELINE] max  delta = {max(baseline_deltas):.6f}")

    # -------------------------
    # Value phase (run until GPi peak then decline)
    # -------------------------
    rt.enable_vta_value = True
    rt.value_set(VALUE_MAG)

    value_deltas = []
    gpi_vals = []

    peak_relief = -1.0
    decline_count = 0
    DECLINE_STEPS_REQUIRED = 5  # hysteresis against noise

    step = 0
    while True:
        rt.step()

        d = dominance_delta(rt)
        g = gpi_relief(rt)

        value_deltas.append(d)
        gpi_vals.append(g)

        if g > peak_relief:
            peak_relief = g
            decline_count = 0
        else:
            decline_count += 1

        if g > 0.47:
            print(f"[WARN][VALUE] GPi relief high: {g:.4f} at step {step}")

        if decision_fired(rt):
            print(f"[WARN][VALUE] Decision fired unexpectedly at step {step}")
            break

        # Stop once we have clearly passed the peak
        if decline_count >= DECLINE_STEPS_REQUIRED:
            print(
                f"[INFO] GPi relief peak reached at {peak_relief:.6f}, "
                f"decline confirmed after {step} steps"
            )
            break

        step += 1


    # ============================================================
    # Post-value recovery
    # ============================================================
    rt.value_set(0.0)

    post_deltas = []

    for _ in range(POST_STEPS):
        rt.step()
        post_deltas.append(dominance_delta(rt))

    print(f"[POST] mean delta = {statistics.mean(post_deltas):.6f}")
    print(f"[POST] max  delta = {max(post_deltas):.6f}")

    print("=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
