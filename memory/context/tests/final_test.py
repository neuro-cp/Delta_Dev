from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DT = 0.01

BASELINE_STEPS = 300
TEST_STEPS = 800
REPORT_EVERY = 50

# Canonical operating point (validated earlier)
CANON_VALUE = 0.74

# Forced sanity parameters
FORCED_CONTEXT = 0.8
FORCED_VALUE = 1.0

# Coincidence parameters
COINCIDENCE_CONTEXT = 0.25
COINCIDENCE_POKE_START = 120
COINCIDENCE_POKE_END = 160

# Rejection parameters
REJECT_CONTEXT = 0.20
REJECT_POKE_START = 200
REJECT_POKE_END = 240


# ============================================================
# HELPERS
# ============================================================

def snapshot(runtime: BrainRuntime) -> Dict[str, Any]:
    snap = getattr(runtime, "_last_striatum_snapshot", None)

    delta_dom = None
    winner = None

    if snap and snap.get("dominance"):
        vals = sorted(snap["dominance"].values(), reverse=True)
        if len(vals) >= 2:
            delta_dom = vals[0] - vals[1]
        winner = snap.get("winner")

    return {
        "step": runtime.step_count,
        "winner": winner,
        "delta_dom": delta_dom,
        "relief": runtime._last_gate_strength,
        "ctx_max": runtime.context.stats()["max_gain"],
    }


def build_runtime() -> BrainRuntime:
    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    return BrainRuntime(brain, dt=DT)


def inject_context(runtime: BrainRuntime, gain: float, channel: Optional[str] = None):
    if gain <= 0.0:
        return

    pfc = runtime.region_states.get("pfc")
    if not pfc:
        return

    for pop_name, plist in pfc["populations"].items():
        if channel and channel not in pop_name:
            continue
        for p in plist:
            runtime.context.add_gain(p.assembly_id, gain, "global")


def sustain_vta(runtime: BrainRuntime, value: float):
    runtime.inject_stimulus("vta", None, None, value)
    runtime.inject_stimulus("md", None, None, 1.0)


# ============================================================
# TEST 1: FORCED SANITY WIN
# ============================================================

def test_forced_win():
    print("\n=== TEST 1: FORCED SANITY WIN ===")

    runtime = build_runtime()

    for _ in range(BASELINE_STEPS):
        runtime.step()

    inject_context(runtime, FORCED_CONTEXT)
    sustain_vta(runtime, FORCED_VALUE)

    for _ in range(TEST_STEPS):
        runtime.step()
        d = runtime.get_decision_state()
        if d:
            print(
                f"FORCED FIRE | step={d['step']} "
                f"| winner={d['winner']} "
                f"| relief={d['relief']:.3f}"
            )
            return

    print("FORCED TEST FAILED (unexpected)")


# ============================================================
# TEST 2: COINCIDENCE (SHOULD FIRE)
# ============================================================

def test_coincidence():
    print("\n=== TEST 2: COINCIDENCE (SHOULD FIRE) ===")

    runtime = build_runtime()

    for _ in range(BASELINE_STEPS):
        runtime.step()

    for i in range(TEST_STEPS):
        sustain_vta(runtime, CANON_VALUE)

        if COINCIDENCE_POKE_START <= i <= COINCIDENCE_POKE_END:
            inject_context(runtime, COINCIDENCE_CONTEXT)

        runtime.step()

        if i % REPORT_EVERY == 0:
            s = snapshot(runtime)
            print(
                f"[{s['step']:5d}] relief={s['relief']:.3f} "
                f"winner={s['winner']} "
                f"delta={s['delta_dom']} "
                f"ctx={s['ctx_max']:.3f}"
            )

        d = runtime.get_decision_state()
        if d:
            print(
                f"COINCIDENCE FIRE | step={d['step']} "
                f"| winner={d['winner']} "
                f"| relief={d['relief']:.3f}"
            )
            return

    print("COINCIDENCE FAILED (unexpected)")


# ============================================================
# TEST 3: REJECTION (SHOULD NOT FIRE)
# ============================================================

def test_rejection():
    print("\n=== TEST 3: REJECTION (SHOULD NOT FIRE) ===")

    runtime = build_runtime()

    for _ in range(BASELINE_STEPS):
        runtime.step()

    for i in range(TEST_STEPS):
        sustain_vta(runtime, CANON_VALUE)

        if REJECT_POKE_START <= i <= REJECT_POKE_END:
            inject_context(runtime, REJECT_CONTEXT)

        runtime.step()

        if i % REPORT_EVERY == 0:
            s = snapshot(runtime)
            print(
                f"[{s['step']:5d}] relief={s['relief']:.3f} "
                f"winner={s['winner']} "
                f"delta={s['delta_dom']} "
                f"ctx={s['ctx_max']:.3f}"
            )

        d = runtime.get_decision_state()
        if d:
            print(
                f"REJECTION FAILED | step={d['step']} "
                f"| winner={d['winner']}"
            )
            return

    print("REJECTION PASSED (no decision)")


# ============================================================
# MAIN
# ============================================================

def main():
    test_forced_win()
    test_coincidence()
    test_rejection()
    print("\n=== ALL SANITY TESTS COMPLETE ===")


if __name__ == "__main__":
    main()
