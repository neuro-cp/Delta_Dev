# engine/vta_value/tests/test_value_x_salience_interaction.py
from __future__ import annotations

import statistics
from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ============================================================
# CONFIG
# ============================================================

ROOT = Path("C:/Users/Admin/Desktop/neural framework")

DT = 0.01

BASELINE_STEPS = 300
SALIENCE_STEPS = 300
VALUE_STEPS = 800
POST_STEPS = 300

VALUE_MAG = 0.3   # deliberately modest
SAL_POKE = 1.0    # mild salience stimulus


# ============================================================
# Helpers (CANONICAL)
# ============================================================

def dominance_delta(rt: BrainRuntime) -> float:
    pops = rt.region_states["striatum"]["populations"]
    d1 = sum(p.output() for p in pops["D1_MSN"])
    d2 = sum(p.output() for p in pops["D2_MSN"])
    return abs(d1 - d2)


def gpi_relief(rt: BrainRuntime) -> float:
    return rt.snapshot_gate_state()["relief"]


# ============================================================
# Test
# ============================================================

def main() -> None:
    print("=== TEST: Value × Salience Interaction (observational) ===")

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

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------
    baseline = []

    for _ in range(BASELINE_STEPS):
        rt.step()
        baseline.append(dominance_delta(rt))

    print(f"[BASELINE] mean delta = {statistics.mean(baseline):.6f}")
    print(f"[BASELINE] max  delta = {max(baseline):.6f}")

    # --------------------------------------------------------
    # Salience only
    # --------------------------------------------------------
    sal_deltas = []
    sal_relief = []

    for _ in range(SALIENCE_STEPS):
        rt.inject_stimulus("pfc", magnitude=SAL_POKE)
        rt.step()

        sal_deltas.append(dominance_delta(rt))
        sal_relief.append(gpi_relief(rt))

    print(f"[SALIENCE] mean delta = {statistics.mean(sal_deltas):.6f}")
    print(f"[SALIENCE] peak delta = {max(sal_deltas):.6f}")
    print(f"[SALIENCE] GPi relief peak = {max(sal_relief):.6f}")

    # --------------------------------------------------------
    # Salience + Value
    # --------------------------------------------------------
    deltas = []
    reliefs = []

    peak_relief = None
    decline_confirmed = False

    for step in range(VALUE_STEPS):
        rt.value_set(VALUE_MAG)
        rt.inject_stimulus("pfc", magnitude=SAL_POKE)
        rt.step()

        d = dominance_delta(rt)
        r = gpi_relief(rt)

        deltas.append(d)
        reliefs.append(r)

        if r > 0.47:
            print(f"[WARN][VALUE+SAL] GPi relief high: {r:.4f} at step {step}")

        if peak_relief is None or r > peak_relief:
            peak_relief = r
        elif r < peak_relief and not decline_confirmed:
            print(
                f"[INFO] GPi relief peak reached at {peak_relief:.6f}, "
                f"decline confirmed after {step} steps"
            )
            decline_confirmed = True
            break

    print(f"[VALUE+SAL] peak delta = {max(deltas):.6f}")
    print(f"[VALUE+SAL] mean delta = {statistics.mean(deltas):.6f}")
    print(f"[VALUE+SAL] GPi relief peak = {max(reliefs):.6f}")

    # --------------------------------------------------------
    # Post recovery
    # --------------------------------------------------------
    post = []

    for _ in range(POST_STEPS):
        rt.step()
        post.append(dominance_delta(rt))

    print(f"[POST] mean delta = {statistics.mean(post):.6f}")
    print(f"[POST] max  delta = {max(post):.6f}")

    print("=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
