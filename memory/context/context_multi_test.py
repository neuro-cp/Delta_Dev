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
        "time": runtime.time,
        "step": runtime.step_count,
        "relief": runtime._last_gate_strength,
        "winner": winner,
        "delta_dom": delta_dom,
        "ctx_max": runtime.context.stats()["max_gain"],
        "decision_counter": getattr(runtime, "_decision_counter", None),
    }


def load_runtime() -> BrainRuntime:
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


# ============================================================
# Trial core
# ============================================================

def run_trial(
    *,
    label: str,
    context_gain: float = 0.0,
    value_gain: float = 0.0,
    sustain_steps: int = 1,
    context_mode: str = "global",  # "global" | "local"
    context_fraction: float = 1.0,
) -> Dict[str, Any]:

    print(f"\n=== TRIAL: {label} ===")

    runtime = load_runtime()

    # ----------------------------
    # Baseline
    # ----------------------------
    for _ in range(BASELINE_STEPS):
        runtime.step()

    # ----------------------------
    # Context injection
    # ----------------------------
    pfc = runtime.region_states.get("pfc")
    biased_ids: List[str] = []

    if pfc and context_gain > 0.0:
        all_assemblies = [
            p.assembly_id
            for plist in pfc["populations"].values()
            for p in plist
        ]

        if context_mode == "local":
            n = max(1, int(len(all_assemblies) * context_fraction))
            biased_ids = all_assemblies[:n]
        else:
            biased_ids = all_assemblies

    # ----------------------------
    # Value injection (VTA)
    # ----------------------------
    if value_gain > 0.0:
        runtime.inject_stimulus(
            region_id="vta",
            population_id=None,
            assembly_index=None,
            magnitude=value_gain,
        )

    # ----------------------------
    # Task stimulus
    # ----------------------------
    runtime.inject_stimulus(
        region_id="md",
        population_id=None,
        assembly_index=None,
        magnitude=1.0,
    )

    # ----------------------------
    # Run window
    # ----------------------------
    decision: Optional[Dict[str, Any]] = None

    for i in range(TEST_STEPS):
        # sustain context
        if i < sustain_steps:
            for aid in biased_ids:
                runtime.context.add_gain(
                    assembly_id=aid,
                    delta=context_gain,
                    domain="global",
                )

        runtime.step()
        snap = snapshot_runtime(runtime)

        if i % REPORT_EVERY == 0:
            print(
                f"[step {snap['step']:5d}] "
                f"relief={snap['relief']:.3f} "
                f"winner={snap['winner']} "
                f"delta_dom={snap['delta_dom']} "
                f"ctx_max={snap['ctx_max']:.3f} "
                f"dec_cnt={snap['decision_counter']}"
            )

        d = runtime.get_decision_state()
        if d is not None:
            decision = d
            print(">>> DECISION LATCH FIRED <<<")
            break

    return {
        "label": label,
        "decision_fired": decision is not None,
        "decision": decision,
    }


# ============================================================
# Main – all three experiments
# ============================================================

def main() -> None:
    print("=== CONTEXT / VALUE / PERSISTENCE TEST SUITE ===")

    # --------------------------------------------------------
    # TEST 1: Context + Value interaction
    # --------------------------------------------------------
    for g in [0.2, 0.5]:
        for v in [0.6, 0.72, 0.8]:
            run_trial(
                label=f"context+value g={g} v={v}",
                context_gain=g,
                value_gain=v,
                sustain_steps=50,
            )

    # --------------------------------------------------------
    # TEST 2: Persistence sweep
    # --------------------------------------------------------
    for sustain in [5, 20, 50, 100, 200]:
        run_trial(
            label=f"persistence sustain={sustain}",
            context_gain=0.3,
            value_gain=0.72,
            sustain_steps=sustain,
        )

    # --------------------------------------------------------
    # TEST 3: Context locality
    # --------------------------------------------------------
    for frac in [1.0, 0.5, 0.25, 0.1]:
        run_trial(
            label=f"context locality frac={frac}",
            context_gain=0.4,
            value_gain=0.72,
            context_mode="local",
            context_fraction=frac,
            sustain_steps=80,
        )

    print("\n=== ALL TESTS COMPLETE ===")


if __name__ == "__main__":
    main()
