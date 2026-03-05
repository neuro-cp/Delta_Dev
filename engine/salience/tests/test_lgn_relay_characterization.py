# engine/thalamus/tests/test_lgn_relay_characterization.py
from __future__ import annotations

from pathlib import Path
from typing import Dict

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


BASE_DIR = Path(__file__).resolve().parents[3]


def snapshot(runtime: BrainRuntime) -> Dict[str, float]:
    """
    Minimal snapshot of relay-relevant regions.
    """
    v1 = runtime.snapshot_region_stats("v1")["mean"]
    assoc = runtime.snapshot_region_stats("association_cortex")["mean"]
    pfc = runtime.snapshot_region_stats("pfc")["mean"]

    snap = getattr(runtime, "_last_striatum_snapshot", {}) or {}
    dom = snap.get("dominance", {})

    delta = 0.0
    if len(dom) >= 2:
        vals = sorted(dom.values(), reverse=True)
        delta = vals[0] - vals[1]

    return {
        "V1": v1,
        "ASSOC": assoc,
        "PFC": pfc,
        "DELTA": delta,
    }


def main():
    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()
    brain = loader.compile()

    rt = BrainRuntime(brain)
    rt.enable_vta_value = False
    rt.enable_urgency = False

    # ------------------------------
    # Warmup
    # ------------------------------
    for _ in range(200):
        rt.step()

    print("[INFO] Warmup complete\n")

    # ============================================================
    # PHASE A — Baseline (no LGN stimulation)
    # ============================================================
    print("[PHASE A] Baseline (no LGN stimulation)")

    phase_a = []
    for i in range(6):
        for _ in range(50):
            rt.step()

        snap = snapshot(rt)
        phase_a.append(snap)

        print(
            f"[A {i*50:03d}] "
            f"V1={snap['V1']:.6f} "
            f"ASSOC={snap['ASSOC']:.6f} "
            f"PFC={snap['PFC']:.6f} "
            f"Δ={snap['DELTA']:.6f}"
        )

    # ============================================================
    # PHASE B — LGN relay active
    # ============================================================
    print("\n[PHASE B] LGN relay active (poke lgn 1.0)")

    phase_b = []
    for i in range(6):
        rt.inject_stimulus("lgn", magnitude=1.0)

        for _ in range(50):
            rt.step()

        snap = snapshot(rt)
        phase_b.append(snap)

        print(
            f"[B {i*50:03d}] "
            f"V1={snap['V1']:.6f} "
            f"ASSOC={snap['ASSOC']:.6f} "
            f"PFC={snap['PFC']:.6f} "
            f"Δ={snap['DELTA']:.6f}"
        )

    # ============================================================
    # SUMMARY
    # ============================================================
    def mean(xs, k):
        return sum(x[k] for x in xs) / len(xs)

    print("\n=== LGN RELAY CHARACTERIZATION SUMMARY ===\n")

    print("Phase A (baseline):")
    print(f"V1 mean:    {mean(phase_a, 'V1'):.6f}")
    print(f"ASSOC mean:{mean(phase_a, 'ASSOC'):.6f}")
    print(f"PFC mean:  {mean(phase_a, 'PFC'):.6f}")
    print(f"Δ mean:    {mean(phase_a, 'DELTA'):.6f}\n")

    print("Phase B (LGN active):")
    print(f"V1 mean:    {mean(phase_b, 'V1'):.6f}")
    print(f"ASSOC mean:{mean(phase_b, 'ASSOC'):.6f}")
    print(f"PFC mean:  {mean(phase_b, 'PFC'):.6f}")
    print(f"Δ mean:    {mean(phase_b, 'DELTA'):.6f}\n")

    print("No decisions expected or checked.")
    print("========================================")


if __name__ == "__main__":
    main()
