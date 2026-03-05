from __future__ import annotations

from pathlib import Path
from typing import Dict

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


BASE_DIR = Path(__file__).resolve().parents[3]


def main() -> None:
    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain, dt=0.01)

    # ------------------------------------------------------------
    # Phase 1: Baseline
    # ------------------------------------------------------------
    print("\n[PHASE 1] Baseline (no value, no hypotheses)")
    for i in range(200):
        runtime.step()
        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            print(
                f"[BASE {i:04d}] dominance={snap.get('dominance')} "
                f"relief={runtime.snapshot_gate_state()['relief']:.4f}"
            )

    # ------------------------------------------------------------
    # Identify association cortex assemblies
    # ------------------------------------------------------------
    assoc = runtime.region_states.get("association_cortex")
    if not assoc:
        raise RuntimeError("association_cortex not found")

    assemblies = [
        p for plist in assoc["populations"].values() for p in plist
    ]
    if len(assemblies) < 2:
        raise RuntimeError("Need at least two association cortex assemblies")

    a0, a1 = assemblies[0], assemblies[1]

    # ------------------------------------------------------------
    # Phase 2: Assign hypotheses
    # ------------------------------------------------------------
    print("\n[PHASE 2] Assigning hypotheses")
    runtime.hypothesis_registry.register(a0.assembly_id, "H1")
    runtime.hypothesis_registry.register(a1.assembly_id, "H2")

    print(f"  {a0.assembly_id} → H1")
    print(f"  {a1.assembly_id} → H2")

    # ------------------------------------------------------------
    # Phase 3: Weak asymmetric drive (creates lawful Δ)
    # ------------------------------------------------------------
    print("\n[PHASE 3] Weak asymmetric stimulation (Δ source)")

    for i in range(300):
        runtime.inject_stimulus(
            "association_cortex",
            assembly_index=0,
            magnitude=0.020 * 1.05,
        )
        runtime.inject_stimulus(
            "association_cortex",
            assembly_index=1,
            magnitude=0.020,
        )

        runtime.step()

        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            dom: Dict[str, float] = snap.get("dominance", {})
            relief = runtime.snapshot_gate_state()["relief"]

            delta = 0.0
            if len(dom) >= 2:
                vals = sorted(dom.values(), reverse=True)
                delta = vals[0] - vals[1]

            print(
                f"[ASYM {i:04d}] dominance={dom} "
                f"Δ={delta:.6f} relief={relief:.4f}"
            )

    # ------------------------------------------------------------
    # Phase 4: Value ceiling sweep
    # ------------------------------------------------------------
    print("\n[PHASE 4] Value ceiling sweep (authorization only)")

    for value in [0.2, 0.4, 0.6, 0.8, 1.0]:
        runtime.value_set(value)

        for i in range(150):
            runtime.step()

        snap = getattr(runtime, "_last_striatum_snapshot", {})
        dom = snap.get("dominance", {})
        relief = runtime.snapshot_gate_state()["relief"]
        decision = runtime.get_decision_state()

        delta = 0.0
        if len(dom) >= 2:
            vals = sorted(dom.values(), reverse=True)
            delta = vals[0] - vals[1]

        print(
            f"[VALUE {value:.2f}] dominance={dom} "
            f"Δ={delta:.6f} relief={relief:.4f} "
            f"decision={decision}"
        )

    # ------------------------------------------------------------
    # Phase 5: Value withdrawal
    # ------------------------------------------------------------
    print("\n[PHASE 5] Value withdrawal")

    runtime.value_set(0.0)

    for i in range(200):
        runtime.step()
        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            print(
                f"[WITHDRAW {i:04d}] dominance={snap.get('dominance')} "
                f"relief={runtime.snapshot_gate_state()['relief']:.4f}"
            )

    print("\n=== TEST COMPLETE ===")
    print("Expect:")
    print("• Δ increases with value but never appears without asymmetry")
    print("• GPi relief saturates")
    print("• No latch firing at any value")
    print("• Clean recovery after value removal")
    print("No asserts by design.")


if __name__ == "__main__":
    main()
