# engine/salience/tests/test_salience_persistence_no_decision.py

from __future__ import annotations

import math
from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

ROOT = Path("C:/Users/Admin/Desktop/neural framework")

DT = 0.01
BASELINE_STEPS = 200
SALIENT_STEPS = 400
OBSERVE_STEPS = 300
MIN_HITS = 5
SALIENT_DELTA = 0.4        # intentionally moderate
DELTA_FLOOR = 0.003        # above baseline jitter
DELTA_CEILING = 0.08       # safety: no runaway


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def striatum_delta(runtime: BrainRuntime) -> float:
    pops = runtime.region_states["striatum"]["populations"]
    d1 = sum(p.output() for p in pops["D1_MSN"])
    d2 = sum(p.output() for p in pops["D2_MSN"])
    return abs(d1 - d2)


def decision_committed(runtime: BrainRuntime) -> bool:
    latch = getattr(runtime, "decision_latch", None)
    if latch is None:
        return False
    return bool(getattr(latch, "committed", False))


def gpi_relieved(runtime: BrainRuntime) -> float:
    gpi = runtime.region_states["gpi"]["populations"]["GPi_OUTPUT"]
    return sum(p.output() for p in gpi)


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

def main() -> None:
    print("=== TEST 5D: Salience persistence without decision ===")

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

    # -------------------------
    # Baseline
    # -------------------------
    for _ in range(BASELINE_STEPS):
        rt.step()

    baseline_delta = striatum_delta(rt)
    print(f"[BASELINE] delta = {baseline_delta:.4f}")

    # -------------------------
    # Salience injection
    # -------------------------

    striatum = rt.region_states["striatum"]["populations"]
    d1_assemblies = striatum["D1_MSN"]

    for _ in range(SALIENT_STEPS):
        for p in d1_assemblies:
            rt.salience.inject(p.assembly_id, SALIENT_DELTA)
        rt.step()

    # -------------------------
    # Persistence window
    # -------------------------
    deltas = []

    for _ in range(OBSERVE_STEPS):
        rt.step()
        deltas.append(striatum_delta(rt))

        # Hard safety checks (fail fast)
        assert not decision_committed(rt), "Decision latch committed unexpectedly"
        assert rt.get_decision_state() is None, "Decision fired under salience persistence"

    min_delta = min(deltas)
    max_delta = max(deltas)

    print(f"[OBSERVE] delta range = {min_delta:.4f} → {max_delta:.4f}")

    # -------------------------
    # Assertions
    # -------------------------
    assert sum(d > DELTA_FLOOR for d in deltas) >= MIN_HITS, \
    "Salience asymmetry not recurrent"

    assert max_delta < DELTA_CEILING, "Runaway dominance detected"

    print("[PASS] Salience-induced asymmetry persists without decision")
    print(f"[INFO] GPi relief range = {min(reliefs):.3f} → {max(reliefs):.3f}")


if __name__ == "__main__":
    main()
