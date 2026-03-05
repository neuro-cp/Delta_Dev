from __future__ import annotations

from pathlib import Path
from typing import Dict

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


BASE_DIR = Path(__file__).resolve().parents[2]


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
    # Phase 1: Baseline (no stimulus, no urgency, no value)
    # ------------------------------------------------------------
    print("\n[PHASE 1] Baseline (no stimulus)")

    runtime.enable_urgency = False
    runtime.enable_vta_value = False

    for i in range(200):
        runtime.step()
        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            dom = snap.get("dominance", {})
            relief = runtime.snapshot_gate_state()["relief"]
            control = runtime.get_control_state()
            working = runtime.pfc_adapter.snapshot()

            print(
                f"[BASE {i:04d}] "
                f"dominance={dom} "
                f"relief={relief:.4f} "
                f"control={control.phase if control else None} "
                f"working={working}"
            )

    # ------------------------------------------------------------
    # Phase 2: Establish lawful asymmetry (fixed source)
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
    # Phase 3: Drive to decision (fixed asymmetric stimulus)
    # ------------------------------------------------------------
    print("\n[PHASE 3] Driving system to lawful decision")

    decision_step = None

    for i in range(600):
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
        dom: Dict[str, float] = snap.get("dominance", {})
        relief = runtime.snapshot_gate_state()["relief"]
        decision = runtime.get_decision_state()

        delta = 0.0
        if len(dom) >= 2:
            vals = sorted(dom.values(), reverse=True)
            delta = vals[0] - vals[1]

        if i % 50 == 0 or decision is not None:
            control = runtime.get_control_state()
            working = runtime.pfc_adapter.snapshot()

            print(
                f"[DRIVE {i:04d}] "
                f"Δ={delta:.6f} "
                f"relief={relief:.4f} "
                f"decision={decision} "
                f"control={control.phase if control else None} "
                f"working={working}"
            )

        if decision is not None:
            decision_step = runtime.step_count
            print(f"\n>>> DECISION FIRED at step {decision_step}")
            break

    if decision_step is None:
        print("\n!!! No decision fired — test inconclusive")
        return

    # ------------------------------------------------------------
    # Phase 4: Post-decision persistence (NO STIMULUS)
    # ------------------------------------------------------------
    print("\n[PHASE 4] Post-decision persistence (stimulus removed)")

    for i in range(600):
        runtime.step()

        snap = getattr(runtime, "_last_striatum_snapshot", {})
        dom = snap.get("dominance", {})
        relief = runtime.snapshot_gate_state()["relief"]
        decision = runtime.get_decision_state()
        control = runtime.get_control_state()
        working = runtime.pfc_adapter.snapshot()

        delta = 0.0
        if len(dom) >= 2:
            vals = sorted(dom.values(), reverse=True)
            delta = vals[0] - vals[1]

        if i % 50 == 0:
            print(
                f"[POST {i:04d}] "
                f"Δ={delta:.6f} "
                f"relief={relief:.4f} "
                f"decision={decision} "
                f"control={control.phase if control else None} "
                f"working={working}"
            )

    print("\n=== TEST COMPLETE ===")
    print("Expect:")
    print("• Decision fires lawfully under stimulus")
    print("• Working state remains engaged post-decision")
    print("• Dominance persists temporarily without stimulus")
    print("• No re-decision occurs")
    print("• Working state eventually decays")
    print("• Control phase remains post-commit, then stabilizes")
    print("No asserts by design.")


if __name__ == "__main__":
    main()
