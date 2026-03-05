from __future__ import annotations

import time

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.salience.salience_sparsity_gate import SalienceSparsityGate
from engine.command_server import start_command_server


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = r"C:\Users\Admin\Desktop\neural framework"
DT = 0.01
STEPS = 800

KEEP_RATIO = 0.25
SPARSITY_SEED = 42

VALUE_MAG = 0.6   # moderate authorization pressure
ENABLE_URGENCY = False


# ============================================================
# TEST
# ============================================================

def main():
    print("\n=== TEST: Salience MD Extension (Observational) ===\n")

    # --------------------------------------------------
    # Load brain
    # --------------------------------------------------
    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile=None,
        state_profile=None,
        compound_profile=None,
    )

    runtime = BrainRuntime(brain, dt=DT)

    # --------------------------------------------------
    # Configure subsystems (no cheating)
    # --------------------------------------------------
    runtime.enable_salience = True
    runtime.enable_vta_value = True
    runtime.enable_urgency = ENABLE_URGENCY

    runtime.value_set(VALUE_MAG)

    # --------------------------------------------------
    # Attach salience sparsity gate (MD ONLY)
    # --------------------------------------------------
    md_state = runtime.region_states.get("md")
    assert md_state is not None, "MD region not found"

    md_assemblies = [
        p.assembly_id
        for plist in md_state["populations"].values()
        for p in plist
    ]

    print(f"[INIT] MD assemblies: {len(md_assemblies)}")

    gate = SalienceSparsityGate(
        keep_ratio=KEEP_RATIO,
        seed=SPARSITY_SEED,
    )

    gate.initialize(md_assemblies)
    runtime.salience.attach_sparsity_gate(gate)

    print("[INIT] Salience sparsity gate attached to MD")
    print("[INIT] Gate stats:", gate.stats())

    # --------------------------------------------------
    # Optional live inspection (TCP)
    # --------------------------------------------------
    start_command_server(runtime, port=5558)
    print("[INFO] Command server on port 5558")

    # --------------------------------------------------
    # Run (NO STIMULI)
    # --------------------------------------------------
    for step in range(STEPS):
        runtime.step()

        if step % 50 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {}) or {}
            gate_state = runtime.snapshot_gate_state()

            delta = 0.0
            dom = snap.get("dominance", {})
            if len(dom) >= 2:
                vals = sorted(dom.values(), reverse=True)
                delta = vals[0] - vals[1]

            print(
                f"[STEP {step:04d}] "
                f"Δ={delta:.6f} "
                f"relief={gate_state.get('relief', 1.0):.4f} "
                f"decision={runtime.get_decision_state() is not None}"
            )

        time.sleep(0.0)

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
