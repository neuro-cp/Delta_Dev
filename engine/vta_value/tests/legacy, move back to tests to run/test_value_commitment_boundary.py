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
VALUE_STEPS = 800

VALUE_START = 0.40
VALUE_END   = 0.84
VALUE_STEP  = 0.02


# ============================================================
# Helpers (CANONICAL)
# ============================================================

def dominance_delta(rt: BrainRuntime) -> float:
    pops = rt.region_states["striatum"]["populations"]
    d1 = sum(p.output() for p in pops["D1_MSN"])
    d2 = sum(p.output() for p in pops["D2_MSN"])
    return abs(d1 - d2)


def gpi_relief(rt: BrainRuntime) -> float:
    # ✔ Canonical, shared with Value × Salience test
    return rt.snapshot_gate_state()["relief"]


def latch_state(rt: BrainRuntime) -> tuple[bool, bool, int]:
    latch = getattr(rt, "decision_latch", None)
    if latch is None:
        return False, False, 0

    armed = bool(getattr(latch, "armed", False))
    committed = bool(getattr(latch, "committed", False))
    count = int(getattr(latch, "decision_count", 0))

    return armed, committed, count


# ============================================================
# Test
# ============================================================

def main() -> None:
    print("=== TEST: Value commitment boundary (observational) ===")

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

    # FX must remain disabled
    rt.enable_decision_fx = False

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
    # Value sweep
    # --------------------------------------------------------
    value = VALUE_START

    while value <= VALUE_END + 1e-9:
        print(f"\n[VALUE] magnitude = {value:.2f}")

        rt.enable_vta_value = True
        rt.vta_value_mag = value

        deltas = []
        reliefs = []

        peak_relief = None
        decline_confirmed = False

        armed = committed = False
        decisions_before = latch_state(rt)[2]

        for step in range(VALUE_STEPS):
            rt.step()

            d = dominance_delta(rt)
            r = gpi_relief(rt)

            deltas.append(d)
            reliefs.append(r)

            if peak_relief is None or r > peak_relief:
                peak_relief = r
            elif r < peak_relief and not decline_confirmed:
                print(
                    f"[INFO] GPi relief peak reached at "
                    f"{peak_relief:.6f}, decline confirmed after {step} steps"
                )
                decline_confirmed = True
                break

        armed, committed, decisions_after = latch_state(rt)

        print(f"[VALUE] peak delta = {max(deltas):.6f}")
        print(f"[VALUE] mean delta = {statistics.mean(deltas):.6f}")
        print(f"[VALUE] GPi relief peak = {max(reliefs):.6f}")
        print(f"[VALUE] latch armed = {armed}")
        print(f"[VALUE] committed = {committed}")
        print(f"[VALUE] decision events = {decisions_after - decisions_before}")

        # Clean reset
        rt.enable_vta_value = False
        rt.vta_value_mag = 0.0

        value += VALUE_STEP

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
