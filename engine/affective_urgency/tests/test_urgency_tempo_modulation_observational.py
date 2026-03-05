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
    # CONFIG: fixed conditions
    # ------------------------------------------------------------
    runtime.enable_urgency = True
    runtime.urgency_signal.enabled = True
    runtime.urgency_signal.rise_rate = 0.004
    runtime.urgency_signal.decay_rate = 0.002

    runtime.value_set(0.4)   # fixed, sub-decisional value

    print("\n[PHASE 1] Baseline (no urgency drive)")
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
        raise RuntimeError("Need at least two association assemblies")

    a0, a1 = assemblies[0], assemblies[1]

    print("\n[PHASE 2] Assigning hypotheses (fixed asymmetry source)")
    runtime.hypothesis_registry.register(a0.assembly_id, "H1")
    runtime.hypothesis_registry.register(a1.assembly_id, "H2")

    print(f"  {a0.assembly_id} → H1")
    print(f"  {a1.assembly_id} → H2")

    # ------------------------------------------------------------
    # Fixed asymmetric stimulation
    # ------------------------------------------------------------
    print("\n[PHASE 3] Fixed asymmetric drive (urgency OFF)")

    runtime.urgency_signal.enabled = False

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
                v = sorted(dom.values(), reverse=True)
                delta = v[0] - v[1]

            print(
                f"[NO-URG {i:04d}] Δ={delta:.6f} "
                f"relief={relief:.4f} decision={runtime.get_decision_state()}"
            )

    # ------------------------------------------------------------
    # Urgency ON (tempo modulation)
    # ------------------------------------------------------------
    print("\n[PHASE 4] Urgency enabled (tempo modulation only)")

    runtime.urgency_signal.enabled = True

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

        snap = getattr(runtime, "_last_striatum_snapshot", {})
        dom = snap.get("dominance", {})
        relief = runtime.snapshot_gate_state()["relief"]
        decision = runtime.get_decision_state()

        delta = 0.0
        if len(dom) >= 2:
            v = sorted(dom.values(), reverse=True)
            delta = v[0] - v[1]

        if i % 50 == 0 or decision:
            print(
                f"[URG {i:04d}] Δ={delta:.6f} "
                f"relief={relief:.4f} decision={decision}"
            )

        if decision:
            break

    print("\n=== TEST COMPLETE ===")
    print("Expect:")
    print("• Δ remains approximately constant")
    print("• Relief rises faster under urgency")
    print("• Latch timing may advance")
    print("• Winner identity unchanged")
    print("• No urgency-only asymmetry creation")
    print("No asserts by design.")


if __name__ == "__main__":
    main()
