# engine/salience/tests/test_salience_driven_asymmetry.py
from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.salience.salience_sparsity_gate import SalienceSparsityGate


DT = 0.01
STEPS = 800
SAL_DELTA = 0.4


def main() -> None:
    print("=== TEST 5C: Salience-driven lawful asymmetry ===")

    root = Path("C:/Users/Admin/Desktop/neural framework")

    # --------------------------------------------------
    # Load brain
    # --------------------------------------------------
    loader = NeuralFrameworkLoader(root)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    rt = BrainRuntime(brain, dt=DT)

    # --------------------------------------------------
    # Attach sparsity gate to salience
    # --------------------------------------------------
    gate = SalienceSparsityGate(
        keep_ratio=0.25,
        seed=42,
    )

    # Collect all assembly IDs
    assembly_ids = [
        p.assembly_id
        for region in rt.region_states.values()
        for plist in region["populations"].values()
        for p in plist
    ]

    gate.initialize(assembly_ids)
    rt.salience.attach_sparsity_gate(gate)

    # --------------------------------------------------
    # Inject salience only (no pokes)
    # --------------------------------------------------
    for aid in assembly_ids:
        rt.salience.inject(aid, SAL_DELTA)

    # --------------------------------------------------
    # Run dynamics
    # --------------------------------------------------
    for _ in range(STEPS):
        rt.step()

    # --------------------------------------------------
    # Measure striatal asymmetry
    # --------------------------------------------------
    striatum = rt.region_states["striatum"]

    d1_mass = sum(
        p.output()
        for p in striatum["populations"]["D1_MSN"]
    )
    d2_mass = sum(
        p.output()
        for p in striatum["populations"]["D2_MSN"]
    )

    delta = abs(d1_mass - d2_mass)

    print(f"D1 mass = {d1_mass:.4f}")
    print(f"D2 mass = {d2_mass:.4f}")
    print(f"Dominance delta = {delta:.4f}")

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert delta > 0.004, "Salience failed to induce asymmetry"
    assert rt.get_decision_state() is None, "Decision fired illegally"

    print("[PASS] Salience induces lawful asymmetry without decisions")


if __name__ == "__main__":
    main()
