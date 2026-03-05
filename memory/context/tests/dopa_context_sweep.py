from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

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

# Context (PFC gain) sweep
CONTEXT_GAINS = [0.0, 0.1, 0.2, 0.3]

# Dopamine / value sweep (centered around your known latch regime)
VALUE_MAGS = [0.60, 0.66, 0.70, 0.72, 0.74, 0.76, 0.80]


# ============================================================
# Helpers
# ============================================================

def snapshot_runtime(runtime: BrainRuntime) -> Dict[str, Any]:
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
        "step": runtime.step_count,
        "time": runtime.time,
        "winner": winner,
        "delta_dom": delta_dom,
        "relief": runtime._last_gate_strength,
        "context": runtime.context.stats(),
    }


# ============================================================
# Trial runner
# ============================================================

def run_trial(context_gain: float, value_mag: float) -> Dict[str, Any]:
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
    # Baseline
    # ----------------------------
    for _ in range(BASELINE_STEPS):
        runtime.step()

    # ----------------------------
    # Inject context into PFC
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
    # Apply value (dopamine)
    # ----------------------------
    runtime.inject_stimulus(
        region_id="vta",
        population_id=None,
        assembly_index=None,
        magnitude=value_mag,
    )

    # ----------------------------
    # Apply identical sensory drive
    # ----------------------------
    runtime.inject_stimulus(
        region_id="md",
        population_id=None,
        assembly_index=None,
        magnitude=1.0,
    )

    decision: Optional[Dict[str, Any]] = None

    for i in range(TEST_STEPS):
        runtime.step()

        if i % REPORT_EVERY == 0:
            snap = snapshot_runtime(runtime)
            print(
                f"[step {snap['step']:5d}] "
                f"ctx={context_gain:.2f} "
                f"val={value_mag:.2f} "
                f"relief={snap['relief']:.3f} "
                f"winner={snap['winner']} "
                f"delta_dom={snap['delta_dom']}"
            )

        d = runtime.get_decision_state()
        if d is not None:
            decision = d
            break

    return {
        "context_gain": context_gain,
        "value_mag": value_mag,
        "decision_fired": decision is not None,
        "decision": decision,
    }


# ============================================================
# Main sweep
# ============================================================

def main() -> None:
    print("=== DOPAMINE x CONTEXT SWEEP ===")

    results: List[Dict[str, Any]] = []

    for ctx in CONTEXT_GAINS:
        for val in VALUE_MAGS:
            print(f"\n--- ctx={ctx:.2f} | value={val:.2f} ---")
            res = run_trial(ctx, val)
            results.append(res)

            if res["decision_fired"]:
                d = res["decision"]
                print(
                    f"FIRE | step={d['step']} "
                    f"| winner={d['winner']} "
                    f"| relief={d['relief']:.3f} "
                    f"| delta_dom={d['delta_dominance']:.4f}"
                )
            else:
                print("NO DECISION")

    print("\n=== SWEEP COMPLETE ===")


if __name__ == "__main__":
    main()
