from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, List

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

# Context (PFC gain)
CONTEXT_GAINS = [0.0, 0.1, 0.2, 0.3]

# Dopamine (VTA)
VALUE_MAGS = [0.60, 0.66, 0.70, 0.72, 0.74, 0.76, 0.80]

# Sustain test (how long context is held)
SUSTAIN_STEPS = [50, 150, 300, 600]

# Forced win parameters
FORCED_CONTEXT = 0.8
FORCED_VALUE = 1.0


# ============================================================
# Helpers
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
        "time": runtime.time,
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


# ============================================================
# TEST 1: FORCED EARLY WIN
# ============================================================

def test_forced_win():
    print("\n=== TEST 1: FORCED EARLY WIN ===")

    runtime = build_runtime()

    for _ in range(BASELINE_STEPS):
        runtime.step()

    inject_context(runtime, FORCED_CONTEXT)
    runtime.inject_stimulus("vta", None, None, FORCED_VALUE)
    runtime.inject_stimulus("md", None, None, 1.0)

    for i in range(TEST_STEPS):
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
# TEST 2: CONTEXT x DOPAMINE SWEEP
# ============================================================

def test_context_dopa_sweep():
    print("\n=== TEST 2: CONTEXT x DOPAMINE SWEEP ===")

    for ctx in CONTEXT_GAINS:
        for val in VALUE_MAGS:
            print(f"\n-- ctx={ctx:.2f} | val={val:.2f} --")
            runtime = build_runtime()

            for _ in range(BASELINE_STEPS):
                runtime.step()

            inject_context(runtime, ctx)
            runtime.inject_stimulus("vta", None, None, val)
            runtime.inject_stimulus("md", None, None, 1.0)

            for i in range(TEST_STEPS):
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
                        f"FIRE | step={d['step']} "
                        f"| winner={d['winner']} "
                        f"| relief={d['relief']:.3f}"
                    )
                    break
            else:
                print("NO DECISION")


# ============================================================
# TEST 3: CONTEXT SUSTAIN SWEEP
# ============================================================

def test_context_sustain():
    print("\n=== TEST 3: CONTEXT SUSTAIN DURATION ===")

    for sustain in SUSTAIN_STEPS:
        print(f"\n-- sustain_steps={sustain} --")
        runtime = build_runtime()

        for _ in range(BASELINE_STEPS):
            runtime.step()

        inject_context(runtime, 0.3)
        runtime.inject_stimulus("vta", None, None, 0.72)
        runtime.inject_stimulus("md", None, None, 1.0)

        for i in range(TEST_STEPS):
            runtime.step()

            if i == sustain:
                runtime.context.clear()

            d = runtime.get_decision_state()
            if d:
                print(
                    f"FIRE | step={d['step']} "
                    f"| sustain={sustain}"
                )
                break
        else:
            print("NO DECISION")


# ============================================================
# TEST 4: TARGETED STRIATAL BIAS
# ============================================================

def test_targeted_bias():
    print("\n=== TEST 4: TARGETED STRIATAL BIAS ===")

    for channel in ["D1", "D2"]:
        print(f"\n-- bias_channel={channel} --")
        runtime = build_runtime()

        for _ in range(BASELINE_STEPS):
            runtime.step()

        inject_context(runtime, 0.3, channel=channel)
        runtime.inject_stimulus("vta", None, None, 0.72)
        runtime.inject_stimulus("md", None, None, 1.0)

        for _ in range(TEST_STEPS):
            runtime.step()
            d = runtime.get_decision_state()
            if d:
                print(
                    f"FIRE | winner={d['winner']} "
                    f"| biased={channel}"
                )
                break
        else:
            print("NO DECISION")


# ============================================================
# MAIN
# ============================================================

def main():
    test_forced_win()
    test_context_dopa_sweep()
    test_context_sustain()
    test_targeted_bias()
    print("\n=== ALL TESTS COMPLETE ===")


if __name__ == "__main__":
    main()
