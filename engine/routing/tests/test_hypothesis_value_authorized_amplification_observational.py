from __future__ import annotations

from pathlib import Path
from typing import Dict

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


BASE_DIR = Path(__file__).resolve().parents[3]


def main() -> None:
    # ============================================================
    # Build runtime
    # ============================================================
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

    # Ensure value is enabled but neutral
    runtime.enable_vta_value = True
    runtime.value_set(0.0)

    # ============================================================
    # PHASE 1 — Baseline
    # ============================================================
    print("\n[PHASE 1] Baseline (no hypotheses, no value)")
    for i in range(200):
        runtime.step()
        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            relief = runtime.snapshot_gate_state()["relief"]
            print(
                f"[BASE {i:04d}] "
                f"dominance={snap.get('dominance')} "
                f"relief={relief:.4f}"
            )

    # ============================================================
    # Identify association cortex assemblies
    # ============================================================
    assoc = runtime.region_states.get("association_cortex")
    if not assoc:
        raise RuntimeError("association_cortex not found")

    assemblies = [
        p for plist in assoc["populations"].values() for p in plist
    ]

    if len(assemblies) < 2:
        raise RuntimeError("Need at least two association cortex assemblies")

    a0, a1 = assemblies[0], assemblies[1]

    # ============================================================
    # PHASE 2 — Assign hypotheses
    # ============================================================
    print("\n[PHASE 2] Assigning hypotheses")

    runtime.hypothesis_registry.register(a0.assembly_id, "H1")
    runtime.hypothesis_registry.register(a1.assembly_id, "H2")

    print(f"  {a0.assembly_id} → H1")
    print(f"  {a1.assembly_id} → H2")

    # ============================================================
    # PHASE 3 — Asymmetric drive (no value)
    # ============================================================
    print("\n[PHASE 3] Asymmetric drive (value = 0.0)")

    for i in range(400):
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
                f"[ASYM {i:04d}] "
                f"dominance={dom} "
                f"Δ={delta:.6f} "
                f"relief={relief:.4f}"
            )

    # ============================================================
    # PHASE 4 — Value-authorized amplification
    # ============================================================
    print("\n[PHASE 4] Value-authorized amplification")

    runtime.value_set(0.6)

    for i in range(400):
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
            dom = snap.get("dominance", {})
            relief = runtime.snapshot_gate_state()["relief"]

            delta = 0.0
            if len(dom) >= 2:
                vals = sorted(dom.values(), reverse=True)
                delta = vals[0] - vals[1]

            print(
                f"[VALUE {i:04d}] "
                f"dominance={dom} "
                f"Δ={delta:.6f} "
                f"relief={relief:.4f}"
            )

    # ============================================================
    # PHASE 5 — Value withdrawal
    # ============================================================
    print("\n[PHASE 5] Value withdrawal")

    runtime.value_set(0.0)

    for i in range(200):
        runtime.step()
        if i % 100 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            relief = runtime.snapshot_gate_state()["relief"]
            print(
                f"[WITHDRAW {i:04d}] "
                f"dominance={snap.get('dominance')} "
                f"relief={relief:.4f}"
            )

    print("\n=== TEST COMPLETE ===")
    print(
        "Expect:\n"
        "• Δ exists before value\n"
        "• Δ increases faster / higher under value\n"
        "• Δ does NOT appear without asymmetry\n"
        "• No latch firing\n"
        "• Clean decay after value removal\n"
    )


if __name__ == "__main__":
    main()
