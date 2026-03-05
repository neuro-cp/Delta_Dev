# competition_d1_poke_test.py
# Runs a D1-only stimulation test and logs competition dynamics
# Output: kernel_dominance_trace.csv
#
# Schema:
# step,time,channel,effective_output,inst_dominance,smooth_dominance,winner,delta

from __future__ import annotations

from pathlib import Path
import csv

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
OUT_CSV = ROOT / "kernel_dominance_trace.csv"

DT = 0.01
BASELINE_STEPS = 300
TEST_STEPS = 500

# D1-only poke
POKE_START = 120
POKE_END   = 130
D1_POKE_MAG = 2.5


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=== D1-ONLY COMPETITION POKE TEST ===")

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
    # Prepare CSV
    # ----------------------------
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "step",
            "time",
            "channel",
            "effective_output",
            "inst_dominance",
            "smooth_dominance",
            "winner",
            "delta",
        ])

        # ----------------------------
        # Run test
        # ----------------------------
        for i in range(TEST_STEPS):
            step = runtime.step_count

            # ---- D1-only poke window ----
            if POKE_START <= step <= POKE_END:
                runtime.inject_stimulus(
                    region_id="striatum",
                    population_id="D1",
                    assembly_index=None,
                    magnitude=D1_POKE_MAG,
                )

            runtime.step()

            snap = getattr(runtime, "_last_striatum_snapshot", None)
            if not snap:
                continue

            dominance = snap.get("dominance", {})
            winner = snap.get("winner")

            # compute delta explicitly
            vals = sorted(dominance.values(), reverse=True)
            delta = vals[0] - vals[1] if len(vals) >= 2 else 0.0

            for channel, eff in snap.get("effective", {}).items():
                writer.writerow([
                    runtime.step_count,
                    runtime.time,
                    channel,
                    eff,
                    dominance.get(channel, 0.0),
                    snap.get("smoothed", {}).get(channel, 0.0),
                    winner,
                    delta,
                ])

    print(f"[OK] Test complete — CSV written to:\n{OUT_CSV}")


if __name__ == "__main__":
    main()
