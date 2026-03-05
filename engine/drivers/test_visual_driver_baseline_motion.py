from __future__ import annotations

from pathlib import Path
from typing import Dict

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.drivers.visual_temporal_driver import VisualTemporalDriver

# ---- salience (explicit, test-driven) ----
from engine.salience.salience_engine import SalienceEngine
from engine.salience.sources.surprise_source import SurpriseSource


ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# Brain compilation
# ============================================================
def compile_brain() -> dict:
    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()
    return loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )


# ============================================================
# Experiment
# ============================================================
def main() -> None:
    brain = compile_brain()
    rt = BrainRuntime(brain, dt=0.01)

    # --------------------------------------------------------
    # Salience (manual, transparent)
    # --------------------------------------------------------
    surprise = SurpriseSource()
    salience_engine = SalienceEngine(sources=[surprise])
    salience_trace = salience_engine.trace

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------
    STABILIZATION_SECONDS = 5.0
    STABILIZATION_STEPS = int(STABILIZATION_SECONDS / rt.dt)

    STIM_DURATION_STEPS = 140
    STIM_ONSET = STABILIZATION_STEPS
    STIM_OFFSET = STABILIZATION_STEPS + STIM_DURATION_STEPS

    driver = VisualTemporalDriver(
        onset_step=STIM_ONSET,
        offset_step=STIM_OFFSET,
        magnitude=0.60,
    )

    print("\n=== BASELINE-AWARE SURPRISE DIAGNOSTIC (LGN) ===")

    total_steps = STIM_OFFSET + 200
    baseline_mass: float | None = None

    # ========================================================
    # Main loop
    # ========================================================
    for step in range(total_steps):
        driver.step(rt)
        rt.step()

        # ----------------------------------------------------
        # Capture baseline ONCE after stabilization
        # ----------------------------------------------------
        if step == STABILIZATION_STEPS:
            snap = rt.snapshot_region_stats("lgn")
            baseline_mass = snap["mass"]

            print(
                f"\n[BASELINE CAPTURED]\n"
                f"  step          = {step}\n"
                f"  baseline_mass = {baseline_mass:.6e}\n"
            )

        # ----------------------------------------------------
        # Compute Δmass and feed surprise
        # ----------------------------------------------------
        delta_mass = None
        if baseline_mass is not None:
            snap = rt.snapshot_region_stats("lgn")
            mass = snap["mass"]
            delta_mass = mass - baseline_mass

            observation: Dict[str, float] = {
                "lgn.mass": delta_mass
            }

            deltas = surprise._compute_delta(observation)

            for channel_id, delta in deltas.items():
                salience_trace.record(
                    source=surprise.name,
                    channel_id=channel_id,
                    delta=delta,
                    step=-1,  # interpretive time
                )

        # ----------------------------------------------------
        # Diagnostic probe (signal + salience)
        # ----------------------------------------------------
        if step in (STIM_ONSET + 20, STIM_OFFSET + 20):
            snap = rt.snapshot_region_stats("lgn")
            mass = snap["mass"]
            mean = snap["mean"]

            print("\n--- DIAGNOSTIC SNAPSHOT ---")
            print(f"step            = {step}")
            print(f"mean_activity   = {mean:.6e}")
            print(f"mass            = {mass:.6e}")
            print(f"baseline_mass   = {baseline_mass:.6e}")
            print(f"Δmass           = {delta_mass:.6e}")
            print(
                f"|Δmass| > EPS   = "
                f"{abs(delta_mass) > surprise.EPSILON}"
            )

            print("\n--- SALIENCE TRACE SNAPSHOT ---")
            recent = salience_trace.recent_events(10)

            if not recent:
                print("  (no salience proposals)")
            else:
                for ev in recent:
                    print(
                        f"  step={ev.step:6d} "
                        f"source={ev.source:>10s} "
                        f"channel={ev.channel_id:>12s} "
                        f"delta={ev.delta:.6e}"
                    )

            print("--- END SNAPSHOT ---")

    print("\n=== END ===")


if __name__ == "__main__":
    main()
