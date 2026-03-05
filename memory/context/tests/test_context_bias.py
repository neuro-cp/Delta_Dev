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
TEST_STEPS = 600

# How often to print live diagnostics (steps)
REPORT_EVERY = 50


# ============================================================
# Helpers
# ============================================================

def snapshot_runtime(runtime: BrainRuntime) -> Dict[str, Any]:
    """
    Non-invasive snapshot of key runtime state.
    """
    snap = getattr(runtime, "_last_striatum_snapshot", None)

    dominance = {}
    delta_dom = None
    winner = None

    if snap and snap.get("dominance"):
        dominance = dict(snap["dominance"])
        vals = sorted(dominance.values(), reverse=True)
        if len(vals) >= 2:
            delta_dom = vals[0] - vals[1]
        winner = snap.get("winner")

    return {
        "time": runtime.time,
        "step": runtime.step_count,
        "relief": runtime._last_gate_strength,
        "winner": winner,
        "dominance": dominance,
        "delta_dom": delta_dom,
        "context": runtime.context.stats(),
        "decision_counter": getattr(runtime, "_decision_counter", None),
    }


# ============================================================
# Trial runner
# ============================================================

def run_trial(context_gain: float) -> Dict[str, Any]:
    """
    Run a single runtime trial with a fixed context gain.
    """

    # ----------------------------
    # Load brain
    # ----------------------------
    loader = NeuralFrameworkLoader(ROOT)

    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain, dt=DT)

    # ----------------------------
    # Baseline settle
    # ----------------------------
    for _ in range(BASELINE_STEPS):
        runtime.step()

    # ----------------------------
    # Inject context (manual)
    # ----------------------------
    if context_gain > 0.0:
        pfc = runtime.region_states.get("pfc")
        if pfc:
            for plist in pfc["populations"].values():
                for p in plist:
                    runtime.context.add_gain(
                        assembly_id=p.assembly_id,
                        delta=context_gain,
                        domain="global",
                    )

    # ----------------------------
    # Apply identical stimulus
    # ----------------------------
    runtime.inject_stimulus(
        region_id="md",
        population_id=None,
        assembly_index=None,
        magnitude=1.0,
    )

    # ----------------------------
    # Run test window
    # ----------------------------
    decision: Optional[Dict[str, Any]] = None
    trace = []

    for i in range(TEST_STEPS):
        runtime.step()

        snap = snapshot_runtime(runtime)
        trace.append(snap)

        if i % REPORT_EVERY == 0:
            print(
                f"[step {snap['step']:5d}] "
                f"relief={snap['relief']:.3f} "
                f"winner={snap['winner']} "
                f"delta_dom={snap['delta_dom'] if snap['delta_dom'] is not None else 'NA'} "
                f"ctx_max={snap['context']['max_gain']:.3f} "
                f"dec_cnt={snap['decision_counter']}"
            )

        d = runtime.get_decision_state()
        if d is not None:
            decision = d
            print(">>> DECISION LATCH FIRED <<<")
            break

    return {
        "context_gain": context_gain,
        "decision_fired": decision is not None,
        "decision": decision,
        "trace": trace,
    }


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=== CONTEXT - DECISION BIAS TEST (INSTRUMENTED) ===\n")

    gains = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]

    for g in gains:
        print(f"\n--- Testing context gain = {g:.2f} ---")
        res = run_trial(g)

        if res["decision_fired"]:
            d = res["decision"]
            print(
                f"\nFIRE | time={d['time']:.3f} "
                f"| step={d['step']} "
                f"| winner={d['winner']} "
                f"| delta_dom={d['delta_dominance']:.4f} "
                f"| relief={d['relief']:.3f}"
            )
        else:
            print("\nNO DECISION (within test window)")

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
