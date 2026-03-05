from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[3]
DT = 0.01

BASELINE_STEPS = 600
REPORT_EVERY = 50


def main() -> None:
    print("=== URGENCY BASELINE SANITY TEST ===")

    # ------------------------------------------------------------
    # Build runtime
    # ------------------------------------------------------------
    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    rt = BrainRuntime(brain, dt=DT)

    # ------------------------------------------------------------
    # Enable urgency system (but keep it inert)
    # ------------------------------------------------------------
    rt.enable_urgency = True

    # Explicitly disable dynamics
    rt.urgency_signal.reset()
    rt.urgency_signal.disable()

    print("[INFO] Urgency enabled, dynamics disabled")
    print("[INFO] Running baseline steps...\n")

    # ------------------------------------------------------------
    # Run
    # ------------------------------------------------------------
    for step in range(BASELINE_STEPS):
        rt.step()

        if step % REPORT_EVERY == 0:
            relief = rt.snapshot_gate_state().get("relief", None)

            snap = getattr(rt, "_last_striatum_snapshot", {}) or {}
            dom = snap.get("dominance", {})
            delta = 0.0
            if len(dom) >= 2:
                vals = sorted(dom.values(), reverse=True)
                delta = vals[0] - vals[1]

            urgency = rt.urgency_adapter.last_urgency

            print(
                f"[t={rt.time:6.2f}] "
                f"relief={relief:.4f} "
                f"delta={delta:.6f} "
                f"urgency={urgency:.4f}"
            )

    # ------------------------------------------------------------
    # Final report
    # ------------------------------------------------------------
    print("\n=== FINAL STATE ===")
    print(f"urgency_signal.value = {rt.urgency_signal.value:.4f}")
    print(f"last_urgency        = {rt.urgency_adapter.last_urgency:.4f}")

    if hasattr(rt, "urgency_trace"):
        summary = rt.urgency_trace.summary()
        print("urgency_trace:", summary)

    decision = rt.get_decision_state()
    print("decision_state:", decision)

    print("\n[OK] Baseline urgency test complete")


if __name__ == "__main__":
    main()
