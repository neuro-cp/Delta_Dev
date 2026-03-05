from __future__ import annotations

from pathlib import Path
from typing import Dict

from engine.loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


BASE_DIR = Path(__file__).resolve().parents[3]


def main() -> None:
    print("=== HYPOTHESIS OBSERVATION TEST (STRUCTURAL, READ-ONLY) ===")

    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    rt = BrainRuntime(brain, dt=0.01)

    # ------------------------------------------------------------
    # Stimulus: association cortex only (lawful source)
    # ------------------------------------------------------------
    TARGET_REGION = "association_cortex"
    TARGET_POP = "L5_PYRAMIDAL_A"

    print(f"[INIT] Stimulating {TARGET_REGION}:{TARGET_POP}")

    for step in range(1200):
        # Sustained but modest drive
        if 50 <= step <= 500:
            rt.inject_stimulus(
                region_id=TARGET_REGION,
                population_id=TARGET_POP,
                magnitude=0.8,
            )

        rt.step()

        if step % 100 == 0:
            snap = getattr(rt, "_last_striatum_snapshot", {}) or {}
            dominance = snap.get("dominance", {})

            active_hypotheses: Dict[str, str] = dict(
                rt.hypothesis_registry.assignments
            )

            print(
                f"[STEP {step:04d}] "
                f"hypotheses={len(active_hypotheses)} "
                f"dominance={ {k: round(v, 4) for k, v in dominance.items()} }"
            )

    print("\n=== FINAL STATE ===")
    print("Registered hypotheses:")
    for aid, hid in rt.hypothesis_registry.assignments.items():
        print(f"  {aid} -> {hid}")

    print("\nTest complete. No assertions made.")


if __name__ == "__main__":
    main()
